"""Claude ёрдамида китобни таҳлил қилиш ва трейлер сценарийсини яратиш."""

from __future__ import annotations

import anthropic
from pydantic import BaseModel, Field

from book_reader import split_into_chunks

MODEL = "claude-opus-5-5"

# Claude Opus 5.5 контексти 1M токен. Кирилл матни ~2-3 белги/токен,
# шунинг учун 800 минг белгигача бўлган китоб бир сўровда юборилади.
# Ундан узун бўлса — аввал бўлакма-бўлак қисқача мазмун олинади.
MAX_CHARS_SINGLE_REQUEST = 800_000
CHUNK_CHARS = 300_000

# Хавфсизлик фильтри сўровни рад этса, API уни автоматик бошқа моделда
# қайта ишлатади ("fallbacks": "default").
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class Scene(BaseModel):
    number: int = Field(description="Саҳна тартиб рақами, 1 дан бошлаб")
    title: str = Field(description="Саҳна номи (китоб тилида)")
    what_happens: str = Field(description="Китобда бу саҳнада нима бўлади (китоб тилида, 1-3 жумла)")
    narration: str = Field(description="Диктор матни ёки экрандаги ёзув (китоб тилида, 1-2 қисқа жумла)")
    video_prompt: str = Field(
        description=(
            "Видео модели (Kling/Veo) учун ИНГЛИЗ тилидаги батафсил промпт: "
            "кадр, камера ҳаракати, ёруғлик, муҳит, персонажлар ташқи кўриниши, кайфият, кино услуби. "
            "Матн, ёзув ва логотипларни сўрама."
        )
    )
    duration_seconds: int = Field(description="Клип узунлиги: фақат 5 ёки 10")


class TrailerScript(BaseModel):
    book_title: str
    language: str = Field(description="Китоб тили: uzbek, russian, english ва ҳ.к.")
    logline: str = Field(description="Бир жумлали асосий ғоя (китоб тилида)")
    visual_style: str = Field(description="Барча клиплар учун умумий визуал услуб (инглизча)")
    characters: str = Field(description="Асосий персонажлар ташқи кўриниши (инглизча), барча клипларда бир хил бўлиши учун")
    full_script: str = Field(description="Тўлиқ трейлер сценарийси (китоб тилида)")
    scenes: list[Scene]


SYSTEM_PROMPT = """Сен тажрибали кино сценаристи ва трейлер монтажчисисан.
Вазифанг — берилган китоб асосида қисқа кинематографик трейлер сценарийсини тузиш.

Қоидалар:
- Китобнинг энг кучли, визуал жиҳатдан таъсирли саҳналарини танла; сюжетнинг охирини (спойлер) очма.
- Саҳналар трейлер мантиқида бўлсин: таништириш → зиддият → кескинлик ошиши → сирли якун.
- narration, title, what_happens, logline ва full_script — китоб ёзилган тилда бўлсин.
- video_prompt — доим инглиз тилида, бир саҳнани тасвирловчи мустақил промпт бўлсин:
  видео модели олдинги саҳналарни билмайди, шунинг учун ҳар промптга персонаж ташқи кўриниши
  ва умумий визуал услубни қайта ёз (персонажлар клиплар орасида бир хил кўриниши учун).
- video_prompt да экрандаги матн, ёзув, субтитр ёки логотип сўрама.
- duration_seconds фақат 5 ёки 10 бўлсин."""


def _client() -> anthropic.Anthropic:
    # ANTHROPIC_API_KEY муҳит ўзгарувчисидан олинади
    return anthropic.Anthropic()


def _check_stop_reason(message) -> None:
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        reason = getattr(details, "explanation", None) if details else None
        raise RuntimeError(f"Claude сўровни рад этди. {reason or ''}".strip())
    if message.stop_reason == "max_tokens":
        raise RuntimeError("Жавоб max_tokens чегарасига етиб кесилди — саҳналар сонини камайтиринг.")


def _summarize_chunk(client: anthropic.Anthropic, chunk: str, index: int, total: int) -> str:
    """Жуда узун китоб учун: битта бўлакнинг батафсил қисқача мазмуни."""
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=16000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": "medium"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Бу китобнинг {index}/{total}-қисми. Уни китоб тилида батафсил қисқача баён қил: "
                    "воқеалар кетма-кетлиги, персонажлар (ташқи кўриниши билан), жойлар, "
                    "энг визуал ва драматик лаҳзалар.\n\n"
                    f"<book_part>\n{chunk}\n</book_part>"
                ),
            }
        ],
    ) as stream:
        message = stream.get_final_message()
    _check_stop_reason(message)
    return "".join(b.text for b in message.content if b.type == "text")


def create_trailer_script(book_text: str, num_scenes: int = 6, extra_wishes: str = "") -> TrailerScript:
    client = _client()

    if len(book_text) <= MAX_CHARS_SINGLE_REQUEST:
        book_block = f"<book>\n{book_text}\n</book>"
    else:
        chunks = split_into_chunks(book_text, CHUNK_CHARS)
        summaries = []
        for i, chunk in enumerate(chunks, 1):
            print(f"  • Китоб қисми {i}/{len(chunks)} таҳлил қилинмоқда...")
            summaries.append(_summarize_chunk(client, chunk, i, len(chunks)))
        joined = "\n\n".join(f"<part index=\"{i}\">\n{s}\n</part>" for i, s in enumerate(summaries, 1))
        book_block = f"<book_summary>\n{joined}\n</book_summary>"

    wishes = f"\n\nҚўшимча истаклар: {extra_wishes}" if extra_wishes else ""
    prompt = (
        f"{book_block}\n\n"
        f"Шу китоб асосида {num_scenes} та саҳнадан иборат трейлер сценарийсини туз.{wishes}"
    )

    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        output_config={"effort": "high"},
        output_format=TrailerScript,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    _check_stop_reason(message)
    script: TrailerScript = message.parsed_output

    # Видео модели фақат 5 ёки 10 сония қабул қилади
    for scene in script.scenes:
        scene.duration_seconds = 10 if scene.duration_seconds >= 8 else 5
    return script
