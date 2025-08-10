# CNSWPL Data Integrity Solution
**Comprehensive Fix for Duplicate Prevention & Match Linking Issues**

**Date**: January 16, 2025  
**Status**: 🔧 IN PROGRESS  
**Priority**: HIGH

## 🎯 **Problems Identified**

### **1. Duplicate Player Records**
- **Issue**: Import process created duplicate players (23 cleaned up)
- **Impact**: Constraint violations, data inconsistency
- **Root Cause**: No duplicate prevention in ETL process

### **2. Missing Match Data for Players** 
- **Issue**: Lisa Wagner (and other CNSWPL players) show no stats/matches in UI
- **Impact**: Users see empty analyze-me pages despite having played matches
- **Root Cause**: CNSWPL matches have 92.7% NULL player IDs vs 0.6% for APTA

## 🔧 **Solutions Implemented**

### **1. Duplicate Prevention System** ✅ **COMPLETED**

**Location**: `data/etl/database_import/duplicate_prevention_service.py`

**Features**:
- **Upsert-based imports**: UPDATE existing, INSERT new
- **Pre-import duplicate detection**: Scans for conflicts before import
- **Constraint enforcement**: Unique constraints at database level
- **Automatic cleanup**: Removes existing duplicates intelligently
- **Monitoring & reporting**: Tracks prevention metrics

**Usage**:
```python
# Enhanced import with duplicate prevention
from duplicate_prevention_service import DuplicatePreventionService

service = DuplicatePreventionService()
service.create_upsert_constraints()  # Ensure DB constraints
results = service.perform_upsert_import(players_data)  # Upsert import
cleanup = service.cleanup_existing_duplicates('CNSWPL')  # Clean existing
```

### **2. Match Player ID Linking Fix** 🔧 **IN PROGRESS**

**Issue Analysis**:
```
League Player ID Coverage:
- APTA_CHICAGO: 99.4% (17,595/17,698) ✅
- CNSWPL: 7.3% (142/1,958) ❌ 
- NSTF: 87.3% (247/283) ⚠️
```

**Root Causes**:
1. **Player Name Matching Failures**: CNSWPL match import can't resolve player names to IDs
2. **Format Mismatches**: Player names in matches don't match player records exactly
3. **Missing Fallback Logic**: No fuzzy matching for name variations

## 🚀 **Implementation Plan**

### **Phase 1: Immediate Fix - Player ID Backfill** 

**Script**: `scripts/fix_cnswpl_match_player_ids.py`

```python
#!/usr/bin/env python3
"""
Fix CNSWPL Match Player ID Linking
==================================

Backfill NULL player IDs in CNSWPL match records by matching 
player names to existing player records with fuzzy matching.
"""

def fix_cnswpl_player_ids():
    # 1. Get all CNSWPL matches with NULL player IDs
    null_matches = get_cnswpl_matches_with_null_players()
    
    # 2. Build player name → ID mapping with variations
    player_mapping = build_cnswpl_player_mapping()
    
    # 3. Parse match data to extract player names
    for match in null_matches:
        players = extract_player_names_from_match(match)
        
        # 4. Match names to player IDs using fuzzy logic
        player_ids = match_names_to_ids(players, player_mapping)
        
        # 5. Update match record with resolved player IDs
        update_match_player_ids(match['id'], player_ids)

def build_cnswpl_player_mapping():
    """Build comprehensive name → ID mapping with variations"""
    
    players = get_cnswpl_players()
    mapping = {}
    
    for player in players:
        # Primary name
        full_name = f"{player['first_name']} {player['last_name']}"
        mapping[full_name.lower()] = player['tenniscores_player_id']
        
        # Common variations
        mapping[f"{player['first_name'][0]}. {player['last_name']}".lower()] = player['tenniscores_player_id']
        mapping[f"{player['last_name']}, {player['first_name']}".lower()] = player['tenniscores_player_id']
        
        # Handle nicknames and variations using existing NAME_VARIATIONS
        for variation in get_name_variations(player['first_name']):
            alt_name = f"{variation} {player['last_name']}"
            mapping[alt_name.lower()] = player['tenniscores_player_id']
    
    return mapping
```

### **Phase 2: Enhanced Match Import Process**

**Location**: `data/etl/scrapers/scrape_match_scores.py`

**Enhancements**:
1. **Real-time Player ID Resolution**: Resolve player IDs during scraping
2. **Fuzzy Name Matching**: Handle name variations automatically  
3. **Player Database Integration**: Query player records during import
4. **Fallback Strategies**: Multiple matching approaches

```python
def enhanced_player_id_resolution(self, player_name: str, team_name: str) -> Optional[str]:
    """Resolve player name to ID with multiple strategies"""
    
    # Strategy 1: Exact match
    player_id = self.exact_name_match(player_name)
    if player_id:
        return player_id
    
    # Strategy 2: Fuzzy match with team context
    player_id = self.fuzzy_match_with_team(player_name, team_name)
    if player_id:
        return player_id
    
    # Strategy 3: Name variations (nicknames, initials)
    player_id = self.name_variation_match(player_name)
    if player_id:
        return player_id
    
    # Strategy 4: Partial match (last name + first initial)
    player_id = self.partial_name_match(player_name)
    if player_id:
        return player_id
    
    # Log unresolved for manual review
    self.log_unresolved_player(player_name, team_name)
    return None
```

### **Phase 3: Validation & Monitoring**

**Health Monitoring**: `scripts/monitor_cnswpl_health.py`

**Match Linking Metrics**:
- Player ID coverage percentage by league
- Unresolved player name tracking
- Match data completeness scoring
- Performance impact analysis

## 📋 **Execution Steps**

### **Immediate Actions (Today)**

1. **✅ Create backfill script** for CNSWPL match player IDs
2. **🔧 Run backfill** on existing 1,958 CNSWPL matches  
3. **✅ Test Lisa Wagner** data display in UI
4. **📊 Validate** player ID coverage improvement

### **Short-term (Next ETL Run)**

1. **🔧 Enhance match scraper** with player ID resolution
2. **🧪 Test new scraper** on sample CNSWPL data
3. **📈 Monitor** new match imports for player ID coverage
4. **🚨 Alert** on low coverage rates

### **Long-term (Future Seasons)**

1. **🏗️ Integrate** duplicate prevention into all ETL workflows
2. **📊 Establish** monitoring dashboards for data quality
3. **🔄 Automate** health checks in ETL pipeline
4. **📚 Document** troubleshooting procedures

## 🎯 **Success Metrics**

### **Target Objectives**

- **✅ Zero Duplicates**: No duplicate player records in future imports
- **🎯 95%+ Player ID Coverage**: CNSWPL matches should reach APTA levels
- **✅ Complete UI Data**: All registered players see their match history
- **📈 Monitoring**: Real-time health metrics and alerting

### **Validation Tests**

1. **Lisa Wagner Test**: Verify she sees match data in analyze-me page
2. **Duplicate Prevention**: Run import twice, confirm no duplicates created  
3. **Player ID Coverage**: Measure improvement from 7.3% to 95%+
4. **Performance Impact**: Ensure solutions don't slow ETL process

## 🚨 **Risk Mitigation**

### **Backup Strategy**
- **Database backup** before running backfill scripts
- **Rollback procedures** for failed player ID updates
- **Validation checks** before committing changes

### **Monitoring**
- **Real-time alerts** for data quality degradation
- **Weekly health reports** on CNSWPL data integrity
- **User feedback** integration for unreported issues

---

## 📞 **Next Steps**

1. **Create and run backfill script** to fix existing matches
2. **Test Lisa Wagner's data** in analyze-me page  
3. **Enhance match scraper** for future imports
4. **Implement monitoring** for ongoing health

**This comprehensive solution ensures robust data integrity for current and future CNSWPL data! 🚀**
