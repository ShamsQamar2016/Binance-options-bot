"""Китоб → Claude сценарий → видео клиплар → трейлер → Telegram

Ишлатиш:
    python main.py китоб.pdf                    # тўлиқ жараён
    python main.py китоб.txt --script-only      # фақат сценарий (видеосиз, арзон синов)
    python main.py китоб.docx --scenes 8 --no-telegram
    python main.py --from-script output/китоб/script.json   # тайёр сценарийдан видео
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from book_reader import read_book
from scenario import TrailerScript, create_trailer_script
from video import compress_for_telegram, concat_clips, generate_clip
import telegram_sender as tg


def format_script(script: TrailerScript) -> str:
    lines = [f"🎬 {script.book_title}", f"💡 {script.logline}", ""]
    for s in script.scenes:
        lines += [f"{s.number}. {s.title} ({s.duration_seconds}с)", f"   {s.narration}", ""]
    return "\n".join(lines)


def build_video(script: TrailerScript, out_dir: Path, aspect_ratio: str) -> Path:
    clips: list[Path] = []
    for scene in script.scenes:
        clip_path = out_dir / f"scene_{scene.number:02d}.mp4"
        if clip_path.exists():  # қайта ишга туширилганда тайёр клипларни ўтказиб юборади
            print(f"  ✓ Саҳна {scene.number} аввал тайёрланган")
        else:
            print(f"  ⏳ Саҳна {scene.number}/{len(script.scenes)}: {scene.title}")
            prompt = f"{scene.video_prompt}\n\nStyle: {script.visual_style}\nCharacters: {script.characters}"
            generate_clip(prompt, clip_path, duration=scene.duration_seconds, aspect_ratio=aspect_ratio)
        clips.append(clip_path)

    trailer = out_dir / "trailer.mp4"
    print("  🎞  Клиплар бирлаштирилмоқда...")
    concat_clips(clips, trailer)
    return trailer


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Китобдан AI трейлер ясаш ва Telegram га юбориш")
    parser.add_argument("book", nargs="?", help="Китоб файли (.txt, .pdf, .docx)")
    parser.add_argument("--from-script", help="Тайёр script.json дан давом этиш")
    parser.add_argument("--scenes", type=int, default=6, help="Саҳналар сони (стандарт: 6)")
    parser.add_argument("--wishes", default="", help="Қўшимча истаклар, мас. 'қоронғи, триллер услубида'")
    parser.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1"], help="9:16 — Reels/Shorts учун")
    parser.add_argument("--script-only", action="store_true", help="Фақат сценарий яратиш, видеосиз")
    parser.add_argument("--no-telegram", action="store_true", help="Telegram га юбормаслик")
    parser.add_argument("--out", default="output", help="Натижалар папкаси")
    args = parser.parse_args()

    if not args.book and not args.from_script:
        parser.error("китоб файли ёки --from-script кўрсатинг")

    # 1) Сценарий
    if args.from_script:
        script_path = Path(args.from_script)
        script = TrailerScript.model_validate_json(script_path.read_text(encoding="utf-8"))
        out_dir = script_path.parent
    else:
        book_path = Path(args.book)
        out_dir = Path(args.out) / book_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"📖 Китоб ўқилмоқда: {book_path.name}")
        text = read_book(book_path)
        print(f"   {len(text):,} белги")

        print("🤖 Claude сценарий ёзмоқда (бир неча дақиқа кетиши мумкин)...")
        script = create_trailer_script(text, num_scenes=args.scenes, extra_wishes=args.wishes)

        script_path = out_dir / "script.json"
        script_path.write_text(script.model_dump_json(indent=2), encoding="utf-8")
        (out_dir / "script.txt").write_text(script.full_script, encoding="utf-8")
        print(f"   ✓ Сценарий сақланди: {script_path}")

    summary = format_script(script)
    print("\n" + summary)

    if args.script_only:
        if not args.no_telegram:
            tg.send_text(summary)
            tg.send_document(out_dir / "script.txt", caption="📝 Тўлиқ сценарий")
            print("📨 Сценарий Telegram га юборилди")
        return 0

    # 2) Видео
    print("🎥 Видео клиплар генерация қилинмоқда...")
    trailer = build_video(script, out_dir, args.aspect)
    print(f"   ✓ Трейлер тайёр: {trailer}")

    # 3) Telegram
    if not args.no_telegram:
        print("📨 Telegram га юборилмоқда...")
        tg.send_video(compress_for_telegram(trailer), caption=f"🎬 {script.book_title}\n{script.logline}")
        tg.send_text(summary)
        print("   ✓ Юборилди")

    return 0


if __name__ == "__main__":
    sys.exit(main())
