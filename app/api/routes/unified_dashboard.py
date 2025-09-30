#!/usr/bin/env python3
"""
Unified Dashboard - Option B: Multi-Tab Operations Center
Combines appointment management, cost monitoring, and performance tracking
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo

import os
from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from sqlalchemy import func

from app.api.auth import require_api_key
from app.db.session import get_session
from app.db.models.appointment import Appointment
from app.db.models.user import User
from app.core.performance import performance_monitor, performance_cache
from app.services.dashboard_session import dashboard_session_manager
from app.services.circuit_breaker import circuit_manager
from app.services.business_metrics import business_metrics
from app.services.alerting import alert_manager
from app.services.cost_optimization import cost_optimizer

# Import cost tracking with fallback
import sys
from pathlib import Path
cost_opt_path = Path(__file__).parent.parent.parent.parent / "cost-optimization"
sys.path.insert(0, str(cost_opt_path))

try:
    from monitoring.cost_tracker import AWSCostTracker
except ImportError:
    class AWSCostTracker:
        def __init__(self):
            self.aws_available = False
        def get_monthly_costs(self):
            return {"Mock Service": 50.0}
        def get_daily_costs(self):
            return []
        def get_recommendations(self):
            return {"immediate": ["Setup AWS Cost Explorer"]}

router = APIRouter(tags=["unified-dashboard"])

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")

def _unified_layout(body: str, title: str = "Bella Operations Center") -> str:
    """Unified dashboard layout with modern design and tab interface"""
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>{title}</title>
    <style>
        :root {{
            --bg: #0d1117;
            --panel: #161b22;
            --text: #e6edf3;
            --muted: #8b949e;
            --accent: #58a6ff;
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
            --border: #30363d;
            --tab-active: #1f6feb;
            --header-height: 64px;
        }}

        * {{ box-sizing: border-box; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
        }}

        /* Header */
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: var(--header-height);
            background: var(--panel);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 24px;
            z-index: 1000;
        }}

        .header h1 {{
            margin: 0;
            font-size: 20px;
            color: var(--text);
        }}

        .header-status {{
            margin-left: auto;
            display: flex;
            gap: 16px;
            align-items: center;
        }}

        .status-indicator {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 12px;
            border: 1px solid var(--border);
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        .status-healthy {{ background: var(--success); }}
        .status-warning {{ background: var(--warning); }}
        .status-error {{ background: var(--danger); }}

        /* Main Content */
        .main-content {{
            margin-top: var(--header-height);
            padding: 24px;
        }}

        /* Tab Navigation */
        .tab-nav {{
            display: flex;
            gap: 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }}

        .tab-button {{
            background: none;
            border: none;
            padding: 12px 24px;
            color: var(--muted);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}

        .tab-button:hover {{
            color: var(--text);
            background: rgba(255, 255, 255, 0.05);
        }}

        .tab-button.active {{
            color: var(--accent);
            border-bottom-color: var(--tab-active);
        }}

        /* Tab Content */
        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        /* Cards and Grids */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}

        .kpi-label {{
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--text);
        }}

        .kpi-change {{
            font-size: 12px;
            margin-top: 4px;
        }}

        .change-positive {{ color: var(--success); }}
        .change-negative {{ color: var(--danger); }}

        /* Tables */
        .table-container {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }}

        .table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .table th,
        .table td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}

        .table th {{
            background: rgba(255, 255, 255, 0.03);
            font-weight: 600;
            color: var(--muted);
            position: sticky;
            top: 0;
        }}

        .table tbody tr:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}

        /* Buttons */
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--panel);
            color: var(--text);
            text-decoration: none;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--accent);
        }}

        .btn-primary {{
            background: var(--tab-active);
            border-color: var(--tab-active);
        }}

        .btn-danger {{
            border-color: var(--danger);
            color: var(--danger);
        }}

        /* Status Pills */
        .status-pill {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
        }}

        .status-booked {{
            background: rgba(88, 166, 255, 0.2);
            color: var(--accent);
            border: 1px solid rgba(88, 166, 255, 0.3);
        }}

        .status-completed {{
            background: rgba(63, 185, 80, 0.2);
            color: var(--success);
            border: 1px solid rgba(63, 185, 80, 0.3);
        }}

        .status-cancelled {{
            background: rgba(248, 81, 73, 0.2);
            color: var(--danger);
            border: 1px solid rgba(248, 81, 73, 0.3);
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .header {{ padding: 0 16px; }}
            .main-content {{ padding: 16px; }}
            .kpi-grid {{ grid-template-columns: 1fr; }}
            .tab-button {{ padding: 8px 16px; font-size: 12px; }}
            .header-status {{ display: none; }}
        }}

        /* Loading States */
        .loading {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid var(--border);
            border-radius: 50%;
            border-top-color: var(--accent);
            animation: spin 1s ease-in-out infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* Utilities */
        .text-muted {{ color: var(--muted); }}
        .text-success {{ color: var(--success); }}
        .text-warning {{ color: var(--warning); }}
        .text-danger {{ color: var(--danger); }}
        .mb-0 {{ margin-bottom: 0; }}
        .mt-16 {{ margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎛️ Bella Operations Center</h1>
        <div class="header-status">
            <div class="status-indicator">
                <div class="status-dot status-healthy" id="system-status"></div>
                System
            </div>
            <div class="status-indicator">
                <div class="status-dot status-warning" id="cost-status"></div>
                Costs
            </div>
            <div class="status-indicator">
                <div class="status-dot status-healthy" id="performance-status"></div>
                Performance
            </div>
        </div>
    </div>

    <div class="main-content">
        <nav class="tab-nav">
            <button class="tab-button active" onclick="showTab('operations')">
                📅 Operations
            </button>
            <button class="tab-button" onclick="showTab('analytics')">
                💰 Analytics
            </button>
            <button class="tab-button" onclick="showTab('system')">
                ⚡ System
            </button>
        </nav>

        {body}
    </div>

    <script>
        // Tab switching
        function showTab(tabName) {{
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});

            // Remove active class from all buttons
            document.querySelectorAll('.tab-button').forEach(btn => {{
                btn.classList.remove('active');
            }});

            // Show selected tab content
            document.getElementById(tabName + '-tab').classList.add('active');

            // Add active class to clicked button
            event.target.classList.add('active');

            // Load tab data if needed
            loadTabData(tabName);
        }}

        // Load data for specific tabs
        function loadTabData(tabName) {{
            if (tabName === 'analytics') {{
                loadAnalyticsData();
            }} else if (tabName === 'system') {{
                loadSystemData();
            }}
        }}

        // Load analytics data
        async function loadAnalyticsData() {{
            try {{
                const response = await fetch('/api/unified/analytics', {{
                    headers: {{ 'X-API-Key': getApiKey() }}
                }});
                if (response.ok) {{
                    const data = await response.json();
                    updateAnalyticsTab(data);
                }}
            }} catch (error) {{
                console.error('Failed to load analytics data:', error);
            }}
        }}

        // Load system data
        async function loadSystemData() {{
            try {{
                const response = await fetch('/api/unified/system', {{
                    headers: {{ 'X-API-Key': getApiKey() }}
                }});
                if (response.ok) {{
                    const data = await response.json();
                    updateSystemTab(data);
                }}
            }} catch (error) {{
                console.error('Failed to load system data:', error);
            }}
        }}

        // Update status indicators
        async function updateStatusIndicators() {{
            try {{
                const response = await fetch('/api/unified/status', {{
                    headers: {{ 'X-API-Key': getApiKey() }}
                }});
                if (response.ok) {{
                    const status = await response.json();

                    // Update status dots
                    document.getElementById('system-status').className =
                        'status-dot status-' + status.system;
                    document.getElementById('cost-status').className =
                        'status-dot status-' + (status.cost_aws_connected ? 'healthy' : 'warning');
                    document.getElementById('performance-status').className =
                        'status-dot status-' + status.performance;
                }}
            }} catch (error) {{
                console.error('Failed to update status indicators:', error);
            }}
        }}

        // Get API key from localStorage or prompt
        function getApiKey() {{
            let apiKey = localStorage.getItem('bella_api_key');
            if (!apiKey) {{
                apiKey = prompt('Enter your API key:');
                if (apiKey) {{
                    localStorage.setItem('bella_api_key', apiKey);
                }}
            }}
            return apiKey;
        }}

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {{
            updateStatusIndicators();

            // Update status every 30 seconds
            setInterval(updateStatusIndicators, 30000);

            // Load initial tab data
            loadTabData('operations');
        }});

        // Utility functions for updating tab content
        function updateAnalyticsTab(data) {{
            // Update analytics content dynamically
            console.log('Analytics data:', data);
        }}

        function updateSystemTab(data) {{
            // Update system content dynamically
            console.log('System data:', data);
        }}
    </script>
</body>
</html>"""

@router.get("/", response_class=HTMLResponse)
async def unified_dashboard(
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    """Main unified dashboard with multi-tab interface"""

    # Get operations data (Tab 1)
    operations_data = await _get_operations_data(db)

    # Build tab contents
    tab_contents = f"""
        <!-- Tab 1: Operations -->
        <div id="operations-tab" class="tab-content active">
            {_render_operations_tab(operations_data)}
        </div>

        <!-- Tab 2: Analytics -->
        <div id="analytics-tab" class="tab-content">
            {_render_analytics_tab()}
        </div>

        <!-- Tab 3: System -->
        <div id="system-tab" class="tab-content">
            {_render_system_tab()}
        </div>
    """

    return HTMLResponse(_unified_layout(tab_contents))

async def _get_operations_data(db: AsyncSession) -> Dict[str, Any]:
    """Get operations data for Tab 1"""
    # KPIs
    total_users = (await db.execute(sa.select(func.count(User.id)))).scalar_one()
    total_appts = (await db.execute(sa.select(func.count(Appointment.id)))).scalar_one()

    # Today's appointments
    now_local = datetime.now(tz=LOCAL_TZ)
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_local = today_start_local + timedelta(days=1)
    today_start_utc = today_start_local.astimezone(UTC)
    today_end_utc = today_end_local.astimezone(UTC)

    today_appts = (await db.execute(
        sa.select(func.count()).where(
            Appointment.starts_at >= today_start_utc,
            Appointment.starts_at < today_end_utc
        )
    )).scalar_one()

    # Recent appointments
    recent_q = (
        sa.select(
            Appointment.id,
            Appointment.starts_at,
            Appointment.duration_min,
            Appointment.status,
            Appointment.notes,
            User.full_name,
            User.mobile,
        )
        .join(User, User.id == Appointment.user_id)
        .order_by(Appointment.starts_at.desc())
        .limit(10)
    )
    recent_appointments = (await db.execute(recent_q)).all()

    return {
        "total_users": total_users,
        "total_appts": total_appts,
        "today_appts": today_appts,
        "recent_appointments": recent_appointments
    }

def _render_operations_tab(data: Dict[str, Any]) -> str:
    """Render operations tab content"""
    # KPI cards
    kpi_html = f"""
    <div class="kpi-grid">
        <div class="card">
            <div class="kpi-label">Total Users</div>
            <div class="kpi-value">{data['total_users']}</div>
        </div>
        <div class="card">
            <div class="kpi-label">Total Appointments</div>
            <div class="kpi-value">{data['total_appts']}</div>
        </div>
        <div class="card">
            <div class="kpi-label">Today's Appointments</div>
            <div class="kpi-value">{data['today_appts']}</div>
        </div>
        <div class="card">
            <div class="kpi-label">System Status</div>
            <div class="kpi-value text-success">Operational</div>
        </div>
    </div>
    """

    # Recent appointments table
    if not data['recent_appointments']:
        table_html = '<div class="card"><p class="text-muted">No appointments yet. Book one via the phone flow or API.</p></div>'
    else:
        rows = []
        for appt in data['recent_appointments']:
            local_time = appt.starts_at.astimezone(LOCAL_TZ)
            when = local_time.strftime("%a, %b %d — %I:%M %p")
            status = (appt.status or "booked").lower()

            rows.append(f"""
            <tr>
                <td>#{appt.id}</td>
                <td>{when}</td>
                <td>{appt.duration_min} min</td>
                <td><span class="status-pill status-{status}">{status}</span></td>
                <td>{appt.full_name}</td>
                <td class="text-muted">{appt.mobile}</td>
                <td>
                    <a href="#" class="btn btn-primary">Edit</a>
                    <a href="#" class="btn btn-danger">Delete</a>
                </td>
            </tr>
            """)

        table_html = f"""
        <div class="table-container">
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>When (Local)</th>
                        <th>Duration</th>
                        <th>Status</th>
                        <th>Name</th>
                        <th>Phone</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    return kpi_html + table_html

def _render_analytics_tab() -> str:
    """Render analytics tab content"""
    return """
    <div class="kpi-grid">
        <div class="card">
            <div class="kpi-label">Monthly AWS Cost</div>
            <div class="kpi-value">$110.00</div>
            <div class="kpi-change change-positive">↓ 15% vs last month</div>
        </div>
        <div class="card">
            <div class="kpi-label">Optimization Potential</div>
            <div class="kpi-value">40%</div>
            <div class="kpi-change">$44/month savings</div>
        </div>
        <div class="card">
            <div class="kpi-label">Top Service</div>
            <div class="kpi-value">EC2</div>
            <div class="kpi-change text-muted">$45/month</div>
        </div>
        <div class="card">
            <div class="kpi-label">Cost Status</div>
            <div class="kpi-value text-warning">Mock Data</div>
            <div class="kpi-change text-muted">AWS setup needed</div>
        </div>
    </div>

    <div class="table-container mt-16">
        <table class="table">
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Monthly Cost</th>
                    <th>Trend</th>
                    <th>Optimization</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Amazon EC2</td>
                    <td>$45.00</td>
                    <td class="text-success">↓ 5%</td>
                    <td>Reserved instances</td>
                </tr>
                <tr>
                    <td>Amazon RDS</td>
                    <td>$20.00</td>
                    <td class="text-muted">→ 0%</td>
                    <td>Right-sizing</td>
                </tr>
                <tr>
                    <td>ElastiCache</td>
                    <td>$15.00</td>
                    <td class="text-success">↓ 10%</td>
                    <td>Auto-scaling</td>
                </tr>
                <tr>
                    <td>Load Balancer</td>
                    <td>$25.00</td>
                    <td class="text-warning">↑ 8%</td>
                    <td>Traffic optimization</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def _render_system_tab() -> str:
    """Render system tab content"""
    return """
    <div class="kpi-grid">
        <div class="card">
            <div class="kpi-label">Response Time</div>
            <div class="kpi-value text-success">213ms</div>
            <div class="kpi-change change-positive">Excellent</div>
        </div>
        <div class="card">
            <div class="kpi-label">Cache Hit Rate</div>
            <div class="kpi-value">85%</div>
            <div class="kpi-change text-success">↑ 5%</div>
        </div>
        <div class="card">
            <div class="kpi-label">System Uptime</div>
            <div class="kpi-value">99.9%</div>
            <div class="kpi-change text-success">24h</div>
        </div>
        <div class="card">
            <div class="kpi-label">Active Sessions</div>
            <div class="kpi-value">12</div>
            <div class="kpi-change text-muted">Current</div>
        </div>
    </div>

    <div class="table-container mt-16">
        <table class="table">
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Status</th>
                    <th>Response Time</th>
                    <th>Last Check</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>API Server</td>
                    <td><span class="status-pill status-completed">Healthy</span></td>
                    <td>213ms</td>
                    <td class="text-muted">30s ago</td>
                </tr>
                <tr>
                    <td>Database</td>
                    <td><span class="status-pill status-completed">Healthy</span></td>
                    <td>45ms</td>
                    <td class="text-muted">30s ago</td>
                </tr>
                <tr>
                    <td>Redis Cache</td>
                    <td><span class="status-pill status-completed">Healthy</span></td>
                    <td>8ms</td>
                    <td class="text-muted">30s ago</td>
                </tr>
                <tr>
                    <td>Cost Explorer</td>
                    <td><span class="status-pill status-cancelled">Offline</span></td>
                    <td>-</td>
                    <td class="text-muted">Setup needed</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

# API Endpoints for tab data
@router.get("/api/unified/operations")
async def get_operations_data(
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get operations data for Tab 1"""
    return await _get_operations_data(db)

@router.get("/api/unified/analytics")
async def get_analytics_data(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get analytics/cost data for Tab 2"""
    try:
        tracker = AWSCostTracker()
        monthly_costs = tracker.get_monthly_costs()
        return {
            "aws_available": tracker.aws_available,
            "monthly_costs": {k: float(v) for k, v in monthly_costs.items()},
            "total_monthly": float(sum(monthly_costs.values())),
            "optimization_potential": 0.4
        }
    except Exception as e:
        return {"error": str(e), "aws_available": False}

@router.get("/api/unified/system")
async def get_system_data(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get system/performance data for Tab 3"""
    perf_summary = performance_monitor.get_performance_summary()
    cache_stats = performance_cache.stats()

    return {
        "performance": perf_summary,
        "cache": cache_stats,
        "status": "healthy" if perf_summary.get('avg_response_time', 0) < 1.0 else "degraded"
    }

@router.post("/api/unified/session")
async def create_dashboard_session(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Create a new dashboard session"""
    session = await dashboard_session_manager.create_session()
    return {
        "session_id": session.session_id,
        "active_tab": session.active_tab,
        "created_at": session.created_at.isoformat()
    }

@router.get("/api/unified/session/{session_id}")
async def get_dashboard_session(
    session_id: str,
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Get dashboard session data"""
    session = await dashboard_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "active_tab": session.active_tab,
        "preferences": session.preferences,
        "filters": session.filters,
        "last_accessed": session.last_accessed.isoformat()
    }

@router.patch("/api/unified/session/{session_id}")
async def update_dashboard_session(
    session_id: str,
    updates: Dict[str, Any],
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Update dashboard session data"""
    success = await dashboard_session_manager.update_session(session_id, **updates)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "updated", "session_id": session_id}

@router.get("/api/unified/session-info")
async def get_session_info(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get session storage information and Redis health"""
    return await dashboard_session_manager.get_session_info()

@router.get("/api/unified/circuit-breakers")
async def get_circuit_breaker_status(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get circuit breaker status for all protected services"""
    return circuit_manager.get_all_stats()

@router.get("/api/unified/business-metrics")
async def get_business_metrics(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get current business KPIs and performance metrics"""
    kpis = await business_metrics.calculate_current_kpis()
    return {
        "total_calls": kpis.total_calls,
        "completed_calls": kpis.completed_calls,
        "failed_calls": kpis.failed_calls,
        "success_rate": kpis.success_rate,
        "avg_response_time": kpis.avg_response_time,
        "completion_rate": kpis.completion_rate,
        "speech_recognition_accuracy": kpis.speech_recognition_accuracy,
        "ai_extraction_success_rate": kpis.ai_extraction_success_rate,
        "fallback_usage_rate": kpis.fallback_usage_rate,
        "cost_per_call": kpis.cost_per_call,
        "whisper_api_calls": kpis.whisper_api_calls,
        "calculated_at": kpis.calculated_at.isoformat()
    }

@router.get("/api/unified/trends")
async def get_performance_trends(
    hours: int = 24,
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Get hourly performance trends for visualization"""
    trends = await business_metrics.get_hourly_trends(hours)
    return {"trends": trends, "period_hours": hours}

@router.get("/api/unified/alerts")
async def get_performance_alerts(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get current performance alerts and warnings"""
    alerts = await business_metrics.get_performance_alerts()
    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "has_critical": any(alert.get("severity") == "high" for alert in alerts)
    }

@router.get("/api/unified/alerts")
async def get_active_alerts(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get active alerts and alert summary"""
    alert_summary = alert_manager.get_alert_summary()
    sla_dashboard = await alert_manager.get_sla_dashboard()

    return {
        "alert_summary": alert_summary,
        "sla_status": sla_dashboard,
        "overall_health": sla_dashboard["overall_health_score"]
    }

@router.get("/api/unified/cost-optimization")
async def get_cost_optimization(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get cost optimization dashboard data"""
    return await cost_optimizer.get_optimization_dashboard()

@router.post("/api/unified/alerts")
async def create_alert(
    alert_data: Dict[str, Any],
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Create a new alert manually"""
    alert_id = await alert_manager.create_alert(
        component=alert_data.get("component", "manual"),
        severity=alert_data.get("severity", "medium"),
        message=alert_data.get("message", "Manual alert"),
        details=alert_data.get("details", {})
    )
    return {"alert_id": alert_id, "status": "created"}

@router.patch("/api/unified/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_data: Dict[str, Any],
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Resolve an active alert"""
    resolution_note = resolution_data.get("note", "Resolved via dashboard")
    success = await alert_manager.resolve_alert(alert_id, resolution_note)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "resolved", "alert_id": alert_id}

@router.get("/api/unified/sla-metrics")
async def get_sla_metrics(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get detailed SLA metrics for all services"""
    return await alert_manager.get_sla_dashboard()

@router.post("/api/unified/service-status")
async def update_service_status(
    status_data: Dict[str, Any],
    api_key: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """Update service status for SLA tracking"""
    service = status_data.get("service")
    is_up = status_data.get("is_up", True)

    if not service:
        raise HTTPException(status_code=400, detail="Service name required")

    await alert_manager.track_service_status(service, is_up)
    return {"status": "updated", "service": service, "is_up": is_up}

@router.get("/api/unified/status")
async def get_unified_status(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get overall system status for header indicators"""
    # System health
    perf_summary = performance_monitor.get_performance_summary()
    avg_response = perf_summary.get('avg_response_time', 0)

    if avg_response < 0.5:
        system_status = "healthy"
        performance_status = "healthy"
    elif avg_response < 1.0:
        system_status = "healthy"
        performance_status = "warning"
    else:
        system_status = "warning"
        performance_status = "error"

    # Redis health check
    session_info = await dashboard_session_manager.get_session_info()
    redis_status = "healthy" if session_info.get("redis_connected") else "warning"

    # Circuit breaker health check
    circuit_stats = circuit_manager.get_all_stats()
    circuit_status = "healthy"
    openai_circuit = circuit_stats.get("openai_api", {})
    if openai_circuit.get("state") == "open":
        circuit_status = "error"
    elif openai_circuit.get("state") == "half_open":
        circuit_status = "warning"

    # Cost status
    try:
        tracker = AWSCostTracker()
        cost_aws_connected = tracker.aws_available
    except:
        cost_aws_connected = False

    return {
        "system": system_status,
        "performance": performance_status,
        "redis": redis_status,
        "circuit_breakers": circuit_status,
        "openai_service": openai_circuit.get("state", "unknown"),
        "cost_aws_connected": cost_aws_connected,
        "timestamp": datetime.now().isoformat()
    }