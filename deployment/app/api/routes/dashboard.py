#!/usr/bin/env python3
"""
Cost Monitoring Dashboard API endpoints.
Serves the cost monitoring dashboard and provides dashboard data APIs.
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from typing import Dict, Any

from app.api.auth import require_api_key
import sys
from pathlib import Path

# Add cost optimization to path
cost_opt_path = Path(__file__).parent.parent.parent.parent / "cost-optimization"
sys.path.insert(0, str(cost_opt_path))

try:
    from monitoring.cost_tracker import AWSCostTracker
except ImportError:
    # Fallback for when cost tracker is not available
    class AWSCostTracker:
        def __init__(self):
            self.aws_available = False

        def get_monthly_costs(self):
            return {"Mock Service": 50.0}

        def get_daily_costs(self):
            return []

        def get_recommendations(self):
            return {"immediate": ["Setup AWS Cost Explorer"]}

        def _get_timestamp(self):
            from datetime import datetime
            return datetime.now().isoformat()

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Path to dashboard files
DASHBOARD_DIR = Path(__file__).parent.parent.parent.parent / "cost-reports"
DASHBOARD_HTML = DASHBOARD_DIR / "dashboard.html"

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(api_key: str = Depends(require_api_key)):
    """Serve the main cost monitoring dashboard"""
    if not DASHBOARD_HTML.exists():
        raise HTTPException(
            status_code=404,
            detail="Dashboard not found. Run setup script to generate dashboard."
        )

    return FileResponse(DASHBOARD_HTML, media_type="text/html")

@router.get("/data/costs")
async def get_cost_data(api_key: str = Depends(require_api_key)) -> Dict[str, Any]:
    """Get current cost data for dashboard"""
    try:
        tracker = AWSCostTracker()

        # Get monthly costs
        monthly_costs = tracker.get_monthly_costs()

        # Get daily costs (last 30 days)
        daily_costs = tracker.get_daily_costs()

        # Get recommendations
        recommendations = tracker.get_recommendations()

        return {
            "timestamp": tracker._get_timestamp(),
            "aws_status": "connected" if tracker.aws_available else "not_available",
            "monthly_costs": {k: float(v) for k, v in monthly_costs.items()},
            "daily_costs": [
                {"date": cost.timestamp.isoformat(), "amount": float(cost.amount)}
                for cost in daily_costs
            ],
            "recommendations": recommendations,
            "summary": {
                "total_monthly_aws": float(sum(monthly_costs.values())),
                "average_daily": float(sum(cost.amount for cost in daily_costs) / len(daily_costs)) if daily_costs else 0,
                "optimization_potential": "30-40%"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cost data: {str(e)}")

@router.get("/data/health")
async def dashboard_health() -> Dict[str, Any]:
    """Dashboard health check (no auth required)"""
    try:
        tracker = AWSCostTracker()
        return {
            "status": "healthy",
            "aws_connected": tracker.aws_available,
            "dashboard_available": DASHBOARD_HTML.exists(),
            "timestamp": tracker._get_timestamp()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "aws_connected": False,
            "dashboard_available": DASHBOARD_HTML.exists()
        }

@router.get("/setup")
async def setup_instructions() -> Dict[str, Any]:
    """Get setup instructions for AWS Cost Explorer"""
    return {
        "title": "AWS Cost Explorer Setup",
        "status": "Setup Required",
        "instructions": {
            "automated": {
                "title": "Automated Setup (Recommended)",
                "command": "./scripts/setup-aws-cost-monitoring.sh",
                "description": "Run this script to automatically configure AWS permissions"
            },
            "manual": {
                "title": "Manual Setup",
                "steps": [
                    "Configure AWS CLI: aws configure",
                    "Apply IAM policy from cost-optimization/aws-cost-policy.json",
                    "Enable Cost Explorer in AWS Console > Billing",
                    "Wait 24 hours for data population"
                ]
            }
        },
        "documentation": "cost-optimization/README.md",
        "policy_file": "cost-optimization/aws-cost-policy.json"
    }

@router.get("/assets/{filename}")
async def dashboard_assets(filename: str):
    """Serve dashboard static assets"""
    asset_path = DASHBOARD_DIR / filename

    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")

    # Determine media type
    if filename.endswith('.json'):
        media_type = "application/json"
    elif filename.endswith('.css'):
        media_type = "text/css"
    elif filename.endswith('.js'):
        media_type = "application/javascript"
    else:
        media_type = "text/plain"

    return FileResponse(asset_path, media_type=media_type)