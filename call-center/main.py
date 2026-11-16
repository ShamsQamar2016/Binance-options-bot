"""
AI Call Center — bolalar nuqtali massaji uchun qabulga yozish.
Twilio (telefon) + OpenAI Realtime (ovozli AI) + Telegram (xabarnoma) + SQLite.
O'zbek va rus tillarida gaplashadi.
"""
import os
import json
import html
import time
import sqlite3
import secrets
import logging
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

import httpx
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from dotenv import load_dotenv

load_dotenv()

# ==================== SOZLAMALAR ====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
PUBLIC_HOST = os.getenv("PUBLIC_HOST")  # masalan: callcenter.example.com (proksi ortida bo'lsa shart)
DB_PATH = os.getenv("DATABASE_PATH", "appointments.db")
OPENAI_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
OPENAI_VOICE = os.getenv("OPENAI_VOICE", "marin")
MAX_CALL_SECONDS = int(os.getenv("MAX_CALL_SECONDS", "600"))
MAX_CONCURRENT_CALLS = int(os.getenv("MAX_CONCURRENT_CALLS", "5"))
LOCAL_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent"))

OPENAI_WS_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
REQUIRED_ENV = ["OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TWILIO_AUTH_TOKEN"]

logging.basicConfig(level=logging.INFO)
# httpx INFO darajasida to'liq URL'ni (Telegram tokeni bilan) logga yozadi — o'chiramiz
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("call-center")

# ==================== MARKAZ HAQIDA MA'LUMOT ====================
# !!! BU YERNI O'ZINGIZ TO'LDIRING. AI faqat shu yerda yozilgan ma'lumotni aytadi.
# Bo'sh qoldirilgan narsa haqida so'ralsa, "administrator qo'ng'iroq qilib aytadi" deydi.
CLINIC_INFO = """
Nomi: "Bolalar nuqtali massaji markazi"
Manzil: (to'ldiring)
Ish vaqti: (to'ldiring, masalan: Dushanba–Shanba, 9:00–18:00)
Narxlar: (to'ldiring)
Bir seans davomiyligi: (to'ldiring)
Qabul qilinadigan yosh: (to'ldiring)
"""

# ==================== MA'LUMOTLAR BAZASI ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_sid TEXT,
            caller_phone TEXT,
            child_full_name TEXT,
            child_age TEXT,
            preferred_time TEXT,
            parent_name TEXT,
            contact_phone TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


FIELDS = ("child_full_name", "child_age", "preferred_time", "parent_name", "contact_phone", "notes")


def _save_appointment(call_sid: str, caller_phone: str, data: dict, existing_id: int | None) -> int:
    """Yangi yozuv yaratadi yoki shu qo'ng'iroqdagi mavjud yozuvni yangilaydi."""
    now = datetime.now(timezone.utc).isoformat()
    values = [data.get(f) for f in FIELDS]
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        if existing_id is None:
            cur.execute(
                f"INSERT INTO appointments (call_sid, caller_phone, {', '.join(FIELDS)}, created_at, updated_at) "
                f"VALUES (?, ?, {', '.join('?' * len(FIELDS))}, ?, ?)",
                [call_sid, caller_phone, *values, now, now],
            )
            existing_id = cur.lastrowid
        else:
            cur.execute(
                f"UPDATE appointments SET {', '.join(f + ' = ?' for f in FIELDS)}, updated_at = ? WHERE id = ?",
                [*values, now, existing_id],
            )
        conn.commit()
        return existing_id
    finally:
        conn.close()


# ==================== TELEGRAM ====================
def _esc(value) -> str:
    return html.escape(str(value)) if value else "—"


async def send_to_telegram(appt: dict, appt_id: int, caller_phone: str, updated: bool) -> bool:
    title = "✏️ <b>Yozuv o'zgartirildi</b>" if updated else "🆕 <b>Yangi yozilish — nuqtali massaj</b>"
    text = (
        f"{title} (№{appt_id})\n"
        "━━━━━━━━━━━━━━━\n"
        f"👶 <b>Bola:</b> {_esc(appt.get('child_full_name'))}\n"
        f"🎂 <b>Yoshi:</b> {_esc(appt.get('child_age'))}\n"
        f"🕒 <b>Qulay vaqt:</b> {_esc(appt.get('preferred_time'))}\n"
        f"👤 <b>Ota-ona:</b> {_esc(appt.get('parent_name'))}\n"
        f"📞 <b>Aloqa raqami:</b> {_esc(appt.get('contact_phone') or caller_phone)}\n"
        f"☎️ <b>Qo'ng'iroq qilgan raqam:</b> {_esc(caller_phone)}\n"
    )
    if appt.get("notes"):
        text += f"💬 <b>Izoh:</b> {_esc(appt['notes'])}\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(url, json=payload)
            if r.status_code == 200:
                return True
            logger.error("Telegram xatolik (%s): %s", r.status_code, r.text)
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return False  # qayta urinish foydasiz
        except httpx.HTTPError as e:
            # str(e) ichida token bo'lishi mumkin — faqat xato turini yozamiz
            logger.error("Telegram ulanish xatosi: %s", type(e).__name__)
        await asyncio.sleep(2 ** attempt)
    return False


# ==================== AI PROMPT ====================
SYSTEM_PROMPT = """
Siz — bolalar nuqtali massaji markazining telefon orqali qabulga yozuvchi ovozli yordamchisisiz.
Qo'ng'iroq qiluvchi odatda bolaning ota-onasi. Samimiy, xotirjam va qisqa gapiring
(bir martada 1–2 gap), bir vaqtda faqat bitta savol bering.

## TIL
- Suhbatni o'zbek tilida boshlang.
- Mijoz ruscha gapirsa — ruscha, o'zbekcha gapirsa — o'zbekcha javob bering.
- Bitta so'z yoki salomlashish uchun tilni almashtirmang; aralash gapirsa, ko'proq ishlatilgan tilda javob bering.

## ASOSIY VAZIFA — qabulga yozish
Quyidagilarni birma-bir so'rab oling:
1. Bolaning ismi va familiyasi.
2. Bolaning yoshi (1 yoshgacha bo'lsa — necha oylik).
3. Nuqtali massajga kelish uchun qulay kun va vaqt.
4. Ota-onaning ismi.
5. Aloqa raqami: "Shu qo'ng'iroq qilayotgan raqamingizga bog'lansak bo'ladimi?" deb so'rang.
   Ha desa — contact_phone maydonini bo'sh qoldiring. Boshqa raqam aytsa — raqamlarni birma-bir qaytarib tasdiqlang.
6. Bolaning shikoyati yoki qo'shimcha izoh bo'lsa (ixtiyoriy, majburlamang).

Hammasi to'plangach, ma'lumotlarni mijozga QAYTA O'QIB bering va "To'g'rimi?" deb so'rang.
Faqat mijoz tasdiqlagandan keyin save_appointment funksiyasini chaqiring.
Ism-familiyani aniq eshitmasangiz, qayta so'rang yoki harflab aytishni iltimos qiling.
Saqlangandan keyin: "Administrator vaqtni tasdiqlash uchun siz bilan bog'lanadi" deng.
Agar mijoz saqlangandan keyin biror narsani o'zgartirsa, save_appointment'ni yangi to'liq ma'lumot bilan qayta chaqiring.

## SAVOLLARGA JAVOB BERISH
- Markaz haqidagi savollarga FAQAT quyidagi "MARKAZ HAQIDA" bo'limidagi ma'lumot asosida javob bering.
- U yerda yo'q yoki "(to'ldiring)" deb turgan narsa (narx, manzil, vaqt va h.k.) haqida so'ralsa,
  hech narsa o'ylab topmang: "Buni administrator aniq aytib beradi, savolingizni yozib qo'yaman" deng
  va savolni notes maydoniga qo'shing.
- Aniq vaqt bo'sh yoki band ekanini bilmaysiz — vaqtni va'da qilmang, faqat mijozning xohishini yozib oling.
- Tibbiy maslahat, tashxis, davolash bo'yicha tavsiya BERMANG, massaj biror kasallikni davolaydi deb va'da qilmang.
  Bunday savolga: "Buni mutaxassisimiz ko'rikda aytadi" deng.
- Agar bolaning ahvoli shoshilinch bo'lsa (nafas qisishi, tutqanoq, yuqori isitma, hushdan ketish) —
  darhol 103 ga qo'ng'iroq qilishni ayting.
- Mavzuga aloqasiz savollarga xushmuomalalik bilan qisqa javob berib, suhbatni qabulga yozishga qaytaring.
- Mijoz jonli xodim bilan gaplashmoqchi bo'lsa — rozi bo'ling, ismi va savolini yozib olib,
  save_appointment orqali notes'ga "administrator qo'ng'iroq qilsin" deb yozing.

## SUHBATNI TUGATISH
Ish bitgach, xayrlashing va shundan KEYIN end_call funksiyasini chaqiring.
Mijoz xayrlashsa ham xuddi shunday qiling.
"""

TOOLS = [
    {
        "type": "function",
        "name": "save_appointment",
        "description": (
            "Bolani nuqtali massajga yozish. Faqat mijoz barcha ma'lumotni tasdiqlagandan keyin chaqiriladi. "
            "O'zgartirish kerak bo'lsa, to'liq ma'lumot bilan qayta chaqiriladi."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "child_full_name": {"type": "string", "description": "Bolaning ismi va familiyasi"},
                "child_age": {"type": "string", "description": "Bolaning yoshi, masalan '3 yosh' yoki '8 oylik'"},
                "preferred_time": {
                    "type": "string",
                    "description": "Qulay kun va vaqt, iloji bo'lsa aniq sana bilan, masalan '18-noyabr, chorshanba, soat 15:00 atrofida'",
                },
                "parent_name": {"type": "string", "description": "Ota-onaning ismi"},
                "contact_phone": {
                    "type": "string",
                    "description": "Boshqa aloqa raqami. Qo'ng'iroq qilingan raqamning o'zi bo'lsa bo'sh qoldiriladi",
                },
                "notes": {"type": "string", "description": "Shikoyat, izoh yoki administratorga savol"},
            },
            "required": ["child_full_name", "child_age", "preferred_time"],
        },
    },
    {
        "type": "function",
        "name": "end_call",
        "description": "Qo'ng'iroqni tugatish. Faqat xayrlashib bo'lgandan keyin chaqiriladi.",
        "parameters": {"type": "object", "properties": {}},
    },
]


def build_instructions() -> str:
    now = datetime.now(LOCAL_TZ)
    weekdays = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
    return (
        f"{SYSTEM_PROMPT}\n## MARKAZ HAQIDA\n{CLINIC_INFO}\n"
        f"## HOZIRGI VAQT\n{now:%Y-%m-%d %H:%M}, {weekdays[now.weekday()]}. "
        "\"Ertaga\", \"indinga\" kabi so'zlarni shu sanaga nisbatan hisoblang."
    )


# ==================== BIR MARTALIK TOKENLAR (/twiml -> /ws/call) ====================
TOKEN_TTL = 60
_pending_tokens: dict[str, dict] = {}
_active_calls = 0


def issue_token(call_sid: str, caller_phone: str) -> str:
    now = time.monotonic()
    for t in [t for t, v in _pending_tokens.items() if v["expires"] < now]:
        _pending_tokens.pop(t, None)
    token = secrets.token_urlsafe(32)
    _pending_tokens[token] = {"call_sid": call_sid, "caller_phone": caller_phone, "expires": now + TOKEN_TTL}
    return token


def consume_token(token: str | None) -> dict | None:
    info = _pending_tokens.pop(token, None) if token else None
    if info and info["expires"] >= time.monotonic():
        return info
    return None


# ==================== OPENAI SESSIYASI ====================
class CallSession:
    def __init__(self, twilio_ws: WebSocket, call_sid: str, stream_sid: str, caller_phone: str):
        self.twilio_ws = twilio_ws
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.caller_phone = caller_phone
        self.openai_ws = None
        self.appointment_id: int | None = None
        self.ending = False
        self.finished = asyncio.Event()

    async def _send_openai(self, payload: dict):
        await self.openai_ws.send(json.dumps(payload))

    async def connect(self):
        self.openai_ws = await websockets.connect(
            OPENAI_WS_URL,
            additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            max_size=None,
            open_timeout=10,
        )
        logger.info("OpenAI ulandi: %s", self.call_sid)
        await self._send_openai({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": build_instructions(),
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 600,
                        },
                    },
                    "output": {"format": {"type": "audio/pcmu"}, "voice": OPENAI_VOICE},
                },
                "tools": TOOLS,
                "tool_choice": "auto",
            },
        })
        # AI birinchi bo'lib salomlashadi
        await self._send_openai({
            "type": "response.create",
            "response": {
                "instructions": (
                    "Mijozga o'zbek tilida qisqa salom bering, bolalar nuqtali massaji markazi ekanini ayting "
                    "va qanday yordam bera olishingizni so'rang."
                )
            },
        })

    # ---------- Twilio -> OpenAI ----------
    async def on_twilio(self, msg: dict):
        ev = msg.get("event")
        if ev == "media":
            await self._send_openai({"type": "input_audio_buffer.append", "audio": msg["media"]["payload"]})
        elif ev == "mark" and msg.get("mark", {}).get("name") == "goodbye":
            self.finished.set()  # xayrlashuv ovozi to'liq eshittirildi
        elif ev == "stop":
            self.finished.set()

    # ---------- OpenAI -> Twilio ----------
    async def on_openai(self, msg: dict):
        etype = msg.get("type")
        if etype in ("response.output_audio.delta", "response.audio.delta"):
            await self.twilio_ws.send_json({
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": msg["delta"]},
            })
        elif etype == "input_audio_buffer.speech_started":
            # Mijoz gapira boshladi: navbatdagi AI ovozini to'xtatamiz (javobni server o'zi bekor qiladi)
            if not self.ending:
                await self.twilio_ws.send_json({"event": "clear", "streamSid": self.stream_sid})
        elif etype == "response.done":
            await self._handle_response_done(msg.get("response") or {})
        elif etype == "error":
            logger.error("OpenAI error: %s", msg.get("error"))

    async def _handle_response_done(self, response: dict):
        calls = [i for i in response.get("output") or [] if i.get("type") == "function_call"]
        if not calls:
            return
        need_reply = False
        for call in calls:
            name = call.get("name")
            if name == "save_appointment":
                output = await self._tool_save(call.get("arguments") or "{}")
                need_reply = True
            elif name == "end_call":
                output = {"status": "ok"}
                self.ending = True
            else:
                output = {"status": "error", "message": "unknown function"}
                need_reply = True
            await self._send_openai({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call.get("call_id"),
                    "output": json.dumps(output, ensure_ascii=False),
                },
            })
        if self.ending:
            # Qolgan ovoz eshittirib bo'lingach Twilio "mark"ni qaytaradi — shunda uzamiz
            await self.twilio_ws.send_json({
                "event": "mark", "streamSid": self.stream_sid, "mark": {"name": "goodbye"},
            })
            asyncio.get_running_loop().call_later(8, self.finished.set)  # zaxira
        elif need_reply:
            await self._send_openai({"type": "response.create"})

    async def _tool_save(self, raw_args: str) -> dict:
        """Har doim natija qaytaradi — model javobsiz qolmasligi kerak."""
        try:
            args = json.loads(raw_args)
            if not isinstance(args, dict):
                raise ValueError("arguments is not an object")
            missing = [f for f in ("child_full_name", "child_age", "preferred_time") if not args.get(f)]
            if missing:
                return {"status": "error", "message": f"Yetishmayapti: {', '.join(missing)}. Mijozdan so'rang."}

            updated = self.appointment_id is not None
            self.appointment_id = await asyncio.to_thread(
                _save_appointment, self.call_sid, self.caller_phone, args, self.appointment_id
            )
            logger.info("Yozuv saqlandi: №%s (%s)", self.appointment_id, self.call_sid)
        except Exception:
            logger.exception("Saqlashda xatolik: %s", self.call_sid)
            return {
                "status": "error",
                "message": "Saqlab bo'lmadi. Mijozdan uzr so'rang va birozdan keyin qayta qo'ng'iroq qilishini ayting.",
            }

        # Telegram xatosi yozuvni bekor qilmaydi — ma'lumot bazada turibdi
        if not await send_to_telegram(args, self.appointment_id, self.caller_phone, updated):
            logger.error("Telegram'ga yuborilmadi, yozuv bazada: №%s", self.appointment_id)
        return {"status": "success", "appointment_id": self.appointment_id}

    # ---------- Asosiy sikl ----------
    async def run(self):
        await self.connect()

        async def twilio_loop():
            async for raw in self.twilio_ws.iter_text():
                await self.on_twilio(json.loads(raw))

        async def openai_loop():
            async for raw in self.openai_ws:
                await self.on_openai(json.loads(raw))

        tasks = [
            asyncio.create_task(twilio_loop()),
            asyncio.create_task(openai_loop()),
            asyncio.create_task(self.finished.wait()),
        ]
        try:
            # Biri tugashi bilan hammasi to'xtaydi; umumiy vaqt cheklangan
            done, _ = await asyncio.wait(tasks, timeout=MAX_CALL_SECONDS, return_when=asyncio.FIRST_COMPLETED)
            if not done:
                logger.warning("Qo'ng'iroq vaqt chegarasidan oshdi: %s", self.call_sid)
            for t in done:
                exc = t.exception()
                if exc and not isinstance(exc, (WebSocketDisconnect, websockets.ConnectionClosed)):
                    logger.error("Sikl xatosi (%s): %r", self.call_sid, exc)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception:
                pass


# ==================== FASTAPI ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise RuntimeError(f".env da yetishmayapti: {', '.join(missing)}")
    await asyncio.to_thread(init_db)
    logger.info("DB tayyor")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    return "<h1>AI Call Center ishlayapti ✅</h1>"


@app.post("/twiml")
async def twiml(request: Request):
    form = await request.form()
    host = PUBLIC_HOST or request.headers.get("host", "")

    # So'rov haqiqatan Twilio'dan kelganini tekshiramiz
    url = f"https://{host}{request.url.path}"
    if request.url.query:
        url += f"?{request.url.query}"
    signature = request.headers.get("X-Twilio-Signature", "")
    if not RequestValidator(TWILIO_AUTH_TOKEN).validate(url, dict(form), signature):
        logger.warning("Twilio imzosi noto'g'ri")
        return Response(status_code=403)

    call_sid = form.get("CallSid", "unknown")
    caller_phone = form.get("From", "")
    logger.info("Qo'ng'iroq: %s", call_sid)

    resp = VoiceResponse()
    connect = Connect()
    stream = Stream(url=f"wss://{host}/ws/call")
    stream.parameter(name="token", value=issue_token(call_sid, caller_phone))
    connect.append(stream)
    resp.append(connect)
    return Response(content=str(resp), media_type="text/xml")


async def _wait_for_start(websocket: WebSocket) -> dict:
    """Twilio avval 'connected', keyin 'start' yuboradi."""
    while True:
        msg = json.loads(await websocket.receive_text())
        if msg.get("event") == "start":
            return msg["start"]


@app.websocket("/ws/call")
async def ws_call(websocket: WebSocket):
    global _active_calls
    await websocket.accept()
    session = None
    counted = False
    call_sid = None
    try:
        start = await asyncio.wait_for(_wait_for_start(websocket), timeout=10)
        info = consume_token((start.get("customParameters") or {}).get("token"))
        if not info:
            logger.warning("WS: token noto'g'ri yoki eskirgan")
            return
        if _active_calls >= MAX_CONCURRENT_CALLS:
            logger.warning("WS: bir vaqtdagi qo'ng'iroqlar chegarasi")
            return
        _active_calls += 1
        counted = True

        call_sid = start.get("callSid") or info["call_sid"]
        logger.info("WS start: %s", call_sid)
        session = CallSession(websocket, call_sid, start["streamSid"], info["caller_phone"])
        await session.run()
    except (WebSocketDisconnect, asyncio.TimeoutError):
        logger.info("WS uzildi: %s", call_sid)
    except Exception:
        logger.exception("WS xatolik: %s", call_sid)
    finally:
        if counted:
            _active_calls -= 1
        if session:
            await session.close()
        try:
            await websocket.close()  # Twilio oqimi yopilsa, qo'ng'iroq ham tugaydi
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
