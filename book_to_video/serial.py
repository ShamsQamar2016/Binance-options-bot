"""Китобдан кундалик AI-сериал: ҳар куни бир қисм Telegram каналга.

Буйруқлар:
    python serial.py plan --book китоб.pdf --name ikki_eshik --minutes 2
    python serial.py plan --url https://.../kitob.pdf --name ...
    python serial.py plan --from-telegram --name ...      # ботга юборилган файлдан
    python serial.py produce [--count 2] [--episode 3]    # қисм(лар) тайёрлаш, админга олдиндан кўрсатиш
    python serial.py publish-next                         # навбатдаги тайёр қисмни каналга
    python serial.py daily                                # ҳар куни cron/Task Scheduler орқали
    python serial.py status
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import telegram_sender as tg
from book_sources import download_from_telegram, download_from_url, load_text
from dubbing import build_voice_map
from episode_builder import EpisodeBuilder
from series_planner import EpisodeScript, SeriesPlan, make_segments, plan_series, write_episode

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
    root.addHandler(file_handler)
    root.addHandler(console)


# ----------------------------- Ҳолат (state) -----------------------------

class Serial:
    def __init__(self, folder: Path):
        self.dir = folder
        self.plan = SeriesPlan.model_validate_json((folder / "plan.json").read_text(encoding="utf-8"))
        self.segments: list[str] = json.loads((folder / "segments.json").read_text(encoding="utf-8"))
        self.settings: dict = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
        self.state_path = folder / "state.json"
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {"published": []}

    def save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

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

    def voices(self) -> dict:
        return build_voice_map(self.plan, self.dir / "voices.json")


def pick_serial(name: str | None) -> Serial:
    if name:
        return Serial(ROOT / name)
    found = [p for p in ROOT.glob("*") if (p / "plan.json").exists()] if ROOT.exists() else []
    if len(found) != 1:
        raise SystemExit("Сериални --serial НОМ билан кўрсатинг. Мавжудлари: " + ", ".join(p.name for p in found))
    return Serial(found[0])


# ----------------------------- Буйруқлар -----------------------------

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
    (folder / "segments.json").write_text(json.dumps(segments, ensure_ascii=False), encoding="utf-8")
    (folder / "settings.json").write_text(json.dumps({
        "minutes": args.minutes, "aspect": args.aspect, "music": args.music,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("🤖 Claude бутун китобни ўқиб, сериал режасини тузмоқда (бир неча дақиқа)...")
    plan = plan_series(segments, args.minutes, args.episodes, args.wishes)
    (folder / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    serial = Serial(folder)
    serial.voices()  # voices.json
    summary = format_plan(plan)
    print("\n" + summary)
    print(f"\n✓ Режа: {folder / 'plan.json'}\n✓ Овозлар: {folder / 'voices.json'} (керак бўлса таҳрирланг)")
    if not args.no_telegram:
        tg.send_text(summary)


def format_plan(plan: SeriesPlan) -> str:
    lines = [f"🎬 {plan.series_title}", plan.logline, "", "👥 Персонажлар:"]
    lines += [f"• {c.name} — {c.role}" for c in plan.characters]
    lines += ["", f"📺 Қисмлар ({len(plan.episodes)} та):"]
    lines += [f"{e.number}. {e.title} — {e.summary}" for e in plan.episodes]
    return "\n".join(lines)


def produce_episode(serial: Serial, n: int, preview: bool = True) -> Path:
    plan = serial.plan
    ep_plan = next(e for e in plan.episodes if e.number == n)
    ep_dir = serial.ep_dir(n)
    ep_dir.mkdir(parents=True, exist_ok=True)
    minutes = serial.settings["minutes"]

    # Тил назорати: қисм бир тилда ясалгач, бошқа тилда аралаштирилмайди
    lang = os.environ.get("DUB_LANGUAGE", "ru").lower()
    marker = ep_dir / "dub_language.txt"
    script_path = ep_dir / "script.json"
    if marker.exists():
        made_in = marker.read_text(encoding="utf-8").strip()
        if made_in != lang:
            raise SystemExit(
                f"{n}-қисм «{made_in}» тилида ясалган, ҳозирги тил «{lang}». "
                f"Аралашмаслиги учун {ep_dir} папкасини бошқа номга ўзгартириб қайта ишга туширинг."
            )
    elif script_path.exists():
        raise SystemExit(
            f"{ep_dir} папкасида тил маркери йўқ (эски қисм, тили номаълум). "
            "Уни бошқа номга ўзгартириб қайта ишга туширинг."
        )
    else:
        marker.write_text(lang, encoding="utf-8")

    if script_path.exists():
        script = EpisodeScript.model_validate_json(script_path.read_text(encoding="utf-8"))
    else:
        print(f"✍️  {n}-қисм сценарийси ёзилмоқда...")
        prev = next((e for e in plan.episodes if e.number == n - 1), None)
        prev_summary = f"{prev.summary} Якуни: {prev.cliffhanger}" if prev else ""
        script = write_episode(plan, ep_plan, serial.segments, minutes, prev_summary)
        script_path.write_text(script.model_dump_json(indent=2), encoding="utf-8")

    print(f"🎬 {n}-қисм йиғилмоқда ({len(script.shots)} кадр)...")
    music = serial.settings.get("music") or os.environ.get("BACKGROUND_MUSIC")
    builder = EpisodeBuilder(plan, serial.voices(), ep_dir, serial.settings.get("aspect", "16:9"))
    video = builder.build(script, Path(music) if music else None)
    print(f"   ✓ Тайёр: {video}")
    logger.info("%s-қисм тайёр: %s", n, video)

    if preview and os.environ.get("TELEGRAM_BOT_TOKEN"):
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


def caption_for(serial: Serial, n: int) -> str:
    script = EpisodeScript.model_validate_json((serial.ep_dir(n) / "script.json").read_text(encoding="utf-8"))
    total = len(serial.plan.episodes)
    text = f"🎬 {serial.plan.series_title}\n📺 {n}-қисм. «{script.title}»\n\n{script.next_episode_teaser}"
    if n < total:
        when = os.environ.get("PUBLISH_TIME")
        text += f"\n\n⏰ {n + 1}-қисм эртага" + (f" соат {when} да" if when else "") + "!"
    else:
        text += "\n\n🏁 Сўнгги қисм. Томоша қилганингиз учун раҳмат!"
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
    try:
        if not serial.is_ready(n):
            produce_episode(serial, n, preview=False)
        publish(serial, n)
        # Эртанги қисмни ҳозирдан тайёрлаймиз — админ олдиндан кўриб чиқади
        for ahead in range(n + 1, n + 1 + args.ahead):
            if any(e.number == ahead for e in serial.plan.episodes) and not serial.is_ready(ahead):
                produce_episode(serial, ahead, preview=True)
    except Exception as exc:  # админни огоҳлантириш
        logger.exception("Кундалик иш хатоси (%s-қисм)", n)
        if os.environ.get("TELEGRAM_BOT_TOKEN"):
            tg.send_text(f"⚠️ Сериал хатоси ({n}-қисм): {exc}"[:3000])
        raise


def cmd_status(args) -> None:
    serial = pick_serial(args.serial)
    published = {p["episode"] for p in serial.state["published"]}
    print(f"🎬 {serial.plan.series_title}")
    for e in serial.plan.episodes:
        mark = "📢 чиқди" if e.number in published else ("✅ тайёр" if serial.is_ready(e.number) else "⏳")
        print(f"  {e.number:>2}. {mark:<9} {e.title}")


def main() -> int:
    load_dotenv()
    setup_logging()
    parser = argparse.ArgumentParser(description="Китобдан кундалик AI-сериал")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="Китобни ўқиб сериал режасини тузиш")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--book", help="Китоб файли (.pdf .docx .fb2 .epub .txt)")
    src.add_argument("--url", help="Китоб файлига тўғридан-тўғри ҳавола")
    src.add_argument("--from-telegram", action="store_true", help="Ботга юборилган охирги файл")
    p.add_argument("--name", required=True, help="Сериал папкаси номи (лотинча), мас. ikki_eshik_orasi")
    p.add_argument("--minutes", type=float, default=2.0, help="Ҳар қисм узунлиги, дақиқа (стандарт 2)")
    p.add_argument("--episodes", type=int, help="Қисмлар сони (бермасангиз Claude ўзи танлайди)")
    p.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1"])
    p.add_argument("--music", help="Фон мусиқаси (mp3) — ҳуқуқи ўзингизда бўлган файл")
    p.add_argument("--wishes", default="", help="Қўшимча истаклар")
    p.add_argument("--no-telegram", action="store_true")
    p.set_defaults(func=cmd_plan)

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

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
