"""
Optional TTS via ElevenLabs for accessibility (e.g. listen to agent output).
"""
from __future__ import annotations

from utils import getenv, get_logger

logger = get_logger(__name__)


def speak_text(text: str, max_chars: int = 500) -> bytes | None:
    """Convert text to speech using ElevenLabs. Returns audio bytes or None on failure."""
    if not text or not getenv("ELEVENLABS_API_KEY"):
        return None
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=getenv("ELEVENLABS_API_KEY"))
        audio = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            text=text[:max_chars],
            model_id="eleven_multilingual_v2",
        )
        return b"".join(audio)
    except Exception as e:
        logger.warning("ElevenLabs TTS failed: %s", e)
        return None
