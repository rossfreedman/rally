# Food Fields Migration - Men's & Women's Paddle Options

## Overview

This migration splits the single `food_text` field into two separate fields to support distinct food options for men's and women's paddle days:

- **Men's Paddle** (Tues/Wed/Thurs)
- **Women's Paddle** (Sun/Mon/Friday)

## Changes Made

### 1. Database Schema Changes

**File:** `migrations/add_mens_womens_food_fields.sql`

Added two new columns to the `food` table:
- `mens_food` (TEXT, nullable)
- `womens_food` (TEXT, nullable)

The original `food_text` column is kept for backward compatibility.

### 2. Model Updates

**File:** `app/models/database_models.py`

Updated the `Food` model class to include:
```python
mens_food = Column(Text, nullable=True)
womens_food = Column(Text, nullable=True)
food_text = Column(Text, nullable=True)  # Kept for backward compatibility
```

### 3. API Route Updates

**File:** `app/routes/api_routes.py`

Updated API endpoints:

#### GET /api/food
Now returns `mens_food` and `womens_food` in addition to `food_text`:
```json
{
  "id": 1,
  "mens_food": "Grilled Salmon",
  "womens_food": "Caesar Salad",
  "food_text": "...",  // backward compatibility
  "date": "2025-10-12",
  "club_id": 8556,
  "is_current_menu": true
}
```

#### POST /api/food
Now accepts `mens_food` and `womens_food` parameters:
```json
{
  "club_id": 8556,
  "mens_food": "Grilled Salmon with Quinoa",
  "womens_food": "Caesar Salad with Grilled Chicken",
  "is_current_menu": true
}
```

Also maintains backward compatibility by accepting `food_text` (will be stored in `mens_food`).

#### Notification System
Updated `get_food_notifications()` to display both options:
- "Men's (T/W/Th): [food] | Women's (S/M/F): [food]"

### 4. Template Updates

#### food.html (Chef Input Page)
- Replaced single textarea with two separate textareas
- Added labels: "Men's Paddle (Tues/Wed/Thurs)" and "Women's Paddle (Sun/Mon/Friday)"
- Updated form submission to send both fields
- At least one field must be filled (both are optional individually)

#### food_display.html (User View Page)
- Updated to display both men's and women's food options
- Shows each option in a colored box (blue for men's, pink for women's)
- Maintains backward compatibility for old records with only `food_text`

## Deployment Steps

### Step 1: Apply Migration to Local Database

```bash
python scripts/apply_food_fields_migration.py
```

This will:
- Add the new columns to your local database
- Copy existing `food_text` values to `mens_food` for backward compatibility
- Show confirmation of successful migration

### Step 2: Test Locally

1. Start your local server:
   ```bash
   python server.py
   ```

2. Visit the food input page: `http://localhost:3000/food`

3. Test entering:
   - Only men's food
   - Only women's food
   - Both men's and women's food

4. Verify the display page shows the options correctly: `http://localhost:3000/food-display?club_id=8556`

### Step 3: Deploy to Staging

Use the dbschema workflow to deploy to staging:

```bash
python data/dbschema/dbschema_workflow.py --auto
```

This will:
- Generate migration from your local schema
- Deploy to staging environment
- Create automatic backups

### Step 4: Test on Staging

1. Visit your staging URL (e.g., `https://rally-staging.up.railway.app/food`)
2. Test the same scenarios as local
3. Verify notifications display correctly

### Step 5: Deploy to Production

```bash
python data/dbschema/dbschema_workflow.py --production
```

## Backward Compatibility

The system maintains full backward compatibility:

1. **Old Records:** Existing records with only `food_text` will continue to display
2. **Old API Calls:** API calls using `food_text` will work (stored in `mens_food`)
3. **Migration Safety:** The migration copies existing `food_text` to `mens_food`

## Rollback Plan

If issues occur, you can rollback by:

1. Reverting code changes:
   ```bash
   git revert <commit-hash>
   ```

2. Database rollback:
   ```sql
   ALTER TABLE food DROP COLUMN IF EXISTS mens_food;
   ALTER TABLE food DROP COLUMN IF EXISTS womens_food;
   ```

## Testing Checklist

- [ ] Local migration applied successfully
- [ ] Can enter only men's food
- [ ] Can enter only women's food  
- [ ] Can enter both men's and women's food
- [ ] Display page shows both options correctly
- [ ] Old records still display correctly
- [ ] Notifications show both options
- [ ] Food history shows both options
- [ ] Set as current menu works
- [ ] Staging deployment successful
- [ ] Production deployment successful

## Files Modified

1. `migrations/add_mens_womens_food_fields.sql` (NEW)
2. `scripts/apply_food_fields_migration.py` (NEW)
3. `app/models/database_models.py`
4. `app/routes/api_routes.py`
5. `templates/food.html`
6. `templates/food_display.html`
7. `docs/FOOD_FIELDS_MIGRATION.md` (NEW)

## Notes

- Keep it simple ✅
- No breaking changes ✅
- Backward compatible ✅
- Easy to test ✅
- Clear deployment path ✅

