"""Claude: китобни сериалга айлантириш.

1) plan_series   — бутун китобни ўқиб «сериал библияси» тузади: персонажлар (ташқи кўриниши,
                   овози), давр ва жой, визуал услуб ва қисмлар рўйхати (ҳар қисм китобнинг
                   қайси бўлакларини қамраши).
2) write_episode — битта қисм учун кадрма-кадр сценарий ва ўзбекча диалоглар ёзади.
"""

from __future__ import annotations

import anthropic
from pydantic import BaseModel, Field

from book_reader import split_into_chunks

MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SEGMENT_CHARS = 8_000            # китоб шу ўлчамдаги рақамланган бўлакларга бўлинади
MAX_CHARS_SINGLE_REQUEST = 800_000


# ----------------------------- Маълумот тузилмалари -----------------------------

class Voice(BaseModel):
    gender: str = Field(description="male ёки female")
    age_group: str = Field(description="child, young, adult, elderly")
    tone: str = Field(description="Овоз хусусияти инглизча, мас. 'deep, tired, warm'")


class Character(BaseModel):
    id: str = Field(description="Лотинча қисқа идентификатор, мас. 'rabbim', 'kimsan'")
    name: str = Field(description="Исми (кириллда, китобдагидек)")
    role: str = Field(description="Сюжетдаги ўрни (ўзбекча)")
    appearance: str = Field(
        description=(
            "Ташқи кўриниш ИНГЛИЗ тилида, видео модели учун жуда аниқ ва ўзгармас: ёши, бўйи, юзи, "
            "сочи, мўйлови, кийими (давр ва миллий кийим аниқ), характерли белгилари. 40-70 сўз."
        )
    )
    voice: Voice


class EpisodePlan(BaseModel):
    number: int
    title: str = Field(description="Қисм номи (ўзбекча, кириллда)")
    segment_start: int = Field(description="Китобнинг биринчи бўлаги рақами")
    segment_end: int = Field(description="Охирги бўлаги рақами (ўзи ҳам киради)")
    summary: str = Field(description="Бу қисмда нима бўлади (ўзбекча, 2-4 жумла)")
    cliffhanger: str = Field(description="Қисм қандай савол/кескинлик билан тугайди — томошабин эртангисини кутиши учун")


class SeriesPlan(BaseModel):
    series_title: str = Field(description="Сериал номи (кириллда)")
    logline: str
    era_and_setting: str = Field(description="Давр, жой, муҳит — ИНГЛИЗЧА, видео промптлари учун (мас. '1940s Uzbek village near Tashkent...')")
    visual_style: str = Field(description="Барча кадрлар учун умумий кино услуби ИНГЛИЗЧА (камера, плёнка, ранг, ёруғлик)")
    narrator_voice: Voice
    characters: list[Character]
    episodes: list[EpisodePlan]


class Line(BaseModel):
    speaker: str = Field(description="Персонаж id си ёки 'narrator'")
    text: str = Field(description="Ўзбекча реплика КИРИЛЛ ёзувида, табиий оғзаки нутқ, 1-2 жумла")
    emotion: str = Field(description="Инглизча бир сўз: calm, sad, angry, joyful, fearful, whisper, tender, tired, excited, crying")


class Shot(BaseModel):
    number: int
    description: str = Field(description="Кадрда нима бўлаётгани (ўзбекча, 1 жумла)")
    characters_in_shot: list[str] = Field(description="Кадрда кўринадиган персонажлар id лари")
    video_prompt: str = Field(
        description=(
            "Видео модели учун ИНГЛИЗЧА промпт: ҳаракат, камера бурчаги ва ҳаракати, ёруғлик, муҳит, "
            "кайфият. Персонажларни исми билан эмас, ташқи кўриниши билан қисқача эсла."
        )
    )
    duration_seconds: int = Field(description="5 ёки 10. Кадрдаги репликалар шу вақтга сиғсин")
    lines: list[Line] = Field(description="Шу кадр давомида айтиладиган репликалар (бўш бўлиши мумкин)")


class EpisodeScript(BaseModel):
    number: int
    title: str
    recap: str = Field(description="'Олдинги қисмда...' — диктор учун 1-2 жумла (1-қисмда — сериалга қисқа кириш)")
    shots: list[Shot]
    next_episode_teaser: str = Field(description="Охирида диктор айтадиган қизиқтирувчи 1 жумла, кейинги қисмни очмасдан")


# ----------------------------- Промптлар -----------------------------

PLAN_SYSTEM = """Сен ўзбек кино ва телесериалларининг тажрибали сценаристи ва шоураннерисан.
Вазифанг — китобни ҳар куни битта қисм чиқадиган қисқа AI-сериалга мослаштириш.

Қоидалар:
- Китобнинг сюжети, руҳи ва персонажларига содиқ қол; ўзингдан воқеа қўшма.
- Китоб <segment id="N"> бўлакларига бўлинган. Ҳар қисм кетма-кет бўлаклар оралиғини қамрасин;
  қисмлар бутун китобни бошидан охиригача, бўлакларни ташлаб кетмасдан қопласин.
- Ҳар қисм ўзича тугалланган кичик воқеа бўлсин ва кескин лаҳзада (cliffhanger) тугасин —
  томошабин эртанги қисмни кутсин.
- Персонажлар ташқи кўриниши (appearance) жуда аниқ ва ўзгармас бўлсин — улар ҳар куни бир хил кўриниши керак.
  Давр ва миллий кийимларни тарихий аниқ тасвирла.
- Кадрлар табиий, ҳаётий, реалистик кино каби бўлсин; мультфильм ёки фантастика услуби эмас."""

EPISODE_SYSTEM = """Сен ўзбек телесериалининг сценаристи ва режиссёрисан. Китобдан берилган парча асосида
сериалнинг битта қисми учун кадрма-кадр сценарий ёзасан.

Диалоглар:
- Реплика ўзбек тилида, КИРИЛЛ ёзувида, жонли оғзаки нутқ — китобдаги диалоглардан фойдалан,
  лекин экран учун қисқартир. Бир репликада 1-2 жумла.
- Диктор (narrator) фақат зарур жойда, қисқа; асосий юкни персонажлар диалоги кўтарсин.
- Ҳар кадрдаги репликалар шу кадр узунлигига сиғсин: ўзбекча нутқ тахминан секундига 12-14 ҳарф.
  Кўп реплика бўлса — 10 сониялик кадр ёки бир нечта кадрга бўл.

Кадрлар (лаб синхронизацияси йўқлигини ҳисобга ол — бу жуда муҳим):
- Видео модели лаб ҳаракатини овозга мослай олмайди. Шунинг учун гапираётган персонажни
  яқиндан, юзи камерага қараган ҳолда кўрсатма. Ўрнига: елка орқасидан кадр, орқа/ён томондан,
  узоқроқ умумий план, тингловчининг юзи (реакция), қўллар ёки буюмлар детали.
  Профессионал дубляж қилинган киноларда шундай қилинади.
- video_prompt инглизча, табиий, реалистик кино: 'cinematic, natural light, realistic, 35mm film'.
  Ҳаракат оддий ва аниқ бўлсин (бир кадрда битта асосий ҳаракат). Экрандаги ёзув/субтитр сўрама.
- Кадрлар орасида монтаж мантиқи бўлсин: умумий план → ўрта → детал → реакция.
- Қисм cliffhanger билан тугасин."""


# ----------------------------- Ёрдамчи функциялар -----------------------------

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _check(message) -> None:
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        raise RuntimeError(f"Claude сўровни рад этди. {getattr(details, 'explanation', '') or ''}".strip())
    if message.stop_reason == "max_tokens":
        raise RuntimeError("Жавоб max_tokens чегарасига етиб кесилди.")


def _structured(system: str, prompt: str, output_type, effort: str = "high"):
    with _client().beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=system,
        output_config={"effort": effort},
        output_format=output_type,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    _check(message)
    return message.parsed_output


def _text(prompt: str, effort: str = "medium") -> str:
    with _client().beta.messages.stream(
        model=MODEL,
        max_tokens=16000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    _check(message)
    return "".join(b.text for b in message.content if b.type == "text")


def make_segments(text: str) -> list[str]:
    return split_into_chunks(text, SEGMENT_CHARS)


def _tagged(segments: list[str], start: int = 1) -> str:
    return "\n".join(f'<segment id="{i}">\n{s}\n</segment>' for i, s in enumerate(segments, start))


# ----------------------------- Асосий функциялар -----------------------------

def plan_series(segments: list[str], episode_minutes: float, episodes: int | None = None, wishes: str = "") -> SeriesPlan:
    total_chars = sum(len(s) for s in segments)

    if total_chars <= MAX_CHARS_SINGLE_REQUEST:
        book_block = f"<book segments=\"{len(segments)}\">\n{_tagged(segments)}\n</book>"
    else:
        # Жуда катта китоб: бўлаклар гуруҳларининг мазмунини оламиз (бўлак рақамлари сақланади)
        group = MAX_CHARS_SINGLE_REQUEST // 3 // SEGMENT_CHARS
        parts = []
        for g in range(0, len(segments), group):
            print(f"  • Бўлаклар {g + 1}-{min(g + group, len(segments))} таҳлил қилинмоқда...")
            parts.append(_text(
                "Китоб парчасини ўзбекча батафсил баён қил. Ҳар бўлак учун алоҳида "
                "'[бўлак N]: ...' шаклида воқеалар, персонажлар (ташқи кўриниши билан), жойлар, "
                f"муҳим диалогларни ёз.\n\n{_tagged(segments[g:g + group], g + 1)}"
            ))
        book_block = f"<book_summary segments=\"{len(segments)}\">\n" + "\n\n".join(parts) + "\n</book_summary>"

    count = f"Қисмлар сони: {episodes}." if episodes else (
        "Қисмлар сонини ўзинг танла — ҳар қисм китобнинг табиий бир воқеасини қамрасин."
    )
    prompt = (
        f"{book_block}\n\n"
        f"Шу китоб асосида кундалик сериал режасини туз. Ҳар қисм экранда тахминан {episode_minutes:g} дақиқа. "
        f"{count} Бўлаклар 1 дан {len(segments)} гача.\n{wishes}"
    )
    plan: SeriesPlan = _structured(PLAN_SYSTEM, prompt, SeriesPlan, effort="high")

    # Бўлак оралиқларини тўғрилаш
    for ep in plan.episodes:
        ep.segment_start = max(1, min(ep.segment_start, len(segments)))
        ep.segment_end = max(ep.segment_start, min(ep.segment_end, len(segments)))
    return plan


def write_episode(
    plan: SeriesPlan,
    episode: EpisodePlan,
    segments: list[str],
    episode_minutes: float,
    previous_summary: str = "",
) -> EpisodeScript:
    characters = "\n".join(
        f"- id={c.id}; {c.name}; {c.role}; кўриниши: {c.appearance}" for c in plan.characters
    )
    excerpt = _tagged(segments[episode.segment_start - 1: episode.segment_end], episode.segment_start)
    target_shots = max(6, round(episode_minutes * 60 / 7))

    prompt = f"""<series>
Номи: {plan.series_title}
Давр ва жой: {plan.era_and_setting}
Визуал услуб: {plan.visual_style}
Персонажлар:
{characters}
</series>

<previous_episode>{previous_summary or "Бу биринчи қисм."}</previous_episode>

<episode_plan>
{episode.number}-қисм: «{episode.title}»
Мазмуни: {episode.summary}
Якуни (cliffhanger): {episode.cliffhanger}
</episode_plan>

<book_excerpt>
{excerpt}
</book_excerpt>

Шу қисм учун тахминан {target_shots} кадрли (жами ~{episode_minutes:g} дақиқа) сценарий ёз.
speaker майдонида фақат юқоридаги персонаж id лари ёки 'narrator' ишлат."""

    script: EpisodeScript = _structured(EPISODE_SYSTEM, prompt, EpisodeScript, effort="high")
    known = {c.id for c in plan.characters}
    for shot in script.shots:
        shot.duration_seconds = 10 if shot.duration_seconds >= 8 else 5
        shot.characters_in_shot = [c for c in shot.characters_in_shot if c in known]
        for line in shot.lines:
            if line.speaker not in known:
                line.speaker = "narrator"
    script.number = episode.number
    return script
