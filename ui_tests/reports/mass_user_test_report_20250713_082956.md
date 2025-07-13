# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:26:46
- **Duration**: 189.64 seconds (3.16 minutes)
- **Total Users Tested**: 2
- **Total Tests Run**: 6
- **Successful Tests**: 0
- **Failed Tests**: 6
- **Success Rate**: 0.0%

## Test Configuration
- **Test Types**: registration, availability, pickup_games
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: http://localhost:8080

## Results by Test Type

### Registration Tests
- **Total Tests**: 2
- **Successful**: 0
- **Failed**: 2
- **Success Rate**: 0.0%

### Availability Tests
- **Total Tests**: 2
- **Successful**: 0
- **Failed**: 2
- **Success Rate**: 0.0%

### Pickup_Games Tests
- **Total Tests**: 2
- **Successful**: 0
- **Failed**: 2
- **Success Rate**: 0.0%

## Failed Tests Analysis

### Test failed: Page.fill: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("input[name=\"first_name\"]")

**Occurrences**: 6

**Affected Users**:
- Brent Clark (Michigan Shores, Chicago 26)
- Brent Clark (Michigan Shores, Chicago 26)
- Brent Clark (Michigan Shores, Chicago 26)
- Sam Vlahos (Chicago Highlands, Chicago 27 SW)
- Sam Vlahos (Chicago Highlands, Chicago 27 SW)
- ... and 1 more users

## Performance Metrics
- **Average Test Duration**: 30.97 seconds
- **Fastest Test**: 30.83 seconds
- **Slowest Test**: 31.16 seconds
- **Tests per Minute**: 1.9

## User Diversity
- **Unique Clubs**: 2
- **Unique Series**: 2
- **Clubs Tested**: Chicago Highlands, Michigan Shores
- **Series Tested**: Chicago 26, Chicago 27 SW

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 6 failed tests
- Consider performance optimizations for slow tests

## Test Data
- **Report Generated**: 2025-07-13 08:29:56
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
