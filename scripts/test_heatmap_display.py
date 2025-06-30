#!/usr/bin/env python3
"""
Test script to verify the redesigned heatmap functionality
"""

import sys
sys.path.append('.')

from database_utils import execute_query
from datetime import datetime, timedelta

def test_heatmap_data():
    """Test the heatmap data generation and display"""
    
    print("🔥 Testing Redesigned Activity Heatmap")
    print("=" * 50)
    
    # Test 1: Check if heatmap endpoint has data
    print("\n1. Checking heatmap data availability...")
    
    # Generate last 30 days date range
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=29)
    
    # Get activity counts per day for last 30 days
    heatmap_data = execute_query("""
        SELECT 
            DATE(ual.timestamp) as date,
            COUNT(*) as count
        FROM user_activity_logs ual
        LEFT JOIN users u ON ual.user_email = u.email
        WHERE DATE(ual.timestamp) >= %s 
        AND DATE(ual.timestamp) <= %s
        AND ual.timestamp IS NOT NULL
        AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
        GROUP BY DATE(ual.timestamp)
        ORDER BY date
    """, [thirty_days_ago, today])
    
    print(f"Found data for {len(heatmap_data)} days out of 30")
    
    if len(heatmap_data) > 0:
        # Show sample data
        total_activities = sum(day['count'] for day in heatmap_data)
        max_day = max(heatmap_data, key=lambda x: x['count'])
        avg_daily = total_activities / 30
        
        print(f"📊 Heatmap Statistics:")
        print(f"   Total Activities: {total_activities}")
        print(f"   Daily Average: {avg_daily:.1f}")
        print(f"   Busiest Day: {max_day['date']} ({max_day['count']} activities)")
        
        print(f"\n📅 Sample days:")
        for day in heatmap_data[-5:]:  # Show last 5 days
            print(f"   {day['date']}: {day['count']} activities")
    
    # Test 2: Check activity level calculation
    print("\n2. Testing activity level calculation...")
    
    if heatmap_data:
        max_count = max(day['count'] for day in heatmap_data)
        
        def get_heatmap_level(count, max_count):
            if count == 0:
                return 0
            percentage = (count / max_count) * 100
            if percentage <= 25:
                return 1
            elif percentage <= 50:
                return 2
            elif percentage <= 75:
                return 3
            else:
                return 4
        
        print(f"   Max count: {max_count}")
        for level in range(5):
            # Find examples of each level
            examples = [day for day in heatmap_data if get_heatmap_level(day['count'], max_count) == level]
            if examples:
                example = examples[0]
                print(f"   Level {level}: {example['count']} activities ({example['date']})")
    
    # Test 3: Verify color scheme
    print("\n3. Color scheme verification...")
    colors = {
        0: "#ebedf0 (Light Gray - No activity)",
        1: "#9be9a8 (Light Green - Low activity)", 
        2: "#40c463 (Medium Green - Moderate activity)",
        3: "#30a14e (Dark Green - High activity)",
        4: "#216e39 (Darkest Green - Peak activity)"
    }
    
    for level, description in colors.items():
        print(f"   Level {level}: {description}")
    
    print("\n✅ Heatmap test completed!")
    print("\n💡 To see the new heatmap:")
    print("   1. Go to http://localhost:8080/admin/dashboard")
    print("   2. Look for 'Activity Heatmap' in the right sidebar")
    print("   3. You should see:")
    print("      - Summary stats (Total, Daily Avg, Busiest Day)")
    print("      - Grid of colored squares (30 days)")
    print("      - Interactive squares (hover for details, click to filter)")
    print("      - Clean legend at the bottom")

if __name__ == "__main__":
    test_heatmap_data() 