# Rally Deployment Workflow Guide

## 🔄 **Ideal Workflow Pattern**

```
feature/fix → staging → production
     ↓           ↓         ↓
  local dev   staging    production
   testing     testing    live users
```

## 🚀 **Step-by-Step Deployment Process**

### **Step 1: Deploy to Staging**
```bash
# From your feature branch or main
python deployment/deploy_staging.py
```

**What this does:**
- ✅ Auto-commits any uncommitted changes
- ✅ Merges current branch → `staging` branch
- ✅ Pushes to Railway staging environment
- ✅ Runs automated staging tests
- ✅ Provides staging URL for manual testing

### **Step 2: Test on Staging**
- 🌐 **URL**: `https://rally-staging.up.railway.app`
- 🧪 **Run tests**: `python deployment/test_staging_session_refresh.py`
- 📱 **Manual testing**: Login, key workflows, mobile functionality
- 🐛 **Check console**: No JavaScript errors

### **Step 3: Deploy to Production** (Only if staging tests pass)
```bash
python deployment/deploy_production.py
```

**What this does:**
- ✅ Verifies staging tests still pass
- ✅ Requires explicit "yes" confirmation
- ✅ Merges `staging` → `main` branch
- ✅ Pushes to Railway production environment
- ✅ Runs production verification tests

## 🛡️ **Safety Features**

### **Staging Protection**
- Auto-commits prevent losing work
- Automated test verification
- Manual testing checklist
- No direct production access

### **Production Protection**
- Staging tests must pass first
- Explicit confirmation required
- Post-deployment verification
- Emergency rollback available

## 📋 **Railway Environment Setup**

| Environment | Branch | URL | Database |
|-------------|--------|-----|----------|
| **Staging** | `staging` | `rally-staging.up.railway.app` | Staging DB |
| **Production** | `main` | `rally.up.railway.app` | Production DB |

## 🔧 **Commands Quick Reference**

```bash
# Deploy local changes to staging
python deployment/deploy_staging.py

# Test staging environment
python deployment/test_staging_session_refresh.py

# Deploy staging to production
python deployment/deploy_production.py

# Emergency rollback
python deployment/rollback.py

# Check deployment status
python deployment/check_deployment_status.py
```

## ✅ **Current Fix Deployment Status**

Your recent Series 22 performance fixes:
- ✅ **Staging**: Deployed and ready for testing
- ⏳ **Production**: Ready to deploy after staging verification

**Next Steps:**
1. Test the fixes on staging: `https://rally-staging.up.railway.app/mobile/settings`
2. Verify Series/Division field loads instantly
3. If staging works, deploy to production: `python deployment/deploy_production.py`

## 🚨 **Emergency Procedures**

### **If Staging Breaks**
```bash
git checkout staging
git reset --hard HEAD~1  # Revert last commit
git push origin staging --force
```

### **If Production Breaks**
```bash
python deployment/rollback.py
# Or manual rollback:
git checkout main
git reset --hard HEAD~1
git push origin main --force
```

## 📊 **Best Practices**

1. **🧪 Always test staging first** - Never skip staging
2. **📱 Test mobile functionality** - Most users are on mobile
3. **⏱️ Monitor performance** - Watch for slow API calls
4. **📝 Document changes** - Update this guide as needed
5. **🔄 Use feature branches** - Keep main clean

## 🎯 **For Your Current Situation**

Since we just fixed the Series 22 issue:

1. **Test staging now**: Visit settings page, verify instant series loading
2. **If staging works**: Run `python deployment/deploy_production.py`
3. **Verify production**: Check that production also loads instantly

The staging environment should now show Series 22 immediately instead of the 5-second delay! 🚀 