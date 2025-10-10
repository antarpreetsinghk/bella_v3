# Production Database Testing

Comprehensive production database testing that validates appointment persistence, data accuracy, and safe test data management.

## Overview

This suite includes **production database testing** that validates:

- **Database persistence**: Appointments are correctly saved to production/staging database
- **Data accuracy**: Extracted information matches expected format and content
- **Duplicate prevention**: System correctly handles duplicate appointment attempts
- **User management**: User profiles are created and reused appropriately
- **Google Calendar integration**: Events sync correctly when enabled
- **Data isolation**: Test data is properly marked and separated from real customer data
- **Automatic cleanup**: Test data is automatically cleaned up after tests

### 🛡️ Safety Features

Production database testing includes multiple safety layers:

1. **Test Data Marking**: All test appointments have `is_test_data=True` flag
2. **Automatic Cleanup**: Test data is automatically removed after each test
3. **Isolation**: Test data is never mixed with real customer data
4. **Dry-run Mode**: Cleanup utilities support dry-run for safety verification
5. **Age-based Retention**: Stale test data (>24 hours) is flagged for cleanup
6. **Database Verification**: Pre-flight checks ensure correct database configuration

## Configuration

### Database Environment Variables

```bash
# Required: Production/staging database URL
# ⚠️ IMPORTANT: Use TEST/STAGING database only, NEVER production customer database
PRODUCTION_DB_URL=postgresql+asyncpg://user:password@host:5432/test_database

# Recommended: Enable test mode for extra safety checks
PRODUCTION_DB_TEST_MODE=true

# Recommended: Enable automatic cleanup after tests
TEST_DATA_AUTO_CLEANUP=true

# Optional: Test data retention period in hours (default: 24)
TEST_DATA_RETENTION_HOURS=24
```

### Database Setup

1. **Apply database migrations:**
   ```bash
   alembic upgrade head
   # Ensure migration bf439ec8d57f (is_test_data) is applied
   ```

2. **Verify test data column exists:**
   ```bash
   psql "$PRODUCTION_DB_URL" -c "\d appointments"
   # Should show: is_test_data | boolean | not null | default false
   ```

3. **Test cleanup utilities:**
   ```bash
   python tests/production/cleanup.py count --db-url="$PRODUCTION_DB_URL"
   # Should execute without errors
   ```

## Database Test Suites

### TestProductionCallFlowWithDatabase

End-to-end tests that validate complete call flows with database persistence.

**Tests:**
- `test_complete_booking_saves_to_database`: Full booking flow creates correct database records
- `test_duplicate_prevention_in_production`: Duplicate appointments are prevented
- `test_user_creation_and_reuse`: User profiles are created once and reused
- `test_appointment_data_accuracy`: Data is stored accurately with correct timezone handling
- `test_google_calendar_integration`: Calendar events sync correctly (if enabled)
- `test_concurrent_bookings_isolation`: Concurrent calls don't interfere with each other

### TestProductionDataCleanup

Tests for cleanup utilities and test data management.

**Tests:**
- `test_cleanup_identifies_test_data`: Cleanup utilities correctly identify test data
- `test_cleanup_respects_age_filter`: Age-based filtering works correctly
- `test_verify_cleanup_rules`: Verification and reporting functions work

## Running Database Tests

### Prerequisites

Before running database tests, **READ THE SAFETY CHECKLIST**:
```bash
cat tests/production/SAFETY_CHECKLIST.md
```

### Run all database tests

```bash
# Configure database URL
export PRODUCTION_DB_URL="postgresql+asyncpg://user:password@test-db:5432/test_database"
export PRODUCTION_DB_TEST_MODE=true
export TEST_DATA_AUTO_CLEANUP=true

# Run database tests
pytest tests/production/test_production_database_flow.py -v
```

### Run with safe test runner script

```bash
# Dry-run mode (safety checks only)
./scripts/run_production_tests.sh --dry-run

# Full run with all safety checks
./scripts/run_production_tests.sh

# Verbose output
./scripts/run_production_tests.sh --verbose
```

### Run specific database tests

```bash
# Complete booking flow test
pytest tests/production/test_production_database_flow.py::TestProductionCallFlowWithDatabase::test_complete_booking_saves_to_database -v

# Duplicate prevention test
pytest tests/production/test_production_database_flow.py::TestProductionCallFlowWithDatabase::test_duplicate_prevention_in_production -v

# Cleanup tests only
pytest tests/production/test_production_database_flow.py::TestProductionDataCleanup -v
```

## Cleanup Utilities

### Manual Cleanup Operations

The `cleanup.py` utility provides safe test data management:

```bash
# Count test appointments
python tests/production/cleanup.py count --db-url="$PRODUCTION_DB_URL"

# List test appointments (with age filter)
python tests/production/cleanup.py list --db-url="$PRODUCTION_DB_URL" --older-than=24

# Cleanup old test data (DRY RUN by default)
python tests/production/cleanup.py cleanup --db-url="$PRODUCTION_DB_URL" --older-than=24

# Cleanup with actual deletion (CAUTION)
python tests/production/cleanup.py cleanup --db-url="$PRODUCTION_DB_URL" --older-than=24 --no-dry-run

# Verify cleanup rules and database state
python tests/production/cleanup.py verify --db-url="$PRODUCTION_DB_URL"

# Get human-readable summary
python tests/production/cleanup.py summary --db-url="$PRODUCTION_DB_URL"
```

### Cleanup Best Practices

1. **Always use dry-run first**: Verify what will be deleted before actual deletion
2. **Regular cleanup**: Run cleanup for data older than 24 hours
3. **Monitor accumulation**: Check test data count regularly
4. **Verify after tests**: Always verify cleanup after test runs

## Monitoring Tools

### Real-time Monitoring Dashboard

```bash
# Live dashboard (auto-refresh every 30 seconds)
python tests/production/monitor_test_data.py dashboard --db-url="$PRODUCTION_DB_URL"

# One-time snapshot
python tests/production/monitor_test_data.py snapshot --db-url="$PRODUCTION_DB_URL"

# Export to JSON for automation
python tests/production/monitor_test_data.py export --db-url="$PRODUCTION_DB_URL" --output=report.json

# Continuous monitoring with alerts
python tests/production/monitor_test_data.py watch --db-url="$PRODUCTION_DB_URL" --alert-threshold=100
```

### Monitoring Dashboard Features

- **Summary Statistics**: Total test appointments, active vs cancelled, stale data count
- **Age Distribution**: Visual breakdown of test data by age
- **Storage Metrics**: Estimated database storage used by test data
- **Trend Analysis**: Hourly creation trends over last 24 hours
- **Alerts**: Automated alerts for high test data counts or stale data
- **Recommendations**: Actionable cleanup recommendations

## Expected Results

### Database Test Success Criteria

- **Appointment Creation**: Appointments created with `is_test_data=True`
- **Data Accuracy**: All fields match expected values (timezone-aware timestamps, correct durations)
- **User Management**: Users created once per phone number, reused correctly
- **Duplicate Prevention**: System rejects duplicate appointments at same time
- **Cleanup Execution**: Test data cleaned up automatically after tests
- **No Orphaned Data**: No test data older than retention period

### Sample Database Test Output

```
tests/production/test_production_database_flow.py::TestProductionCallFlowWithDatabase::test_complete_booking_saves_to_database PASSED
tests/production/test_production_database_flow.py::TestProductionCallFlowWithDatabase::test_duplicate_prevention_in_production PASSED
tests/production/test_production_database_flow.py::TestProductionCallFlowWithDatabase::test_user_creation_and_reuse PASSED
tests/production/test_production_database_flow.py::TestProductionCallFlowWithDatabase::test_appointment_data_accuracy PASSED
tests/production/test_production_database_flow.py::TestProductionDataCleanup::test_cleanup_identifies_test_data PASSED

============================== 5 passed in 12.34s ==============================
```

## Safety Checklist

**BEFORE running any production database tests**, complete the safety checklist:

📋 **[SAFETY_CHECKLIST.md](./SAFETY_CHECKLIST.md)**

Key safety checks:
- [ ] Verify database URL points to TEST/STAGING database only
- [ ] Confirm `is_test_data` migration is applied
- [ ] Test cleanup utilities in dry-run mode
- [ ] Verify auto-cleanup is enabled
- [ ] Review emergency procedures

## Troubleshooting Database Tests

### Tests are skipped (no database)
**Problem**: Tests show `SKIPPED - PRODUCTION_DB_URL not configured`

**Solution**: Set the database URL:
```bash
export PRODUCTION_DB_URL="postgresql+asyncpg://user:password@host:5432/database"
```

### Migration not applied
**Problem**: Tests fail with column `is_test_data` does not exist

**Solution**: Apply the migration:
```bash
alembic upgrade head
```

### Cleanup fails
**Problem**: Cleanup utilities fail or don't delete test data

**Solution**: Check test data flag:
```sql
SELECT COUNT(*), is_test_data FROM appointments GROUP BY is_test_data;
```

Verify appointments have `is_test_data=True` flag set.

### Database connection errors
**Problem**: Cannot connect to database

**Solution**: Verify connection string and database availability:
```bash
psql "$PRODUCTION_DB_URL" -c "SELECT 1;"
```

### Stale data accumulation
**Problem**: Test data keeps accumulating

**Solution**: Run manual cleanup:
```bash
python tests/production/cleanup.py cleanup --older-than=0 --no-dry-run --db-url="$PRODUCTION_DB_URL"
```

## CI/CD Integration for Database Tests

### GitHub Actions Example

```yaml
name: Production Database Tests

on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM
  workflow_dispatch:

jobs:
  database-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run database migrations
        env:
          PRODUCTION_DB_URL: ${{ secrets.STAGING_DB_URL }}
        run: alembic upgrade head

      - name: Run database tests
        env:
          PRODUCTION_DB_URL: ${{ secrets.STAGING_DB_URL }}
          PRODUCTION_DB_TEST_MODE: true
          TEST_DATA_AUTO_CLEANUP: true
          PRODUCTION_TEST_URL: ${{ secrets.STAGING_API_URL }}
        run: |
          pytest tests/production/test_production_database_flow.py -v --tb=short

      - name: Cleanup stale test data
        if: always()
        env:
          PRODUCTION_DB_URL: ${{ secrets.STAGING_DB_URL }}
        run: |
          python tests/production/cleanup.py cleanup --older-than=24 --no-dry-run
```

## Database Security Best Practices

1. **Database Isolation**
   - ✅ Use dedicated test/staging databases
   - ❌ NEVER test against production customer database
   - ✅ Verify database name contains "test" or "staging"

2. **Credential Management**
   - ✅ Use environment variables for database URLs
   - ❌ Never commit database credentials to version control
   - ✅ Use secret management (AWS Secrets Manager, etc.)

3. **Data Isolation**
   - ✅ All test appointments marked with `is_test_data=True`
   - ✅ Automatic cleanup enabled by default
   - ✅ Regular verification of test data isolation

4. **Access Control**
   - ✅ Test database user has limited permissions
   - ✅ Read/write access only to test tables
   - ❌ No access to production customer data

5. **Monitoring**
   - ✅ Monitor test data accumulation
   - ✅ Alert on cleanup failures
   - ✅ Track database performance impact

## Additional Resources

- **Safety Checklist**: `SAFETY_CHECKLIST.md` - Complete safety procedures
- **Cleanup Utilities**: `cleanup.py` - Test data management CLI
- **Monitoring Dashboard**: `monitor_test_data.py` - Real-time monitoring
- **Test Runner**: `../../scripts/run_production_tests.sh` - Safe test execution wrapper
- **Database Fixtures**: `conftest.py` - Pytest fixtures for database testing
- **Example Tests**: `test_production_database_flow.py` - Comprehensive test examples
- **Call Flow Tests**: `README.md` - Production call flow testing documentation

## Support

For issues or questions about database tests, see:
- Main project README: `/README.md`
- Claude Code guide: `/CLAUDE.md`
- Call flow testing: `tests/production/README.md`
- Safety Checklist: `tests/production/SAFETY_CHECKLIST.md`
