"""Видео генерация (fal.ai орқали Kling ва бошқа моделлар) ва клипларни бирлаштириш."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


def _retry(func, what: str, attempts: int = 4, base_delay: float = 3.0):
    """Тармоқ хатоси ёки вақтинчалик 429/5xx да экспоненциал кутиш билан қайта уриниш."""
    for attempt in range(1, attempts + 1):
        try:
            resp = func()
            if getattr(resp, "status_code", 200) in RETRY_STATUSES and attempt < attempts:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # Доимий хато (400, 401, 403 ва ҳ.к.) — қайта урини маслик
            if isinstance(exc, requests.HTTPError) and status is not None and status not in RETRY_STATUSES:
                raise
            if attempt == attempts:
                logger.error("%s: %d уринишдан кейин ҳам муваффақиятсиз: %s", what, attempts, exc)
                raise
            delay = base_delay * 2 ** (attempt - 1)
            logger.warning("%s: уриниш %d/%d хато (%s). %.0f сонидан кейин қайта.", what, attempt, attempts, exc, delay)
            time.sleep(delay)

FAL_QUEUE_URL = "https://queue.fal.run"
DEFAULT_FAL_MODEL = "fal-ai/kling-video/v2.1/standard/text-to-video"


def _kling_duration(duration: int) -> int:
    """Kling фақат 5 ёки 10 секундни қабул қилади."""
    return 10 if int(duration) >= 8 else 5


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
    started = time.time()
    resp = _retry(
        lambda: requests.post(f"{XAI_BASE_URL}/videos/generations", json=payload, headers=headers, timeout=60),
        "Grok сўров юбориш",
    )
    resp.raise_for_status()
    request_id = resp.json()["request_id"]
    logger.info("Grok видео сўрови юборилди: %s (%ss, %s)", request_id, payload["duration"], payload["model"])

    # 2) Тайёр бўлишини кутиш: pending → done | failed
    deadline = time.time() + timeout_s
    while True:
        data = _retry(
            lambda: requests.get(f"{XAI_BASE_URL}/videos/{request_id}", headers=headers, timeout=60),
            "Grok статус",
        ).json()
        state = data.get("status")
        if state == "done":
            logger.info("Grok видео тайёр: %s (%.0f сония)", request_id, time.time() - started)
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
    # Аввал вақтинчалик файлга юкланади: узилган юклаш тайёр кадр сифатида қолмайди
    tmp_path = out_path.with_suffix(".part")
    with requests.get(video_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for part in r.iter_content(chunk_size=1 << 20):
                f.write(part)
    tmp_path.replace(out_path)
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
        return _grok_generate(prompt, out_path, duration, aspect_ratio, timeout_s, poll_every_s)
    if provider != "kling":
        raise ValueError(f"Номаълум VIDEO_PROVIDER: {provider} (grok ёки kling бўлиши керак)")

    model = os.environ.get("FAL_MODEL", DEFAULT_FAL_MODEL)
    payload = {
        "prompt": prompt,
        "duration": str(_kling_duration(duration)),
        "aspect_ratio": aspect_ratio,
        "negative_prompt": "text, subtitles, watermark, logo, blurry, distorted faces",
    }

    # 1) Навбатга қўйиш
    resp = _retry(
        lambda: requests.post(f"{FAL_QUEUE_URL}/{model}", json=payload, headers=_headers(), timeout=60),
        "Kling сўров юбориш",
    )
    resp.raise_for_status()
    job = resp.json()
    status_url = job["status_url"]
    response_url = job["response_url"]

    # 2) Тайёр бўлишини кутиш
    deadline = time.time() + timeout_s
    while True:
        status = _retry(
            lambda: requests.get(status_url, headers=_headers(), timeout=60),
            "Kling статус",
        ).json()
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
    tmp_path = out_path.with_suffix(".part")
    with requests.get(video_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for part in r.iter_content(chunk_size=1 << 20):
                f.write(part)
    tmp_path.replace(out_path)
    return out_path


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    """ffmpeg ёрдамида клипларни битта трейлерга бирлаштиради."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg топилмади. Ўрнатинг: https://ffmpeg.org/download.html")

    list_file = out_path.with_suffix(".txt")
    # ffmpeg concat рўйхатида апострофни '\'' кўринишда экранлаш керак
    lines = []
    for c in clips:
        safe = c.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe}'\n")
    list_file.write_text("".join(lines), encoding="utf-8")

    # Клиплар бир моделдан бўлгани учун одатда тез нусхалаш (-c copy) етарли
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)]
    first = subprocess.run(cmd, capture_output=True)
    if first.returncode != 0:
        # Биринчи уриниш нега йиқилганини логлаймиз, акс ҳолда сабаб йўқолади
        logger.warning("FFmpeg -c copy муваффақиятсиз: %s", first.stderr.decode("utf-8", "ignore")[-500:])
        # Формат фарқ қилса — қайта кодлаш
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_path)]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg қайта кодлаш хатоси: {res.stderr.decode('utf-8', 'ignore')[-1500:]}")
    list_file.unlink(missing_ok=True)
    return out_path


def compress_for_telegram(video: Path, max_mb: int = 49) -> Path:
    """Telegram бот API 50 МБ гача файл қабул қилади — каттасини сиқади."""
    if video.stat().st_size <= max_mb * 1024 * 1024:
        return video
    out = video.with_name(video.stem + "_tg.mp4")
    res = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vf", "scale=-2:720", "-c:v", "libx264",
         "-crf", "28", "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k", str(out)],
        capture_output=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg сиқиш хатоси: {res.stderr.decode('utf-8', 'ignore')[-1500:]}")
    return out


def still_to_clip(image: Path, out_path: Path, duration: float, width: int = 1280, height: int = 720, fps: int = 24) -> Path:
    """Ҳаракатсиз расмдан оҳиста зум (Ken Burns) билан клип ясайди.

    Видео моделидаги ҳаракат хатолари (йўқдан одам, адашган буюм) бўлмайди: кадр қотган, фақат камера яқинлашади.
    """
    frames = max(1, int(round(duration * fps)))
    # Силлиқ зум учун аввал 2 баравар катталаштирамиз, сўнг кесамиз
    vf = (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan=z='min(zoom+0.0008,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-vf", vf,
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"Ken Burns хатоси: {res.stderr.decode('utf-8', 'ignore')[-1500:]}")
    return out_path
