"""Видео генерация (fal.ai орқали Kling ва бошқа моделлар) ва клипларни бирлаштириш."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

FAL_QUEUE_URL = "https://queue.fal.run"
DEFAULT_FAL_MODEL = "fal-ai/kling-video/v2.1/standard/text-to-video"


def _headers() -> dict[str, str]:
    key = os.environ.get("FAL_KEY")
    if not key:
        raise RuntimeError("FAL_KEY ўрнатилмаган (.env файлига қўшинг)")
    return {"Authorization": f"Key {key}", "Content-Type": "application/json"}


XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_GROK_MODEL = "grok-imagine-video-1.5-lite"


def _grok_generate(
    prompt: str,
    out_path: Path,
    duration: int,
    aspect_ratio: str,
    timeout_s: int = 1200,
    poll_every_s: int = 5,
) -> Path:
    """xAI Grok Imagine видео. Ҳужжат: docs.x.ai/developers/model-capabilities/video/generation"""
    key = os.environ.get("XAI_API_KEY")
    if not key:
        raise RuntimeError("XAI_API_KEY ўрнатилмаган (.env файлига қўшинг)")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    payload = {
        "model": os.environ.get("GROK_MODEL", DEFAULT_GROK_MODEL),
        "prompt": prompt,
        "duration": max(1, min(15, int(duration))),
        "aspect_ratio": aspect_ratio,
        "resolution": os.environ.get("GROK_RESOLUTION", "720p"),
        # Ўз овозини яратмасин: ўзбекча дубляж фақат бизнинг TTS овози бўлсин
        "generate_audio": False,
    }

    # 1) Сўровни юбориш → request_id
    resp = requests.post(f"{XAI_BASE_URL}/videos/generations", json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    request_id = resp.json()["request_id"]

    # 2) Тайёр бўлишини кутиш: pending → done | failed
    deadline = time.time() + timeout_s
    while True:
        data = requests.get(f"{XAI_BASE_URL}/videos/{request_id}", headers=headers, timeout=60).json()
        state = data.get("status")
        if state == "done":
            break
        if state == "failed":
            raise RuntimeError(f"Grok видео хатоси: {data.get('error')}")
        if time.time() > deadline:
            raise TimeoutError(f"Grok видео {timeout_s} сонияда тайёр бўлмади: {request_id}")
        time.sleep(poll_every_s)

    # 3) Видео ҳаволасини юклаб олиш (ҳавола вақтинчалик, дарров сақлаймиз)
    video_url = (data.get("video") or {}).get("url")
    if not video_url:
        raise RuntimeError(f"Жавобда видео ҳаволаси йўқ: {data}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(video_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for part in r.iter_content(chunk_size=1 << 20):
                f.write(part)
    return out_path


def generate_clip(
    prompt: str,
    out_path: Path,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    timeout_s: int = 1200,
    poll_every_s: int = 10,
) -> Path:
    """Битта клипни генерация қилади ва .mp4 сифатида сақлайди.

    VIDEO_PROVIDER=grok (стандарт) ёки kling. Grok учун XAI_API_KEY, Kling учун FAL_KEY керак.
    """
    provider = os.environ.get("VIDEO_PROVIDER", "grok").lower()
    if provider == "grok":
        return _grok_generate(prompt, out_path, duration, aspect_ratio, timeout_s)

    model = os.environ.get("FAL_MODEL", DEFAULT_FAL_MODEL)
    payload = {
        "prompt": prompt,
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
        "negative_prompt": "text, subtitles, watermark, logo, blurry, distorted faces",
    }

    # 1) Навбатга қўйиш
    resp = requests.post(f"{FAL_QUEUE_URL}/{model}", json=payload, headers=_headers(), timeout=60)
    resp.raise_for_status()
    job = resp.json()
    status_url = job["status_url"]
    response_url = job["response_url"]

    # 2) Тайёр бўлишини кутиш
    deadline = time.time() + timeout_s
    while True:
        status = requests.get(status_url, headers=_headers(), timeout=60).json()
        state = status.get("status")
        if state == "COMPLETED":
            break
        if state in ("FAILED", "ERROR", "CANCELLED"):
            raise RuntimeError(f"Видео генерация хатоси: {status}")
        if time.time() > deadline:
            raise TimeoutError(f"Видео {timeout_s} сонияда тайёр бўлмади: {status_url}")
        time.sleep(poll_every_s)

    # 3) Натижани олиш ва юклаб олиш
    result = requests.get(response_url, headers=_headers(), timeout=60).json()
    video_url = (result.get("video") or {}).get("url")
    if not video_url:
        raise RuntimeError(f"Жавобда видео ҳаволаси йўқ: {result}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(video_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for part in r.iter_content(chunk_size=1 << 20):
                f.write(part)
    return out_path


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    """ffmpeg ёрдамида клипларни битта трейлерга бирлаштиради."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg топилмади. Ўрнатинг: https://ffmpeg.org/download.html")

    list_file = out_path.with_suffix(".txt")
    list_file.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")

    # Клиплар бир моделдан бўлгани учун одатда тез нусхалаш (-c copy) етарли
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        # Формат фарқ қилса — қайта кодлаш
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True)
    list_file.unlink(missing_ok=True)
    return out_path


def compress_for_telegram(video: Path, max_mb: int = 49) -> Path:
    """Telegram бот API 50 МБ гача файл қабул қилади — каттасини сиқади."""
    if video.stat().st_size <= max_mb * 1024 * 1024:
        return video
    out = video.with_name(video.stem + "_tg.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vf", "scale=-2:720", "-c:v", "libx264",
         "-crf", "28", "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k", str(out)],
        check=True, capture_output=True,
    )
    return out
