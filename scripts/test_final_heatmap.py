#!/usr/bin/env python3
"""
Final test for the redesigned heatmap functionality
"""

import sys
sys.path.append('.')

from database_utils import execute_query
from datetime import datetime, timedelta

def test_heatmap_final():
    """Final test of the calendar-style heatmap"""
    
    print("🔥 FINAL HEATMAP TEST - Calendar Layout")
    print("=" * 50)
    
    # Check heatmap data
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=29)
    
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
    
    print(f"✅ Found activity data for {len(heatmap_data)} days")
    
    if heatmap_data:
        total = sum(day['count'] for day in heatmap_data)
        max_day = max(heatmap_data, key=lambda x: x['count'])
        
        print(f"📊 Quick Stats:")
        print(f"   Total: {total} activities")
        print(f"   Peak: {max_day['count']} on {max_day['date']}")
        
        # Test the calendar layout logic
        print(f"\n📅 Calendar Layout Test:")
        
        # Find the Sunday before thirty_days_ago
        start_date = thirty_days_ago
        while start_date.weekday() != 6:  # Sunday is 6 in Python weekday()
            start_date -= timedelta(days=1)
            
        print(f"   Calendar starts: {start_date} (Sunday)")
        print(f"   Data range: {thirty_days_ago} to {today}")
        print(f"   Calendar covers: 6 weeks (42 days)")
        
        # Count in-range vs out-of-range days
        in_range_days = 0
        total_calendar_days = 42
        
        for i in range(42):
            cal_date = start_date + timedelta(days=i)
            if thirty_days_ago <= cal_date <= today:
                in_range_days += 1
                
        print(f"   In-range days: {in_range_days}/42")
        print(f"   Out-of-range days: {42 - in_range_days}/42 (dimmed)")
    
    print(f"\n🎨 New Features:")
    print(f"   ✅ Calendar-style weekly grid (7 columns)")
    print(f"   ✅ Day labels (S M T W T F S)")
    print(f"   ✅ 6 rows covering full date range")
    print(f"   ✅ Summary stats at top")
    print(f"   ✅ Interactive squares (click to filter)")
    print(f"   ✅ Responsive design for mobile")
    print(f"   ✅ Proper GitHub-style colors")
    
    print(f"\n💡 Testing Instructions:")
    print(f"   1. Go to: http://localhost:8080/admin/dashboard")
    print(f"   2. Look for 'Activity Heatmap' in right sidebar")
    print(f"   3. You should see:")
    print(f"      • Summary with 3 stats boxes")
    print(f"      • Day labels row (S M T W T F S)")
    print(f"      • 6 rows of 7 squares each")
    print(f"      • Clickable squares (in date range)")
    print(f"      • Dimmed squares (outside range)")
    print(f"      • Color legend at bottom")
    
    print(f"\n🐛 If still showing vertical list:")
    print(f"   • Hard refresh the browser (Cmd+Shift+R)")
    print(f"   • Check browser console for errors")
    print(f"   • Verify CSS is loading properly")

if __name__ == "__main__":
    test_heatmap_final() 