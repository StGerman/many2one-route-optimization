# Product Requirements Document (PRD)

## Overview
This document outlines the requirements, objectives, and functionality for a Many-to-One route optimization script. The script processes passenger pickup requests, uses configuration parameters, retrieves travel time data from the Google Distance Matrix/Directions API, and produces optimized vehicle route assignments.

## Goals
- **Primary Objective**: Minimize total travel time for servicing all passenger pickups and delivering them to a single known destination.
- **Secondary Objective**: Minimize the number of vehicles used, given an unlimited pool of predefined car types.

## Key Features and Requirements

### Input
- **Data Format**: CSV file
- **CSV Fields**:
  - `id`
  - `pickup_lat`
  - `pickup_lng`
- **Consistency**: Field names and structure are fixed and do not change.

### Configuration
- **Format**: YAML file
- **Content**:
  - **API Keys**: Google Distance Matrix/Directions API key
  - **Constraints**:
    - Max time between stops (in seconds)
    - Max total route time (in seconds)
    - Vehicle capacity constraints (in terms of number of passengers)
  - **Car Types**: A predefined, fixed list of car types with their seat capacities.
  - **Destination Location**: Latitude/longitude coordinates of the final drop-off point.

### Routing and Optimization
- **Routing Provider**: Google Distance Matrix/Directions API
- **Approach**: Heuristic-based
  - Perform clustering of passengers (e.g., agglomerative clustering) to group nearby pickups.
  - Assign passengers to vehicles using a bin-packing-like strategy, starting with the largest capacity vehicles, to reduce the number of vehicles.
  - For each vehicle’s assigned cluster of passengers, perform route optimization (e.g., a greedy approach) to minimize travel time.
- **Objectives**:
  - **Primary**: Minimize total travel time.
  - **Secondary**: Minimize the number of vehicles.

### Constraints
- **Max Time Between Stops**: No pair of consecutive stops should exceed this time.
- **Max Total Route Time**: The entire route’s total travel time must not exceed this limit.
- **Vehicle Capacity**: Do not exceed the seat capacity of the assigned vehicle.

### Output
- **Final Output Format**: YAML file
- **Final Output Content**:
  - Assigned vehicle type for each route
  - Total travel time for each route
  - Any warnings (e.g., constraint violations)
- **Intermediate Outputs**:
  - Clusters formed
  - Time matrices generated
- These intermediate results should be available for debugging and auditing, either as separate YAML files or logged artifacts.

### Execution Environment
- **Local Execution**: The script runs on a local machine.
- **No Special Resource Handling**: No need for streaming data or handling extremely large datasets.
- **Logging and Monitoring**:
  - Implement logging to track intermediate steps (e.g., cluster formation, time matrix creation).
  - Log warnings and errors (e.g., invalid input data, API failures).

### Error Handling and Validation
- **Invalid Data**: Skip invalid passenger entries. Log warnings or errors.
- **Unreachable Locations or API Failures**:
  - Skip problematic passengers.
  - Log these events with appropriate error messages.
- **Non-Blocking Errors**: Do not stop the entire process if some data points fail.

### Maintainability and Extensibility
- **Simplicity Priority**: Keep the code structure straightforward and easily understandable.
- **Documentation**: Provide a `README.md` in the GitHub repository with instructions on:
  - How to install dependencies
  - How to run the script
  - Configuration details (YAML structure)
  - Interpreting output files

## Success Criteria
- **Functional Completeness**: The script should successfully:
  1. Read the CSV input.
  2. Apply constraints and cluster assignments.
  3. Retrieve travel times from the Google API.
  4. Produce a route plan that respects constraints.
- **Performance**: Handle a typical number of passengers (tens to low hundreds) efficiently on a local machine.
- **Reliability**: Log and handle errors gracefully, without crashing.
- **Clarity**: The output YAML should clearly communicate results, and the `README.md` should guide users through the entire process.

## Versioning and Future Improvements
- Initial version focuses on heuristics and basic clustering.
- Future iterations could integrate more sophisticated optimization techniques or add GUI/visualization support.

---
