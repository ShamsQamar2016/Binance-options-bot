"""Сценарий текшируви: кетма-кет такрорланган сўзлар, бир хил репликалар ва кўп учрайдиган иборалар.

Ишлатиш:
    python check_script.py output\\serials\\otgan_kunlar\\episode_01\\script.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[\w'ʻ’]+", re.UNICODE)
PHRASE_LEN = 3          # нечта сўзли иборалар текширилади
PHRASE_MIN_COUNT = 3    # шунча ва ундан кўп учраса — огоҳлантирамиз


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def collect(script: dict) -> list[tuple[str, str]]:
    """(жой, матн) жуфтлари: ҳар репликани ва диктор матнини йиғади."""
    items: list[tuple[str, str]] = []
    items.append(("recap", script.get("recap", "")))
    items.append(("teaser", script.get("next_episode_teaser", "")))
    for shot in script.get("shots", []):
        for line in shot.get("lines", []):
            items.append((f"кадр {shot.get('number')} / {line.get('speaker')}", line.get("text", "")))
    return items


def check(script: dict) -> list[str]:
    problems: list[str] = []
    items = collect(script)

    # 1) Кетма-кет такрорланган сўзлар: "бу бу", "ҳа ҳа"
    for where, text in items:
        ws = words(text)
        for a, b in zip(ws, ws[1:]):
            if a == b and len(a) > 1:
                problems.append(f"[кетма-кет] {where}: «{a} {b}» — «{text[:80]}»")

    # 2) Бир хил ёки деярли бир хил репликалар
    seen: dict[str, str] = {}
    for where, text in items:
        key = " ".join(words(text))
        if len(key) < 12:
            continue
        if key in seen:
            problems.append(f"[такрор реплика] {where} = {seen[key]}: «{text[:80]}»")
        else:
            seen[key] = where

    # 3) Бутун сериал бўйича кўп учрайдиган иборалар
    counter: Counter = Counter()
    for _, text in items:
        ws = words(text)
        for i in range(len(ws) - PHRASE_LEN + 1):
            phrase = " ".join(ws[i:i + PHRASE_LEN])
            if all(len(w) > 2 for w in ws[i:i + PHRASE_LEN]):
                counter[phrase] += 1
    for phrase, n in counter.most_common():
        if n < PHRASE_MIN_COUNT:
            break
        problems.append(f"[кўп учрайди] «{phrase}» — {n} марта")

    # 4) Кадрга сиғмайдиган нутқ (рус нутқи ~14.5 белги/сония)
    for shot in script.get("shots", []):
        speech = sum(len(" ".join((line.get("text") or "").split())) for line in shot.get("lines", [])) / 14.5
        planned = shot.get("duration_seconds") or 0
        if speech > max(planned, 8) + 0.5:
            problems.append(f"[узун нутқ] кадр {shot.get('number')}: ~{speech:.1f} с нутқ, кадр {planned} с "
                            "— репликани қисқартиринг ёки кадрни иккига бўлинг")

    return problems


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = Path(sys.argv[1])
    script = json.loads(path.read_text(encoding="utf-8"))
    problems = check(script)
    if not problems:
        print("✓ Сценарийда такрорлар топилмади.")
        return 0
    print(f"⚠ Топилган муаммолар: {len(problems)}")
    for p in problems:
        print(" -", p)
    return 2


if __name__ == "__main__":
    sys.exit(main())
