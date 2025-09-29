# 🎛️ Unified Dashboard Access Guide

## 🚀 Quick Start

```bash
# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Access unified dashboard
# URL: http://localhost:8000/
# Auth: X-API-Key: bella-dev-key-2024
```

## 📊 Dashboard Features

### 🎯 Single Interface with 3 Tabs:

**📅 Tab 1: Operations**
- Appointment management (view, edit, delete)
- User management and statistics
- Today's appointment summary
- Real-time KPIs (users, appointments, status)

**💰 Tab 2: Analytics**
- AWS cost monitoring and breakdown
- Cost optimization recommendations
- Monthly spending trends
- Service-level cost analysis

**⚡ Tab 3: System**
- API performance monitoring
- Cache hit rates and response times
- System health indicators
- Component status monitoring

### 🔄 Real-time Updates
- Status indicators in header
- Automatic data refresh every 30 seconds
- Live performance metrics
- Dynamic cost tracking

## 🔑 Authentication

**API Key Method:**
```bash
# Via Header (recommended)
curl -H "X-API-Key: bella-dev-key-2024" http://localhost:8000/

# Via JavaScript
fetch('http://localhost:8000/', {
  headers: { 'X-API-Key': 'bella-dev-key-2024' }
})
```

## 🛠 API Endpoints

```bash
# Main dashboard
GET /
→ Returns complete unified dashboard HTML

# Tab data APIs
GET /api/unified/operations
→ Appointment management data

GET /api/unified/analytics
→ Cost monitoring data

GET /api/unified/system
→ Performance monitoring data

GET /api/unified/status
→ System status for header indicators
```

## 📱 Responsive Design

- Desktop: Full 3-tab interface with sidebar
- Tablet: Collapsible tabs with touch navigation
- Mobile: Stacked layout with swipe gestures

## 🔧 Configuration

```bash
# API Key
export BELLA_API_KEY="your-production-key"

# AWS Cost Monitoring (optional)
./scripts/setup-aws-cost-monitoring.sh
```

## 🎯 Production Deployment

1. Set production API key: `export BELLA_API_KEY="secure-production-key"`
2. Configure AWS Cost Explorer: `./scripts/setup-aws-cost-monitoring.sh`
3. Start with SSL: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Access: `https://your-domain.com/`

## 🚀 Migration from Old Dashboards

**Old → New Mapping:**
- `http://localhost:8000/` (Basic Auth) → `http://localhost:8000/` Tab 1 (Operations)
- `http://localhost:8000/dashboard/` → `http://localhost:8000/` Tab 2 (Analytics)
- `http://localhost:8000/performance/health` → `http://localhost:8000/` Tab 3 (System)

**Authentication Change:**
- Old: HTTP Basic Auth (admin/changeme) + API Keys
- New: Single API Key for everything

## 🎉 Benefits

✅ **Single Access Point** - One URL for all operations
✅ **Unified Authentication** - One API key for everything
✅ **Consistent UX** - Same design language across all functions
✅ **Real-time Updates** - Live status indicators and data refresh
✅ **Mobile Responsive** - Works perfectly on all devices
✅ **Production Ready** - Secure, scalable, and maintainable

The unified dashboard provides everything you need in one comprehensive interface! 🎛️
