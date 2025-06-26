# Milestone Deployment Guide

## Overview
The `scripts/milestone.py` script provides a comprehensive, automated deployment workflow that combines all critical deployment tasks into a single command. It's designed to prevent deployment issues and ensure consistency across all environments.

## What It Does

The milestone script performs these steps in sequence:

1. **🔍 Deployment Status Check** - Verifies local/remote sync using `check_deployment_status.py`
2. **🚀 Git Deployment** - Commits and pushes changes to staging or production branch
3. **🗄️ Database Sync Verification** - Compares local and Railway databases using `compare_databases.py`
4. **💾 Code & Database Backup** - Creates comprehensive backups using `cb.py`

## Usage

### Interactive Mode (Recommended)
```bash
python scripts/milestone.py
```
The script will prompt you to select staging or production and guide you through each step.

### Command Line Options
```bash
# Deploy to staging
python scripts/milestone.py --branch staging

# Deploy to production  
python scripts/milestone.py --branch production

# Quick mode (skip confirmations)
python scripts/milestone.py --branch staging --quick

# Skip backup step
python scripts/milestone.py --branch production --skip-backup

# Combine options
python scripts/milestone.py --branch staging --quick --skip-backup
```

## Step-by-Step Breakdown

### Step 1: Deployment Status Check
- Runs `check_deployment_status.py` to identify uncommitted/unpushed changes
- ✅ **Success**: Local and remote are in sync
- ⚠️ **Warning**: Changes detected, offers to continue
- ❌ **Error**: Git issues detected

### Step 2: Git Deployment
- Stages all uncommitted changes with `git add .`
- Commits with descriptive message (auto-generated or user-provided)
- Switches to target branch (`staging` or `main` for production)
- Pushes to remote repository
- Creates branch if it doesn't exist

### Step 3: Database Sync Verification
- Runs comprehensive database comparison between local and Railway
- Compares schema (tables, columns, constraints)
- Compares data (row counts, basic integrity)
- Options when differences found:
  1. Continue anyway (differences may be expected)
  2. View detailed comparison report
  3. Cancel milestone

### Step 4: Code & Database Backup
- Creates timestamped backup using `cb.py`
- Backs up both codebase and database
- Keeps 5 most recent backups by default
- Can be skipped with `--skip-backup` flag

## Branch Strategy

### Staging Branch
- **Purpose**: Testing and validation
- **Target**: `staging` branch
- **Railway**: Deploys to staging environment (if configured)
- **Use Case**: Feature testing, integration testing

### Production Branch  
- **Purpose**: Live deployment
- **Target**: `main` branch
- **Railway**: Deploys to production environment
- **Use Case**: Final deployment to live site
- **Safety**: Extra confirmation required

## Success Criteria

The milestone is considered successful when:
- ✅ Git deployment succeeds (critical)
- ✅ At least one of: deployment status check, database sync, backup

Optional steps (database sync, backup) can have warnings but won't fail the milestone.

## Example Workflows

### Feature Development
```bash
# 1. Develop feature locally
# 2. Test locally
# 3. Deploy to staging for testing
python scripts/milestone.py --branch staging

# 4. Test in staging environment
# 5. Deploy to production when ready
python scripts/milestone.py --branch production
```

### Hotfix Deployment
```bash
# 1. Make critical fix
# 2. Quick deploy to production
python scripts/milestone.py --branch production --quick
```

### Regular Development
```bash
# Interactive mode with full verification
python scripts/milestone.py
# Choose staging or production interactively
```

## Output and Reporting

### Console Output
The script provides real-time progress with clear emojis and status indicators:
- 🔍 Status checks
- 🚀 Git operations  
- 🗄️ Database operations
- 💾 Backup operations
- ✅ Success indicators
- ⚠️ Warnings
- ❌ Errors

### Final Report
```
📋 MILESTONE COMPLETION REPORT
===============================================================================
⏱️  Duration: 45.23 seconds
📅 Completed: 2024-06-26 14:30:15
🎯 Target: production

✅ 🔍 Deployment Status: OUT_OF_SYNC - Changes need to be committed/pushed
✅ 🚀 Git Deployment: SUCCESS - Deployed to main
✅ 🗄️ Database Sync: IDENTICAL - Local and Railway databases are in sync  
✅ 💾 Backup: SUCCESS - Code and database backup created

🎉 MILESTONE COMPLETED SUCCESSFULLY!
🚀 Your changes have been deployed to production
🌟 Production deployment complete - changes are now live!

📄 Detailed report saved: milestone_report_20240626_143015.json
===============================================================================
```

### JSON Report
Detailed machine-readable report saved as `milestone_report_TIMESTAMP.json`:
```json
{
  "timestamp": "2024-06-26T14:30:15.123456",
  "duration_seconds": 45.23,
  "target_branch": "production",
  "results": {
    "deployment_status": {"status": "out_of_sync", "message": "..."},
    "git_deployment": {"status": "success", "branch": "main", "message": "..."},
    "database_sync": {"status": "identical", "message": "..."},
    "backup": {"status": "success", "message": "..."},
    "overall_success": true
  },
  "success": true
}
```

## Error Handling

### Common Issues and Solutions

**Git conflicts:**
```bash
# Resolve conflicts manually, then re-run
git status
git add .
git commit -m "resolve conflicts"
python scripts/milestone.py --branch production
```

**Database differences:**
- Review the comparison report
- Decide if differences are expected
- Continue or fix issues before deployment

**Backup failures:**
- Check disk space
- Verify database connectivity
- Use `--skip-backup` if urgent

**Railway deployment issues:**
- Check Railway dashboard
- Verify branch is configured for auto-deploy
- Monitor deployment logs

## Best Practices

### Before Running Milestone
1. **Test locally** - Ensure your changes work
2. **Review changes** - Know what you're deploying  
3. **Check dependencies** - Ensure all requirements are met
4. **Plan rollback** - Know how to revert if needed

### Staging First
Always deploy to staging before production:
```bash
# Test in staging first
python scripts/milestone.py --branch staging
# Verify everything works
# Then deploy to production
python scripts/milestone.py --branch production
```

### Production Safety
- Use interactive mode for production (avoid `--quick`)
- Review the deployment status carefully
- Have a rollback plan ready
- Monitor the live site after deployment

## Integration with Existing Tools

The milestone script leverages your existing deployment infrastructure:
- **`check_deployment_status.py`** - Git sync verification
- **`compare_databases.py`** - Database comparison
- **`cb.py`** - Backup creation
- **Railway** - Automatic deployment from git branches

## Troubleshooting

### Script Fails to Run
```bash
# Check permissions
chmod +x scripts/milestone.py

# Check Python path
which python
python --version

# Run with explicit path
python3 scripts/milestone.py
```

### Git Issues
```bash
# Check git status manually
git status
git log --oneline -5

# Reset if needed
git reset --soft HEAD~1
```

### Database Issues
```bash
# Test database connections manually
python scripts/compare_databases.py
```

### Backup Issues
```bash
# Test backup manually
python scripts/cb.py --list
```

## Quick Reference

```bash
# Most common usage patterns
python scripts/milestone.py                    # Interactive
python scripts/milestone.py --branch staging   # Staging
python scripts/milestone.py --branch production # Production
python scripts/milestone.py --quick            # Skip prompts
python scripts/milestone.py --skip-backup      # No backup

# Check what would be deployed
python scripts/check_deployment_status.py

# Manual backup
python scripts/cb.py

# Manual database check  
python scripts/compare_databases.py
```

## Tips

- 💡 Run `python scripts/check_deployment_status.py` before milestone to preview changes
- 💡 Use staging deployments to test the milestone process
- 💡 Keep the detailed JSON reports for deployment auditing
- 💡 Monitor Railway dashboard during deployment
- 💡 Test the live site after production deployment 