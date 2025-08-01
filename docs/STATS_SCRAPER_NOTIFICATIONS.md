# Stats Scraper Notification System

## 📱 **Overview**

The stats scraper now includes **SMS notifications** to alert you when the scraper doesn't achieve 100% success rate. You'll receive notifications via Twilio SMS to your phone number.

## 🎯 **Notification Triggers**

### **✅ Perfect Success (100%)**
- **Trigger**: All series processed successfully
- **Message**: 🎉 Success notification with stats
- **Example**: `"🎉 Stats Scraper: NSTF ✅ Success Rate: 100.0% Series: 5/5 Teams: 28"`

### **⚠️ Good Success with Warnings (80-99%)**
- **Trigger**: Most series successful, some failures
- **Message**: ⚠️ Warning notification with failed series
- **Example**: `"⚠️ Stats Scraper: NSTF ⚠️ Success Rate: 80.0% Series: 4/5 Failed: 1 Failed Series: Series 2B"`

### **🚨 Poor Success Rate (<80%)**
- **Trigger**: Significant failures
- **Message**: ❌ Alert notification with details
- **Example**: `"🚨 Stats Scraper: NSTF ❌ Success Rate: 40.0% Series: 2/5 Failed: 3 Failed Series: Series 2A, Series 2B, Series 3"`

### **💥 Complete Failure (0%)**
- **Trigger**: No series processed successfully
- **Message**: 🚨 Critical failure with error details
- **Example**: `"🚨 Stats Scraper: NSTF ❌ Success Rate: 0.0% Error: ScraperAPI timeout after multiple retries"`

## 📊 **Information Included**

Each notification includes:
- **Success Rate**: Percentage of series processed successfully
- **Series Count**: `X/Y` format (successful/total)
- **Failed Count**: Number of failed series
- **Failed Series**: Names of failed series (up to 3, then "+X more")
- **Teams Processed**: Total number of teams scraped
- **Duration**: Total scraping time
- **Error Details**: Error message for complete failures

## 🔧 **Configuration**

### **Phone Number**
The notification system uses your phone number:
```python
ADMIN_PHONE = "17736121115"  # Ross's phone number
```

### **Twilio Integration**
Uses the existing Twilio SMS service with:
- **Retry Logic**: Handles temporary failures
- **Error 21704**: Special handling for Twilio infrastructure issues
- **Fallback**: MMS if SMS fails

## 🧪 **Testing**

You can test the notification system:

```bash
python scripts/test_stats_notification.py
```

This will send test notifications for different scenarios:
1. **Perfect Success** (100%)
2. **Good Success** (80%)
3. **Poor Success** (40%)
4. **Complete Failure** (0%)

## 📈 **Real-World Examples**

### **From Your Recent NSTF Scrape:**
```
⚠️ Stats Scraper: NSTF ⚠️
Success Rate: 80.0%
Series: 4/5
Failed: 1
Failed Series: Series 2B
Teams: 22
Duration: 0:06:17
```

### **Complete Failure Example:**
```
🚨 Stats Scraper: NSTF ❌
Success Rate: 0.0%
Series: 0/5
Failed: 5
Failed Series: Series A, Series 1, Series 2A, Series 2B, Series 3
Error: ScraperAPI timeout after multiple retries...
Teams: 0
Duration: 0:01:30
```

## 🎯 **Benefits**

1. **Immediate Awareness**: Know instantly if scraping had issues
2. **Detailed Information**: See exactly which series failed
3. **Performance Tracking**: Monitor success rates over time
4. **Error Diagnosis**: Get error details for troubleshooting
5. **Proactive Response**: Take action when needed

## 🔄 **Integration**

The notification system is automatically integrated into:
- **Successful completions**: Sends summary with success rate
- **Partial failures**: Alerts with failed series details
- **Complete failures**: Critical alerts with error information
- **Exception handling**: Notifies on unexpected errors

## 📱 **Message Format**

All notifications follow this format:
```
[EMOJI] Stats Scraper: [LEAGUE] [STATUS]
Success Rate: [X.X]%
Series: [X/Y]
Failed: [X]
Failed Series: [LIST] (if any)
Teams: [X]
Duration: [TIME]
Error: [DETAILS] (if failure)
```

## ✅ **Summary**

**YES - You will now get notified when the scraper doesn't achieve 100% success!**

The system provides:
- ✅ **Immediate SMS alerts** for any issues
- ✅ **Detailed failure information** 
- ✅ **Success rate tracking**
- ✅ **Error diagnosis**
- ✅ **Performance monitoring**

You'll never miss a scraping issue again! 🎉 