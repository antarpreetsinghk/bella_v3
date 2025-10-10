# SSH Key Authentication Setup for Production Access

## 🎯 Goal
Set up SSH key authentication to access production server (15.157.56.64) for database verification and monitoring.

---

## ✅ Step 1: Your SSH Key is Ready!

**SSH Key Pair Located:**
- **Private Key**: `~/.ssh/bella-voice-app`
- **Public Key**: `~/.ssh/bella-voice-app.pub`

**Your Public Key:**
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC40njTzRB4pzp5ZaEvjpc375qJK5E/ozkpxHP868iqxcvg8rylAbLTp44fVXGf64YMzTYW3reHfBpGgQo/Bfbd2VkRUbYj3HfLqYK+iryIpk7jbEMH/AeNj5DoWsMm2PVRc/KKU5LOrky4CB0Sy0OeTJ0jmIUVR4o5mUSpv0JLbfP3fdMoLdZsS+YBqR5bcikXN8Rhb12i/4Ib3379YVTsD2BUg0lRCdZNau4Mmfd/TOXQgy32qgJyiYFc/JcR6AMJkpri1kQpXk7xgzYePiPekPt3ddzazHQImxgMqBBZ4ktfQumA0DA6PnmIu5Pd2x4vuCulR66DgVMObaH4U4QShcx46LaxZxc1rfVtROmso+HAAnqIDEcdVAADck/BK8kqeO6uL2U44pn0rwySIDPDufDzWDxSwjJBpiEQ6ozzSxBxMTLioyDFqSpPqtatzK0u4hHmdiOj1k7dno5MbbEbfgwuUlIvYNGbWX/UEGfPv4GI+6ZCPZsDzn8/BviOzOOxtocyBp9LEJgO0BF4XCcWwBF2/ADWc/Rr8n7VokH/W5UeyJWtgopDdNhhzXVZx0F2JhNXvpEuj6ASt8vuYnN/V0poHHNEBG5IJnTh5DIkRpM6jquI7MRbIOQ1s74b3eNwxKab4puE8eyXS/jLLB6RbEzXZ67Ntil3VolvNsfDNQ== antarpreet@fedora
```

---

## 🔧 Step 2: Add Public Key to Production Server

### Option A: Using ssh-copy-id (Easiest)

**If you have password access to the server:**

```bash
ssh-copy-id -i ~/.ssh/bella-voice-app.pub <your-user>@15.157.56.64
```

You'll be prompted for your password, then the key will be automatically added.

### Option B: Manual Copy

**If ssh-copy-id doesn't work:**

1. **Copy the public key to clipboard:**
   ```bash
   cat ~/.ssh/bella-voice-app.pub
   ```
   (Copy the entire output)

2. **SSH into production with password:**
   ```bash
   ssh <your-user>@15.157.56.64
   ```

3. **On the production server, run:**
   ```bash
   # Create .ssh directory if it doesn't exist
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh

   # Add your public key
   echo 'ssh-rsa AAAAB3NzaC1yc2E... (paste full key here)' >> ~/.ssh/authorized_keys

   # Set correct permissions
   chmod 600 ~/.ssh/authorized_keys

   # Exit the server
   exit
   ```

### Option C: If You Have Root Access

**If you need to add the key for a specific user:**

```bash
# SSH as root or sudo user
ssh root@15.157.56.64

# Add key for specific user (e.g., 'user' or 'ubuntu')
mkdir -p /home/<username>/.ssh
echo 'ssh-rsa AAAAB3NzaC1yc2E... (paste key)' >> /home/<username>/.ssh/authorized_keys
chmod 700 /home/<username>/.ssh
chmod 600 /home/<username>/.ssh/authorized_keys
chown -R <username>:<username> /home/<username>/.ssh
```

---

## ✅ Step 3: Test SSH Connection

### Test Basic SSH Access

```bash
ssh -i ~/.ssh/bella-voice-app <your-user>@15.157.56.64 "echo 'SSH key authentication successful!'"
```

**Expected output:**
```
SSH key authentication successful!
```

### Test Interactive SSH

```bash
ssh -i ~/.ssh/bella-voice-app <your-user>@15.157.56.64
```

You should be logged in **without a password prompt**.

---

## 🔌 Step 4: Set Up SSH Port Forwarding for Database Access

### Start SSH Tunnel

```bash
# Forward local port 15432 to production database port 5432
ssh -i ~/.ssh/bella-voice-app -L 15432:localhost:5432 <your-user>@15.157.56.64 -N -f
```

**What this does:**
- Creates a tunnel from your local port 15432 to production database port 5432
- `-N` = Don't execute remote commands
- `-f` = Run in background

### Verify Tunnel is Active

```bash
# Check if port forwarding is running
ps aux | grep "ssh.*15432"

# Test database connection through tunnel
nc -zv localhost 15432
```

### Set Database URL

```bash
export PRODUCTION_DB_URL="postgresql+asyncpg://bella_user:BellaPassword123@localhost:15432/bella_db"
```

---

## 🎯 Step 5: Run Production Verification

### Verify Calendar Sync

```bash
# Run the Python verification script
python scripts/verify_production_calendar.py

# Or check last 30 minutes
python scripts/verify_production_calendar.py --minutes 30
```

**Expected output:**
```
Production Calendar Sync Verification
======================================
Database: Production (via SSH tunnel)
Looking back: 15 minutes

✅ Connected to production database
✅ Found 1 recent appointment(s)

Appointment #1
==============
ID:           X
User:         Test User 209
Phone:        +14165558209
✅ Calendar Event ID: abc123xyz
✅ Calendar event verified!
```

### Check Appointments via Bash Script

```bash
# Check last 15 minutes
./scripts/check_production_appointments.sh 15

# Check last hour
./scripts/check_production_appointments.sh 60
```

---

## 🔐 Optional: Configure SSH Config for Easy Access

### Add to ~/.ssh/config

```bash
cat >> ~/.ssh/config <<EOF

# Bella Voice Production Server
Host bella-production
    HostName 15.157.56.64
    User <your-user>
    IdentityFile ~/.ssh/bella-voice-app
    ForwardAgent yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
```

### Now You Can Use Simple Commands

```bash
# SSH into production
ssh bella-production

# Port forwarding
ssh -L 15432:localhost:5432 bella-production -N -f

# Run remote commands
ssh bella-production "docker logs bella_app --tail 50"
```

---

## 🛠️ Automated Setup Script

**Run the automated setup script:**

```bash
./scripts/setup_production_ssh.sh
```

This script will:
1. ✅ Check for existing SSH keys
2. ✅ Display your public key
3. ✅ Provide step-by-step instructions
4. ✅ Optionally configure SSH config file

---

## 🔍 Troubleshooting

### Issue: "Permission denied (publickey)"

**Cause**: Public key not added to production server or wrong username

**Solution:**
1. Verify public key is in `~/.ssh/authorized_keys` on production server
2. Check permissions: `chmod 600 ~/.ssh/authorized_keys`
3. Verify you're using correct username

### Issue: "Connection timeout"

**Cause**: Firewall or network issue

**Solution:**
1. Check if port 22 is open: `nc -zv 15.157.56.64 22`
2. Verify production server is running
3. Check firewall rules on server

### Issue: "Could not resolve hostname"

**Cause**: Network connectivity issue

**Solution:**
1. Test connectivity: `ping 15.157.56.64`
2. Check DNS/network configuration

### Issue: Port forwarding not working

**Cause**: Port already in use or SSH connection failed

**Solution:**
```bash
# Kill existing port forwarding
pkill -f "ssh.*15432"

# Try again with verbose output
ssh -v -L 15432:localhost:5432 <your-user>@15.157.56.64 -N
```

---

## 📊 Verification Checklist

- [ ] SSH key pair exists (`~/.ssh/bella-voice-app`)
- [ ] Public key copied to production server
- [ ] SSH connection works without password
- [ ] Port forwarding established successfully
- [ ] Database accessible via tunnel (localhost:15432)
- [ ] Verification scripts run successfully
- [ ] Can query production appointments
- [ ] Can verify Google Calendar sync

---

## 🎯 Next Steps After Setup

1. **Run verification script:**
   ```bash
   python scripts/verify_production_calendar.py
   ```

2. **Check test appointment:**
   - Look for "Test User 209"
   - Verify `google_event_id` is populated

3. **Monitor production logs:**
   ```bash
   ssh bella-production "docker logs -f bella_app"
   ```

4. **Clean up test data:**
   ```bash
   # Via SSH tunnel
   python tests/production/cleanup.py cleanup --older-than=24 --db-url="$PRODUCTION_DB_URL"
   ```

---

## 📚 Related Documentation

- **Production Verification**: `PRODUCTION_VERIFICATION_GUIDE.md`
- **Log Monitoring**: `docs/PRODUCTION_LOG_MONITORING.md`
- **Database Testing**: `tests/production/DATABASE_TESTING.md`
- **Cleanup Utilities**: `tests/production/cleanup.py`

---

**Last Updated**: 2025-10-10 01:35 UTC

**Quick Reference Commands:**
```bash
# SSH access
ssh -i ~/.ssh/bella-voice-app <user>@15.157.56.64

# Port forwarding
ssh -i ~/.ssh/bella-voice-app -L 15432:localhost:5432 <user>@15.157.56.64 -N -f

# Verify appointments
export PRODUCTION_DB_URL="postgresql+asyncpg://bella_user:BellaPassword123@localhost:15432/bella_db"
python scripts/verify_production_calendar.py
```
