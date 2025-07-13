# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:26:00
- **Duration**: 5.68 seconds (0.09 minutes)
- **Total Users Tested**: 3
- **Total Tests Run**: 9
- **Successful Tests**: 0
- **Failed Tests**: 9
- **Success Rate**: 0.0%

## Test Configuration
- **Test Types**: registration, availability, pickup_games
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: http://localhost:5001

## Results by Test Type

### Registration Tests
- **Total Tests**: 3
- **Successful**: 0
- **Failed**: 3
- **Success Rate**: 0.0%

### Availability Tests
- **Total Tests**: 3
- **Successful**: 0
- **Failed**: 3
- **Success Rate**: 0.0%

### Pickup_Games Tests
- **Total Tests**: 3
- **Successful**: 0
- **Failed**: 3
- **Success Rate**: 0.0%

## Failed Tests Analysis

### Test failed: Page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:5001/register
Call log:
  - navigating to "http://localhost:5001/register", waiting until "load"

**Occurrences**: 9

**Affected Users**:
- Don Ensing (Butterfield, Chicago 19 SW)
- Don Ensing (Butterfield, Chicago 19 SW)
- Don Ensing (Butterfield, Chicago 19 SW)
- Barry Metzger (Briarwood, Chicago 28)
- Barry Metzger (Briarwood, Chicago 28)
- ... and 4 more users

## Performance Metrics
- **Average Test Duration**: 0.04 seconds
- **Fastest Test**: 0.03 seconds
- **Slowest Test**: 0.06 seconds
- **Tests per Minute**: 95.1

## User Diversity
- **Unique Clubs**: 3
- **Unique Series**: 3
- **Clubs Tested**: Briarwood, Butterfield, Michigan Shores
- **Series Tested**: Chicago 12, Chicago 19 SW, Chicago 28

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 9 failed tests

## Test Data
- **Report Generated**: 2025-07-13 08:26:06
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
