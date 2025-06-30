#!/usr/bin/env python3
"""
Emergency Production Rollback Script
====================================

Use this script to quickly rollback production to the last known good state
when issues are discovered after deployment.
"""

import subprocess
import sys
import os
from datetime import datetime

def check_prerequisites():
    """Check that we can perform a rollback"""
    print("🔍 Checking Rollback Prerequisites...")
    
    # Check if we're in Rally project directory
    if not os.path.exists('requirements.txt') or not os.path.exists('server.py'):
        print("❌ Not in Rally project directory")
        return False
    
    # Check git status
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("❌ You have uncommitted changes. Please commit or stash them.")
        return False
    
    print("✅ Prerequisites checked")
    return True

def get_current_branch():
    """Get the current git branch"""
    result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
    return result.stdout.strip()

def get_last_commits():
    """Get the last few commits for review"""
    print("📋 Recent commits on main branch:")
    result = subprocess.run(['git', 'log', '--oneline', '-10', 'main'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines):
            status = "→ CURRENT" if i == 0 else f"  {i+1}."
            print(f"   {status} {line}")
    return lines

def confirm_rollback():
    """Get explicit confirmation for rollback"""
    print("\n🚨 PRODUCTION ROLLBACK CONFIRMATION")
    print("=" * 60)
    print("This will rollback the LIVE production environment")
    print("This affects real users immediately!")
    print()
    
    recent_commits = get_last_commits()
    
    print("\nRollback options:")
    print("1. Revert last commit (safest)")
    print("2. Reset to specific commit (more dangerous)")
    print("3. Cancel rollback")
    
    choice = input("\nChoose rollback method (1/2/3): ")
    
    if choice == '1':
        return 'revert_last'
    elif choice == '2':
        commit_hash = input("Enter commit hash to reset to: ")
        if len(commit_hash) >= 7:
            return f'reset_to:{commit_hash}'
        else:
            print("❌ Invalid commit hash")
            return None
    else:
        return None

def revert_last_commit():
    """Revert the last commit on main"""
    print("🔄 Reverting last commit...")
    
    try:
        # Switch to main
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        
        # Revert the last commit
        subprocess.run(['git', 'revert', 'HEAD', '--no-edit'], check=True)
        
        # Push the revert
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print("✅ Successfully reverted last commit")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to revert commit: {e}")
        return False

def reset_to_commit(commit_hash):
    """Reset main to a specific commit (dangerous)"""
    print(f"🔄 Resetting to commit {commit_hash}...")
    
    response = input("⚠️  This is DANGEROUS and will lose commits. Type 'yes' to confirm: ")
    if response != 'yes':
        print("Rollback cancelled")
        return False
    
    try:
        # Switch to main
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        
        # Reset to commit
        subprocess.run(['git', 'reset', '--hard', commit_hash], check=True)
        
        # Force push (dangerous!)
        subprocess.run(['git', 'push', '--force-with-lease', 'origin', 'main'], check=True)
        
        print(f"✅ Successfully reset to {commit_hash}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to reset to commit: {e}")
        return False

def verify_rollback():
    """Verify the rollback was successful"""
    print("🔍 Verifying rollback...")
    
    try:
        import requests
        response = requests.get("https://rally.up.railway.app/mobile", 
                              allow_redirects=False, timeout=10)
        
        if response.status_code in [200, 302]:
            print("✅ Production environment is responding")
            return True
        else:
            print(f"⚠️  Production returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to verify rollback: {e}")
        return False

def run_post_rollback_verification():
    """Run verification after rollback"""
    print("🧪 Running post-rollback verification...")
    
    if os.path.exists('deployment/test_production_session_refresh.py'):
        try:
            result = subprocess.run([sys.executable, 'deployment/test_production_session_refresh.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Post-rollback verification passed")
                return True
            else:
                print("❌ Post-rollback verification failed:")
                print(result.stdout)
                return False
        except Exception as e:
            print(f"❌ Error running verification: {e}")
            return False
    else:
        print("⚠️  No verification tests found")
        return True

def provide_rollback_summary():
    """Provide information about the rollback"""
    print("\n🎯 ROLLBACK COMPLETE")
    print("=" * 60)
    print("🌐 Production URL: https://rally.up.railway.app")
    print("✅ Status: Rollback deployed")
    print()
    print("📊 Next steps:")
    print("   □ Monitor production for stability")
    print("   □ Notify stakeholders of rollback")
    print("   □ Investigate root cause of issues")
    print("   □ Fix issues before next deployment")
    print("   □ Update staging with fixes")
    print()
    print("🔧 Once fixed:")
    print("   python deployment/deploy_staging.py   # Test fixes")
    print("   python deployment/deploy_production.py # Re-deploy when ready")

def main():
    print("🚨 Rally Emergency Production Rollback")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        return 1
    
    # Get rollback confirmation and method
    rollback_method = confirm_rollback()
    if not rollback_method:
        print("Rollback cancelled")
        return 0
    
    # Perform rollback
    success = False
    if rollback_method == 'revert_last':
        success = revert_last_commit()
    elif rollback_method.startswith('reset_to:'):
        commit_hash = rollback_method.split(':', 1)[1]
        success = reset_to_commit(commit_hash)
    
    if not success:
        print("❌ ROLLBACK FAILED!")
        print("Manual intervention may be required")
        return 1
    
    # Verify rollback
    if not verify_rollback():
        print("⚠️  Rollback deployed but verification failed")
        print("Check production manually")
    
    # Run post-rollback verification
    run_post_rollback_verification()
    
    # Provide summary
    provide_rollback_summary()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 