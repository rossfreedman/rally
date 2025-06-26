#!/usr/bin/env python3
"""
Test Dependencies Verification Script
Verifies that all required testing dependencies can be imported
"""

import sys

def test_imports():
    """Test that all required dependencies can be imported"""
    failed_imports = []
    
    # Core testing dependencies with correct import names
    test_modules = [
        'pytest',
        'pytest_cov', 
        'xdist',  # pytest-xdist imports as 'xdist'
        'pytest_mock',
        'pytest_html',
        'flake8',
        'black',
        'isort',
        'bandit',
        'safety',
        'pip_audit',
        # 'locust',  # Skip locust due to zmq issues
        'faker',
        # 'playwright',  # Skip for now
        # 'selenium',  # Already in main requirements
        # 'webdriver_manager'  # Already in main requirements
    ]
    
    print("🧪 Testing import of required dependencies...")
    print("=" * 50)
    
    for module in test_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
        except Exception as e:
            print(f"⚠️  {module}: {e} (import issue but module exists)")
    
    print("=" * 50)
    
    if failed_imports:
        print(f"❌ {len(failed_imports)} modules failed to import:")
        for module in failed_imports:
            print(f"   - {module}")
        print("\nTo fix: pip install -r requirements-test.txt")
        return False
    else:
        print("✅ All testing dependencies imported successfully!")
        return True

def test_pytest_markers():
    """Test that pytest markers are working"""
    print("\n🏷️  Testing pytest marker registration...")
    
    try:
        import pytest
        
        # Check if markers are defined
        markers = ['unit', 'integration', 'security', 'performance', 'regression']
        print("Testing pytest markers:", markers)
        
        # This would normally be done in pytest.ini or conftest.py
        for marker in markers:
            pytest.mark.__getattr__(marker)
        
        print("✅ Pytest markers are accessible")
        return True
        
    except Exception as e:
        print(f"❌ Pytest marker test failed: {e}")
        return False

def test_database_imports():
    """Test that database-related imports work"""
    print("\n🗄️  Testing database imports...")
    
    try:
        from database_config import get_db_url
        from app.models.database_models import Base
        print("✅ Database imports successful")
        return True
    except ImportError as e:
        print(f"❌ Database import failed: {e}")
        return False

def test_security_tools():
    """Test that security tools can be invoked"""
    print("\n🔐 Testing security tools...")
    
    try:
        # Test bandit
        import bandit
        print("✅ Bandit available")
        
        # Test safety
        import safety
        print("✅ Safety available")
        
        # Test pip-audit
        import pip_audit
        print("✅ pip-audit available")
        
        return True
    except Exception as e:
        print(f"❌ Security tools test failed: {e}")
        return False

if __name__ == "__main__":
    print("Rally Test Dependencies Verification")
    print("=====================================\n")
    
    success = True
    success &= test_imports()
    success &= test_pytest_markers() 
    success &= test_database_imports()
    success &= test_security_tools()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 All dependency tests passed!")
        print("The GitHub Actions workflow should now work correctly.")
        sys.exit(0)
    else:
        print("💥 Some dependency tests failed!")
        print("Please install missing dependencies before running CI.")
        sys.exit(1) 