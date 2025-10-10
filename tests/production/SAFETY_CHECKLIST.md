# 🛡️ Production Database Testing - Safety Checklist

## ⚠️ CRITICAL: Read Before Running Production Tests

This checklist ensures safe execution of production database tests without affecting real customer data.

---

## 📋 Pre-Flight Safety Checks

### ✅ 1. Database Configuration Verification

**BEFORE running any production database tests, verify:**

- [ ] **Database URL is CORRECT**
  ```bash
  echo $PRODUCTION_DB_URL
  # Should point to TEST/STAGING database, NOT production customer database
  ```

- [ ] **Database is TEST/STAGING only**
  - Verify with your database administrator
  - Check database name (should contain "test", "staging", or "dev")
  - Confirm NO real customer data exists in this database

- [ ] **Test mode is ENABLED**
  ```bash
  echo $PRODUCTION_DB_TEST_MODE
  # Should be: true
  ```

- [ ] **Auto-cleanup is ENABLED**
  ```bash
  echo $TEST_DATA_AUTO_CLEANUP
  # Should be: true
  ```

### ✅ 2. Migration Status

- [ ] **Database schema is up-to-date**
  ```bash
  alembic current
  # Should show: bf439ec8d57f or later (is_test_data migration)
  ```

- [ ] **is_test_data column exists**
  ```bash
  # Connect to database and verify:
  \d appointments
  # Should show: is_test_data | boolean | not null | default false
  ```

- [ ] **Index exists for fast cleanup**
  ```sql
  SELECT indexname FROM pg_indexes
  WHERE tablename = 'appointments' AND indexname = 'ix_appointments_is_test_data';
  -- Should return: ix_appointments_is_test_data
  ```

### ✅ 3. Cleanup Utilities Verification

- [ ] **Cleanup script is accessible**
  ```bash
  python tests/production/cleanup.py count --db-url="$PRODUCTION_DB_URL"
  # Should execute without errors
  ```

- [ ] **Dry-run mode works**
  ```bash
  python tests/production/cleanup.py cleanup --db-url="$PRODUCTION_DB_URL" --older-than=0
  # Should show: [DRY RUN] with found count
  ```

- [ ] **Manual cleanup is tested**
  ```bash
  # Create a test appointment, then cleanup in dry-run mode
  python tests/production/cleanup.py verify --db-url="$PRODUCTION_DB_URL"
  ```

### ✅ 4. External Service Configuration

- [ ] **Google Calendar is configured correctly**
  - If testing calendar integration, verify service account
  - Check calendar ID is test calendar, not production
  - Test calendar permissions are read/write

- [ ] **Twilio webhook URL points to test environment**
  ```bash
  echo $PRODUCTION_TEST_URL
  # Should be staging/test environment, NOT live production
  ```

- [ ] **API keys are for test environment**
  ```bash
  echo $PRODUCTION_API_KEY
  # Verify with team this is test/staging key
  ```

### ✅ 5. Test Data Isolation Verification

**Run this verification before first test:**

```bash
# Check that test data flag works
pytest tests/production/test_production_database_flow.py::TestProductionDataCleanup::test_cleanup_identifies_test_data -v
```

Expected output:
- ✅ Test passes
- ✅ No errors about is_test_data column
- ✅ Cleanup utilities can query test data

---

## 🚨 During Test Execution

### Monitor These Indicators

1. **Test Data Markers**
   - Every test should create appointments with `is_test_data=True`
   - Check test output for "is_test_data" confirmations

2. **Database Connection**
   - Watch for connection errors
   - Monitor connection pool usage
   - Check for deadlocks or timeouts

3. **Cleanup Execution**
   - Verify cleanup messages after each test
   - Check that `test_appointment_ids` are tracked
   - Confirm deletions are executed

4. **Error Handling**
   - Any database errors should be investigated immediately
   - Stop tests if you see warnings about customer data

### ⚠️ WARNING SIGNS - STOP IMMEDIATELY IF:

- ❌ Tests fail to create `is_test_data=True` appointments
- ❌ Cleanup is skipped or fails
- ❌ Database shows production customer data
- ❌ Connection errors or permission denied
- ❌ Unexpected appointment counts or data corruption
- ❌ Google Calendar events created in production calendar

**If any warning sign appears: STOP TESTS and run cleanup verification**

---

## 🔍 Post-Test Verification

### After test suite completes:

1. **Verify Cleanup Executed**
   ```bash
   python tests/production/cleanup.py verify --db-url="$PRODUCTION_DB_URL"
   ```

   Expected output:
   - Total test appointments: should be 0 or very low
   - Stale test data: should be 0
   - Cleanup recommended: NO

2. **Check for Orphaned Test Data**
   ```bash
   python tests/production/cleanup.py summary --db-url="$PRODUCTION_DB_URL"
   ```

   Look for:
   - Age distribution (should be mostly recent)
   - No appointments older than 24 hours (unless intended)

3. **Manual Database Query**
   ```sql
   SELECT COUNT(*), MAX(created_at), MIN(created_at)
   FROM appointments
   WHERE is_test_data = true;
   ```

   - Count should be low (< 10 unless actively testing)
   - Timestamps should be very recent

4. **Google Calendar Cleanup** (if integration enabled)
   - Check test calendar for orphaned events
   - Delete any events with "TEST" or test names

---

## 🆘 Emergency Procedures

### If Real Customer Data is Affected

1. **STOP ALL TESTS IMMEDIATELY**
   ```bash
   # Kill all running pytest processes
   pkill -f "pytest.*production"
   ```

2. **Assess Damage**
   ```sql
   -- Check if any real appointments were modified
   SELECT * FROM appointments
   WHERE is_test_data = false
   AND updated_at > NOW() - INTERVAL '1 hour'
   ORDER BY updated_at DESC;
   ```

3. **Rollback if Possible**
   - If within transaction: rollback
   - If committed: restore from backup
   - Contact database administrator immediately

4. **Document Incident**
   - What tests were running
   - Time of incident
   - Database state before/after
   - Steps taken to recover

### If Cleanup Fails

1. **Manual Cleanup Procedure**
   ```bash
   # Force cleanup (NO DRY RUN - use with caution)
   python tests/production/cleanup.py cleanup \
     --db-url="$PRODUCTION_DB_URL" \
     --older-than=0 \
     --no-dry-run \
     --limit=1000
   ```

2. **Verify Deletion**
   ```bash
   python tests/production/cleanup.py count --db-url="$PRODUCTION_DB_URL"
   ```

3. **If Still Failing**
   ```sql
   -- LAST RESORT: Manual SQL cleanup
   -- VERIFY this query carefully before running
   DELETE FROM appointments
   WHERE is_test_data = true
   AND created_at < NOW() - INTERVAL '24 hours'
   RETURNING id, user_id, created_at;
   ```

### If Database Connection Lost

1. **Check connection status**
   ```bash
   psql "$PRODUCTION_DB_URL" -c "SELECT 1;"
   ```

2. **Verify database is running**
   - Check with hosting provider
   - Check database server status
   - Verify network connectivity

3. **Do NOT retry tests** until connection is stable

---

## 📞 Emergency Contacts

### Escalation Path

1. **Level 1: Test Failures**
   - Review test output and logs
   - Check this safety checklist
   - Run cleanup verification

2. **Level 2: Data Integrity Issues**
   - Contact: Database Administrator
   - Provide: Test logs, database state, timeline

3. **Level 3: Customer Data Affected**
   - Contact: Engineering Lead + Database Administrator
   - Initiate: Incident response procedure
   - Document: Full timeline and impact assessment

### Contact Information

```bash
# Update these with your team's actual contacts
DATABASE_ADMIN="dba@your-company.com"
ENGINEERING_LEAD="engineering-lead@your-company.com"
ON_CALL_ROTATION="oncall@your-company.com"
```

---

## 📊 Pre-Deployment Checklist

Before deploying production database testing to CI/CD:

- [ ] All safety checks pass on local environment
- [ ] Cleanup utilities tested thoroughly
- [ ] Test data isolation verified
- [ ] Rollback procedures documented
- [ ] Team trained on safety procedures
- [ ] Emergency contacts updated
- [ ] Database backups configured
- [ ] Monitoring alerts set up
- [ ] Dry-run mode tested in CI/CD
- [ ] Test database separate from production

---

## 🎯 Best Practices

### DO ✅

- ✅ Always use `is_test_data=True` for test appointments
- ✅ Enable auto-cleanup (`TEST_DATA_AUTO_CLEANUP=true`)
- ✅ Run cleanup verification after tests
- ✅ Test cleanup utilities regularly
- ✅ Use staging/test databases only
- ✅ Monitor test execution closely
- ✅ Document any issues or anomalies
- ✅ Keep retention period short (24 hours max)

### DON'T ❌

- ❌ Run against production customer database
- ❌ Disable auto-cleanup without good reason
- ❌ Create appointments without `is_test_data=True`
- ❌ Ignore cleanup failures
- ❌ Run tests without verification
- ❌ Skip safety checks "just this once"
- ❌ Leave orphaned test data
- ❌ Use production Google Calendar for tests

---

## 🔄 Regular Maintenance

### Daily (If Running Tests)

- [ ] Verify test data count is low
- [ ] Check for stale data (> 24 hours)
- [ ] Review any cleanup failures

### Weekly

- [ ] Run comprehensive cleanup
  ```bash
  python tests/production/cleanup.py cleanup --older-than=168 --no-dry-run
  ```
- [ ] Verify database performance (test data shouldn't impact)
- [ ] Review test failure patterns

### Monthly

- [ ] Audit test data isolation (no real data affected)
- [ ] Review and update safety procedures
- [ ] Test emergency rollback procedures
- [ ] Update contact information
- [ ] Review retention policies

---

## 📚 Additional Resources

- **Production Testing Guide**: `tests/production/README.md`
- **Cleanup Utilities**: `tests/production/cleanup.py`
- **Database Fixtures**: `tests/production/conftest.py`
- **Example Tests**: `tests/production/test_production_database_flow.py`
- **Migration**: `alembic/versions/bf439ec8d57f_*.py`

---

## ✅ Sign-Off

**Before running production database tests, confirm:**

- [ ] I have read this entire safety checklist
- [ ] I have verified the database is TEST/STAGING only
- [ ] I have tested cleanup utilities
- [ ] I have emergency procedures available
- [ ] I have contact information for escalation
- [ ] I understand the risks and safeguards

**Tester Name:** _______________
**Date:** _______________
**Database Verified:** _______________
**Approved By:** _______________

---

<div align="center">

**🛡️ Safety First - Test Responsibly 🛡️**

*If in doubt, don't run the test. Ask for help.*

</div>
