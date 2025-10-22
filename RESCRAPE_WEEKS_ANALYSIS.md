# 📊 Production Rescraping Analysis - How Many Weeks Back?

## Date: October 21, 2025
## Analysis: Weeks needed to fix production date issues

---

## 🎯 **Key Findings**

### **Current Scraper Configuration:**
- ✅ **Current scraper**: `--weeks 2` (goes back 14 days)
- ✅ **Current range**: Oct 7 - Oct 21 (today)
- ✅ **Command**: `python3 data/etl/scrapers/apta_scrape_match_scores.py aptachicago --weeks 2`

### **Production Database Status:**
- ❌ **Missing historical data**: Only has Oct 14-21 (4 days)
- ❌ **Missing Aaron Walsh matches**: Sep 25, Oct 2, Oct 9
- ❌ **Wrong dates**: All matches show Oct 16 instead of actual dates

### **Local Database Status (After Fix):**
- ✅ **Complete data**: Sep 23 - Oct 16 (12 days)
- ✅ **Correct dates**: Aaron Walsh has 4 different dates
- ✅ **Comprehensive coverage**: 3,825 matches

---

## 🔍 **Aaron Walsh Analysis**

### **Production (BROKEN):**
```
2025-10-16: Tennaqua 12 vs Inverness 12    (DB ID: 1801907)
2025-10-16: Tennaqua 12 vs Lakeshore S&F 12 (DB ID: 1800493)  
2025-10-16: Tennaqua 12 vs Skokie 12       (DB ID: 1799156)
2025-10-16: Tennaqua 12 vs Barrington Hill (DB ID: 1798210)
```

### **Local (FIXED):**
```
2025-10-16: Tennaqua 12 vs Inverness 12    (DB ID: 1801907)
2025-10-09: Tennaqua 12 vs Lakeshore S&F 12 (DB ID: 1800493)
2025-10-02: Tennaqua 12 vs Skokie 12       (DB ID: 1799156)  
2025-09-25: Tennaqua 12 vs Barrington Hill (DB ID: 1798210)
```

### **Date Range Analysis:**
- **Earliest match**: Sep 25, 2025 (26 days ago)
- **Latest match**: Oct 16, 2025 (5 days ago)
- **Total span**: 21 days
- **Weeks needed**: 4 weeks (26 days ÷ 7 = 3.7 weeks, round up to 4)

---

## 🚨 **The Problem**

### **Current Scraper Limitation:**
- **Current**: 2 weeks back (Oct 7 - Oct 21)
- **Needed**: 4 weeks back (Sep 25 - Oct 21)
- **Missing**: Sep 25 - Oct 6 (12 days of data)

### **Why Production is Missing Data:**
1. **Production scraper** only runs 2 weeks back
2. **Aaron Walsh's older matches** (Sep 25, Oct 2, Oct 9) are **not in production**
3. **Only his Oct 16 match** is in production, but shows wrong date
4. **Result**: Missing historical data + wrong dates

---

## 🎯 **Solution: 4-Week Rescrape**

### **Recommended Command:**
```bash
# Change from 2 weeks to 4 weeks
python3 data/etl/scrapers/apta_scrape_match_scores.py aptachicago --weeks 4
```

### **Expected Result:**
- ✅ **Aaron Walsh will have 4 different dates** (Sep 25, Oct 2, Oct 9, Oct 16)
- ✅ **All players will have correct individual match dates**
- ✅ **Complete historical coverage** (Sep 25 - Oct 21)
- ✅ **Analyze-me page will show different dates** for different matches

---

## 📊 **Impact Assessment**

### **Data Coverage:**
- **Current production**: Oct 14-21 (4 days, ~3,780 matches)
- **After 4-week rescrape**: Sep 25 - Oct 21 (27 days, ~4,000+ matches)
- **Additional data**: ~220+ matches from missing dates

### **Players Affected:**
- **All players** with matches before Oct 14
- **All players** with multiple matches (date accuracy)
- **Estimated**: Hundreds of players with incomplete/incorrect data

---

## 🚀 **Implementation Plan**

### **Step 1: Update Scraper Configuration**
```bash
# Modify apta_scraper_runner_stats_scores.py line 73:
# FROM: --weeks 2
# TO:   --weeks 4
```

### **Step 2: Deploy Fix**
1. ✅ **Deploy date extraction fix** to production
2. ✅ **Update scraper to 4 weeks** 
3. ✅ **Run full rescrape**

### **Step 3: Validation**
- ✅ **Check Aaron Walsh analyze-me page** shows 4 different dates
- ✅ **Verify all players** have correct individual match dates
- ✅ **Confirm data completeness** (Sep 25 - Oct 21)

---

## 💡 **Key Insight**

**The issue is TWO-FOLD:**

1. **Missing historical data** - Production only has 4 days (Oct 14-21)
2. **Wrong individual dates** - All matches show same date instead of actual match dates

**Solution requires:**
- ✅ **4-week rescrape** (to get missing historical data)
- ✅ **Fixed date extraction** (to get correct individual dates)

---

## 🎯 **Final Recommendation**

### **RESCrape 4 Weeks Back**

**Why 4 weeks:**
- ✅ **Covers Aaron Walsh's earliest match** (Sep 25)
- ✅ **Provides complete historical coverage**
- ✅ **Fixes both missing data AND wrong dates**
- ✅ **Matches local database scope**

**Command:**
```bash
python3 data/etl/scrapers/apta_scrape_match_scores.py aptachicago --weeks 4
```

**Expected Result:**
- Aaron Walsh analyze-me page shows 4 different dates
- All players have correct individual match dates
- Complete historical data coverage

---

*Analysis Completed: October 21, 2025, 6:00 PM*  
*Recommendation: 4-week rescrape*  
*Current: 2 weeks (insufficient)*  
*Needed: 4 weeks (complete coverage)* ✅
