"""Placeholder integrations — Google Calendar, grocery / rehab tracker."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/integrations", tags=["nexus-integrations"])


@router.get("/google-calendar/status")
async def google_calendar_status() -> dict:
    return {
        "provider": "google_calendar",
        "mode": "placeholder",
        "use_cases": [
            "Tennis match holds + travel buffers",
            "Work / Dataverse sprint milestones as all-day markers",
        ],
        "next_steps": [
            "Create Google Cloud OAuth client (Desktop or Web)",
            "Store GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / refresh token as secrets",
            "Implement calendar.events.list with timeMin/timeMax in a dedicated worker",
        ],
        "suggested_scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
    }


@router.post("/google-calendar/preview-query")
async def google_calendar_preview() -> dict:
    return {"status": "not_implemented", "message": "Wire Google Calendar API here."}


@router.get("/grocery-rehab/status")
async def grocery_rehab_status() -> dict:
    return {
        "provider": "grocery_rehab_tracker",
        "mode": "placeholder",
        "domains": [
            "Grocery lists + macros (future)",
            "Leg rehab sets / pain log (future)",
            "Trail run GPX summaries (future)",
        ],
        "next_steps": [
            "Define grocery_rehab table or reuse unified_nexus.domain=physical_state payloads",
            "Optional mobile capture → POST /nexus/records",
        ],
    }


@router.post("/grocery-rehab/log")
async def grocery_rehab_log_stub() -> dict:
    return {"status": "not_implemented", "message": "POST rehab or grocery entries to /nexus/records when ready."}
