"""Claude: китобни вертикал сериалга айлантириш (ҳар қандай мамлакат, рус дубляжи).

1) plan_series   — бутун китобни ўқиб «сериал библияси»ни тузади: воқеа қаерда ва қачон бўлади,
                   персонажлар (миллати, ташқи кўриниши, кийими, овози), жойлар, услуб ва қисмлар.
2) write_episode — битта қисм учун кадрма-кадр сценарий: планлар, расм ва ҳаракат промптлари,
                   русча репликалар, ким кадрда гапиради (лаб синхрони учун), товушлар.
3) pick_best_image — бир нечта калит расмдан эталонларга энг мосини танлайди (Claude кўриб баҳолайди).

Claude учун кўрсатмалар рус тилида: томошабин эшитадиган ва кўрадиган ҳамма нарса русча бўлади.
Расм ва видео моделлари учун тавсифлар инглизча (улар инглизчада яхшироқ ишлайди).
"""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from book_reader import split_into_chunks
from claude_client import structured as _structured
from claude_client import text as _text

SEGMENT_CHARS = 8_000            # китоб шу ўлчамдаги рақамланган бўлакларга бўлинади
MAX_CHARS_SINGLE_REQUEST = 800_000

SPEECH_CHARS_PER_SECOND = 14.5   # рус нутқи тахминан шунча белги/сония
MAX_SPEECH_PER_SHOT = 7.5        # бир кадрга сиғадиган нутқ (видео 8 с гача; ундан узуни секинлашади ёки қотади)


# ----------------------------- Маълумот тузилмалари -----------------------------

class VoiceSpec(BaseModel):
    gender: Literal["male", "female"]
    age: int = Field(description="Примерный возраст голоса в годах")
    description: str = Field(
        description=(
            "По-английски, для генератора голосов (Voice Design): тембр, высота, темп, манера, характер. "
            "Всегда носитель русского языка, актёр профессионального русского дубляжа. "
            "Пример: 'Native Russian male voice actor, about 55, deep warm baritone, slow and measured, "
            "slightly hoarse, calm authority, professional film dubbing quality'. 25-60 слов."
        )
    )


class Character(BaseModel):
    id: str = Field(description="Короткий латинский идентификатор: kenji, mary, old_tom")
    name: str = Field(description="Имя по-русски, в принятой русской передаче (Кэндзи, Мэри)")
    role: str = Field(description="Роль в сюжете, по-русски, одна фраза")
    gender: Literal["male", "female"]
    age: int
    ethnicity: str = Field(description="По-английски: народ/этническая принадлежность, например 'Japanese', 'Irish-American'")
    appearance: str = Field(
        description=(
            "По-английски, для генерации изображений, очень конкретно и неизменно: лицо, форма глаз, "
            "кожа, волосы (цвет, длина, причёска), растительность на лице, телосложение, рост, приметы. "
            "40-70 слов. Без одежды — она в costume."
        )
    )
    costume: str = Field(description="По-английски: основная одежда, исторически точная для эпохи, страны и сословия. 20-40 слов")
    voice: VoiceSpec


class Location(BaseModel):
    id: str = Field(description="Короткий латинский идентификатор: tea_house, ship_deck")
    name: str = Field(description="Название по-русски")
    description: str = Field(
        description="По-английски, для генерации изображений: архитектура, материалы, предметы, эпоха, свет. 30-60 слов"
    )
    interior: bool
    ambience: str = Field(
        description=(
            "По-английски: фоновый звук этого места для генератора звуков, без музыки и речи. "
            "Пример: 'quiet 1930s Tokyo side street at dusk, distant tram bell, wooden sandals on stone, light wind'"
        )
    )


class EpisodePlan(BaseModel):
    number: int
    title: str = Field(description="Название серии по-русски")
    segment_start: int = Field(description="Номер первого сегмента книги")
    segment_end: int = Field(description="Номер последнего сегмента (включительно)")
    summary: str = Field(description="Что происходит в серии, по-русски, 2-4 предложения")
    cliffhanger: str = Field(description="Каким вопросом/напряжением заканчивается серия, по-русски")


class SeriesPlan(BaseModel):
    series_title: str = Field(description="Название сериала по-русски")
    original_title: str = Field(description="Название книги так, как оно указано в книге")
    author: str
    logline: str = Field(description="Главная идея в одном предложении, по-русски")
    country: str = Field(description="По-английски: страна/регион, где происходит действие (не страна автора)")
    era: str = Field(description="По-английски: эпоха и годы действия, например 'Tokyo, Japan, 1932-1934'")
    setting: str = Field(description="По-английски: общий мир фильма для промптов — быт, архитектура, природа, социальная среда. 40-80 слов")
    visual_style: str = Field(
        description=(
            "По-английски: единый кинематографический стиль всех кадров — камера, оптика, плёнка, палитра, свет. "
            "Реалистичное живое кино, не мультфильм."
        )
    )
    music_style: str = Field(description="По-английски: стиль музыки (инструменты, характер), подходящий стране, эпохе и жанру")
    narrator_voice: VoiceSpec
    characters: list[Character]
    locations: list[Location]
    episodes: list[EpisodePlan]


class Line(BaseModel):
    speaker: str = Field(description="id персонажа или 'narrator'")
    text: str = Field(description="Реплика по-русски, живая разговорная речь, 1-2 коротких предложения")
    delivery: str = Field(
        description=(
            "Короткие английские теги подачи для синтеза речи через запятую: whispers, sighs, angry, "
            "laughs softly, trembling voice, tired, excited, crying, sarcastic, shouting. '' — нейтрально"
        )
    )


ShotType = Literal[
    "establishing", "wide", "medium", "medium_close_up", "close_up",
    "extreme_close_up", "over_the_shoulder", "insert",
]


class Shot(BaseModel):
    number: int
    location_id: str = Field(description="id локации из библии сериала")
    shot_type: ShotType
    characters_in_shot: list[str] = Field(description="id персонажей, которые видны в кадре")
    speaker_on_screen: str = Field(
        description=(
            "id персонажа, чьё лицо видно в кадре и кто говорит в этом кадре (для липсинка). "
            "'' — если лица говорящего не видно или в кадре никто не говорит"
        )
    )
    description: str = Field(description="Что происходит в кадре, по-русски, одно предложение")
    image_prompt: str = Field(
        description=(
            "По-английски: композиция первого кадра — кто где, поза, выражение лица, план, объектив, свет, "
            "время суток. Персонажей называй только как [id], например [kenji]. Вертикальный кадр 9:16; "
            "главное — в центре, нижняя треть без важных деталей (там субтитры)."
        )
    )
    motion_prompt: str = Field(
        description=(
            "По-английски: одно ясное естественное действие в кадре + движение камеры "
            "(static, slow push-in, slow pull-back, handheld, pan left/right, tilt up). Персонажи как [id]."
        )
    )
    sound: str = Field(
        description="По-английски: шумы и эффекты этого кадра (footsteps on gravel, door creaks), без музыки и речи. '' если нет"
    )
    duration_seconds: int = Field(description="Желаемая длительность кадра, от 3 до 8 секунд")
    lines: list[Line] = Field(description="Реплики в этом кадре (может быть пусто)")


class EpisodeScript(BaseModel):
    number: int
    title: str = Field(description="Название серии по-русски")
    recap: str = Field(description="Одно короткое предложение по-русски: что было раньше (для подписи к посту). В 1-й серии — о чём сериал")
    shots: list[Shot]
    music_prompt: str = Field(
        description=(
            "По-английски: музыка для этой серии для генератора музыки — настроение и его развитие от начала "
            "к концу, инструменты, темп. Только инструментал, без вокала"
        )
    )
    next_episode_teaser: str = Field(description="Одна интригующая фраза диктора по-русски в конце серии, не раскрывая следующую")


class ImageVerdict(BaseModel):
    best_index: int = Field(description="Номер лучшего варианта (с 1)")
    problems: list[str] = Field(description="Коротко по-русски: недостатки выбранного варианта ([] если нет)")


# ----------------------------- Промптлар -----------------------------

PLAN_SYSTEM = """Ты — опытный шоураннер и сценарист. Ты адаптируешь книги в короткие вертикальные \
сериалы (YouTube Shorts, Instagram Reels) с профессиональным русским дубляжом. Серия выходит каждый день.

Мир фильма берётся из книги:
- Определи страну, регион и эпоху, где ПРОИСХОДИТ ДЕЙСТВИЕ (не страну автора). Внешность, этническая \
принадлежность, костюмы, причёски, архитектура, интерьеры, быт, транспорт и природа — как в этой стране \
и эпохе, исторически достоверно.
- Персонажи выглядят как актёры соответствующего народа: японский роман — японские актёры, американский — \
американские. Если книга описывает персонажа иначе (иностранец, другой народ) — следуй книге.
- Тексты для генерации изображений (appearance, costume, setting, описания локаций, visual_style) пиши \
по-английски, конкретно и неизменно: они повторяются в каждом кадре, чтобы персонаж выглядел одинаково \
во всех сериях.
- Реалистичное живое кино, как снятое с настоящими актёрами. Не мультфильм и не фэнтези-иллюстрация \
(если сама книга не фантастика).

Язык: всё, что зритель видит и слышит (названия, имена, реплики, титры), — по-русски. Имена и топонимы — \
в принятой русской передаче (японские — по системе Поливанова: Кэндзи, Сётаро; английские — практической \
транскрипцией: Джон, Мэри).

Структура:
- Книга разбита на сегменты <segment id="N">. Каждая серия охватывает непрерывный диапазон сегментов; \
серии покрывают книгу от начала до конца без пропусков.
- Каждая серия — законченный маленький эпизод: цепляющее начало и клиффхэнгер в конце.
- Будь верен сюжету, духу и персонажам книги; не выдумывай событий.

Голоса: голоса персонажей должны заметно отличаться друг от друга (возраст, тембр, темп, манера)."""

EPISODE_SYSTEM = """Ты — сценарист и режиссёр вертикального сериала (кадр 9:16, смотрят на телефоне) \
с профессиональным русским дубляжом. По отрывку книги пиши покадровый сценарий одной серии.

Диалоги:
- Все реплики, текст рассказчика (narrator), recap и next_episode_teaser — по-русски, живой разговорной \
речью, как в хорошем русском дубляже зарубежного кино.
- Не копируй текст книги или её перевода дословно: пиши собственные реплики по событиям книги.
- Реплика — 1-2 коротких предложения. Русская речь — примерно 14-15 знаков в секунду. Все реплики кадра \
должны уложиться в его длительность: не больше ~7 секунд речи на кадр. Длинный разговор дели на несколько кадров.
- Рассказчик — только там, где без него непонятно; основное несут диалоги и действие.

Кадры:
- Монтаж как в кино: новая локация — establishing или wide, затем средние планы, на эмоциях — крупные, \
детали (insert) и реакции слушающих. Чередуй крупность и ракурсы, не повторяй один план подряд.
- Для телефона предпочитай средние и крупные планы; общие — коротко, для ориентации.
- Липсинк: если в кадре видно лицо говорящего — укажи его в speaker_on_screen. В таком кадре говорит только \
он; реплики собеседника — в его собственном кадре (восьмёрка) или за кадром. Если говорящего не видно \
(спина, за кадром) — speaker_on_screen = "".
- В characters_in_shot — только те, кто действительно виден в кадре; максимум 3 персонажа.
- image_prompt и motion_prompt — по-английски; персонажей называй только как [id] (внешность и костюм \
подставятся автоматически). В motion_prompt — одно естественное действие и движение камеры. Не проси \
надписей на экране.
- sound — шумы этого кадра по-английски, без музыки и речи.
- Первый кадр серии должен сразу цеплять: начинай с действия или сильного образа, а не с вступления.
- Серия заканчивается клиффхэнгером."""


# ----------------------------- Ёрдамчи функциялар -----------------------------

def make_segments(text: str) -> list[str]:
    return split_into_chunks(text, SEGMENT_CHARS)


def _tagged(segments: list[str], start: int = 1) -> str:
    return "\n".join(f'<segment id="{i}">\n{s}\n</segment>' for i, s in enumerate(segments, start))


def speech_seconds(text: str) -> float:
    """Репликанинг тахминий узунлиги (сония) — сценарийни текшириш учун."""
    return len(re.sub(r"\s+", " ", text or "").strip()) / SPEECH_CHARS_PER_SECOND


def long_speech_shots(script: dict) -> list[tuple[int, float]]:
    """Нутқи битта кадрга сиғмайдиган кадрлар: [(кадр рақами, тахминий сония)].

    script — script.json мазмуни (dict). serial.py ва check_script.py бир хил қоидани ишлатади.
    """
    out = []
    for shot in script.get("shots", []):
        seconds = sum(speech_seconds(line.get("text", "")) for line in shot.get("lines", []))
        if seconds > MAX_SPEECH_PER_SHOT:
            out.append((shot.get("number"), round(seconds, 1)))
    return out


# ----------------------------- Асосий функциялар -----------------------------

def plan_series(segments: list[str], episode_minutes: float, episodes: int | None = None, wishes: str = "") -> SeriesPlan:
    total_chars = sum(len(s) for s in segments)

    if total_chars <= MAX_CHARS_SINGLE_REQUEST:
        book_block = f"<book segments=\"{len(segments)}\">\n{_tagged(segments)}\n</book>"
    else:
        # Жуда катта китоб: бўлаклар гуруҳларининг батафсил мазмунини оламиз (бўлак рақамлари сақланади)
        group = MAX_CHARS_SINGLE_REQUEST // 3 // SEGMENT_CHARS
        parts = []
        for g in range(0, len(segments), group):
            print(f"  • Бўлаклар {g + 1}-{min(g + group, len(segments))} таҳлил қилинмоқда...")
            parts.append(_text(
                "Подробно перескажи отрывок книги по-русски. Для каждого сегмента отдельно, в виде "
                "'[сегмент N]: ...': события, персонажи (с внешностью, возрастом, одеждой), места, эпоха, "
                f"важные диалоги.\n\n{_tagged(segments[g:g + group], g + 1)}"
            ))
        book_block = f"<book_summary segments=\"{len(segments)}\">\n" + "\n\n".join(parts) + "\n</book_summary>"

    count = f"Количество серий: {episodes}." if episodes else (
        "Количество серий выбери сам — каждая серия охватывает одно естественное событие книги."
    )
    prompt = (
        f"{book_block}\n\n"
        f"Составь по этой книге план ежедневного вертикального сериала. Каждая серия на экране длится "
        f"примерно {episode_minutes:g} мин. {count} Сегменты от 1 до {len(segments)}."
        + (f"\nДополнительные пожелания: {wishes}" if wishes else "")
    )
    plan: SeriesPlan = _structured(PLAN_SYSTEM, prompt, SeriesPlan, effort="high", max_tokens=128000)
    return normalize_plan(plan, len(segments))


def normalize_plan(plan: SeriesPlan, n_segments: int) -> SeriesPlan:
    """Claude режасини тартибга солади: қисмлар 1, 2, 3… бўлиб рақамланади, бўлак оралиқлари текширилади."""
    for ep in plan.episodes:
        ep.segment_start = max(1, min(ep.segment_start, n_segments))
        ep.segment_end = max(ep.segment_start, min(ep.segment_end, n_segments))
    # Қисмлар китоб тартибида ва 1 дан бошлаб узлуксиз рақамланади (0, такрор ёки ташлаб кетилган рақам бўлмасин)
    plan.episodes.sort(key=lambda e: (e.segment_start, e.number))
    for i, ep in enumerate(plan.episodes, 1):
        ep.number = i
    expected = 1
    for ep in plan.episodes:
        if ep.segment_start > expected:
            print(f"   ⚠️  {expected}–{ep.segment_start - 1}-бўлаклар бирорта қисмга кирмаган ({ep.number}-қисмдан олдин)")
        elif ep.segment_start < expected:
            print(f"   ⚠️  {ep.number}-қисм олдинги қисм билан устма-уст тушади (бўлак {ep.segment_start})")
        expected = max(expected, ep.segment_end + 1)
    if plan.episodes and expected <= n_segments:
        print(f"   ⚠️  Китоб охири ({expected}–{n_segments}-бўлаклар) бирорта қисмга кирмаган")
    for c in plan.characters:
        c.id = _slug(c.id)
    for loc in plan.locations:
        loc.id = _slug(loc.id)
    return plan


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_") or "x"


def write_episode(
    plan: SeriesPlan,
    episode: EpisodePlan,
    segments: list[str],
    episode_minutes: float,
    previous_summary: str = "",
) -> EpisodeScript:
    characters = "\n".join(
        f"- id={c.id}; {c.name}; {c.role}; {c.gender}, {c.age}; {c.ethnicity}" for c in plan.characters
    )
    locations = "\n".join(f"- id={loc.id}; {loc.name}; {loc.description}" for loc in plan.locations)
    excerpt = _tagged(segments[episode.segment_start - 1: episode.segment_end], episode.segment_start)
    seconds = episode_minutes * 60
    target_shots = max(8, round(seconds / 5))

    prompt = f"""<series>
Название: {plan.series_title}
Где и когда: {plan.country}; {plan.era}
Мир: {plan.setting}
Персонажи:
{characters}
Локации:
{locations}
</series>

<previous_episode>{previous_summary or "Это первая серия."}</previous_episode>

<episode_plan>
Серия {episode.number}: «{episode.title}»
Содержание: {episode.summary}
Финал (клиффхэнгер): {episode.cliffhanger}
</episode_plan>

<book_excerpt>
{excerpt}
</book_excerpt>

Напиши сценарий этой серии: примерно {target_shots} кадров, всего около {seconds:.0f} секунд \
(строго не больше {min(seconds + 20, 170):.0f} секунд). В speaker используй только id персонажей выше \
или 'narrator'; в location_id — только id локаций выше."""

    script: EpisodeScript = _structured(episode_system(), prompt, EpisodeScript, effort="high")
    return normalize_script(script, plan, episode.number)


def episode_system() -> str:
    return EPISODE_SYSTEM


def normalize_script(script: EpisodeScript, plan: SeriesPlan, number: int, renumber: bool = True) -> EpisodeScript:
    """Номаълум id ларни тозалаш ва чегараларни тўғрилаш.

    Claude ёзган янги сценарийда ҳам, қўлда таҳрирланган script.json да ҳам ишлатилади.
    renumber=False: кадр рақамлари сақланади (тайёр расм ва видеолар шу рақамларга боғланган),
    фақат рақамлар такрорланса ёки нотўғри бўлса қайта рақамланади.
    """
    known = {c.id for c in plan.characters}
    locations = {loc.id for loc in plan.locations}
    first_location = plan.locations[0].id if plan.locations else ""
    numbers = [s.number for s in script.shots]
    if renumber or len(set(numbers)) != len(numbers) or any(n < 1 or n > 99 for n in numbers):
        if not renumber:
            print("   ⚠️  script.json да кадр рақамлари такрорланган ёки нотўғри — кадрлар қайта рақамланди")
        for i, shot in enumerate(script.shots, 1):
            shot.number = i
    for i, shot in enumerate(script.shots, 1):
        shot.duration_seconds = max(3, min(8, int(shot.duration_seconds)))
        shot.characters_in_shot = [c for c in dict.fromkeys(_slug(c) for c in shot.characters_in_shot) if c in known][:3]
        if _slug(shot.location_id) in locations:
            shot.location_id = _slug(shot.location_id)
        else:
            shot.location_id = script.shots[i - 2].location_id if i > 1 else first_location
        speaker = _slug(shot.speaker_on_screen) if shot.speaker_on_screen else ""
        speaks_here = {_slug(line.speaker) for line in shot.lines}
        shot.speaker_on_screen = speaker if (speaker in known and speaker in shot.characters_in_shot
                                             and speaker in speaks_here) else ""
        for line in shot.lines:
            sp = _slug(line.speaker)
            line.speaker = sp if sp in known else "narrator"
    script.number = number
    return script


def pick_best_image(candidates: list[Path], references: list[tuple[str, Path]], shot_text: str) -> ImageVerdict:
    """Claude калит расм вариантларини эталонлар билан солиштириб, энг яхшисини танлайди.

    candidates ва references — кичрайтирилган JPEG файллар (ҳар бири ~1 МБ дан кичик).
    """
    content: list[dict] = []
    for label, path in references:
        content.append({"type": "text", "text": f"Эталон: {label}"})
        content.append(_image_block(path))
    for i, path in enumerate(candidates, 1):
        content.append({"type": "text", "text": f"Вариант {i}"})
        content.append(_image_block(path))
    content.append({"type": "text", "text": (
        f"Задуманный кадр: {shot_text}\n\nВыбери лучший вариант для кадра фильма. Критерии по важности: "
        "1) лица и костюмы совпадают с эталонами персонажей; 2) нет дефектов (лишние люди, искажённые руки "
        "и лица, надписи); 3) кадр соответствует задумке; 4) реалистичность и красота композиции."
    )})
    return _structured(
        "Ты — внимательный ассистент режиссёра по непрерывности (скрипт-супервайзер).",
        content, ImageVerdict, effort="low", max_tokens=16000,
    )


def _image_block(path: Path) -> dict:
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}
