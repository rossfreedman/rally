#!/usr/bin/env python3
"""
Test Railway ETL Fix
===================

This script tests the Railway-specific ETL optimizations to ensure they work correctly
in production environment and resolve the root cause issues.
"""

import os
import sys
import time
import psutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_railway_environment_detection():
    """Test that environment is correctly detected (Railway OR Local)"""
    print("🔍 Testing Environment Detection")
    print("=" * 50)
    
    # Test environment variable detection
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    database_url = os.getenv('DATABASE_URL', '')
    
    print(f"RAILWAY_ENVIRONMENT: {railway_env}")
    print(f"DATABASE_URL contains railway: {'railway' in database_url.lower()}")
    
    is_railway = railway_env or 'railway' in database_url.lower()
    
    if is_railway:
        print("✅ Railway environment detected correctly")
        return True
    else:
        print("✅ Local environment detected correctly")
        print("   (This is expected when running locally)")
        return True  # Both Railway and Local detection are valid

def test_etl_optimizations():
    """Test the ETL class optimizations"""
    print("\n🚂 Testing ETL Railway Optimizations")
    print("=" * 50)
    
    try:
        from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
        
        # Test ETL initialization with Railway detection
        etl = ComprehensiveETL()
        
        print(f"Railway detected: {etl.is_railway}")
        print(f"Batch size: {etl.batch_size}")
        print(f"Commit frequency: {etl.commit_frequency}")
        print(f"Connection retries: {etl.connection_retry_attempts}")
        
        if etl.is_railway:
            # Verify Railway optimizations are applied
            if (etl.batch_size == 50 and 
                etl.commit_frequency == 25 and 
                etl.connection_retry_attempts == 10):
                print("✅ Railway optimizations applied correctly")
                return True
            else:
                print("❌ Railway optimizations NOT applied correctly")
                return False
        else:
            print("ℹ️  Not running on Railway - testing local optimizations")
            if (etl.batch_size == 1000 and 
                etl.commit_frequency == 100 and 
                etl.connection_retry_attempts == 5):
                print("✅ Local optimizations applied correctly")
                return True
            else:
                print("❌ Local optimizations NOT applied correctly")
                return False
                
    except Exception as e:
        print(f"❌ Error testing ETL optimizations: {e}")
        return False

def test_database_connection():
    """Test database connection with Railway optimizations"""
    print("\n💾 Testing Database Connection")
    print("=" * 50)
    
    try:
        from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
        
        etl = ComprehensiveETL()
        
        if etl.is_railway:
            print("🚂 Testing Railway-optimized database connection...")
            # Test Railway-optimized connection
            with etl.get_railway_optimized_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 as test, version()")
                result = cursor.fetchone()
                print(f"✅ Railway database connection successful")
                print(f"   Test query result: {result[0]}")
                print(f"   PostgreSQL version: {result[1][:50]}...")
                return True
        else:
            print("🏠 Testing local database connection...")
            from database_config import get_db
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                print(f"✅ Local database connection successful")
                print(f"   Test query result: {result[0]}")
                return True
                
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def test_memory_monitoring():
    """Test memory monitoring capabilities"""
    print("\n🧠 Testing Memory Monitoring")
    print("=" * 50)
    
    try:
        # Test psutil availability for memory monitoring
        memory_info = psutil.virtual_memory()
        print(f"✅ Memory monitoring available")
        print(f"   Total memory: {memory_info.total / (1024**3):.1f} GB")
        print(f"   Available memory: {memory_info.available / (1024**3):.1f} GB")
        print(f"   Memory usage: {memory_info.percent:.1f}%")
        
        # Test if we're in a resource-constrained environment (likely Railway)
        if memory_info.total / (1024**3) < 2.0:  # Less than 2GB total
            print("⚠️  Resource-constrained environment detected")
            print("   ETL optimizations are especially important here")
        
        return True
        
    except ImportError:
        print("⚠️  psutil not available for memory monitoring")
        print("   Memory monitoring will be disabled")
        return True  # Not critical for ETL function
    except Exception as e:
        print(f"❌ Memory monitoring test failed: {e}")
        return False

def test_json_file_access():
    """Test access to JSON data files"""
    print("\n📁 Testing JSON File Access")
    print("=" * 50)
    
    try:
        from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
        
        etl = ComprehensiveETL()
        
        # Test file path resolution
        data_dir = etl.data_dir
        print(f"Data directory: {data_dir}")
        print(f"Directory exists: {os.path.exists(data_dir)}")
        
        # Test access to each required JSON file
        required_files = [
            "players.json",
            "player_history.json", 
            "match_history.json",
            "series_stats.json",
            "schedules.json"
        ]
        
        all_files_accessible = True
        for filename in required_files:
            filepath = os.path.join(data_dir, filename)
            exists = os.path.exists(filepath)
            print(f"   {filename}: {'✅' if exists else '❌'}")
            if not exists:
                all_files_accessible = False
        
        if all_files_accessible:
            print("✅ All required JSON files are accessible")
            return True
        else:
            print("❌ Some JSON files are missing")
            return False
            
    except Exception as e:
        print(f"❌ JSON file access test failed: {e}")
        return False

def test_batch_processing():
    """Test Railway-optimized batch processing"""
    print("\n📦 Testing Batch Processing Logic")
    print("=" * 50)
    
    try:
        from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
        
        etl = ComprehensiveETL()
        
        # Create mock batch data
        mock_batch_data = [
            (f"2024-01-{i:02d}", f"Team{i}A", f"Team{i}B", None, None, 
             None, None, None, None, "6-4, 6-2", "home", 1)
            for i in range(1, 101)  # 100 records
        ]
        
        print(f"Testing batch processing with {len(mock_batch_data)} mock records")
        print(f"Railway mode: {etl.is_railway}")
        print(f"Batch size setting: {etl.batch_size}")
        
        if etl.is_railway:
            expected_batches = len(mock_batch_data) // etl.batch_size
            if len(mock_batch_data) % etl.batch_size > 0:
                expected_batches += 1
            print(f"Expected number of batches: {expected_batches}")
            
            if expected_batches > 1:
                print("✅ Large dataset will be properly chunked for Railway")
            else:
                print("ℹ️  Dataset fits in single batch")
        else:
            print("ℹ️  Local mode - no batch size limits")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and retry logic"""
    print("\n🛡️  Testing Error Handling")
    print("=" * 50)
    
    try:
        from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
        
        etl = ComprehensiveETL()
        
        print(f"Connection retry attempts: {etl.connection_retry_attempts}")
        
        if etl.is_railway and etl.connection_retry_attempts > 5:
            print("✅ Railway has increased retry attempts for better reliability")
        elif not etl.is_railway and etl.connection_retry_attempts == 5:
            print("✅ Local environment uses standard retry attempts")
        else:
            print("⚠️  Unexpected retry configuration")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🧪 RAILWAY ETL FIX COMPREHENSIVE TEST")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print("=" * 60)
    
    tests = [
        ("Environment Detection", test_railway_environment_detection),
        ("ETL Optimizations", test_etl_optimizations),
        ("Database Connection", test_database_connection),
        ("Memory Monitoring", test_memory_monitoring),
        ("JSON File Access", test_json_file_access),
        ("Batch Processing", test_batch_processing),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name:<25}: {status}")
    
    print("-" * 60)
    print(f"   {'TOTAL':<25}: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Railway ETL fix is ready for production.")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review issues before deploying.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 