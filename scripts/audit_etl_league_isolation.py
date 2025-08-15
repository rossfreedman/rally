#!/usr/bin/env python3
"""
ETL League Isolation Audit
==========================

Comprehensive audit of ETL scripts to ensure they all properly handle league isolation
and won't recreate the series conflicts we just fixed.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

class ETLLeagueIsolationAuditor:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.etl_dir = self.project_root / "data" / "etl"
        self.issues = []
        self.good_practices = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def audit_file(self, file_path):
        """Audit a single Python file for league isolation issues"""
        self.log(f"🔍 Auditing: {file_path.relative_to(self.project_root)}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            file_issues = []
            file_good_practices = []
            
            # Check for problematic patterns
            self._check_series_creation_patterns(file_path, content, file_issues, file_good_practices)
            self._check_series_lookup_patterns(file_path, content, file_issues, file_good_practices)
            self._check_database_constraints(file_path, content, file_issues, file_good_practices)
            
            # Report findings for this file
            if file_issues:
                self.log(f"❌ {len(file_issues)} issue(s) found in {file_path.name}", "ERROR")
                for issue in file_issues:
                    self.log(f"   • {issue}", "ERROR")
                self.issues.extend([(file_path, issue) for issue in file_issues])
            else:
                self.log(f"✅ No issues found in {file_path.name}")
            
            if file_good_practices:
                self.log(f"🎯 {len(file_good_practices)} good practice(s) in {file_path.name}")
                for practice in file_good_practices:
                    self.log(f"   • {practice}")
                self.good_practices.extend([(file_path, practice) for practice in file_good_practices])
                
        except Exception as e:
            self.log(f"⚠️ Error reading {file_path}: {e}", "WARNING")
    
    def _check_series_creation_patterns(self, file_path, content, issues, good_practices):
        """Check for series creation patterns"""
        
        # Bad patterns - series creation without league_id
        bad_patterns = [
            (r'INSERT INTO series \([^)]*\) VALUES.*(?!.*league_id)', 
             "Series INSERT without league_id column"),
            (r'INSERT INTO series \(name\) VALUES', 
             "Series INSERT with only name (missing league_id)"),
            (r'CREATE.*series.*(?!.*league_id)', 
             "Series creation without league_id consideration"),
        ]
        
        for pattern, description in bad_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(f"Line {line_num}: {description}")
        
        # Good patterns - series creation with league_id
        good_patterns = [
            (r'INSERT INTO series.*league_id.*VALUES', 
             "Proper series INSERT with league_id"),
            (r'ON CONFLICT \(name, league_id\)', 
             "Uses composite unique constraint (name, league_id)"),
            (r'ensure_series.*league_id.*int', 
             "ensure_series function properly accepts league_id parameter"),
        ]
        
        for pattern, description in good_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                good_practices.append(f"Line {line_num}: {description}")
    
    def _check_series_lookup_patterns(self, file_path, content, issues, good_practices):
        """Check for series lookup patterns"""
        
        # Bad patterns - series lookup without league isolation
        bad_patterns = [
            (r'SELECT.*FROM series WHERE name = %s(?!.*league_id)', 
             "Series lookup by name only (missing league_id filter)"),
            (r'SELECT.*FROM series WHERE.*name.*(?!.*league_id).*LIMIT', 
             "Series SELECT without league_id filter"),
        ]
        
        for pattern, description in bad_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(f"Line {line_num}: {description}")
        
        # Good patterns - series lookup with league isolation  
        good_patterns = [
            (r'SELECT.*FROM series WHERE name = %s AND league_id = %s', 
             "Proper series lookup with league isolation"),
            (r'get_series_db_id.*league_db_id', 
             "Series lookup function properly uses league_db_id"),
        ]
        
        for pattern, description in good_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                good_practices.append(f"Line {line_num}: {description}")
    
    def _check_database_constraints(self, file_path, content, issues, good_practices):
        """Check for proper database constraint usage"""
        
        # Good patterns - proper constraint usage
        constraint_patterns = [
            (r'ON CONFLICT.*name.*league_id.*DO NOTHING', 
             "Uses proper conflict resolution with composite key"),
            (r'UNIQUE.*name.*league_id', 
             "References composite unique constraint"),
        ]
        
        for pattern, description in constraint_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                good_practices.append(f"Line {line_num}: {description}")
    
    def audit_all_etl_scripts(self):
        """Audit all Python files in the ETL directory"""
        self.log("🚀 Starting ETL League Isolation Audit")
        self.log("=" * 60)
        
        if not self.etl_dir.exists():
            self.log(f"❌ ETL directory not found: {self.etl_dir}", "ERROR")
            return False
        
        # Find all Python files in ETL directory
        python_files = list(self.etl_dir.rglob("*.py"))
        
        if not python_files:
            self.log("⚠️ No Python files found in ETL directory", "WARNING")
            return True
        
        self.log(f"📁 Found {len(python_files)} Python files to audit")
        
        # Audit each file
        for file_path in sorted(python_files):
            self.audit_file(file_path)
        
        # Generate summary report
        self.generate_summary_report()
        
        return len(self.issues) == 0
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        self.log("")
        self.log("📊 ETL LEAGUE ISOLATION AUDIT SUMMARY")
        self.log("=" * 60)
        
        # Issues summary
        if self.issues:
            self.log(f"❌ FOUND {len(self.issues)} CRITICAL ISSUES:")
            self.log("")
            
            # Group issues by file
            issues_by_file = {}
            for file_path, issue in self.issues:
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []
                issues_by_file[file_path].append(issue)
            
            for file_path, file_issues in issues_by_file.items():
                self.log(f"📄 {file_path.relative_to(self.project_root)}:")
                for issue in file_issues:
                    self.log(f"   ❌ {issue}")
                self.log("")
            
            self.log("🔧 REQUIRED ACTIONS:")
            self.log("1. Fix all series creation to include league_id")
            self.log("2. Update all series lookups to filter by league_id")
            self.log("3. Ensure all scripts use proper composite constraints")
            self.log("4. Test ETL on staging before production")
            
        else:
            self.log("✅ NO CRITICAL ISSUES FOUND!")
            self.log("All ETL scripts properly handle league isolation.")
        
        self.log("")
        
        # Good practices summary
        if self.good_practices:
            self.log(f"🎯 FOUND {len(self.good_practices)} GOOD PRACTICES:")
            
            # Group by file
            practices_by_file = {}
            for file_path, practice in self.good_practices:
                if file_path not in practices_by_file:
                    practices_by_file[file_path] = []
                practices_by_file[file_path].append(practice)
            
            for file_path, file_practices in practices_by_file.items():
                self.log(f"📄 {file_path.relative_to(self.project_root)}:")
                for practice in file_practices[:3]:  # Show first 3
                    self.log(f"   ✅ {practice}")
                if len(file_practices) > 3:
                    self.log(f"   ... and {len(file_practices) - 3} more")
                self.log("")
        
        # Recommendations
        self.log("💡 RECOMMENDATIONS:")
        self.log("1. ✅ Keep using league_id in all series operations")
        self.log("2. ✅ Always use composite constraints (name, league_id)")
        self.log("3. ✅ Test ETL scripts on staging before production")
        self.log("4. ✅ Monitor for orphaned series after imports")
        
        if self.issues:
            self.log("")
            self.log("⚠️ WARNING: ETL SCRIPTS NEED FIXES BEFORE NEXT IMPORT!")
        else:
            self.log("")
            self.log("🎉 ETL SCRIPTS ARE READY FOR PRODUCTION!")
    
    def create_fix_recommendations(self):
        """Create specific fix recommendations for found issues"""
        if not self.issues:
            return
        
        self.log("")
        self.log("🔧 SPECIFIC FIX RECOMMENDATIONS:")
        self.log("=" * 50)
        
        for file_path, issue in self.issues:
            self.log(f"📄 {file_path.relative_to(self.project_root)}")
            self.log(f"   Issue: {issue}")
            
            if "INSERT INTO series" in issue and "league_id" not in issue:
                self.log("   Fix: Add league_id parameter and column to INSERT")
                self.log("   Example: INSERT INTO series (name, league_id) VALUES (%s, %s)")
            
            elif "SELECT" in issue and "league_id" not in issue:
                self.log("   Fix: Add league_id filter to WHERE clause")
                self.log("   Example: SELECT id FROM series WHERE name = %s AND league_id = %s")
            
            self.log("")

def main():
    """Main execution function"""
    auditor = ETLLeagueIsolationAuditor()
    success = auditor.audit_all_etl_scripts()
    
    if not success:
        auditor.create_fix_recommendations()
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
