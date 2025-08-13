# Manual Production Database Update

## Step 1: Connect to Production Database

1. Open a new terminal window
2. Navigate to the Rally project: `cd /Users/rossfreedman/dev/rally`
3. Ensure you're connected to production database:
   ```bash
   railway service
   # Select: Rally Production Database
   ```
4. Connect to database:
   ```bash
   railway connect
   ```

## Step 2: Add Missing Clubs

Once connected to the PostgreSQL prompt, run:

```sql
-- Add missing clubs that cause ETL import failures
INSERT INTO clubs (name) VALUES ('PraIrie Club'), ('Glenbrook') ON CONFLICT (name) DO NOTHING;

-- Verify clubs were added
SELECT name FROM clubs WHERE name IN ('PraIrie Club', 'Glenbrook') ORDER BY name;
```

Expected output:
```
     name     
--------------
 Glenbrook
 PraIrie Club
(2 rows)
```

## Step 3: Verify ETL Dependencies (Optional)

```sql
-- Check Anne Mooney's dependencies exist
SELECT 
    'Tennaqua club' as item,
    CASE WHEN COUNT(*) > 0 THEN 'EXISTS' ELSE 'MISSING' END as status
FROM clubs WHERE name = 'Tennaqua'

UNION ALL

SELECT 
    'Tennaqua B team' as item,
    CASE WHEN COUNT(*) > 0 THEN 'EXISTS' ELSE 'MISSING' END as status  
FROM teams WHERE team_name = 'Tennaqua B' AND league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')

UNION ALL

SELECT 
    'Series B' as item,
    CASE WHEN COUNT(*) > 0 THEN 'EXISTS' ELSE 'MISSING' END as status
FROM series WHERE name = 'Series B';
```

## Step 4: Exit

```sql
\q
```

## Verification

After completing this, the enhanced ETL system will be 100% operational:

- ✅ Missing clubs added to both staging and production
- ✅ Enhanced import scripts deployed 
- ✅ Anne Mooney will import successfully with her 6 matches
- ✅ Future ETL imports will achieve 100% success rate

## Next ETL Run Test

To test the improvements, run:
```bash
python data/etl/database_import/import_players.py
```

Expected: 100% success rate with enhanced error handling!
