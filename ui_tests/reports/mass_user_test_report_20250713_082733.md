# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: 2025-07-13 08:24:29
- **Duration**: 183.40 seconds (3.06 minutes)
- **Total Users Tested**: 100
- **Total Tests Run**: 300
- **Successful Tests**: 0
- **Failed Tests**: 300
- **Success Rate**: 0.0%

## Test Configuration
- **Test Types**: registration, availability, pickup_games
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: http://localhost:5001

## Results by Test Type

### Registration Tests
- **Total Tests**: 100
- **Successful**: 0
- **Failed**: 100
- **Success Rate**: 0.0%

### Availability Tests
- **Total Tests**: 100
- **Successful**: 0
- **Failed**: 100
- **Success Rate**: 0.0%

### Pickup_Games Tests
- **Total Tests**: 100
- **Successful**: 0
- **Failed**: 100
- **Success Rate**: 0.0%

## Failed Tests Analysis

### Test failed: Page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:5001/register
Call log:
  - navigating to "http://localhost:5001/register", waiting until "load"

**Occurrences**: 300

**Affected Users**:
- Brent Hashiguchi (Winnetka II, Chicago 5)
- Brent Hashiguchi (Winnetka II, Chicago 5)
- Brent Hashiguchi (Winnetka II, Chicago 5)
- Aaron Wiltshire (Winnetka, Chicago 21)
- Aaron Wiltshire (Winnetka, Chicago 21)
- ... and 295 more users

## Performance Metrics
- **Average Test Duration**: 0.05 seconds
- **Fastest Test**: 0.03 seconds
- **Slowest Test**: 0.09 seconds
- **Tests per Minute**: 98.1

## User Diversity
- **Unique Clubs**: 48
- **Unique Series**: 44
- **Clubs Tested**: Biltmore CC, Birchwood, Briarwood, Bryn Mawr, Evanston, Exmoor, Glen Ellyn, Glen Oak I, Glen Oak II, Glen View, Glenbrook RC, Hinsdale GC, Hinsdale PC, Hinsdale PC I, Hinsdale PC II, Indian Hill, Inverness, Knollwood, LaGrange CC, Lake Bluff, Michigan Shores, Midt-Bannockburn, Midtown, North Shore, Northmoor, Oak Park CC, Oak Park CC I, Oak Park CC II, Onwentsia, Prairie Club, Prairie Club I, Prairie Club II, Royal Melbourne, Ruth Lake, Saddle & Cycle, Salt Creek, Skokie, Sunset Ridge, Tennaqua, Valley Lo, Westmoreland, Wilmette PD, Wilmette PD I, Wilmette PD II, Winnetka, Winnetka I, Winnetka II, Winter Club
- **Series Tested**: Chicago 10, Chicago 12, Chicago 13, Chicago 13 SW, Chicago 14, Chicago 15, Chicago 16, Chicago 17, Chicago 17 SW, Chicago 18, Chicago 19, Chicago 19 SW, Chicago 2, Chicago 20, Chicago 21, Chicago 21 SW, Chicago 22, Chicago 23, Chicago 25, Chicago 26, Chicago 27, Chicago 27 SW, Chicago 28, Chicago 29, Chicago 29 SW, Chicago 3, Chicago 30, Chicago 31, Chicago 32, Chicago 33, Chicago 34, Chicago 35, Chicago 36, Chicago 37, Chicago 38, Chicago 39, Chicago 4, Chicago 5, Chicago 6, Chicago 7, Chicago 8, Chicago 9, Chicago 9 SW, Chicago Chicago

## Recommendations

❌ **Needs Attention**: Significant issues detected that require immediate attention.
- Investigate and fix the 300 failed tests

## Test Data
- **Report Generated**: 2025-07-13 08:27:33
- **Test Runner**: MassUserTestRunner v1.0
- **Environment**: local
