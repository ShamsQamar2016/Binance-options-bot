"""Текшириш: fal.ai ва Anthropic қолдиғини API орқали ўқиш мумкинми?

Ишлатиш (лойиҳа папкасида, CMD'да):
    python check_balance.py

Калитлар .env дан олинади ва ҳеч қаерга чиқарилмайди. Натижада фақат HTTP код ва жавоб
бошланиши кўрсатилади (калит ёки шахсий маълумот кўрсатилмайди).
"""

from __future__ import annotations

import os
import re

import requests
from dotenv import load_dotenv

FAL_CANDIDATES = [
    "https://rest.alpha.fal.ai/billing",
    "https://api.fal.ai/v1/billing",
    "https://api.fal.ai/v1/account/billing",
    "https://rest.fal.ai/billing",
]
ANTHROPIC_CANDIDATES = [
    "https://api.anthropic.com/v1/organizations/cost_report?starting_at=2026-11-01T00:00:00Z",
]


def redact(text: str) -> str:
    return re.sub(r"(sk-[A-Za-z0-9_\-]{6,}|[0-9a-f]{8,}:[A-Za-z0-9_\-]{6,})", "***", text)


def probe(name: str, url: str, headers: dict) -> None:
    try:
        r = requests.get(url, headers=headers, timeout=20)
        body = redact(r.text[:300]).replace("\n", " ")
        print(f"[{name}] {r.status_code} {url}\n    {body}")
    except requests.RequestException as exc:
        print(f"[{name}] уланмади {url}: {exc.__class__.__name__}")


def main() -> None:
    load_dotenv()
    fal_key = os.environ.get("FAL_KEY")
    if fal_key:
        for url in FAL_CANDIDATES:
            probe("fal", url, {"Authorization": f"Key {fal_key}"})
    else:
        print("[fal] FAL_KEY .env да йўқ")

    anth_key = os.environ.get("ANTHROPIC_API_KEY")
    if anth_key:
        for url in ANTHROPIC_CANDIDATES:
            probe("anthropic", url, {"x-api-key": anth_key, "anthropic-version": "2023-06-01"})
    else:
        print("[anthropic] ANTHROPIC_API_KEY .env да йўқ")

    print("\nЭслатма: 200 код чиққан эндпоинтни юборинг; 401/403/404 — бу эндпоинт ишламайди.")


if __name__ == "__main__":
    main()
