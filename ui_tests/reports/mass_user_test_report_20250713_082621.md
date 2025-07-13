# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:26:17
- **Duration**: 3.94 seconds (0.07 minutes)
- **Total Users Tested**: 2
- **Total Tests Run**: 6
- **Successful Tests**: 0
- **Failed Tests**: 6
- **Success Rate**: 0.0%

## Test Configuration
- **Test Types**: registration, availability, pickup_games
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: http://localhost:5001

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

### Test failed: Page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:5001/register
Call log:
  - navigating to "http://localhost:5001/register", waiting until "load"

**Occurrences**: 6

**Affected Users**:
- Tom Guenther (Lake Bluff, Chicago 22)
- Tom Guenther (Lake Bluff, Chicago 22)
- Tom Guenther (Lake Bluff, Chicago 22)
- Adam Berman (Birchwood, Chicago 4)
- Adam Berman (Birchwood, Chicago 4)
- ... and 1 more users

## Performance Metrics
- **Average Test Duration**: 0.05 seconds
- **Fastest Test**: 0.04 seconds
- **Slowest Test**: 0.06 seconds
- **Tests per Minute**: 91.4

## User Diversity
- **Unique Clubs**: 2
- **Unique Series**: 2
- **Clubs Tested**: Birchwood, Lake Bluff
- **Series Tested**: Chicago 22, Chicago 4

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 6 failed tests

## Test Data
- **Report Generated**: 2025-07-13 08:26:21
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
