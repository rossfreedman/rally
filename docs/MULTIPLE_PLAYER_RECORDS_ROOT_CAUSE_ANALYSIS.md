# Multiple Player Records: Root Cause Analysis & Prevention

## 🔍 ROOT CAUSE ANALYSIS

### How Aaron Ended Up with Multiple Active Records

Based on our investigation, Aaron Walsh had **two active player records**:
1. **Record 757918**: team_id=56007, series_id=13368, "Chicago 18" (CORRECT)
2. **Record 756918**: team_id=55925, series_id=13584, "Series 13" (OLD)

### 📊 The Problem Chain

1. **ETL Import Process**: Creates player records with `ON CONFLICT` logic
2. **Multiple Team/Series Participation**: Aaron played in both Series 13 and Chicago 18
3. **Conflict Resolution Logic**: The ETL's conflict resolution wasn't designed for team changes
4. **UserContext Mismatch**: UserContext pointed to old team (55925) instead of new team (56007)
5. **Session Builder Priority**: Selected wrong record due to UserContext priority

## 🧩 HOW THIS HAPPENS

### 1. ETL Conflict Resolution Issue

```sql
-- Current ETL logic (problematic)
ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id) DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    team_id = EXCLUDED.team_id,
    pti = EXCLUDED.pti,
    updated_at = CURRENT_TIMESTAMP
```

**Problem**: This creates **separate records** for each `(player_id, league_id, club_id, series_id)` combination. When a player moves teams/series, it creates a NEW record instead of updating the existing one.

### 2. Team Movement Scenarios

Aaron's journey:
- **Season 1**: Registered for "Tennaqua - Series 13" → Creates Record A
- **Season 2**: Moved to "Midt-Bannockburn - Chicago 18" → Creates Record B
- **Result**: Both records remain `is_active = true`

### 3. UserContext Lag

When Aaron switched teams:
- Session was updated ✅
- Player records were created ✅  
- **UserContext was NOT updated** ❌ (still pointed to old team 55925)

### 4. Session Builder Confusion

```sql
-- Session priority logic
ORDER BY u.id, 
    (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END),  -- Both match
    (CASE WHEN p.team_id = uc.team_id THEN 1 ELSE 2 END),          -- Old team wins!
```

Since UserContext pointed to old team (55925), the session builder selected the Series 13 record.

## 🚨 PREVENTION STRATEGIES

### 1. Fix ETL Logic - Deactivate Old Records

```sql
-- Enhanced ETL logic
WITH deactivate_old AS (
    UPDATE players 
    SET is_active = false 
    WHERE tenniscores_player_id = %s 
    AND league_id = %s 
    AND (club_id != %s OR series_id != %s)
    AND is_active = true
)
INSERT INTO players (...) VALUES (...)
ON CONFLICT (...) DO UPDATE SET ...
```

### 2. Automatic UserContext Synchronization

```python
def update_user_context_after_etl():
    """Ensure UserContext points to most recent active player record"""
    query = """
        UPDATE user_contexts uc
        SET team_id = p.team_id, league_id = p.league_id
        FROM (
            SELECT DISTINCT ON (upa.user_id)
                upa.user_id,
                p.team_id,
                p.league_id
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE p.is_active = true
            ORDER BY upa.user_id, p.id DESC
        ) p
        WHERE uc.user_id = p.user_id
    """
```

### 3. Team Switch Enhancement

```python
def switch_user_team_enhanced(user_email: str, new_team_id: int):
    """Enhanced team switching with old record deactivation"""
    
    # 1. Deactivate old player records in same league
    execute_update("""
        UPDATE players 
        SET is_active = false 
        WHERE tenniscores_player_id IN (
            SELECT upa.tenniscores_player_id 
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            WHERE u.email = %s
        )
        AND league_id = %s
        AND team_id != %s
        AND is_active = true
    """, [user_email, league_id, new_team_id])
    
    # 2. Update UserContext
    # 3. Build new session
```

### 4. Registration Enhancement

```python
def register_user_enhanced(...):
    """Enhanced registration with automatic cleanup"""
    
    # Before creating association
    if player_found:
        # Deactivate old records for this player in same league
        execute_update("""
            UPDATE players 
            SET is_active = false 
            WHERE tenniscores_player_id = %s 
            AND league_id = %s 
            AND (club_id != %s OR series_id != %s)
        """, [player_id, league_id, new_club_id, new_series_id])
```

### 5. Health Check & Monitoring

```python
def detect_multiple_active_records():
    """Detect users with multiple active records in same league"""
    return execute_query("""
        SELECT 
            u.email,
            COUNT(*) as active_records,
            STRING_AGG(DISTINCT s.name, ', ') as series_list
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN series s ON p.series_id = s.id
        WHERE p.is_active = true
        GROUP BY u.email, p.league_id
        HAVING COUNT(*) > 1
    """)
```

## 🔧 IMMEDIATE FIXES NEEDED

### 1. Create Monitoring Script

```python
# scripts/monitor_multiple_active_records.py
def find_problematic_users():
    """Find all users with multiple active records"""
    # Check for multiple active records per league
    # Generate fix commands
    # Alert administrators
```

### 2. Enhance ETL Process

```python
# data/etl/database_import/enhanced_import_players.py
def import_with_deactivation():
    """Import players with automatic old record deactivation"""
    # For each player being imported:
    # 1. Check for existing active records
    # 2. Deactivate records with different club/series
    # 3. Insert/update current record
```

### 3. Fix UserContext Synchronization

```python
# app/services/session_service.py
def sync_user_context_after_import():
    """Ensure UserContext points to most recent active team"""
    # Run after ETL imports
    # Update all UserContext records to point to latest active team
```

## 📋 DEPLOYMENT CHECKLIST

- [ ] Deploy monitoring script to detect multiple active records
- [ ] Enhance ETL process to deactivate old records
- [ ] Add UserContext synchronization to ETL pipeline
- [ ] Create automated health checks
- [ ] Update team switching logic
- [ ] Add alerts for multiple active record detection

## 🎯 SUCCESS METRICS

- **Zero users with multiple active records in same league**
- **UserContext always points to correct active team**
- **Session builder selects correct player record 100% of time**
- **No "No Series Data" errors due to record confusion**

This comprehensive approach will prevent the Aaron Walsh scenario from happening again! 🛡️
