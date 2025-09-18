# Club Address Management Commands

## 📋 **Main Commands**

### **Load Addresses from CSV**
```bash
# Using the wrapper script (recommended)
python3 scripts/load_club_addresses.py

# Using the main script directly
python3 data/etl/import/load_club_addresses_from_csv.py

# Dry run (preview changes)
python3 scripts/load_club_addresses.py --dry-run

# Custom CSV file
python3 scripts/load_club_addresses.py --csv-file data/your_addresses.csv
```

### **Fuzzy Match Remaining Clubs**
```bash
# Find matches for clubs without addresses
python3 scripts/fuzzy_match_club_addresses.py

# With custom threshold
python3 scripts/fuzzy_match_club_addresses.py --threshold 0.5

# Dry run
python3 scripts/fuzzy_match_club_addresses.py --dry-run --threshold 0.5
```

## 📁 **File Locations**

- **Main Script**: `data/etl/import/load_club_addresses_from_csv.py`
- **Wrapper Script**: `scripts/load_club_addresses.py`
- **Fuzzy Matching**: `scripts/fuzzy_match_club_addresses.py`
- **Address CSV**: `data/club_addresses.csv`

## 🎯 **Current Status**

- **Total clubs**: 136
- **Clubs with addresses**: 132 (97.1%)
- **Clubs without addresses**: 4 (2.9%)
  - BYE (placeholder)
  - Midt (abbreviated name)
  - Old Willow (inactive)
  - Ravinia Green (inactive)

## 📝 **Usage Notes**

1. **Main script** is now in `data/etl/import/` following the project structure
2. **Wrapper script** in `scripts/` provides easy access
3. **Fuzzy matching** helps find matches for clubs with name variations
4. **Dry run mode** always recommended before live updates
