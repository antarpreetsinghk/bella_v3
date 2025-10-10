# 📞 Test Calendar Sync - Step-by-Step Guide

**Objective**: Verify Google Calendar integration works by making a test phone call

---

## 🎯 Option 1: Manual Phone Call Test (RECOMMENDED)

### Step 1: Start Monitoring

**In this terminal**, run the monitoring script:

```bash
./scripts/monitor_test_call.sh
```

This will:
- Monitor production logs in real-time
- Watch database for new appointments
- Detect calendar sync automatically
- Display results when appointment is created

### Step 2: Make the Phone Call

**From your phone**, call:

```
📞 +1 (438) 256-5719
```

### Step 3: Complete the Booking Flow

The system will ask you:

1. **"What's your name?"**
   - Say your name clearly (e.g., "John Smith")

2. **"Did I get that right? [repeats name]"**
   - Say "Yes" to confirm

3. **"What time would you like your appointment?"**
   - Say a time (e.g., "Tomorrow at 2 PM" or "Friday at 10 AM")

4. **"Let me confirm... [repeats details]"**
   - Say "Yes" to confirm and create the appointment

### Step 4: Watch the Monitoring Script

The monitoring script will automatically detect:
- ✅ New appointment created
- ✅ Customer name and phone
- ✅ Appointment time
- ✅ Google Calendar Event ID (if synced)

### Expected Output

```
🎉 NEW APPOINTMENT DETECTED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Appointment Details:
  ID:           2
  Customer:     John Smith
  Phone:        +14165551234
  Time:         2025-10-11 20:00:00+00:00
  Created:      2 seconds ago

✅ GOOGLE CALENDAR SYNC: SUCCESSFUL
Calendar Event ID: abc123xyz456789
View Event: https://calendar.google.com/calendar/event?eid=abc123xyz456789
```

---

## 🤖 Option 2: Automated Test via Twilio API

If you prefer automated testing:

### Step 1: Get Twilio Test Token

You'll need your Twilio auth token from the .env file.

### Step 2: Initiate Test Call via API

```bash
# This requires Twilio credentials from your .env file
curl -X POST https://api.twilio.com/2010-04-01/Accounts/<YOUR_ACCOUNT_SID>/Calls.json \
  --data-urlencode "Url=http://15.157.56.64/twilio/voice" \
  --data-urlencode "To=+14165551234" \
  --data-urlencode "From=<YOUR_TWILIO_PHONE>" \
  -u <YOUR_ACCOUNT_SID>:<YOUR_AUTH_TOKEN>
```

**Note**: Replace placeholders with your actual Twilio credentials from `.env` file.
**Warning**: This creates a real phone call, which will call the "To" number.

---

## 🔍 Manual Verification (If Monitoring Script Fails)

### Check Database for New Appointment

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-db psql -U bella_user -d bella_db -c \"
SELECT
    a.id,
    u.full_name,
    u.mobile,
    a.starts_at,
    a.google_event_id,
    a.created_at
FROM appointments a
JOIN users u ON a.user_id = u.id
ORDER BY a.created_at DESC
LIMIT 3;
\""
```

### Check Application Logs

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 5m 2>&1 | grep -iE 'appointment|calendar'"
```

### Verify Calendar Sync

Look for `google_event_id` in the appointment:
- **If populated** (e.g., `abc123xyz`): ✅ **Calendar sync worked!**
- **If NULL**: ❌ Calendar sync failed - check logs for errors

---

## 🎯 Success Criteria

### ✅ What to Look For

1. **Appointment Created in Database**
   - New row in `appointments` table
   - Correct customer name
   - Correct phone number
   - Correct appointment time

2. **Google Calendar Event Created**
   - `google_event_id` field is populated
   - Event ID looks like: `abc123xyz456789`
   - Event is visible in Google Calendar

3. **No Errors in Logs**
   - No "calendar sync failed" messages
   - No "Google API error" messages
   - No exceptions or errors

### ✅ Complete Success

```
✅ Appointment created in database
✅ google_event_id populated
✅ Event visible in Google Calendar
✅ No errors in application logs
```

---

## 🐛 Troubleshooting

### Issue: "No appointment created"

**Possible causes:**
1. Call didn't complete the full flow
2. Webhook not reaching production server
3. Application error

**Solution:**
```bash
# Check if call was received
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 10m 2>&1 | grep -i 'twilio\|voice\|call'"
```

### Issue: "Appointment created but google_event_id is NULL"

**Possible causes:**
1. Google Calendar credentials issue
2. Calendar API error
3. Network issue

**Solution:**
```bash
# Check for calendar errors
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 10m 2>&1 | grep -iE 'calendar.*error|google.*failed'"

# Verify environment variables
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-app printenv | grep GOOGLE_CALENDAR"
```

### Issue: "Call connects but doesn't respond"

**Possible causes:**
1. Application not running
2. Webhook URL incorrect
3. Network/firewall issue

**Solution:**
```bash
# Check application health
curl http://15.157.56.64/healthz

# Check container status
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker ps --filter name=bella-app"
```

---

## 📊 After Testing

### Verify Calendar Event

1. **Log into Google Calendar** with the service account email:
   - bella-calendar-secure@bella-voice-booking.iam.gserviceaccount.com

2. **Or use Calendar API** to list events:
   ```bash
   # This requires Google Calendar API credentials
   # Check for events created in last hour
   ```

3. **Check event details** match appointment:
   - Event summary includes customer name
   - Event start time matches appointment time
   - Event duration is correct (default: 30 min)

### Document Results

Record the test results:
- [ ] Phone call completed successfully
- [ ] Appointment created in database
- [ ] Google Calendar event created
- [ ] Event ID matches database record
- [ ] Event details are correct
- [ ] No errors in logs

---

## 🎉 If Everything Works

**Congratulations!** Google Calendar integration is working correctly.

**What this means:**
- ✅ All future appointments will automatically sync to Google Calendar
- ✅ Customers will receive calendar invitations
- ✅ You can view all appointments in Google Calendar
- ✅ Calendar events include customer name, phone, and time

### Next Steps

1. **Update Karen's existing appointment** (ID: 1)
   - Currently not synced to calendar
   - Consider manually creating calendar event or re-booking

2. **Monitor sync success rate**
   - Check daily for any sync failures
   - Review logs for errors

3. **Set up alerts** for calendar sync failures
   - Get notified if sync stops working
   - Monitor API quota usage

---

## 📞 Quick Start (TL;DR)

```bash
# Terminal 1: Start monitoring
./scripts/monitor_test_call.sh

# Terminal 2 (or your phone): Call the number
# Call: +1 (438) 256-5719
# Complete the booking flow

# Monitor will show results automatically
```

**Expected result**: New appointment with Google Calendar Event ID ✅

---

## 📚 Related Documentation

- **Deployment Success**: `GOOGLE_CALENDAR_DEPLOYMENT_SUCCESS.md`
- **Security Review**: `SECURITY_REVIEW_CALENDAR_DEPLOYMENT.md`
- **Monitoring Guide**: `docs/PRODUCTION_LOG_MONITORING.md`

---

**Ready to test? Run the monitoring script and make the call!** 📞
