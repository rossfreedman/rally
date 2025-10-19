# Instructions: Populate starting_pti on Staging via SSH

## Method 1: Using Railway CLI (Recommended)

1. **Open Railway staging shell interactively:**
   ```bash
   cd /Users/rossfreedman/dev/rally
   railway link
   # Select: rossfreedman's Projects > rally > staging
   railway shell
   ```

2. **Once in the Railway shell, run:**
   ```bash
   python scripts/populate_starting_pti.py
   ```

   This will automatically use the staging database (DATABASE_URL environment variable).

---

## Method 2: Direct PostgreSQL Connection (if Railway shell unavailable)

Since the populate script connects via the DATABASE_PUBLIC_URL, we can run it directly from local but it's slow over network.

**Run this from your local machine:**
```bash
cd /Users/rossfreedman/dev/rally
export DATABASE_PUBLIC_URL="postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
python3 scripts/populate_starting_pti.py
```

This will take longer (5-10 minutes) due to network latency for 5,228 UPDATE queries.

---

## Method 3: Single SQL Statement (Fastest)

Run this SQL directly on staging database for instant update:

```sql
-- Connect to staging database
psql "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

-- Update all starting_pti values in one query
UPDATE players p
SET starting_pti = subquery.pti_value
FROM (VALUES
    ('Ross', 'Freedman', 'Series 20', 50.8),
    -- Add all 5,228 values here...
) AS subquery(first_name, last_name, series, pti_value)
JOIN series s ON LOWER(s.display_name) = LOWER(subquery.series)
WHERE LOWER(p.first_name) = LOWER(subquery.first_name)
  AND LOWER(p.last_name) = LOWER(subquery.last_name)
  AND p.series_id = s.id
  AND p.is_active = true;
```

---

## Current Status

✅ **Completed:**
- Schema migration applied to staging (starting_pti column exists)
- Code pushed to staging branch and deployed
- Migration file: `20251019_133000_add_starting_pti_to_players.sql`

⏳ **In Progress:**
- Populating 5,228 player records with starting_pti values

🔜 **Next:**
- Verify on staging analyze-me page after population completes

---

## Quick Verification After Population

```bash
# Check count of populated records
psql "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway" \
  -c "SELECT COUNT(*) as total, COUNT(starting_pti) as populated FROM players WHERE is_active = true;"

# Verify Ross Freedman's record
psql "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway" \
  -c "SELECT first_name, last_name, pti, starting_pti FROM players WHERE first_name = 'Ross' AND last_name = 'Freedman';"
```

