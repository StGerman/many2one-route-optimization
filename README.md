# Many-to-One Route Optimization

This project provides a Many-to-One Route Optimization solution using the Google Distance Matrix API. It reads a list of passenger pickups and a single destination from a CSV file, applies clustering and heuristic optimization to determine efficient routes that minimize total travel time and vehicle usage, and outputs the resulting routes as a YAML file.

## Features

- **Google Distance Matrix API Integration**: Retrieves travel times between coordinates.
- **Agglomerative Clustering**: Groups passengers into clusters where intra-cluster travel times do not exceed the allowed maximum.
- **Heuristic Optimization**: Assigns passengers to vehicles and computes routes that minimize total travel time within given constraints.
- **Capacity and Time Constraints**: Respects maximum vehicle capacity, maximum time between stops, and total route time.
- **Logging and Error Handling**: Provides detailed logs and robust error handling for easier debugging.
- **Configuration-Driven**: Configurable via a YAML file for constraints, vehicle types, and destination. API keys are stored in `.env`.

## Requirements

- Python ^3.11
- [Poetry](https://python-poetry.org/) for dependency and environment management.
- A valid Google Distance Matrix API key with appropriate billing set up.
- `.env` file containing `GOOGLE_API_KEY=YOUR_KEY`

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/many2one-route-optimization.git
   cd many2one-route-optimization
   ```

2. **Set Up Environment**:
   Make sure you have Poetry installed, then:
   ```bash
   poetry install
   ```

3. **Configure API Key**:
   Create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=YOUR_ACTUAL_API_KEY
   ```

4. **Prepare Configuration**:
   Edit `config.yaml` as needed for constraints, vehicle types, and destination.

## Usage

### Input Files

- **CSV (requests.csv)**: Should contain columns `id`, `pickup_lat`, `pickup_lng`.
- **config.yaml**: Defines constraints (`max_time_between_stops_many2one`, `max_total_route_time`), `car_types` (with `seats`), and `destination_location`.

Example `config.yaml`:

```yaml
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
```

### Running the Script

Use Poetry to run the optimization:

```bash
poetry run python optimize_many2one.py requests.csv config.yaml output.yaml
```

- `requests.csv`: Input file containing passenger pickup points.
- `config.yaml`: Configuration file with constraints, vehicle data, and destination.
- `output.yaml`: File where the result will be written.

The script will generate a YAML output with routes, including assigned vehicle types, stops with coordinates, total travel time, max leg time, and any warnings.

## Testing

We use `pytest` for testing. Tests mock the Distance Matrix API and verify functional correctness, clustering logic, capacity constraints, and error handling.

To run tests:
```bash
poetry run pytest
```

## Logging

Logs provide information about each step (clustering, vehicle assignment, route optimization). Check `INFO` and `DEBUG` logs for details. If needed, adjust the logging level in `optimize_many2one.py`.

## Troubleshooting

- Ensure `.env` is present with a valid `GOOGLE_API_KEY`.
- Check that `requests.csv` and `config.yaml` are properly formatted.
- Verify that all dependencies are installed via Poetry.
- If encountering issues with the Distance Matrix API, ensure your API key is valid, enabled for the appropriate API, and that billing is configured.

## License

This project is released under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please open issues or pull requests on the [GitHub repository](https://github.com/yourusername/many2one-route-optimization).
