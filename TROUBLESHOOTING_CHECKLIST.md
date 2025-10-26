# 🔧 Troubleshooting Checklist

**Purpose:** Quick fixes for common issues during customer testing.

**Rule #1:** Don't panic! Most issues have simple fixes.

---

## 🚨 Issue: "Customer called but nothing happened"

### **Symptoms:**
- Customer says they called
- No appointment was created
- No logs showing the call

### **Diagnosis Steps:**

**Step 1: Check if call reached Twilio**
```bash
# Go to Twilio Console
https://console.twilio.com/us1/monitor/logs/calls

# Search for customer's phone number or time of call
# Check call status and duration
```

**If call NOT in Twilio:**
- ❌ Customer called wrong number
- ❌ Their carrier blocked the call
- → **Fix:** Verify customer has correct number

**If call IS in Twilio but shows error:**
- Check error message in Twilio console
- Common: "Unable to reach webhook URL"
- → Continue to Step 2

---

**Step 2: Check if production server is running**
```bash
curl http://15.157.56.64/healthz
```

**If no response:**
- ❌ Server is down
- → **Fix:** See "Server Not Responding" section below

**If responds:**
- Server is up
- → Continue to Step 3

---

**Step 3: Check if Twilio webhook is configured correctly**

```bash
# Check .env file for correct webhook URL
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "cat ~/bella_v3/.env | grep TWILIO"
```

**Twilio should be configured to call:**
```
http://15.157.56.64/twilio/voice
```

**How to verify in Twilio:**
1. Go to: https://console.twilio.com/
2. Phone Numbers → Manage → Active numbers
3. Click your number
4. Check "Voice & Fax" → "A CALL COMES IN"
5. Should be: `http://15.157.56.64/twilio/voice`

**If wrong URL:**
- → **Fix:** Update in Twilio console

---

**Step 4: Check nginx logs for the request**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-nginx --tail 100 | grep '/twilio/'"
```

**If no logs:**
- ❌ Request never reached nginx
- → **Fix:** Security group may be blocking port 8000

**If you see "403 Forbidden":**
- ❌ Twilio signature validation failed
- → **Fix:** See "Signature Validation Failed" section

**If you see "200 OK":**
- ✅ Request reached server
- → Continue to Step 5

---

**Step 5: Check application logs**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 200 | grep -i twilio"
```

**Look for error messages and follow specific troubleshooting below**

---

## 🔴 Issue: "Signature Validation Failed"

### **Symptoms:**
- Nginx logs show "403 Forbidden"
- App logs show "Invalid Twilio signature"
- Calls don't process

### **Fix:**

**Check TWILIO_AUTH_TOKEN is correct:**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-app env | grep TWILIO_AUTH_TOKEN"
```

**Compare with Twilio Console:**
1. Go to: https://console.twilio.com/
2. Account → Account Info
3. Auth Token (click to reveal)
4. Must match exactly!

**If different:**
```bash
# Update .env file
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
nano ~/bella_v3/.env

# Update TWILIO_AUTH_TOKEN=your_correct_token

# Restart app
cd ~/bella_v3
docker compose -f docker-compose.cost-optimized.yml restart app
```

---

## 🗣️ Issue: "Voice not understanding customer"

### **Symptoms:**
- Customer speaks clearly
- AI says "I didn't catch that"
- Wrong information extracted

### **Common Causes:**

**1. Background Noise**
- Customer calling from noisy environment
- → **Ask:** Can they call from quieter place?

**2. Accent/Pronunciation**
- Canadian French names
- Indian/Asian names
- → **Note for future:** Need better accent handling

**3. Speaking Too Fast**
- → **Ask:** Can they speak slower?

**4. Phone Line Quality**
- Bad cell connection
- → **Ask:** Can they try landline or better signal?

### **Debug:**

```bash
# Check what was captured in logs
docker logs bella-app --tail 200 | grep -i "speech_result"
```

**For now:** Note which names/words cause issues - improve later

---

## 📅 Issue: "Appointment created but not in Google Calendar"

### **Symptoms:**
- Appointment in database
- Customer doesn't see in calendar
- No error messages

### **Diagnosis:**

**Step 1: Check if Google Calendar is enabled**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-app env | grep GOOGLE_CALENDAR_ENABLED"
```

**Should be:** `GOOGLE_CALENDAR_ENABLED=true`

**If false:**
- → **Fix:** Enable in .env file

---

**Step 2: Check Google Calendar credentials**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "ls -la ~/bella_v3/credentials.json"
```

**If file missing:**
- → **Fix:** Re-add credentials.json (see TEST_CALENDAR_SYNC_GUIDE.md)

---

**Step 3: Check calendar sync logs**
```bash
docker logs bella-app --tail 200 | grep -i calendar
```

**Common errors:**

**"Token expired":**
```bash
# Refresh OAuth token
# See TEST_CALENDAR_SYNC_GUIDE.md for re-authentication
```

**"Calendar not found":**
```bash
# Verify GOOGLE_CALENDAR_ID in .env
docker exec bella-app env | grep GOOGLE_CALENDAR_ID
```

**"Insufficient permissions":**
```bash
# Re-authenticate with correct scopes
# See TEST_CALENDAR_SYNC_GUIDE.md
```

---

**Step 4: Manual test**
```bash
# Try creating test event
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
cd ~/bella_v3
# Run test script (see TEST_CALENDAR_SYNC_GUIDE.md)
```

---

## 📱 Issue: "SMS confirmation not received"

### **Symptoms:**
- Appointment created successfully
- Customer didn't get text message
- No error in logs

### **Diagnosis:**

**Step 1: Check Twilio Messages Console**
```
https://console.twilio.com/us1/monitor/logs/messages
```

**Look for:**
- ✅ Message sent? (Status: "delivered")
- ❌ Message failed? (Check error code)
- ⏳ Message pending? (May take 1-2 minutes)

**Common Twilio SMS errors:**
- **21211**: Invalid 'To' phone number
- **21608**: 'To' number not mobile (can't receive SMS)
- **30003**: Unreachable destination
- **30006**: Landline (can't receive SMS)

---

**Step 2: Check phone number format**
```bash
# Check database for how number was stored
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT customer_phone FROM appointments WHERE customer_name LIKE '%[CUSTOMER_NAME]%';"
```

**Should be in E.164 format:** `+16471234567`

**If wrong format:**
- → **Note:** Phone extraction needs improvement
- → **Workaround:** Manually update in database for now

---

**Step 3: Check SMS sending code**
```bash
# Check app logs for SMS attempt
docker logs bella-app --tail 200 | grep -i sms
```

---

## 🐌 Issue: "Response is too slow"

### **Symptoms:**
- Long pauses during call
- Customer has to wait >5 seconds
- Call feels laggy

### **Diagnosis:**

**Step 1: Check server resources**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker stats --no-stream"
```

**If CPU >80% or Memory >80%:**
- ❌ Server overloaded
- → **Fix:** Restart or upgrade instance type

---

**Step 2: Check response times in logs**
```bash
docker logs bella-app --tail 200 | grep -i "response_time\|duration"
```

**Normal:** <2 seconds
**Slow:** >3 seconds

---

**Step 3: Check external API calls**

**OpenAI API (if used):**
- May be slow sometimes
- Check logs for OpenAI call duration

**Google Calendar API:**
- Check logs for calendar sync duration
- May need caching

---

**Temporary workaround:**
```bash
# Restart app to clear any memory issues
cd ~/bella_v3
docker compose -f docker-compose.cost-optimized.yml restart app
```

---

## 🔄 Issue: "Server Not Responding"

### **Symptoms:**
- Can't access http://15.157.56.64/healthz
- Containers not running
- Complete system down

### **Fix:**

**Step 1: Check if containers are running**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker ps"
```

**If no containers running:**
```bash
# Start all services
cd ~/bella_v3
docker compose -f docker-compose.cost-optimized.yml up -d
```

---

**Step 2: Check if containers are healthy**
```bash
docker ps
```

**If status shows "unhealthy":**
```bash
# Check what's wrong
docker logs bella-app --tail 100

# Restart unhealthy container
docker compose -f docker-compose.cost-optimized.yml restart [container-name]
```

---

**Step 3: Check disk space**
```bash
df -h
```

**If disk >90% full:**
```bash
# Clean up Docker
docker system prune -f
docker volume prune -f
```

---

**Step 4: Check if port 8000 is bound**
```bash
ss -tulpn | grep :8000
```

**If no output:**
```bash
# App not listening on port 8000
# Check app logs
docker logs bella-app --tail 100
```

---

**Step 5: Nuclear option - Full restart**
```bash
cd ~/bella_v3
docker compose -f docker-compose.cost-optimized.yml down
docker compose -f docker-compose.cost-optimized.yml up -d

# Wait 60 seconds for startup
sleep 60

# Check health
curl http://localhost:8000/healthz
```

---

## 🗄️ Issue: "Database Connection Error"

### **Symptoms:**
- App logs show "database connection failed"
- Can't create appointments
- 500 errors

### **Fix:**

**Step 1: Check database container**
```bash
docker ps | grep bella-db
```

**If not running:**
```bash
docker compose -f docker-compose.cost-optimized.yml up -d db
```

---

**Step 2: Test database connection**
```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT 1;"
```

**Should return:** `1`

**If fails:**
```bash
# Check database logs
docker logs bella-db --tail 100

# May need to restart
docker compose -f docker-compose.cost-optimized.yml restart db
```

---

**Step 3: Check DATABASE_URL**
```bash
docker exec bella-app env | grep DATABASE_URL
```

**Should be:** `postgresql+asyncpg://bella_user:[password]@db:5432/bella_db`

---

## 📊 Emergency Commands

### **Full System Restart**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
cd ~/bella_v3
docker compose -f docker-compose.cost-optimized.yml restart
```

### **Check All Container Logs**
```bash
docker compose -f docker-compose.cost-optimized.yml logs --tail 50
```

### **View Real-Time Logs (All Containers)**
```bash
docker compose -f docker-compose.cost-optimized.yml logs -f
```

### **Force Recreate Everything**
```bash
cd ~/bella_v3
docker compose -f docker-compose.cost-optimized.yml down
docker compose -f docker-compose.cost-optimized.yml up -d --force-recreate
```

---

## 📞 When to Contact Support

**Call me immediately if:**
- ❌ System completely down for >10 minutes
- ❌ Data loss (appointments disappeared)
- ❌ Security breach suspected
- ❌ Customer is angry and you can't fix it

**Can wait until next day:**
- ⚠️ Slow performance but working
- ⚠️ Minor voice recognition issues
- ⚠️ SMS occasionally not sending
- ⚠️ Calendar sync intermittent

---

## 💡 Prevention Tips

1. **Check health daily:**
```bash
curl http://15.157.56.64/healthz
```

2. **Monitor disk space weekly:**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "df -h"
```

3. **Review error logs weekly:**
```bash
docker logs bella-app --since 168h | grep -i error
```

4. **Restart services weekly (during low-traffic time):**
```bash
docker compose -f docker-compose.cost-optimized.yml restart
```

5. **Keep customer informed:**
   - "I see the issue"
   - "Working on it"
   - "Fixed! Please try again"

---

## 🎯 Issue Resolution Priority

### **Critical (Fix Immediately):**
- System completely down
- No calls being processed
- Database offline

### **High (Fix Within 1 Hour):**
- Calls failing 50%+ of time
- Appointments not being created
- Customer can't use system

### **Medium (Fix Within 24 Hours):**
- Slow performance
- Calendar sync issues
- SMS occasionally failing

### **Low (Fix When You Have Time):**
- Voice recognition could be better
- Minor UI issues
- Feature requests

---

*For log review commands, see: LOG_REVIEW_COMMANDS.md*
*For testing guide, see: QUICK_TEST_GUIDE.md*
