"""Telegram Bot API: хабар/видео юбориш, каналга жойлаш, ботга юборилган файлни олиш.

TELEGRAM_CHAT_ID    — сизнинг (админ) чатингиз: олдиндан кўриш ва хабарлар учун
TELEGRAM_CHANNEL_ID — сериал чиқадиган канал (@kanal_nomi). Бот канал админи бўлиши керак.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

TG_LIMIT = 4000  # Telegram хабари 4096 белгигача


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ўрнатилмаган")
    return token


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{_token()}/{method}"


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} ўрнатилмаган (.env файлига қўшинг)")
    return value


def admin_chat() -> str:
    return _env("TELEGRAM_CHAT_ID")


def channel() -> str:
    return _env("TELEGRAM_CHANNEL_ID")


def _check(r: requests.Response) -> dict:
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram хатоси: {data.get('description')}")
    return data["result"]


def send_text(text: str, chat_id: str | None = None) -> None:
    chat_id = chat_id or admin_chat()
    for start in range(0, len(text), TG_LIMIT):
        _check(requests.post(_api("sendMessage"), data={"chat_id": chat_id, "text": text[start:start + TG_LIMIT]}, timeout=60))


def send_video(video: Path, caption: str = "", chat_id: str | None = None) -> dict:
    with open(video, "rb") as f:
        return _check(requests.post(
            _api("sendVideo"),
            data={"chat_id": chat_id or admin_chat(), "caption": caption[:1000], "supports_streaming": "true"},
            files={"video": (video.name, f, "video/mp4")},
            timeout=900,
        ))


def send_document(path: Path, caption: str = "", chat_id: str | None = None) -> None:
    with open(path, "rb") as f:
        _check(requests.post(
            _api("sendDocument"),
            data={"chat_id": chat_id or admin_chat(), "caption": caption[:1000]},
            files={"document": (path.name, f)},
            timeout=300,
        ))


def latest_document_from_admin() -> dict | None:
    """Админ чатидан ботга юборилган охирги файл (document)."""
    updates = _check(requests.get(_api("getUpdates"), params={"allowed_updates": '["message"]'}, timeout=60))
    admin = str(admin_chat())
    for update in reversed(updates):
        msg = update.get("message") or {}
        if str(msg.get("chat", {}).get("id")) == admin and msg.get("document"):
            return msg["document"]
    return None


def download_file(file_id: str, dest: Path) -> Path:
    """Бот API орқали 20 МБ гача файлни юклаб олади."""
    info = _check(requests.get(_api("getFile"), params={"file_id": file_id}, timeout=60))
    url = f"https://api.telegram.org/file/bot{_token()}/{info['file_path']}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for part in r.iter_content(1 << 20):
                f.write(part)
    return dest
