#!/usr/bin/env python3
"""
Test script to verify lineup escrow access functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import SessionLocal, LineupEscrow
from app.services.lineup_escrow_service import LineupEscrowService

def test_escrow_access():
    """Test escrow access with and without contact parameter"""
    
    print("🧪 Testing Lineup Escrow Access Functionality")
    print("=" * 50)
    
    # Test escrow token
    escrow_token = "escrow_E6gcE-qTCtLjO0kbr9Agiw"
    contact_info = "7732138911"
    
    try:
        with SessionLocal() as db_session:
            escrow_service = LineupEscrowService(db_session)
            
            # Test 1: Check if escrow exists
            print(f"✅ Test 1: Checking if escrow token exists...")
            escrow = db_session.query(LineupEscrow).filter(
                LineupEscrow.escrow_token == escrow_token
            ).first()
            
            if escrow:
                print(f"   ✅ Escrow found: ID {escrow.id}, Status: {escrow.status}")
                print(f"   ✅ Recipient Contact: {escrow.recipient_contact}")
                print(f"   ✅ Contact Type: {escrow.contact_type}")
            else:
                print(f"   ❌ Escrow not found")
                return
            
            # Test 2: Test with correct contact
            print(f"\n✅ Test 2: Testing with correct contact...")
            result = escrow_service.get_escrow_details(escrow_token, contact_info)
            
            if result["success"]:
                print(f"   ✅ Access granted with correct contact")
                print(f"   ✅ Both lineups visible: {result['both_lineups_visible']}")
                print(f"   ✅ Status: {result['escrow']['status']}")
            else:
                print(f"   ❌ Access denied: {result.get('error')}")
            
            # Test 3: Test with wrong contact
            print(f"\n✅ Test 3: Testing with wrong contact...")
            wrong_contact = "wrong@email.com"
            result = escrow_service.get_escrow_details(escrow_token, wrong_contact)
            
            if not result["success"]:
                print(f"   ✅ Access correctly denied with wrong contact")
                print(f"   ✅ Error: {result.get('error')}")
            else:
                print(f"   ⚠️  Access granted with wrong contact (this might be a security issue)")
            
            # Test 4: Test with empty contact
            print(f"\n✅ Test 4: Testing with empty contact...")
            result = escrow_service.get_escrow_details(escrow_token, "")
            
            if not result["success"]:
                print(f"   ✅ Access correctly denied with empty contact")
                print(f"   ✅ Error: {result.get('error')}")
            else:
                print(f"   ⚠️  Access granted with empty contact (this might be a security issue)")
            
            # Test 5: Test with non-existent token
            print(f"\n✅ Test 5: Testing with non-existent token...")
            fake_token = "escrow_fake_token_123"
            result = escrow_service.get_escrow_details(fake_token, contact_info)
            
            if not result["success"]:
                print(f"   ✅ Access correctly denied with fake token")
                print(f"   ✅ Error: {result.get('error')}")
            else:
                print(f"   ⚠️  Access granted with fake token (this would be a security issue)")
            
            print(f"\n🎉 All tests completed!")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")

if __name__ == "__main__":
    test_escrow_access() 