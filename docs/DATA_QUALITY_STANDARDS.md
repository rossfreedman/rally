# Data Quality Standards

## Overview

This document establishes comprehensive data quality standards for the Rally platform to prevent data integrity issues and ensure reliable system operation.

## 🎯 **Core Principles**

### **1. Data Integrity**
- All data must be consistent and accurate
- Foreign key relationships must be maintained
- No orphaned records should exist
- Data should be validated before and after import

### **2. Completeness**
- All required fields must be populated
- No critical data should be missing
- Coverage should be >95% for all data types
- Missing data should be logged and reported

### **3. Consistency**
- Data formats should be standardized
- Naming conventions should be consistent
- Date/time formats should be uniform
- Team names should follow established patterns

### **4. Accuracy**
- Data should match source systems
- Calculations should be mathematically correct
- Relationships should be logically sound
- No duplicate records should exist

## 📊 **Schedule Data Standards**

### **Required Fields**
- `match_date`: Valid date in YYYY-MM-DD format
- `home_team`: Non-empty string
- `away_team`: Non-empty string
- `league_id`: Valid foreign key reference
- `home_team_id`: Valid team ID or NULL
- `away_team_id`: Valid team ID or NULL

### **Quality Metrics**
- **Coverage**: >95% of teams should have schedule data
- **NULL team_id**: <1% of records should have NULL team_id
- **Duplicates**: 0 duplicate schedule records
- **Orphaned records**: 0 orphaned schedule records

### **Validation Rules**
```sql
-- No duplicate schedule records
SELECT COUNT(*) FROM (
    SELECT match_date, home_team, away_team, league_id, COUNT(*)
    FROM schedule 
    GROUP BY match_date, home_team, away_team, league_id 
    HAVING COUNT(*) > 1
) duplicates;

-- No NULL team_id records
SELECT COUNT(*) FROM schedule 
WHERE home_team_id IS NULL AND away_team_id IS NULL;

-- No orphaned records
SELECT COUNT(*) FROM schedule s
LEFT JOIN teams t1 ON s.home_team_id = t1.id
LEFT JOIN teams t2 ON s.away_team_id = t2.id
WHERE (s.home_team_id IS NOT NULL AND t1.id IS NULL)
   OR (s.away_team_id IS NOT NULL AND t2.id IS NULL);
```

## 🏆 **Team Data Standards**

### **Required Fields**
- `team_name`: Non-empty string
- `club_id`: Valid foreign key reference
- `series_id`: Valid foreign key reference
- `league_id`: Valid foreign key reference

### **Quality Metrics**
- **Naming consistency**: Team names should follow established patterns
- **Reference integrity**: All foreign keys should be valid
- **Coverage**: All teams should have associated schedule data

### **Validation Rules**
```sql
-- All teams should have valid references
SELECT COUNT(*) FROM teams t
LEFT JOIN clubs c ON t.club_id = c.id
LEFT JOIN series s ON t.series_id = s.id
LEFT JOIN leagues l ON t.league_id = l.id
WHERE c.id IS NULL OR s.id IS NULL OR l.id IS NULL;

-- Team naming consistency
SELECT team_name, COUNT(*) FROM teams 
GROUP BY team_name 
HAVING COUNT(*) > 1;
```

## 👥 **Player Data Standards**

### **Required Fields**
- `first_name`: Non-empty string
- `last_name`: Non-empty string
- `tenniscores_player_id`: Unique identifier
- `club_id`: Valid foreign key reference
- `series_id`: Valid foreign key reference
- `league_id`: Valid foreign key reference

### **Quality Metrics**
- **Uniqueness**: tenniscores_player_id should be unique
- **Completeness**: All required fields should be populated
- **Association accuracy**: Player-team associations should be correct

### **Validation Rules**
```sql
-- Unique player IDs
SELECT tenniscores_player_id, COUNT(*) FROM players 
GROUP BY tenniscores_player_id 
HAVING COUNT(*) > 1;

-- Complete player records
SELECT COUNT(*) FROM players 
WHERE first_name IS NULL OR last_name IS NULL OR tenniscores_player_id IS NULL;
```

## 📈 **Match Data Standards**

### **Required Fields**
- `match_date`: Valid date
- `home_team_id`: Valid team ID
- `away_team_id`: Valid team ID
- `winner`: Valid player ID
- `scores`: Non-empty string

### **Quality Metrics**
- **No self-matches**: Teams should not play against themselves
- **Valid scores**: Score format should be consistent
- **Winner validation**: Winner should be a player in the match

### **Validation Rules**
```sql
-- No self-matches
SELECT COUNT(*) FROM match_scores 
WHERE home_team_id = away_team_id;

-- Valid winner
SELECT COUNT(*) FROM match_scores ms
LEFT JOIN players p ON ms.winner = p.tenniscores_player_id
WHERE ms.winner IS NOT NULL AND p.id IS NULL;
```

## 🔄 **ETL Process Standards**

### **Pre-Import Validation**
- [ ] Database constraints are in place
- [ ] No existing duplicate records
- [ ] Team name mapping is functional
- [ ] Data structure is valid

### **Import Process**
- [ ] Use upsert operations for idempotency
- [ ] Batch processing for performance
- [ ] Comprehensive error handling
- [ ] Progress logging

### **Post-Import Validation**
- [ ] All teams have schedule data
- [ ] No NULL team_id values
- [ ] No duplicate records
- [ ] No orphaned records

### **Health Check Thresholds**
```python
# Schedule data health thresholds
SCHEDULE_HEALTH_THRESHOLDS = {
    'missing_teams_percentage': 5.0,  # Alert if >5% teams missing data
    'null_team_records_percentage': 1.0,  # Alert if >1% records have NULL team_id
    'duplicate_records_percentage': 0.1,  # Alert if >0.1% duplicate records
    'orphaned_records_percentage': 0.1,  # Alert if >0.1% orphaned records
    'coverage_minimum': 95.0,  # Minimum coverage percentage
}
```

## 🚨 **Alerting Standards**

### **Critical Alerts**
- Health score < 75
- >10% teams missing schedule data
- >5% records with NULL team_id
- >1% duplicate records
- >1% orphaned records

### **Warning Alerts**
- Health score < 90
- >5% teams missing schedule data
- >1% records with NULL team_id
- Coverage < 95%

### **Alert Channels**
- SMS notifications to admin
- Email notifications to team
- Dashboard alerts
- Log file entries

## 📋 **Monitoring Standards**

### **Daily Checks**
- Schedule data health check
- Team coverage validation
- Data integrity verification
- Performance metrics

### **Weekly Checks**
- Comprehensive data quality audit
- ETL process performance review
- User feedback analysis
- System health assessment

### **Monthly Checks**
- Data quality trend analysis
- Process optimization review
- Standards compliance audit
- Improvement planning

## 🛠️ **Implementation Standards**

### **Database Constraints**
```sql
-- Unique constraint for upsert operations
ALTER TABLE schedule 
ADD CONSTRAINT unique_schedule_match 
UNIQUE (match_date, home_team, away_team, league_id);

-- Prevent NULL team_id values
ALTER TABLE schedule 
ADD CONSTRAINT schedule_team_id_not_null 
CHECK (home_team_id IS NOT NULL OR away_team_id IS NOT NULL);

-- Prevent self-matches
ALTER TABLE schedule 
ADD CONSTRAINT schedule_no_self_match 
CHECK (home_team_id != away_team_id OR (home_team_id IS NULL AND away_team_id IS NULL));
```

### **Application Validation**
```python
# Pre-import validation
def validate_etl_preconditions():
    """Validate ETL preconditions before import"""
    checks = []
    
    # Check 1: Unique constraint exists
    if not unique_constraint_exists('schedule', 'unique_schedule_match'):
        checks.append("Missing unique constraint on schedule table")
    
    # Check 2: No existing duplicate records
    duplicate_count = count_duplicate_schedule_records()
    if duplicate_count > 0:
        checks.append(f"Found {duplicate_count} duplicate schedule records")
    
    # Check 3: Team name mapping integrity
    mapping_issues = validate_team_name_mapping()
    if mapping_issues:
        checks.append(f"Team name mapping issues: {mapping_issues}")
    
    return len(checks) == 0, checks

# Post-import validation
def validate_import_results():
    """Validate ETL import results"""
    validations = []
    
    # Validation 1: All teams have schedule data
    missing_teams = get_teams_without_schedule()
    if missing_teams:
        validations.append(f"Teams missing schedule data: {len(missing_teams)}")
    
    # Validation 2: No NULL team_id values
    null_team_count = count_schedule_records_with_null_team_id()
    if null_team_count > 0:
        validations.append(f"Schedule records with NULL team_id: {null_team_count}")
    
    # Validation 3: No duplicate records
    duplicate_count = count_duplicate_schedule_records()
    if duplicate_count > 0:
        validations.append(f"Duplicate schedule records: {duplicate_count}")
    
    return len(validations) == 0, validations
```

## 📊 **Success Metrics**

### **Data Quality Metrics**
- **Schedule Coverage**: >99% of teams have schedule data
- **Data Integrity**: <0.1% records with NULL team_id
- **Duplicate Rate**: <0.01% duplicate records
- **Orphaned Rate**: <0.01% orphaned records

### **Process Metrics**
- **ETL Success Rate**: >95% successful imports
- **Error Detection Time**: <1 hour from issue occurrence
- **Recovery Time**: <4 hours for critical issues
- **Validation Coverage**: 100% of data validated

### **Monitoring Metrics**
- **Health Check Frequency**: Daily automated checks
- **Alert Response Time**: <30 minutes for critical alerts
- **Issue Resolution Time**: <24 hours for non-critical issues
- **Standards Compliance**: 100% adherence to standards

## 🔄 **Continuous Improvement**

### **Monthly Reviews**
- Review ETL performance metrics
- Analyze data quality trends
- Update prevention strategies
- Identify improvement opportunities

### **Quarterly Assessments**
- Evaluate prevention strategy effectiveness
- Identify new risk factors
- Update monitoring and alerting
- Review and update standards

### **Annual Audits**
- Comprehensive data quality audit
- ETL process optimization review
- Technology stack evaluation
- Standards compliance assessment

## 📚 **Documentation Standards**

### **Required Documentation**
- Data quality standards (this document)
- ETL process documentation
- Validation procedures
- Monitoring and alerting procedures
- Troubleshooting guides

### **Documentation Quality**
- Clear and concise language
- Step-by-step procedures
- Examples and use cases
- Regular updates and maintenance

### **Access and Distribution**
- Centralized documentation repository
- Version control for all documents
- Regular review and updates
- Team training and awareness

This comprehensive data quality framework ensures that all data meets high standards of integrity, completeness, consistency, and accuracy, preventing the types of issues that occurred with schedule data. 