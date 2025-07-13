# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-12 20:57:47
- **Duration**: 10.68 seconds (0.18 minutes)
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
- Mike Stomberg (Chicago Highlands, Chicago 17 SW)
- Mike Stomberg (Chicago Highlands, Chicago 17 SW)
- Mike Stomberg (Chicago Highlands, Chicago 17 SW)
- Jeremy Johnson (Ruth Lake, Chicago 25 SW)
- Jeremy Johnson (Ruth Lake, Chicago 25 SW)
- ... and 10 more users

## Performance Metrics
- **Average Test Duration**: 0.05 seconds
- **Fastest Test**: 0.03 seconds
- **Slowest Test**: 0.12 seconds
- **Tests per Minute**: 84.2

## User Diversity
- **Unique Clubs**: 5
- **Unique Series**: 5
- **Clubs Tested**: Chicago Highlands, Knollwood, Ruth Lake, Skokie, Sunset Ridge
- **Series Tested**: Chicago 12, Chicago 17 SW, Chicago 24, Chicago 25 SW, Chicago 33

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 15 failed tests

## Test Data
- **Report Generated**: 2025-07-12 20:57:57
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
