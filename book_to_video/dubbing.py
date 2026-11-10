"""Русча дубляж (ElevenLabs): ҳар персонажга алоҳида, махсус яратилган овоз.

Овозлар (voices.json):
  - Сериал режаси тузилгач, ҳар персонаж учун Voice Design (eleven_ttv_v3) тавсифидан янги овоз ясалади
    ва ElevenLabs ҳисобингизга сақланади. voice_id лар voices.json да туради.
  - Овоз ёқмаса: voices.json да шу персонажнинг voice_id сини ўчириб, `python serial.py voices` ни
    қайта ишга туширинг ёки ElevenLabs кутубхонасидан ўзингиз танлаган voice_id ни ёзинг.

Нутқ: eleven_v3 модели, рус тили, ҳиссиёт теглари ([whispers], [sighs], [angry] ...).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import time
from pathlib import Path

import requests

from fileutil import PROBE_TIMEOUT, write_text_atomic

logger = logging.getLogger(__name__)

API = "https://api.elevenlabs.io/v1"
RETRY_STATUSES = {429, 500, 502, 503, 504}

SAMPLE_TEXT = {
    "male": ("Знаешь, я долго молчал. Но сегодня скажу всё, как есть. Ты можешь мне не верить, "
             "но я видел это своими глазами — и с тех пор не могу спать по ночам."),
    "female": ("Послушай меня внимательно. Я не прошу многого — только правду. Если ты уйдёшь сейчас, "
               "я пойму. Но если останешься, обещай, что больше никогда мне не солжёшь."),
}
NARRATOR_SAMPLE = ("В тот год зима пришла раньше обычного. Никто в городе ещё не знал, что эта ночь "
                   "изменит всё — и для тех, кто ждал перемен, и для тех, кто их боялся.")


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY ўрнатилмаган (.env файлига қўшинг)")
    return key


def _post(path: str, payload: dict, params: dict | None = None, timeout: int = 300) -> requests.Response:
    """ElevenLabs'га POST: вақтинчалик хатоларда (429/5xx, тармоқ) экспоненциал кутиб қайта уринади."""
    for attempt in range(1, 6):
        try:
            r = requests.post(f"{API}{path}", params=params, json=payload,
                              headers={"xi-api-key": _key()}, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == 5:
                raise
            logger.warning("ElevenLabs %s: тармоқ хатоси (%s), қайта уриниш %d", path, exc, attempt)
        else:
            if r.status_code not in RETRY_STATUSES or attempt == 5:
                if r.status_code >= 400:
                    raise RuntimeError(f"ElevenLabs {path} хатоси {r.status_code}: {r.text[:800]}")
                return r
            logger.warning("ElevenLabs %s: HTTP %s, қайта уриниш %d", path, r.status_code, attempt)
        time.sleep(3 * 2 ** (attempt - 1))
    raise RuntimeError("unreachable")


# ----------------------------- Овозларни яратиш -----------------------------

def design_voice(name: str, description: str, gender: str, preview_path: Path | None = None,
                 sample: str | None = None) -> str:
    """Тавсифдан янги овоз ясайди ва ElevenLabs ҳисобига сақлайди. voice_id ни қайтаради."""
    text = sample or SAMPLE_TEXT.get(gender, SAMPLE_TEXT["male"])
    data = _post("/text-to-voice/design", {
        "voice_description": description[:1000],
        "model_id": os.environ.get("ELEVENLABS_VOICE_DESIGN_MODEL", "eleven_ttv_v3"),
        "text": text,
    }).json()
    previews = data.get("previews") or []
    if not previews:
        raise RuntimeError(f"Voice Design вариант қайтармади: {str(data)[:300]}")
    best = previews[0]
    if preview_path is not None and best.get("audio_base_64"):
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_bytes(base64.b64decode(best["audio_base_64"]))
    created = _post("/text-to-voice", {
        "voice_name": name[:100],
        "voice_description": description[:1000],
        "generated_voice_id": best["generated_voice_id"],
    }).json()
    return created["voice_id"]


def build_voice_map(plan, path: Path, create: bool = False, previews_dir: Path | None = None) -> dict:
    """voices.json ни тузади/янгилайди. create=True бўлса, voice_id йўқ персонажларга овоз яратади.

    Қўлда ёзилган voice_id ва созламалар сақланади.
    """
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    voices: dict = {}
    entries = [("narrator", "Рассказчик", plan.narrator_voice)] + [(c.id, c.name, c.voice) for c in plan.characters]
    for cid, name, spec in entries:
        entry = {"name": name, "gender": spec.gender, "age": spec.age,
                 "description": spec.description, "voice_id": ""}
        entry.update(existing.get(cid, {}))
        if create and not entry.get("voice_id"):
            print(f"🎙  Овоз яратилмоқда: {name}")
            sample = NARRATOR_SAMPLE if cid == "narrator" else None
            preview = previews_dir / f"{cid}.mp3" if previews_dir else None
            entry["voice_id"] = design_voice(f"{plan.series_title[:40]} — {name}", spec.description,
                                             spec.gender, preview, sample)
        voices[cid] = entry
        # Ҳар овоз яратилгач сақланади: жараён узилса, яратилган овозлар йўқолмайди
        write_text_atomic(path, json.dumps(voices | {k: v for k, v in existing.items() if k not in voices},
                                           ensure_ascii=False, indent=2))
    return voices


# ----------------------------- Нутқ -----------------------------

def _tagged_text(text: str, delivery: str) -> str:
    tags = [t.strip().strip("[]") for t in (delivery or "").split(",") if t.strip()]
    tags = [t for t in tags if t.lower() not in ("neutral", "calm", "normal")][:2]
    return "".join(f"[{t}] " for t in tags) + text


def synthesize(text: str, voice: dict, delivery: str, out: Path) -> Path:
    """Битта репликани русча овозлаштиради (mp3)."""
    voice_id = voice.get("voice_id")
    if not voice_id:
        raise RuntimeError(f"voices.json да «{voice.get('name')}» учун voice_id йўқ: python serial.py voices")
    model = os.environ.get("ELEVENLABS_MODEL", "eleven_v3")
    payload = {
        "text": _tagged_text(text, delivery) if "v3" in model else text,
        "model_id": model,
        "voice_settings": {"stability": float(voice.get("stability", 0.5)),
                           "similarity_boost": float(voice.get("similarity_boost", 0.75))},
    }
    lang = os.environ.get("ELEVENLABS_LANGUAGE_CODE", "ru")
    params = {"output_format": os.environ.get("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")}
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = _post(f"/text-to-speech/{voice_id}", payload | ({"language_code": lang} if lang else {}), params)
    except RuntimeError as exc:
        msg = str(exc)
        if lang and (" 400" in msg or "language" in msg.lower()):
            # Баъзи моделлар language_code ни қабул қилмайди — усиз қайта уринамиз
            r = _post(f"/text-to-speech/{voice_id}", payload, params)
        else:
            raise
    tmp = out.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(out)
    return out


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True, timeout=PROBE_TIMEOUT,
    )
    return float(result.stdout.strip())
