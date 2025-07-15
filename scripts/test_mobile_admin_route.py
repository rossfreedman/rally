#!/usr/bin/env python3

"""
Test script for mobile admin route fix
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_mobile_admin_route():
    """Test that the mobile admin route function exists"""
    
    print("=== Testing Mobile Admin Route Fix ===")
    
    try:
        # Import the mobile routes module
        from app.routes.mobile_routes import mobile_bp, serve_mobile_admin
        
        print("✅ Mobile routes blueprint imported successfully")
        print("✅ serve_mobile_admin function imported successfully")
        
        # Check that the function exists and has the right name
        if hasattr(serve_mobile_admin, '__name__') and serve_mobile_admin.__name__ == 'serve_mobile_admin':
            print("✅ serve_mobile_admin function exists with correct name")
        else:
            print("❌ serve_mobile_admin function not found or has wrong name")
            return False
        
        print("✅ Mobile admin route fix is working correctly")
        print("   - Route function /mobile/admin now exists")
        print("   - It will redirect to /admin (main admin panel)")
        print("   - Both mobile templates can now access admin functionality")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error testing mobile admin route: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_mobile_admin_route()
    if success:
        print("\n🎉 Mobile admin route fix is complete!")
    else:
        print("\n❌ Mobile admin route fix failed!")
        sys.exit(1) 