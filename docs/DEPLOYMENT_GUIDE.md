# 🚀 Rally Deployment Guide

This guide explains how to deploy Rally to **staging** and **production** environments using our automated git workflows.

## 📋 **Quick Reference**

| Command | Action | Environment | Safety |
|---------|--------|-------------|---------|
| `git deploy-staging` | Deploy to staging | 🟡 Staging | ✅ Safe |
| `git deploy-production` | Deploy to production | 🚨 Production | ⚠️ Live users affected |
| `git status-deployments` | Check deployment status | - | ✅ Read-only |

## 🔄 **Deployment Workflow**

### **For Feature Development & Testing:**

```bash
# 1. Develop on feature branch or main
git add .
git commit -m "Add new feature"

# 2. Deploy to staging for testing
git deploy-staging

# 3. Test thoroughly on staging environment
# Visit: https://rally-staging.up.railway.app

# 4. If tests pass, deploy to production
git deploy-production
```

### **For Hotfixes:**

```bash
# 1. Fix the issue on main branch
git add .
git commit -m "Fix critical bug"

# 2. Optional: Quick staging test
git deploy-staging

# 3. Deploy to production immediately
git deploy-production
```

## 🎯 **Environment Details**

### **🟡 Staging Environment**
- **URL**: https://rally-staging.up.railway.app
- **Trigger**: Push to `staging` branch
- **Purpose**: Testing, QA, feature validation
- **Database**: Railway staging database
- **Safety**: ✅ Safe to break - no real users affected

### **🚨 Production Environment** 
- **URL**: https://rally.up.railway.app
- **Trigger**: Push to `main` branch
- **Purpose**: Live application for real users
- **Database**: Railway production database  
- **Safety**: ⚠️ **CRITICAL** - affects live users!

## 🛠 **Manual Deployment Options**

### **GitHub Actions (Manual Trigger)**

1. Go to **GitHub Actions** tab in your repository
2. Select **"Deploy to Staging"** or **"Deploy to Production"**
3. Click **"Run workflow"**
4. For production: Type `PRODUCTION` to confirm

### **Command Line (Advanced)**

```bash
# Deploy to staging manually
git checkout staging
git merge main
git push origin staging
git checkout main

# Deploy to production manually  
git push origin main
```

## 🔍 **Monitoring Deployments**

### **Check Status**
```bash
# View recent commits on both branches
git status-deployments

# Check GitHub Actions
# Visit: https://github.com/rossfreedman/rally/actions
```

### **Deployment Logs**
- **GitHub Actions**: Check workflow runs for detailed logs
- **Railway Dashboard**: Monitor application performance
- **Application Logs**: Check for errors after deployment

## 🚨 **Safety Features**

### **Staging Deployment**
- ✅ Runs basic tests
- ✅ Allows deployment even if tests fail (force option)
- ✅ Safe environment for breaking changes

### **Production Deployment**
- 🔒 **Comprehensive testing** - all tests must pass
- 🔒 **Manual confirmation** required for GitHub UI deployments
- 🔒 **Automatic rollback** if health checks fail
- 🔒 **Deployment tags** created for tracking
- 🔒 **Strict linting** and code quality checks

## 📊 **Database Management**

### **Sync Local → Staging**
```bash
# Clone your local database to staging
python data/etl/clone/clone_local_to_railway_STAGING_auto.py
```

### **Sync Local → Production**
```bash
# Clone your local database to production (BE CAREFUL!)
python data/etl/clone/clone_local_to_railway_PROD_auto.py
```

## 🆘 **Emergency Procedures**

### **Rollback Production**
```bash
# Option 1: Revert to previous commit
git revert HEAD
git push origin main

# Option 2: Reset to previous working commit
git reset --hard <previous-commit-hash>
git push --force-with-lease origin main
```

### **Emergency Hotfix**
```bash
# Skip staging and deploy directly to production
git add .
git commit -m "Emergency fix: critical issue"
git deploy-production
```

## 🎯 **Best Practices**

### **✅ DO**
- Always test on staging before production
- Write descriptive commit messages
- Run tests locally before pushing
- Monitor application after production deployments
- Use database cloning scripts for data sync

### **❌ DON'T**
- Deploy to production without staging tests
- Force push to main branch
- Deploy during peak usage hours (unless emergency)
- Skip testing for "small" changes
- Ignore deployment failure notifications

## 🔧 **Troubleshooting**

### **Deployment Stuck**
```bash
# Check GitHub Actions status
# Visit: https://github.com/rossfreedman/rally/actions

# Check Railway deployment status  
railway status --environment staging
railway status --environment production
```

### **Database Issues**
```bash
# Check database connectivity
python scripts/check_database_status.py

# Re-sync databases if needed
python data/etl/clone/clone_local_to_railway_STAGING_auto.py
```

### **Application Not Responding**
1. Check Railway logs in dashboard
2. Verify environment variables are set
3. Check database connectivity
4. Consider rolling back to previous version

## 📞 **Support**

- **GitHub Issues**: For deployment workflow problems
- **Railway Dashboard**: For infrastructure issues  
- **Application Logs**: For runtime errors

---

## 🎉 **You're All Set!**

Your dual deployment system is now configured. Use `git deploy-staging` for safe testing and `git deploy-production` when you're ready to go live! 

**Remember**: Staging first, production second! 🚀 