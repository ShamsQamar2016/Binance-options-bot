"""Тасвир: персонаж ва жой эталонлари → калит расм → расмдан видео → лаб синхрони.

Ҳар кадр матндан эмас, тасдиқланган эталон расмлардан бошланади: шунинг учун персонаж ҳар кадрда ва
ҳар қисмда бир хил кўринади. Моделлар .env орқали алмаштирилади (fal.ai даги ID):

  IMAGE_MODEL       — матндан расм (эталонлар учун)          стандарт: fal-ai/nano-banana-pro
  IMAGE_EDIT_MODEL  — эталон расмлар асосида калит расм       стандарт: fal-ai/nano-banana-pro/edit
  VIDEO_MODEL       — расмдан видео                          стандарт: fal-ai/veo3.1/image-to-video
  LIPSYNC_MODEL     — лабни овозга мослаш                    стандарт: veed/lipsync/v2
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path

import fal_api
from series_planner import Character, Location, SeriesPlan, Shot, pick_best_image

logger = logging.getLogger(__name__)

NO_TEXT = "No text, letters, captions, subtitles, logos, watermarks or borders."
NEGATIVE = ("text, subtitles, captions, watermark, logo, cartoon, anime, illustration, CGI look, "
            "distorted face, deformed hands, extra fingers, extra people, morphing, flicker, blurry")

SHOT_WORDS = {
    "establishing": "establishing shot", "wide": "wide shot", "medium": "medium shot",
    "medium_close_up": "medium close-up", "close_up": "close-up", "extreme_close_up": "extreme close-up",
    "over_the_shoulder": "over-the-shoulder shot", "insert": "insert detail shot",
}


def model(name: str) -> str:
    defaults = {
        "IMAGE_MODEL": "fal-ai/nano-banana-pro",
        "IMAGE_EDIT_MODEL": "fal-ai/nano-banana-pro/edit",
        "VIDEO_MODEL": "fal-ai/veo3.1/image-to-video",
        "LIPSYNC_MODEL": "veed/lipsync/v2",
    }
    return os.environ.get(name) or defaults[name]


def _person(c: Character) -> str:
    who = "man" if c.gender == "male" else "woman"
    if c.age < 15:
        who = "boy" if c.gender == "male" else "girl"
    return f"{c.age}-year-old {c.ethnicity} {who}"


def _label(c: Character) -> str:
    return c.id.replace("_", " ").title()


def _sub_ids(text: str, names: dict[str, str]) -> str:
    """[kenji] → «Kenji (reference image 1)»; номаълум id лардан қавсни олиб ташлайди."""
    return re.sub(r"\[([a-zA-Z0-9_ ]+)\]", lambda m: names.get(m.group(1).strip().lower(), m.group(1)), text)


# ----------------------------- Эталонлар -----------------------------

def character_ref_prompt(plan: SeriesPlan, c: Character) -> str:
    return (
        f"Photorealistic casting reference photograph of a {_person(c)}. {c.appearance} "
        f"Wearing {c.costume}. Period and place: {plan.era}, {plan.country}. "
        "Three-quarter body from head to knees, standing, facing the camera, calm neutral expression, "
        "plain light-grey studio background, soft even lighting, sharp focus on the face, natural skin "
        f"texture, real human proportions. Looks like a real actor. {NO_TEXT}"
    )


def location_ref_prompt(plan: SeriesPlan, loc: Location) -> str:
    kind = "Interior" if loc.interior else "Exterior"
    return (
        f"Photorealistic cinematic establishing photograph, vertical 9:16 frame. {kind}: {loc.description} "
        f"Place and time: {plan.country}, {plan.era}. {plan.setting} Empty scene, no people. "
        f"Style: {plan.visual_style}. {NO_TEXT}"
    )


def text_to_image(prompt: str, out: Path, aspect: str, count: int = 1) -> list[Path]:
    result = fal_api.run(model("IMAGE_MODEL"), {
        "prompt": prompt, "aspect_ratio": aspect, "resolution": os.environ.get("IMAGE_RESOLUTION", "2K"),
        "num_images": count, "output_format": "png",
    }, timeout_s=600)
    return _save_images(result, out, count)


def _save_images(result: dict, out: Path, count: int) -> list[Path]:
    urls = fal_api.result_urls(result)
    if not urls:
        raise RuntimeError(f"Расм қайтмади: {json.dumps(result)[:400]}")
    paths = []
    for i, url in enumerate(urls[:count], 1):
        target = out if (count == 1 and i == 1) else out.with_name(f"{out.stem}_v{i}{out.suffix}")
        paths.append(fal_api.download(url, target))
    return paths


def make_reference(plan: SeriesPlan, item: Character | Location, out: Path) -> Path:
    if isinstance(item, Character):
        return text_to_image(character_ref_prompt(plan, item), out, "2:3")[0]
    return text_to_image(location_ref_prompt(plan, item), out, "9:16")[0]


# ----------------------------- Калит расм -----------------------------

def keyframe_prompt(plan: SeriesPlan, shot: Shot, refs: list[tuple[str, Path]]) -> str:
    chars = {c.id: c for c in plan.characters}
    loc = next((loc for loc in plan.locations if loc.id == shot.location_id), None)
    index = {key: i for i, (key, _) in enumerate(refs, 1)}
    names, cast = {}, []
    for cid in shot.characters_in_shot:
        c = chars[cid]
        where = f" (the person in reference image {index[cid]})" if cid in index else ""
        names[cid] = f"{_label(c)}{where}"
        cast.append(f"- {_label(c)}{where}: {_person(c)}. {c.appearance} Wearing {c.costume}.")
    for c in plan.characters:  # кадрда кўринмайдиган персонаж тилга олинса
        names.setdefault(c.id, f"{_label(c)}, a {_person(c)}")
    lines = [
        "Photorealistic vertical 9:16 film still from a live-action movie shot with real actors.",
        f"Shot: {SHOT_WORDS.get(shot.shot_type, shot.shot_type)}. {_sub_ids(shot.image_prompt, names)}",
    ]
    if cast:
        lines.append("Characters — keep each face, age, hair and costume exactly as in their reference image:")
        lines += cast
    if loc:
        ref = f" Match the place in reference image {index['@' + loc.id]}." if "@" + loc.id in index else ""
        lines.append(f"Location: {loc.description}.{ref}")
    lines += [
        f"World: {plan.country}, {plan.era}. {plan.setting}",
        f"Style: {plan.visual_style}. Natural skin texture, realistic anatomy and hands, motivated cinematic "
        "lighting, shallow depth of field.",
        "Composition: vertical frame, main subject near the center, nothing important in the bottom quarter.",
        NO_TEXT,
    ]
    return "\n".join(lines)


def make_keyframe(plan: SeriesPlan, shot: Shot, refs: list[tuple[str, Path]], out: Path) -> Path:
    """Калит расм: эталонлар билан бир неча вариант ясайди, Claude энг мосини танлайди."""
    takes = max(1, int(os.environ.get("KEYFRAME_TAKES", "2")))
    prompt = keyframe_prompt(plan, shot, refs)
    (out.parent / f"{out.stem}_prompt.txt").write_text(prompt, encoding="utf-8")
    payload = {"prompt": prompt, "aspect_ratio": "9:16", "resolution": os.environ.get("IMAGE_RESOLUTION", "2K"),
               "num_images": takes, "output_format": "png"}
    candidates: list[Path] = []
    while len(candidates) < takes:
        if refs:
            payload["image_urls"] = [fal_api.upload(p) for _, p in refs]
            result = fal_api.run(model("IMAGE_EDIT_MODEL"), payload, timeout_s=600)
        else:
            result = fal_api.run(model("IMAGE_MODEL"), payload, timeout_s=600)
        urls = fal_api.result_urls(result)[: takes - len(candidates)]
        if not urls:
            raise RuntimeError(f"Калит расм қайтмади: {json.dumps(result)[:400]}")
        for url in urls:
            n = len(candidates) + 1
            candidates.append(fal_api.download(url, out.with_name(f"{out.stem}_v{n}.png")))
    choice = 1
    if len(candidates) > 1:
        try:
            verdict = pick_best_image(
                [_thumb(p) for p in candidates],
                [(_ref_label(plan, key), _thumb(p)) for key, p in refs],
                shot.description + " / " + shot.image_prompt,
            )
            choice = verdict.best_index if 1 <= verdict.best_index <= len(candidates) else 1
            (out.parent / f"{out.stem}_choice.json").write_text(
                json.dumps({"best": choice, "problems": verdict.problems}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            if verdict.problems:
                print(f"       ⚠️  {'; '.join(verdict.problems)[:200]}")
        except Exception as exc:  # танлаш ишламаса — биринчи вариант
            logger.warning("Калит расм танланмади (%s), 1-вариант олинди", exc)
    candidates[choice - 1].replace(out)
    return out


def _ref_label(plan: SeriesPlan, key: str) -> str:
    if key.startswith("@"):
        return f"место «{key[1:]}»"
    c = next((c for c in plan.characters if c.id == key), None)
    return f"персонаж {c.name} ({key})" if c else key


def _thumb(path: Path) -> Path:
    """Claude'га юбориш учун кичрайтирилган JPEG."""
    out = path.with_name(path.stem + "_thumb.jpg")
    if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vf",
                        "scale='min(768,iw)':-2", "-q:v", "4", str(out)], check=True)
    return out


# ----------------------------- Видео -----------------------------

def motion_prompt(plan: SeriesPlan, shot: Shot, native_audio: bool, ambience: str = "") -> str:
    chars = {c.id: c for c in plan.characters}
    names = {c.id: f"{_label(c)} (the {_person(c)})" for c in plan.characters}
    parts = [f"{SHOT_WORDS.get(shot.shot_type, shot.shot_type).capitalize()}. {_sub_ids(shot.motion_prompt, names)}"]
    if shot.speaker_on_screen in chars:
        parts.append(f"{_label(chars[shot.speaker_on_screen])} is talking: natural mouth movement while "
                     "speaking, subtle facial expressions, natural blinking and small head movements.")
    parts.append("Keep the faces, costumes, lighting and setting exactly as in the image. Realistic natural "
                 f"human motion, physically plausible, cinematic. {plan.visual_style}")
    if native_audio:
        sound = shot.sound or ambience or "quiet natural room tone"
        parts.append(f"Audio: only natural diegetic sound — {sound}. No speech, no voices, no music.")
    parts.append("No text or subtitles on screen.")
    return " ".join(parts)


def make_clip(plan: SeriesPlan, shot: Shot, keyframe: Path, seconds: float, out: Path,
              native_audio: bool, ambience: str = "") -> Path:
    prompt = motion_prompt(plan, shot, native_audio, ambience)
    (out.parent / f"{out.stem}_prompt.txt").write_text(prompt, encoding="utf-8")
    result = fal_api.run(model("VIDEO_MODEL"), {
        "prompt": prompt,
        "image_url": fal_api.upload(keyframe),
        "duration": seconds,
        "aspect_ratio": "9:16",
        "resolution": os.environ.get("VIDEO_RESOLUTION", "1080p"),
        "generate_audio": native_audio,
        "negative_prompt": NEGATIVE,
    }, timeout_s=1800)
    return fal_api.download(fal_api.result_url(result, "video"), out)


def clip_seconds(needed: float) -> float:
    """Модел қабул қиладиган энг қисқа узунлик ≥ needed (номаълум бўлса — needed ни яхлитлаймиз)."""
    allowed = fal_api.allowed_durations(model("VIDEO_MODEL"))
    if allowed:
        bigger = [d for d in allowed if d >= needed - 0.01]
        return bigger[0] if bigger else allowed[-1]
    return float(min(15, max(4, int(needed + 0.99))))


def lipsync(video: Path, audio: Path, out: Path) -> Path:
    result = fal_api.run(model("LIPSYNC_MODEL"), {
        "video_url": fal_api.upload(video),
        "audio_url": fal_api.upload(audio),
    }, timeout_s=1800)
    return fal_api.download(fal_api.result_url(result, "video"), out)
