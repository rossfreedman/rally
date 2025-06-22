# Rally Staging Environment Setup Guide

This guide documents the complete staging environment setup for the Rally platform tennis management application.

## 🎯 Overview

The staging environment provides:
- **Isolated testing environment** with separate database
- **Automated deployments** from `staging` branch via GitHub Actions
- **Production-like data** with sanitized/anonymized PII
- **Environment-specific configuration** (debug mode, staging URLs)

## 🏗️ Architecture

```
Production Environment          Staging Environment
├── rally.up.railway.app       ├── rally-staging.up.railway.app
├── Production Database         ├── Staging Database (separate)
├── FLASK_ENV=production        ├── FLASK_ENV=staging
└── DEBUG=False                 └── DEBUG=True
```

## ✅ Setup Completed

### 1. Railway Environment Configuration

- ✅ **Staging environment created** (`staging`)
- ✅ **Separate PostgreSQL database** provisioned
- ✅ **Environment variables configured**:
  - `FLASK_ENV=staging`
  - `DEBUG=True`
  - `DATABASE_URL` pointing to staging database
  - All production secrets duplicated

### 2. GitHub Actions Deployment

- ✅ **Deployment workflow** (`.github/workflows/deploy-staging.yml`)
- ✅ **Automatic deployment** on push to `staging` branch
- ✅ **Manual deployment** via GitHub Actions (workflow_dispatch)
- ✅ **Health checks and smoke tests**

### 3. Data Migration Script

- ✅ **Production data import script** (`scripts/populate_staging_from_production.py`)
- ✅ **PII sanitization** (emails, phone numbers)
- ✅ **Data integrity verification**
- ✅ **Automatic backups** before import

## 🚀 Using the Staging Environment

### Accessing Staging

- **URL**: https://rally-staging.up.railway.app
- **Environment**: Staging-specific configuration
- **Database**: Isolated from production

### Deploying to Staging

#### Option 1: Push to Staging Branch
```bash
# Create and push to staging branch
git checkout -b staging
git push origin staging
```

#### Option 2: Manual Deployment via GitHub Actions
1. Go to GitHub Actions → "Deploy to Staging"
2. Click "Run workflow"
3. Optionally enable "Force deploy" if tests fail

### Managing the Staging Database

#### Get Railway Connection Details
```bash
# Switch to staging environment
railway environment staging

# Get database connection details
railway service "Rally Staging Database"
railway variables
```

#### Populate with Production Data
```bash
# Set environment variables
export PRODUCTION_DATABASE_URL="postgresql://..."
export STAGING_DATABASE_URL="postgresql://..."

# Run data population script
python scripts/populate_staging_from_production.py
```

## 🔒 Security & Privacy

### Data Sanitization Features
- **Email anonymization**: `john.doe@example.com` → `user1234@example.com`
- **Phone number masking**: `555-123-4567` → `555-XXXX-XXXX`
- **Auth table exclusion**: User passwords and sessions not copied
- **Sensitive comment removal**: SQL comments marked as sensitive

### Environment Isolation
- **Separate databases**: Production and staging never cross-connect
- **Different domains**: Clear visual distinction
- **Debug mode enabled**: Additional logging for troubleshooting

## 🔧 Configuration Details

### Environment Variables (Staging)

```bash
# Application Configuration
FLASK_ENV=staging
DEBUG=True

# Database (Staging-specific)
DATABASE_URL=postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@postgres.railway.internal:5432/railway

# Railway Configuration
RAILWAY_ENVIRONMENT=staging
RAILWAY_PUBLIC_DOMAIN=rally-staging.up.railway.app

# Secrets (Duplicated from Production)
FLASK_SECRET_KEY=9e38fb9f66c13c4892d8ef60996f4d97730309fed9b6e68fdc23dfc36a3ef58b
OPENAI_API_KEY=sk-proj-...
OPENAI_ASSISTANT_ID=asst_Q6GQOccbb0ymf9IpLMG1lFHe
```

### GitHub Secrets Required

Add these secrets to your GitHub repository:

```bash
RAILWAY_TOKEN=<your-railway-token>
```

To get your Railway token:
```bash
railway login
railway auth
```

## 📋 Deployment Workflow

### Automated Process (on `staging` branch push):

1. **Pre-deployment Tests**
   - Code linting (flake8)
   - Unit tests
   - Database setup verification

2. **Railway Deployment**
   - `railway up --environment staging --detach`
   - Deployment status monitoring
   - Health check verification

3. **Post-deployment Verification**
   - HTTP health endpoint test
   - Basic smoke tests
   - Deployment summary generation

### Manual Interventions

If deployment fails:
1. Check GitHub Actions logs
2. Verify Railway environment status
3. Test locally with staging database URL
4. Use "Force deploy" option if needed

## 🐛 Troubleshooting

### Common Issues

#### Deployment Fails with Database Connection Error
```bash
# Check staging database status
railway environment staging
railway service "Rally Staging Database"
railway logs
```

#### Tests Fail in GitHub Actions
```bash
# Run tests locally first
pytest tests/ -v -m "unit" --tb=short
```

#### Data Population Script Errors
```bash
# Check database URLs are correct
echo $PRODUCTION_DATABASE_URL
echo $STAGING_DATABASE_URL

# Verify pg_dump and psql are available
which pg_dump
which psql
```

### Health Check Endpoints

Test staging environment health:
```bash
curl https://rally-staging.up.railway.app/health
curl https://rally-staging.up.railway.app/health/routes
```

## 📝 Maintenance Tasks

### Regular Maintenance

1. **Weekly**: Refresh staging data from production
2. **After major schema changes**: Update data migration script
3. **Monthly**: Review and cleanup old staging backups

### Updating Staging Data

```bash
# Full refresh with latest production data
python scripts/populate_staging_from_production.py

# Check data freshness
railway environment staging
railway service rally
# Access staging app and verify data currency
```

### Schema Updates

When production schema changes:
1. Update migration scripts
2. Deploy to staging first
3. Test data population script
4. Verify application functionality

## 🎭 Testing Strategy

### Use Staging For:
- ✅ Feature testing before production
- ✅ Integration testing with real-like data
- ✅ Performance testing
- ✅ User acceptance testing
- ✅ Database migration testing

### Don't Use Staging For:
- ❌ Long-term data storage
- ❌ Production user testing
- ❌ Storing real PII data
- ❌ Load testing without coordination

## 🔄 Development Workflow

### Recommended Flow:
1. **Development** → Local testing
2. **Feature branch** → Create PR
3. **PR review** → Automated tests run
4. **Merge to staging** → Deploy to staging
5. **Staging testing** → Manual QA
6. **Merge to main** → Deploy to production

### Branch Strategy:
```
main (production)
├── staging (staging environment)
├── feature-branches (development)
└── hotfix-branches (urgent fixes)
```

## 📞 Support

### Getting Help
- Check Railway dashboard for service status
- Review GitHub Actions logs for deployment issues
- Check staging application logs: `railway logs --environment staging`
- Refer to production troubleshooting guides

### Escalation Process
1. Check this guide and troubleshooting section
2. Review recent deployment logs
3. Test against local development environment
4. Contact system administrator if infrastructure issues

---

## 🎉 Success! Your staging environment is ready.

**Staging URL**: https://rally-staging.up.railway.app
**Deployment**: Automatic on push to `staging` branch
**Data**: Can be populated from production (sanitized)

Happy testing! 🏓 