# Production Call Flow Tests

Comprehensive production testing suite for real-world call pattern simulation and validation.

## Overview

This test suite validates the VoiceFlow AI platform's behavior under production-like conditions, including:

- **Real-world call scenarios**: Simulates diverse customer interactions
- **Peak hour simulation**: Tests performance under high call volume
- **Daily pattern simulation**: Validates consistent behavior across business hours
- **Edge case scenarios**: Tests handling of unusual inputs and error conditions
- **Call flow validation**: Ensures proper state progression and data extraction

## Configuration

### Environment Variables

The production tests require the following environment variables to run:

```bash
# Required: Production or staging endpoint URL
PRODUCTION_TEST_URL=https://your-deployment-url.com
# OR
FUNCTION_URL=https://your-lambda-url.aws.com

# Optional: API key for authenticated endpoints
PRODUCTION_API_KEY=your-api-key-here

# Optional: Request timeout in seconds (default: 30)
PRODUCTION_TEST_TIMEOUT=30
```

### Setup

1. **For local testing against a deployed instance:**
   ```bash
   export PRODUCTION_TEST_URL="https://your-deployment-url.com"
   export PRODUCTION_API_KEY="your-api-key"
   pytest tests/production/ -v
   ```

2. **For CI/CD pipeline testing:**
   Add the environment variables to your CI/CD secrets:
   ```yaml
   # Example GitHub Actions workflow
   - name: Run Production Tests
     env:
       PRODUCTION_TEST_URL: ${{ secrets.PRODUCTION_TEST_URL }}
       PRODUCTION_API_KEY: ${{ secrets.PRODUCTION_API_KEY }}
     run: pytest tests/production/ -v -m production
   ```

3. **Skip production tests (default behavior):**
   ```bash
   # Tests will be skipped if URL is not configured
   pytest tests/production/ -v
   # Output: SKIPPED - PRODUCTION_TEST_URL or FUNCTION_URL environment variable not set
   ```

## Test Suites

### TestRealWorldCallScenarios

Simulates complete customer journeys from call initiation to booking completion.

**Scenarios:**
- `quick_booking`: Fast booking with all information provided upfront
- `detailed_booking`: Step-by-step information collection
- `unclear_speech`: Handles speech recognition challenges
- `international_caller`: Tests international phone number handling
- `reschedule_request`: Appointment modification workflows
- `elderly_caller`: Tests patient, clear communication

**Tests:**
- `test_individual_scenarios`: Runs each scenario sequentially
- `test_concurrent_scenarios`: Tests 3 scenarios simultaneously
- `test_peak_hour_simulation`: 10 calls in compressed time
- `test_daily_pattern_simulation`: 15 calls representing business hours
- `test_edge_case_scenarios`: Empty speech, long input, special characters

### TestCallFlowValidation

Validates call flow logic and state management.

**Tests:**
- `test_appointment_extraction_accuracy`: Verifies name and phone extraction
- `test_call_state_progression`: Validates proper state transitions

## Running Tests

### Run all production tests
```bash
# With configured environment
export PRODUCTION_TEST_URL="https://your-url.com"
pytest tests/production/ -v
```

### Run specific test suites
```bash
# Real-world scenarios only
pytest tests/production/test_call_scenarios.py::TestRealWorldCallScenarios -v

# Validation tests only
pytest tests/production/test_call_scenarios.py::TestCallFlowValidation -v
```

### Run specific scenarios
```bash
# Peak hour simulation
pytest tests/production/test_call_scenarios.py::TestRealWorldCallScenarios::test_peak_hour_simulation -v

# Edge case testing
pytest tests/production/test_call_scenarios.py::TestRealWorldCallScenarios::test_edge_case_scenarios -v
```

### Run with markers
```bash
# Essential tests only
pytest tests/production/ -v -m essential

# All production tests
pytest tests/production/ -v -m production
```

## Expected Results

### Success Criteria

- **Individual scenarios**: All steps complete successfully, < 15s total duration
- **Concurrent scenarios**: At least 2/3 scenarios succeed under load
- **Peak hour simulation**: ≥90% success rate, <3s average response time
- **Daily pattern**: ≥95% success rate, <2s average response time
- **Edge cases**: All cases handled gracefully with valid TwiML responses

### Sample Output

```
🧪 Testing scenario: quick_booking
✅ quick_booking: 5/5 steps in 3.24s

📈 Simulating peak hour call pattern
✅ Peak hour simulation: 100% success, 1.45s avg response

📅 Simulating daily call pattern (compressed)
✅ Daily pattern: 100% success over 15 calls
   Average response time: 1.32s

🔬 Testing edge case scenarios
✅ Edge case empty_speech: handled gracefully
✅ Edge case very_long_speech: handled gracefully
✅ Edge case special_characters: handled gracefully
✅ Edge case numbers_only: handled gracefully
```

## Troubleshooting

### Tests are skipped
**Problem**: Tests show `SKIPPED - PRODUCTION_TEST_URL or FUNCTION_URL environment variable not set`

**Solution**: Set the required environment variable:
```bash
export PRODUCTION_TEST_URL="https://your-deployment-url.com"
```

### Authentication failures
**Problem**: Tests fail with 401/403 errors

**Solution**: Set the API key if your endpoint requires authentication:
```bash
export PRODUCTION_API_KEY="your-api-key"
```

### Timeout errors
**Problem**: Tests fail with timeout errors

**Solution**: Increase the timeout value:
```bash
export PRODUCTION_TEST_TIMEOUT="60"
```

### Connection refused
**Problem**: Tests fail with connection errors

**Solution**: Verify the endpoint URL is correct and accessible:
```bash
curl -v $PRODUCTION_TEST_URL/healthz
```

## Best Practices

1. **Pre-deployment validation**: Run production tests against staging before deploying
2. **Scheduled testing**: Set up cron jobs or CI/CD schedules for regular production testing
3. **Performance monitoring**: Track response times and success rates over time
4. **Alert on failures**: Configure alerts for production test failures
5. **Test data cleanup**: Ensure test appointments are properly cleaned up or marked as test data

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Production Tests

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  production-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run Production Tests
        env:
          PRODUCTION_TEST_URL: ${{ secrets.PRODUCTION_TEST_URL }}
          PRODUCTION_API_KEY: ${{ secrets.PRODUCTION_API_KEY }}
        run: |
          pytest tests/production/ -v -m production --tb=short
```

## Security Notes

- **Never commit** production URLs or API keys to version control
- Use environment variables or secure secret management
- Ensure test data is isolated from real customer data
- Consider using dedicated test accounts for production testing
- Monitor test call costs if using paid telephony services

## Support

For issues or questions about production tests, see:
- Main project README: `/README.md`
- Claude Code guide: `/CLAUDE.md`
- Contributing guidelines: `/CONTRIBUTING.md`
