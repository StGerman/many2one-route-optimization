import yaml
import pandas as pd
import math
import sys
import requests
import os
import logging
from dotenv import load_dotenv
from scipy.cluster.hierarchy import linkage, fcluster
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_requests(csv_path):
    df = pd.read_csv(csv_path)
    if df.empty or 'pickup_lat' not in df.columns or 'pickup_lng' not in df.columns:
        logging.error("CSV input invalid or empty.")
        raise ValueError("CSV does not contain required fields or is empty.")
    return list(zip(df['pickup_lat'], df['pickup_lng']))

def call_distance_matrix_api(locations, api_key):
    """Call Google Distance Matrix API and return time matrix."""
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    origins = "|".join([f"{lat},{lng}" for lat, lng in locations])
    destinations = origins

    params = {
        "origins": origins,
        "destinations": destinations,
        "key": api_key,
        "mode": "driving",
        "departure_time": "now"
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        logging.error(f"Distance Matrix API returned non-200 status: {response.status_code}")
        raise RuntimeError("Failed to get a valid response from Distance Matrix API.")

    data = response.json()
    if "rows" not in data:
        logging.error("Invalid response structure from Distance Matrix API.")
        raise RuntimeError("Invalid response from Distance Matrix API.")

    time_matrix = []
    for row in data["rows"]:
        row_times = []
        for element in row["elements"]:
            if element.get('status') == 'OK':
                if 'duration_in_traffic' in element:
                    row_times.append(element['duration_in_traffic']['value'])
                else:
                    row_times.append(element['duration']['value'])
            else:
                # If not OK, this location pair is unreachable - treat as large time
                # Could also raise an error or handle differently
                row_times.append(999999)
        time_matrix.append(row_times)

    return time_matrix

def build_time_matrix(locations, api_key):
    """Build a travel time matrix using Google API with error handling."""
    if not locations:
        logging.warning("No locations provided to build_time_matrix.")
        return []

    logging.debug(f"Building time matrix for {len(locations)} locations.")
    matrix = call_distance_matrix_api(locations, api_key)
    if not matrix or len(matrix) != len(locations):
        logging.error("Time matrix dimensions are incorrect.")
        raise RuntimeError("Time matrix dimensions mismatch.")
    return matrix

def cluster_passengers(pickups, max_time_between_stops, api_key):
    """
    Cluster passengers so that no cluster requires a leg > max_time_between_stops.
    We will use hierarchical clustering on the time matrix between pickups.
    """
    if not pickups:
        logging.info("No pickups to cluster.")
        return []

    logging.info("Clustering passengers based on max_time_between_stops.")
    # Build full time matrix for pickups
    time_matrix = build_time_matrix(pickups, api_key)

    # Convert time_matrix to a condensed distance matrix required by linkage
    # Linkage requires a condensed distance vector (like from scipy.spatial.distance.squareform)
    # We'll treat time as 'distance'. We must ensure symmetry and remove diagonal.
    # Assume time_matrix is symmetric enough for this purpose.
    # If not perfectly symmetric, we can symmetrize by max or average.
    dist_mat = np.array(time_matrix)
    # In case matrix is not symmetric, symmetrize:
    dist_mat = 0.5*(dist_mat + dist_mat.T)

    # If any unreachable routes (999999), clustering might be skewed.
    # We assume data is valid as per PRD. Otherwise, we could filter them out or log an error.

    # Convert to condensed form (upper triangular without diagonal)
    # Use scipy.spatial.distance.squareform
    from scipy.spatial.distance import squareform
    condensed = squareform(dist_mat, checks=False)

    # Perform hierarchical clustering
    Z = linkage(condensed, method='complete')
    # fcluster to form clusters where no inter-cluster distance > max_time_between_stops
    clusters_labels = fcluster(Z, t=max_time_between_stops, criterion='distance')

    # Group pickups by cluster label
    clusters = {}
    for i, label in enumerate(clusters_labels):
        clusters.setdefault(label, []).append(pickups[i])

    clustered_list = list(clusters.values())
    logging.info(f"Formed {len(clustered_list)} clusters from {len(pickups)} passengers.")
    return clustered_list

def assign_passengers_to_vehicles(clusters, car_types):
    """
    Assign passengers from clusters to vehicles:
    - Flatten clusters
    - Sort vehicles by capacity and fill from largest to smallest
    """
    logging.info("Assigning passengers to vehicles.")
    passengers = [p for cluster in clusters for p in cluster]

    if not passengers:
        logging.warning("No passengers available for assignment.")
        return [], []

    car_types_sorted = sorted(car_types, key=lambda x: x['seats'], reverse=True)
    assigned_vehicles = []
    passenger_indices = list(range(len(passengers)))

    while passenger_indices:
        assigned_this_round = False
        for ctype in car_types_sorted:
            if not passenger_indices:
                break
            capacity = ctype['seats']
            vehicle_passengers = passenger_indices[:capacity]
            passenger_indices = passenger_indices[capacity:]
            assigned_vehicles.append((ctype['type'], vehicle_passengers))
            assigned_this_round = True
            if not passenger_indices:
                break

        if not assigned_this_round and passenger_indices:
            # This means we cannot assign remaining passengers due to capacity constraints.
            # According to PRD, we have an unlimited pool of vehicles of given types,
            # but if not enough capacity is defined, it's a config issue.
            logging.error("Unable to assign all passengers to vehicles with given capacities.")
            raise RuntimeError("Vehicle capacity assignment failed.")

    logging.info(f"Assigned {len(passengers)} passengers to {len(assigned_vehicles)} vehicles.")
    return assigned_vehicles, passengers

def greedy_tsp(time_matrix, start_index=0):
    """Simple greedy nearest-neighbor TSP approach."""
    n = len(time_matrix)
    unvisited = set(range(n))
    route = [start_index]
    unvisited.remove(start_index)

    while unvisited:
        current = route[-1]
        next_node = min(unvisited, key=lambda x: time_matrix[current][x])
        route.append(next_node)
        unvisited.remove(next_node)
    return route

def optimize_routes(csv_path, config_path):
    logging.info("Starting route optimization.")
    config = load_config(config_path)

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # fallback if config has it (not recommended, but just in case)
        api_key = config.get('google_api_key', None)
    if not api_key:
        logging.error("Google API key not found.")
        raise ValueError("Google API key missing in .env or config.")

    pickups = load_requests(csv_path)
    if not pickups:
        logging.info("No passengers found. Nothing to optimize.")
        return {"routes": []}

    destination = tuple(config['destination_location'])
    max_between = config['constraints']['max_time_between_stops_many2one']
    max_total = config['constraints']['max_total_route_time']

    # Cluster passengers
    clusters = cluster_passengers(pickups, max_between, api_key)

    # Assign to vehicles
    assigned_vehicles, passenger_list = assign_passengers_to_vehicles(clusters, config['car_types'])

    results = []
    # For each vehicle group of passengers
    for (vtype, p_indices) in assigned_vehicles:
        v_pickups = [passenger_list[i] for i in p_indices]
        all_points = v_pickups + [destination]

        # Build time matrix for this vehicle’s points
        vehicle_time_matrix = build_time_matrix(all_points, api_key)
        if not vehicle_time_matrix:
            logging.warning("No time matrix for this vehicle. Skipping vehicle.")
            continue

        route = greedy_tsp(vehicle_time_matrix, start_index=0)

        # Ensure destination last
        dest_index = len(all_points)-1
        if route[-1] != dest_index:
            route.remove(dest_index)
            route.append(dest_index)

        total_time = 0
        max_leg_time = 0
        for i in range(len(route)-1):
            leg = vehicle_time_matrix[route[i]][route[i+1]]
            total_time += leg
            if leg > max_leg_time:
                max_leg_time = leg

        warnings = []
        if total_time > max_total:
            warnings.append("Total route time exceeds max allowed time.")
        if max_leg_time > max_between:
            warnings.append("A leg exceeds max time between stops.")

        stops = [all_points[i] for i in route]

        results.append({
            "vehicle_type": vtype,
            "stops": stops,
            "total_travel_time": total_time,
            "max_leg_time": max_leg_time,
            "warnings": warnings
        })

    logging.info("Route optimization completed.")
    return {"routes": results}

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python optimize_many2one.py <requests.csv> <config.yaml> <output.yaml>")
        sys.exit(1)

    csv_path = sys.argv[1]
    config_path = sys.argv[2]
    output_path = sys.argv[3]

    try:
        result = optimize_routes(csv_path, config_path)
        with open(output_path, 'w') as f:
            yaml.dump(result, f)
        logging.info(f"Results saved to {output_path}")
    except Exception as e:
        logging.error(f"An error occurred during optimization: {e}")
        sys.exit(1)
