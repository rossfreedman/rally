# 📧 SendGrid Email Notification Setup Guide

## Overview

The Rally platform has been updated to send admin activity notifications via email using Twilio's SendGrid service instead of SMS. This guide explains how to configure and test the new email notification system.

## 🔧 Configuration

### Required Environment Variables

Add these environment variables to your `.env` file or deployment configuration:

```bash
# SendGrid Configuration
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_FROM_EMAIL=noreply@lovetorally.com
SENDGRID_FROM_NAME=Rally Platform
ADMIN_EMAIL=ross@lovetorally.com
SENDGRID_EU_DATA_RESIDENCY=false
```

### Environment Variable Details

- **SENDGRID_API_KEY**: Your SendGrid API key (required)
  - Get this from the [SendGrid Dashboard](https://app.sendgrid.com/settings/api_keys)
  - Should start with `SG.`

- **SENDGRID_FROM_EMAIL**: Email address for sending notifications (optional)
  - Default: `noreply@lovetorally.com`
  - Must be a verified sender in SendGrid

- **SENDGRID_FROM_NAME**: Display name for outgoing emails (optional)
  - Default: `Rally Platform`

- **ADMIN_EMAIL**: Email address to receive activity notifications (optional)
  - Default: `ross@lovetorally.com`
  - This replaces the old `ADMIN_PHONE_NUMBER`

- **SENDGRID_EU_DATA_RESIDENCY**: Enable EU data residency for GDPR compliance (optional)
  - Default: `false`
  - Set to `true` if using an EU-pinned SendGrid subuser
  - Required for EU data residency compliance

## 🚀 Setup Steps

### 1. Get SendGrid API Key

1. Log in to [SendGrid](https://app.sendgrid.com)
2. Navigate to Settings → API Keys
3. Click "Create API Key"
4. Choose "Full Access" or create a restricted key with Mail Send permissions
5. Copy the generated API key (starts with `SG.`)

### 2. Verify Sender Identity

Before sending emails, you need to verify your sender identity in SendGrid:

1. Go to Settings → Sender Authentication
2. Either:
   - **Single Sender Verification**: Verify the email address in `SENDGRID_FROM_EMAIL`
   - **Domain Authentication**: Authenticate the entire domain (recommended for production)

### 3. Update Environment Variables

Add the SendGrid configuration to your environment:

**Local Development (.env file):**
```bash
SENDGRID_API_KEY=SG.your_actual_api_key_here
SENDGRID_FROM_EMAIL=noreply@lovetorally.com
SENDGRID_FROM_NAME=Rally Platform
ADMIN_EMAIL=ross@lovetorally.com
```

**Production (Railway/Server):**
Set these as environment variables in your deployment platform.

### 4. EU Data Residency (Optional)

If you need GDPR compliance or data to stay within the EU:

1. **Create EU Subuser in SendGrid:**
   - Go to Settings → Subuser Management
   - Create a subuser with EU data residency
   - Use the EU subuser's API key

2. **Enable EU Data Residency:**
   ```bash
   SENDGRID_EU_DATA_RESIDENCY=true
   ```

3. **Verify EU Sending:**
   - All emails will be processed through EU data centers
   - Data will remain within the EU for compliance

### 5. Install Dependencies

The SendGrid Python library has been added to `requirements.txt`. Install it:

```bash
pip install sendgrid==6.11.0
```

## 🧪 Testing

### Test Configuration and Email Sending

Use the provided test script to verify everything is working:

```bash
# Test configuration only
python scripts/test_sendgrid_email.py --config-only

# Test in validation mode (no actual emails sent)
python scripts/test_sendgrid_email.py --test-mode

# Send real test emails
python scripts/test_sendgrid_email.py
```

### Manual Testing

You can also trigger activity notifications by:

1. Enabling detailed logging notifications in the admin panel
2. Performing activities on the platform (page visits, form submissions, etc.)
3. Checking the admin email inbox for notifications

## 📋 What Changed

### Before (SMS Notifications)
- Admin received SMS messages via Twilio
- Configured with `ADMIN_PHONE_NUMBER`
- Limited message length and formatting

### After (Email Notifications)
- Admin receives HTML-formatted emails via SendGrid
- Configured with `ADMIN_EMAIL`
- Rich formatting, better readability, and more detailed information
- Includes direct links to admin panel

### Files Modified

1. **`requirements.txt`**: Added `sendgrid==6.11.0`
2. **`config.py`**: Added `SendGridConfig` class
3. **`app/services/notifications_service.py`**: Added email notification functions
4. **`utils/logging.py`**: Updated to use email instead of SMS
5. **`scripts/test_sendgrid_email.py`**: Test script for email functionality

## 🔍 Troubleshooting

### Common Issues

**1. "SendGrid not configured" error**
- Check that `SENDGRID_API_KEY` is set correctly
- Verify the API key starts with `SG.`

**2. "Authentication failed" error**
- Verify your API key has Mail Send permissions
- Check that the API key hasn't expired

**3. "Sender not verified" error**
- Verify the sender email address in SendGrid dashboard
- Or set up domain authentication

**4. Emails not being received**
- Check spam/junk folders
- Verify the `ADMIN_EMAIL` address is correct
- Test with different email addresses

### Debug Commands

```bash
# Check configuration
python -c "from config import SendGridConfig; print(SendGridConfig.validate_config())"

# Test basic functionality
python scripts/test_sendgrid_email.py --test-mode
```

## 📧 Email Format

Admin activity notifications now include:

- **Subject**: Activity type and impersonation status
- **Rich HTML formatting** with tables and styling
- **Activity details**: User, page, action, timestamp
- **Direct link** to admin panel
- **Clear visual indicators** for different activity types

## 🔐 Security Notes

- Store the SendGrid API key securely (never commit to git)
- Use environment variables for all configuration
- Consider using restricted API keys with only Mail Send permissions
- Regularly rotate API keys for security

## 💡 Migration Notes

- The old SMS notification system remains available
- Environment variables can coexist during transition
- The `ADMIN_PHONE_NUMBER` constant is preserved for backwards compatibility
- Email notifications are enabled when SendGrid is properly configured

---

For questions or issues, contact the development team or check the SendGrid documentation.
