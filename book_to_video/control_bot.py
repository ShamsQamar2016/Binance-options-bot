"""Telegram орқали бошқариладиган назоратчи бот.

Ишлатиш (сизнинг компьютерингизда, лойиҳа папкасидан):
    python control_bot.py --serial wuthering_full

Буйруқлар (фақат TELEGRAM_CHAT_ID дан келганлари қабул қилинади):
    /status    — қисмлар ҳолати
    /produce   — навбатдаги қисмни йиғиш (вақтинчалик хатолар автоматик қайта урилади)
    /publish   — тайёр қисмни каналга чиқариш (аввал тасдиқ сўрайди)
    /help      — рўйхат

Бот серия файлларини ўзи ўзгартирмайди: ҳамма иш serial.py буйруқлари орқали бажарилади.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

LOG_FILE = Path("output/control_bot.log")
POLL_TIMEOUT = 50
CONFIRM_WINDOW = 300  # /publish тасдиғи 5 дақиқа амал қилади

# Вақтинчалик хатолар: қайта уриш фойда беради (пул такрорланмайди — fal_api журнали бор)
TRANSIENT = [
    r"ConnectTimeout", r"ConnectError", r"ConnectionError", r"NameResolutionError",
    r"Invalid storage type", r"HTTP 429", r"HTTP 5\d\d", r"ReadTimeout", r"Timeout",
]
# Тугалланмаган сўров ёки бошқа чеклов — қайта уриш ёрдам бермайди, сизга хабар берамиз
PERMANENT_HINTS = {
    r"voice_limit_reached": "ElevenLabs овоз лимити тугади. Янги овоз учун voices.json га тайёр voice_id ёзинг.",
    r"credit balance is too low": "Anthropic ҳисобида кредит тугади. console.anthropic.com → Plans & Billing.",
    r"exhausted balance|Exhausted|insufficient": "fal.ai ҳисобида маблағ тугади. fal.ai/dashboard/billing да тўлдиринг.",
    r"no_media_generated": "Модель бу кадрни рад этди (хавфсизлик фильтри). Кадр тавсифини юмшатиш керак.",
    r"blocked_generation|403": "ElevenLabs матнни рад этди (хавфсизлик қоидаси). Овоз тавсифини ёки матнни ўзгартиринг.",
    r"Unauthorized|Authentication is required|401": "Калит нотўғри. .env даги калитни текширинг.",
}


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()])


class Telegram:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = str(chat_id)

    def call(self, method: str, **data) -> dict:
        r = requests.post(f"{self.base}/{method}", data=data, timeout=POLL_TIMEOUT + 15)
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method}: {body.get('description')}")
        return body["result"]

    def say(self, text: str) -> None:
        for start in range(0, len(text), 3900):
            self.call("sendMessage", chat_id=self.chat_id, text=text[start:start + 3900])

    def updates(self, offset: int | None) -> list[dict]:
        params = {"timeout": POLL_TIMEOUT, "allowed_updates": '["message"]'}
        if offset is not None:
            params["offset"] = offset
        r = requests.get(f"{self.base}/getUpdates", params=params, timeout=POLL_TIMEOUT + 15)
        body = r.json()
        return body.get("result", []) if body.get("ok") else []


def explain(output: str) -> str:
    for pattern, hint in PERMANENT_HINTS.items():
        if re.search(pattern, output, re.I):
            return hint
    return "Номаълум хато. Журнални охирги қаторлари: output/control_bot.log"


def is_transient(output: str) -> bool:
    if any(re.search(p, output, re.I) for p in PERMANENT_HINTS):
        return False
    return any(re.search(p, output) for p in TRANSIENT)


def run_serial(args: list[str], timeout: int = 4 * 3600) -> tuple[int, str]:
    """serial.py буйругини ишга туширади, чиқишини қайтаради (сўнги 6000 белги)."""
    proc = subprocess.run([sys.executable, "serial.py", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    logging.info("serial.py %s → код %s", " ".join(args), proc.returncode)
    return proc.returncode, out[-6000:]


def produce_with_retry(tg: Telegram, serial: str, attempts: int = 4) -> None:
    for attempt in range(1, attempts + 1):
        tg.say(f"⏳ Йиғиш бошланди (уриниш {attempt}/{attempts}). Тугагач хабар бераман.")
        code, out = run_serial(["produce", "--serial", serial, "--no-telegram"])
        if code == 0:
            ep = Path("output/serials") / serial / "episode_01" / "episode.mp4"
            tg.say(f"✅ Қисм тайёр: {ep}\nТасдиқлаш учун /publish ёзинг.")
            return
        if is_transient(out) and attempt < attempts:
            wait = 60 * attempt
            tg.say(f"⚠️ Вақтинчалик хато. {wait} сониядан кейин автоматик қайта урилади.")
            time.sleep(wait)
            continue
        tg.say(f"❌ Тўхтади.\nСабаб: {explain(out)}\n\nОхирги қатор:\n{out.strip().splitlines()[-1][:800] if out.strip() else '—'}")
        return


def main() -> int:
    load_dotenv()
    setup_logging()
    parser = argparse.ArgumentParser(description="Telegram назоратчи бот")
    parser.add_argument("--serial", required=True, help="Сериал папкаси номи, мас. wuthering_full")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_BOT_TOKEN ва TELEGRAM_CHAT_ID .env да бўлиши керак")
    tg = Telegram(token, chat)
    tg.say(f"🤖 Бот ишга тушди. Сериал: {args.serial}. Буйруқлар: /help")

    offset = None
    pending_publish = 0.0
    while True:
        try:
            updates = tg.updates(offset)
        except requests.RequestException as exc:
            logging.warning("Telegram уланиш хатоси: %s", exc)
            time.sleep(10)
            continue
        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != tg.chat_id:
                continue  # бошқаларнинг буйруқлари қабул қилинмайди
            cmd = (msg.get("text") or "").strip().split()[0:1]
            cmd = cmd[0].lower() if cmd else ""
            try:
                if cmd in ("/start", "/help"):
                    tg.say("/status — ҳолат\n/produce — навбатдаги қисмни йиғиш\n/publish — каналга чиқариш (тасдиқ билан)")
                elif cmd == "/status":
                    _, out = run_serial(["status", "--serial", args.serial])
                    tg.say(out.strip() or "Маълумот йўқ")
                elif cmd == "/produce":
                    produce_with_retry(tg, args.serial)
                elif cmd == "/publish":
                    pending_publish = time.time()
                    tg.say("Каналга чиқарайми? 5 дақиқа ичида /ha ёзинг.")
                elif cmd == "/ha" and time.time() - pending_publish < CONFIRM_WINDOW:
                    pending_publish = 0.0
                    code, out = run_serial(["publish-next", "--serial", args.serial])
                    tg.say("📢 Чиқарилди." if code == 0 else f"❌ {explain(out)}")
                else:
                    tg.say("Номаълум буйруқ. /help")
            except subprocess.TimeoutExpired:
                tg.say("❌ Вақт тугади. /produce ни қайта ёзинг: тайёр қисмлар сақланган.")
            except Exception as exc:  # бот ўзи тўхтаб қолмасин
                logging.exception("буйруқ хатоси")
                tg.say(f"❌ Ички хато: {exc}")


if __name__ == "__main__":
    sys.exit(main())
