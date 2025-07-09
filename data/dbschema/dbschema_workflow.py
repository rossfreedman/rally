#!/usr/bin/env python3
"""
DbSchema Automated Workflow for Rally
=====================================

Complete automation for schema changes from local → staging → production
Integrates with existing Railway deployment workflow.

Workflow Steps:
1. Generate schema migration from local changes
2. Deploy to staging (with backup)
3. Test on staging environment
4. Deploy to production (with confirmation)
5. Validate production deployment

Usage:
    python data/dbschema/dbschema_workflow.py             # Interactive workflow
    python data/dbschema/dbschema_workflow.py --auto      # Automated workflow (staging only)
    python data/dbschema/dbschema_workflow.py --production # Include production deployment
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class DbSchemaWorkflow:
    """Manages complete DbSchema workflow automation"""
    
    def __init__(self, auto_mode=False, include_production=False):
        self.auto_mode = auto_mode
        self.include_production = include_production
        self.root_dir = Path(__file__).parent.parent.parent
        self.migration_manager = self.root_dir / "data" / "dbschema" / "dbschema_migration_manager.py"
        
    def print_banner(self, title):
        """Print workflow banner"""
        print(f"\n🎯 {title}")
        print("=" * 70)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def run_command(self, cmd, description=""):
        """Run command with logging"""
        if description:
            print(f"🔄 {description}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            return False, e.stderr
    
    def confirm_action(self, message):
        """Get user confirmation unless in auto mode"""
        if self.auto_mode:
            print(f"✅ Auto-mode: {message}")
            return True
        
        response = input(f"❓ {message} [y/N]: ").strip().lower()
        return response in ['y', 'yes']
    
    def step_1_generate_migration(self):
        """Step 1: Generate migration from local schema changes"""
        self.print_banner("Step 1: Generate Schema Migration")
        
        print("📝 This step will analyze your local database and generate a migration file")
        print("🔍 Make sure your local database has the schema changes you want to deploy")
        print()
        
        if not self.confirm_action("Generate migration from current local schema?"):
            return False
        
        # Get migration description
        if self.auto_mode:
            description = f"automated_migration_{datetime.now().strftime('%H%M')}"
        else:
            description = input("📝 Enter migration description (optional): ").strip()
            if not description:
                description = "schema_migration"
        
        # Run migration generation
        cmd = [sys.executable, str(self.migration_manager), "generate", "--description", description]
        success, output = self.run_command(cmd, "Generating migration from local schema...")
        
        if success:
            print("✅ Migration generation completed")
            return True
        else:
            print("❌ Migration generation failed")
            return False
    
    def step_2_deploy_to_staging(self):
        """Step 2: Deploy migration to staging"""
        self.print_banner("Step 2: Deploy to Staging")
        
        print("🧪 This step will deploy your migration to the staging environment")
        print("💾 A backup will be created automatically before deployment")
        print()
        
        if not self.confirm_action("Deploy migration to staging?"):
            return False
        
        # Deploy to staging
        cmd = [sys.executable, str(self.migration_manager), "deploy-staging"]
        success, output = self.run_command(cmd, "Deploying migration to staging...")
        
        if success:
            print("✅ Staging deployment completed")
            return True
        else:
            print("❌ Staging deployment failed")
            return False
    
    def step_3_test_staging(self):
        """Step 3: Test staging deployment"""
        self.print_banner("Step 3: Test Staging Environment")
        
        print("🧪 This step will run automated tests on the staging environment")
        print("🌐 Staging URL: https://rally-staging.up.railway.app")
        print()
        
        # Run automated staging tests
        cmd = [sys.executable, str(self.migration_manager), "test-staging"]
        success, output = self.run_command(cmd, "Running staging tests...")
        
        if success:
            print("✅ Staging tests passed")
        else:
            print("⚠️  Staging tests had issues")
            if not self.auto_mode:
                print("💡 You may want to manually test the staging environment")
                print("   Visit: https://rally-staging.up.railway.app")
                
                if not self.confirm_action("Continue with workflow despite test issues?"):
                    return False
        
        # Manual testing checklist
        if not self.auto_mode:
            print("\n📋 Manual Testing Checklist for Staging:")
            print("   □ Login functionality works")
            print("   □ Database schema changes are applied correctly")
            print("   □ No console errors in browser")
            print("   □ Key workflows function properly")
            print("   □ New schema features work as expected")
            
            if not self.confirm_action("Manual staging tests completed successfully?"):
                return False
        
        return True
    
    def step_4_deploy_to_production(self):
        """Step 4: Deploy to production (if enabled)"""
        if not self.include_production:
            print("\n🏁 Workflow Complete - Staging Only")
            print("✅ Schema migration deployed and tested on staging")
            print("💡 To deploy to production, run:")
            print("   python data/dbschema/dbschema_migration_manager.py deploy-production")
            return True
        
        self.print_banner("Step 4: Deploy to Production")
        
        print("🚀 This step will deploy your tested migration to production")
        print("⚠️  This affects the live production database")
        print("💾 A backup will be created automatically before deployment")
        print()
        
        # Extra confirmation for production
        if not self.auto_mode:
            print("⚠️  PRODUCTION DEPLOYMENT CONFIRMATION")
            print("You are about to modify the live production database.")
            print("Ensure you have:")
            print("   ✅ Tested thoroughly on staging")
            print("   ✅ Verified all functionality works")
            print("   ✅ Have a rollback plan ready")
            print()
            
            confirm = input("Type 'DEPLOY' to confirm production deployment: ")
            if confirm != "DEPLOY":
                print("❌ Production deployment cancelled")
                return False
        
        # Deploy to production
        cmd = [sys.executable, str(self.migration_manager), "deploy-production"]
        
        # For production, we need to handle the manual confirmation
        print("🚀 Initiating production deployment...")
        print("   (You will need to confirm with 'YES' when prompted)")
        
        try:
            # Run interactively for production deployment
            result = subprocess.run(cmd, check=True)
            print("✅ Production deployment completed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Production deployment failed or was cancelled")
            return False
    
    def step_5_post_deployment_validation(self):
        """Step 5: Post-deployment validation"""
        self.print_banner("Step 5: Post-Deployment Validation")
        
        environments = ["staging"]
        if self.include_production:
            environments.append("production")
        
        print(f"🔍 Validating deployment on: {', '.join(environments)}")
        
        # Check migration status
        cmd = [sys.executable, str(self.migration_manager), "status"]
        success, output = self.run_command(cmd, "Checking migration status...")
        
        if success:
            print("✅ Migration status check completed")
        
        # Additional validation recommendations
        print("\n📋 Post-Deployment Checklist:")
        print("   □ Monitor application logs for errors")
        print("   □ Verify key functionality still works")
        print("   □ Check database constraints and relationships")
        print("   □ Monitor performance impact")
        
        if self.include_production:
            print("   □ Notify team of production deployment")
            print("   □ Monitor user feedback")
        
        return True
    
    def show_workflow_status(self):
        """Show current workflow status"""
        self.print_banner("DbSchema Workflow Status")
        
        # Check migration manager status
        cmd = [sys.executable, str(self.migration_manager), "status"]
        success, output = self.run_command(cmd, "Getting current status...")
        
        print("\n🔗 Quick Commands:")
        print("   Generate migration:     python data/dbschema/dbschema_migration_manager.py generate")
        print("   Deploy to staging:      python data/dbschema/dbschema_migration_manager.py deploy-staging")
        print("   Test staging:           python data/dbschema/dbschema_migration_manager.py test-staging")
        print("   Deploy to production:   python data/dbschema/dbschema_migration_manager.py deploy-production")
        print("   Check status:           python data/dbschema/dbschema_migration_manager.py status")
    
    def run_complete_workflow(self):
        """Run the complete automated workflow"""
        self.print_banner("DbSchema Automated Workflow")
        
        workflow_steps = [
            ("Generate Migration", self.step_1_generate_migration),
            ("Deploy to Staging", self.step_2_deploy_to_staging),
            ("Test Staging", self.step_3_test_staging),
            ("Deploy to Production", self.step_4_deploy_to_production),
            ("Post-Deployment Validation", self.step_5_post_deployment_validation),
        ]
        
        print(f"🚀 Starting {'automated' if self.auto_mode else 'interactive'} workflow")
        if self.include_production:
            print("📦 Target: Staging + Production")
        else:
            print("📦 Target: Staging only")
        print()
        
        completed_steps = 0
        total_steps = len(workflow_steps)
        
        for i, (step_name, step_func) in enumerate(workflow_steps, 1):
            print(f"\n{'='*20} STEP {i}/{total_steps}: {step_name} {'='*20}")
            
            try:
                success = step_func()
                if success:
                    completed_steps += 1
                    print(f"✅ Step {i} completed: {step_name}")
                else:
                    print(f"❌ Step {i} failed: {step_name}")
                    break
                    
                # Brief pause between steps
                if not self.auto_mode and i < total_steps:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print(f"\n⚠️  Workflow interrupted at step {i}: {step_name}")
                break
            except Exception as e:
                print(f"❌ Unexpected error in step {i}: {e}")
                break
        
        # Workflow summary
        print(f"\n{'='*70}")
        print(f"📊 WORKFLOW SUMMARY")
        print(f"{'='*70}")
        print(f"Steps completed: {completed_steps}/{total_steps}")
        
        if completed_steps == total_steps:
            print("🎉 Workflow completed successfully!")
            if self.include_production:
                print("✅ Schema changes deployed to staging and production")
            else:
                print("✅ Schema changes deployed to staging")
        else:
            print("⚠️  Workflow incomplete")
            print("💡 Use individual commands to continue from where you left off")
        
        # Show next steps
        print(f"\n🔗 Useful Commands:")
        print(f"   Check status:     python data/dbschema/dbschema_migration_manager.py status")
        print(f"   View rollback:    python data/dbschema/dbschema_migration_manager.py rollback")
        
        return completed_steps == total_steps


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="DbSchema Automated Workflow for Rally")
    parser.add_argument("--auto", action="store_true", 
                       help="Run in automated mode (skip confirmations)")
    parser.add_argument("--production", action="store_true",
                       help="Include production deployment (default: staging only)")
    parser.add_argument("--status", action="store_true",
                       help="Show workflow status and exit")
    
    args = parser.parse_args()
    
    workflow = DbSchemaWorkflow(
        auto_mode=args.auto,
        include_production=args.production
    )
    
    if args.status:
        workflow.show_workflow_status()
        sys.exit(0)
    
    # Run complete workflow
    success = workflow.run_complete_workflow()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 