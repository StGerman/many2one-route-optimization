# Software Test Plan (STP) - Many-to-One Route Optimization

## 1. Introduction

This document outlines the strategy, approach, and test cases for verifying the functional correctness and route quality of the Many-to-One Route Optimization script. The script processes passenger pickup requests, leverages mocked travel time data from the Google Distance Matrix/Directions API, applies clustering and optimization heuristics, and outputs optimized routes that minimize total travel time (primary) and vehicle usage (secondary).

**Objectives**:
- Ensure the script produces logically correct and time-efficient routes for a variety of input sizes and geographic distributions.
- Validate that key constraints (max time between stops, max total route time, and vehicle capacity) are respected.
- Test only within a local/dev environment, using mocked data, and focusing strictly on functional correctness and route quality.

## 2. Scope

**In Scope**:
- Functional correctness of the end-to-end workflow:
  - Reading input CSV.
  - Clustering and heuristic optimization.
  - Assigning passengers to vehicles.
  - Producing routes that meet constraints using mocked API responses.

**Out of Scope**:
- Handling invalid or unreachable input data.
- Error logging and performance testing.
- Live API requests.

## 3. Test Items

- **CSV Input Processing**: Ensure correct parsing of passenger data.
- **Clustering & Optimization**: Validate logical grouping of pickups and quality of route solutions.
- **Vehicle Assignment & Capacity Handling**: Confirm correct use of vehicle capacities and minimal vehicle count.
- **Mocked API Integration**: Verify stable, predictable route computation from mocked travel times.

## 4. Test Approach

- Focus on end-to-end tests with functional correctness as the priority.
- Use pytest for automation.
- Test with a range of passenger counts (from 5–10 up to ~100) and different geographic distributions (urban concentration vs. dispersed across Israel).
- All travel times come from mocked responses to ensure repeatability and stability.

**Key Scenarios**:
1. Small sets of passengers to ensure basic correctness.
2. Moderate sets to test multiple vehicles and capacity logic.
3. Larger sets to ensure scalability and consistency.
4. Geographic variations to test clustering logic and route quality.

## 5. Test Environment

- Local environment with Python `^3.11` and Poetry.
- No external dependencies beyond mocked responses.
- Standard development machine.

## 6. Test Deliverables

- Combined STP and Test Cases in this document.
- Automated test scripts (pytest) referencing these scenarios.
- Test result summaries after execution.

## 7. Responsibilities

- **QA Engineer**: Create, run, and maintain test cases. Interpret results.
- **Developers**: Address any defects discovered.

## 8. Schedule

- Test case development after finalizing requirements.
- Test execution incrementally as features are integrated.
- Regression tests run after fixes or enhancements.

## 9. Tools

- **Pytest**: Test framework.
- **Mocking Libraries**: For stable, controlled API responses.
- **Version Control (GitHub)**: For test code and data versioning.

## 10. Risks & Contingencies

- Mocked responses may not represent every real-world nuance, but this is acceptable for functional correctness tests.

## 11. Approval

The STP and test cases will be reviewed by QA and Development leads before execution.

---

## 12. Test Cases

### TC-001: Basic Scenario (5–10 Passengers)
**Description**: Verify route correctness with a small number of passengers and a single vehicle capable of carrying all.
**Prerequisites**:
- Config: one car type (e.g., Minivan with 6 seats).
- CSV: 6 passengers close to each other and destination in Tel Aviv.
- Mocked API responses provide short travel times.

**Steps**:
1. Run the script with the CSV and config.
2. Verify a single route is produced with all passengers and one vehicle.

**Expected Results**:
- One route covering all pickups, ending at destination.
- Total travel time < 3600s, each leg < 900s.
- Route is logically efficient (no unnecessary long legs).

---

### TC-002: Moderate Capacity Scenario (20–30 Passengers)
**Description**: Multiple vehicles required; test capacity handling and route distribution.
**Prerequisites**:
- Config: multiple car types (Minivan: 6 seats, Sedan: 4 seats).
- CSV: ~25 passengers spread across Tel Aviv, Haifa, Jerusalem.
- Mocked API responses reflect realistic travel times between cities.

**Steps**:
1. Run the script.
2. Check that passengers are grouped into clusters and assigned to vehicles efficiently.

**Expected Results**:
- Multiple vehicles used, starting with largest capacity first.
- All constraints met: no time violation, capacity respected.
- Routes appear logically grouped by region, minimizing travel time.

---

### TC-003: Larger Input Scenario (50–150 Passengers)
**Description**: Validate performance and quality with ~100 passengers.
**Prerequisites**:
- Config: same constraints, multiple car types.
- CSV: ~100 passengers spread widely across Israel.
- Mocked API responses scaled for large input.

**Steps**:
1. Run the script with larger CSV.
2. Ensure it completes successfully and forms coherent clusters.

**Expected Results**:
- A set of routes covering all passengers.
- Respect for max times and capacities.
- Routes are still logical and not obviously inefficient.

---

### TC-004: Geographic Variation - Urban Concentration
**Description**: All passengers close together (e.g., 10 in downtown Tel Aviv).
**Prerequisites**:
- Config: standard constraints.
- CSV: 10 passengers within a small radius in Tel Aviv.
- Mocked API responses very short travel times.

**Steps**:
1. Run the script.
2. Expect minimal complexity and short travel times.

**Expected Results**:
- Possibly a single vehicle route.
- Very low total travel time.
- Easily meets all constraints due to proximity.

---

### TC-005: Geographic Variation - Spread Across Israel
**Description**: Passengers grouped by city regions (Haifa, Tel Aviv, Jerusalem).
**Prerequisites**:
- Config: multiple vehicle types.
- CSV: 30 passengers (10 per city).
- Mocked API times reflect realistic driving between cities.

**Steps**:
1. Run the script.
2. Expect multiple clusters formed by geography.

**Expected Results**:
- Clusters per city or region.
- Routes comply with constraints.
- Logical city-based grouping shows route quality.

---

### TC-006: Vehicle Capacity Edge Cases
**Description**: Test exact, under, and over capacity scenarios.
**Prerequisites**:
- Config: one car type (Minivan with 6 seats).
- Three separate CSVs:
  - A: 6 passengers (exact capacity)
  - B: 4 passengers (under capacity)
  - C: 8 passengers (over capacity)

**Steps**:
1. Run with CSV A: Expect exactly one vehicle.
2. Run with CSV B: One vehicle with spare capacity.
3. Run with CSV C: At least two vehicles.

**Expected Results**:
- A: One route, no spare vehicle needed.
- B: One route, under capacity, still valid.
- C: Multiple routes due to capacity limit, all constraints met.

---

**Note**: Output format verification is not required. Focus remains on correctness, constraint adherence, and logical route efficiency.

---
