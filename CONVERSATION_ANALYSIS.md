# Real Conversation Analysis - Session Flow Issues

## Data Source
Extracted from AWS CloudWatch logs: `/ecs/bella-prod` (last 2 hours)
Date: 2025-09-27 17:00-19:40 UTC

## Real Conversations Identified

### Conversation 1: CA5437f8c001314394837d1664c606086b (REAL USER)
```
Step 1: ask_name  → "My name is Johnny Walker."
Step 2: ask_mobile → "It's 8153288957."
Step 3: ask_time  → "Next week. Thursday at 9:30 a.m."
Step 4: ask_name  → "next Thursday, at 11 a.m." ❌ RESET TO ask_name
Step 5: ask_time  → "<empty>"
```
**Issue**: Session reset from ask_time back to ask_name

### Conversation 2: CAc6daa33212d9c48105b00a4ab48dbde4 (REAL USER)
```
Step 1: ask_name   → "My full name is Rocky, Jonathan."
Step 2: ask_mobile → "8536945968."
Step 3: ask_mobile → "685 963 6251." (phone retry)
Step 4: ask_mobile → "693. 543 8631." (phone retry)
Step 5: ask_mobile → "Six nine, three five eight. Six five nine three, two." (phone retry)
Step 6: ask_name   → "The 204-869-4905." ❌ RESET TO ask_name
Step 7: ask_mobile → "To 204 869 4905."
Step 8: ask_time   → "Here. Next week, Thursday at 11 a.m."
Step 9: ask_mobile → "Yes." ❌ RESET TO ask_mobile
Step 10: ask_mobile → "<empty>"
```
**Issues**: Multiple session resets, phone extraction failing

### Test Conversations (My debugging)
All show consistent pattern: session state not persisting between requests

## Pattern Analysis

### Expected Flow:
```
ask_name → ask_mobile → ask_time → confirm → complete
```

### Actual Flow (All conversations):
```
ask_name → ask_mobile → [RANDOM RESETS] → ask_name/ask_mobile (infinite loop)
```

## Key Findings:
1. **Session state never persists** between HTTP requests
2. **Random resets** occur at any step
3. **Phone extraction issues** cause stuck loops
4. **Real users experiencing frustration** - multiple retry attempts
5. **No conversation completes successfully**

## Root Causes to Investigate:
1. Redis connection failures
2. In-memory session storage not working
3. Session retrieval/save logic bugs
4. Container/ECS task restarts wiping memory
5. Phone number extraction logic failures