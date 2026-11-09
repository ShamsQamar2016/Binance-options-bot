"""Товуш дизайни (ElevenLabs): жой муҳити (ambience), кадр эффектлари (SFX) ва қисм мусиқаси.

- ambience — ҳар жой учун бир марта, айланма (loop) товуш: шу жойдаги барча кадрлар остида узлуксиз
  чалади, кадрлар алмашганда муҳит «узилмайди».
- SFX — кадрдаги аниқ товушлар (қадам, эшик, от кишнаши).
- мусиқа — ҳар қисм учун алоҳида басталанган инструментал мусиқа (реплика пайтида пасаяди).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dubbing import _post

logger = logging.getLogger(__name__)

SFX_MODEL = "eleven_text_to_sound_v2"


def _save(content: bytes, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.replace(out)
    return out


def sound_effect(prompt: str, seconds: float, out: Path, loop: bool = False) -> Path:
    """Матн тавсифидан товуш эффекти (0.5–30 сония)."""
    payload = {
        "text": prompt[:450],
        "duration_seconds": round(max(0.5, min(30.0, seconds)), 1),
        "prompt_influence": 0.45,
        "model_id": os.environ.get("ELEVENLABS_SFX_MODEL", SFX_MODEL),
    }
    if loop:
        payload["loop"] = True
    r = _post("/sound-generation", payload, params={"output_format": "mp3_44100_128"})
    return _save(r.content, out)


def ambience(prompt: str, out: Path) -> Path:
    """Жой муҳити: 25 сониялик айланма товуш (кадрлар остида керакли узунликкача такрорланади)."""
    return sound_effect(f"{prompt}. Continuous ambient background, no music, no speech, no voices.", 25, out, loop=True)


def music(prompt: str, seconds: float, out: Path) -> Path | None:
    """Қисм учун инструментал мусиқа. Хато бўлса None қайтаради (қисм мусиқасиз йиғилади)."""
    try:
        r = _post("/music", {
            "prompt": prompt[:2000],
            "music_length_ms": int(max(10, min(300, seconds)) * 1000),
            "model_id": os.environ.get("ELEVENLABS_MUSIC_MODEL", "music_v1"),
            "force_instrumental": True,
        }, params={"output_format": "mp3_44100_128"}, timeout=600)
    except RuntimeError as exc:
        logger.warning("Мусиқа яратилмади, қисм мусиқасиз йиғилади: %s", exc)
        print(f"   ⚠️  Мусиқа яратилмади: {str(exc)[:200]}")
        return None
    return _save(r.content, out)
