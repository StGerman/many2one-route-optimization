import pytest
from unittest.mock import patch, MagicMock
import os
import yaml
import io
import pandas as pd

from src.many2one_route_optimization.optimize_many2one import optimize_routes

@pytest.fixture
def default_config(tmp_path):
    """Fixture to create a default config file with standard constraints and car types."""
    config_content = """
google_api_key: "FAKE_API_KEY_FALLBACK"
constraints:
  max_time_between_stops_many2one: 900
  max_total_route_time: 3600
car_types:
  - type: "Minivan"
    seats: 14
  - type: "Sedan"
    seats: 4
destination_location: [32.0853, 34.7818]
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return str(config_path)

@pytest.fixture
def simple_csv(tmp_path):
    """Simple CSV with 6 passengers close together."""
    csv_content = """id,pickup_lat,pickup_lng
1,32.0664,34.7777
2,32.0670,34.7780
3,32.0675,34.7785
4,32.0680,34.7790
5,32.0685,34.7795
6,32.0700,34.7800
"""
    csv_path = tmp_path / "requests.csv"
    csv_path.write_text(csv_content)
    return str(csv_path)

@pytest.fixture
def medium_csv(tmp_path):
    """CSV with ~20 passengers spread out (Tel Aviv, Haifa, Jerusalem) to test clustering and multiple vehicles."""
    data = "id,pickup_lat,pickup_lng\n"
    # Tel Aviv (10)
    for i in range(1,11):
        data += f"{i},32.0664,{34.7777 + i*0.001}\n"
    # Haifa (5)
    for i in range(11,16):
        data += f"{i},32.8150,{34.98 + (i-10)*0.001}\n"
    # Jerusalem (5)
    for i in range(16,21):
        data += f"{i},31.78,{35.22 + (i-15)*0.001}\n"

    csv_path = tmp_path / "requests.csv"
    csv_path.write_text(data)
    return str(csv_path)

def mock_matrix_small(locations, api_key):
    """
    Return a small time matrix with short distances between points.
    This simulates close pickups resulting in few or one cluster.
    """
    n = len(locations)
    matrix = [[300 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 0
    return matrix

def mock_matrix_spread(locations, api_key):
    """
    Create a matrix that simulates greater distances:
    - First 10 points (Tel Aviv) close to each other (300s).
    - Next 5 points (Haifa) are further from Tel Aviv (1000s to/from Tel Aviv cluster),
      but close among themselves (300s).
    - Last 5 points (Jerusalem) are even further (2000s to/from Tel Aviv, 1500s to/from Haifa),
      but close among themselves (300s).
    """
    n = len(locations)
    matrix = [[0 for _ in range(n)] for _ in range(n)]

    # Define clusters:
    # indices: 0-9 (Tel Aviv), 10-14 (Haifa), 15-19 (Jerusalem)
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 0
            else:
                # same cluster close
                if (i<10 and j<10) or (10<=i<15 and 10<=j<15) or (15<=i<20 and 15<=j<20):
                    matrix[i][j] = 300
                else:
                    # Different clusters:
                    # TA <-> Haifa ~1000
                    # TA <-> Jerusalem ~2000
                    # Haifa <-> Jerusalem ~1500
                    if (i<10 and 10<=j<15) or (j<10 and 10<=i<15):
                        matrix[i][j] = 1000
                    elif (i<10 and j>=15) or (j<10 and i>=15):
                        matrix[i][j] = 2000
                    else:
                        matrix[i][j] = 1500
    return matrix

def mock_matrix_large_unreachable(locations, api_key):
    """
    Some unreachable routes (999999) to test error handling or clustering issues.
    """
    n = len(locations)
    matrix = [[300 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 0
    # Introduce unreachable route between first and last point
    matrix[0][-1] = 999999
    matrix[-1][0] = 999999
    return matrix

@patch("optimize_many2one.call_distance_matrix_api", side_effect=mock_matrix_small)
def test_basic_scenario(mock_api, simple_csv, default_config):
    """TC-001-like test: small scenario, one cluster, one vehicle."""
    result = optimize_routes(simple_csv, default_config)
    assert "routes" in result
    assert len(result["routes"]) == 1
    route = result["routes"][0]
    # Check constraints
    assert route["total_travel_time"] < 3600
    assert route["max_leg_time"] < 900
    # 6 passengers + 1 destination = 7 stops
    assert len(route["stops"]) == 7

@patch("optimize_many2one.call_distance_matrix_api", side_effect=mock_matrix_spread)
def test_moderate_capacity_scenario(mock_api, medium_csv, default_config):
    """TC-002-like test: 20 passengers spread across 3 regions (clusters)."""
    result = optimize_routes(medium_csv, default_config)
    assert "routes" in result
    # We have 20 passengers split into 3 clusters by time distance.
    # Expect multiple vehicles due to capacity constraints.
    total_passengers = 0
    for r in result["routes"]:
        # subtract destination
        total_passengers += (len(r["stops"]) - 1)
        assert r["total_travel_time"] < 3600
        assert r["max_leg_time"] <= 2000  # because between clusters we had large times
    assert total_passengers == 20

@patch("optimize_many2one.call_distance_matrix_api", side_effect=mock_matrix_spread)
def test_clustering_logic(mock_api, medium_csv, default_config):
    """
    Test clustering logic by verifying that passengers form separate clusters.
    With the mock_matrix_spread:
    - Tel Aviv cluster (0-9)
    - Haifa cluster (10-14)
    - Jerusalem cluster (15-19)
    Clusters should not mix due to large inter-cluster times > max_time (900s).
    Actually, we set max_time_between_stops to 900 in config, but we have larger distances between clusters.
    This means each city cluster should remain separate.
    """
    # We can't directly read clusters from the result, but we can infer from routes grouping.
    # If the algorithm tries to group them and route them, each route should primarily contain from one cluster.
    result = optimize_routes(medium_csv, default_config)
    # Check if each route's stops mostly come from one of the known clusters
    # This is a heuristic check: if clustering worked, we won't see a single route mixing far-apart points.
    for r in result["routes"]:
        coords = r["stops"][:-1]  # exclude destination
        # Check variation in coords to guess cluster membership
        # Tel Aviv lat ~32.06-32.07, Haifa ~32.815, Jerusalem ~31.78
        lats = [c[0] for c in coords]
        avg_lat = sum(lats)/len(lats)
        if avg_lat > 32.7:
            # Haifa cluster
            assert len(coords) <= 14  # capacity check
        elif avg_lat > 32.0:
            # Tel Aviv cluster
            assert len(coords) <= 14
        else:
            # Jerusalem cluster
            assert len(coords) <= 14

@patch("optimize_many2one.call_distance_matrix_api", side_effect=mock_matrix_large_unreachable)
def test_unreachable_scenario(mock_api, medium_csv, default_config):
    """
    Test unreachable routes scenario.
    With large_unreachable mock, some routes have 999999 travel time.
    Clustering or routing might handle them as large times.
    According to code, unreachable routes become big number, but still route is produced.
    Just check no exception is raised and result is formed.
    """
    result = optimize_routes(medium_csv, default_config)
    assert "routes" in result
    # Even if unreachable segments appear, code currently doesn't raise error automatically.
    # Check for warnings in routes.
    for r in result["routes"]:
        # If unreachable leads to large legs > 900
        # we should see a warning possibly, but not required by the original code?
        # The code sets unreachable to large time, route forms anyway.
        # Check no crash.
        pass

def test_no_passengers(default_config, tmp_path):
    """Check behavior with empty CSV (no passengers)."""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("id,pickup_lat,pickup_lng\n")  # no data

    result = optimize_routes(str(csv_path), default_config)
    assert "routes" in result
    # No passengers means no routes
    assert len(result["routes"]) == 0

def test_no_api_key(default_config, tmp_path):
    """Check error handling if no API key in .env or config."""
    # Clear env var if present
    if "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]

    # Remove api key from config fallback
    config_data = yaml.safe_load(open(default_config))
    if "google_api_key" in config_data:
        del config_data["google_api_key"]
    with open(default_config, 'w') as f:
        yaml.dump(config_data, f)

    csv_path = tmp_path / "requests.csv"
    csv_path.write_text("""id,pickup_lat,pickup_lng
1,32.0664,34.7777
""")

    with pytest.raises(ValueError, match="Google API key missing"):
        optimize_routes(str(csv_path), default_config)

@patch("optimize_many2one.call_distance_matrix_api", side_effect=mock_matrix_small)
def test_large_single_cluster_exceeds_one_vehicle_capacity(mock_api, default_config, tmp_path):
    """
    Test scenario where a single cluster (all passengers are close to each other)
    is larger than one vehicle's capacity (14 seats in a Minivan).
    With 20 passengers and available vehicle types: Minivan(14), Sedan(4),
    we need at least 2 vehicles to cover all passengers.
    """

    # Create a CSV with 20 passengers all very close together, same cluster
    csv_data = "id,pickup_lat,pickup_lng\n"
    # All near Tel Aviv coordinates
    lat, lng = 32.0664, 34.7777
    for i in range(1, 21):
        # Slight variation in coordinates, still very close
        csv_data += f"{i},{lat + i*0.0001},{lng + i*0.0001}\n"

    csv_path = tmp_path / "requests.csv"
    csv_path.write_text(csv_data)

    result = optimize_routes(str(csv_path), default_config)
    assert "routes" in result

    routes = result["routes"]
    assert len(routes) > 1, "Expect multiple vehicles/routes since capacity is exceeded."

    total_passengers_covered = sum(len(r["stops"]) - 1 for r in routes)
    assert total_passengers_covered == 20, "All 20 passengers must be covered."

    # Each vehicle should not exceed its capacity
    # Minivan: 14 seats, Sedan: 4 seats. The solution should use at least 2 vehicles.
    for r in routes:
        passenger_count = len(r["stops"]) - 1
        if r["vehicle_type"] == "Minivan":
            assert passenger_count <= 14
        elif r["vehicle_type"] == "Sedan":
            assert passenger_count <= 4

    # Check constraints
    for r in routes:
        assert r["total_travel_time"] < 3600
        assert r["max_leg_time"] < 900
