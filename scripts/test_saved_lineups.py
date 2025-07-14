#!/usr/bin/env python3
"""
Test script to debug saved lineups functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import SessionLocal, SavedLineup, User
from database_config import get_db_url

def test_saved_lineups():
    """Test saved lineups functionality"""
    print("🔍 Testing Saved Lineups Functionality")
    print("=" * 50)
    
    with SessionLocal() as session:
        # Check all saved lineups
        lineups = session.query(SavedLineup).all()
        print(f"📊 Total saved lineups: {len(lineups)}")
        
        for lineup in lineups:
            print(f"\n📋 Lineup ID: {lineup.id}")
            print(f"   User ID: {lineup.user_id}")
            print(f"   Team ID: {lineup.team_id}")
            print(f"   Name: {lineup.lineup_name}")
            print(f"   Active: {lineup.is_active}")
            print(f"   Created: {lineup.created_at}")
            print(f"   Updated: {lineup.updated_at}")
            
            # Check if user exists
            user = session.query(User).filter(User.id == lineup.user_id).first()
            if user:
                print(f"   User Email: {user.email}")
                print(f"   User Name: {user.first_name} {user.last_name}")
            else:
                print(f"   ❌ User {lineup.user_id} not found!")
        
        # Check for user with email rossfreedman@gmail.com
        print(f"\n🔍 Looking for user: rossfreedman@gmail.com")
        user = session.query(User).filter(User.email == "rossfreedman@gmail.com").first()
        if user:
            print(f"   ✅ Found user ID: {user.id}")
            print(f"   Name: {user.first_name} {user.last_name}")
            
            # Check if this user has any saved lineups
            user_lineups = session.query(SavedLineup).filter(SavedLineup.user_id == user.id).all()
            print(f"   Saved lineups for this user: {len(user_lineups)}")
            
            for lineup in user_lineups:
                print(f"     - Team {lineup.team_id}: {lineup.lineup_name}")
        else:
            print(f"   ❌ User not found!")

if __name__ == "__main__":
    test_saved_lineups() 