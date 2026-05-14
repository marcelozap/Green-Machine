"""Jarvis-style voice passphrase gate (HTTP JSON, not audio)."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.nexus.schemas import VoicePassRequest, VoicePassResponse

router = APIRouter(prefix="/auth", tags=["nexus-auth"])


def _phrase_match(user: str, expected: str) -> bool:
    uh = hashlib.sha256(user.encode("utf-8")).digest()
    eh = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(uh, eh)


@router.post("/voice-pass", response_model=VoicePassResponse)
async def voice_pass(body: VoicePassRequest) -> VoicePassResponse:
    secret = settings.xiv_voice_passphrase.strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="XIV voice passphrase not configured (set XIV_VOICE_PASSPHRASE or GM_XIV_VOICE_PASSPHRASE).",
        )
    if not _phrase_match(body.passphrase.strip(), secret):
        raise HTTPException(status_code=401, detail="Voice signature rejected.")
    return VoicePassResponse()
