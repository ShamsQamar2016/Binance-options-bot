"""Натижани Telegram га юбориш (Bot API)."""

from __future__ import annotations

import os
from pathlib import Path

import requests

TG_LIMIT = 4000  # Telegram хабари 4096 белгигача


def _api(method: str) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ўрнатилмаган")
    return f"https://api.telegram.org/bot{token}/{method}"


def _chat_id() -> str:
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID ўрнатилмаган")
    return chat_id


def send_text(text: str) -> None:
    for start in range(0, len(text), TG_LIMIT):
        r = requests.post(_api("sendMessage"), data={"chat_id": _chat_id(), "text": text[start:start + TG_LIMIT]}, timeout=60)
        r.raise_for_status()


def send_video(video: Path, caption: str = "") -> None:
    with open(video, "rb") as f:
        r = requests.post(
            _api("sendVideo"),
            data={"chat_id": _chat_id(), "caption": caption[:1000], "supports_streaming": "true"},
            files={"video": (video.name, f, "video/mp4")},
            timeout=600,
        )
    r.raise_for_status()


def send_document(path: Path, caption: str = "") -> None:
    with open(path, "rb") as f:
        r = requests.post(
            _api("sendDocument"),
            data={"chat_id": _chat_id(), "caption": caption[:1000]},
            files={"document": (path.name, f)},
            timeout=300,
        )
    r.raise_for_status()
