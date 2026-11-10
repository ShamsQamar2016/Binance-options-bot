"""Китобдан кундалик вертикал AI-сериал (рус дубляжи): ҳар куни бир қисм Telegram каналга.

Персонажлар ва атмосфера китобдан олинади (япон китоби — японлар ва Япония, Америка китоби — американлар
ва Америка), дубляж ва титрлар доим рус тилида. Формат: 9:16, 1080×1920 — YouTube Shorts, Instagram Reels.

Буйруқлар:
    python serial.py plan --book китоб.pdf --name my_serial      # 1. режа (персонажлар, жойлар, қисмлар)
    python serial.py plan --from-telegram --name my_serial        #    ёки ботга юборилган файлдан
    python serial.py refs                                         # 2. персонаж ва жой эталонлари → Telegram
    python serial.py voices                                       # 3. ҳар персонажга русча овоз → Telegram
    python serial.py storyboard                                   # 4. навбатдаги қисм раскадровкаси (арзон)
    python serial.py produce [--count 2] [--episode 3]            # 5. қисм(лар)ни тайёрлаш → сизга кўрсатиш
    python serial.py publish-next                                 #    навбатдаги тайёр қисмни каналга
    python serial.py daily                                        #    ҳар куни (cron / Task Scheduler)
    python serial.py status
    python serial.py check-models                                 #    fal.ai моделлари параметрларини кўриш
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

import telegram_sender as tg
from book_sources import download_from_telegram, download_from_url, load_text
from dubbing import build_voice_map
from episode_builder import EpisodeBuilder, ensure_references
from fileutil import PROBE_TIMEOUT, write_text_atomic
from series_planner import (EpisodeScript, SeriesPlan, long_speech_shots, make_segments, normalize_script,
                            plan_series, write_episode)

ROOT = Path("output/serials")
LOG_FILE = Path("output/serial.log")
logger = logging.getLogger("serial")


def setup_logging() -> None:
    """Журнални экранга ва output/serial.log файлга ёзади (cron ишлаганда из қолади)."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(logging.WARNING)  # экранда фақат огоҳлантиришлар, батафсили — журналда
    root.addHandler(file_handler)
    root.addHandler(console)


def telegram_on() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


# ----------------------------- Ҳолат (state) -----------------------------

class Serial:
    def __init__(self, folder: Path):
        self.dir = folder
        if not (folder / "plan.json").exists():
            raise SystemExit(f"Сериал топилмади: {folder} (аввал: python serial.py plan ...)")
        try:
            self.plan = SeriesPlan.model_validate_json((folder / "plan.json").read_text(encoding="utf-8"))
        except ValidationError as exc:
            raise SystemExit(
                f"{folder / 'plan.json'} эски форматда ёки бузилган. Янги режа тузинг: "
                f"python serial.py plan ... --name янги_ном\n{exc}"
            )
        self.segments: list[str] = json.loads((folder / "segments.json").read_text(encoding="utf-8"))
        self.settings: dict = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
        self.state_path = folder / "state.json"
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {"published": []}

    def save_state(self) -> None:
        write_text_atomic(self.state_path, json.dumps(self.state, ensure_ascii=False, indent=2))

    def ep_dir(self, n: int) -> Path:
        return self.dir / f"episode_{n:02d}"

    def is_ready(self, n: int) -> bool:
        return (self.ep_dir(n) / "episode.mp4").exists()

    def next_unpublished(self) -> int | None:
        done = {p["episode"] for p in self.state["published"]}
        for ep in self.plan.episodes:
            if ep.number not in done:
                return ep.number
        return None

    def voices(self, create: bool = True) -> dict:
        return build_voice_map(self.plan, self.dir / "voices.json", create=create,
                               previews_dir=self.dir / "voice_previews")

    def episode_plan(self, n: int):
        ep = next((e for e in self.plan.episodes if e.number == n), None)
        if ep is None:
            raise SystemExit(f"{n}-қисм режада йўқ (1–{len(self.plan.episodes)})")
        return ep


def pick_serial(name: str | None) -> Serial:
    if name:
        return Serial(ROOT / name)
    found = [p for p in ROOT.glob("*") if (p / "plan.json").exists()] if ROOT.exists() else []
    if len(found) != 1:
        raise SystemExit("Сериални --serial НОМ билан кўрсатинг. Мавжудлари: " + ", ".join(p.name for p in found))
    return Serial(found[0])


def _jpeg(path: Path, width: int = 1280) -> Path:
    """Telegram'га юбориш учун JPEG нусха (PNG эталонлар катта бўлиши мумкин)."""
    out = path.with_name(path.stem + "_tg.jpg")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vf", f"scale='min({width},iw)':-2",
                    "-q:v", "3", str(out)], check=True, timeout=PROBE_TIMEOUT)
    return out


# ----------------------------- Режа -----------------------------

def cmd_plan(args) -> None:
    folder = ROOT / args.name
    folder.mkdir(parents=True, exist_ok=True)

    if args.book:
        book_path = Path(args.book)
    elif args.url:
        print("⬇️  Китоб юклаб олинмоқда...")
        book_path = download_from_url(args.url, folder)
    else:
        print("⬇️  Telegram ботга юборилган китоб олинмоқда...")
        book_path = download_from_telegram(folder)

    text = load_text(book_path)
    segments = make_segments(text)
    print(f"📖 {book_path.name}: {len(text):,} белги, {len(segments)} бўлак")
    write_text_atomic(folder / "segments.json", json.dumps(segments, ensure_ascii=False))
    write_text_atomic(folder / "settings.json", json.dumps({
        "minutes": args.minutes, "music": args.music,
    }, ensure_ascii=False, indent=2))

    print("🤖 Claude бутун китобни ўқиб, сериал режасини тузмоқда (бир неча дақиқа)...")
    plan = plan_series(segments, args.minutes, args.episodes, args.wishes)
    write_text_atomic(folder / "plan.json", plan.model_dump_json(indent=2))

    serial = Serial(folder)
    serial.voices(create=False)  # voices.json (овозлар `voices` буйруғида яратилади)
    summary = format_plan(plan)
    print("\n" + summary)
    print(f"\n✓ Режа: {folder / 'plan.json'}"
          f"\nКейинги қадам: python serial.py refs  →  python serial.py voices  →  python serial.py storyboard")
    if not args.no_telegram and telegram_on():
        tg.send_text(summary)


def format_plan(plan: SeriesPlan) -> str:
    lines = [f"🎬 {plan.series_title}", f"📚 «{plan.original_title}», {plan.author}", plan.logline, "",
             f"🌍 {plan.country} · {plan.era}", "", "👥 Персонажлар:"]
    lines += [f"• {c.name} ({c.age}, {c.ethnicity}) — {c.role}" for c in plan.characters]
    lines += ["", "📍 Жойлар: " + ", ".join(loc.name for loc in plan.locations)]
    lines += ["", f"📺 Қисмлар ({len(plan.episodes)} та):"]
    lines += [f"{e.number}. {e.title} — {e.summary}" for e in plan.episodes]
    return "\n".join(lines)


# ----------------------------- Эталонлар ва овозлар -----------------------------

def _redo(value: str | None) -> set[str]:
    return {x.strip() for x in (value or "").split(",") if x.strip()}


def cmd_refs(args) -> None:
    serial = pick_serial(args.serial)
    items = ensure_references(serial.plan, serial.dir, _redo(args.redo))
    print(f"✓ Эталонлар: {serial.dir / 'refs'} ({len(items)} та)")
    if not args.no_telegram and telegram_on():
        tg.send_text("🖼 Персонаж ва жой эталонлари. Ёқмаганини қайта ясаш:\n"
                     "python serial.py refs --redo id1,id2  (id лар plan.json да)")
        tg.send_album([(_jpeg(p), caption) for caption, p in items])


def cmd_voices(args) -> None:
    serial = pick_serial(args.serial)
    path = serial.dir / "voices.json"
    redo = _redo(args.redo)
    if redo and path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in redo:
            if key in data:
                data[key]["voice_id"] = ""
        write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2))
    voices = serial.voices(create=True)
    print(f"✓ Овозлар: {path}")
    previews = serial.dir / "voice_previews"
    if not args.no_telegram and telegram_on():
        tg.send_text("🎙 Персонажлар овозлари. Ёқмаганини қайта ясаш: python serial.py voices --redo id\n"
                     "Ёки voices.json га ElevenLabs кутубхонасидан ўзингиз танлаган voice_id ни ёзинг.")
        for key, v in voices.items():
            sample = previews / f"{key}.mp3"
            if sample.exists() and (not redo or key in redo):
                tg.send_audio(sample, f"{v['name']} ({key})")


# ----------------------------- Қисм тайёрлаш -----------------------------

def load_script(serial: Serial, n: int) -> EpisodeScript:
    ep_plan = serial.episode_plan(n)
    ep_dir = serial.ep_dir(n)
    ep_dir.mkdir(parents=True, exist_ok=True)
    script_path = ep_dir / "script.json"
    if script_path.exists():
        try:
            script = EpisodeScript.model_validate_json(script_path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            raise SystemExit(
                f"{script_path} нотўғри ёки эски форматда. Хатони тузатинг ёки {ep_dir} папкасини бошқа номга "
                f"ўзгартириб, қайта ишга туширинг (сценарий янгидан ёзилади).\n{exc}"
            )
        # Қўлда таҳрирланган сценарий ҳам текширилади (номаълум id, кадр узунлиги ва ҳ.к.)
        script = normalize_script(script, serial.plan, n, renumber=False)
    else:
        print(f"✍️  {n}-қисм сценарийси ёзилмоқда...")
        prev = next((e for e in serial.plan.episodes if e.number == n - 1), None)
        prev_summary = f"{prev.summary} Финал: {prev.cliffhanger}" if prev else ""
        script = write_episode(serial.plan, ep_plan, serial.segments, serial.settings["minutes"], prev_summary)
        write_text_atomic(script_path, script.model_dump_json(indent=2))
    long_shots = long_speech_shots(script.model_dump())
    if long_shots:
        print("   ℹ️  Нутқи узун кадрлар (видео секинлашади ёки охирги кадр ушлаб турилади): "
              + ", ".join(f"{n_} ({s} с)" for n_, s in long_shots))
    return script


def format_script(script: EpisodeScript) -> str:
    lines = [f"📺 {script.number}-қисм «{script.title}»", ""]
    for s in script.shots:
        lines.append(f"{s.number}. [{s.shot_type}] {s.description}")
        for line in s.lines:
            lines.append(f"   — {line.speaker}: {line.text}")
    return "\n".join(lines)


def cmd_storyboard(args) -> None:
    serial = pick_serial(args.serial)
    n = args.episode or serial.next_unpublished()
    if n is None:
        print("Барча қисмлар чиқарилган.")
        return
    script = load_script(serial, n)
    ensure_references(serial.plan, serial.dir)
    builder = EpisodeBuilder(serial.plan, serial.voices(create=False), serial.dir, serial.ep_dir(n))
    print(f"🖼  {n}-қисм раскадровкаси ({len(script.shots)} кадр)...")
    sheet = builder.storyboard(script)
    print(f"✓ {sheet}")
    if not args.no_telegram and telegram_on():
        tg.send_photo(_jpeg(sheet, 1620), f"🎞 {n}-қисм раскадровкаси. Ёқмаган кадр расмини ўчиринг: "
                                          f"episode_{n:02d}/clips/shot_NN.png ва қайта ишга туширинг")
        tg.send_text(format_script(script))


def write_post(serial: Serial, n: int, script: EpisodeScript) -> Path:
    """YouTube Shorts ва Instagram Reels учун тайёр сарлавҳа ва тавсиф."""
    plan = serial.plan
    tags = " ".join("#" + re.sub(r"\W+", "", w) for w in ["сериал", "кино", plan.series_title.split()[0]] if w)
    text = (
        f"YouTube сарлавҳа:\n{plan.series_title} — Серия {n}: {script.title} #shorts\n\n"
        f"Тавсиф (YouTube ва Instagram):\n{script.recap}\n\n{script.next_episode_teaser}\n\n"
        f"По мотивам книги «{plan.original_title}», {plan.author}.\n{tags}\n"
    )
    path = serial.ep_dir(n) / "post.txt"
    path.write_text(text, encoding="utf-8")
    return path


def produce_episode(serial: Serial, n: int, preview: bool = True) -> Path:
    script = load_script(serial, n)
    ensure_references(serial.plan, serial.dir)
    builder = EpisodeBuilder(serial.plan, serial.voices(create=True), serial.dir, serial.ep_dir(n))
    print(f"🎬 {n}-қисм йиғилмоқда ({len(script.shots)} кадр)...")
    music = serial.settings.get("music") or os.environ.get("BACKGROUND_MUSIC")
    video = builder.build(script, is_last=n == serial.plan.episodes[-1].number,
                          music_file=Path(music) if music else None)
    write_post(serial, n, script)
    print(f"   ✓ Тайёр: {video}")
    logger.info("%s-қисм тайёр: %s", n, video)

    if preview and telegram_on():
        from video import compress_for_telegram
        tg.send_video(compress_for_telegram(video), caption=f"👀 Олдиндан кўриш: {n}-қисм «{script.title}»")
    return video


def cmd_produce(args) -> None:
    serial = pick_serial(args.serial)
    if args.episode:
        produce_episode(serial, args.episode, preview=not args.no_telegram)
        return
    start = serial.next_unpublished()
    if start is None:
        print("Барча қисмлар чиқарилган.")
        return
    todo = [e.number for e in serial.plan.episodes if e.number >= start and not serial.is_ready(e.number)][: args.count]
    for n in todo:
        produce_episode(serial, n, preview=not args.no_telegram)


# ----------------------------- Чиқариш -----------------------------

def caption_for(serial: Serial, n: int) -> str:
    script = EpisodeScript.model_validate_json((serial.ep_dir(n) / "script.json").read_text(encoding="utf-8"))
    total = len(serial.plan.episodes)
    text = (f"🎬 {serial.plan.series_title}\n📺 Серия {n}. «{script.title}»\n\n"
            f"{script.recap}\n\n{script.next_episode_teaser}")
    if n < total:
        when = os.environ.get("PUBLISH_TIME")
        text += f"\n\n⏰ Серия {n + 1} — завтра" + (f" в {when}" if when else "") + "!"
    else:
        text += "\n\n🏁 Последняя серия. Спасибо, что смотрели!"
    return text


def publish(serial: Serial, n: int) -> None:
    from video import compress_for_telegram
    video = compress_for_telegram(serial.ep_dir(n) / "episode.mp4")
    result = tg.send_video(video, caption=caption_for(serial, n), chat_id=tg.channel())
    serial.state["published"].append({"episode": n, "at": datetime.now().isoformat(timespec="seconds"),
                                      "message_id": result.get("message_id")})
    serial.save_state()
    print(f"📢 {n}-қисм каналга чиқарилди")
    logger.info("%s-қисм каналга чиқарилди (message_id=%s)", n, result.get("message_id"))


def cmd_publish_next(args) -> None:
    serial = pick_serial(args.serial)
    n = serial.next_unpublished()
    if n is None:
        print("Барча қисмлар чиқарилган.")
    elif not serial.is_ready(n):
        raise SystemExit(f"{n}-қисм ҳали тайёр эмас: python serial.py produce")
    else:
        publish(serial, n)


def cmd_daily(args) -> None:
    """Ҳар куни: навбатдаги қисмни чиқариш, кейин эртанги қисмни олдиндан тайёрлаш."""
    serial = pick_serial(args.serial)
    n = serial.next_unpublished()
    if n is None:
        print("Сериал тугаган.")
        return
    current = n
    try:
        if not serial.is_ready(n):
            produce_episode(serial, n, preview=False)
        publish(serial, n)
        # Эртанги қисмни ҳозирдан тайёрлаймиз — админ олдиндан кўриб чиқади
        for ahead in range(n + 1, n + 1 + args.ahead):
            current = ahead
            if any(e.number == ahead for e in serial.plan.episodes) and not serial.is_ready(ahead):
                produce_episode(serial, ahead, preview=True)
    except (Exception, SystemExit) as exc:  # админни огоҳлантириш
        logger.exception("Кундалик иш хатоси (%s-қисм)", current)
        if telegram_on():
            tg.send_text(f"⚠️ Сериал хатоси ({current}-қисм): {exc}"[:3000])
        raise


def cmd_status(args) -> None:
    serial = pick_serial(args.serial)
    published = {p["episode"] for p in serial.state["published"]}
    refs = serial.dir / "refs"
    n_refs = len(list(refs.glob("*.png"))) if refs.exists() else 0
    voices = json.loads((serial.dir / "voices.json").read_text(encoding="utf-8")) if (serial.dir / "voices.json").exists() else {}
    print(f"🎬 {serial.plan.series_title}  ({serial.plan.country}, {serial.plan.era})")
    print(f"   эталонлар: {n_refs}/{len(serial.plan.characters) + len(serial.plan.locations)}, "
          f"овозлар: {sum(1 for v in voices.values() if v.get('voice_id'))}/{len(serial.plan.characters) + 1}")
    for e in serial.plan.episodes:
        mark = "📢 чиқди" if e.number in published else ("✅ тайёр" if serial.is_ready(e.number) else "⏳")
        print(f"  {e.number:>2}. {mark:<9} {e.title}")


def cmd_check_models(args) -> None:
    import fal_api
    import visuals
    for name in ("IMAGE_MODEL", "IMAGE_EDIT_MODEL", "VIDEO_MODEL", "LIPSYNC_MODEL"):
        print(f"[{name}] " + fal_api.describe(visuals.model(name)) + "\n")


def main() -> int:
    load_dotenv()
    setup_logging()
    parser = argparse.ArgumentParser(description="Китобдан кундалик вертикал AI-сериал (рус дубляжи)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="Китобни ўқиб сериал режасини тузиш")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--book", help="Китоб файли (.pdf .docx .fb2 .epub .txt)")
    src.add_argument("--url", help="Китоб файлига тўғридан-тўғри ҳавола")
    src.add_argument("--from-telegram", action="store_true", help="Ботга юборилган охирги файл")
    p.add_argument("--name", required=True, help="Сериал папкаси номи (лотинча), мас. snow_country")
    p.add_argument("--minutes", type=float, default=2.0, help="Ҳар қисм узунлиги, дақиқа (стандарт 2, кўпи билан 2.8)")
    p.add_argument("--episodes", type=int, help="Қисмлар сони (бермасангиз Claude ўзи танлайди)")
    p.add_argument("--music", help="Ўз мусиқангиз (mp3) — бўлмаса ҳар қисмга мусиқа басталанади")
    p.add_argument("--wishes", default="", help="Қўшимча истаклар")
    p.add_argument("--no-telegram", action="store_true")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("refs", help="Персонаж ва жой эталон расмлари")
    p.add_argument("--serial")
    p.add_argument("--redo", help="Қайта ясаш: id лар вергул билан (мас. kenji,tea_house)")
    p.add_argument("--no-telegram", action="store_true")
    p.set_defaults(func=cmd_refs)

    p = sub.add_parser("voices", help="Персонажларга русча овоз яратиш")
    p.add_argument("--serial")
    p.add_argument("--redo", help="Қайта яратиш: id лар вергул билан (мас. kenji,narrator)")
    p.add_argument("--no-telegram", action="store_true")
    p.set_defaults(func=cmd_voices)

    p = sub.add_parser("storyboard", help="Қисм раскадровкаси (фақат калит расмлар)")
    p.add_argument("--serial")
    p.add_argument("--episode", type=int)
    p.add_argument("--no-telegram", action="store_true")
    p.set_defaults(func=cmd_storyboard)

    p = sub.add_parser("produce", help="Навбатдаги қисм(лар)ни тайёрлаш")
    p.add_argument("--serial")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--episode", type=int, help="Аниқ бир қисмни (қайта) тайёрлаш")
    p.add_argument("--no-telegram", action="store_true", help="Админга олдиндан кўришни юбормаслик")
    p.set_defaults(func=cmd_produce)

    p = sub.add_parser("publish-next", help="Навбатдаги тайёр қисмни каналга чиқариш")
    p.add_argument("--serial")
    p.set_defaults(func=cmd_publish_next)

    p = sub.add_parser("daily", help="Кундалик: чиқариш + эртангисини тайёрлаш (cron учун)")
    p.add_argument("--serial")
    p.add_argument("--ahead", type=int, default=1, help="Нечта қисм олдиндан тайёр турсин")
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("status", help="Қисмлар ҳолати")
    p.add_argument("--serial")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("check-models", help="fal.ai моделлари қабул қиладиган параметрлар")
    p.set_defaults(func=cmd_check_models)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
