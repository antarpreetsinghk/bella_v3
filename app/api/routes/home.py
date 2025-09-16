# app/api/routes/home.py
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import os, secrets, hmac, hashlib, base64
from fastapi import APIRouter, Depends, Response, Form, Request, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from sqlalchemy import func

from app.db.session import get_session
from app.db.models.appointment import Appointment
from app.db.models.user import User

# Optional: reuse your validators for phone/name by going through the Pydantic schema + CRUD
from app.schemas.user import UserUpdate
from app.crud.user import update_user

router = APIRouter(tags=["home"])

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")

# ---------------------------
# Basic Auth (protects admin)
# ---------------------------
security = HTTPBasic()
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")

def require_admin(creds: HTTPBasicCredentials = Depends(security)) -> bool:
    ok_user = secrets.compare_digest(creds.username, ADMIN_USER)
    ok_pass = secrets.compare_digest(creds.password, ADMIN_PASS)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# ---------------------------
# Tiny CSRF (HMAC-based)
# ---------------------------
CSRF_SECRET = os.getenv("CSRF_SECRET", "change-me")

def _csrf_make(user: str) -> str:
    mac = hmac.new(CSRF_SECRET.encode(), user.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode()

def _csrf_ok(token: str, user: str) -> bool:
    try:
        expected = _csrf_make(user)
        return secrets.compare_digest(token or "", expected)
    except Exception:
        return False

# ---------------------------
# HTML helpers
# ---------------------------
def _layout(body: str, title: str = "Bella — Dashboard") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
  <style>
    :root {{
      --bg:#0d1117; --panel:#161b22; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --ok:#3fb950;
      --warn:#d29922; --danger:#f85149; --border:#30363d; --red:#f85149; --btn:#1f6feb;
    }}
    * {{ box-sizing:border-box; }}
    body {{ background:var(--bg); color:var(--text); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin:0; }}
    header {{ padding:20px 24px; border-bottom:1px solid var(--border); background:var(--panel); display:flex; gap:12px; align-items:center; }}
    h1 {{ margin:0; font-size:20px; }}
    a, a:visited {{ color:var(--accent); text-decoration:none; }}
    main {{ padding:24px; }}
    .grid {{ display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom:24px; }}
    .card {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; }}
    .kpi-label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
    .kpi-value {{ font-size:28px; font-weight:700; margin-top:6px; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--border); border-radius:12px; background:var(--panel); }}
    table {{ width:100%; border-collapse:collapse; min-width:980px; }}
    th, td {{ padding:12px 14px; border-bottom:1px solid var(--border); text-align:left; font-size:14px; }}
    th {{ background:rgba(255,255,255,0.03); position:sticky; top:0; }}
    .muted {{ color:var(--muted); }}
    .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; background:#1f6feb22; border:1px solid #1f6feb55; }}
    .empty {{ padding:22px; color:var(--muted); }}
    .btn {{ display:inline-block; padding:6px 10px; border-radius:8px; border:1px solid var(--border); background:#1f6feb22; color:var(--text); cursor:pointer; font-size:13px; }}
    .btn:hover {{ filter:brightness(1.1); }}
    .btn-red {{ background:#f8514922; border-color:#f8514955; }}
    .btn-row {{ display:flex; gap:8px; }}
    .form {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; max-width:720px; }}
    .row {{ display:grid; grid-template-columns: 180px 1fr; gap:12px; margin:10px 0; align-items:center; }}
    input[type="text"], input[type="tel"], input[type="datetime-local"], select, textarea {{
      width:100%; padding:10px 12px; border-radius:8px; border:1px solid var(--border); background:#0f141b; color:var(--text);
    }}
    textarea {{ min-height:90px; }}
    .actions {{ display:flex; gap:10px; margin-top:12px; }}
    .back {{ margin-top:16px; display:inline-block; }}
  </style>
  <script>
    function confirmDelete(formId) {{
      const ok = confirm("Delete this appointment? This cannot be undone.");
      if (ok) document.getElementById(formId).submit();
    }}
  </script>
</head>
<body>
  <header><h1>📅 Bella</h1><a href="/">Dashboard</a></header>
  <main>
    {body}
  </main>
</body>
</html>"""

def _to_local_iso(dt_utc: datetime) -> str:
    """Return value suitable for <input type='datetime-local'> (no TZ, local wall time)."""
    local = dt_utc.astimezone(LOCAL_TZ)
    return local.strftime("%Y-%m-%dT%H:%M")

def _parse_local_to_utc(s: str) -> datetime:
    """
    Accepts ISO 'YYYY-MM-DDTHH:MM' or full ISO; interprets naive as LOCAL_TZ; returns UTC.
    Raises ValueError on invalid input.
    """
    s = (s or "").strip()
    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        if len(s) == 16:  # try append seconds
            dt = datetime.fromisoformat(s + ":00")
    if dt is None:
        raise ValueError("Invalid datetime format")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(UTC)

# ---------------------------
# Routes (protected by Basic Auth)
# ---------------------------
@router.get("/", include_in_schema=False)
async def dashboard(_: bool = Depends(require_admin), db: AsyncSession = Depends(get_session)) -> Response:
    # KPIs
    total_users = (await db.execute(sa.select(func.count(User.id)))).scalar_one()
    total_appts = (await db.execute(sa.select(func.count(Appointment.id)))).scalar_one()

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

    # ALL appointments (past + future), joined with users, ordered newest first
    all_q = (
        sa.select(
            Appointment.id,
            Appointment.starts_at,
            Appointment.duration_min,
            Appointment.status,
            Appointment.notes,
            User.full_name,
            User.mobile,
            User.id.label("user_id"),
        )
        .join(User, User.id == Appointment.user_id)
        .order_by(Appointment.starts_at.desc())
    )
    rows = (await db.execute(all_q)).all()

    token = _csrf_make(ADMIN_USER)

    if not rows:
        table_html = '<div class="empty">No appointments yet. Book one via the phone flow or API.</div>'
    else:
        tr_html = []
        for r in rows:
            local = r.starts_at.astimezone(LOCAL_TZ)
            when = local.strftime("%a, %b %d %Y — %I:%M %p")
            status = (r.status or "booked").lower()
            # Edit/Delete controls (with CSRF token)
            del_form_id = f"del-{r.id}"
            controls = (
                f"<div class='btn-row'>"
                f"<a class='btn' href='/manage/appointments/{r.id}/edit'>Edit</a>"
                f"<form id='{del_form_id}' action='/manage/appointments/{r.id}/delete' method='post' style='display:inline;'>"
                f"<input type='hidden' name='csrf_token' value='{token}'/>"
                f"</form>"
                f"<button class='btn btn-red' onclick=\"confirmDelete('{del_form_id}')\">Delete</button>"
                f"</div>"
            )
            tr_html.append(
                f"<tr>"
                f"<td>{r.id}</td>"
                f"<td>{when}</td>"
                f"<td>{r.duration_min} min</td>"
                f"<td><span class='pill'>{status}</span></td>"
                f"<td>{r.full_name}</td>"
                f"<td class='muted'>{r.mobile}</td>"
                f"<td class='muted'>#{r.user_id}</td>"
                f"<td>{controls}</td>"
                f"</tr>"
            )
        table_html = (
            '<div class="table-wrap">'
            "<table>"
            "<thead><tr>"
            "<th>ID</th><th>When (Local)</th><th>Duration</th><th>Status</th>"
            "<th>Name</th><th>Phone</th><th>User ID</th><th>Actions</th>"
            "</tr></thead>"
            "<tbody>"
            + "".join(tr_html)
            + "</tbody></table></div>"
        )

    body = f"""
<div class="grid">
  <div class="card"><div class="kpi-label">Total Users</div><div class="kpi-value">{total_users}</div></div>
  <div class="card"><div class="kpi-label">Total Appointments</div><div class="kpi-value">{total_appts}</div></div>
  <div class="card"><div class="kpi-label">Today</div><div class="kpi-value">{today_appts}</div></div>
</div>

{table_html}

<footer class="muted">Local time zone: America/Edmonton. Showing all appointments (newest first).</footer>
"""
    return Response(content=_layout(body), media_type="text/html")

@router.get("/manage/appointments/{appt_id}/edit", include_in_schema=False)
async def edit_appointment_page(appt_id: int, _: bool = Depends(require_admin), db: AsyncSession = Depends(get_session)) -> Response:
    row = (await db.execute(
        sa.select(Appointment, User)
        .join(User, User.id == Appointment.user_id)
        .where(Appointment.id == appt_id)
    )).one_or_none()

    if not row:
        return Response(content=_layout("<p class='empty'>Appointment not found.</p>", "Not Found"), media_type="text/html")

    appt: Appointment = row[0]
    user: User = row[1]

    when_local_iso = _to_local_iso(appt.starts_at)
    notes_val = appt.notes or ""
    status_val = appt.status or "booked"
    token = _csrf_make(ADMIN_USER)

    form_html = f"""
<h2>Edit Appointment #{appt.id}</h2>
<form class="form" action="/manage/appointments/{appt.id}/edit" method="post">
  <input type="hidden" name="csrf_token" value="{token}" />
  <div class="row">
    <label>Full Name</label>
    <input type="text" name="full_name" value="{user.full_name}" required />
  </div>
  <div class="row">
    <label>Phone</label>
    <input type="tel" name="mobile" value="{user.mobile}" required />
  </div>
  <div class="row">
    <label>When (Local)</label>
    <input type="datetime-local" name="starts_at_local" value="{when_local_iso}" required />
  </div>
  <div class="row">
    <label>Duration (minutes)</label>
    <input type="text" name="duration_min" value="{appt.duration_min}" required />
  </div>
  <div class="row">
    <label>Status</label>
    <select name="status">
      <option value="booked" {"selected" if status_val=="booked" else ""}>booked</option>
      <option value="completed" {"selected" if status_val=="completed" else ""}>completed</option>
      <option value="cancelled" {"selected" if status_val=="cancelled" else ""}>cancelled</option>
    </select>
  </div>
  <div class="row">
    <label>Notes</label>
    <textarea name="notes">{notes_val}</textarea>
  </div>
  <div class="actions">
    <button class="btn" type="submit">Save</button>
    <a class="btn" href="/">Cancel</a>
  </div>
</form>
<a class="back" href="/">← Back to dashboard</a>
"""
    return Response(content=_layout(form_html, f"Edit #{appt.id}"), media_type="text/html")

@router.post("/manage/appointments/{appt_id}/edit", include_in_schema=False)
async def edit_appointment_save(
    appt_id: int,
    _: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
    request: Request = None,
    csrf_token: str = Form(...),
    full_name: str = Form(...),
    mobile: str = Form(...),
    starts_at_local: str = Form(...),
    duration_min: str = Form(...),
    status: str = Form(...),
    notes: Optional[str] = Form(None),
) -> Response:
    if not _csrf_ok(csrf_token, ADMIN_USER):
        return Response(
            status_code=400,
            content=_layout("<p class='empty'>Invalid CSRF token.</p>", "Bad Request"),
            media_type="text/html",
        )

    row = (await db.execute(
        sa.select(Appointment, User)
        .join(User, User.id == Appointment.user_id)
        .where(Appointment.id == appt_id)
    )).one_or_none()
    if not row:
        return Response(status_code=404, content=_layout("<p class='empty'>Appointment not found.</p>", "Not Found"), media_type="text/html")

    appt: Appointment = row[0]
    user: User = row[1]

    # Update User via existing validators (normalizes phone, trims name)
    try:
        upd = UserUpdate(full_name=full_name, mobile=mobile)
        await update_user(db, user.id, upd)  # commits inside
    except Exception as e:
        msg = f"<p class='empty'>User update failed: {e}</p><p><a href='/manage/appointments/{appt_id}/edit'>← Back</a></p>"
        return Response(content=_layout(msg, "Validation Error"), media_type="text/html", status_code=400)

    # Update Appointment fields
    try:
        appt.starts_at = _parse_local_to_utc(starts_at_local)
    except Exception:
        msg = "<p class='empty'>Invalid date/time. Use the date-time picker.</p><p><a href='/manage/appointments/{0}/edit'>← Back</a></p>".format(appt_id)
        return Response(content=_layout(msg, "Validation Error"), media_type="text/html", status_code=400)

    try:
        appt.duration_min = int(duration_min)
    except Exception:
        msg = "<p class='empty'>Duration must be an integer.</p><p><a href='/manage/appointments/{0}/edit'>← Back</a></p>".format(appt_id)
        return Response(content=_layout(msg, "Validation Error"), media_type="text/html", status_code=400)

    appt.status = status or appt.status
    appt.notes = notes

    await db.commit()

    # Redirect back to dashboard
    return Response(status_code=303, headers={"Location": "/"})

@router.post("/manage/appointments/{appt_id}/delete", include_in_schema=False)
async def delete_appointment(
    appt_id: int,
    _: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
    csrf_token: str = Form(...),
) -> Response:
    if not _csrf_ok(csrf_token, ADMIN_USER):
        return Response(
            status_code=400,
            content=_layout("<p class='empty'>Invalid CSRF token.</p>", "Bad Request"),
            media_type="text/html",
        )

    appt = await db.get(Appointment, appt_id)
    if not appt:
        return Response(status_code=404, content=_layout("<p class='empty'>Appointment not found.</p>", "Not Found"), media_type="text/html")

    await db.delete(appt)
    await db.commit()
    # Redirect to dashboard
    return Response(status_code=303, headers={"Location": "/"})
