"""Тахминий сарф журнали: fal.ai ва Anthropic чақирувлари. Ёзувлар output/spend.json да.

fal.ai нархлари тахминий (ҳар модел учун аниқ нарх эмас), шунинг учун қолдиқ ҳам тахминий бўлади.
Anthropic сарфи — ҳақиқий токенлар ва модел нархи асосида.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

PATH = Path("output/spend.json")
FAL_ESTIMATE = {"video": 1.2, "lipsync": 0.15, "image": 0.15}   # $ бир чақириққа, тахминий
CLAUDE_PER_MTOK = {"in": 4.0, "out": 20.0}                       # claude-opus-5-5: $ 1 млн токенга


def _load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"entries": [], "balances": {}}


def _save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def add(service: str, usd: float, note: str = "") -> None:
    data = _load()
    data["entries"].append({"t": time.time(), "service": service, "usd": round(usd, 4), "note": note})
    _save(data)


def fal_estimate(endpoint: str) -> tuple[str, float]:
    e = endpoint.lower()
    kind = "lipsync" if "lipsync" in e else ("video" if ("veo" in e or "kling" in e or "video" in e) else "image")
    return kind, FAL_ESTIMATE[kind]


def add_claude(usage) -> None:
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    cost = (tokens_in * CLAUDE_PER_MTOK["in"] + tokens_out * CLAUDE_PER_MTOK["out"]) / 1_000_000
    add("anthropic", cost, f"{tokens_in} кириш, {tokens_out} чиқиш токен")


def set_balance(service: str, usd: float) -> None:
    data = _load()
    data["balances"][service] = {"t": time.time(), "usd": usd}
    _save(data)


def status(service: str) -> dict:
    data = _load()
    bal = data["balances"].get(service)
    since = bal["t"] if bal else 0
    spent_since = sum(e["usd"] for e in data["entries"] if e["service"] == service and e["t"] > since)
    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    today = sum(e["usd"] for e in data["entries"] if e["service"] == service and e["t"] >= midnight)
    total = sum(e["usd"] for e in data["entries"] if e["service"] == service)
    return {
        "set": bal["usd"] if bal else None,
        "spent_since_set": spent_since,
        "remaining": (bal["usd"] - spent_since) if bal else None,
        "today": today,
        "total": total,
    }
