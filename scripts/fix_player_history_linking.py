#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from database_utils import execute_query, execute_query_one

print("🔧 FIXING PLAYER_HISTORY LINKING")
print("=" * 50)

def fix_ross_freedman_linking():
    """Fix Ross Freedman's player_history linking as a test case"""
    print("\n1. Fixing Ross Freedman's PTI linking:")
    
    ross_player_id = 10732
    ross_pti = 50.80
    
    # Find exact PTI matches for Ross in correct series
    exact_matches_query = '''
        SELECT 
            id,
            date,
            end_pti,
            series,
            TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
        FROM player_history
        WHERE end_pti = %s
        AND (series ILIKE '%Chicago%22%' OR series ILIKE '%Chicago: 22%')
        ORDER BY date DESC
    '''
    
    matches = execute_query(exact_matches_query, [ross_pti])
    
    if matches:
        print(f"   Found {len(matches)} exact PTI matches for Ross:")
        for match in matches:
            print(f"     ID {match['id']}: {match['formatted_date']} - Series: {match['series']}")
        
        # Update these records to link to Ross
        update_query = '''
            UPDATE player_history
            SET player_id = %s
            WHERE end_pti = %s
            AND (series ILIKE '%Chicago%22%' OR series ILIKE '%Chicago: 22%')
            AND player_id IS NULL
        '''
        
        print(f"\n   Executing linking update...")
        print(f"   SQL: UPDATE player_history SET player_id = {ross_player_id} WHERE end_pti = {ross_pti} AND series matches Chicago 22")
        
        # Execute the update
        try:
            from database_utils import execute_update
            success = execute_update(update_query, [ross_player_id, ross_pti])
            if success:
                print(f"   ✅ Successfully executed linking update for Ross Freedman")
            
            # Verify the link
            verification_query = '''
                SELECT COUNT(*) as count
                FROM player_history
                WHERE player_id = %s
            '''
            verification = execute_query_one(verification_query, [ross_player_id])
            print(f"   ✅ Verification: Ross now has {verification['count']} linked PTI history records")
            
        except Exception as e:
            print(f"   ❌ Error updating records: {e}")
            
    else:
        print("   ❌ No exact PTI matches found for Ross")

def analyze_linking_opportunities():
    """Analyze how many players can be linked using exact PTI matching"""
    print("\n2. Analyzing linking opportunities:")
    
    # Find players with unique PTI values that have exact matches in history
    unique_pti_query = '''
        SELECT 
            p.id,
            p.first_name,
            p.last_name,
            p.pti,
            s.name as series_name,
            COUNT(ph.id) as history_matches
        FROM players p
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN player_history ph ON (
            ph.end_pti = p.pti AND
            ph.player_id IS NULL AND
            (ph.series ILIKE '%' || REPLACE(s.name, ' ', '%') || '%' OR
             ph.series ILIKE '%' || REPLACE(s.name, ' ', ':%') || '%')
        )
        WHERE p.pti IS NOT NULL
        GROUP BY p.id, p.first_name, p.last_name, p.pti, s.name
        HAVING COUNT(ph.id) > 0
        ORDER BY COUNT(ph.id) DESC
        LIMIT 20
    '''
    
    opportunities = execute_query(unique_pti_query)
    
    if opportunities:
        print(f"   Found {len(opportunities)} players with linkable PTI history:")
        total_linkable = 0
        for opp in opportunities:
            print(f"     {opp['first_name']} {opp['last_name']} (PTI: {opp['pti']}): {opp['history_matches']} records")
            total_linkable += opp['history_matches']
        
        print(f"\n   Total linkable records: {total_linkable:,}")
        return opportunities
    else:
        print("   No linking opportunities found")
        return []

def implement_bulk_linking(opportunities, limit=5):
    """Implement linking for the top N players with clear matches"""
    print(f"\n3. Implementing bulk linking (limit: {limit} players):")
    
    total_linked = 0
    
    for i, opp in enumerate(opportunities[:limit]):
        player_id = opp['id']
        player_name = f"{opp['first_name']} {opp['last_name']}"
        pti = opp['pti']
        series_name = opp['series_name']
        
        print(f"\n   {i+1}. Linking {player_name} (ID: {player_id}, PTI: {pti}):")
        
        # Create series pattern for matching
        series_patterns = []
        if series_name:
            series_patterns.extend([
                f"%{series_name.replace(' ', '%')}%",
                f"%{series_name.replace(' ', ':%')}%"
            ])
        
        # Build the update query
        pattern_conditions = " OR ".join([f"ph.series ILIKE '{pattern}'" for pattern in series_patterns])
        
        update_query = f'''
            UPDATE player_history
            SET player_id = %s
            WHERE end_pti = %s
            AND player_id IS NULL
            AND ({pattern_conditions})
        '''
        
        try:
            from database_utils import execute_update
            success = execute_update(update_query, [player_id, pti])
            if success:
                print(f"     ✅ Successfully executed linking update")
                total_linked += 1  # Count successful operations
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    print(f"\n   📊 Total players processed: {total_linked:,}")
    return total_linked

def verify_fixes():
    """Verify the linking fixes worked correctly"""
    print("\n4. Verifying fixes:")
    
    # Check total linked records
    linked_count_query = "SELECT COUNT(*) as count FROM player_history WHERE player_id IS NOT NULL"
    linked_count = execute_query_one(linked_count_query)['count']
    
    total_count_query = "SELECT COUNT(*) as count FROM player_history"
    total_count = execute_query_one(total_count_query)['count']
    
    percentage = (linked_count / total_count) * 100 if total_count > 0 else 0
    
    print(f"   📊 Linked records: {linked_count:,} / {total_count:,} ({percentage:.1f}%)")
    
    # Check Ross specifically
    ross_check_query = '''
        SELECT 
            ph.date,
            ph.end_pti,
            ph.series,
            TO_CHAR(ph.date, 'YYYY-MM-DD') as formatted_date
        FROM player_history ph
        WHERE ph.player_id = 10732
        ORDER BY ph.date DESC
        LIMIT 5
    '''
    
    ross_records = execute_query(ross_check_query)
    if ross_records:
        print(f"\n   ✅ Ross Freedman's linked PTI history:")
        for record in ross_records:
            print(f"     {record['formatted_date']}: PTI={record['end_pti']} - {record['series']}")
    else:
        print(f"\n   ❌ No linked records found for Ross")

def test_mobile_service_after_fix():
    """Test that the mobile service now works with proper linking"""
    print("\n5. Testing mobile service after fix:")
    
    try:
        from services.mobile_service import get_player_analysis
        
        # Test with Ross's data
        user = {
            'tenniscores_player_id': 'nndz-WkMrK3didjlnUT09',
            'email': 'test@example.com',
            'league_id': 'APTA'
        }
        
        result = get_player_analysis(user)
        
        print(f"   PTI Data Available: {result.get('pti_data_available')}")
        print(f"   Current PTI: {result.get('current_pti')}")
        print(f"   PTI Change: {result.get('weekly_pti_change')}")
        
        if result.get('pti_data_available'):
            print(f"   ✅ Mobile service working with proper player_history linking!")
        else:
            print(f"   ⚠️  Mobile service still using fallback method")
            
    except Exception as e:
        print(f"   ❌ Error testing mobile service: {e}")

if __name__ == "__main__":
    print("Starting player_history linking repair...")
    
    # Step 1: Fix Ross as a test case
    fix_ross_freedman_linking()
    
    # Step 2: Analyze opportunities
    opportunities = analyze_linking_opportunities()
    
    # Step 3: Implement bulk linking for top candidates
    if opportunities:
        implement_bulk_linking(opportunities, limit=10)
    
    # Step 4: Verify results
    verify_fixes()
    
    # Step 5: Test mobile service
    test_mobile_service_after_fix()
    
    print(f"\n🎉 Player_history linking repair completed!") 