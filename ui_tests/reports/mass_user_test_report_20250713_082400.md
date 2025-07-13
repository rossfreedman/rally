# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:23:50
- **Duration**: 9.81 seconds (0.16 minutes)
- **Total Users Tested**: 5
- **Total Tests Run**: 15
- **Successful Tests**: 0
- **Failed Tests**: 15
- **Success Rate**: 0.0%

## Test Configuration
- **Test Types**: registration, availability, pickup_games
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: http://localhost:5001

## Results by Test Type

### Registration Tests
- **Total Tests**: 5
- **Successful**: 0
- **Failed**: 5
- **Success Rate**: 0.0%

### Availability Tests
- **Total Tests**: 5
- **Successful**: 0
- **Failed**: 5
- **Success Rate**: 0.0%

### Pickup_Games Tests
- **Total Tests**: 5
- **Successful**: 0
- **Failed**: 5
- **Success Rate**: 0.0%

## Failed Tests Analysis

### Test failed: Page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:5001/register
Call log:
  - navigating to "http://localhost:5001/register", waiting until "load"

**Occurrences**: 15

**Affected Users**:
- Dave Groose (Valley Lo, Chicago 25)
- Dave Groose (Valley Lo, Chicago 25)
- Dave Groose (Valley Lo, Chicago 25)
- Glen Nixon (Salt Creek, Chicago 29 SW)
- Glen Nixon (Salt Creek, Chicago 29 SW)
- ... and 10 more users

## Performance Metrics
- **Average Test Duration**: 0.06 seconds
- **Fastest Test**: 0.04 seconds
- **Slowest Test**: 0.16 seconds
- **Tests per Minute**: 91.8

## User Diversity
- **Unique Clubs**: 5
- **Unique Series**: 5
- **Clubs Tested**: Lifesport-Lshire, North Shore, Salt Creek, Sunset Ridge, Valley Lo
- **Series Tested**: Chicago 25, Chicago 29 SW, Chicago 30, Chicago 33, Chicago 38

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 15 failed tests

## Test Data
- **Report Generated**: 2025-07-13 08:24:00
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
