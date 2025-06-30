# Deployment Workflow Guide

## Overview
This guide ensures changes make it from local development to Railway production without getting missed.

## The Deployment Pipeline
```
Local Development → Git Commit → Git Push → Railway Auto-Deploy
```

## Pre-Deployment Checklist

### 1. Check What's Modified Locally
```bash
# See all modified files
git status

# See detailed changes
git diff

# See staged vs unstaged
git status --porcelain
```

### 2. Review Changes Before Committing
```bash
# Review specific file changes
git diff templates/mobile/index.html

# Review all changes at once
git diff --name-only | xargs git diff
```

### 3. Stage and Commit Related Changes Together
```bash
# Add specific files for a feature
git add templates/mobile/index.html templates/mobile/track_byes_courts.html app/routes/api_routes.py

# Or add all changes (be careful!)
git add .

# Commit with descriptive message
git commit -m "feat: Add league/team selector functionality"
```

### 4. Push to Trigger Deployment
```bash
git push origin main
```

### 5. Verify Deployment
- Check Railway dashboard for deployment status
- Test the live site after deployment completes
- Monitor for any deployment errors

## Prevention Tools

### 1. Git Aliases for Quick Checks
Add to your `~/.gitconfig`:
```ini
[alias]
    st = status
    unstaged = diff --name-only
    staged = diff --cached --name-only
    deploy-check = !git status && echo "\n--- Unpushed commits ---" && git log origin/main..HEAD --oneline
```

### 2. Pre-Push Hook
Create `.git/hooks/pre-push`:
```bash
#!/bin/bash
echo "🚀 About to push to production..."
echo "📋 Files being deployed:"
git diff --name-only origin/main..HEAD
echo ""
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi
```

### 3. Deployment Status Script
Create `scripts/check_deployment_status.py`:
```python
#!/usr/bin/env python3
import subprocess
import sys

def check_git_status():
    """Check if there are uncommitted changes"""
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  WARNING: Uncommitted changes found:")
        print(result.stdout)
        return False
    return True

def check_unpushed_commits():
    """Check if there are unpushed commits"""
    result = subprocess.run(['git', 'log', 'origin/main..HEAD', '--oneline'], 
                          capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  WARNING: Unpushed commits found:")
        print(result.stdout)
        return False
    return True

def main():
    print("🔍 Checking deployment status...")
    
    uncommitted = not check_git_status()
    unpushed = not check_unpushed_commits()
    
    if not uncommitted and not unpushed:
        print("✅ Local and remote are in sync!")
        print("🚀 Railway should have the latest code")
    else:
        print("\n❌ Deployment may be out of sync!")
        if uncommitted:
            print("   Run: git add . && git commit -m 'description'")
        if unpushed:
            print("   Run: git push origin main")

if __name__ == "__main__":
    main()
```

### 4. VS Code/Cursor Integration
Add to your editor settings for visual indicators:
- Git status in sidebar
- Uncommitted changes highlighting
- Branch status in status bar

## Best Practices

### 1. Commit Frequently
```bash
# Good practice: commit logical chunks
git add specific_files
git commit -m "feat: specific feature"

# Avoid: giant commits with everything
git add .
git commit -m "various changes"
```

### 2. Feature Branch Workflow (Optional)
```bash
# Create feature branch
git checkout -b feature/league-selector

# Work and commit
git add . && git commit -m "Add league selector"

# Merge to main when ready
git checkout main
git merge feature/league-selector
git push origin main
```

### 3. Test Before Pushing
```bash
# Run local tests if available
python -m pytest tests/

# Check for obvious errors
python -m py_compile app/**/*.py
```

### 4. Deployment Verification
After pushing:
1. Check Railway dashboard (https://railway.app)
2. Wait for deployment to complete (~2-5 minutes)
3. Test the live site
4. Check logs for any errors

## Quick Commands Reference

```bash
# Daily workflow
git status                          # What's changed?
git add files                       # Stage changes
git commit -m "description"         # Commit changes  
git push origin main               # Deploy to Railway

# Troubleshooting
git log --oneline -10              # Recent commits
git diff origin/main..HEAD        # What's different from deployed?
git reset --soft HEAD~1           # Undo last commit (keep changes)
git reset --hard origin/main      # Reset to deployed version
```

## Emergency Fixes

If you need to quickly fix a production issue:
```bash
# Make the fix
git add fixed_files
git commit -m "hotfix: critical issue description"
git push origin main

# Railway will auto-deploy within 2-5 minutes
```

## Monitoring

- **Railway Dashboard**: Check deployment status and logs
- **Git Status**: Always check before switching tasks
- **Live Site**: Verify changes after deployment

Remember: **If it's not in git, it's not deployed!** 