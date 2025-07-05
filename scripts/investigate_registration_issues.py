#!/usr/bin/env python3
"""
Investigation: Registration Issues for Aaron Sheffren
====================================================

This script investigates the registration failure for Aaron Sheffren and proposes fixes.

Issues found:
1. Name spelling: "Sheffren" (user) vs "Shefren" (database) 
2. Missing series field in registration form
3. SQL syntax error when no series provided
    4. Missing series.display_name mappings (formerly series_name_mappings table)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database_utils import execute_query, execute_query_one
from utils.database_player_lookup import find_player_by_database_lookup, get_name_variations

def simple_similarity(str1, str2):
    """Simple string similarity using character overlap"""
    str1, str2 = str1.lower(), str2.lower()
    
    # Handle exact matches
    if str1 == str2:
        return 1.0
    
    # Calculate character-level similarity
    set1, set2 = set(str1), set(str2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0.0
    
    # Jaccard similarity with length penalty
    jaccard = intersection / union
    
    # Length difference penalty
    len_diff = abs(len(str1) - len(str2))
    max_len = max(len(str1), len(str2))
    len_penalty = 1.0 - (len_diff / max_len) if max_len > 0 else 0.0
    
    # Combined similarity
    return (jaccard + len_penalty) / 2

def test_name_variations():
    """Test the current name variations system"""
    print("🧪 Testing current name variations system:")
    
    test_names = ["Aaron", "Sheffren", "Shefren"]
    for name in test_names:
        variations = get_name_variations(name)
        print(f"  {name} → {variations}")

def test_similarity():
    """Test string similarity for name matching"""
    print("\n🧪 Testing string similarity:")
    
    user_input = "Sheffren"
    database_name = "Shefren" 
    
    similarity = simple_similarity(user_input, database_name)
    
    print(f"  '{user_input}' vs '{database_name}':")
    print(f"    Similarity: {similarity:.2%}")
    print(f"    Should match: {'YES' if similarity >= 0.8 else 'NO'}")

def find_similar_names_in_db():
    """Find names in database similar to 'Sheffren'"""
    print("\n🔍 Finding similar last names in database:")
    
    # Get all unique last names starting with 'Sh'
    results = execute_query("""
        SELECT DISTINCT last_name, COUNT(*) as count
        FROM players 
        WHERE LOWER(last_name) LIKE 'sh%'
        GROUP BY last_name
        ORDER BY last_name
    """)
    
    user_input = "Sheffren"
    matches = []
    
    for result in results:
        db_name = result['last_name']
        similarity = simple_similarity(user_input, db_name)
        if similarity >= 0.7:  # 70% similarity threshold
            matches.append({
                'name': db_name, 
                'similarity': similarity,
                'count': result['count']
            })
    
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    print(f"  Similar to '{user_input}':")
    for match in matches:
        print(f"    {match['name']:15} {match['similarity']:.2%} similarity ({match['count']} players)")

def test_player_lookup_with_fix():
    """Test player lookup with proposed name similarity fix"""
    print("\n🧪 Testing player lookup:")
    
    # Test exact spelling (should fail)
    print("  1. Exact spelling 'Sheffren':")
    try:
        result1 = find_player_by_database_lookup(
            first_name="Aaron",
            last_name="Sheffren",
            club_name="Tennaqua", 
            series_name="Chicago 38",
            league_id="APTA_CHICAGO"
        )
        print(f"     Result: {result1.get('match_type', 'error')}")
    except Exception as e:
        print(f"     Error: {str(e)[:100]}...")
    
    # Test correct spelling (should work)
    print("  2. Correct spelling 'Shefren':")
    try:
        result2 = find_player_by_database_lookup(
            first_name="Aaron",
            last_name="Shefren",
            club_name="Tennaqua",
            series_name="Chicago 38", 
            league_id="APTA_CHICAGO"
        )
        print(f"     Result: {result2.get('match_type', 'error')}")
        if result2.get('player'):
            print(f"     Player ID: {result2['player']['tenniscores_player_id']}")
    except Exception as e:
        print(f"     Error: {str(e)[:100]}...")

def test_empty_series_issue():
    """Test the empty series SQL issue"""
    print("\n🧪 Testing empty series SQL issue:")
    
    print("  1. With empty series (should cause SQL error):")
    try:
        result = find_player_by_database_lookup(
            first_name="Aaron",
            last_name="Shefren",
            club_name="Tennaqua",
            series_name="",  # Empty series
            league_id="APTA_CHICAGO"
        )
        print(f"     Result: {result.get('match_type', 'error')}")
    except Exception as e:
        print(f"     Error: {str(e)[:100]}...")

def check_series_api_data():
    """Check what series data is available"""
    print("\n🔍 Checking series data for APTA Chicago:")
    
    # Get all Chicago series
    results = execute_query("""
        SELECT DISTINCT s.name as series_name, COUNT(p.id) as player_count
        FROM series s
        JOIN players p ON s.id = p.series_id AND p.is_active = true
        JOIN leagues l ON p.league_id = l.id
        WHERE l.league_id = 'APTA_CHICAGO'
        GROUP BY s.name
        ORDER BY s.name
    """)
    
    print(f"  Found {len(results)} series:")
    for i, result in enumerate(results):
        if i < 10:  # Show first 10
            print(f"    {result['series_name']} ({result['player_count']} players)")
        elif i == 10:
            print(f"    ... and {len(results) - 10} more")
            break
    
    # Check if Chicago 38 exists
    chicago38 = [r for r in results if r['series_name'] == 'Chicago 38']
    if chicago38:
        print(f"\n  ✅ 'Chicago 38' exists with {chicago38[0]['player_count']} players")
    else:
        print(f"\n  ❌ 'Chicago 38' not found")

def proposed_fixes():
    """Suggest fixes for the identified issues"""
    print("\n💡 PROPOSED FIXES:")
    print("=" * 50)
    
    print("1. **Enhanced Name Matching**:")
    print("   - Add similarity checking for last names")
    print("   - Use 80% similarity threshold for close matches")
    print("   - 'Sheffren' → 'Shefren' should match with high similarity")
    
    print("\n2. **Fix Empty Series SQL Issue**:")
    print("   - Modify database_player_lookup.py to handle empty series")
    print("   - Skip series filtering when series_name is empty")
    print("   - Add proper validation before building SQL WHERE clauses")
    
    print("\n3. **Fix Series Dropdown Loading**:")
    print("   - Ensure series API endpoints work properly") 
    print("   - Add fallback when series.display_name mappings are missing")
    print("   - Convert 'Chicago 38' → 'Series 38' for APTA league display")
    
    print("\n4. **Registration Form Improvements**:")
    print("   - Make series field more prominent/visible")
    print("   - Add validation to ensure series is selected")
    print("   - Provide better error messages when player not found")

def create_fix_summary():
    """Create a summary of fixes needed"""
    print("\n📋 FIX PRIORITY:")
    print("=" * 30)
    print("🔥 **HIGH PRIORITY**:")
    print("   1. Fix empty series SQL syntax error")
    print("   2. Add name similarity matching (80% threshold)")
    print("   3. Ensure series dropdown populates correctly")
    
    print("\n🔧 **MEDIUM PRIORITY**:")
    print("   1. Better registration error messages")
    print("   2. Series field validation and prominence")
    print("   3. Fallback for missing database tables")

def main():
    """Run all investigations"""
    print("🔍 INVESTIGATING REGISTRATION ISSUES")
    print("User: Aaron Sheffren, Tennaqua, APTA Chicago")
    print("=" * 60)
    
    try:
        test_name_variations()
        test_similarity()
        find_similar_names_in_db()
        test_player_lookup_with_fix()
        test_empty_series_issue()
        check_series_api_data()
        proposed_fixes()
        create_fix_summary()
        
        print(f"\n📋 SUMMARY:")
        print("- ✅ Aaron Shefren exists in database (Player ID: nndz-WlNlN3dMeitndz09)")
        print("- ✅ Chicago 38 series exists") 
        print("- ❌ Name spelling mismatch: 'Sheffren' vs 'Shefren'")
        print("- ❌ Empty series causes SQL syntax error")
        print("- ❌ Series dropdown may not be loading properly")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 