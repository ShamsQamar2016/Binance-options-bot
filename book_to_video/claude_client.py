"""Claude API билан ишлаш учун умумий ёрдамчилар (сериал ва трейлер режимлари учун битта жой).

Модел, fallback ва хатоларни текшириш шу ерда: ўзгартириш керак бўлса, фақат шу файл ўзгаради.
"""

from __future__ import annotations

import anthropic

MODEL = "claude-opus-5-5"
# Хавфсизлик фильтри сўровни рад этса, API уни автоматик бошқа моделда қайта ишлатади
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def client() -> anthropic.Anthropic:
    # ANTHROPIC_API_KEY муҳит ўзгарувчисидан олинади. SDK 429 (лимит), 5xx ва тармоқ хатоларида
    # ўзи кутиб қайта уринади; кундалик автоматик иш узилмаслиги учун уринишлар сонини оширамиз.
    return anthropic.Anthropic(max_retries=5)


def check(message, hint: str = "") -> None:
    """Рад этилган ёки кесилган жавобда тушунарли хато беради."""
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        reason = getattr(details, "explanation", None) if details else None
        raise RuntimeError(f"Claude сўровни рад этди. {reason or ''}".strip())
    if message.stop_reason == "max_tokens":
        raise RuntimeError(f"Жавоб max_tokens чегарасига етиб кесилди. {hint}".strip())


def structured(system: str, content, output_type, effort: str = "high", max_tokens: int = 64000,
               hint: str = ""):
    """Claude'дан Pydantic схемасига мос жавоб олади. content — матн ёки контент блоклари рўйхати."""
    with client().beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=system,
        output_config={"effort": effort},
        output_format=output_type,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        message = stream.get_final_message()
    check(message, hint)
    return message.parsed_output


def text(prompt: str, effort: str = "medium", max_tokens: int = 32000) -> str:
    """Оддий матнли жавоб (масалан, узун китоб бўлагининг мазмуни)."""
    with client().beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    check(message)
    return "".join(b.text for b in message.content if b.type == "text")
