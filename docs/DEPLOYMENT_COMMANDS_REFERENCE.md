# 🎯 Deployment Commands Reference

Quick reference for knowing exactly where your git commands deploy to.

## 📍 **Check Before You Deploy**

```bash
# Show which environment each command targets
git deployment-info
```

This shows:
- ✅ Current branch you're on
- ✅ What each deployment command does  
- ✅ Current deployment status
- ✅ Safety level of each environment

## 🚀 **Deployment Commands**

### **🟡 Deploy to Staging (Safe Testing)**
```bash
git deploy-staging
```
**What it does:**
- Shows staging deployment info
- Asks for confirmation (y/N)
- Merges `main` → `staging` branch
- Pushes to `staging` branch
- Triggers staging deployment workflow
- **Result**: Updates https://rally-staging.up.railway.app

### **🚨 Deploy to Production (Live Users!)**
```bash
git deploy-production  
```
**What it does:**
- Shows production deployment warning
- Requires typing "PRODUCTION" to confirm
- Pushes `main` branch
- Triggers production deployment workflow  
- **Result**: Updates https://rally.up.railway.app ⚠️

### **📊 Check Status**
```bash
git status-deployments
```
**What it shows:**
- Recent commits on main (production) 
- Recent commits on staging
- Current sync status

## 🎨 **Visual Deployment Flow**

```
Your Code Changes
       ↓
   [git add & commit]
       ↓
┌─────────────────┐    ┌─────────────────┐
│  git deploy-    │    │  git deploy-    │
│    staging      │    │   production    │
│                 │    │                 │
│ ✅ Safe Testing │    │ ⚠️ Live Users   │
│ 🟡 Staging      │    │ 🚨 Production   │
│ Can break       │    │ Must work!      │
└─────────────────┘    └─────────────────┘
       ↓                       ↓
🟡 Staging Environment    🚨 Production Environment
rally-staging.up.railway  rally.up.railway.app
```

## 🔍 **How to Tell Which Environment**

### **1. Use the Info Command**
```bash
git deployment-info
```

### **2. Look for Visual Cues**
- **🟡 Yellow** = Staging (safe)
- **🚨 Red** = Production (dangerous)

### **3. Check the URLs**
- **staging** subdomain = Staging environment
- **No subdomain** = Production environment

### **4. Read the Confirmations**
- **Simple y/N** = Staging deployment
- **Must type "PRODUCTION"** = Production deployment

## ⚡ **Quick Commands Summary**

| Command | Environment | Safety | Confirmation |
|---------|-------------|---------|--------------|
| `git deployment-info` | None (info only) | ✅ Safe | None |
| `git deploy-staging` | 🟡 Staging | ✅ Safe | y/N |
| `git deploy-production` | 🚨 Production | ⚠️ Live users | Type "PRODUCTION" |
| `git status-deployments` | None (status) | ✅ Safe | None |

## 🎯 **Best Practice Flow**

```bash
# 1. Check current status
git deployment-info

# 2. Deploy to staging first
git deploy-staging

# 3. Test on staging: https://rally-staging.up.railway.app

# 4. If tests pass, deploy to production
git deploy-production
```

## 🚨 **Emergency: "Oh No, Where Did I Deploy?"**

```bash
# Quick check - where are my recent deployments?
git deployment-info

# Check GitHub Actions to see what's running
# https://github.com/rossfreedman/rally/actions
```

---

**🎯 Remember**: The commands are designed to make it **impossible to accidentally deploy to production**. You'll always know exactly where you're deploying! 