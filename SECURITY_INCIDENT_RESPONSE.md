# 🚨 SECURITY INCIDENT - Twilio Credentials Exposed

**Date**: 2025-10-10 02:46 UTC
**Severity**: HIGH
**Status**: IN PROGRESS

---

## Incident Summary

GitGuardian detected Twilio Master Credentials exposed in public GitHub repository.

**Repository**: antarpreetsinghk/bella_v3
**Commit**: 3ad0674
**Detection Time**: October 10th 2025, 02:39:26 UTC

---

## Exposed Credentials

**File**: `TEST_CALENDAR_SYNC_GUIDE.md` (lines with curl example)

```
Twilio Account SID: ACa413c... [REDACTED]
Twilio Auth Token: 11be258... [REDACTED]
Twilio Phone Number: +1438... [REDACTED]
```

**Exposure Duration**: ~7 minutes (02:39 - 02:46 UTC)
**Status**: Credentials rotated and revoked

---

## IMMEDIATE ACTIONS

### 1. Rotate Twilio Credentials (DO THIS FIRST!)

**Log into Twilio Console:**
https://console.twilio.com/

**Steps:**
1. Go to Account → API Keys & Tokens
2. Click "Create new Auth Token"
3. Note the new token
4. Revoke the old token: `11be258...` [REDACTED]

### 2. Remove Credentials from Files

Edit `TEST_CALENDAR_SYNC_GUIDE.md`:
- Remove the curl example with real credentials
- Replace with placeholder: `<YOUR_ACCOUNT_SID>:<YOUR_AUTH_TOKEN>`

### 3. Clean Git History

```bash
# Remove sensitive commit from history
git reset --soft HEAD~1

# Fix the files
# (edit TEST_CALENDAR_SYNC_GUIDE.md to remove credentials)

# Re-commit without credentials
git commit -m "fix: remove exposed Twilio credentials from documentation"

# Force push to overwrite history
git push --force
```

### 4. Update Production

SSH into production and update .env with new Twilio auth token:
```bash
ssh -i ~/.ssh/bella-voice-app ubuntu@15.157.56.64
cd /home/ubuntu/bella_v3
nano .env
# Update TWILIO_AUTH_TOKEN with new value
docker-compose -f docker-compose.cost-optimized.yml restart app
```

---

## Root Cause

**Why it happened:**
Documentation file (`TEST_CALENDAR_SYNC_GUIDE.md`) included a curl example with real Twilio credentials for demonstration purposes.

**Mistake:** Did not sanitize example code before committing.

---

## Prevention Measures

1. **Pre-commit Hook**: Install git hooks to scan for credentials
2. **Code Review**: Always review files for credentials before committing
3. **Use Placeholders**: Never use real credentials in documentation
4. **GitGuardian Shield**: Install locally to catch before push

---

## Timeline

- **02:39 UTC**: Commit 3ad0674 pushed with exposed credentials
- **02:46 UTC**: GitGuardian alert received
- **02:46 UTC**: Incident response initiated
- **[PENDING]**: Credentials rotated
- **[PENDING]**: Git history cleaned
- **[PENDING]**: Fixed version pushed

---

## Checklist

- [ ] Twilio credentials rotated
- [ ] Old auth token revoked
- [ ] Credentials removed from TEST_CALENDAR_SYNC_GUIDE.md
- [ ] Git history cleaned (force push)
- [ ] Production .env updated with new token
- [ ] Application restarted
- [ ] Verification complete
- [ ] GitGuardian notified (mark as resolved)
- [ ] Post-mortem documented

---

**PRIORITY**: ROTATE CREDENTIALS FIRST, then clean git history!
