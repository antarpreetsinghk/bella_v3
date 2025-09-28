# 🎙️ Permanent Speech Monitor System

A permanent, continuous monitoring system for Bella V3 production speech-to-text processing.

## 🚀 Quick Start

```bash
# Start continuous monitoring (recommended for testing)
./start_speech_monitor.sh daemon

# Generate HTML dashboard
./start_speech_monitor.sh dashboard

# Generate text report
./start_speech_monitor.sh report
```

## 📋 Features

### 🔄 **Continuous Monitoring**
- Real-time capture of all production speech-to-text data
- Automatic logging to persistent storage
- Live console output with timestamps

### 📊 **Web Dashboard**
- Auto-refreshing HTML dashboard
- Visual statistics and metrics
- Recent speech inputs display
- Success rate tracking

### 📈 **Automated Reports**
- Comprehensive analysis reports
- 24-hour activity summaries
- Extraction performance metrics
- Historical data trends

### 🎯 **Live Speech Capture**
What gets captured from every production call:
- **Speech Input:** Raw Twilio speech recognition results
- **Processing Steps:** Name, phone, time extraction attempts
- **Success/Failure:** Each extraction result with timing
- **Call Flow:** Complete conversation progression

## 📁 File Structure

```
speech_monitor_data.jsonl         # Raw monitoring data (persistent)
speech_monitor_dashboard.html     # Generated HTML dashboard
speech_monitor_report_*.md        # Generated reports
permanent_speech_monitor.py       # Core monitoring system
start_speech_monitor.sh          # Easy startup script
```

## 🎤 Example Captured Data

### Speech Input:
```json
{
  "timestamp": "2025-09-28T15:39:28",
  "call_id": "CAcb9ec296d727838858bad8ede71c60e0",
  "step": "ask_name",
  "speech_text": "My name is Jennifer.",
  "type": "speech_input"
}
```

### Extraction Result:
```json
{
  "timestamp": "2025-09-28T15:39:30",
  "extraction_type": "name_canadian",
  "input": "My name is Jennifer.",
  "output": "Jennifer",
  "success": true,
  "type": "extraction_result"
}
```

## 🛠️ Usage Examples

### Start Monitoring Daemon
```bash
./start_speech_monitor.sh daemon
```
- Runs continuously in foreground
- Captures all speech data in real-time
- Press Ctrl+C to stop
- Perfect for active testing sessions

### Generate Dashboard
```bash
./start_speech_monitor.sh dashboard
```
- Creates `speech_monitor_dashboard.html`
- Auto-refreshes every 30 seconds
- Visual interface for monitoring
- Open in any web browser

### Generate Report
```bash
./start_speech_monitor.sh report
```
- Comprehensive analysis of last 24 hours
- Speech accuracy statistics
- Extraction performance metrics
- Saves to timestamped markdown file

## 📊 Dashboard Features

- **📞 Total Calls:** Count of monitored calls
- **⏱️ Avg Response Time:** Speech processing speed
- **🎯 Success Rate:** Extraction accuracy percentage
- **🟢 Status:** Live monitoring indicator
- **📝 Live Speech Log:** Real-time speech inputs

## 🔧 Advanced Usage

### Custom Log File
```bash
python permanent_speech_monitor.py --start-daemon --log-file custom_log.jsonl
```

### Background Daemon (Linux/Mac)
```bash
nohup ./start_speech_monitor.sh daemon > monitor.log 2>&1 &
```

### Scheduled Reports (Cron)
```bash
# Add to crontab for hourly reports
0 * * * * cd /path/to/bella_v3 && ./start_speech_monitor.sh report
```

## 🎯 Testing Workflow

1. **Start Monitor:** `./start_speech_monitor.sh daemon`
2. **Make Test Calls:** Call your production number
3. **Watch Live Data:** See speech captured in real-time
4. **Generate Reports:** `./start_speech_monitor.sh report`
5. **View Dashboard:** `./start_speech_monitor.sh dashboard`

## 📈 What You'll See

### During Active Monitoring:
```
🎤 [2025-09-28T15:39:28] SPEECH CAPTURED
   Call: CAcb9ec296d727838858bad8ede71c60e0
   Step: ask_name
   Text: "My name is Jennifer."

🧠 [2025-09-28T15:39:30] EXTRACTION ✅
   Type: name_canadian
   Input: "My name is Jennifer."
   Output: "Jennifer"
```

### Performance Metrics:
- Speech recognition accuracy
- Extraction success rates by type
- Processing time analysis
- Call completion statistics

## 🔒 Privacy & Security

- All sensitive data is masked in logs
- Only speech-to-text processing data captured
- No personal information stored permanently
- AWS logs accessed with proper credentials

## 💡 Benefits for Testing

- **Real-time Feedback:** See speech processing as it happens
- **Historical Analysis:** Track performance over time
- **Issue Detection:** Identify speech recognition problems
- **Performance Monitoring:** Measure system reliability
- **Debugging Aid:** Detailed logs for troubleshooting

## 🚀 Perfect For:

- **Development Testing:** Validate speech processing changes
- **QA Validation:** Comprehensive testing workflows
- **Performance Analysis:** Monitor system health
- **Issue Investigation:** Debug speech recognition problems
- **User Acceptance Testing:** Demonstrate system capabilities

---

*The permanent speech monitor provides complete visibility into your voice-to-database pipeline, making it perfect for ongoing testing and validation.*