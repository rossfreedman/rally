#!/usr/bin/env python3
"""
Check if a specific escrow token exists in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import SessionLocal
from app.models.database_models import LineupEscrow

def check_escrow_token(token):
    """Check if escrow token exists and get details"""
    
    print(f"🔍 Checking escrow token: {token}")
    print("=" * 50)
    
    try:
        with SessionLocal() as db_session:
            # Check if token exists
            escrow = db_session.query(LineupEscrow).filter(
                LineupEscrow.escrow_token == token
            ).first()
            
            if escrow:
                print("✅ Escrow token found!")
                print(f"   ID: {escrow.id}")
                print(f"   Status: {escrow.status}")
                print(f"   Initiator User ID: {escrow.initiator_user_id}")
                print(f"   Recipient Name: {escrow.recipient_name}")
                print(f"   Recipient Contact: {escrow.recipient_contact}")
                print(f"   Contact Type: {escrow.contact_type}")
                print(f"   Created At: {escrow.created_at}")
                print(f"   Expires At: {escrow.expires_at}")
                print(f"   Initiator Submitted At: {escrow.initiator_submitted_at}")
                print(f"   Recipient Submitted At: {escrow.recipient_submitted_at}")
                print(f"   Has Initiator Lineup: {'Yes' if escrow.initiator_lineup else 'No'}")
                print(f"   Has Recipient Lineup: {'Yes' if escrow.recipient_lineup else 'No'}")
                
                # Check if expired
                from datetime import datetime
                if escrow.expires_at and datetime.utcnow() > escrow.expires_at:
                    print("⚠️  ESCROW IS EXPIRED!")
                else:
                    print("✅ Escrow is still valid")
                    
            else:
                print("❌ Escrow token not found in database")
                
                # Check for similar tokens
                print("\n🔍 Checking for similar tokens...")
                similar_tokens = db_session.query(LineupEscrow).filter(
                    LineupEscrow.escrow_token.like(f"%{token[:10]}%")
                ).limit(5).all()
                
                if similar_tokens:
                    print("Found similar tokens:")
                    for similar in similar_tokens:
                        print(f"   {similar.escrow_token} (ID: {similar.id}, Status: {similar.status})")
                else:
                    print("No similar tokens found")
                
                # Check total escrow count
                total_count = db_session.query(LineupEscrow).count()
                print(f"\n📊 Total escrow sessions in database: {total_count}")
                
    except Exception as e:
        print(f"❌ Error checking escrow token: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_escrow_token.py <escrow_token>")
        sys.exit(1)
    
    token = sys.argv[1]
    check_escrow_token(token) 