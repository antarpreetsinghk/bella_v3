#!/usr/bin/env python3
"""
Professional Admin Dashboard - Appointments & Users Management System
Username/password authentication with modern UI/UX
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo

import os
import hashlib
import secrets
from fastapi import APIRouter, Depends, Response, HTTPException, Form, Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from sqlalchemy import func, desc, asc

from app.db.session import get_session
from app.db.models.appointment import Appointment
from app.db.models.user import User

router = APIRouter(tags=["admin-dashboard"])

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")

# Admin credentials (in production, store securely)
ADMIN_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "super_admin",
        "name": "Admin User"
    },
    "manager": {
        "password_hash": hashlib.sha256("manager123".encode()).hexdigest(),
        "role": "manager",
        "name": "Manager User"
    }
}

# Session secret key for token signing
SESSION_SECRET = os.getenv("CSRF_SECRET", "bella-admin-secret-key-2024")

def verify_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify admin credentials"""
    if username in ADMIN_USERS:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash == ADMIN_USERS[username]["password_hash"]:
            return ADMIN_USERS[username]
    return None

def create_session(username: str) -> str:
    """Create a stateless admin session token"""
    import time
    import base64
    import hmac

    # Create payload with username and expiration
    payload = f"{username}:{int(time.time())}"
    payload_b64 = base64.b64encode(payload.encode()).decode()

    # Create signature
    signature = hmac.new(
        SESSION_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    # Return token = payload.signature
    return f"{payload_b64}.{signature}"

def verify_session(session_token: Optional[str]) -> Optional[str]:
    """Verify stateless admin session token"""
    if not session_token:
        return None

    try:
        import time
        import base64
        import hmac

        # Split token into payload and signature
        if '.' not in session_token:
            return None

        payload_b64, signature = session_token.split('.', 1)

        # Verify signature
        expected_signature = hmac.new(
            SESSION_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_signature):
            return None

        # Decode payload
        payload = base64.b64decode(payload_b64).decode()
        username, timestamp_str = payload.split(':', 1)
        timestamp = int(timestamp_str)

        # Check expiration (8 hours)
        if time.time() - timestamp > 8 * 3600:
            return None

        # Verify username still exists
        if username not in ADMIN_USERS:
            return None

        return username

    except (ValueError, TypeError, Exception):
        return None

def require_admin_auth(session_id: Optional[str] = Cookie(None, alias="admin_session")):
    """Dependency to require admin authentication"""
    username = verify_session(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")
    return username

def admin_layout(body: str, title: str = "Bella Admin Dashboard", active_tab: str = "appointments") -> str:
    """Professional admin dashboard layout"""
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root {{
            --bella-primary: #4f46e5;
            --bella-secondary: #6366f1;
            --bella-success: #10b981;
            --bella-warning: #f59e0b;
            --bella-danger: #ef4444;
            --bella-dark: #1f2937;
            --bella-light: #f9fafb;
        }}

        body {{
            background-color: var(--bella-light);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}

        .navbar-brand {{
            font-weight: 700;
            color: var(--bella-primary) !important;
        }}

        .navbar {{
            background: white !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .sidebar {{
            background: var(--bella-dark);
            min-height: calc(100vh - 56px);
            padding: 0;
        }}

        .nav-link {{
            color: #d1d5db !important;
            padding: 12px 20px;
            border-left: 3px solid transparent;
            transition: all 0.2s;
        }}

        .nav-link:hover {{
            color: white !important;
            background-color: rgba(255,255,255,0.1);
        }}

        .nav-link.active {{
            color: white !important;
            background-color: var(--bella-primary);
            border-left-color: var(--bella-secondary);
        }}

        .main-content {{
            background: white;
            min-height: calc(100vh - 56px);
            padding: 30px;
        }}

        .stats-card {{
            background: linear-gradient(135deg, var(--bella-primary), var(--bella-secondary));
            color: white;
            border-radius: 12px;
            padding: 24px;
            border: none;
        }}

        .stats-number {{
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0;
        }}

        .stats-label {{
            opacity: 0.9;
            font-size: 0.9rem;
            margin-top: 4px;
        }}

        .table-card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: none;
        }}

        .table-card .card-header {{
            background: white;
            border-bottom: 1px solid #e5e7eb;
            padding: 20px 24px;
        }}

        .table-card .card-body {{
            padding: 0;
        }}

        .table {{
            margin: 0;
        }}

        .table th {{
            background-color: #f8f9fa;
            border: none;
            padding: 16px 24px;
            color: var(--bella-dark);
            font-weight: 600;
        }}

        .table td {{
            border: none;
            padding: 16px 24px;
            border-bottom: 1px solid #f3f4f6;
        }}

        .badge {{
            font-size: 0.75rem;
            padding: 6px 12px;
        }}

        .btn-sm {{
            padding: 6px 12px;
            font-size: 0.8rem;
        }}

        .page-header {{
            margin-bottom: 32px;
        }}

        .page-title {{
            color: var(--bella-dark);
            font-weight: 700;
            margin: 0;
        }}

        .page-subtitle {{
            color: #6b7280;
            margin-top: 4px;
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #6b7280;
        }}

        .empty-state i {{
            font-size: 3rem;
            margin-bottom: 16px;
            opacity: 0.5;
        }}

        .status-booked {{ background-color: var(--bella-primary); }}
        .status-completed {{ background-color: var(--bella-success); }}
        .status-cancelled {{ background-color: var(--bella-danger); }}
        .status-confirmed {{ background-color: var(--bella-warning); }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-light">
        <div class="container-fluid">
            <a class="navbar-brand" href="/admin">
                <i class="bi bi-calendar-check me-2"></i>Bella Admin
            </a>
            <div class="navbar-nav ms-auto">
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        <i class="bi bi-person-circle me-1"></i>Admin
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="/admin/logout">
                            <i class="bi bi-box-arrow-right me-2"></i>Logout
                        </a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <div class="container-fluid p-0">
        <div class="row g-0">
            <!-- Sidebar -->
            <div class="col-md-3 col-lg-2">
                <div class="sidebar">
                    <nav class="nav flex-column">
                        <a class="nav-link {'active' if active_tab == 'appointments' else ''}" href="/admin">
                            <i class="bi bi-calendar3 me-2"></i>Appointments
                        </a>
                        <a class="nav-link {'active' if active_tab == 'users' else ''}" href="/admin/users">
                            <i class="bi bi-people me-2"></i>Users
                        </a>
                        <a class="nav-link {'active' if active_tab == 'analytics' else ''}" href="/admin/analytics">
                            <i class="bi bi-graph-up me-2"></i>Analytics
                        </a>
                    </nav>
                </div>
            </div>

            <!-- Main Content -->
            <div class="col-md-9 col-lg-10">
                <div class="main-content">
                    {body}
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Appointment management functions
        async function deleteAppointment(appointmentId) {{
            if (!confirm('Are you sure you want to delete this appointment? This action cannot be undone.')) {{
                return;
            }}

            try {{
                const response = await fetch(`/admin/appointments/${{appointmentId}}/delete`, {{
                    method: 'POST',
                    credentials: 'same-origin'
                }});

                if (response.ok) {{
                    location.reload();
                }} else {{
                    alert('Failed to delete appointment. Please try again.');
                }}
            }} catch (error) {{
                console.error('Delete error:', error);
                alert('Error deleting appointment. Please try again.');
            }}
        }}

        async function updateAppointmentStatus(appointmentId, newStatus) {{
            try {{
                const response = await fetch(`/admin/appointments/${{appointmentId}}/status`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ status: newStatus }})
                }});

                if (response.ok) {{
                    location.reload();
                }} else {{
                    alert('Failed to update appointment status.');
                }}
            }} catch (error) {{
                console.error('Update error:', error);
                alert('Error updating appointment status.');
            }}
        }}

        async function syncToCalendar(appointmentId) {{
            if (!confirm('Sync this appointment to Google Calendar?')) {{
                return;
            }}

            try {{
                const response = await fetch(`/admin/appointments/${{appointmentId}}/sync-calendar`, {{
                    method: 'POST',
                    credentials: 'same-origin'
                }});

                if (response.ok) {{
                    const result = await response.json();
                    alert(`Successfully synced to Google Calendar! Event ID: ${{result.event_id}}`);
                    location.reload();
                }} else {{
                    const error = await response.json();
                    alert(`Failed to sync to calendar: ${{error.detail}}`);
                }}
            }} catch (error) {{
                console.error('Calendar sync error:', error);
                alert('Error syncing to calendar. Please try again.');
            }}
        }}

        async function editAppointment(appointmentId) {{
            // Get current appointment data (simplified - in a real app you'd fetch this from the server)
            const newDateTime = prompt('Enter new appointment date and time (YYYY-MM-DD HH:MM):');
            if (!newDateTime) return;

            const newDuration = prompt('Enter duration in minutes:', '30');
            if (!newDuration) return;

            const newNotes = prompt('Enter notes (optional):') || '';

            try {{
                const response = await fetch(`/admin/appointments/${{appointmentId}}/edit`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{
                        starts_at: newDateTime,
                        duration_min: parseInt(newDuration),
                        notes: newNotes
                    }})
                }});

                if (response.ok) {{
                    alert('Appointment updated successfully!');
                    location.reload();
                }} else {{
                    const error = await response.json();
                    alert(`Failed to update appointment: ${{error.detail}}`);
                }}
            }} catch (error) {{
                console.error('Edit error:', error);
                alert('Error updating appointment. Please try again.');
            }}
        }}

        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page():
    """Admin login page"""
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Bella Admin Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {{
            --bella-primary: #4f46e5;
            --bella-secondary: #6366f1;
        }}

        body {{
            background: linear-gradient(135deg, var(--bella-primary), var(--bella-secondary));
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .login-card {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }}

        .login-header {{
            text-align: center;
            margin-bottom: 32px;
        }}

        .login-header h1 {{
            color: var(--bella-primary);
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .login-header p {{
            color: #6b7280;
            margin: 0;
        }}

        .form-control {{
            border-radius: 8px;
            border: 2px solid #e5e7eb;
            padding: 12px 16px;
        }}

        .form-control:focus {{
            border-color: var(--bella-primary);
            box-shadow: 0 0 0 0.2rem rgba(79, 70, 229, 0.25);
        }}

        .btn-primary {{
            background: var(--bella-primary);
            border: none;
            border-radius: 8px;
            padding: 12px;
            font-weight: 600;
        }}

        .btn-primary:hover {{
            background: var(--bella-secondary);
        }}
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <h1><i class="bi bi-calendar-check"></i> Bella Admin</h1>
            <p>Appointments & Users Management</p>
        </div>

        <form method="post" action="/admin/login">
            <div class="mb-3">
                <label for="username" class="form-label">Username</label>
                <input type="text" class="form-control" id="username" name="username" required>
            </div>
            <div class="mb-4">
                <label for="password" class="form-label">Password</label>
                <input type="password" class="form-control" id="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100">Sign In</button>
        </form>

    </div>
</body>
</html>""")

@router.post("/login")
async def admin_login(
    username: str = Form(...),
    password: str = Form(...),
    response: Response = None
):
    """Process admin login"""
    user = verify_credentials(username, password)
    if not user:
        return RedirectResponse("/admin/login?error=invalid", status_code=302)

    session_id = create_session(username)
    response = RedirectResponse("/admin", status_code=302)
    response.set_cookie("admin_session", session_id, httponly=True, max_age=28800)  # 8 hours
    return response

@router.get("/logout")
async def admin_logout(session_id: Optional[str] = Cookie(None, alias="admin_session")):
    """Admin logout"""
    if session_id and session_id in active_sessions:
        del active_sessions[session_id]

    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Main appointments dashboard"""

    # Get statistics
    stats = await get_dashboard_stats(db)

    # Get recent appointments
    recent_appointments = await get_recent_appointments(db)

    # Build dashboard content
    content = f"""
    <div class="page-header">
        <h1 class="page-title">Appointments Dashboard</h1>
        <p class="page-subtitle">Manage and monitor customer appointments</p>
    </div>

    <!-- Statistics Cards -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{stats['total_appointments']}</div>
                <div class="stats-label">Total Appointments</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{stats['today_appointments']}</div>
                <div class="stats-label">Today's Appointments</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{stats['this_week_appointments']}</div>
                <div class="stats-label">This Week</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{stats['total_users']}</div>
                <div class="stats-label">Total Users</div>
            </div>
        </div>
    </div>

    <!-- Recent Appointments Table -->
    <div class="card table-card">
        <div class="card-header">
            <h5 class="mb-0">Recent Appointments</h5>
        </div>
        <div class="card-body">
            {render_appointments_table(recent_appointments)}
        </div>
    </div>
    """

    return HTMLResponse(admin_layout(content, active_tab="appointments"))

async def get_dashboard_stats(db: AsyncSession) -> Dict[str, int]:
    """Get dashboard statistics"""
    # Total appointments
    total_appointments = (await db.execute(sa.select(func.count(Appointment.id)))).scalar_one()

    # Total users
    total_users = (await db.execute(sa.select(func.count(User.id)))).scalar_one()

    # Today's appointments
    now_local = datetime.now(tz=LOCAL_TZ)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_start_utc = today_start.astimezone(UTC)
    today_end_utc = today_end.astimezone(UTC)

    today_appointments = (await db.execute(
        sa.select(func.count()).where(
            Appointment.starts_at >= today_start_utc,
            Appointment.starts_at < today_end_utc
        )
    )).scalar_one()

    # This week's appointments
    week_start = today_start - timedelta(days=today_start.weekday())
    week_end = week_start + timedelta(days=7)
    week_start_utc = week_start.astimezone(UTC)
    week_end_utc = week_end.astimezone(UTC)

    this_week_appointments = (await db.execute(
        sa.select(func.count()).where(
            Appointment.starts_at >= week_start_utc,
            Appointment.starts_at < week_end_utc
        )
    )).scalar_one()

    return {
        "total_appointments": total_appointments,
        "total_users": total_users,
        "today_appointments": today_appointments,
        "this_week_appointments": this_week_appointments
    }

async def get_recent_appointments(db: AsyncSession, limit: int = 20) -> List[Any]:
    """Get recent appointments with user details and Google Calendar sync status"""
    query = (
        sa.select(
            Appointment.id,
            Appointment.starts_at,
            Appointment.duration_min,
            Appointment.status,
            Appointment.notes,
            Appointment.created_at,
            Appointment.google_event_id,
            Appointment.modified_at,
            Appointment.modification_count,
            User.full_name,
            User.mobile
        )
        .join(User, User.id == Appointment.user_id)
        .order_by(desc(Appointment.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    return result.all()

def render_appointments_table(appointments: List[Any]) -> str:
    """Render appointments table HTML"""
    if not appointments:
        return '''
        <div class="empty-state">
            <i class="bi bi-calendar-x"></i>
            <h5>No appointments yet</h5>
            <p>Appointments will appear here once customers start booking through the phone system.</p>
        </div>
        '''

    rows = []
    for appt in appointments:
        # Format appointment time
        local_time = appt.starts_at.astimezone(LOCAL_TZ)
        formatted_time = local_time.strftime("%a, %b %d at %I:%M %p")

        # Status badge
        status = (appt.status or "booked").lower()
        status_class = f"status-{status}"

        # Google Calendar sync status
        has_calendar_event = bool(appt.google_event_id)
        calendar_status = "✅ Synced" if has_calendar_event else "❌ Not Synced"
        calendar_class = "text-success" if has_calendar_event else "text-warning"

        # Modification tracking
        modification_info = ""
        if appt.modification_count and appt.modification_count > 0:
            modification_info = f'<br><small class="text-info">Modified {appt.modification_count} time(s)</small>'

        rows.append(f"""
        <tr>
            <td>
                <strong>#{appt.id}</strong><br>
                <small class="text-muted">Created {appt.created_at.strftime("%m/%d %I:%M %p")}</small>
                {modification_info}
            </td>
            <td>
                <strong>{appt.full_name or 'Unknown'}</strong><br>
                <small class="text-muted">{appt.mobile}</small>
            </td>
            <td>
                {formatted_time}<br>
                <small class="text-muted">{appt.duration_min} minutes</small>
            </td>
            <td>
                <span class="badge {status_class}">{status.title()}</span><br>
                <small class="{calendar_class}">{calendar_status}</small>
            </td>
            <td>
                <small class="text-muted">{appt.notes[:50] + '...' if appt.notes and len(appt.notes) > 50 else appt.notes or ''}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="updateAppointmentStatus({appt.id}, 'confirmed')" title="Confirm">
                        <i class="bi bi-check"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="updateAppointmentStatus({appt.id}, 'completed')" title="Mark Complete">
                        <i class="bi bi-check2-all"></i>
                    </button>
                    {"" if has_calendar_event else f'<button class="btn btn-outline-info" onclick="syncToCalendar({appt.id})" title="Sync to Calendar"><i class="bi bi-calendar-plus"></i></button>'}
                    <button class="btn btn-outline-secondary" onclick="editAppointment({appt.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteAppointment({appt.id})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        """)

    return f"""
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Customer</th>
                    <th>Appointment Time</th>
                    <th>Status & Sync</th>
                    <th>Notes</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    """

@router.post("/appointments/{appointment_id}/delete")
async def delete_appointment(
    appointment_id: int,
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Delete an appointment"""
    result = await db.execute(
        sa.delete(Appointment).where(Appointment.id == appointment_id)
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"status": "deleted"}

@router.post("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    status_data: Dict[str, str],
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Update appointment status"""
    new_status = status_data.get("status")
    if new_status not in ["booked", "confirmed", "completed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    result = await db.execute(
        sa.update(Appointment)
        .where(Appointment.id == appointment_id)
        .values(status=new_status)
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"status": "updated"}

@router.post("/appointments/{appointment_id}/sync-calendar")
async def sync_appointment_to_calendar(
    appointment_id: int,
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Sync appointment to Google Calendar"""
    # Get appointment details
    query = (
        sa.select(Appointment, User)
        .join(User, User.id == Appointment.user_id)
        .where(Appointment.id == appointment_id)
    )
    result = await db.execute(query)
    appointment_data = result.first()

    if not appointment_data:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment, user = appointment_data

    # Check if already synced
    if appointment.google_event_id:
        raise HTTPException(status_code=400, detail="Appointment already synced to calendar")

    try:
        # Create Google Calendar event
        from app.services.google_calendar import create_calendar_event

        calendar_event = await create_calendar_event(
            user_name=user.full_name,
            user_mobile=user.mobile,
            starts_at_utc=appointment.starts_at,
            duration_min=appointment.duration_min,
            notes=appointment.notes
        )

        if calendar_event and calendar_event.get('event_id'):
            # Update appointment with calendar event ID
            await db.execute(
                sa.update(Appointment)
                .where(Appointment.id == appointment_id)
                .values(google_event_id=calendar_event['event_id'])
            )
            await db.commit()

            return {"success": True, "event_id": calendar_event['event_id']}
        else:
            raise HTTPException(status_code=500, detail="Failed to create calendar event")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar sync failed: {str(e)}")

@router.post("/appointments/{appointment_id}/edit")
async def edit_appointment(
    appointment_id: int,
    appointment_data: Dict[str, Any],
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Edit appointment details"""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    # Extract data
    starts_at = appointment_data.get("starts_at")
    duration_min = appointment_data.get("duration_min", 30)
    notes = appointment_data.get("notes", "")

    # Parse and validate the new time
    try:
        # Parse the datetime string (assuming local timezone)
        new_datetime = datetime.fromisoformat(starts_at)
        if new_datetime.tzinfo is None:
            new_datetime = new_datetime.replace(tzinfo=ZoneInfo("America/Edmonton"))
        new_datetime_utc = new_datetime.astimezone(ZoneInfo("UTC"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    # Get current appointment
    query = (
        sa.select(Appointment, User)
        .join(User, User.id == Appointment.user_id)
        .where(Appointment.id == appointment_id)
    )
    result = await db.execute(query)
    appointment_data_db = result.first()

    if not appointment_data_db:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment, user = appointment_data_db

    try:
        # Update appointment in database
        await db.execute(
            sa.update(Appointment)
            .where(Appointment.id == appointment_id)
            .values(
                starts_at=new_datetime_utc,
                duration_min=duration_min,
                notes=notes,
                modified_at=datetime.now(ZoneInfo("UTC")),
                modification_count=(appointment.modification_count or 0) + 1
            )
        )

        # Update Google Calendar event if it exists
        if appointment.google_event_id:
            try:
                from app.services.google_calendar import update_calendar_event

                await update_calendar_event(
                    event_id=appointment.google_event_id,
                    user_name=user.full_name,
                    user_mobile=user.mobile,
                    starts_at_utc=new_datetime_utc,
                    duration_min=duration_min,
                    notes=notes
                )
            except Exception as e:
                # Log the error but don't fail the appointment update
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to update calendar event: {e}")

        await db.commit()
        return {"success": True, "message": "Appointment updated successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update appointment: {str(e)}")

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Users management page"""

    # Get users statistics
    users_stats = await get_users_stats(db)

    # Get recent users
    recent_users = await get_recent_users(db)

    content = f"""
    <div class="page-header">
        <h1 class="page-title">Users Management</h1>
        <p class="page-subtitle">Manage customer accounts and information</p>
    </div>

    <!-- Users Statistics -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{users_stats['total_users']}</div>
                <div class="stats-label">Total Users</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{users_stats['new_this_week']}</div>
                <div class="stats-label">New This Week</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{users_stats['active_users']}</div>
                <div class="stats-label">Active Users</div>
            </div>
        </div>
    </div>

    <!-- Users Table -->
    <div class="card table-card">
        <div class="card-header">
            <h5 class="mb-0">All Users</h5>
        </div>
        <div class="card-body">
            {render_users_table(recent_users)}
        </div>
    </div>
    """

    return HTMLResponse(admin_layout(content, active_tab="users"))

@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics(
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Analytics page"""

    # Get analytics data
    analytics = await get_analytics_data(db)

    content = f"""
    <div class="page-header">
        <h1 class="page-title">Analytics</h1>
        <p class="page-subtitle">Business insights and performance metrics</p>
    </div>

    <!-- Key Metrics -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{analytics['appointments_this_month']}</div>
                <div class="stats-label">Appointments This Month</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{analytics['completion_rate']}%</div>
                <div class="stats-label">Completion Rate</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{analytics['avg_booking_time']}</div>
                <div class="stats-label">Avg. Booking Time</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{analytics['customer_satisfaction']}%</div>
                <div class="stats-label">Customer Satisfaction</div>
            </div>
        </div>
    </div>

    <!-- Charts and Tables -->
    <div class="row">
        <div class="col-md-6">
            <div class="card table-card">
                <div class="card-header">
                    <h5 class="mb-0">Appointment Status Distribution</h5>
                </div>
                <div class="card-body">
                    {render_status_distribution(analytics['status_distribution'])}
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card table-card">
                <div class="card-header">
                    <h5 class="mb-0">Daily Booking Trends</h5>
                </div>
                <div class="card-body">
                    {render_booking_trends(analytics['daily_trends'])}
                </div>
            </div>
        </div>
    </div>
    """

    return HTMLResponse(admin_layout(content, active_tab="analytics"))

async def get_users_stats(db: AsyncSession) -> Dict[str, int]:
    """Get users statistics"""
    # Total users
    total_users = (await db.execute(sa.select(func.count(User.id)))).scalar_one()

    # Users with appointments (active)
    active_users = (await db.execute(
        sa.select(func.count(func.distinct(User.id)))
        .select_from(User)
        .join(Appointment, User.id == Appointment.user_id)
    )).scalar_one()

    # New users this week
    now_local = datetime.now(tz=LOCAL_TZ)
    week_start = now_local - timedelta(days=now_local.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start_utc = week_start.astimezone(UTC)

    new_this_week = (await db.execute(
        sa.select(func.count()).where(User.created_at >= week_start_utc)
    )).scalar_one()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "new_this_week": new_this_week
    }

async def get_recent_users(db: AsyncSession, limit: int = 50) -> List[Any]:
    """Get recent users with appointment counts"""
    query = (
        sa.select(
            User.id,
            User.full_name,
            User.mobile,
            User.created_at,
            func.count(Appointment.id).label('appointment_count')
        )
        .outerjoin(Appointment, User.id == Appointment.user_id)
        .group_by(User.id, User.full_name, User.mobile, User.created_at)
        .order_by(desc(User.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    return result.all()

def render_users_table(users: List[Any]) -> str:
    """Render users table HTML"""
    if not users:
        return '''
        <div class="empty-state">
            <i class="bi bi-people"></i>
            <h5>No users yet</h5>
            <p>Users will appear here once customers start calling and booking appointments.</p>
        </div>
        '''

    rows = []
    for user in users:
        created_date = user.created_at.strftime("%m/%d/%Y")
        last_activity = "Recent" if user.appointment_count > 0 else "No appointments"

        rows.append(f"""
        <tr>
            <td>
                <strong>#{user.id}</strong><br>
                <small class="text-muted">Joined {created_date}</small>
            </td>
            <td>
                <strong>{user.full_name or 'Unknown'}</strong><br>
                <small class="text-muted">Customer</small>
            </td>
            <td>
                <strong>{user.mobile}</strong>
            </td>
            <td>
                <span class="badge bg-info">{user.appointment_count} appointments</span>
            </td>
            <td>
                <small class="text-muted">{last_activity}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewUserDetails({user.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-secondary" onclick="editUser({user.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                </div>
            </td>
        </tr>
        """)

    return f"""
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Appointments</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    """

async def get_analytics_data(db: AsyncSession) -> Dict[str, Any]:
    """Get analytics data"""
    # Appointments this month
    now_local = datetime.now(tz=LOCAL_TZ)
    month_start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_utc = month_start.astimezone(UTC)

    appointments_this_month = (await db.execute(
        sa.select(func.count()).where(Appointment.starts_at >= month_start_utc)
    )).scalar_one()

    # Status distribution
    status_query = (
        sa.select(
            Appointment.status,
            func.count().label('count')
        )
        .group_by(Appointment.status)
    )
    status_result = await db.execute(status_query)
    status_distribution = {row.status or 'booked': row.count for row in status_result}

    # Calculate completion rate
    total_appts = sum(status_distribution.values())
    completed = status_distribution.get('completed', 0)
    completion_rate = round((completed / total_appts * 100) if total_appts > 0 else 0)

    # Daily trends for last 7 days
    daily_trends = []
    for i in range(7):
        day = now_local - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_start_utc = day_start.astimezone(UTC)
        day_end_utc = day_end.astimezone(UTC)

        count = (await db.execute(
            sa.select(func.count()).where(
                Appointment.starts_at >= day_start_utc,
                Appointment.starts_at < day_end_utc
            )
        )).scalar_one()

        daily_trends.append({
            'date': day.strftime('%m/%d'),
            'count': count
        })

    return {
        "appointments_this_month": appointments_this_month,
        "completion_rate": completion_rate,
        "avg_booking_time": "2.5 min",  # Mock data
        "customer_satisfaction": 95,  # Mock data
        "status_distribution": status_distribution,
        "daily_trends": list(reversed(daily_trends))
    }

def render_status_distribution(status_distribution: Dict[str, int]) -> str:
    """Render status distribution chart"""
    if not status_distribution:
        return '<p class="text-muted">No data available</p>'

    total = sum(status_distribution.values())
    items = []

    for status, count in status_distribution.items():
        percentage = round((count / total * 100) if total > 0 else 0)
        status_display = status.title() if status else 'Booked'

        items.append(f"""
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span>{status_display}</span>
            <div class="d-flex align-items-center">
                <div class="progress me-2" style="width: 100px; height: 8px;">
                    <div class="progress-bar" style="width: {percentage}%"></div>
                </div>
                <strong>{count}</strong>
            </div>
        </div>
        """)

    return f"""
    <div class="p-3">
        {"".join(items)}
    </div>
    """

@router.post("/cleanup-so-what")
async def cleanup_so_what_names(
    username: str = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_session)
):
    """Clean up 'So What' customer names in the database"""
    try:
        # Find all users with 'So What' names
        result = await db.execute(
            sa.select(User).where(
                sa.or_(
                    User.full_name.ilike('%so what%'),
                    User.full_name.ilike('%sowhat%'),
                    User.full_name == 'So What'
                )
            )
        )
        so_what_users = result.scalars().all()

        updated_count = 0
        for user in so_what_users:
            # Update to a generic placeholder name
            user.full_name = "Customer (Name Correction Needed)"
            updated_count += 1

        await db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Updated {updated_count} 'So What' entries to placeholder names"
        }

    except Exception as e:
        await db.rollback()
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to cleanup 'So What' names"
        }

def render_booking_trends(daily_trends: List[Dict[str, Any]]) -> str:
    """Render booking trends chart"""
    if not daily_trends:
        return '<p class="text-muted">No data available</p>'

    max_count = max((trend['count'] for trend in daily_trends), default=1)
    items = []

    for trend in daily_trends:
        height = (trend['count'] / max_count * 100) if max_count > 0 else 0

        items.append(f"""
        <div class="text-center" style="flex: 1;">
            <div class="bg-primary mb-1 mx-auto" style="width: 20px; height: {height}%; min-height: 4px; border-radius: 2px;"></div>
            <small class="text-muted">{trend['date']}</small><br>
            <small><strong>{trend['count']}</strong></small>
        </div>
        """)

    return f"""
    <div class="p-3">
        <div class="d-flex align-items-end justify-content-between" style="height: 120px;">
            {"".join(items)}
        </div>
    </div>
    """