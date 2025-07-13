# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:30:31
- **Duration**: 95.01 seconds (1.58 minutes)
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

### Test failed: Page.select_option: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#series")
    - locator resolved to <select id="series" required="" class="form-control">…</select>
  - attempting select option action
    2 × waiting for element to be visible and enabled
      - did not find some options
    - retrying select option action
    - waiting 20ms
    2 × waiting for element to be visible and enabled
      - did not find some options
    - retrying select option action
      - waiting 100ms
    60 × waiting for element to be visible and enabled
       - did not find some options
     - retrying select option action
       - waiting 500ms

**Occurrences**: 3

**Affected Users**:
- Sam Shapiro (River Forest PD, Chicago 7 SW)
- Sam Shapiro (River Forest PD, Chicago 7 SW)
- Sam Shapiro (River Forest PD, Chicago 7 SW)

## Performance Metrics
- **Average Test Duration**: 31.00 seconds
- **Fastest Test**: 30.96 seconds
- **Slowest Test**: 31.02 seconds
- **Tests per Minute**: 1.9

## User Diversity
- **Unique Clubs**: 1
- **Unique Series**: 1
- **Clubs Tested**: River Forest PD
- **Series Tested**: Chicago 7 SW

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 3 failed tests
- Consider performance optimizations for slow tests

## Test Data
- **Report Generated**: 2025-07-13 08:32:06
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
