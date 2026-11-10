"""fal.ai орқали моделларни ишлатиш: файл юклаш, навбатга қўйиш, натижани юклаб олиш.

Моделлар тез-тез янгиланади ва уларнинг параметрлари бир-биридан фарқ қилади (мас. Veo'да duration
"8s", Kling'да 10). Шунинг учун ҳар модел учун fal.ai дан унинг OpenAPI схемаси олинади ва сўров
шу схемага мослаштирилади:
  - схемада йўқ майдонлар олиб ташланади;
  - duration, aspect_ratio, resolution каби танловли майдонлар энг яқин рухсат этилган қийматга ўтказилади;
  - расм майдони номи (image_url / start_image_url / first_frame_url ...) моделга қараб танланади.
Схема олинмаса, сўров ўзгаришсиз юборилади.

Пул тежаш: ҳар бир пулли сўров (request_id) журналга ёзилади. Кутиш вақти тугаса, алоқа узилса ёки
дастур тўхтаса, кейинги ишга туширишда янги сўров юборилмайди — ўша сўровнинг натижаси кутилади.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

import requests

from fileutil import read_json_cache, write_json_atomic

logger = logging.getLogger(__name__)

SCHEMA_DIR = Path("output/.fal_schemas")
SCHEMA_MAX_AGE = 3 * 24 * 3600

# Бизнинг майдон номимиз → моделларда учрайдиган номлар
ALIASES = {
    "image_url": ["image_url", "start_image_url", "first_frame_url", "input_image_url", "image", "first_frame_image"],
    "image_urls": ["image_urls", "reference_image_urls", "input_image_urls", "images", "reference_images"],
    "video_url": ["video_url", "video", "input_video_url"],
    "audio_url": ["audio_url", "audio", "input_audio_url"],
    "negative_prompt": ["negative_prompt"],
}


def _client():
    try:
        import fal_client
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("fal-client ўрнатилмаган: pip install -r requirements.txt") from exc
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError("FAL_KEY ўрнатилмаган (.env файлига қўшинг): https://fal.ai/dashboard/keys")
    return fal_client.SyncClient(key=os.environ["FAL_KEY"])


# ----------------------------- Файл юклаш -----------------------------

_UPLOADS = Path("output/.fal_uploads.json")
UPLOAD_MAX_AGE = 24 * 3600
_LOCK = threading.Lock()  # кадрлар параллел ишланганда кеш файлларини ҳимоя қилади


def upload(path: Path) -> str:
    """Маҳаллий файлни fal CDN га юклайди ва URL қайтаради (24 соат кешланади)."""
    path = Path(path)
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    with _LOCK:
        hit = read_json_cache(_UPLOADS, {}).get(digest)
    if hit and time.time() - hit.get("at", 0) < UPLOAD_MAX_AGE:
        return hit["url"]
    url = _with_retry(lambda: _client().upload_file(path), f"юклаш {path.name}")
    with _LOCK:
        cache = read_json_cache(_UPLOADS, {})
        cache[digest] = {"url": url, "at": time.time()}
        write_json_atomic(_UPLOADS, cache)
    return url


def download(url: str, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(out)
    return out


def _with_retry(func, what: str, attempts: int = 4):
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # тармоқ ва вақтинчалик хатолар
            status = getattr(exc, "status_code", None)
            permanent = status is not None and status < 500 and status != 429
            if permanent or attempt == attempts:
                detail = getattr(getattr(exc, "response", None), "text", "") or ""
                raise RuntimeError(f"fal.ai: {what} муваффақиятсиз: {exc} {detail[:1500]}") from exc
            delay = 5 * 2 ** (attempt - 1)
            logger.warning("fal.ai: %s хато (%s), %d сониядан кейин қайта", what, exc, delay)
            time.sleep(delay)


# ----------------------------- Схема -----------------------------

def _schema_path(endpoint: str) -> Path:
    return SCHEMA_DIR / (re.sub(r"[^a-zA-Z0-9]+", "_", endpoint) + ".json")


def _resolve(node: dict, root: dict) -> dict:
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"].lstrip("#/").split("/")
        node = root
        for part in ref:
            node = node.get(part, {})
    if isinstance(node, dict) and "allOf" in node and len(node["allOf"]) == 1:
        merged = {k: v for k, v in node.items() if k != "allOf"}
        merged.update(_resolve(node["allOf"][0], root))
        return merged
    return node


def _input_schema(openapi: dict) -> dict | None:
    for path, ops in (openapi.get("paths") or {}).items():
        post = (ops or {}).get("post") or {}
        body = (((post.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema")
        if body and "/requests/" not in path:
            schema = _resolve(body, openapi)
            props = {k: _resolve(v, openapi) for k, v in (schema.get("properties") or {}).items()}
            return {"properties": props, "required": schema.get("required", [])}
    return None


def input_schema(endpoint: str) -> dict | None:
    """Модел кириш параметрлари схемаси ({properties, required}) ёки None."""
    cached = _schema_path(endpoint)
    with _LOCK:
        data = read_json_cache(cached, None)
        age = time.time() - cached.stat().st_mtime if data is not None else 0
    if data is not None:
        if (data and age < SCHEMA_MAX_AGE) or (not data and age < 3600):  # топилмаганини 1 соатдан кейин қайта сўраймиз
            return data or None
    schema = None
    headers = {"Authorization": f"Key {os.environ['FAL_KEY']}"} if os.environ.get("FAL_KEY") else {}
    attempts = [
        ("https://api.fal.ai/v1/models", {"endpoint_id": endpoint, "expand": "openapi-3.0"}),
        ("https://fal.ai/api/openapi/queue/openapi.json", {"endpoint_id": endpoint}),
    ]
    for url, params in attempts:
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code != 200:
                continue
            data = r.json()
            if "models" in data:
                models = data.get("models") or []
                data = (models[0].get("openapi") if models else None) or {}
            schema = _input_schema(data)
            if schema:
                break
        except (requests.RequestException, ValueError) as exc:
            logger.info("fal.ai схемаси олинмади (%s): %s", url, exc)
    with _LOCK:
        write_json_atomic(cached, schema or {})
    if not schema:
        logger.warning("%s схемаси топилмади — сўров ўзгаришсиз юборилади", endpoint)
    return schema


def _number(value) -> float | None:
    m = re.search(r"\d+(\.\d+)?", str(value))
    return float(m.group()) if m else None


def _enum(prop: dict) -> list | None:
    if "enum" in prop:
        return prop["enum"]
    for key in ("anyOf", "oneOf"):
        for option in prop.get(key, []) or []:
            if "enum" in option:
                return option["enum"]
    return None


def _fit_value(key: str, value, prop: dict):
    choices = _enum(prop)
    if key == "duration":
        want = _number(value) or 5
        if choices:
            nums = sorted(((n, c) for c in choices if (n := _number(c)) is not None), key=lambda x: x[0])
            bigger = [c for n, c in nums if n >= want - 0.01]
            return bigger[0] if bigger else (nums[-1][1] if nums else value)
        typ = prop.get("type")
        lo, hi = prop.get("minimum"), prop.get("maximum")
        if lo is not None:
            want = max(want, lo)
        if hi is not None:
            want = min(want, hi)
        if typ == "integer":
            return int(round(want + 0.49))
        if typ == "number":
            return want
        return str(int(round(want + 0.49)))
    if choices is None or value in choices:
        if isinstance(value, list) and prop.get("maxItems"):
            return value[: prop["maxItems"]]
        return value
    if key == "aspect_ratio":
        return "auto" if "auto" in choices else None
    if key == "resolution":
        order = ["4K", "4k", "2160p", "2K", "2k", "1440p", "1080p", "1K", "1k", "720p", "768p", "540p", "480p"]
        want_idx = order.index(value) if value in order else len(order)
        for cand in order[want_idx:] + order[:want_idx][::-1]:
            if cand in choices:
                return cand
    if isinstance(value, bool) or prop.get("type") == "boolean":
        return value
    return None


def fit(endpoint: str, payload: dict) -> dict:
    """Сўровни модел схемасига мослаштиради."""
    schema = input_schema(endpoint)
    if not schema:
        return {k: v for k, v in payload.items() if v is not None}
    props = schema["properties"]
    out: dict = {}
    for key, value in payload.items():
        if value is None:
            continue
        names = ALIASES.get(key, [key])
        target = next((n for n in names if n in props), None)
        if target is None:
            logger.info("%s: '%s' параметри моделда йўқ — ташлаб юборилди", endpoint, key)
            continue
        fitted = _fit_value(key, value, props[target])
        if fitted is None:
            logger.info("%s: '%s'=%r моделда рухсат этилмаган — ташлаб юборилди", endpoint, key, value)
            continue
        out[target] = fitted
    missing = [r for r in schema.get("required", []) if r not in out]
    if missing:
        logger.warning("%s: мажбурий параметрлар йўқ: %s", endpoint, missing)
    return out


def allowed_durations(endpoint: str) -> list[float] | None:
    """Модел қабул қиладиган видео узунликлари (сония) ёки None (номаълум/исталган)."""
    schema = input_schema(endpoint) or {}
    prop = (schema.get("properties") or {}).get("duration")
    if not prop:
        return None
    choices = _enum(prop)
    if choices:
        return sorted(n for c in choices if (n := _number(c)) is not None)
    return None


# ----------------------------- Ишга тушириш -----------------------------

_JOURNAL = Path("output/.fal_requests.json")
JOURNAL_MAX_AGE = 24 * 3600   # fal.ai натижаларни шунча вақт сақлайди деб ҳисоблаймиз
POLL_EVERY = 5


class _RequestGone(Exception):
    """Журналдаги сўров fal.ai да топилмади (муддати ўтган)."""


def _journal(update=None):
    """Пулли сўровлар журнали: {калит: {endpoint, request_id, at}}. update(journal) — ўзгартириш."""
    with _LOCK:
        data = read_json_cache(_JOURNAL, {})
        if update is not None:
            update(data)
            write_json_atomic(_JOURNAL, data)
        return data


def _start(endpoint: str, payload: dict, timeout_s: int) -> tuple[str, dict]:
    """Сўровни юборади (ёки олдингисини давом эттиради) ва натижани қайтаради. Журнал ёзувини ўчирмайди:
    ўчириш — натижа файлга тўлиқ сақлангандан кейин (run_to_files) ёки доимий хатода."""
    arguments = fit(endpoint, payload)
    key = hashlib.sha1(f"{endpoint}|{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}".encode()).hexdigest()
    client = _client()
    started = time.time()

    entry = _journal().get(key)
    if entry and time.time() - entry.get("at", 0) < JOURNAL_MAX_AGE:
        logger.info("fal.ai: олдинги сўров давом эттирилмоқда %s (%s)", entry["request_id"], endpoint)
        try:
            return key, _wait(client, endpoint, entry["request_id"], key, timeout_s, started)
        except _RequestGone:
            logger.warning("fal.ai: олдинги сўров %s топилмади — янгиси юборилади", entry["request_id"])
            _journal(lambda j: j.pop(key, None))

    logger.info("fal.ai → %s %s", endpoint, json.dumps(_short(arguments), ensure_ascii=False)[:600])
    handle = _submit(client, endpoint, arguments)
    _journal(lambda j: j.__setitem__(key, {"endpoint": endpoint, "request_id": handle.request_id, "at": time.time()}))
    try:
        return key, _wait(client, endpoint, handle.request_id, key, timeout_s, started)
    except _RequestGone:
        _journal(lambda j: j.pop(key, None))
        raise RuntimeError(f"fal.ai: {endpoint} сўрови {handle.request_id} йўқолиб қолди")


def _download_retry(url: str, out: Path, attempts: int = 4) -> Path:
    """Файлни юклайди; тармоқ узилишида қайта уриниб кўради (сўров эмас, фақат юклаш қайта бажарилади)."""
    for attempt in range(1, attempts + 1):
        try:
            return download(url, out)
        except requests.RequestException as exc:
            if attempt == attempts:
                raise
            delay = 5 * 2 ** (attempt - 1)
            logger.warning("fal.ai: файл юклаш хатоси (%s), %d сониядан кейин қайта", exc, delay)
            time.sleep(delay)


def run_to_files(endpoint: str, payload: dict, urls_of, outs: list[Path], timeout_s: int = 1800) -> list[Path]:
    """Моделни ишга туширади ва натижа файлларини сақлайди.

    Пул тежаш: журнал ёзуви фақат ҳамма файл диска тўлиқ ёзилгандан кейин ўчирилади. Юклаш узилса ёки
    жараён тўхтаса, кейинги ишга туширишда янги сўров юборилмайди — ўша натижа қайта юкланади.
    Сўров fal.ai га фақат БИР МАРТА юборилади; кутиш вақтида хато бўлса ҳам қайта юборилмайди.
    urls_of(result) — натижадан URL лар рўйхати; outs — уларга мос файл йўллари.
    """
    key, result = _start(endpoint, payload, timeout_s)
    urls = urls_of(result)
    if not urls:
        raise RuntimeError(f"fal.ai: {endpoint} натижасида файл йўқ: {json.dumps(result)[:500]}")
    paths = [_download_retry(url, out) for url, out in zip(urls, outs)]
    _journal(lambda j: j.pop(key, None))
    return paths


def run(endpoint: str, payload: dict, timeout_s: int = 1800) -> dict:
    """Натижани (JSON) қайтаради. Файл юклаш керак бўлса — run_to_files ишлатинг."""
    key, result = _start(endpoint, payload, timeout_s)
    _journal(lambda j: j.pop(key, None))
    return result


def _submit(client, endpoint: str, arguments: dict):
    """Сўровни юборади. Устидан қайта уринмаймиз: fal-client вақтинчалик тармоқ хатоларини ўзи
    қайта юборади, иккинчи қават эса битта иш учун икки марта пул тўлашга олиб келиши мумкин."""
    try:
        return client.submit(endpoint, arguments=arguments)
    except Exception as exc:
        detail = getattr(getattr(exc, "response", None), "text", "") or ""
        raise RuntimeError(f"fal.ai: {endpoint} сўрови юборилмади: {exc} {detail[:1500]}") from exc


def _wait(client, endpoint: str, request_id: str, key: str, timeout_s: int, started: float) -> dict:
    """Сўров тайёр бўлишини кутади (қайта юбормасдан) ва натижасини қайтаради."""
    import fal_client

    deadline = time.time() + timeout_s
    failures = 0
    while True:
        try:
            status = client.status(endpoint, request_id)
            failures = 0
        except Exception as exc:  # тармоқ узилиши — фақат ҳолатни қайта сўраймиз
            code = getattr(exc, "status_code", None)
            if code in (404, 410):
                raise _RequestGone(request_id) from exc
            failures += 1
            if failures >= 12 or (code is not None and code < 500 and code != 429):
                raise RuntimeError(f"fal.ai: {endpoint} ҳолатини олиб бўлмади (request_id={request_id}): {exc}. "
                                   "Қайта ишга туширсангиз, шу сўровнинг натижаси кутилади.") from exc
            time.sleep(min(60, POLL_EVERY * failures))
            continue
        if isinstance(status, fal_client.Completed):
            if status.error:
                _journal(lambda j: j.pop(key, None))
                raise RuntimeError(f"fal.ai: {endpoint} хатоси ({status.error_type}): {status.error}")
            try:
                result = _with_retry(lambda: client.result(endpoint, request_id), f"{endpoint} натижа")
            except Exception:
                _journal(lambda j: j.pop(key, None))  # доимий хато (мас. параметр нотўғри) — журналда қолмасин
                raise
            # Журнал ёзуви бу ерда ўчирилмайди: файл сақлангандан кейин run_to_files ўчиради
            logger.info("fal.ai ← %s (%.0f сония)", endpoint, time.time() - started)
            return result
        if time.time() > deadline:
            raise TimeoutError(f"fal.ai: {endpoint} {timeout_s} сонияда тайёр бўлмади (request_id={request_id}). "
                               "Қайта ишга туширсангиз, шу сўровнинг натижаси кутилади — қайта пул тўланмайди.")
        time.sleep(POLL_EVERY)


def _short(data: dict) -> dict:
    return {k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v) for k, v in data.items()}


def result_url(result: dict, kind: str) -> str:
    """Натижадан файл URL ни олади. kind: video | image | audio."""
    if kind == "image":
        images = result.get("images") or ([result["image"]] if result.get("image") else [])
        if images:
            return images[0]["url"] if isinstance(images[0], dict) else images[0]
    item = result.get(kind)
    if isinstance(item, dict) and item.get("url"):
        return item["url"]
    if isinstance(item, str):
        return item
    raise RuntimeError(f"fal.ai жавобида {kind} топилмади: {json.dumps(result)[:500]}")


def result_urls(result: dict) -> list[str]:
    images = result.get("images") or ([result["image"]] if result.get("image") else [])
    return [(i["url"] if isinstance(i, dict) else i) for i in images]


def describe(endpoint: str) -> str:
    """Модел параметрлари рўйхати (текшириш учун)."""
    schema = input_schema(endpoint)
    if not schema:
        return f"{endpoint}: схема олинмади"
    lines = [f"{endpoint}:"]
    for name, prop in schema["properties"].items():
        choices = _enum(prop)
        mark = "*" if name in schema.get("required", []) else " "
        extra = f" {choices}" if choices else (f" [{prop.get('minimum')}..{prop.get('maximum')}]"
                                               if "minimum" in prop or "maximum" in prop else "")
        lines.append(f"  {mark} {name}: {prop.get('type', '')}{extra}")
    return "\n".join(lines)
