#!/usr/bin/env python3
"""
SMS Usage Analysis Script
========================

This script analyzes SMS usage patterns in the Rally application to identify:
1. Which teams and players are generating the most SMS costs
2. Which functionality is sending the most text messages
3. SMS usage trends over time
4. Cost optimization opportunities

Usage:
    python scripts/sms_usage_analysis.py
"""

import os
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import psycopg2

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_connection():
    """Get database connection"""
    try:
        from database_config import get_db_url, parse_db_url
        params = parse_db_url(get_db_url())
        conn = psycopg2.connect(**params)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def analyze_sms_usage_by_activity_type():
    """Analyze SMS usage by activity type from user_activity_logs"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Query activity logs that trigger SMS notifications
        query = """
        SELECT 
            activity_type,
            action,
            COUNT(*) as activity_count,
            COUNT(DISTINCT user_email) as unique_users,
            MIN(timestamp) as first_activity,
            MAX(timestamp) as last_activity
        FROM user_activity_logs 
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY activity_type, action
        ORDER BY activity_count DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("📊 SMS-Triggering Activity Analysis (Last 30 Days)")
        print("=" * 60)
        
        activity_data = []
        for row in results:
            activity_type, action, count, unique_users, first_activity, last_activity = row
            activity_data.append({
                'activity_type': activity_type,
                'action': action,
                'count': count,
                'unique_users': unique_users,
                'first_activity': first_activity,
                'last_activity': last_activity
            })
            
            print(f"🔹 {activity_type} - {action or 'N/A'}")
            print(f"   📈 Total Activities: {count:,}")
            print(f"   👥 Unique Users: {unique_users}")
            print(f"   📅 First: {first_activity.strftime('%Y-%m-%d %H:%M')}")
            print(f"   📅 Last: {last_activity.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        return activity_data
        
    except Exception as e:
        print(f"❌ Error analyzing activity types: {e}")
        return None
    finally:
        if conn:
            conn.close()

def analyze_sms_usage_by_teams():
    """Analyze SMS usage by teams"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Query team-related activities that trigger SMS
        query = """
        SELECT 
            t.name as team_name,
            c.name as club_name,
            s.name as series_name,
            l.name as league_name,
            COUNT(ual.id) as activity_count,
            COUNT(DISTINCT ual.user_email) as unique_users
        FROM user_activity_logs ual
        LEFT JOIN users u ON ual.user_email = u.email
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN teams t ON upa.team_id = t.id
        LEFT JOIN clubs c ON t.club_id = c.id
        LEFT JOIN series s ON t.series_id = s.id
        LEFT JOIN leagues l ON t.league_id = l.id
        WHERE ual.timestamp >= NOW() - INTERVAL '30 days'
        AND ual.activity_type IN ('team_notification_sent', 'lineup_message_sent', 'pickup_game_join', 'pickup_game_leave')
        GROUP BY t.id, t.name, c.name, s.name, l.name
        ORDER BY activity_count DESC
        LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("🏆 Top Teams by SMS-Triggering Activity (Last 30 Days)")
        print("=" * 70)
        
        team_data = []
        for row in results:
            team_name, club_name, series_name, league_name, count, unique_users = row
            team_data.append({
                'team_name': team_name,
                'club_name': club_name,
                'series_name': series_name,
                'league_name': league_name,
                'activity_count': count,
                'unique_users': unique_users
            })
            
            print(f"🔹 {team_name} ({club_name} - {series_name})")
            print(f"   🏢 League: {league_name}")
            print(f"   📈 Activities: {count:,}")
            print(f"   👥 Unique Users: {unique_users}")
            print()
        
        return team_data
        
    except Exception as e:
        print(f"❌ Error analyzing teams: {e}")
        return None
    finally:
        if conn:
            conn.close()

def analyze_sms_usage_by_users():
    """Analyze SMS usage by individual users"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Query user activities that trigger SMS
        query = """
        SELECT 
            ual.user_email,
            u.first_name,
            u.last_name,
            COUNT(ual.id) as activity_count,
            COUNT(DISTINCT ual.activity_type) as activity_types,
            MIN(ual.timestamp) as first_activity,
            MAX(ual.timestamp) as last_activity
        FROM user_activity_logs ual
        LEFT JOIN users u ON ual.user_email = u.email
        WHERE ual.timestamp >= NOW() - INTERVAL '30 days'
        AND ual.activity_type IN (
            'registration_successful', 'registration_failed', 'team_notification_sent', 
            'lineup_message_sent', 'pickup_game_join', 'pickup_game_leave',
            'player_search', 'team_switch', 'settings_update'
        )
        GROUP BY ual.user_email, u.first_name, u.last_name
        ORDER BY activity_count DESC
        LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("👥 Top Users by SMS-Triggering Activity (Last 30 Days)")
        print("=" * 60)
        
        user_data = []
        for row in results:
            email, first_name, last_name, count, activity_types, first_activity, last_activity = row
            user_data.append({
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'activity_count': count,
                'activity_types': activity_types,
                'first_activity': first_activity,
                'last_activity': last_activity
            })
            
            name = f"{first_name} {last_name}".strip() if first_name or last_name else email.split('@')[0]
            print(f"🔹 {name} ({email})")
            print(f"   📈 Activities: {count:,}")
            print(f"   🎯 Activity Types: {activity_types}")
            print(f"   📅 First: {first_activity.strftime('%Y-%m-%d %H:%M')}")
            print(f"   📅 Last: {last_activity.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        return user_data
        
    except Exception as e:
        print(f"❌ Error analyzing users: {e}")
        return None
    finally:
        if conn:
            conn.close()

def analyze_sms_usage_trends():
    """Analyze SMS usage trends over time"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Query daily activity trends
        query = """
        SELECT 
            DATE(timestamp) as activity_date,
            activity_type,
            COUNT(*) as daily_count
        FROM user_activity_logs 
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        AND activity_type IN (
            'registration_successful', 'registration_failed', 'team_notification_sent', 
            'lineup_message_sent', 'pickup_game_join', 'pickup_game_leave',
            'player_search', 'team_switch', 'settings_update'
        )
        GROUP BY DATE(timestamp), activity_type
        ORDER BY activity_date DESC, daily_count DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("📈 SMS-Triggering Activity Trends (Last 30 Days)")
        print("=" * 50)
        
        # Group by date
        daily_totals = defaultdict(int)
        activity_trends = defaultdict(list)
        
        for row in results:
            date, activity_type, count = row
            daily_totals[date] += count
            activity_trends[activity_type].append((date, count))
        
        # Show daily totals
        print("📅 Daily Activity Totals:")
        for date in sorted(daily_totals.keys(), reverse=True)[:10]:
            print(f"   {date}: {daily_totals[date]:,} activities")
        
        print("\n🎯 Top Activity Types by Volume:")
        activity_totals = defaultdict(int)
        for activity_type, trends in activity_trends.items():
            total = sum(count for _, count in trends)
            activity_totals[activity_type] = total
        
        for activity_type, total in sorted(activity_totals.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {activity_type}: {total:,} activities")
        
        return {
            'daily_totals': dict(daily_totals),
            'activity_trends': dict(activity_trends)
        }
        
    except Exception as e:
        print(f"❌ Error analyzing trends: {e}")
        return None
    finally:
        if conn:
            conn.close()

def analyze_pickup_game_sms_usage():
    """Analyze pickup game SMS usage specifically"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Query pickup game activities
        query = """
        SELECT 
            pg.description as game_description,
            c.name as club_name,
            pg.game_date,
            pg.players_committed,
            pg.players_requested,
            COUNT(ual.id) as notification_count
        FROM user_activity_logs ual
        LEFT JOIN pickup_games pg ON ual.details::json->>'game_id' = pg.id::text
        LEFT JOIN clubs c ON pg.club_id = c.id
        WHERE ual.timestamp >= NOW() - INTERVAL '30 days'
        AND ual.activity_type IN ('pickup_game_join', 'pickup_game_leave')
        AND pg.id IS NOT NULL
        GROUP BY pg.id, pg.description, c.name, pg.game_date, pg.players_committed, pg.players_requested
        ORDER BY notification_count DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("🎾 Top Pickup Games by SMS Notifications (Last 30 Days)")
        print("=" * 60)
        
        for row in results:
            description, club_name, game_date, committed, requested, count = row
            print(f"🔹 {description}")
            print(f"   🏢 Club: {club_name}")
            print(f"   📅 Date: {game_date}")
            print(f"   👥 Players: {committed}/{requested}")
            print(f"   📱 Notifications: {count}")
            print()
        
        return results
        
    except Exception as e:
        print(f"❌ Error analyzing pickup games: {e}")
        return None
    finally:
        if conn:
            conn.close()

def estimate_sms_costs():
    """Estimate SMS costs based on activity patterns"""
    print("💰 SMS Cost Estimation")
    print("=" * 30)
    
    # Twilio pricing (as of 2024)
    SMS_COST_US = 0.0075  # $0.0075 per SMS in US
    SMS_COST_CANADA = 0.0075  # $0.0075 per SMS in Canada
    MMS_COST_US = 0.02  # $0.02 per MMS in US
    
    # Estimate based on activity logs
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Count different types of activities that trigger SMS
        query = """
        SELECT 
            activity_type,
            action,
            COUNT(*) as count
        FROM user_activity_logs 
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        AND activity_type IN (
            'team_notification_sent', 'lineup_message_sent', 
            'pickup_game_join', 'pickup_game_leave',
            'registration_successful', 'registration_failed'
        )
        GROUP BY activity_type, action
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        total_estimated_sms = 0
        cost_breakdown = {}
        
        for activity_type, action, count in results:
            # Estimate SMS count based on activity type
            if activity_type == 'team_notification_sent':
                # Team notifications go to multiple team members
                estimated_sms = count * 8  # Assume average 8 team members
            elif activity_type == 'lineup_message_sent':
                # Lineup messages go to team members
                estimated_sms = count * 6  # Assume average 6 team members
            elif activity_type in ['pickup_game_join', 'pickup_game_leave']:
                # Pickup game notifications go to all participants
                estimated_sms = count * 4  # Assume average 4 participants
            elif activity_type in ['registration_successful', 'registration_failed']:
                # Registration notifications go to admin only
                estimated_sms = count * 1
            else:
                estimated_sms = count
            
            total_estimated_sms += estimated_sms
            cost_breakdown[f"{activity_type}_{action or 'default'}"] = {
                'count': count,
                'estimated_sms': estimated_sms,
                'estimated_cost': estimated_sms * SMS_COST_US
            }
        
        print(f"📊 Estimated SMS Volume (Last 30 Days): {total_estimated_sms:,}")
        print(f"💰 Estimated Cost (US): ${total_estimated_sms * SMS_COST_US:.2f}")
        print(f"💰 Estimated Cost (Canada): ${total_estimated_sms * SMS_COST_CANADA:.2f}")
        print()
        
        print("📋 Cost Breakdown by Activity Type:")
        for activity, data in sorted(cost_breakdown.items(), key=lambda x: x[1]['estimated_cost'], reverse=True):
            print(f"   {activity}: {data['count']} activities → {data['estimated_sms']} SMS → ${data['estimated_cost']:.2f}")
        
        return {
            'total_estimated_sms': total_estimated_sms,
            'estimated_cost_us': total_estimated_sms * SMS_COST_US,
            'estimated_cost_canada': total_estimated_sms * SMS_COST_CANADA,
            'cost_breakdown': cost_breakdown
        }
        
    except Exception as e:
        print(f"❌ Error estimating costs: {e}")
        return None
    finally:
        if conn:
            conn.close()

def generate_recommendations():
    """Generate cost optimization recommendations"""
    print("\n💡 SMS Cost Optimization Recommendations")
    print("=" * 50)
    
    recommendations = [
        "1. 📱 Implement SMS Opt-in/Opt-out System",
        "   - Allow users to disable SMS notifications in settings",
        "   - Default to email notifications for non-critical updates",
        "",
        "2. 🎯 Optimize Team Notification Frequency",
        "   - Limit team notifications to once per day per team",
        "   - Use email for detailed updates, SMS for urgent alerts only",
        "",
        "3. 📊 Implement Smart Batching",
        "   - Batch multiple updates into single SMS messages",
        "   - Use digest notifications instead of individual alerts",
        "",
        "4. 🔔 Prioritize Notification Types",
        "   - SMS: Match reminders, urgent team updates, security alerts",
        "   - Email: General updates, detailed reports, non-urgent info",
        "",
        "5. 📈 Add Usage Analytics Dashboard",
        "   - Track SMS costs per team/player in real-time",
        "   - Set monthly SMS budgets per team",
        "   - Alert when approaching cost thresholds",
        "",
        "6. 🎾 Optimize Pickup Game Notifications",
        "   - Only notify when game is close to capacity",
        "   - Use push notifications instead of SMS for mobile app users",
        "",
        "7. 🔄 Implement Notification Preferences",
        "   - Let users choose notification frequency",
        "   - Allow team captains to set notification policies",
        "   - Create notification templates with different verbosity levels"
    ]
    
    for rec in recommendations:
        print(rec)

def main():
    """Main analysis function"""
    print("🔍 Rally SMS Usage Analysis")
    print("=" * 40)
    print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all analyses
    activity_data = analyze_sms_usage_by_activity_type()
    team_data = analyze_sms_usage_by_teams()
    user_data = analyze_sms_usage_by_users()
    trends_data = analyze_sms_usage_trends()
    pickup_data = analyze_pickup_game_sms_usage()
    cost_data = estimate_sms_costs()
    
    # Generate recommendations
    generate_recommendations()
    
    # Save results to file
    results = {
        'analysis_date': datetime.now().isoformat(),
        'activity_data': activity_data,
        'team_data': team_data,
        'user_data': user_data,
        'trends_data': trends_data,
        'pickup_data': pickup_data,
        'cost_data': cost_data
    }
    
    output_file = f"sms_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main()
