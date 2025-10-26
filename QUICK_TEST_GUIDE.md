# 🚀 Quick Test Guide - Real Customer Trial

**Goal:** Test your voice booking system with a real customer TODAY using existing logs.

**Time Required:** 30 minutes testing + 15 minutes review

---

## ✅ Phase 1: Pre-Flight Check (Test Yourself First)

### **Step 1: Verify Production is Running**

```bash
# Check all containers are healthy
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker ps"

# Check health endpoint
curl http://15.157.56.64/healthz
```

**Expected:** All containers show "healthy" status, health endpoint returns `{"ok":true}`

---

### **Step 2: Test Call Yourself (5-10 minutes)**

**Your Twilio Number:** Check `.env` file for `TWILIO_PHONE_NUMBER`

**Test Scenario 1: Successful Booking**
1. Call your Twilio number from your phone
2. Follow voice prompts
3. Provide:
   - Your name: "John Test"
   - Date: "Tomorrow"
   - Time: "2 PM"
   - Phone: Your actual number

**What to Check:**
- ✅ Voice is clear and understandable
- ✅ AI understands your responses
- ✅ Confirmation is spoken correctly
- ✅ You receive SMS confirmation

**Test Scenario 2: Different Time Formats**
1. Call again
2. Try: "Next Tuesday at 3:30 PM"
3. Try: "This Friday morning at 10"

**Test Scenario 3: Canadian Accent Names**
1. Call again
2. Use names like: "François Dubois", "Preet Singh"
3. Verify pronunciation and spelling

---

### **Step 3: Verify Data Was Created**

```bash
# SSH to production
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64

# Check database for your test appointments
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT id, customer_name, customer_phone, appointment_time, status FROM appointments ORDER BY created_at DESC LIMIT 5;"
```

**Expected:** Your test appointments should appear

---

### **Step 4: Check Google Calendar**

1. Open your Google Calendar
2. Check if test appointments appear
3. Verify details are correct (name, time, phone)

**If appointments missing:** Check calendar sync logs (see LOG_REVIEW_COMMANDS.md)

---

## 👥 Phase 2: Real Customer Test

### **Before You Call Customer:**

**Prepare:**
- ✅ All self-tests passed
- ✅ You have customer's phone number
- ✅ You know customer's business hours
- ✅ You have notebook ready for feedback

---

### **Step 1: Introduction Call (5 minutes)**

**What to Say:**

```
"Hi [Customer Name],

I'm ready to start the free trial of the 24/7 voice booking system.
Here's how it works:

1. Your customers call [YOUR TWILIO NUMBER]
2. An AI voice assistant takes their booking
3. Appointments automatically appear in your Google Calendar
4. They receive SMS confirmation

This is a FREE trial for one month - we're testing it with real
customers to make sure everything works perfectly.

Can we do a quick test right now together? I'll stay on the line
and you can call the booking number to see how it works."
```

---

### **Step 2: Live Test with Customer (10 minutes)**

**Option A: Customer Tests While You Listen**
1. Ask customer to call booking number
2. You stay on phone with them (using different device)
3. They walk through booking process
4. Ask them to describe what's happening

**Option B: You Demonstrate First**
1. You call booking number (speaker phone)
2. Book appointment while customer listens
3. Show them appointment in calendar
4. Then ask them to try themselves

---

### **Step 3: Monitor in Real-Time**

**Open terminal and watch logs:**

```bash
# In one terminal - watch application logs
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app -f --tail 50"

# In another terminal - watch nginx logs
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-nginx -f --tail 20"
```

**Watch for:**
- ✅ Twilio webhook requests coming in
- ✅ Voice input being processed
- ✅ Appointment creation logs
- ❌ Any error messages (note them down)

---

### **Step 4: Immediate Verification**

**After call ends:**

1. **Check appointment created:**
```bash
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT * FROM appointments WHERE customer_phone LIKE '%[LAST 4 DIGITS]%' ORDER BY created_at DESC LIMIT 1;"
```

2. **Check customer received SMS:**
   - Ask customer if they got text message
   - What did it say?
   - Was it clear and professional?

3. **Check calendar:**
   - Refresh Google Calendar
   - Is appointment there?
   - Are details correct?

---

### **Step 5: Collect Feedback (5 minutes)**

**Ask Customer (use CUSTOMER_FEEDBACK_TEMPLATE.md):**

1. "On a scale of 1-10, how easy was that to use?"
2. "Did the voice sound natural and professional?"
3. "Did it understand you correctly?"
4. "Would your customers be comfortable using this?"
5. "What would you want different or better?"

**Write down EVERYTHING they say** - this is gold!

---

## 🎯 Phase 3: Daily Testing Schedule

### **Week 1: Light Monitoring**

**Every Morning (5 minutes):**
```bash
# Check yesterday's calls
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64 "docker logs bella-app --since 24h | grep -i appointment | tail -20"

# Check database for new appointments
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT COUNT(*), DATE(created_at) FROM appointments GROUP BY DATE(created_at) ORDER BY DATE(created_at) DESC LIMIT 7;"
```

**Every Evening (2 minutes):**
- Quick call to customer: "How's it going? Any issues?"
- Note any feedback

---

### **Week 2-4: Ongoing Monitoring**

**Monday, Wednesday, Friday (10 minutes each):**
- Review logs for errors
- Check appointment success rate
- Talk to customer for feedback

**End of Each Week:**
- Generate simple report:
  - Total calls this week
  - Successful bookings
  - Issues encountered
  - Customer feedback summary

---

## 🚨 When Things Go Wrong

**If customer reports issue:**

1. **Don't panic** - this is trial phase, issues are expected
2. **Get details:**
   - When did it happen? (date/time)
   - What phone number called?
   - What went wrong exactly?

3. **Check logs immediately:**
```bash
# Find calls from that time
docker logs bella-app --since [DATE] --until [DATE] | grep [PHONE_NUMBER]
```

4. **Check Twilio Console:**
   - Go to https://console.twilio.com/
   - Monitor → Logs → Calls
   - Find the specific call
   - See recording and details

5. **Follow TROUBLESHOOTING_CHECKLIST.md**

6. **Keep customer informed:**
   - "Thanks for letting me know"
   - "I'm looking into it right now"
   - "I'll have this fixed within [TIMEFRAME]"

---

## 📊 Success Metrics

### **What "Success" Looks Like:**

**Week 1:**
- ✅ 5+ successful bookings
- ✅ Customer says "This is helpful"
- ✅ <2 major issues
- ✅ Response time < 3 seconds

**By End of Month:**
- ✅ 50+ successful bookings
- ✅ Customer wants to pay $450/month
- ✅ 90%+ success rate
- ✅ Clear understanding of improvements needed

---

## 🎯 Next Steps After Successful Trial

**If trial goes well:**

1. ✅ Add HTTPS (domain name + Let's Encrypt)
2. ✅ Implement enhanced logging system
3. ✅ Add monitoring alerts
4. ✅ Create service agreement
5. ✅ Start charging $450 CAD/month

**Use this trial to:**
- Prove the concept works
- Identify pain points
- Gather feature requests
- Build confidence for paid service

---

## 📞 Quick Reference

### **Production Server:**
```
IP: 15.157.56.64
SSH: ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
Health: http://15.157.56.64/healthz
```

### **Key Commands:**
```bash
# Check status
docker ps

# View recent logs
docker logs bella-app --tail 100

# Check recent appointments
docker exec -it bella-db psql -U bella_user -d bella_db -c "SELECT * FROM appointments ORDER BY created_at DESC LIMIT 5;"

# Restart if needed
cd ~/bella_v3 && docker compose -f docker-compose.cost-optimized.yml restart app
```

### **Important Files:**
- Logs: `LOG_REVIEW_COMMANDS.md`
- Troubleshooting: `TROUBLESHOOTING_CHECKLIST.md`
- Feedback: `CUSTOMER_FEEDBACK_TEMPLATE.md`

---

## 💡 Pro Tips

1. **Record the first test call** (with customer permission)
   - Helps debug issues later
   - Can show to future customers

2. **Keep a simple spreadsheet:**
   - Date | Time | Caller | Success? | Issues | Notes

3. **Set expectations with customer:**
   - "This is trial - some bumps expected"
   - "Your feedback helps improve it"
   - "Free month = we're learning together"

4. **Be responsive:**
   - Check in daily first week
   - Fix issues same day if possible
   - Show customer you care

5. **Celebrate wins:**
   - First successful booking? Awesome!
   - Customer says it's helpful? Document it!
   - No issues for 3 days? Progress!

---

## 🚀 Ready to Start?

**Checklist before customer call:**

- [ ] Ran self-tests (Phase 1)
- [ ] All tests passed
- [ ] Have customer's contact info
- [ ] Know what to say (Step 1 script)
- [ ] Have LOG_REVIEW_COMMANDS.md open
- [ ] Have TROUBLESHOOTING_CHECKLIST.md ready
- [ ] Notebook ready for feedback
- [ ] Calm and confident! 😊

**You got this! Go make your first sale! 🎉**

---

*Last Updated: October 2025*
*For questions or issues, review TROUBLESHOOTING_CHECKLIST.md*
