# Real Calls Testing for Bella V3

This document explains how to use the comprehensive real calls testing system for the Bella V3 voice appointment booking system.

## 📋 Overview

The `real_calls_testing.py` script simulates real voice call scenarios to test the complete voice-to-database flow:

```
Voice Input → Speech Processing → Canadian Extraction → Database Storage
```

## 🚀 Quick Start

### Local Testing
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests locally
python real_calls_testing.py --run-all-tests

# Run specific test
python real_calls_testing.py --test-case simple_booking

# Interactive mode
python real_calls_testing.py
```

### Production Testing
```bash
# Test production deployment
python real_calls_testing.py --environment production --base-url https://your-domain.com --run-all-tests

# Save results to file
python real_calls_testing.py --environment production --base-url https://your-domain.com --run-all-tests --save-results
```

## 🧪 Test Cases

### Easy Tests (Perfect Conditions)
- **simple_booking**: Clear speech, perfect information
- **spelled_out_phone**: Phone number spelled digit by digit

### Medium Tests (Real-World Scenarios)
- **canadian_accent_test**: Canadian pronunciation and phrases
- **noisy_background**: Background noise and speech artifacts
- **multilingual_name**: French-Canadian names
- **power_caller**: All info provided at once

### Hard Tests (Challenging Scenarios)
- **complex_scheduling**: Complex time expressions and rescheduling
- **correction_scenario**: Caller corrects information
- **speech_recognition_errors**: Common speech-to-text errors

## 📊 Test Results

Each test produces:
- ✅/❌ Success status
- ⏱️ Execution time
- 📝 Detailed responses
- 🔍 Extracted data
- ⚠️ Error details

Example output:
```
🧪 Running test: simple_booking
Description: Perfect speech, clear information
  Step 1: 'Hi, my name is John Smith'
  Step 2: 'My phone number is 416-555-1234'
  Step 3: 'I'd like to book for next Tuesday at 2 PM'
  ✅ PASSED in 2.34s
```

## 🎯 Usage Examples

### 1. Development Testing
```bash
# Test while developing locally
python real_calls_testing.py --test-case canadian_accent_test
```

### 2. Pre-Deployment Validation
```bash
# Test all scenarios before production deploy
python real_calls_testing.py --run-all-tests --save-results
```

### 3. Production Monitoring
```bash
# Regular production health checks
python real_calls_testing.py --environment production --base-url https://bella-alb-1924818779.ca-central-1.elb.amazonaws.com --test-case simple_booking
```

### 4. Debugging Specific Issues
```bash
# Test problematic scenarios
python real_calls_testing.py --test-case speech_recognition_errors
```

## 📁 Test Results Files

Results are automatically saved as JSON files:
- `real_calls_test_results_YYYYMMDD_HHMMSS.json`

Contains:
- Environment and timestamp
- Summary statistics
- Detailed results for each test
- Error logs and extracted data

## 🔧 Configuration

### Environment Variables
The script uses your existing `.env` configuration:
- `POSTGRES_*` for database
- `OPENAI_API_KEY` for LLM fallback
- `TWILIO_AUTH_TOKEN` for webhook validation

### Custom Test Cases
Add new test cases by modifying the `get_test_cases()` method:

```python
CallTestCase(
    name="my_custom_test",
    description="Description of test scenario",
    call_sid="TEST_CUSTOM_001",
    from_number="+12345678901",
    speech_inputs=[
        "First thing caller says",
        "Second response",
        "Final input"
    ],
    expected_outcomes={
        "name": "Expected Name",
        "phone": "+1234567890",
        "appointment_booked": True
    },
    difficulty="medium"
)
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Make sure server is running
   uvicorn app.main:app --reload
   ```

2. **Database Errors**
   ```bash
   # Check database is running
   docker-compose up db -d
   ```

3. **Import Errors**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   ```

### Debug Mode
Add logging for detailed debugging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Continuous Integration

### GitHub Actions Integration
```yaml
- name: Run Real Calls Tests
  run: |
    source venv/bin/activate
    python real_calls_testing.py --run-all-tests --save-results
```

### Production Health Checks
```bash
# Daily production testing (cron job)
0 9 * * * cd /path/to/bella_v3 && python real_calls_testing.py --environment production --base-url https://your-domain.com --test-case simple_booking
```

## 🎯 Best Practices

1. **Run tests after each deployment**
2. **Test locally before production**
3. **Save results for comparison**
4. **Monitor success rates over time**
5. **Add new test cases for edge cases found in production**

## 📞 Real Call Flow Validation

The script validates the complete flow:

1. **Twilio Webhook** → `/twilio/voice`
2. **Speech Input** → `/twilio/voice/collect`
3. **Canadian Extraction** → Name, phone, time parsing
4. **Database Storage** → User and appointment creation
5. **Response Generation** → TwiML for caller

Each test case verifies this end-to-end functionality with realistic voice scenarios.