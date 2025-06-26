#!/usr/bin/env python3
"""
Rally Milestone Deployment Script

This comprehensive script performs a complete deployment milestone with verification:
1. Check deployment status and deploy changes to git (staging or production)
2. Ensure local and Railway are in sync
3. Verify databases are completely in sync (schema and data perspective)
4. Backup code using scripts/cb.py

Usage:
    python scripts/milestone.py                    # Interactive mode
    python scripts/milestone.py --branch staging   # Deploy to staging
    python scripts/milestone.py --branch production # Deploy to production
    python scripts/milestone.py --skip-backup      # Skip backup step
    python scripts/milestone.py --quick           # Skip confirmations
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class MilestoneDeployment:
    def __init__(self, args):
        self.args = args
        self.start_time = time.time()
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        
        # Results tracking
        self.results = {
            "deployment_status": None,
            "git_deployment": None,
            "database_sync": None,
            "backup": None,
            "overall_success": False
        }
        
    def print_header(self):
        """Print milestone header"""
        print("🚀" + "=" * 78 + "🚀")
        print("🎯 RALLY MILESTONE DEPLOYMENT")
        print("🚀" + "=" * 78 + "🚀")
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📍 Target: {self.args.branch}")
        print(f"🏠 Project: {self.project_root}")
        print()

    def run_subprocess(self, command, cwd=None, capture_output=True):
        """Run subprocess with error handling"""
        try:
            if isinstance(command, str):
                command = command.split()
            
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=capture_output,
                text=True,
                check=False
            )
            return result
        except Exception as e:
            logger.error(f"Error running command {command}: {e}")
            return None

    def step_1_check_deployment_status(self):
        """Step 1: Check deployment status using existing script"""
        print("🔍 STEP 1: Checking Deployment Status")
        print("-" * 50)
        
        try:
            # Run the deployment status checker
            result = self.run_subprocess([
                sys.executable, 
                str(self.script_dir / "check_deployment_status.py")
            ])
            
            if result and result.returncode == 0:
                print("✅ Deployment status: IN SYNC")
                self.results["deployment_status"] = {"status": "in_sync", "message": "Local and remote are synchronized"}
                return True
            else:
                print("⚠️  Deployment status: OUT OF SYNC")
                self.results["deployment_status"] = {"status": "out_of_sync", "message": "Changes need to be committed/pushed"}
                
                if not self.args.quick:
                    proceed = input("\n🤔 Continue with deployment of uncommitted changes? [y/N]: ")
                    if proceed.lower() != 'y':
                        print("❌ Deployment cancelled by user")
                        return False
                
                return True
                
        except Exception as e:
            print(f"❌ Error checking deployment status: {e}")
            self.results["deployment_status"] = {"status": "error", "message": str(e)}
            return False

    def step_2_git_deployment(self):
        """Step 2: Deploy changes to git"""
        print("\n🚀 STEP 2: Git Deployment")
        print("-" * 50)
        
        try:
            # Check current branch
            current_branch = self.run_subprocess(["git", "branch", "--show-current"])
            if current_branch:
                current_branch = current_branch.stdout.strip()
                print(f"📍 Current branch: {current_branch}")
            
            # Check for uncommitted changes
            status_result = self.run_subprocess(["git", "status", "--porcelain"])
            if status_result and status_result.stdout.strip():
                print("📝 Found uncommitted changes")
                
                if not self.args.quick:
                    commit_msg = input("📝 Enter commit message (or press Enter for auto): ").strip()
                    if not commit_msg:
                        commit_msg = f"milestone: Deploy changes to {self.args.branch} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                else:
                    commit_msg = f"milestone: Deploy changes to {self.args.branch} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                # Add all changes
                print("📦 Staging all changes...")
                add_result = self.run_subprocess(["git", "add", "."])
                if not add_result or add_result.returncode != 0:
                    raise Exception("Failed to stage changes")
                
                # Commit changes
                print(f"💾 Committing: {commit_msg}")
                commit_result = self.run_subprocess(["git", "commit", "-m", commit_msg])
                if not commit_result or commit_result.returncode != 0:
                    raise Exception("Failed to commit changes")
            
            # Determine target branch
            if self.args.branch == "staging":
                target_branch = "staging"
            else:
                target_branch = "main"  # Production goes to main
            
            # Switch to target branch if needed
            if current_branch != target_branch:
                print(f"🔄 Switching to {target_branch} branch...")
                checkout_result = self.run_subprocess(["git", "checkout", target_branch])
                if not checkout_result or checkout_result.returncode != 0:
                    # Try to create the branch if it doesn't exist
                    print(f"📦 Creating {target_branch} branch...")
                    create_result = self.run_subprocess(["git", "checkout", "-b", target_branch])
                    if not create_result or create_result.returncode != 0:
                        raise Exception(f"Failed to create/switch to {target_branch}")
            
            # Push to remote
            print(f"🚀 Pushing to origin/{target_branch}...")
            push_result = self.run_subprocess(["git", "push", "origin", target_branch])
            if not push_result or push_result.returncode != 0:
                # Try with upstream if it's a new branch
                push_result = self.run_subprocess(["git", "push", "--set-upstream", "origin", target_branch])
                if not push_result or push_result.returncode != 0:
                    raise Exception("Failed to push to remote")
            
            print(f"✅ Successfully deployed to {target_branch}")
            self.results["git_deployment"] = {
                "status": "success", 
                "branch": target_branch,
                "message": f"Deployed to {target_branch}"
            }
            return True
            
        except Exception as e:
            print(f"❌ Git deployment failed: {e}")
            self.results["git_deployment"] = {"status": "error", "message": str(e)}
            return False

    def step_3_verify_database_sync(self):
        """Step 3: Verify database sync"""
        print("\n🗄️  STEP 3: Database Sync Verification")
        print("-" * 50)
        
        try:
            # Run database comparison script
            print("🔍 Comparing local and Railway databases...")
            compare_result = self.run_subprocess([
                sys.executable,
                str(self.script_dir / "compare_databases.py")
            ])
            
            if compare_result:
                if compare_result.returncode == 0:
                    print("✅ Databases are identical!")
                    self.results["database_sync"] = {
                        "status": "identical",
                        "message": "Local and Railway databases are in sync"
                    }
                    return True
                else:
                    print("⚠️  Database differences detected!")
                    self.results["database_sync"] = {
                        "status": "differences",
                        "message": "Databases have schema or data differences"
                    }
                    
                    if not self.args.quick:
                        print("\n🤔 Database sync options:")
                        print("1. Continue anyway (differences may be expected)")
                        print("2. View detailed comparison report")
                        print("3. Cancel milestone")
                        
                        choice = input("Select option [1/2/3]: ").strip()
                        
                        if choice == "2":
                            # Show recent comparison report
                            reports = list(self.project_root.glob("database_comparison_*.json"))
                            if reports:
                                latest_report = max(reports, key=lambda x: x.stat().st_mtime)
                                print(f"\n📄 Latest comparison report: {latest_report}")
                                
                                view_report = input("View report? [y/N]: ").strip()
                                if view_report.lower() == 'y':
                                    with open(latest_report) as f:
                                        report_data = json.load(f)
                                        self._print_db_summary(report_data)
                        
                        elif choice == "3":
                            print("❌ Milestone cancelled by user")
                            return False
                    
                    # Continue with differences (option 1 or quick mode)
                    print("⚠️  Continuing with database differences...")
                    return True
            else:
                raise Exception("Failed to run database comparison")
                
        except Exception as e:
            print(f"❌ Database sync verification failed: {e}")
            self.results["database_sync"] = {"status": "error", "message": str(e)}
            return False

    def _print_db_summary(self, report_data):
        """Print a summary of database comparison report"""
        print("\n📊 DATABASE COMPARISON SUMMARY")
        print("-" * 40)
        
        schema = report_data["schema_comparison"]["summary"]
        data = report_data["data_comparison"]["summary"]
        
        print(f"Schema identical: {'✅' if schema['schema_identical'] else '❌'}")
        print(f"Data identical: {'✅' if data['data_identical'] else '❌'}")
        print(f"Tables with differences: {schema.get('tables_with_differences', 0)}")
        print(f"Tables with count differences: {data.get('tables_with_count_differences', 0)}")

    def step_4_backup_code(self):
        """Step 4: Backup code using cb.py"""
        print("\n💾 STEP 4: Code & Database Backup")
        print("-" * 50)
        
        if self.args.skip_backup:
            print("⏭️  Skipping backup (--skip-backup flag)")
            self.results["backup"] = {"status": "skipped", "message": "Backup skipped by user"}
            return True
        
        try:
            print("📦 Creating comprehensive backup...")
            
            # Run cb.py backup script
            backup_result = self.run_subprocess([
                sys.executable,
                str(self.script_dir / "cb.py"),
                "--max-backups", "5",  # Keep 5 most recent
                "--no-confirm"  # Don't ask for confirmation
            ])
            
            if backup_result and backup_result.returncode == 0:
                print("✅ Backup completed successfully!")
                self.results["backup"] = {
                    "status": "success",
                    "message": "Code and database backup created"
                }
                return True
            else:
                error_msg = backup_result.stderr if backup_result else "Unknown error"
                raise Exception(f"Backup failed: {error_msg}")
                
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            self.results["backup"] = {"status": "error", "message": str(e)}
            
            if not self.args.quick:
                continue_anyway = input("⚠️  Continue without backup? [y/N]: ")
                if continue_anyway.lower() != 'y':
                    return False
            
            print("⚠️  Continuing without backup...")
            return True

    def generate_milestone_report(self):
        """Generate final milestone report"""
        duration = time.time() - self.start_time
        
        print("\n📋 MILESTONE COMPLETION REPORT")
        print("=" * 80)
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target: {self.args.branch}")
        print()
        
        # Check overall success
        critical_steps = ["git_deployment"]  # These must succeed
        optional_steps = ["deployment_status", "database_sync", "backup"]
        
        critical_success = all(
            self.results.get(step, {}).get("status") == "success" 
            for step in critical_steps
        )
        
        self.results["overall_success"] = critical_success
        
        # Print step results
        steps = [
            ("deployment_status", "🔍 Deployment Status"),
            ("git_deployment", "🚀 Git Deployment"),
            ("database_sync", "🗄️  Database Sync"),
            ("backup", "💾 Backup")
        ]
        
        for step_key, step_name in steps:
            result = self.results.get(step_key, {})
            status = result.get("status", "not_run")
            message = result.get("message", "No details")
            
            if status == "success":
                print(f"✅ {step_name}: SUCCESS - {message}")
            elif status == "skipped":
                print(f"⏭️  {step_name}: SKIPPED - {message}")
            elif status in ["in_sync", "identical"]:
                print(f"✅ {step_name}: {status.upper()} - {message}")
            elif status in ["out_of_sync", "differences"]:
                print(f"⚠️  {step_name}: {status.upper()} - {message}")
            else:
                print(f"❌ {step_name}: ERROR - {message}")
        
        print()
        if self.results["overall_success"]:
            print("🎉 MILESTONE COMPLETED SUCCESSFULLY!")
            print(f"🚀 Your changes have been deployed to {self.args.branch}")
            
            if self.args.branch == "production":
                print("🌟 Production deployment complete - changes are now live!")
            else:
                print("🧪 Staging deployment complete - ready for testing!")
                
        else:
            print("⚠️  MILESTONE COMPLETED WITH ISSUES")
            print("Please review the errors above and address them as needed.")
        
        # Save detailed report
        report_file = f"milestone_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "target_branch": self.args.branch,
            "results": self.results,
            "success": self.results["overall_success"]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"📄 Detailed report saved: {report_file}")
        print("=" * 80)

    def run(self):
        """Run the complete milestone process"""
        self.print_header()
        
        try:
            # Step 1: Check deployment status
            if not self.step_1_check_deployment_status():
                return False
            
            # Step 2: Git deployment  
            if not self.step_2_git_deployment():
                return False
            
            # Step 3: Database sync verification
            if not self.step_3_verify_database_sync():
                return False
            
            # Step 4: Backup
            if not self.step_4_backup_code():
                return False
            
            return True
            
        finally:
            self.generate_milestone_report()


def main():
    parser = argparse.ArgumentParser(description="Rally Milestone Deployment Script")
    parser.add_argument(
        "--branch", 
        choices=["staging", "production"], 
        default=None,
        help="Target deployment branch (staging or production)"
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip the backup step"
    )
    parser.add_argument(
        "--quick",
        action="store_true", 
        help="Skip confirmations and run with defaults"
    )
    
    args = parser.parse_args()
    
    # Interactive branch selection if not specified
    if not args.branch:
        print("🎯 Select deployment target:")
        print("1. Staging (for testing)")
        print("2. Production (live deployment)")
        
        while True:
            choice = input("Enter choice [1/2]: ").strip()
            if choice == "1":
                args.branch = "staging"
                break
            elif choice == "2":
                args.branch = "production"
                
                # Extra confirmation for production
                if not args.quick:
                    confirm = input("⚠️  Are you sure you want to deploy to PRODUCTION? [yes/no]: ")
                    if confirm.lower() != "yes":
                        print("❌ Production deployment cancelled")
                        sys.exit(1)
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    # Run milestone deployment
    milestone = MilestoneDeployment(args)
    success = milestone.run()
    
    sys.exit(0 if success and milestone.results["overall_success"] else 1)


if __name__ == "__main__":
    main() 