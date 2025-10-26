# 📊 Uptime Monitoring Setup Guide

## Overview
Set up free uptime monitoring to get alerts when your API goes down (and prevent embarrassing situations with recruiters!).

---

## 🚀 Quick Setup (5 minutes)

### 1. Create UptimeRobot Account (Free)

1. Go to: https://uptimerobot.com
2. Click "Register for FREE"
3. Verify your email

**Free Tier Includes:**
- ✅ 50 monitors
- ✅ 5-minute check intervals
- ✅ Email/SMS alerts
- ✅ Public status pages
- ✅ No credit card required

---

### 2. Add Monitors

#### Monitor 1: Health Endpoint (Primary)
```
Monitor Type: HTTP(s)
Friendly Name: Bella API - Health Check
URL: http://15.157.56.64/healthz
Monitoring Interval: 5 minutes
Alert Contacts: Your email
```

#### Monitor 2: API Documentation (Secondary)
```
Monitor Type: HTTP(s)
Friendly Name: Bella API - Docs
URL: http://15.157.56.64/docs
Monitoring Interval: 5 minutes
Alert Contacts: Your email
```

#### Monitor 3: LLM Demo (Optional)
```
Monitor Type: HTTP(s)
Friendly Name: Bella API - LLM Demo
URL: http://15.157.56.64/llm-demo/status
Monitoring Interval: 5 minutes
Alert Contacts: Your email
```

---

### 3. Configure Alert Settings

**Settings → Alert Contacts:**
- Email: Your email (primary)
- Optional: Add phone number for SMS alerts
- Optional: Slack/Discord webhook for team notifications

**Recommended Alert Schedule:**
- Send alerts when down: **Immediately**
- Send recovery notification: **Yes**
- Maximum notifications: **Unlimited** (free tier allows this)

---

### 4. Create Public Status Page (Optional but Impressive!)

**Why Add a Status Page?**
- Shows uptime % to recruiters
- Demonstrates production monitoring skills
- Professional touch for portfolio

**Setup:**
1. UptimeRobot → Status Pages → Add Status Page
2. Select monitors to display
3. Choose subdomain: `bella-api.statuspage.io` (or custom domain)
4. Make it public

**Add to README.md:**
```markdown
[![Uptime Status](https://img.shields.io/uptimerobot/ratio/7/m123456789-YOUR_MONITOR_ID)](https://stats.uptimerobot.com/YOUR_PAGE_ID)
```

---

## 📱 Alert Response Procedure

### When You Get an Alert

**1. Check Alert Details**
- What endpoint is down?
- How long has it been down?
- Is it a real outage or false positive?

**2. Quick Diagnosis**
```bash
# From your local machine
bash scripts/diagnose_deployment.sh
```

**3. Common Fixes**

**If EC2 Stopped:**
```bash
bash scripts/fix_deployment.sh
# Follow prompts to start instance
```

**If Containers Stopped:**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
cd bella_v3
docker-compose -f docker-compose.cost-optimized.yml up -d
```

**If Application Crashed:**
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
docker logs bella-app --tail 100
# Check for errors, restart if needed
docker restart bella-app
```

**4. Verify Recovery**
```bash
curl http://15.157.56.64/healthz
# Should return: {"ok":true}
```

---

## 📊 Monitoring Dashboard

### UptimeRobot Dashboard View

Log in to see:
- **Uptime %**: Last 24h, 7 days, 30 days
- **Response Time**: Average API response time
- **Downtime Events**: When and why it went down
- **Alerts Sent**: History of all notifications

**Aim For:**
- ✅ 99%+ uptime (shows reliability to recruiters)
- ✅ <500ms response time
- ✅ <3 downtime events per month

---

## 🎯 Advanced Monitoring (Optional)

### CloudWatch Integration (Already Configured)

Your application already logs to CloudWatch:
- View logs: AWS Console → CloudWatch → Log Groups → `/bella/application`
- Metrics: Custom business metrics, API response times
- Alarms: Can set up AWS SNS alerts

### Local Monitoring Script

Add to your crontab for self-monitoring:
```bash
# Add this to crontab (crontab -e)
*/5 * * * * curl -s http://15.157.56.64/healthz || echo "API Down!" | mail -s "Bella API Alert" your@email.com
```

---

## 🎓 For Interview Discussions

When recruiters ask about monitoring:

**Good Answer:**
> "I use UptimeRobot for external health checks with 5-minute intervals and email alerts. The application also has Docker health checks configured for automatic container restarts. All services use `restart: unless-stopped` policies to recover from failures automatically. For production metrics, I integrate with AWS CloudWatch for detailed logging and performance tracking."

**Show Them:**
- ✅ UptimeRobot dashboard with uptime %
- ✅ Status page (if you created one)
- ✅ Docker-compose health check configuration
- ✅ CloudWatch logs (if interviewing for AWS roles)

---

## 📋 Monitoring Checklist

**Initial Setup:**
- [ ] UptimeRobot account created
- [ ] Health endpoint monitor added
- [ ] Docs endpoint monitor added (optional)
- [ ] Email alerts configured
- [ ] Test alert received (pause monitor to test)
- [ ] Status page created (optional)
- [ ] Status badge added to README (optional)

**Monthly Maintenance:**
- [ ] Review uptime % (should be >99%)
- [ ] Check for downtime patterns (time of day, day of week)
- [ ] Verify alerts are working (test monthly)
- [ ] Review CloudWatch logs for errors

---

## 🚨 Troubleshooting

### Not Receiving Alerts?

1. Check spam folder
2. Verify email in UptimeRobot settings
3. Test alert by manually pausing monitor
4. Check alert contact settings (enabled?)

### False Positives?

1. Check monitor timeout settings (increase if needed)
2. Verify endpoint is truly accessible (not just from your IP)
3. Check response time - slow != down
4. Consider using keyword monitoring (check response contains "ok")

### Status Badge Not Working?

1. Get monitor ID from UptimeRobot → Monitors → Select monitor → Settings
2. Use format: `https://img.shields.io/uptimerobot/ratio/7/m123456789`
3. Verify monitor is set to "Public" in settings

---

## 💰 Cost

**Free Tier (Recommended for Portfolio):**
- 50 monitors
- 5-minute intervals
- Email alerts
- **Cost: $0/month**

**Paid Tier (If You Go Pro):**
- 1-minute intervals
- SMS alerts
- Custom domain status page
- **Cost: $7-18/month**

**Recommendation:** Free tier is perfect for portfolio projects!

---

## 📞 Support Resources

- UptimeRobot Docs: https://blog.uptimerobot.com/how-to-set-up-a-monitor/
- Status: https://status.uptimerobot.com/
- Support: support@uptimerobot.com

---

**Last Updated:** October 2025
**Estimated Setup Time:** 5-10 minutes
**Maintenance Time:** 5 minutes/month
