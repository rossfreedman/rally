#!/usr/bin/env python3
"""
Simple Incremental Scraping Analysis
===================================

Quick analysis of current match data to demonstrate incremental scraping benefits.
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_engine
from app.models.database_models import MatchScore, League
from sqlalchemy.orm import sessionmaker

def analyze_current_data():
    """Analyze current match data to show incremental scraping benefits"""
    
    print("🎾 Simple Incremental Scraping Analysis")
    print("=" * 50)
    
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    
    try:
        session = Session()
        
        # Get total matches
        total_matches = session.query(MatchScore).count()
        print(f"📊 Total matches in database: {total_matches:,}")
        
        if total_matches == 0:
            print("⚠️  No matches found - incremental scraping not applicable")
            session.close()
            return
        
        # Get leagues
        leagues = session.query(League).all()
        print(f"🏆 Total leagues: {len(leagues)}")
        
        # Analyze by league
        for league in leagues:
            league_matches = session.query(MatchScore)\
                .filter(MatchScore.league_id == league.id)\
                .order_by(MatchScore.match_date.desc())\
                .all()
            
            if not league_matches:
                continue
            
            match_count = len(league_matches)
            latest_match = league_matches[0]
            earliest_match = league_matches[-1]
            
            # Calculate days since latest match
            today = datetime.now().date()
            days_since_latest = (today - latest_match.match_date).days
            
            # Estimate new matches (last 30 days)
            recent_matches = [m for m in league_matches if (today - m.match_date).days <= 30]
            new_matches_estimate = len(recent_matches)
            
            efficiency = (new_matches_estimate / match_count * 100) if match_count > 0 else 0
            
            print(f"\n📈 {league.league_name}:")
            print(f"   Total matches: {match_count:,}")
            print(f"   Latest match: {latest_match.match_date}")
            print(f"   Days since latest: {days_since_latest}")
            print(f"   Recent matches (30 days): {new_matches_estimate}")
            print(f"   Efficiency: {efficiency:.1f}%")
        
        session.close()
        
        # Overall benefits
        print(f"\n💰 BENEFITS OF INCREMENTAL SCRAPING:")
        print("=" * 50)
        
        # Estimate based on typical patterns
        estimated_new_matches = total_matches * 0.05  # Assume 5% new matches
        estimated_savings = total_matches - estimated_new_matches
        
        print(f"🌐 Current approach scrapes: {total_matches:,} matches")
        print(f"🆕 Incremental would scrape: ~{estimated_new_matches:.0f} matches")
        print(f"💾 Requests saved per run: {estimated_savings:.0f}")
        print(f"⏱️  Time saved per run: {estimated_savings * 2 / 3600:.1f} hours")
        print(f"📊 Bandwidth saved: {estimated_savings * 50 / 1024:.1f} MB")
        
        print(f"\n💡 RECOMMENDATION:")
        if total_matches > 1000:
            print("✅ HIGH PRIORITY: Implement incremental scraping")
            print("   - Significant resource savings")
            print("   - Faster scraping times")
            print("   - Reduced risk of rate limiting")
        elif total_matches > 100:
            print("📊 MEDIUM PRIORITY: Consider incremental scraping")
            print("   - Moderate benefits")
            print("   - Worth implementing")
        else:
            print("⚠️  LOW PRIORITY: Current approach may be sufficient")
            print("   - Limited data volume")
            print("   - Benefits may be minimal")
    
    except Exception as e:
        print(f"❌ Error analyzing data: {e}")

if __name__ == "__main__":
    analyze_current_data()
    print(f"\n✅ Analysis complete!") 