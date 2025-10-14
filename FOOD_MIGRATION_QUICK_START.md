# 🍽️ Food Fields Migration - Quick Start Guide

## What Changed?

The food input page now has **TWO text boxes** instead of one:

1. **Men's Paddle (Tues/Wed/Thurs)** - separate food option
2. **Women's Paddle (Sun/Mon/Friday)** - separate food option

## Quick Deploy (3 Steps)

### 1️⃣ Apply Database Migration Locally

```bash
python scripts/apply_food_fields_migration.py
```

This adds two new database columns: `mens_food` and `womens_food`

### 2️⃣ Test It Locally

```bash
# Start your server
python server.py

# Visit: http://localhost:3000/food
# Try entering food for both men's and women's paddle
```

### 3️⃣ Deploy to Staging

```bash
python data/dbschema/dbschema_workflow.py --auto
```

## What You'll See

### Before (Old Way)
```
Food Description:
[Single text box for all food]
```

### After (New Way)
```
Men's Paddle (Tues/Wed/Thurs):
[Text box for men's food]

Women's Paddle (Sun/Mon/Friday):
[Text box for women's food]
```

## Display Changes

When users view the menu, they'll see:

```
┌─────────────────────────────────────┐
│         Current Menu                │
├─────────────────────────────────────┤
│ Men's Paddle (Tues/Wed/Thurs)      │
│ Grilled Salmon with Quinoa          │
│                                     │
│ Women's Paddle (Sun/Mon/Friday)     │
│ Caesar Salad with Grilled Chicken   │
└─────────────────────────────────────┘
```

## Files Changed

✅ Database: Added `mens_food` and `womens_food` columns  
✅ Backend: Updated API routes to handle both fields  
✅ Frontend: Updated input form with two text boxes  
✅ Display: Shows both options nicely formatted  
✅ Notifications: Shows both options in alerts  

## Backward Compatibility

✅ Old records with single `food_text` will still work  
✅ Existing data is preserved  
✅ No breaking changes  

## Need Help?

Full documentation: `docs/FOOD_FIELDS_MIGRATION.md`

---

**Keep it simple!** ✨

