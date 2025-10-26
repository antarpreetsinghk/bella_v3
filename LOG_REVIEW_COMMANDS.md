# 📋 Log Review Commands - Quick Reference

**Purpose:** Fast commands to check what's happening in production during customer testing.

---

## 🚀 Quick Start - One Command to See Everything

```bash
# SSH to production and see overview
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "
echo '=== CONTAINER STATUS ===' &&
docker ps --format 'table {{.Names}}\t{{.Status}}' &&
echo '' &&
echo '=== RECENT APPOINTMENTS ===' &&
docker exec bella-db psql -U bella_user -d bella_db -c 'SELECT id, customer_name, customer_phone, appointment_time, status FROM appointments ORDER BY created_at DESC LIMIT 5;' &&
echo '' &&
echo '=== HEALTH CHECK ===' &&
curl -s http://localhost:8000/healthz
"
```

---

## 🎯 Application Logs (Most Important)

### **Watch Logs in Real-Time (During Test)**

```bash
# Live tail - shows logs as they happen
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app -f --tail 50"
```

**Press Ctrl+C to stop**

---

### **Check Last 100 Lines**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 100"
```

---

### **Search for Specific Call (by phone number)**

```bash
# Replace 6471234567 with actual phone number (no spaces/dashes)
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app | grep '6471234567'"
```

---

### **Check Recent Errors Only**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 200 | grep -i error"
```

---

### **Check Logs from Specific Time**

```bash
# Last 1 hour
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 1h"

# Last 24 hours
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 24h"

# Since specific time (format: 2025-10-14T14:30:00)
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 2025-10-14T14:30:00"
```

---

## 📞 Twilio-Specific Logs

### **See All Twilio Webhook Calls**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 200 | grep -i twilio"
```

---

### **Check Voice Responses Sent**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 200 | grep -i 'TwiML'"
```

---

### **Check Signature Validation**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 200 | grep -i 'signature'"
```

---

## 🗄️ Database Queries

### **SSH to Production First**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
```

Then run these commands:

---

### **Check Recent Appointments**

```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "
SELECT
  id,
  customer_name,
  customer_phone,
  TO_CHAR(appointment_time, 'YYYY-MM-DD HH24:MI') as appointment,
  status,
  TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created
FROM appointments
ORDER BY created_at DESC
LIMIT 10;
"
```

---

### **Count Appointments Today**

```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "
SELECT COUNT(*) as total_today
FROM appointments
WHERE DATE(created_at) = CURRENT_DATE;
"
```

---

### **Count Appointments by Status**

```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "
SELECT status, COUNT(*) as count
FROM appointments
GROUP BY status;
"
```

---

### **Find Specific Customer's Appointments**

```bash
# Replace 6471234567 with actual phone number
docker exec -it bella-db psql -U bella_user -d bella_db -c "
SELECT *
FROM appointments
WHERE customer_phone LIKE '%6471234567%'
ORDER BY created_at DESC;
"
```

---

### **Check Appointments This Week**

```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "
SELECT
  DATE(created_at) as day,
  COUNT(*) as bookings
FROM appointments
WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
GROUP BY DATE(created_at)
ORDER BY day DESC;
"
```

---

## 🔴 Redis Session Data

### **Check Active Sessions**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-redis redis-cli KEYS 'call_session:*'"
```

---

### **Count Total Sessions**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-redis redis-cli KEYS 'call_session:*' | wc -l"
```

---

### **View Specific Session Data**

```bash
# Replace CALL_SID with actual Twilio Call SID
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-redis redis-cli GET 'call_session:CALL_SID'"
```

---

## 🌐 Nginx Logs

### **Check Recent Access (All Requests)**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-nginx --tail 50"
```

---

### **Check Only Twilio Webhook Requests**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-nginx | grep '/twilio/'"
```

---

### **Check for 4xx/5xx Errors**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-nginx | grep -E ' (4[0-9]{2}|5[0-9]{2}) '"
```

---

## 📊 System Health Checks

### **Container Status**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker ps"
```

**Look for:** All containers should show "Up" and "healthy"

---

### **Container Resource Usage**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker stats --no-stream"
```

**Watch for:** CPU/Memory usage shouldn't be >80%

---

### **Disk Space**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "df -h"
```

**Watch for:** Root filesystem shouldn't be >80% full

---

### **Application Health Endpoint**

```bash
# From your local machine
curl http://15.157.56.64/healthz

# Or from production server
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "curl -s http://localhost:8000/healthz"
```

**Expected:** `{"ok":true}`

---

## 🔍 Advanced Debugging

### **See Full Appointment Details (JSON)**

```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "
SELECT row_to_json(appointments.*)
FROM appointments
ORDER BY created_at DESC
LIMIT 1;
"
```

---

### **Check Database Connection**

```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT version();"
```

---

### **Test Redis Connection**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-redis redis-cli PING"
```

**Expected:** `PONG`

---

### **Check App Container Environment Variables** (Careful - may show secrets!)

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-app env | grep -E '(TWILIO|DATABASE|OPENAI)' | sed 's/=.*/=***hidden***/'"
```

---

## 📱 Twilio Console (Manual Check)

**Go to:** https://console.twilio.com/

### **Monitor → Logs → Calls**

**Check:**
- ✅ Call start/end times
- ✅ Duration
- ✅ Status (completed, busy, failed)
- ✅ Recording (if enabled)
- ✅ Error messages

### **Monitor → Logs → Messages**

**Check SMS confirmations:**
- ✅ Message delivered?
- ✅ What was sent?
- ✅ Any delivery errors?

---

## 📥 Save Logs for Later Review

### **Export Application Logs**

```bash
# Save last 1000 lines to file
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 1000" > bella_app_logs_$(date +%Y%m%d_%H%M%S).txt
```

---

### **Export Database Data**

```bash
# Export all appointments to CSV
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker exec bella-db psql -U bella_user -d bella_db -c \"COPY (SELECT * FROM appointments ORDER BY created_at DESC) TO STDOUT WITH CSV HEADER;\"" > appointments_$(date +%Y%m%d).csv
```

---

## 🎯 Common Scenarios

### **Scenario 1: Customer says "I called but nothing happened"**

```bash
# 1. Check nginx logs for their phone number
docker logs bella-nginx | grep [PHONE_NUMBER]

# 2. Check app logs for their call
docker logs bella-app | grep [PHONE_NUMBER]

# 3. Check if webhook even received
docker logs bella-app | grep -i "twilio webhook"

# 4. Check Twilio console for the call
```

---

### **Scenario 2: "Appointment wasn't created"**

```bash
# 1. Search database for customer name
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT * FROM appointments WHERE customer_name ILIKE '%[NAME]%';"

# 2. Check app logs for errors during booking
docker logs bella-app --tail 200 | grep -i error

# 3. Check Redis session to see what data was collected
docker exec bella-redis redis-cli KEYS 'call_session:*'
```

---

### **Scenario 3: "Voice was garbled/unclear"**

```bash
# This is usually Twilio-side issue
# 1. Check call quality in Twilio console
# 2. Check app logs for any timeout/connection issues
docker logs bella-app --tail 200 | grep -i timeout

# 3. Check server resources weren't maxed out
docker stats --no-stream
```

---

## 🚨 Emergency Commands

### **Restart Application (If Frozen)**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "cd ~/bella_v3 && docker compose -f docker-compose.cost-optimized.yml restart app"
```

---

### **Restart All Services**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "cd ~/bella_v3 && docker compose -f docker-compose.cost-optimized.yml restart"
```

---

### **Check if Port 8000 is Responding**

```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "nc -zv localhost 8000"
```

---

## 💡 Pro Tips

1. **Keep a terminal open during testing**
   - Run: `docker logs bella-app -f`
   - Watch in real-time

2. **Use grep with color for easier reading**
   ```bash
   docker logs bella-app --tail 100 | grep --color=always -i error
   ```

3. **Create aliases for common commands**
   ```bash
   alias bella-logs="ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 'docker logs bella-app -f --tail 50'"
   alias bella-status="ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 'docker ps'"
   ```

4. **Use `screen` or `tmux` for persistent sessions**
   - Logs keep running even if you disconnect

5. **Check logs chronologically**
   - Logs have timestamps - follow the timeline

---

## 📞 Quick Command Cheat Sheet

```bash
# Most useful during testing
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app -f"           # Live logs
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker ps"                          # Container status
curl http://15.157.56.64/healthz                                                   # Health check

# Most useful after testing
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --tail 200 | grep -i error"  # Find errors
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT * FROM appointments ORDER BY created_at DESC LIMIT 5;"  # Recent bookings
```

---

*For troubleshooting specific issues, see: TROUBLESHOOTING_CHECKLIST.md*
*For testing steps, see: QUICK_TEST_GUIDE.md*
