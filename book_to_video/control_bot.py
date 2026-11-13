"""Telegram орқали бошқариладиган назоратчи бот.

Ишлатиш (сизнинг компьютерингизда, лойиҳа папкасидан):
    python control_bot.py --serial wuthering_full

Буйруқлар (фақат TELEGRAM_CHAT_ID дан келганлари қабул қилинади):
    /help                 — рўйхат
    /status               — қисмлар ҳолати
    /use ИСМ              — ишлайдиган сериални танлаш
    /mavzu ИСМ МАВЗУ      — мавзу асосида режа тузиш (тасдиқ билан)
    /plan ИСМ             — китоб файлини юборишни сўраш; кейин файлни юборинг (тасдиқ билан)
    /plan_show            — режани кўриш
    /storyboard [N]       — N-қисм раскадровкасини расм ва сценарий билан юбориш
    /produce [N]          — N-қисмни видеога йиғиш (тасдиқ билан)
    /publish              — тайёр қисмни каналга чиқариш (тасдиқ билан)
    /ha                   — сўралган ишни тасдиқлаш

Пулли ишлар (режа, видео, чиқариш) фақат /ha билан бажарилади.
Бот ҳамма ишни serial.py буйруқлари орқали бажаради; серия файлларини ўзи бузмайди.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

import telegram_sender as tg
from book_sources import safe_filename

LOG_FILE = Path("output/control_bot.log")
ROOT = Path("output/serials")
POLL_TIMEOUT = 50
CONFIRM_WINDOW = 600           # тасдиқ ва китоб кутиш 10 дақиқа амал қилади
MAX_FILE = 20 * 1024 * 1024    # Telegram бот API лимити
EPISODES = int(os.environ.get("BOT_EPISODES", "12"))
MINUTES = os.environ.get("BOT_MINUTES", "2")

# Вақтинчалик хатолар: қайта уриш фойда беради (пул такрорланмайди — fal_api журнали бор)
TRANSIENT = [
    r"ConnectTimeout", r"ConnectError", r"ConnectionError", r"NameResolutionError",
    r"Invalid storage type", r"HTTP 429", r"HTTP 5\d\d", r"ReadTimeout", r"Timeout",
]
# Қайта уриш ёрдам бермайдиган хатолар — сабабини тушунтирамиз
PERMANENT_HINTS = {
    r"voice_limit_reached": "ElevenLabs овоз лимити тугади. Янги овоз учун voices.json га тайёр voice_id ёзинг.",
    r"credit balance is too low": "Anthropic ҳисобида кредит тугади. console.anthropic.com → Plans & Billing.",
    r"exhausted balance|insufficient": "fal.ai ҳисобида маблағ тугади. fal.ai/dashboard/billing да тўлдиринг.",
    r"no_media_generated": "Модель бу кадрни рад этди (хавфсизлик фильтри). Кадр тавсифини юмшатиш керак.",
    r"blocked_generation|403": "ElevenLabs матнни рад этди (хавфсизлик қоидаси). Овоз тавсифини ёки матнни ўзгартиринг.",
    r"Unauthorized|Authentication is required|401": "Калит нотўғри. .env даги калитни текширинг.",
}


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()])


def explain(output: str) -> str:
    for pattern, hint in PERMANENT_HINTS.items():
        if re.search(pattern, output, re.I):
            return hint
    return "Номаълум хато. Батафсил: output/control_bot.log"


def is_transient(output: str) -> bool:
    if any(re.search(p, output, re.I) for p in PERMANENT_HINTS):
        return False
    return any(re.search(p, output) for p in TRANSIENT)


def run_serial(args: list[str], timeout: int = 4 * 3600) -> tuple[int, str]:
    """serial.py буйругини ишга туширади; (код, чиқиш охирги 6000 белгиси)."""
    proc = subprocess.run([sys.executable, "serial.py", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    logging.info("serial.py %s → код %s", " ".join(args), proc.returncode)
    return proc.returncode, out[-6000:]


def plan_text(serial: str) -> str:
    p = json.loads((ROOT / serial / "plan.json").read_text(encoding="utf-8"))
    lines = [f"🎬 {p.get('series_title', '')}",
             f"📚 «{p.get('original_title', '')}», {p.get('author', '')}",
             p.get("logline", ""), "",
             f"🌍 {p.get('country', '')} · {p.get('era', '')}", "", "👥 Персонажлар:"]
    lines += [f"• {c['name']} ({c['age']}) — {c['role']}" for c in p.get("characters", [])]
    lines += ["", f"📺 Қисмлар ({len(p.get('episodes', []))} та):"]
    lines += [f"{e['number']}. {e['title']} — {e['summary']}" for e in p.get("episodes", [])]
    return "\n".join(lines)


def script_text(serial: str, n: int) -> str:
    s = json.loads((ROOT / serial / f"episode_{n:02d}" / "script.json").read_text(encoding="utf-8"))
    lines = [f"📺 {s['number']}-қисм «{s['title']}»", ""]
    for sh in s["shots"]:
        lines.append(f"{sh['number']}. [{sh['shot_type']}] {sh['description']}")
        lines += [f"   — {ln['speaker']}: {ln['text']}" for ln in sh["lines"]]
    return "\n".join(lines)


class Bot:
    def __init__(self, token: str, chat: str, serial: str):
        self.token = token
        self.chat = str(chat)
        self.active = serial
        self.pending: tuple | None = None        # (иш, аргументлар, тугаш вақти)
        self.waiting_book: tuple | None = None   # (сериал номи, тугаш вақти)
        self.offset: int | None = None

    # ---- Telegram ----
    def say(self, text: str) -> None:
        for start in range(0, len(text), 3900):
            tg.send_text(text[start:start + 3900], chat_id=self.chat)

    def updates(self) -> list[dict]:
        params = {"timeout": POLL_TIMEOUT, "allowed_updates": '["message"]'}
        if self.offset is not None:
            params["offset"] = self.offset
        r = requests.get(f"https://api.telegram.org/bot{self.token}/getUpdates",
                         params=params, timeout=POLL_TIMEOUT + 15)
        body = r.json()
        return body.get("result", []) if body.get("ok") else []

    # ---- буйруқлар ----
    def handle(self, msg: dict) -> None:
        if msg.get("document"):
            return self.on_document(msg["document"])
        text = (msg.get("text") or "").strip()
        cmd, _, arg = text.partition(" ")
        cmd = cmd.lower().split("@")[0]
        arg = arg.strip()
        now = time.time()

        if cmd in ("/start", "/help"):
            self.say("/status — ҳолат\n/use ИСМ — сериални танлаш\n"
                     "/mavzu ИСМ МАВЗУ — мавзу асосида режа\n/plan ИСМ — китоб файлидан режа\n"
                     "/plan_show — режа\n/storyboard [N] — раскадровка расм билан\n"
                     "/produce [N] — видеога йиғиш\n/publish — каналга чиқариш\n/ha — тасдиқ")
        elif cmd == "/status":
            _, out = run_serial(["status", "--serial", self.active])
            self.say(out.strip() or "Маълумот йўқ")
        elif cmd == "/use" and arg:
            self.active = arg
            self.say(f"Фаол сериал: {arg}")
        elif cmd == "/mavzu":
            name, _, topic = arg.partition(" ")
            if not name or not topic.strip():
                return self.say("Ёзинг: /mavzu ИСМ МАВЗУ\nМас: /mavzu kizil_botqoq детектив, 1920 Лондон")
            self.pending = ("plan_topic", (name, topic.strip()), now + CONFIRM_WINDOW)
            self.say(f"Мавзу асосида «{name}» режасини тузаймиз (Claude'га пул кетади, тахминан $1–3).\n"
                     "Тасдиқ учун /ha ёзинг (10 дақиқа).")
        elif cmd == "/plan" and arg:
            self.waiting_book = (arg, now + CONFIRM_WINDOW)
            self.say(f"«{arg}» учун китоб файлини юборинг (PDF, EPUB, FB2, DOCX, TXT; 20 МБ гача).\n"
                     "Муаллифи 70 йилдан олдин вафот этган китоб бўлсин.")
        elif cmd == "/plan":
            self.say("Ёзинг: /plan ИСМ")
        elif cmd == "/plan_show":
            try:
                self.say(plan_text(self.active))
            except FileNotFoundError:
                self.say("Режа топилмади. /mavzu ёки /plan билан тузинг.")
        elif cmd == "/storyboard":
            n = int(arg) if arg.isdigit() else 1
            code, out = run_serial(["storyboard", "--serial", self.active, "--episode", str(n), "--no-telegram"])
            if code != 0:
                return self.say(f"❌ Раскадровка тугамади: {explain(out)}")
            sheet = ROOT / self.active / f"episode_{n:02d}" / "storyboard.jpg"
            try:
                tg.send_photo(sheet, caption=f"🎞 {n}-қисм раскадровкаси", chat_id=self.chat)
            except Exception as exc:
                self.say(f"Расмни юбориш мумкин эмас: {exc}")
            self.say(script_text(self.active, n))
            self.say("Ёқмаган кадр бўлса, ёзинг. Ҳаммаси маъқул бўлса: /produce " + str(n))
        elif cmd == "/produce":
            n = int(arg) if arg.isdigit() else 1
            self.pending = ("produce", (n,), now + CONFIRM_WINDOW)
            self.say(f"{n}-қисмни видеога йиғамиз (fal.ai'га тахминан $35–50). Тасдиқ: /ha")
        elif cmd == "/publish":
            self.pending = ("publish", (), now + CONFIRM_WINDOW)
            self.say("Навбатдаги тайёр қисмни каналга чиқарамизми? Тасдиқ: /ha")
        elif cmd == "/ha":
            self.confirm()
        else:
            self.say("Номаълум буйруқ. /help")

    def on_document(self, doc: dict) -> None:
        if not self.waiting_book or time.time() > self.waiting_book[1]:
            return self.say("Китоб қабул қилиш учун аввал /plan ИСМ ёзинг.")
        name, _ = self.waiting_book
        self.waiting_book = None
        if doc.get("file_size", 0) > MAX_FILE:
            return self.say("Файл 20 МБ дан катта. Бот қабул қила олмайди.")
        dest = ROOT / name / safe_filename(doc.get("file_name", ""), "book.txt")
        tg.download_file(doc["file_id"], dest)
        self.pending = ("plan_book", (name, str(dest)), time.time() + CONFIRM_WINDOW)
        self.say(f"Китоб қабул қилинди: {dest.name}.\nРежа тузиш учун /ha ёзинг (Claude'га пул кетади).")

    # ---- тасдиқланган ишлар ----
    def confirm(self) -> None:
        if not self.pending or time.time() > self.pending[2]:
            return self.say("Тасдиқланадиган иш йўқ ёки муддати ўтган.")
        action, args, _ = self.pending
        self.pending = None
        if action in ("plan_topic", "plan_book"):
            name, src = args
            flag = ["--topic", src] if action == "plan_topic" else ["--book", src]
            self.say("⏳ Режа тузилмоқда... (бир неча дақиқа)")
            code, out = run_serial(["plan", *flag, "--name", name, "--episodes", str(EPISODES),
                                    "--minutes", MINUTES, "--no-telegram"])
            if code != 0:
                return self.say(f"❌ Режа тузилмади: {explain(out)}")
            self.active = name
            self.say(plan_text(name))
            self.say(f"✅ Режа тайёр ва сақланди. Текшириб, раскадровка: /storyboard 1")
        elif action == "produce":
            self.produce(args[0])
        elif action == "publish":
            code, out = run_serial(["publish-next", "--serial", self.active])
            self.say("📢 Каналга чиқарилди." if code == 0 else f"❌ {explain(out)}")

    def produce(self, n: int, attempts: int = 4) -> None:
        for attempt in range(1, attempts + 1):
            self.say(f"⏳ {n}-қисм йиғилмоқда (уриниш {attempt}/{attempts}). Тугагач хабар бераман.")
            code, out = run_serial(["produce", "--serial", self.active, "--episode", str(n), "--no-telegram"])
            if code == 0:
                self.say(f"✅ {n}-қисм тайёр: output\\serials\\{self.active}\\episode_{n:02d}\\episode.mp4\n"
                         "Каналга чиқариш учун /publish.")
                return
            if is_transient(out) and attempt < attempts:
                wait = 60 * attempt
                self.say(f"⚠️ Вақтинчалик хато. {wait} сониядан кейин автоматик қайта урилади.")
                time.sleep(wait)
                continue
            last = out.strip().splitlines()[-1][:600] if out.strip() else "—"
            return self.say(f"❌ Тўхтади.\nСабаб: {explain(out)}\n\n{last}")


def main() -> int:
    load_dotenv()
    setup_logging()
    parser = argparse.ArgumentParser(description="Telegram назоратчи бот")
    parser.add_argument("--serial", required=True, help="Фаол сериал папкаси, мас. wuthering_full")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_BOT_TOKEN ва TELEGRAM_CHAT_ID .env да бўлиши керак")
    bot = Bot(token, chat, args.serial)
    bot.say(f"🤖 Бот ишга тушди. Фаол сериал: {args.serial}. Буйруқлар: /help")

    while True:
        try:
            updates = bot.updates()
        except requests.RequestException as exc:
            logging.warning("Telegram уланиш хатоси: %s", exc)
            time.sleep(10)
            continue
        for upd in updates:
            bot.offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != bot.chat:
                continue  # бошқаларнинг буйруқлари қабул қилинмайди
            try:
                bot.handle(msg)
            except subprocess.TimeoutExpired:
                bot.say("❌ Вақт тугади. Тайёр қисмлар сақланган; қайта буйруқ беринг.")
            except Exception as exc:  # бот ўзи тўхтаб қолмасин
                logging.exception("буйруқ хатоси")
                bot.say(f"❌ Ички хато: {exc}")


if __name__ == "__main__":
    sys.exit(main())
