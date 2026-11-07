#!/usr/bin/env python3
"""Ишчиларнинг иш вақтини ҳисоблаш тизими.

* Планшетда очиладиган веб-саҳифа: ҳар бир ходим учун «Келдим» / «Кетдим» тугмалари.
* Ҳар бир босишда раҳбарнинг Телеграмига хабар боради.
* Телеграм бот буйруқлари: /bugun, /kecha, /oy, /hafta, /start.
* Белгиланган вақтда «ким келмади» ва кунлик ҳисобот автоматик юборилади.

Фақат Python стандарт кутубхонаси ишлатилади — қўшимча ўрнатиш шарт эмас.
"""

import calendar
import json
import os
import queue
import sqlite3
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("ISH_CONFIG", os.path.join(BASE_DIR, "config.json"))
DB_PATH = os.environ.get("ISH_DB", os.path.join(BASE_DIR, "ish_vaqti.db"))

OYLAR = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
         "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
HAFTA_KUNLARI = ["Душанба", "Сешанба", "Чоршанба", "Пайшанба", "Жума", "Шанба", "Якшанба"]


# --------------------------------------------------------------------------- config

def load_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"config.json топилмади: {CONFIG_PATH}\n"
                 f"config.example.json дан нусха олиб, config.json деб сақланг.")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("port", 8080)
    cfg.setdefault("utc_offset_hours", 5)
    cfg.setdefault("work_start", "09:00")
    cfg.setdefault("absent_report_time", "09:30")
    cfg.setdefault("daily_report_time", "20:00")
    cfg["admin_chat_ids"] = [int(x) for x in cfg.get("admin_chat_ids", [])]
    if not cfg.get("workers"):
        sys.exit("config.json да 'workers' рўйхати бўш.")
    return cfg


CFG = load_config()
TZ = timezone(timedelta(hours=CFG["utc_offset_hours"]))


def now():
    return datetime.now(TZ).replace(microsecond=0)


def parse_hhmm(s):
    h, m = s.split(":")
    return int(h), int(m)


# --------------------------------------------------------------------------- database

DB_LOCK = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK, db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker TEXT NOT NULL,
                        day TEXT NOT NULL,          -- YYYY-MM-DD (келган кун)
                        start_ts TEXT NOT NULL,     -- ISO вақт
                        end_ts TEXT                 -- NULL = ҳали кетмаган
                     )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_day ON sessions(day)")
        c.execute("""CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)""")


def kv_get(key):
    with DB_LOCK, db() as c:
        r = c.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return r["v"] if r else None


def kv_set(key, val):
    with DB_LOCK, db() as c:
        c.execute("INSERT OR REPLACE INTO kv(k, v) VALUES(?, ?)", (key, str(val)))


def open_session(worker):
    with db() as c:
        return c.execute("SELECT * FROM sessions WHERE worker=? AND end_ts IS NULL "
                         "ORDER BY id DESC LIMIT 1", (worker,)).fetchone()


def check_in(worker):
    """Қайтаради: (ok, хабар матни)."""
    t = now()
    with DB_LOCK:
        s = open_session(worker)
        if s:
            st = datetime.fromisoformat(s["start_ts"])
            return False, f"{worker}, сиз {st:%H:%M} да «Келдим» босгансиз."
        with db() as c:
            c.execute("INSERT INTO sessions(worker, day, start_ts) VALUES(?,?,?)",
                      (worker, t.date().isoformat(), t.isoformat()))
    return True, t


def check_out(worker):
    t = now()
    with DB_LOCK:
        s = open_session(worker)
        if not s:
            return False, f"{worker}, сиз ҳали «Келдим» босмагансиз."
        with db() as c:
            c.execute("UPDATE sessions SET end_ts=? WHERE id=?", (t.isoformat(), s["id"]))
    start = datetime.fromisoformat(s["start_ts"])
    return True, (start, t)


def sessions_between(d1, d2):
    """d1..d2 (иккаласи ҳам киради) оралиғидаги сессиялар."""
    with DB_LOCK, db() as c:
        return c.execute("SELECT * FROM sessions WHERE day>=? AND day<=? ORDER BY start_ts",
                         (d1.isoformat(), d2.isoformat())).fetchall()


def session_seconds(s, at=None):
    start = datetime.fromisoformat(s["start_ts"])
    if s["end_ts"]:
        end = datetime.fromisoformat(s["end_ts"])
    else:
        end = at or now()
    return max(0, int((end - start).total_seconds()))


# --------------------------------------------------------------------------- ҳисоботлар

def fmt_dur(sec):
    h, m = divmod(sec // 60, 60)
    if h and m:
        return f"{h} соат {m} дақ"
    if h:
        return f"{h} соат"
    return f"{m} дақ"


def day_summary(d):
    """Ҳар бир ходим учун: {'sessions': [...], 'seconds': int, 'open': bool}."""
    rows = sessions_between(d, d)
    res = {w: {"sessions": [], "seconds": 0, "open": False} for w in CFG["workers"]}
    for s in rows:
        info = res.setdefault(s["worker"], {"sessions": [], "seconds": 0, "open": False})
        info["sessions"].append(s)
        info["seconds"] += session_seconds(s)
        if not s["end_ts"]:
            info["open"] = True
    return res


def late_text(first_start, d):
    h, m = parse_hhmm(CFG["work_start"])
    plan = datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)
    if first_start > plan + timedelta(minutes=1):
        return f" ⚠️ {fmt_dur(int((first_start - plan).total_seconds()))} кечикди"
    return ""


def report_day(d):
    summ = day_summary(d)
    title = f"📋 <b>{d:%d.%m.%Y}, {HAFTA_KUNLARI[d.weekday()]}</b>\n"
    came, absent = [], []
    total = 0
    for w, info in summ.items():
        if not info["sessions"]:
            absent.append(w)
            continue
        total += info["seconds"]
        parts = []
        for s in info["sessions"]:
            st = datetime.fromisoformat(s["start_ts"])
            en = datetime.fromisoformat(s["end_ts"]).strftime("%H:%M") if s["end_ts"] else "…"
            parts.append(f"{st:%H:%M}–{en}")
        first = datetime.fromisoformat(info["sessions"][0]["start_ts"])
        status = " 🟢 ишда" if info["open"] else ""
        came.append(f"👤 <b>{esc(w)}</b>: {fmt_dur(info['seconds'])}{status}\n"
                    f"     {', '.join(parts)}{late_text(first, d)}")
    out = title + "\n"
    out += ("✅ <b>Келганлар:</b>\n" + "\n".join(came) + "\n\n") if came else ""
    out += ("❌ <b>Келмаганлар:</b> " + ", ".join(esc(a) for a in absent) + "\n") if absent \
        else "🎉 Ҳамма келди!\n"
    out += f"\n⏱ Жами: {fmt_dur(total)}"
    return out


def report_range(d1, d2, title):
    rows = sessions_between(d1, d2)
    stats = {w: {"sec": 0, "days": set()} for w in CFG["workers"]}
    for s in rows:
        st = stats.setdefault(s["worker"], {"sec": 0, "days": set()})
        st["sec"] += session_seconds(s)
        st["days"].add(s["day"])
    lines = [f"📊 <b>{title}</b>", f"{d1:%d.%m.%Y} — {d2:%d.%m.%Y}", ""]
    total = 0
    for w, st in sorted(stats.items(), key=lambda kv: -kv[1]["sec"]):
        total += st["sec"]
        n = len(st["days"])
        avg = f", ўртача {fmt_dur(st['sec'] // n)}/кун" if n else ""
        lines.append(f"👤 <b>{esc(w)}</b>: {fmt_dur(st['sec'])} ({n} кун{avg})")
    lines += ["", f"⏱ Жами: {fmt_dur(total)}"]
    return "\n".join(lines)


def report_month(year, month):
    d1 = date(year, month, 1)
    d2 = date(year, month, calendar.monthrange(year, month)[1])
    today = now().date()
    if d1 <= today < d2:
        d2 = today  # жорий ой — бугунгача
    return report_range(d1, d2, f"{OYLAR[month]} {year} — ойлик ҳисобот")


def month_csv(year, month):
    d1 = date(year, month, 1)
    d2 = date(year, month, calendar.monthrange(year, month)[1])
    rows = sessions_between(d1, d2)
    per = {}
    for s in rows:
        per.setdefault((s["worker"], s["day"]), 0)
        per[(s["worker"], s["day"])] += session_seconds(s)
    days = [d1 + timedelta(days=i) for i in range((d2 - d1).days + 1)]
    header = ["Ходим"] + [f"{d:%d}" for d in days] + ["Жами (соат)"]
    lines = [";".join(header)]
    workers = list(CFG["workers"]) + sorted({s["worker"] for s in rows} - set(CFG["workers"]))
    for w in workers:
        vals, tot = [], 0
        for d in days:
            sec = per.get((w, d.isoformat()), 0)
            tot += sec
            vals.append(f"{sec / 3600:.2f}".replace(".", ",") if sec else "")
        lines.append(";".join([w] + vals + [f"{tot / 3600:.2f}".replace(".", ",")]))
    return ("﻿" + "\r\n".join(lines)).encode("utf-8")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------- Telegram

API = f"https://api.telegram.org/bot{CFG['bot_token']}/"
TG_ENABLED = bool(CFG.get("bot_token")) and "EXAMPLE" not in CFG["bot_token"]
OUTBOX = queue.Queue()


def tg(method, params=None, timeout=40):
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(API + method, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def tg_send_document(chat_id, filename, content, caption=""):
    boundary = "----ishvaqti" + str(int(time.time() * 1000))
    body = b""
    for k, v in (("chat_id", str(chat_id)), ("caption", caption)):
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                 f"{v}\r\n").encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
             f"filename=\"{filename}\"\r\nContent-Type: text/csv\r\n\r\n").encode()
    body += content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(API + "sendDocument", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def notify_admins(text):
    if not TG_ENABLED:
        print("[Телеграм ўчирилган]", text)
        return
    for cid in CFG["admin_chat_ids"]:
        OUTBOX.put((cid, text))


def sender_loop():
    while True:
        cid, text = OUTBOX.get()
        for attempt in range(5):
            try:
                tg("sendMessage", {"chat_id": cid, "text": text, "parse_mode": "HTML"})
                break
            except Exception as e:  # интернет узилиб қолса — қайта уринади
                print("Телеграмга юбориб бўлмади:", e)
                time.sleep(5 * (attempt + 1))


HELP = ("🤖 <b>Иш вақти боти</b>\n\n"
        "/bugun — бугун ким келди, ким келмади\n"
        "/kecha — кечаги ҳисобот\n"
        "/hafta — шу ҳафта бўйича соатлар\n"
        "/oy — шу ой бўйича соатлар\n"
        "/oy 2026-10 — бошқа ой\n"
        "/excel — ойлик жадвал (Excel учун CSV)\n"
        "/excel 2026-10 — бошқа ой жадвали\n"
        "/kun 05.11.2026 — исталган кун ҳисоботи")


def parse_month_arg(arg):
    t = now()
    if not arg:
        return t.year, t.month
    arg = arg.replace(".", "-").replace("/", "-")
    a, b = arg.split("-")
    y, m = (int(a), int(b)) if len(a) == 4 else (int(b), int(a))
    if not 1 <= m <= 12:
        raise ValueError
    return y, m


def handle_command(chat_id, text):
    parts = text.strip().split()
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if chat_id not in CFG["admin_chat_ids"]:
        return (f"Сизнинг chat ID: <code>{chat_id}</code>\n"
                f"Уни config.json даги admin_chat_ids га ёзиб, дастурни қайта ишга туширинг.")
    today = now().date()
    if cmd in ("/start", "/help", "/yordam"):
        return HELP
    if cmd == "/bugun":
        return report_day(today)
    if cmd == "/kecha":
        return report_day(today - timedelta(days=1))
    if cmd == "/kun":
        try:
            d = datetime.strptime(arg, "%d.%m.%Y").date()
        except ValueError:
            return "Формат: /kun 05.11.2026"
        return report_day(d)
    if cmd == "/hafta":
        d1 = today - timedelta(days=today.weekday())
        return report_range(d1, today, "Шу ҳафта")
    if cmd == "/oy":
        try:
            y, m = parse_month_arg(arg)
        except ValueError:
            return "Формат: /oy 2026-10"
        return report_month(y, m)
    if cmd == "/excel":
        try:
            y, m = parse_month_arg(arg)
        except ValueError:
            return "Формат: /excel 2026-10"
        tg_send_document(chat_id, f"ish_vaqti_{y}-{m:02d}.csv", month_csv(y, m),
                         f"{OYLAR[m]} {y} — кунлик соатлар")
        return None
    return HELP


def bot_loop():
    offset = int(kv_get("tg_offset") or 0)
    while True:
        try:
            res = tg("getUpdates", {"offset": offset, "timeout": 30}, timeout=40)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                kv_set("tg_offset", offset)
                msg = upd.get("message") or {}
                text = msg.get("text")
                if not text or not text.startswith("/"):
                    continue
                cid = msg["chat"]["id"]
                try:
                    reply = handle_command(cid, text)
                except Exception:
                    traceback.print_exc()
                    reply = "Хатолик юз берди."
                if reply:
                    OUTBOX.put((cid, reply))
        except Exception as e:
            print("getUpdates хатоси:", e)
            time.sleep(5)


def scheduler_loop():
    """Ҳар дақиқада текширади: келмаганлар рўйхати ва кунлик ҳисобот вақти."""
    while True:
        t = now()
        today = t.date().isoformat()
        hm = t.strftime("%H:%M")

        if hm >= CFG["absent_report_time"] and kv_get("absent_sent") != today:
            kv_set("absent_sent", today)
            summ = day_summary(t.date())
            absent = [w for w, i in summ.items() if not i["sessions"] and w in CFG["workers"]]
            if absent:
                notify_admins(f"⏰ Соат {CFG['absent_report_time']} ҳолатига ҳали келмаганлар:\n❌ "
                              + ", ".join(esc(a) for a in absent))
            else:
                notify_admins(f"⏰ Соат {CFG['absent_report_time']}: ҳамма ишга келди ✅")

        if hm >= CFG["daily_report_time"] and kv_get("daily_sent") != today:
            kv_set("daily_sent", today)
            notify_admins(report_day(t.date()))
            # ой охирги куни — ойлик ҳисобот ҳам
            if (t.date() + timedelta(days=1)).month != t.month:
                notify_admins(report_month(t.year, t.month))

        time.sleep(30)


# --------------------------------------------------------------------------- веб (планшет)

def status_json():
    summ = day_summary(now().date())
    out = []
    for w in CFG["workers"]:
        info = summ[w]
        last = info["sessions"][-1] if info["sessions"] else None
        out.append({
            "name": w,
            "in": info["open"],
            "came": datetime.fromisoformat(info["sessions"][0]["start_ts"]).strftime("%H:%M")
            if info["sessions"] else None,
            "left": datetime.fromisoformat(last["end_ts"]).strftime("%H:%M")
            if last and last["end_ts"] else None,
            "worked": fmt_dur(info["seconds"]) if info["sessions"] else None,
        })
    return {"time": now().strftime("%H:%M"),
            "date": f"{now():%d.%m.%Y}, {HAFTA_KUNLARI[now().weekday()]}",
            "workers": out}


def do_action(worker, action):
    if worker not in CFG["workers"]:
        return False, "Бундай ходим йўқ."
    if action == "in":
        ok, r = check_in(worker)
        if not ok:
            return False, r
        late = late_text(r, r.date())
        notify_admins(f"✅ <b>{esc(worker)}</b> ишга келди — {r:%H:%M}{late}")
        return True, f"Хуш келибсиз, {worker}! ({r:%H:%M})"
    if action == "out":
        ok, r = check_out(worker)
        if not ok:
            return False, r
        start, end = r
        today_total = day_summary(start.date())[worker]["seconds"]
        notify_admins(f"🏁 <b>{esc(worker)}</b> ишдан кетди — {end:%H:%M}\n"
                      f"Келган: {start:%H:%M}, ишлади: {fmt_dur(int((end - start).total_seconds()))}\n"
                      f"Бугун жами: {fmt_dur(today_total)}")
        return True, f"Хайр, {worker}! Бугун {fmt_dur(today_total)} ишладингиз."
    return False, "Нотўғри амал."


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(os.path.join(BASE_DIR, "kiosk.html"), encoding="utf-8") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/status":
            return self._send(200, status_json())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/mark":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            ok, msg = do_action(data.get("name", ""), data.get("action", ""))
        except Exception:
            traceback.print_exc()
            ok, msg = False, "Хатолик юз берди."
        self._send(200, {"ok": ok, "message": msg, "status": status_json()})

    def log_message(self, fmt, *args):
        pass


def main():
    init_db()
    threads = [sender_loop, scheduler_loop]
    if TG_ENABLED:
        threads.append(bot_loop)
    else:
        print("ДИҚҚАТ: bot_token киритилмаган — Телеграм хабарлари юборилмайди.")
    for fn in threads:
        threading.Thread(target=fn, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", CFG["port"]), Handler)
    print(f"Ишга тушди: http://<компьютер-IP>:{CFG['port']}  (планшетда шу манзилни очинг)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
