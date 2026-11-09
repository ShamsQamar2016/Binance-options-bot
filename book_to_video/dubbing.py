"""Ўзбекча дубляж (TTS): ҳар персонажга алоҳида овоз.

Провайдерлар (.env даги TTS_PROVIDER):
  azure       — Microsoft Azure: ўзбекча овозлар uz-UZ-SardorNeural (эркак) ва uz-UZ-MadinaNeural (аёл).
                Персонажлар баланд-пастлиги (pitch) ва тезлиги (rate) билан фарқланади.
  elevenlabs  — ElevenLabs: жуда кўп ва эмоционал овозлар. Ҳар персонажга voices.json да voice_id беринг.
                Ўзбекча талаффузни аввал синаб кўринг.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

import requests

# ----------------------------- Кирилл → лотин -----------------------------

_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'",
    "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}
_VOWELS = set("аеёиоуэюяўАЕЁИОУЭЮЯЎ")


def cyr_to_lat(text: str) -> str:
    """Ўзбек кирилл ёзувини лотинга ўгиради (TTS лотин ёзувини яхшироқ ўқийди)."""
    out = []
    for i, ch in enumerate(text):
        low = ch.lower()
        prev = text[i - 1] if i else " "
        if low == "е":
            lat = "ye" if (not prev.isalpha() or prev in _VOWELS or prev in "ъьЪЬ") else "e"
        elif low in _MAP:
            lat = _MAP[low]
        else:
            out.append(ch)
            continue
        if ch != low and lat:  # бош ҳарф
            nxt = text[i + 1] if i + 1 < len(text) else ""
            lat = lat.upper() if (nxt.isupper() and len(lat) > 1) else lat[0].upper() + lat[1:]
        out.append(lat)
    return "".join(out)


# ----------------------------- Овозларни тайинлаш -----------------------------

_AZURE_VOICES = {"male": "uz-UZ-SardorNeural", "female": "uz-UZ-MadinaNeural"}
_AZURE_RU = {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"}


def _is_ru() -> bool:
    """DUB_LANGUAGE=ru (стандарт): диалог русча. uz бўлса — ўзбекча (кирилл → лотин)."""
    return os.environ.get("DUB_LANGUAGE", "ru").lower() == "ru"
_AGE_PROSODY = {  # Azure да икки овоздан турли персонажлар ясаш
    "child": {"pitch": "+18%", "rate": "+8%"},
    "young": {"pitch": "+5%", "rate": "+3%"},
    "adult": {"pitch": "0%", "rate": "0%"},
    "elderly": {"pitch": "-12%", "rate": "-12%"},
}


def build_voice_map(plan, path: Path) -> dict:
    """Персонажлар учун voices.json тузади (мавжуд бўлса — ўзгаришларингизни сақлайди)."""
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    voices: dict = {}
    entries = [("narrator", "Диктор", plan.narrator_voice)] + [(c.id, c.name, c.voice) for c in plan.characters]

    # Бир хил жинс ва ёшдаги персонажлар бир-биридан фарқлансин
    seen: dict[tuple, int] = {}
    for cid, name, v in entries:
        gender = "female" if v.gender.lower().startswith("f") else "male"
        age = v.age_group if v.age_group in _AGE_PROSODY else "adult"
        n = seen.get((gender, age), 0)
        seen[(gender, age)] = n + 1
        prosody = dict(_AGE_PROSODY[age])
        if n:  # кейингиларини бироз силжитамиз
            shift = (-6 if n % 2 else 6) * ((n + 1) // 2)
            prosody["pitch"] = f"{int(prosody['pitch'].rstrip('%')) + shift:+d}%"
        voices[cid] = {
            "name": name,
            "gender": gender,
            "age_group": age,
            "tone": v.tone,
            "azure_voice": _AZURE_VOICES[gender],
            "azure_pitch": prosody["pitch"],
            "azure_rate": prosody["rate"],
            "elevenlabs_voice_id": os.environ.get(
                "ELEVENLABS_NARRATOR_VOICE" if cid == "narrator" else
                ("ELEVENLABS_FEMALE_VOICE" if gender == "female" else "ELEVENLABS_MALE_VOICE"), ""),
        }
        voices[cid].update(existing.get(cid, {}))  # қўлда киритилганлар устун
    path.write_text(json.dumps(voices, ensure_ascii=False, indent=2), encoding="utf-8")
    return voices


# ----------------------------- TTS провайдерлари -----------------------------

_AZURE_STYLE = {  # Azure ўзбек овозлари style ни қўллаб-қувватламаслиги мумкин — тезлик/баландлик орқали
    "sad": (-4, -8), "tired": (-6, -12), "whisper": (-2, -10), "tender": (0, -6), "crying": (-6, -10),
    "angry": (4, 8), "excited": (6, 10), "joyful": (5, 6), "fearful": (6, 6), "calm": (0, -3),
}


def _azure(text: str, voice: dict, emotion: str, out: Path) -> None:
    key, region = os.environ.get("AZURE_SPEECH_KEY"), os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise RuntimeError("AZURE_SPEECH_KEY ва AZURE_SPEECH_REGION ўрнатилмаган")
    dp, dr = _AZURE_STYLE.get(emotion, (0, 0))
    pitch = int(voice["azure_pitch"].rstrip("%")) + dp
    rate = int(voice["azure_rate"].rstrip("%")) + dr
    volume = ' volume="-30%"' if emotion == "whisper" else ""
    if _is_ru():
        lang_code, voice_name, spoken = "ru-RU", _AZURE_RU[voice.get("gender", "male")], text
    else:
        lang_code, voice_name, spoken = "uz-UZ", voice["azure_voice"], cyr_to_lat(text)
    ssml = (
        f'<speak version="1.0" xml:lang="{lang_code}"><voice name="{voice_name}">'
        f'<prosody pitch="{pitch:+d}%" rate="{rate:+d}%"{volume}>{escape(spoken)}</prosody>'
        f"</voice></speak>"
    )
    r = requests.post(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
            "User-Agent": "book-to-serial",
        },
        data=ssml.encode("utf-8"),
        timeout=120,
    )
    r.raise_for_status()
    out.write_bytes(r.content)


def _elevenlabs(text: str, voice: dict, emotion: str, out: Path) -> None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY ўрнатилмаган")
    voice_id = voice.get("elevenlabs_voice_id")
    if not voice_id:
        raise RuntimeError(f"voices.json да «{voice['name']}» учун elevenlabs_voice_id кўрсатилмаган")
    model = os.environ.get("ELEVENLABS_MODEL", "eleven_v3")
    spoken = text if _is_ru() else cyr_to_lat(text)
    if "v3" in model and emotion not in ("", "calm"):
        spoken = f"[{emotion}] {spoken}"  # v3 моделида эмоция теглари
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": spoken, "model_id": model,
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35}},
        timeout=180,
    )
    r.raise_for_status()
    out.write_bytes(r.content)


def synthesize(text: str, voice: dict, emotion: str, out: Path) -> Path:
    provider = os.environ.get("TTS_PROVIDER", "azure").lower()
    out.parent.mkdir(parents=True, exist_ok=True)
    {"azure": _azure, "elevenlabs": _elevenlabs}[provider](text, voice, emotion, out)
    return out


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())
