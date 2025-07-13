# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:32:24
- **Duration**: 35.24 seconds (0.59 minutes)
- **Total Users Tested**: 1
- **Total Tests Run**: 3
- **Successful Tests**: 0
- **Failed Tests**: 3
- **Success Rate**: 0.0%

## Test Configuration
- **Test Types**: registration, availability, pickup_games
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: http://localhost:8080

## Results by Test Type

### Registration Tests
- **Total Tests**: 1
- **Successful**: 0
- **Failed**: 1
- **Success Rate**: 0.0%

### Availability Tests
- **Total Tests**: 1
- **Successful**: 0
- **Failed**: 1
- **Success Rate**: 0.0%

### Pickup_Games Tests
- **Total Tests**: 1
- **Successful**: 0
- **Failed**: 1
- **Success Rate**: 0.0%

## Failed Tests Analysis

### Test failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("#club option[value]") to be visible
    2 × locator resolved to 84 elements. Proceeding with the first one: <option value="">Select your club</option>
    23 × locator resolved to 74 elements. Proceeding with the first one: <option value="">Select your club</option>

**Occurrences**: 3

**Affected Users**:
- Peter Slaven (Skokie, Chicago 3)
- Peter Slaven (Skokie, Chicago 3)
- Peter Slaven (Skokie, Chicago 3)

## Performance Metrics
- **Average Test Duration**: 11.07 seconds
- **Fastest Test**: 10.93 seconds
- **Slowest Test**: 11.28 seconds
- **Tests per Minute**: 5.1

## User Diversity
- **Unique Clubs**: 1
- **Unique Series**: 1
- **Clubs Tested**: Skokie
- **Series Tested**: Chicago 3

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 3 failed tests
- Consider performance optimizations for slow tests

## Test Data
- **Report Generated**: 2025-07-13 08:32:59
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
