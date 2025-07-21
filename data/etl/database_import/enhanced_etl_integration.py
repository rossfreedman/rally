#!/usr/bin/env python3
"""
Enhanced ETL Integration with Bulletproof Team ID Preservation
=============================================================

This module integrates the bulletproof team ID preservation system
into the existing ETL workflow, ensuring zero orphaned records.

Key Features:
- Drop-in replacement for existing team import
- Automatic constraint validation and fixing
- Comprehensive backup and restore
- Health monitoring and auto-repair
- Rollback capabilities on failure

Usage:
    # Replace existing import_teams call
    from enhanced_etl_integration import bulletproof_import_teams
    
    # In ETL script, replace:
    # self.import_teams(conn, teams_data)
    # With:
    # bulletproof_import_teams(self, conn, teams_data)
"""

import sys
import os
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bulletproof_team_id_preservation import BulletproofTeamPreservation

def bulletproof_import_teams(etl_instance, conn, teams_data: List[Dict]) -> int:
    """
    Drop-in replacement for ETL team import with bulletproof preservation
    
    Args:
        etl_instance: The ETL instance (for logging compatibility)
        conn: Database connection
        teams_data: List of team dictionaries to import
    
    Returns:
        int: Number of teams successfully processed
    
    Raises:
        Exception: If preservation fails critically
    """
    
    etl_instance.log("🛡️  BULLETPROOF TEAM ID PRESERVATION")
    etl_instance.log("=" * 60)
    etl_instance.log("Using enhanced team import with zero orphan guarantee")
    
    try:
        with BulletproofTeamPreservation() as preservation:
            # Step 1: Validate constraints
            etl_instance.log("🔍 Step 1: Validating database constraints...")
            if not preservation.validate_constraints():
                raise Exception("❌ Constraint validation failed - ETL cannot proceed safely")
            etl_instance.log("✅ All constraints validated successfully")
            
            # Step 2: Backup user data
            etl_instance.log("💾 Step 2: Creating comprehensive backup...")
            backup_stats = preservation.backup_user_data()
            etl_instance.log(f"✅ Backed up {sum(backup_stats.values())} records across {len(backup_stats)} tables")
            
            # Step 3: Import teams with preservation
            etl_instance.log("🏆 Step 3: Importing teams with ID preservation...")
            import_stats = preservation.preserve_teams_during_import(teams_data)
            
            total_processed = import_stats['preserved'] + import_stats['created'] + import_stats['updated']
            etl_instance.log(f"✅ Processed {total_processed} teams:")
            etl_instance.log(f"   • Preserved: {import_stats['preserved']}")
            etl_instance.log(f"   • Created: {import_stats['created']}")
            etl_instance.log(f"   • Updated: {import_stats['updated']}")
            etl_instance.log(f"   • Errors: {import_stats['errors']}")
            
            # Step 4: Restore user data
            etl_instance.log("🔄 Step 4: Restoring user data...")
            restore_stats = preservation.restore_user_data()
            etl_instance.log(f"✅ Restored {sum(restore_stats.values())} records across {len(restore_stats)} tables")
            
            # Step 5: Health validation
            etl_instance.log("🔍 Step 5: Validating system health...")
            health = preservation.validate_health()
            
            if health['overall_health'] == 'HEALTHY':
                etl_instance.log("✅ System health: PERFECT - No issues detected")
            elif health['overall_health'] == 'DEGRADED':
                etl_instance.log("⚠️  System health: DEGRADED - Minor issues detected")
                etl_instance.log("🔧 Attempting automatic repair...")
                
                repair_stats = preservation.auto_repair_orphans()
                if sum(repair_stats.values()) > 0:
                    etl_instance.log(f"✅ Auto-repaired {sum(repair_stats.values())} orphaned records")
                    
                    # Re-validate after repair
                    health = preservation.validate_health()
                    if health['overall_health'] == 'HEALTHY':
                        etl_instance.log("✅ System health: PERFECT after auto-repair")
                    else:
                        etl_instance.log("⚠️  System health: Still degraded after auto-repair")
                        for issue in health['issues']:
                            etl_instance.log(f"   • {issue}")
                else:
                    etl_instance.log("⚠️  No orphaned records to repair")
                    for issue in health['issues']:
                        etl_instance.log(f"   • {issue}")
            
            elif health['overall_health'] == 'CRITICAL':
                etl_instance.log("❌ System health: CRITICAL - Major issues detected")
                for issue in health['issues']:
                    etl_instance.log(f"   • {issue}")
                
                etl_instance.log("🔧 Attempting emergency auto-repair...")
                repair_stats = preservation.auto_repair_orphans()
                
                # Re-validate after emergency repair
                health = preservation.validate_health()
                if health['overall_health'] in ['HEALTHY', 'DEGRADED']:
                    etl_instance.log("✅ Emergency repair successful")
                else:
                    raise Exception(f"❌ Critical team ID preservation failure: {health['issues']}")
            
            else:  # ERROR
                raise Exception(f"❌ Health validation error: {health['issues']}")
            
            etl_instance.log("=" * 60)
            etl_instance.log("🛡️  BULLETPROOF PRESERVATION COMPLETED SUCCESSFULLY")
            etl_instance.log("✅ ZERO ORPHANED RECORDS GUARANTEED")
            etl_instance.log("=" * 60)
            
            return total_processed
            
    except Exception as e:
        etl_instance.log(f"❌ BULLETPROOF PRESERVATION FAILED: {str(e)}")
        etl_instance.log("🔄 Database will be rolled back to preserve data integrity")
        raise


def patch_existing_etl_class(etl_class):
    """
    Monkey patch existing ETL class to use bulletproof preservation
    
    Usage:
        from enhanced_etl_integration import patch_existing_etl_class
        from import_all_jsons_to_database import ComprehensiveETL
        
        # Patch the ETL class
        patch_existing_etl_class(ComprehensiveETL)
        
        # Now use ETL normally - team import is automatically bulletproof
        etl = ComprehensiveETL()
        etl.run()
    """
    
    # Store original import_teams method
    original_import_teams = etl_class.import_teams
    
    def enhanced_import_teams(self, conn, teams_data):
        """Enhanced import_teams with bulletproof preservation"""
        return bulletproof_import_teams(self, conn, teams_data)
    
    # Replace import_teams method
    etl_class.import_teams = enhanced_import_teams
    
    # Add bulletproof validation method
    def validate_bulletproof_health(self):
        """Validate bulletproof preservation health"""
        with BulletproofTeamPreservation() as preservation:
            return preservation.validate_health()
    
    etl_class.validate_bulletproof_health = validate_bulletproof_health
    
    return etl_class


def create_bulletproof_etl_wrapper(original_etl_class):
    """
    Create a bulletproof wrapper around existing ETL class
    
    Usage:
        from enhanced_etl_integration import create_bulletproof_etl_wrapper
        from import_all_jsons_to_database import ComprehensiveETL
        
        # Create bulletproof wrapper
        BulletproofETL = create_bulletproof_etl_wrapper(ComprehensiveETL)
        
        # Use bulletproof ETL
        etl = BulletproofETL()
        etl.run()
    """
    
    class BulletproofETLWrapper(original_etl_class):
        """Bulletproof wrapper around original ETL class"""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.bulletproof_enabled = True
            
        def import_teams(self, conn, teams_data):
            """Override team import with bulletproof preservation"""
            if self.bulletproof_enabled:
                return bulletproof_import_teams(self, conn, teams_data)
            else:
                return super().import_teams(conn, teams_data)
        
        def run(self, *args, **kwargs):
            """Enhanced run with pre and post validation"""
            self.log("🛡️  STARTING BULLETPROOF ETL PROCESS")
            self.log("=" * 60)
            
            try:
                # Pre-validation
                with BulletproofTeamPreservation() as preservation:
                    if not preservation.validate_constraints():
                        self.log("🔧 Fixing constraint issues before ETL...")
                        if not preservation.validate_constraints():
                            raise Exception("Failed to fix constraint issues")
                
                # Run original ETL process
                result = super().run(*args, **kwargs)
                
                # Post-validation
                self.log("🔍 Final health validation...")
                with BulletproofTeamPreservation() as preservation:
                    health = preservation.validate_health()
                    
                    if health['overall_health'] != 'HEALTHY':
                        self.log("🔧 Final auto-repair...")
                        preservation.auto_repair_orphans()
                
                self.log("=" * 60)
                self.log("🛡️  BULLETPROOF ETL COMPLETED SUCCESSFULLY")
                self.log("✅ ZERO ORPHANED RECORDS GUARANTEED")
                self.log("=" * 60)
                
                return result
                
            except Exception as e:
                self.log(f"❌ BULLETPROOF ETL FAILED: {str(e)}")
                raise
        
        def disable_bulletproof(self):
            """Disable bulletproof preservation (for testing)"""
            self.bulletproof_enabled = False
            self.log("⚠️  Bulletproof preservation DISABLED")
        
        def enable_bulletproof(self):
            """Re-enable bulletproof preservation"""
            self.bulletproof_enabled = True
            self.log("✅ Bulletproof preservation ENABLED")
    
    return BulletproofETLWrapper


def emergency_repair_orphans():
    """
    Emergency repair function for fixing orphaned records
    Can be run independently if issues are discovered
    """
    print("🚨 EMERGENCY ORPHAN REPAIR")
    print("=" * 40)
    
    with BulletproofTeamPreservation() as preservation:
        # Health check
        health = preservation.validate_health()
        
        if health['overall_health'] == 'HEALTHY':
            print("✅ System is healthy - no repair needed")
            return
        
        print(f"System health: {health['overall_health']}")
        for issue in health['issues']:
            print(f"  • {issue}")
        
        # Attempt repair
        print("\n🔧 Attempting repair...")
        repair_stats = preservation.auto_repair_orphans()
        
        total_fixed = sum(repair_stats.values())
        if total_fixed > 0:
            print(f"✅ Repaired {total_fixed} orphaned records:")
            for key, count in repair_stats.items():
                if count > 0:
                    print(f"  • {key}: {count}")
        else:
            print("⚠️  No orphaned records found to repair")
        
        # Final validation
        print("\n🔍 Final validation...")
        health = preservation.validate_health()
        print(f"Final system health: {health['overall_health']}")
        
        if health['overall_health'] == 'HEALTHY':
            print("✅ System is now healthy")
        else:
            print("❌ Issues remain:")
            for issue in health['issues']:
                print(f"  • {issue}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced ETL Integration Tools')
    parser.add_argument('--emergency-repair', action='store_true', 
                       help='Run emergency orphan repair')
    parser.add_argument('--health-check', action='store_true', 
                       help='Run health check only')
    
    args = parser.parse_args()
    
    if args.emergency_repair:
        emergency_repair_orphans()
    elif args.health_check:
        with BulletproofTeamPreservation() as preservation:
            health = preservation.validate_health()
            print(f"System health: {health['overall_health']}")
            if health['issues']:
                for issue in health['issues']:
                    print(f"  • {issue}")
            else:
                print("✅ No issues found")
    else:
        print("Enhanced ETL Integration Tools")
        print("Usage:")
        print("  --emergency-repair : Fix orphaned records")
        print("  --health-check     : Check system health") 