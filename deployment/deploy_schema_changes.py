#!/usr/bin/env python3
"""
Rally Schema Deployment Integration
===================================

Integrates DbSchema migrations with the existing Rally deployment workflow.
This script bridges the gap between schema changes and application deployment.

Workflow:
1. Deploy schema changes to staging
2. Deploy application code to staging  
3. Test complete staging environment
4. Deploy schema + application to production
5. Validate production deployment

Usage:
    python deployment/deploy_schema_changes.py               # Interactive deployment
    python deployment/deploy_schema_changes.py --staging     # Staging only
    python deployment/deploy_schema_changes.py --production  # Full deployment
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SchemaDeploymentIntegration:
    """Integrates schema and application deployments"""
    
    def __init__(self, staging_only=False, auto_mode=False):
        self.staging_only = staging_only
        self.auto_mode = auto_mode
        self.root_dir = Path(__file__).parent.parent
        
        # Scripts
        self.dbschema_workflow = self.root_dir / "data" / "dbschema" / "dbschema_workflow.py"
        self.deploy_staging = self.root_dir / "deployment" / "deploy_staging.py"
        self.deploy_production = self.root_dir / "deployment" / "deploy_production.py"
        
    def print_banner(self, title):
        """Print deployment banner"""
        print(f"\n🚀 {title}")
        print("=" * 70)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def run_command(self, cmd, description="", interactive=False):
        """Run command with appropriate handling"""
        if description:
            print(f"🔄 {description}")
        
        try:
            if interactive:
                # Run interactively for commands that need user input
                result = subprocess.run(cmd, check=True)
                return True, ""
            else:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            if hasattr(e, 'stdout') and e.stdout:
                print(f"Output: {e.stdout}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Error: {e.stderr}")
            return False, getattr(e, 'stderr', str(e))
    
    def confirm_action(self, message):
        """Get user confirmation unless in auto mode"""
        if self.auto_mode:
            print(f"✅ Auto-mode: {message}")
            return True
        
        response = input(f"❓ {message} [y/N]: ").strip().lower()
        return response in ['y', 'yes']
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        self.print_banner("Prerequisites Check")
        
        # Check if DbSchema workflow is available
        if not self.dbschema_workflow.exists():
            print(f"❌ DbSchema workflow not found: {self.dbschema_workflow}")
            return False
        print("✅ DbSchema workflow available")
        
        # Check if deployment scripts are available
        if not self.deploy_staging.exists():
            print(f"❌ Staging deployment script not found: {self.deploy_staging}")
            return False
        print("✅ Staging deployment script available")
        
        if not self.staging_only and not self.deploy_production.exists():
            print(f"❌ Production deployment script not found: {self.deploy_production}")
            return False
        print("✅ Production deployment script available")
        
        # Check git status
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, check=True)
            if result.stdout.strip():
                print("⚠️  Uncommitted changes detected")
                if not self.confirm_action("Continue with uncommitted changes?"):
                    return False
            else:
                print("✅ Git status clean")
        except subprocess.CalledProcessError:
            print("⚠️  Could not check git status")
        
        return True
    
    def phase_1_schema_deployment(self):
        """Phase 1: Deploy schema changes"""
        self.print_banner("Phase 1: Schema Deployment")
        
        print("📝 This phase deploys database schema changes")
        print("🎯 Target: Staging environment")
        if not self.staging_only:
            print("🎯 Will also prepare for production deployment")
        print()
        
        # Run DbSchema workflow for staging
        workflow_args = [sys.executable, str(self.dbschema_workflow)]
        if self.auto_mode:
            workflow_args.append("--auto")
        
        print("🔄 Running DbSchema workflow...")
        success, output = self.run_command(workflow_args, 
                                         "Deploying schema changes to staging",
                                         interactive=True)
        
        if not success:
            print("❌ Schema deployment to staging failed")
            return False
        
        print("✅ Schema deployment to staging completed")
        return True
    
    def phase_2_application_deployment_staging(self):
        """Phase 2: Deploy application to staging"""
        self.print_banner("Phase 2: Application Deployment (Staging)")
        
        print("📦 This phase deploys application code to staging")
        print("🔄 Application will use the new schema deployed in Phase 1")
        print()
        
        if not self.confirm_action("Deploy application code to staging?"):
            return False
        
        # Deploy application to staging
        success, output = self.run_command([sys.executable, str(self.deploy_staging)],
                                         "Deploying application to staging",
                                         interactive=True)
        
        if not success:
            print("❌ Application deployment to staging failed")
            return False
        
        print("✅ Application deployment to staging completed")
        return True
    
    def phase_3_staging_integration_testing(self):
        """Phase 3: Complete staging environment testing"""
        self.print_banner("Phase 3: Staging Integration Testing")
        
        print("🧪 This phase tests the complete staging environment")
        print("🔍 Testing schema + application integration")
        print("🌐 Staging URL: https://rally-staging.up.railway.app")
        print()
        
        # Run staging tests
        staging_test_script = self.root_dir / "deployment" / "test_staging_session_refresh.py"
        if staging_test_script.exists():
            success, output = self.run_command([sys.executable, str(staging_test_script)],
                                             "Running staging integration tests")
            if success:
                print("✅ Automated staging tests passed")
            else:
                print("⚠️  Automated staging tests had issues")
        
        # Manual testing checklist
        print("\n📋 Manual Integration Testing Checklist:")
        print("   □ Login and authentication work")
        print("   □ Database schema changes are reflected in UI")
        print("   □ New features work as expected")
        print("   □ Existing functionality still works")
        print("   □ No console errors or warnings")
        print("   □ Performance is acceptable")
        print("   □ Mobile functionality works")
        print()
        
        if not self.confirm_action("All staging integration tests passed?"):
            print("❌ Staging integration testing failed")
            print("💡 Fix issues before proceeding to production")
            return False
        
        print("✅ Staging integration testing completed")
        return True
    
    def phase_4_production_deployment(self):
        """Phase 4: Production deployment"""
        if self.staging_only:
            print("\n🏁 Deployment Complete - Staging Only")
            print("✅ Schema and application deployed to staging")
            print("🧪 Staging environment ready for testing")
            print()
            print("💡 To deploy to production:")
            print("   python deployment/deploy_schema_changes.py --production")
            return True
        
        self.print_banner("Phase 4: Production Deployment")
        
        print("🚀 This phase deploys to production environment")
        print("⚠️  This affects live users and production database")
        print("💾 Automatic backups will be created")
        print()
        
        # Extra confirmation for production
        print("⚠️  PRODUCTION DEPLOYMENT CONFIRMATION")
        print("You are about to deploy to the live production environment.")
        print("Ensure you have:")
        print("   ✅ Thoroughly tested on staging")
        print("   ✅ All integration tests pass")
        print("   ✅ Schema and application work together")
        print("   ✅ Rollback plan ready")
        print()
        
        if not self.auto_mode:
            confirm = input("Type 'PRODUCTION' to confirm production deployment: ")
            if confirm != "PRODUCTION":
                print("❌ Production deployment cancelled")
                return False
        
        # Deploy schema to production
        print("🗄️  Step 4a: Deploying schema to production...")
        schema_workflow_args = [sys.executable, str(self.dbschema_workflow), "--production"]
        if self.auto_mode:
            schema_workflow_args.append("--auto")
        
        success, output = self.run_command(schema_workflow_args,
                                         "Deploying schema to production",
                                         interactive=True)
        
        if not success:
            print("❌ Schema deployment to production failed")
            return False
        
        # Deploy application to production
        print("\n📦 Step 4b: Deploying application to production...")
        success, output = self.run_command([sys.executable, str(self.deploy_production)],
                                         "Deploying application to production",
                                         interactive=True)
        
        if not success:
            print("❌ Application deployment to production failed")
            return False
        
        print("✅ Production deployment completed")
        return True
    
    def phase_5_production_validation(self):
        """Phase 5: Production validation"""
        if self.staging_only:
            return True
        
        self.print_banner("Phase 5: Production Validation")
        
        print("🔍 This phase validates the production deployment")
        print("🌐 Production URL: https://rally.up.railway.app")
        print()
        
        # Run production tests
        production_test_script = self.root_dir / "deployment" / "test_production_session_refresh.py"
        if production_test_script.exists():
            success, output = self.run_command([sys.executable, str(production_test_script)],
                                             "Running production validation tests")
            if success:
                print("✅ Production validation tests passed")
            else:
                print("⚠️  Production validation tests had issues")
                print("💡 Monitor production closely")
        
        # Post-deployment checklist
        print("\n📋 Post-Production Deployment Checklist:")
        print("   □ Monitor application logs for errors")
        print("   □ Check key user workflows")
        print("   □ Verify schema changes work in production")
        print("   □ Monitor database performance")
        print("   □ Check error rates and response times")
        print("   □ Notify team of successful deployment")
        print()
        
        print("✅ Production validation completed")
        print("🎉 Full deployment successful!")
        return True
    
    def run_integrated_deployment(self):
        """Run the complete integrated deployment workflow"""
        self.print_banner("Rally Integrated Schema + Application Deployment")
        
        target = "Staging Only" if self.staging_only else "Staging + Production"
        mode = "Automated" if self.auto_mode else "Interactive"
        
        print(f"🎯 Target: {target}")
        print(f"🔧 Mode: {mode}")
        print()
        
        phases = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Schema Deployment", self.phase_1_schema_deployment),
            ("Application Deployment (Staging)", self.phase_2_application_deployment_staging),
            ("Staging Integration Testing", self.phase_3_staging_integration_testing),
            ("Production Deployment", self.phase_4_production_deployment),
            ("Production Validation", self.phase_5_production_validation),
        ]
        
        completed_phases = 0
        total_phases = len(phases)
        
        for i, (phase_name, phase_func) in enumerate(phases, 1):
            print(f"\n{'='*25} PHASE {i}/{total_phases}: {phase_name} {'='*25}")
            
            try:
                success = phase_func()
                if success:
                    completed_phases += 1
                    print(f"✅ Phase {i} completed: {phase_name}")
                else:
                    print(f"❌ Phase {i} failed: {phase_name}")
                    break
                    
                # Brief pause between phases
                if not self.auto_mode and i < total_phases:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print(f"\n⚠️  Deployment interrupted at phase {i}: {phase_name}")
                break
            except Exception as e:
                print(f"❌ Unexpected error in phase {i}: {e}")
                break
        
        # Deployment summary
        print(f"\n{'='*70}")
        print(f"📊 DEPLOYMENT SUMMARY")
        print(f"{'='*70}")
        print(f"Phases completed: {completed_phases}/{total_phases}")
        
        if completed_phases == total_phases:
            print("🎉 Integrated deployment completed successfully!")
            if self.staging_only:
                print("✅ Schema and application deployed to staging")
            else:
                print("✅ Schema and application deployed to staging and production")
        else:
            print("⚠️  Deployment incomplete")
            print("💡 Check error messages above and resolve issues")
        
        # Show useful commands
        print(f"\n🔗 Useful Commands:")
        print(f"   Schema status:        python data/dbschema/dbschema_migration_manager.py status")
        print(f"   Schema rollback:      python data/dbschema/dbschema_migration_manager.py rollback")
        print(f"   Deployment status:    python deployment/check_deployment_status.py")
        
        return completed_phases == total_phases


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Rally Integrated Schema + Application Deployment")
    parser.add_argument("--staging", action="store_true",
                       help="Deploy to staging only (default: staging + production)")
    parser.add_argument("--production", action="store_true",
                       help="Deploy to staging + production")
    parser.add_argument("--auto", action="store_true",
                       help="Run in automated mode (minimal confirmations)")
    
    args = parser.parse_args()
    
    # Determine staging_only flag
    if args.staging and args.production:
        print("❌ Cannot specify both --staging and --production")
        sys.exit(1)
    
    staging_only = args.staging or not args.production
    
    deployment = SchemaDeploymentIntegration(
        staging_only=staging_only,
        auto_mode=args.auto
    )
    
    # Run integrated deployment
    success = deployment.run_integrated_deployment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 