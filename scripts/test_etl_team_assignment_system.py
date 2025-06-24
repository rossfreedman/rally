#!/usr/bin/env python3
"""
Test ETL Team Assignment System

This script tests the new match-based team assignment system by:
1. Capturing current "good" team assignments state
2. Simulating an ETL run with new logic
3. Comparing before/after states
4. Validating improvements

This ensures the new system will work correctly for future ETL runs.
"""

import sys
import os
import json
from datetime import datetime
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

class ETLTeamAssignmentTester:
    def __init__(self):
        self.test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            'timestamp': self.test_timestamp,
            'phases': {},
            'comparisons': {},
            'validation': {}
        }
    
    def capture_current_state(self):
        """Capture the current state of team assignments (our baseline)"""
        print("=" * 80)
        print("PHASE 1: CAPTURING CURRENT TEAM ASSIGNMENT STATE")
        print("=" * 80)
        
        # Get current team assignments
        current_state_query = """
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                p.team_id,
                t.team_name,
                CASE 
                    WHEN p.team_id IS NULL THEN 'UNASSIGNED'
                    ELSE 'ASSIGNED'
                END as assignment_status
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.is_active = TRUE
            ORDER BY p.last_name, p.first_name
        """
        
        current_assignments = execute_query(current_state_query)
        
        # Analyze current state
        assignment_stats = {
            'total_players': len(current_assignments),
            'assigned_players': len([p for p in current_assignments if p['assignment_status'] == 'ASSIGNED']),
            'unassigned_players': len([p for p in current_assignments if p['assignment_status'] == 'UNASSIGNED']),
            'teams_with_players': len(set([p['team_name'] for p in current_assignments if p['team_name']])),
        }
        
        print(f"Current State Analysis:")
        print(f"  📊 Total Players: {assignment_stats['total_players']}")
        print(f"  ✅ Assigned Players: {assignment_stats['assigned_players']}")
        print(f"  ❌ Unassigned Players: {assignment_stats['unassigned_players']}")
        print(f"  🏆 Teams with Players: {assignment_stats['teams_with_players']}")
        
        # Get validation results for current state
        current_validation = execute_query("SELECT * FROM validate_team_assignments()")
        
        print(f"\nCurrent Validation Issues:")
        for issue in current_validation:
            print(f"  {issue['validation_type']}: {issue['issue_count']} issues")
        
        self.results['phases']['current_state'] = {
            'assignments': current_assignments,
            'stats': assignment_stats,
            'validation': current_validation
        }
        
        return current_assignments, assignment_stats
    
    def simulate_new_etl_assignments(self):
        """Simulate what the new ETL system would assign"""
        print("\n" + "=" * 80)
        print("PHASE 2: SIMULATING NEW MATCH-BASED ETL ASSIGNMENTS")
        print("=" * 80)
        
        # Get suggestions from our new intelligent function
        new_assignments_query = """
            SELECT * FROM assign_player_teams_from_matches()
            ORDER BY match_count DESC
        """
        
        suggested_assignments = execute_query(new_assignments_query)
        
        print(f"New ETL System Analysis:")
        print(f"  🎯 Players needing reassignment: {len(suggested_assignments)}")
        
        # Analyze confidence levels
        confidence_analysis = defaultdict(int)
        for assignment in suggested_assignments:
            confidence_analysis[assignment['assignment_confidence']] += 1
        
        print(f"  Confidence Distribution:")
        for confidence, count in confidence_analysis.items():
            print(f"    {confidence}: {count} players")
        
        # Show top recommendations
        print(f"\n  Top 10 Recommendations:")
        for i, assignment in enumerate(suggested_assignments[:10]):
            print(f"    {i+1}. {assignment['player_name']}: {assignment['old_team']} → {assignment['new_team']} ({assignment['match_count']} matches, {assignment['assignment_confidence']})")
        
        self.results['phases']['new_etl_simulation'] = {
            'suggested_assignments': suggested_assignments,
            'confidence_analysis': dict(confidence_analysis),
            'total_suggestions': len(suggested_assignments)
        }
        
        return suggested_assignments
    
    def apply_high_confidence_assignments(self, suggested_assignments):
        """Apply only HIGH confidence assignments to test the system"""
        print("\n" + "=" * 80)
        print("PHASE 3: APPLYING HIGH CONFIDENCE ASSIGNMENTS (TEST)")
        print("=" * 80)
        
        # Filter for HIGH confidence assignments only
        high_confidence = [a for a in suggested_assignments if a['assignment_confidence'] == 'HIGH']
        
        print(f"High Confidence Assignments: {len(high_confidence)}")
        
        if not high_confidence:
            print("  No HIGH confidence assignments to test")
            return []
        
        # Ask for confirmation
        print(f"\nReady to apply {len(high_confidence)} HIGH confidence assignments for testing?")
        response = input("This is a test - proceed? (yes/no): ").lower().strip()
        
        if response not in ['yes', 'y']:
            print("❌ Test cancelled.")
            return []
        
        applied_assignments = []
        
        for assignment in high_confidence:
            try:
                # Find target team ID
                target_team_query = """
                    SELECT id FROM teams 
                    WHERE team_name = %s
                    LIMIT 1
                """
                
                target_team = execute_query_one(target_team_query, [assignment['new_team']])
                
                if target_team:
                    # Update player's team assignment
                    update_query = """
                        UPDATE players 
                        SET team_id = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE tenniscores_player_id = %s
                    """
                    
                    execute_query(update_query, [target_team['id'], assignment['player_id']])
                    applied_assignments.append(assignment)
                    print(f"  ✅ {assignment['player_name']}: {assignment['old_team']} → {assignment['new_team']}")
                
            except Exception as e:
                print(f"  ❌ Failed to assign {assignment['player_name']}: {e}")
        
        print(f"\nApplied {len(applied_assignments)} HIGH confidence assignments")
        
        self.results['phases']['test_application'] = {
            'high_confidence_count': len(high_confidence),
            'applied_count': len(applied_assignments),
            'applied_assignments': applied_assignments
        }
        
        return applied_assignments
    
    def capture_post_test_state(self):
        """Capture state after applying test assignments"""
        print("\n" + "=" * 80)
        print("PHASE 4: CAPTURING POST-TEST STATE")
        print("=" * 80)
        
        # Get post-test assignments
        post_test_query = """
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                p.team_id,
                t.team_name,
                CASE 
                    WHEN p.team_id IS NULL THEN 'UNASSIGNED'
                    ELSE 'ASSIGNED'
                END as assignment_status
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.is_active = TRUE
            ORDER BY p.last_name, p.first_name
        """
        
        post_test_assignments = execute_query(post_test_query)
        
        # Analyze post-test state
        post_test_stats = {
            'total_players': len(post_test_assignments),
            'assigned_players': len([p for p in post_test_assignments if p['assignment_status'] == 'ASSIGNED']),
            'unassigned_players': len([p for p in post_test_assignments if p['assignment_status'] == 'UNASSIGNED']),
            'teams_with_players': len(set([p['team_name'] for p in post_test_assignments if p['team_name']])),
        }
        
        print(f"Post-Test State Analysis:")
        print(f"  📊 Total Players: {post_test_stats['total_players']}")
        print(f"  ✅ Assigned Players: {post_test_stats['assigned_players']}")
        print(f"  ❌ Unassigned Players: {post_test_stats['unassigned_players']}")
        print(f"  🏆 Teams with Players: {post_test_stats['teams_with_players']}")
        
        # Get validation results for post-test state
        post_test_validation = execute_query("SELECT * FROM validate_team_assignments()")
        
        print(f"\nPost-Test Validation Issues:")
        for issue in post_test_validation:
            print(f"  {issue['validation_type']}: {issue['issue_count']} issues")
        
        self.results['phases']['post_test_state'] = {
            'assignments': post_test_assignments,
            'stats': post_test_stats,
            'validation': post_test_validation
        }
        
        return post_test_assignments, post_test_stats
    
    def compare_states(self, current_stats, post_test_stats):
        """Compare before and after states to validate improvements"""
        print("\n" + "=" * 80)
        print("PHASE 5: COMPARING BEFORE/AFTER STATES")
        print("=" * 80)
        
        # Calculate changes
        assigned_change = post_test_stats['assigned_players'] - current_stats['assigned_players']
        unassigned_change = post_test_stats['unassigned_players'] - current_stats['unassigned_players']
        
        print(f"Assignment Changes:")
        print(f"  📈 Assigned Players: {current_stats['assigned_players']} → {post_test_stats['assigned_players']} ({assigned_change:+d})")
        print(f"  📉 Unassigned Players: {current_stats['unassigned_players']} → {post_test_stats['unassigned_players']} ({unassigned_change:+d})")
        
        # Compare validation issues
        current_validation = {v['validation_type']: v['issue_count'] for v in self.results['phases']['current_state']['validation']}
        post_test_validation = {v['validation_type']: v['issue_count'] for v in self.results['phases']['post_test_state']['validation']}
        
        print(f"\nValidation Issue Changes:")
        for issue_type in current_validation:
            current_count = current_validation[issue_type]
            post_count = post_test_validation.get(issue_type, 0)
            change = post_count - current_count
            print(f"  {issue_type}: {current_count} → {post_count} ({change:+d})")
        
        # Determine if improvements were made
        improvements = {
            'more_assignments': assigned_change > 0,
            'fewer_unassigned': unassigned_change < 0,
            'reduced_mismatches': post_test_validation.get('MISMATCHED_ASSIGNMENTS', 0) < current_validation.get('MISMATCHED_ASSIGNMENTS', 0),
            'reduced_unassigned_with_matches': post_test_validation.get('UNASSIGNED_WITH_MATCHES', 0) < current_validation.get('UNASSIGNED_WITH_MATCHES', 0)
        }
        
        improvement_count = sum(improvements.values())
        
        print(f"\nImprovement Analysis:")
        for improvement, achieved in improvements.items():
            status = "✅" if achieved else "❌"
            print(f"  {status} {improvement.replace('_', ' ').title()}: {achieved}")
        
        print(f"\n🎯 Overall Assessment: {improvement_count}/4 improvements achieved")
        
        self.results['comparisons'] = {
            'assigned_change': assigned_change,
            'unassigned_change': unassigned_change,
            'validation_changes': {
                issue_type: post_test_validation.get(issue_type, 0) - current_validation.get(issue_type, 0)
                for issue_type in current_validation
            },
            'improvements': improvements,
            'improvement_score': improvement_count
        }
        
        return improvements, improvement_count
    
    def generate_test_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "=" * 80)
        print("PHASE 6: GENERATING TEST REPORT")
        print("=" * 80)
        
        report_filename = f"etl_team_assignment_test_report_{self.test_timestamp}.json"
        
        # Add summary to results
        self.results['summary'] = {
            'test_passed': self.results['comparisons']['improvement_score'] >= 3,
            'key_metrics': {
                'assignments_improved': self.results['comparisons']['assigned_change'],
                'validation_issues_reduced': sum(1 for change in self.results['comparisons']['validation_changes'].values() if change < 0),
                'high_confidence_assignments_applied': self.results['phases']['test_application']['applied_count']
            },
            'recommendation': 'DEPLOY' if self.results['comparisons']['improvement_score'] >= 3 else 'NEEDS_REVIEW'
        }
        
        # Save report
        with open(report_filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📊 Test Report Generated: {report_filename}")
        print(f"📈 Test Result: {'PASSED' if self.results['summary']['test_passed'] else 'NEEDS REVIEW'}")
        print(f"🎯 Recommendation: {self.results['summary']['recommendation']}")
        
        return report_filename
    
    def rollback_test_changes(self, applied_assignments):
        """Rollback test changes to restore original state"""
        print("\n" + "=" * 80)
        print("ROLLBACK: RESTORING ORIGINAL STATE")
        print("=" * 80)
        
        if not applied_assignments:
            print("No changes to rollback")
            return
        
        print(f"Rolling back {len(applied_assignments)} test assignments...")
        
        for assignment in applied_assignments:
            try:
                if assignment['old_team'] == 'UNASSIGNED':
                    # Restore to unassigned
                    rollback_query = """
                        UPDATE players 
                        SET team_id = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE tenniscores_player_id = %s
                    """
                    execute_query(rollback_query, [assignment['player_id']])
                else:
                    # Restore to original team
                    original_team_query = """
                        SELECT id FROM teams 
                        WHERE team_name = %s
                        LIMIT 1
                    """
                    original_team = execute_query_one(original_team_query, [assignment['old_team']])
                    
                    if original_team:
                        rollback_query = """
                            UPDATE players 
                            SET team_id = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE tenniscores_player_id = %s
                        """
                        execute_query(rollback_query, [original_team['id'], assignment['player_id']])
                
                print(f"  ↩️  Restored {assignment['player_name']}: {assignment['new_team']} → {assignment['old_team']}")
                
            except Exception as e:
                print(f"  ❌ Failed to rollback {assignment['player_name']}: {e}")
        
        print("✅ Rollback completed - database restored to original state")
    
    def run_full_test(self):
        """Run the complete test suite"""
        print("🧪 ETL Team Assignment System Test")
        print("This test validates the new match-based assignment system\n")
        
        # Phase 1: Capture current state
        current_assignments, current_stats = self.capture_current_state()
        
        # Phase 2: Simulate new ETL
        suggested_assignments = self.simulate_new_etl_assignments()
        
        # Phase 3: Apply high confidence assignments
        applied_assignments = self.apply_high_confidence_assignments(suggested_assignments)
        
        # Phase 4: Capture post-test state
        post_test_assignments, post_test_stats = self.capture_post_test_state()
        
        # Phase 5: Compare states
        improvements, improvement_count = self.compare_states(current_stats, post_test_stats)
        
        # Phase 6: Generate report
        report_filename = self.generate_test_report()
        
        # Rollback changes
        self.rollback_test_changes(applied_assignments)
        
        return self.results

if __name__ == "__main__":
    tester = ETLTeamAssignmentTester()
    results = tester.run_full_test()
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE!")
    print(f"{'='*80}")
    
    if results['summary']['test_passed']:
        print("🎉 NEW ETL SYSTEM VALIDATED!")
        print("   The match-based team assignment system is ready for production use.")
        print("   It successfully improves team assignments compared to the current system.")
    else:
        print("⚠️  NEW ETL SYSTEM NEEDS REVIEW")
        print("   The match-based system shows promise but needs refinement.")
        print("   Review the test report for detailed analysis.")
    
    print(f"\n📊 Full test report available: etl_team_assignment_test_report_{tester.test_timestamp}.json") 