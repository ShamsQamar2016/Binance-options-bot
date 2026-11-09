# book_to_video — тўлиқ код (аудитдан кейинги версия)

GitHub: ShamsQamar2016/Binance-options-bot, бранч `ccr-4c4c7d98-5ed5j0`, коммит `a0f48a5` (2026-11-09).
Бу файлда лойиҳанинг ҳамма файллари кетма-кет берилган, GitHub'дагиси билан бир хил.

## Аудитда топилган камчиликлар ва улар тузатилган жой

| № | Камчилик | Қаерда тузатилди |
|---|---|---|
| 1 | Чала қолган видео каналга чиқиб кетиши | `episode_builder.py` (`_final_mix`) |
| 2 | Пулли видео сўрови такрор юборилиши | `fal_api.py` (`run`, `_wait`, журнал) |
| 3 | Параллел ишлашда кеш файли бузилиши | `fileutil.py` (янги), `fal_api.py`, `serial.py`, `dubbing.py` |
| 4 | Таҳрирланган `script.json` қисмни тўхтатиши | `serial.py` (`load_script`), `series_planner.py` (`normalize_script`), `visuals.py`, `episode_builder.py` (`storyboard`) |
| 5 | Қисм рақамлари текширилмаслиги | `series_planner.py` (`normalize_plan`) |
| 6 | Файл номи орқали папкадан ташқарига ёзиш | `book_sources.py` (`safe_filename`) |
| 7 | Эталон нусхаси бир вақтда ёзилиши | `visuals.py` (`_thumb`) |
| 8 | Овоз кешида созламалар ҳисобга олинмаслиги | `episode_builder.py` (`voice_lines`) |
| 9 | Ишлатилмайдиган эски код | `video.py`, `main.py` |
| 10 | Такрорланган код | `claude_client.py` (янги), `scenario.py`, `check_script.py` |
| + | Кадр узунлиги оширилганда видео қотиб қолиши | `episode_builder.py` (`build_shot`) |

## Файллар

«Ҳолат» устуни аудит қилинган версияга (`1ecb993`) нисбатан нима ўзгарганини кўрсатади.

| № | Файл | Вазифаси | Қатор | Ҳолат |
|---|---|---|---|---|
| 1 | `README.md` | Қўлланма: ўрнатиш ва ишлатиш | 240 | тузатилган |
| 2 | `requirements.txt` | Керакли Python кутубхоналари | 8 | ўзгармаган |
| 3 | `.env.example` | Калитлар ва созламалар намунаси | 66 | ўзгармаган |
| 4 | `serial.py` | Сериал буйруқлари (асосий файл) | 467 | тузатилган |
| 5 | `series_planner.py` | Claude: сериал режаси, сценарий, калит расм танлаш | 434 | тузатилган |
| 6 | `claude_client.py` | Claude API билан ишлаш (умумий) | 60 | янги |
| 7 | `fileutil.py` | Файлларни хавфсиз ёзиш ва ўқиш | 44 | янги |
| 8 | `book_sources.py` | Китобни олиш: файл, ҳавола ёки Telegram | 91 | тузатилган |
| 9 | `book_reader.py` | PDF, DOCX, TXT ўқиш | 54 | ўзгармаган |
| 10 | `visuals.py` | Эталон расм, калит расм, видео, лаб синхрони | 261 | тузатилган |
| 11 | `fal_api.py` | fal.ai моделлари билан ишлаш | 385 | тузатилган |
| 12 | `dubbing.py` | ElevenLabs: русча овозлар | 162 | тузатилган |
| 13 | `sound.py` | Жой муҳити, эффектлар, мусиқа | 62 | ўзгармаган |
| 14 | `episode_builder.py` | Қисмни йиғиш: видео, товуш, субтитр, ранг | 564 | тузатилган |
| 15 | `telegram_sender.py` | Telegram'га юбориш | 143 | ўзгармаган |
| 16 | `video.py` | Telegram учун сиқиш + эски трейлер режими видеоси | 248 | тузатилган |
| 17 | `check_script.py` | Сценарий текшируви | 97 | тузатилган |
| 18 | `main.py` | Эски трейлер режими (сериалга алоқаси йўқ) | 114 | тузатилган |
| 19 | `scenario.py` | Эски трейлер режими сценарийси (сериалга алоқаси йўқ) | 93 | тузатилган |

---

## 1. `README.md`

Қўлланма: ўрнатиш ва ишлатиш · тузатилган

````markdown
# Китобдан AI трейлер → Telegram

Бу скрипт китобни олади ва автоматик равишда:

1. **Китобни ўқийди** (`.txt`, `.pdf`, `.docx`)
2. **Claude** (Opus 5.5) китобни таҳлил қилиб, энг кучли саҳналарни танлайди ва трейлер сценарийсини ёзади.
   Ҳар саҳна учун видео моделига инглизча промпт ҳам тайёрлайди.
3. **Kling** (fal.ai орқали) ҳар саҳнага 5–10 сониялик видео клип яратади
4. **ffmpeg** клипларни битта трейлерга бирлаштиради
5. **Telegram** га трейлер ва сценарийни юборади

Китоб ўзбекча, русча ёки инглизча бўлиши мумкин — сценарий ва диктор матни китоб тилида,
видео промптлари эса инглизча бўлади (видео моделлари инглизчада яхшироқ ишлайди).

## Ўрнатиш

```bash
cd book_to_video
pip install -r requirements.txt
cp .env.example .env      # кейин .env ичига калитларни ёзинг
```

ffmpeg ҳам керак: Windows — https://ffmpeg.org/download.html, Ubuntu — `sudo apt install ffmpeg`, Mac — `brew install ffmpeg`.

### Калитлар (.env)

| Ўзгарувчи | Қаердан олинади |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| `FAL_KEY` | https://fal.ai/dashboard/keys |
| `FAL_MODEL` | Видео модели ID. Стандарт: `fal-ai/kling-video/v2.1/standard/text-to-video`. fal.ai сайтидаги модел саҳифасидан ID ни текшириб, керак бўлса алмаштиринг |
| `TELEGRAM_BOT_TOKEN` | Telegramда @BotFather → `/newbot` |
| `TELEGRAM_CHAT_ID` | @userinfobot га ёзинг — у ID ни беради. Ботга аввал `/start` ёзиб қўйинг |

## Ишлатиш

```bash
# 1. Аввал фақат сценарийни синаб кўринг (арзон, видеосиз)
python main.py китоб.pdf --script-only

# 2. Тўлиқ жараён: сценарий + видео + Telegram
python main.py китоб.pdf

# Саҳналар сони, услуб ва формат
python main.py китоб.docx --scenes 8 --wishes "қоронғи, триллер услубида" --aspect 9:16

# Сценарийни қўлда таҳрирлаб, кейин видео ясаш
python main.py китоб.pdf --script-only --no-telegram
#   → output/китоб/script.json ни таҳрирланг
python main.py --from-script output/китоб/script.json
```

`--aspect 9:16` — Instagram Reels / YouTube Shorts / TikTok учун вертикал видео.

Агар видео генерация ўртада тўхтаб қолса, буйруқни `--from-script` билан қайта ишга туширинг:
тайёр бўлган клиплар қайта генерация қилинмайди (пул тежалади).

## Натижалар

```
output/<китоб номи>/
  script.json     — саҳналар ва промптлар (таҳрирлаш мумкин)
  script.txt      — тўлиқ сценарий матни
  scene_01.mp4 …  — алоҳида клиплар
  trailer.mp4     — тайёр трейлер
```

## Файллар

| Файл | Вазифаси |
|---|---|
| `main.py` | Асосий скрипт (буйруқ қатори) |
| `book_reader.py` | Китоб файлини ўқиш ва бўлакларга ажратиш |
| `scenario.py` | Claude билан сценарий яратиш |
| `video.py` | fal.ai орқали видео генерация, ffmpeg билан бирлаштириш |
| `telegram_sender.py` | Telegram га юбориш |

## Нархи ҳақида

- **Claude**: китоб ҳажмига боғлиқ. Opus 5.5 — 1 млн кирувчи токен $4, 1 млн чиқувчи токен $20.
  300 саҳифали китоб тахминан $1–3.
- **Kling**: ҳар клип учун алоҳида тўланади (fal.ai нархлар саҳифасини кўринг). 6 саҳна × 5 сония — энг кўп харажат шу ерда.
  Шунинг учун аввал `--script-only` билан синаб кўринг.

## Эслатма

- Жуда узун китоблар (800 минг белгидан ортиқ) аввал қисмларга бўлиниб, ҳар қисмнинг мазмуни олинади, кейин сценарий ёзилади.
- Telegram бот 50 МБ гача видео юбора олади — катта трейлер автоматик сиқилади.
- Видео моделлари овоз яратмайди. Диктор матни `script.json` даги `narration` майдонида — уни TTS (масалан ElevenLabs) орқали овозлаштириб қўшиш мумкин.

---

# 📺 Сериал режими: китобдан кундалик вертикал сериал (`serial.py`)

Китобни кундалик сериалга айлантиради ва ҳар куни бир қисмини Telegram каналга чиқаради.
Тайёр қисмни YouTube Shorts ва Instagram Reels'га ҳам жойлаш мумкин.

- **Персонажлар ва атмосфера китобдан олинади.** Япон китобида персонажлар японлардек кўринади ва
  воқеа Японияда бўлади, Америка китобида эса — американлар ва Америка. Ҳисобга олинадиган нарса муаллифнинг
  миллати эмас, воқеа бўлиб ўтадиган жой ва давр.
- **Дубляж, субтитр ва титрлар доим рус тилида.** Исмлар рус анъанасида ёзилади: Кэндзи, Джон.
- **Формат: вертикал 9:16, 1080×1920, ҳар қисм 3 дақиқадан қисқа.** Бу формат YouTube Shorts ва
  Instagram Reels учун бир хил ишлайди.

## Қандай ишлайди

1. **Режа** (`plan`). Claude бутун китобни ўқиб, «сериал библияси»ни тузади:
   - воқеа бўлиб ўтадиган мамлакат ва давр;
   - персонажларнинг миллати, юзи, кийими ва овози;
   - жойлар ва уларнинг муҳит товуши;
   - кино услуби ва қисмлар рўйхати.
2. **Эталонлар** (`refs`). Ҳар персонаж учун «кастинг сурати», ҳар жой учун эталон расм ясалади.
   Ҳамма кадрлар шу расмлардан бошланади, шунинг учун персонаж ҳар куни бир хил кўринади.
3. **Овозлар** (`voices`). ElevenLabs Voice Design ҳар персонажга алоҳида русча овоз яратади. Персонаж тавсифидаги
   ёш, тембр ва феъл-атвор ҳисобга олинади.
4. **Раскадровка** (`storyboard`). Claude қисм сценарийсини ёзади: кадр планлари, русча диалоглар ва
   ҳиссиёт теглари. Кейин ҳар кадр учун калит расм ясалади:
   - ҳар кадрдан 2 та вариант чиқади;
   - Claude уларни эталонлар билан солиштириб, энг мосини танлайди;
   - раскадровка Telegram'га келади.

   Бу босқич арзон. Пул асосан видеога кетади, у эса кейинги босқичда ясалади.
5. **Қисм** (`produce`):
   - ҳар калит расмдан видео ясалади (Veo 3.1);
   - гапираётган одамнинг юзи кўринса, лаби русча овозга мосланади (VEED Lipsync);
   - товуш тўрт йўлакдан иборат: диалог, кадр эффектлари, жой муҳити ва қисм учун басталанган мусиқа;
   - мусиқа реплика пайтида ўзи пасаяди;
   - бутун қисмга ягона кино ранги берилади;
   - русча субтитрлар Shorts/Reels тугмалари тагида қолмайдиган жойга ёзилади;
   - бошида сериал номи ва серия рақами, охирида «Продолжение следует…» чиқади;
   - овоз баландлиги -14 LUFS га келтирилади.
6. **Кундалик** (`daily`). Тайёр қисм каналга чиқади, кейин эртанги қисм ясалиб, сизга кўриш учун юборилади.

## Ишга тушириш

```bash
pip install -r requirements.txt
cp .env.example .env        # калитларни ёзинг: ANTHROPIC_API_KEY, FAL_KEY, ELEVENLABS_API_KEY, TELEGRAM_*

# 1. Режа: китоб файлидан, ҳаволадан ёки Telegram ботга юборилган файлдан
python serial.py plan --book "Snow Country.pdf" --name snow_country
python serial.py plan --from-telegram --name snow_country      # аввал ботга PDF юборинг (20 МБ гача)

# 2. Эталонлар → Telegram'га келади. Ёқмаганини қайта ясаш:
python serial.py refs
python serial.py refs --redo shimamura,inn

# 3. Овозлар → намуналар Telegram'га келади. Ёқмаганини қайта яратиш:
python serial.py voices
python serial.py voices --redo komako

# 4. Биринчи қисм раскадровкаси (арзон). Ёқмаган кадрнинг расмини ўчириб, қайта ишга туширинг:
python serial.py storyboard
#    output/serials/snow_country/episode_01/clips/shot_07.png ни ўчириш → shot 7 қайта ясалади

# 5. Қисмни тайёрлаш → олдиндан кўриш сизга келади
python serial.py produce

# 6. Ёқса — ҳар куни автоматик
python serial.py daily
python serial.py status
```

Тайёр қисм `episode_NN/episode.mp4` да туради. Бу 1080×1920 сифатли асл файл: YouTube ва Instagram'га шуни
юкланг. Telegram'га сиқилган нусха кетади. YouTube ва Instagram учун тайёр сарлавҳа ва тавсиф
`episode_NN/post.txt` файлида.

### Таҳрирлаш (пул тежаб)

Ҳамма оралиқ файллар сақланади. Қайта ишга туширганда фақат ўчирилган ёки ўзгартирилган қисм қайта ясалади.

Жараён узилса (интернет, компьютер ўчиши), буйруқни қайта ишга туширинг. fal.ai'га юборилган видео сўровлари қайта юборилмайди: тайёр бўлган натижа олинади, пул икки марта тўланмайди.

| Нима қилсангиз | Нима қайта ясалади |
|---|---|
| `episode_NN/clips/shot_XX.mp4` ни ўчирсангиз | шу кадр видеоси |
| `episode_NN/clips/shot_XX.png` ни ўчирсангиз | шу кадрнинг калит расми ва видеоси |
| `episode_NN/script.json` да реплика матнини ўзгартирсангиз | шу реплика овози ва лаб синхрони |
| `refs/<id>.png` ни ўчирсангиз (ёки `refs --redo id`) | персонаж эталони (кейинги кадрлар учун) |

Сценарийни текшириш (такрорлар, кадрга сиғмайдиган узун нутқ):
`python check_script.py output/serials/snow_country/episode_01/script.json`

### Моделлар

Барча тасвир моделлари битта **fal.ai** калити орқали ишлайди. Уларни `.env` да алмаштириш мумкин:

| Вазифа | Стандарт | Муқобил |
|---|---|---|
| Эталон ва калит расм | `fal-ai/nano-banana-pro` + `/edit` | Seedream, FLUX Kontext |
| Расмдан видео | `fal-ai/veo3.1/image-to-video` | `fal-ai/veo3.1/fast/image-to-video` (арзонроқ), Kling 3, Seedance 2.5 |
| Лаб синхрони | `veed/lipsync/v2` | Kling Lipsync, sync.so |
| Овоз, эффектлар, мусиқа | ElevenLabs `eleven_v3`, Voice Design v3, Sound Effects, Music | — |
| Сценарий ва танлов | Claude Opus 5.5 | — |

Моделлар параметрлари бир-биридан фарқ қилади. Масалан, Veo'да видео узунлиги "8s", Kling'да 10.
Скрипт ҳар модел учун унинг схемасини fal.ai дан олиб, сўровни шу схемага ўзи мослаштиради. Модел
нимани қабул қилишини кўриш учун:
```bash
python serial.py check-models
```

### Нархи ҳақида (тахминан, fal.ai ва ElevenLabs нархларини текширинг)

Ҳисоб 2 дақиқалик бир қисм учун (~24 кадр):

| Нима | Тахминий нарх |
|---|---|
| Калит расмлар (24 кадр × 2 вариант) | ~$7 |
| Видео (Veo 3.1, 1080p, товушсиз, ~6 с × 24) | ~$25–35 |
| Лаб синхрони | ~$3–5 |
| Claude | ~$0.5–1 |
| **Жами** | **~$35–50** |

- Эталонлар ва режа бир марта ясалади: ~$5–10.
- ElevenLabs ойлик обуна билан ишлайди: овоз, эффектлар ва мусиқа кредит ҳисобидан кетади, тарифни кредит ҳажмига қараб танланг.
- Арзонлаштириш: `VIDEO_MODEL=fal-ai/veo3.1/fast/image-to-video` ва `KEYFRAME_TAKES=1`.

### Ҳар куни автоматик ишлатиш

Linux/Mac (cron), ҳар куни соат 20:00 да:
```
0 20 * * * cd /йўл/book_to_video && /usr/bin/python3 serial.py daily >> serial.log 2>&1
```
Windows: Task Scheduler → Create Basic Task → Daily → Program: `python`, Arguments: `serial.py daily`,
Start in: `book_to_video` папкаси.

`daily` аввал тайёр қисмни чиқаради, кейин эртангисини ясайди. Шунинг учун видео генерацияси узоқ
давом этса ҳам, чиқиш вақти кечикмайди. Хато бўлса, сизга Telegram орқали хабар келади.

## ⚠️ Муаллифлик ҳуқуқи

Китоб асосида сериал ясаб, уни оммага чиқариш учун **асар ҳуқуқ эгасининг рухсати керак**.

- Кўп мамлакатларда асар муаллиф вафотидан 70 йил ўтгач эркин бўлади. Масалан, Дюма, Гюго, Диккенс,
  Конан Дойл ва Жюль Верн асарларидан эркин фойдаланиш мумкин.
- Китоб эркин бўлса ҳам, унинг **замонавий рус таржимаси таржимоннинг мулки**. Шунинг учун Claude
  диалогларни таржимадан сўзма-сўз кўчирмайди, ўзи қайта ёзади.
- Фон мусиқаси ҳам ҳуқуқи сизда бўлган ёки эркин лицензияли бўлсин. Стандарт ҳолатда ҳар қисмга
  ElevenLabs Music орқали янги мусиқа басталанади.
````

---

## 2. `requirements.txt`

Керакли Python кутубхоналари · ўзгармаган

````text
anthropic>=2.6.0
fal-client>=1.0
pydantic>=2.0
requests>=2.31
python-dotenv>=1.0
# ихтиёрий: PDF ва DOCX китобларни ўқиш учун
pypdf>=4.0
python-docx>=1.1
````

---

## 3. `.env.example`

Калитлар ва созламалар намунаси · ўзгармаган

````bash
# ================= Асосий калитлар =================
# Claude API калити (сценарий, режа, калит расм танлаш): https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...

# fal.ai калити (расм, видео, лаб синхрони — ҳаммаси битта калит орқали): https://fal.ai/dashboard/keys
FAL_KEY=...

# ElevenLabs (русча овозлар, эффектлар, мусиқа): https://elevenlabs.io → Profile → API Keys
ELEVENLABS_API_KEY=...

# Telegram: @BotFather дан бот токени ва чат ID (@userinfobot орқали билиш мумкин)
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
# Сериал чиқадиган канал. Ботни каналга админ қилиб қўшинг.
TELEGRAM_CHANNEL_ID=@kanal_nomi
# Каналдаги «Серия N — завтра в ...» ёзуви учун
PUBLISH_TIME=20:00

# ================= Сериал: моделлар (fal.ai ID) =================
# Ўзгартирмасангиз ҳам бўлади — стандарт қийматлар энг юқори сифат учун танланган.
# Модел нимани қабул қилишини кўриш: python serial.py check-models
IMAGE_MODEL=fal-ai/nano-banana-pro
IMAGE_EDIT_MODEL=fal-ai/nano-banana-pro/edit
VIDEO_MODEL=fal-ai/veo3.1/image-to-video
LIPSYNC_MODEL=veed/lipsync/v2
# Расм сифати (1K / 2K / 4K) ва видео сифати (720p / 1080p)
IMAGE_RESOLUTION=2K
VIDEO_RESOLUTION=1080p
# Ҳар кадр учун нечта калит расм варианти (Claude энг яхшисини танлайди). 1 — арзонроқ
KEYFRAME_TAKES=2
# Нечта кадр параллел ясалсин
VISUAL_WORKERS=4
# 1 — гапираётган юз кўринадиган кадрларда лабни овозга мослаш
LIPSYNC=1
# 1 — диалогсиз кадрларда видео моделининг ўз табиий товуши (қадам, шамол) ишлатилсин
#     (видео нархи ошади; 0 бўлса, эффектлар ElevenLabs орқали ясалади)
VIDEO_NATIVE_AUDIO=0

# ================= Сериал: овоз ва товуш (ElevenLabs) =================
ELEVENLABS_MODEL=eleven_v3
ELEVENLABS_VOICE_DESIGN_MODEL=eleven_ttv_v3
ELEVENLABS_LANGUAGE_CODE=ru
# 1 — ҳар қисмга мусиқа басталансин (ElevenLabs Music); 0 — мусиқасиз
MUSIC=1
# Ўз мусиқангиз (mp3, ҳуқуқи сизда бўлсин) — берилса, басталанмайди
BACKGROUND_MUSIC=

# ================= Сериал: кўриниш =================
# film — ягона кино ранги ва енгил плёнка доначаси; none — рангга тегмаслик
GRADE=film
# 1 — русча субтитрни видеога ёзиш, 0 — ёзмаслик
BURN_SUBTITLES=1
# Субтитр пастдан неча пиксел юқорида (Shorts/Reels тугмалари тагида қолмаслиги учун ~520)
SUB_MARGIN=520
# Кирилл ҳарфли шрифт файли (ихтиёрий). Windows: C:/Windows/Fonts/arialbd.ttf
FONT_FILE=
# Шрифт номи (FONT_FILE ичидаги оила номи, мас. Montserrat). Бўш бўлса — автоматик
SUB_FONT=

# ================= Трейлер режими (main.py) =================
# Видео провайдер: grok ёки kling
VIDEO_PROVIDER=grok
XAI_API_KEY=xai-...
GROK_MODEL=grok-imagine-video-1.5-lite
GROK_RESOLUTION=720p
FAL_MODEL=fal-ai/kling-video/v2.1/standard/text-to-video
````

---

## 4. `serial.py`

Сериал буйруқлари (асосий файл) · тузатилган

````python
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
from fileutil import write_text_atomic
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
                    "-q:v", "3", str(out)], check=True)
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
````

---

## 5. `series_planner.py`

Claude: сериал режаси, сценарий, калит расм танлаш · тузатилган

````python
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
````

---

## 6. `claude_client.py`

Claude API билан ишлаш (умумий) · янги

````python
"""Claude API билан ишлаш учун умумий ёрдамчилар (сериал ва трейлер режимлари учун битта жой).

Модел, fallback ва хатоларни текшириш шу ерда: ўзгартириш керак бўлса, фақат шу файл ўзгаради.
"""

from __future__ import annotations

import anthropic

MODEL = "claude-opus-5-5"
# Хавфсизлик фильтри сўровни рад этса, API уни автоматик бошқа моделда қайта ишлатади
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def client() -> anthropic.Anthropic:
    # ANTHROPIC_API_KEY муҳит ўзгарувчисидан олинади
    return anthropic.Anthropic()


def check(message, hint: str = "") -> None:
    """Рад этилган ёки кесилган жавобда тушунарли хато беради."""
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        reason = getattr(details, "explanation", None) if details else None
        raise RuntimeError(f"Claude сўровни рад этди. {reason or ''}".strip())
    if message.stop_reason == "max_tokens":
        raise RuntimeError(f"Жавоб max_tokens чегарасига етиб кесилди. {hint}".strip())


def structured(system: str, content, output_type, effort: str = "high", max_tokens: int = 64000,
               hint: str = ""):
    """Claude'дан Pydantic схемасига мос жавоб олади. content — матн ёки контент блоклари рўйхати."""
    with client().beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=system,
        output_config={"effort": effort},
        output_format=output_type,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        message = stream.get_final_message()
    check(message, hint)
    return message.parsed_output


def text(prompt: str, effort: str = "medium", max_tokens: int = 32000) -> str:
    """Оддий матнли жавоб (масалан, узун китоб бўлагининг мазмуни)."""
    with client().beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    check(message)
    return "".join(b.text for b in message.content if b.type == "text")
````

---

## 7. `fileutil.py`

Файлларни хавфсиз ёзиш ва ўқиш · янги

````python
"""Файлларни хавфсиз ёзиш ва ўқиш.

Файл аввал вақтинчалик номга тўлиқ ёзилади, кейин бир ҳаракатда асл номга алмаштирилади. Шунда
жараён ёзиш пайтида узилса ҳам, ёки бошқа поток (thread) уни шу пайт ўқиса ҳам, чала файл қолмайди.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


def temp_name(path: Path) -> Path:
    """Шу жараён ва шу поток учун ноёб вақтинчалик ном (кенгайтма сақланади)."""
    path = Path(path)
    return path.with_name(f".{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp{path.suffix}")


def write_text_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = temp_name(path)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, data) -> None:
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=1))


def read_json_cache(path: Path, default):
    """Кеш файлини ўқийди. Йўқ ёки бузилган бўлса — default (кеш қайта тўлдирилади)."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (ValueError, OSError) as exc:
        logger.warning("Бузилган кеш файли эътиборсиз қолдирилди: %s (%s)", path, exc)
        return default
````

---

## 8. `book_sources.py`

Китобни олиш: файл, ҳавола ёки Telegram · тузатилган

````python
"""Китобни олиш: локал файл, URL ҳавола ёки Telegram ботга юборилган файл.

Китоб манбаини сиз танлайсиз: скрипт интернетдан ўзи қидирмайди, чунки
тасодифий сайтлардан рухсатсиз (пират) нусха олиб қўйиш хавфи бор.
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

import requests

import telegram_sender as tg
from book_reader import read_book

SUPPORTED = (".txt", ".md", ".pdf", ".docx", ".fb2", ".epub")


def safe_filename(name: str, default: str = "book") -> str:
    """Ташқаридан келган файл номини хавфсиз қилади: фақат охирги қисм қолади, «../» ва
    Windows'да тақиқланган белгилар олиб ташланади. Шунда файл сериал папкасидан ташқарига ёзилмайди."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip(" .")
    return name[:150] or default


def download_from_url(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        name = Path(unquote(urlparse(url).path)).name or "book"
        disposition = r.headers.get("content-disposition", "")
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disposition)
        if m:
            name = unquote(m.group(1))
        name = safe_filename(name)
        if not name.lower().endswith(SUPPORTED):
            ctype = r.headers.get("content-type", "")
            name += ".pdf" if "pdf" in ctype else ".txt"
        path = dest_dir / name
        with open(path, "wb") as f:
            for part in r.iter_content(1 << 20):
                f.write(part)
    return path


def download_from_telegram(dest_dir: Path) -> Path:
    """Ботга (TELEGRAM_CHAT_ID чатидан) охирги юборилган китоб файлини юклаб олади."""
    doc = tg.latest_document_from_admin()
    if not doc:
        raise RuntimeError("Ботга китоб файли юборилмаган. Ботга .pdf/.docx/.fb2/.epub/.txt файл юборинг.")
    return tg.download_file(doc["file_id"], dest_dir / safe_filename(doc.get("file_name", ""), "book.txt"))


def _strip_html(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)</(p|div|h\d|br|li)>|<br\s*/?>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def _read_fb2(path: Path) -> str:
    root = ElementTree.parse(path).getroot()
    paragraphs = [
        "".join(el.itertext()) for el in root.iter() if el.tag.split("}")[-1] in ("p", "title", "subtitle")
    ]
    return "\n".join(paragraphs)


def _read_epub(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        return "\n".join(_strip_html(z.read(n).decode("utf-8", errors="ignore")) for n in names)


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".fb2":
        text = _read_fb2(path)
    elif suffix == ".epub":
        text = _read_epub(path)
    else:
        text = read_book(path)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 2000:
        raise RuntimeError(f"Китоб матни жуда қисқа ({len(text)} белги) — файл тўғрими? (сканер қилинган PDF матнсиз бўлади)")
    return text
````

---

## 9. `book_reader.py`

PDF, DOCX, TXT ўқиш · ўзгармаган

````python
"""Китоб файлини ўқиш: .txt, .md, .pdf, .docx"""

from pathlib import Path


def read_book(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        # Ўзбек/рус матнлари кўпинча UTF-8 ёки Windows-1251 да бўлади
        for encoding in ("utf-8", "utf-8-sig", "cp1251"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Файл кодировкасини аниқлаб бўлмади: {path}")

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        import docx

        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)

    raise ValueError(f"Қўллаб-қувватланмайдиган формат: {suffix} (.txt, .pdf, .docx бўлиши керак)")


def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Матнни абзацлар бўйича бўлакларга ажратади (абзац ўртасидан кесмайди)."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in text.split("\n"):
        if current_len + len(paragraph) > max_chars and current:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        # Жуда узун абзацни мажбуран бўлиш
        while len(paragraph) > max_chars:
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        current.append(paragraph)
        current_len += len(paragraph) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks
````

---

## 10. `visuals.py`

Эталон расм, калит расм, видео, лаб синхрони · тузатилган

````python
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
import threading
from pathlib import Path

import fal_api
from fileutil import temp_name
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
        c = chars.get(cid)
        if c is None:  # номаълум id (мас. script.json қўлда таҳрирланганда) — эътиборсиз
            continue
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


_THUMB_LOCK = threading.Lock()


def _thumb(path: Path) -> Path:
    """Claude'га юбориш учун кичрайтирилган JPEG.

    Бир эталон расмни бир неча кадр бир вақтда ишлатади, шунинг учун нусха навбат билан ва
    вақтинчалик файл орқали ясалади: бошқа поток чала файлни ўқиб қолмайди.
    """
    out = path.with_name(path.stem + "_thumb.jpg")
    with _THUMB_LOCK:
        if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
            tmp = temp_name(out)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vf",
                            "scale='min(768,iw)':-2", "-q:v", "4", str(tmp)], check=True)
            os.replace(tmp, out)
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
````

---

## 11. `fal_api.py`

fal.ai моделлари билан ишлаш · тузатилган

````python
"""fal.ai орқали моделларни ишлатиш: файл юклаш, навбатга қўйиш, натижани юклаб олиш.

Моделлар тез-тез янгиланади ва уларнинг параметрлари бир-биридан фарқ қилади (мас. Veo'да duration
"8s", Kling'да 10). Шунинг учун ҳар модел учун fal.ai дан унинг OpenAPI схемаси олинади ва сўров
шу схемага мослаштирилади:
  - схемада йўқ майдонлар олиб ташланади;
  - duration, aspect_ratio, resolution каби танловли майдонлар энг яқин рухсат этилган қийматга ўтказилади;
  - расм майдони номи (image_url / start_image_url / first_frame_url ...) моделга қараб танланади.
Схема олинмаса, сўров ўзгаришсиз юборилади.

Пул тежаш: ҳар бир пулли сўров (request_id) журналга ёзилади. Кутиш вақти тугаса, алоқа узилса ёки
дастур тўхтаса, кейинги ишга туширишда янги сўров юборилмайди — ўша сўровнинг натижаси кутилади.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

import requests

from fileutil import read_json_cache, write_json_atomic

logger = logging.getLogger(__name__)

SCHEMA_DIR = Path("output/.fal_schemas")
SCHEMA_MAX_AGE = 3 * 24 * 3600

# Бизнинг майдон номимиз → моделларда учрайдиган номлар
ALIASES = {
    "image_url": ["image_url", "start_image_url", "first_frame_url", "input_image_url", "image", "first_frame_image"],
    "image_urls": ["image_urls", "reference_image_urls", "input_image_urls", "images", "reference_images"],
    "video_url": ["video_url", "video", "input_video_url"],
    "audio_url": ["audio_url", "audio", "input_audio_url"],
    "negative_prompt": ["negative_prompt"],
}


def _client():
    try:
        import fal_client
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("fal-client ўрнатилмаган: pip install -r requirements.txt") from exc
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError("FAL_KEY ўрнатилмаган (.env файлига қўшинг): https://fal.ai/dashboard/keys")
    return fal_client.SyncClient(key=os.environ["FAL_KEY"])


# ----------------------------- Файл юклаш -----------------------------

_UPLOADS = Path("output/.fal_uploads.json")
UPLOAD_MAX_AGE = 24 * 3600
_LOCK = threading.Lock()  # кадрлар параллел ишланганда кеш файлларини ҳимоя қилади


def upload(path: Path) -> str:
    """Маҳаллий файлни fal CDN га юклайди ва URL қайтаради (24 соат кешланади)."""
    path = Path(path)
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    with _LOCK:
        hit = read_json_cache(_UPLOADS, {}).get(digest)
    if hit and time.time() - hit.get("at", 0) < UPLOAD_MAX_AGE:
        return hit["url"]
    url = _with_retry(lambda: _client().upload_file(path), f"юклаш {path.name}")
    with _LOCK:
        cache = read_json_cache(_UPLOADS, {})
        cache[digest] = {"url": url, "at": time.time()}
        write_json_atomic(_UPLOADS, cache)
    return url


def download(url: str, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(out)
    return out


def _with_retry(func, what: str, attempts: int = 4):
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # тармоқ ва вақтинчалик хатолар
            status = getattr(exc, "status_code", None)
            permanent = status is not None and status < 500 and status != 429
            if permanent or attempt == attempts:
                detail = getattr(getattr(exc, "response", None), "text", "") or ""
                raise RuntimeError(f"fal.ai: {what} муваффақиятсиз: {exc} {detail[:1500]}") from exc
            delay = 5 * 2 ** (attempt - 1)
            logger.warning("fal.ai: %s хато (%s), %d сониядан кейин қайта", what, exc, delay)
            time.sleep(delay)


# ----------------------------- Схема -----------------------------

def _schema_path(endpoint: str) -> Path:
    return SCHEMA_DIR / (re.sub(r"[^a-zA-Z0-9]+", "_", endpoint) + ".json")


def _resolve(node: dict, root: dict) -> dict:
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"].lstrip("#/").split("/")
        node = root
        for part in ref:
            node = node.get(part, {})
    if isinstance(node, dict) and "allOf" in node and len(node["allOf"]) == 1:
        merged = {k: v for k, v in node.items() if k != "allOf"}
        merged.update(_resolve(node["allOf"][0], root))
        return merged
    return node


def _input_schema(openapi: dict) -> dict | None:
    for path, ops in (openapi.get("paths") or {}).items():
        post = (ops or {}).get("post") or {}
        body = (((post.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema")
        if body and "/requests/" not in path:
            schema = _resolve(body, openapi)
            props = {k: _resolve(v, openapi) for k, v in (schema.get("properties") or {}).items()}
            return {"properties": props, "required": schema.get("required", [])}
    return None


def input_schema(endpoint: str) -> dict | None:
    """Модел кириш параметрлари схемаси ({properties, required}) ёки None."""
    cached = _schema_path(endpoint)
    with _LOCK:
        data = read_json_cache(cached, None)
        age = time.time() - cached.stat().st_mtime if data is not None else 0
    if data is not None:
        if (data and age < SCHEMA_MAX_AGE) or (not data and age < 3600):  # топилмаганини 1 соатдан кейин қайта сўраймиз
            return data or None
    schema = None
    headers = {"Authorization": f"Key {os.environ['FAL_KEY']}"} if os.environ.get("FAL_KEY") else {}
    attempts = [
        ("https://api.fal.ai/v1/models", {"endpoint_id": endpoint, "expand": "openapi-3.0"}),
        ("https://fal.ai/api/openapi/queue/openapi.json", {"endpoint_id": endpoint}),
    ]
    for url, params in attempts:
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code != 200:
                continue
            data = r.json()
            if "models" in data:
                models = data.get("models") or []
                data = (models[0].get("openapi") if models else None) or {}
            schema = _input_schema(data)
            if schema:
                break
        except (requests.RequestException, ValueError) as exc:
            logger.info("fal.ai схемаси олинмади (%s): %s", url, exc)
    with _LOCK:
        write_json_atomic(cached, schema or {})
    if not schema:
        logger.warning("%s схемаси топилмади — сўров ўзгаришсиз юборилади", endpoint)
    return schema


def _number(value) -> float | None:
    m = re.search(r"\d+(\.\d+)?", str(value))
    return float(m.group()) if m else None


def _enum(prop: dict) -> list | None:
    if "enum" in prop:
        return prop["enum"]
    for key in ("anyOf", "oneOf"):
        for option in prop.get(key, []) or []:
            if "enum" in option:
                return option["enum"]
    return None


def _fit_value(key: str, value, prop: dict):
    choices = _enum(prop)
    if key == "duration":
        want = _number(value) or 5
        if choices:
            nums = sorted(((n, c) for c in choices if (n := _number(c)) is not None), key=lambda x: x[0])
            bigger = [c for n, c in nums if n >= want - 0.01]
            return bigger[0] if bigger else (nums[-1][1] if nums else value)
        typ = prop.get("type")
        lo, hi = prop.get("minimum"), prop.get("maximum")
        if lo is not None:
            want = max(want, lo)
        if hi is not None:
            want = min(want, hi)
        if typ == "integer":
            return int(round(want + 0.49))
        if typ == "number":
            return want
        return str(int(round(want + 0.49)))
    if choices is None or value in choices:
        if isinstance(value, list) and prop.get("maxItems"):
            return value[: prop["maxItems"]]
        return value
    if key == "aspect_ratio":
        return "auto" if "auto" in choices else None
    if key == "resolution":
        order = ["4K", "4k", "2160p", "2K", "2k", "1440p", "1080p", "1K", "1k", "720p", "768p", "540p", "480p"]
        want_idx = order.index(value) if value in order else len(order)
        for cand in order[want_idx:] + order[:want_idx][::-1]:
            if cand in choices:
                return cand
    if isinstance(value, bool) or prop.get("type") == "boolean":
        return value
    return None


def fit(endpoint: str, payload: dict) -> dict:
    """Сўровни модел схемасига мослаштиради."""
    schema = input_schema(endpoint)
    if not schema:
        return {k: v for k, v in payload.items() if v is not None}
    props = schema["properties"]
    out: dict = {}
    for key, value in payload.items():
        if value is None:
            continue
        names = ALIASES.get(key, [key])
        target = next((n for n in names if n in props), None)
        if target is None:
            logger.info("%s: '%s' параметри моделда йўқ — ташлаб юборилди", endpoint, key)
            continue
        fitted = _fit_value(key, value, props[target])
        if fitted is None:
            logger.info("%s: '%s'=%r моделда рухсат этилмаган — ташлаб юборилди", endpoint, key, value)
            continue
        out[target] = fitted
    missing = [r for r in schema.get("required", []) if r not in out]
    if missing:
        logger.warning("%s: мажбурий параметрлар йўқ: %s", endpoint, missing)
    return out


def allowed_durations(endpoint: str) -> list[float] | None:
    """Модел қабул қиладиган видео узунликлари (сония) ёки None (номаълум/исталган)."""
    schema = input_schema(endpoint) or {}
    prop = (schema.get("properties") or {}).get("duration")
    if not prop:
        return None
    choices = _enum(prop)
    if choices:
        return sorted(n for c in choices if (n := _number(c)) is not None)
    return None


# ----------------------------- Ишга тушириш -----------------------------

_JOURNAL = Path("output/.fal_requests.json")
JOURNAL_MAX_AGE = 24 * 3600   # fal.ai натижаларни шунча вақт сақлайди деб ҳисоблаймиз
POLL_EVERY = 5


class _RequestGone(Exception):
    """Журналдаги сўров fal.ai да топилмади (муддати ўтган)."""


def _journal(update=None):
    """Пулли сўровлар журнали: {калит: {endpoint, request_id, at}}. update(journal) — ўзгартириш."""
    with _LOCK:
        data = read_json_cache(_JOURNAL, {})
        if update is not None:
            update(data)
            write_json_atomic(_JOURNAL, data)
        return data


def run(endpoint: str, payload: dict, timeout_s: int = 1800) -> dict:
    """Моделни навбат орқали ишга туширади ва натижани (JSON) қайтаради.

    Сўров fal.ai га фақат БИР МАРТА юборилади. Кутиш вақтида хато бўлса ёки вақт тугаса, сўров
    қайта юборилмайди: request_id журналда қолади ва кейинги ишга туширишда ўша сўровнинг натижаси
    олинади (иккинчи марта пул тўланмайди).
    """
    arguments = fit(endpoint, payload)
    key = hashlib.sha1(f"{endpoint}|{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}".encode()).hexdigest()
    client = _client()
    started = time.time()

    entry = _journal().get(key)
    if entry and time.time() - entry.get("at", 0) < JOURNAL_MAX_AGE:
        logger.info("fal.ai: олдинги сўров давом эттирилмоқда %s (%s)", entry["request_id"], endpoint)
        try:
            return _wait(client, endpoint, entry["request_id"], key, timeout_s, started)
        except _RequestGone:
            logger.warning("fal.ai: олдинги сўров %s топилмади — янгиси юборилади", entry["request_id"])
            _journal(lambda j: j.pop(key, None))

    logger.info("fal.ai → %s %s", endpoint, json.dumps(_short(arguments), ensure_ascii=False)[:600])
    handle = _with_retry(lambda: client.submit(endpoint, arguments=arguments), f"{endpoint} юбориш", attempts=2)
    _journal(lambda j: j.__setitem__(key, {"endpoint": endpoint, "request_id": handle.request_id, "at": time.time()}))
    try:
        return _wait(client, endpoint, handle.request_id, key, timeout_s, started)
    except _RequestGone:
        _journal(lambda j: j.pop(key, None))
        raise RuntimeError(f"fal.ai: {endpoint} сўрови {handle.request_id} йўқолиб қолди")


def _wait(client, endpoint: str, request_id: str, key: str, timeout_s: int, started: float) -> dict:
    """Сўров тайёр бўлишини кутади (қайта юбормасдан) ва натижасини қайтаради."""
    import fal_client

    deadline = time.time() + timeout_s
    failures = 0
    while True:
        try:
            status = client.status(endpoint, request_id)
            failures = 0
        except Exception as exc:  # тармоқ узилиши — фақат ҳолатни қайта сўраймиз
            code = getattr(exc, "status_code", None)
            if code in (404, 410):
                raise _RequestGone(request_id) from exc
            failures += 1
            if failures >= 12 or (code is not None and code < 500 and code != 429):
                raise RuntimeError(f"fal.ai: {endpoint} ҳолатини олиб бўлмади (request_id={request_id}): {exc}. "
                                   "Қайта ишга туширсангиз, шу сўровнинг натижаси кутилади.") from exc
            time.sleep(min(60, POLL_EVERY * failures))
            continue
        if isinstance(status, fal_client.Completed):
            if status.error:
                _journal(lambda j: j.pop(key, None))
                raise RuntimeError(f"fal.ai: {endpoint} хатоси ({status.error_type}): {status.error}")
            try:
                result = _with_retry(lambda: client.result(endpoint, request_id), f"{endpoint} натижа")
            except Exception:
                _journal(lambda j: j.pop(key, None))  # доимий хато (мас. параметр нотўғри) — журналда қолмасин
                raise
            _journal(lambda j: j.pop(key, None))
            logger.info("fal.ai ← %s (%.0f сония)", endpoint, time.time() - started)
            return result
        if time.time() > deadline:
            raise TimeoutError(f"fal.ai: {endpoint} {timeout_s} сонияда тайёр бўлмади (request_id={request_id}). "
                               "Қайта ишга туширсангиз, шу сўровнинг натижаси кутилади — қайта пул тўланмайди.")
        time.sleep(POLL_EVERY)


def _short(data: dict) -> dict:
    return {k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v) for k, v in data.items()}


def result_url(result: dict, kind: str) -> str:
    """Натижадан файл URL ни олади. kind: video | image | audio."""
    if kind == "image":
        images = result.get("images") or ([result["image"]] if result.get("image") else [])
        if images:
            return images[0]["url"] if isinstance(images[0], dict) else images[0]
    item = result.get(kind)
    if isinstance(item, dict) and item.get("url"):
        return item["url"]
    if isinstance(item, str):
        return item
    raise RuntimeError(f"fal.ai жавобида {kind} топилмади: {json.dumps(result)[:500]}")


def result_urls(result: dict) -> list[str]:
    images = result.get("images") or ([result["image"]] if result.get("image") else [])
    return [(i["url"] if isinstance(i, dict) else i) for i in images]


def describe(endpoint: str) -> str:
    """Модел параметрлари рўйхати (текшириш учун)."""
    schema = input_schema(endpoint)
    if not schema:
        return f"{endpoint}: схема олинмади"
    lines = [f"{endpoint}:"]
    for name, prop in schema["properties"].items():
        choices = _enum(prop)
        mark = "*" if name in schema.get("required", []) else " "
        extra = f" {choices}" if choices else (f" [{prop.get('minimum')}..{prop.get('maximum')}]"
                                               if "minimum" in prop or "maximum" in prop else "")
        lines.append(f"  {mark} {name}: {prop.get('type', '')}{extra}")
    return "\n".join(lines)
````

---

## 12. `dubbing.py`

ElevenLabs: русча овозлар · тузатилган

````python
"""Русча дубляж (ElevenLabs): ҳар персонажга алоҳида, махсус яратилган овоз.

Овозлар (voices.json):
  - Сериал режаси тузилгач, ҳар персонаж учун Voice Design (eleven_ttv_v3) тавсифидан янги овоз ясалади
    ва ElevenLabs ҳисобингизга сақланади. voice_id лар voices.json да туради.
  - Овоз ёқмаса: voices.json да шу персонажнинг voice_id сини ўчириб, `python serial.py voices` ни
    қайта ишга туширинг ёки ElevenLabs кутубхонасидан ўзингиз танлаган voice_id ни ёзинг.

Нутқ: eleven_v3 модели, рус тили, ҳиссиёт теглари ([whispers], [sighs], [angry] ...).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import time
from pathlib import Path

import requests

from fileutil import write_text_atomic

logger = logging.getLogger(__name__)

API = "https://api.elevenlabs.io/v1"
RETRY_STATUSES = {429, 500, 502, 503, 504}

SAMPLE_TEXT = {
    "male": ("Знаешь, я долго молчал. Но сегодня скажу всё, как есть. Ты можешь мне не верить, "
             "но я видел это своими глазами — и с тех пор не могу спать по ночам."),
    "female": ("Послушай меня внимательно. Я не прошу многого — только правду. Если ты уйдёшь сейчас, "
               "я пойму. Но если останешься, обещай, что больше никогда мне не солжёшь."),
}
NARRATOR_SAMPLE = ("В тот год зима пришла раньше обычного. Никто в городе ещё не знал, что эта ночь "
                   "изменит всё — и для тех, кто ждал перемен, и для тех, кто их боялся.")


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY ўрнатилмаган (.env файлига қўшинг)")
    return key


def _post(path: str, payload: dict, params: dict | None = None, timeout: int = 300) -> requests.Response:
    """ElevenLabs'га POST: вақтинчалик хатоларда (429/5xx, тармоқ) экспоненциал кутиб қайта уринади."""
    for attempt in range(1, 6):
        try:
            r = requests.post(f"{API}{path}", params=params, json=payload,
                              headers={"xi-api-key": _key()}, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == 5:
                raise
            logger.warning("ElevenLabs %s: тармоқ хатоси (%s), қайта уриниш %d", path, exc, attempt)
        else:
            if r.status_code not in RETRY_STATUSES or attempt == 5:
                if r.status_code >= 400:
                    raise RuntimeError(f"ElevenLabs {path} хатоси {r.status_code}: {r.text[:800]}")
                return r
            logger.warning("ElevenLabs %s: HTTP %s, қайта уриниш %d", path, r.status_code, attempt)
        time.sleep(3 * 2 ** (attempt - 1))
    raise RuntimeError("unreachable")


# ----------------------------- Овозларни яратиш -----------------------------

def design_voice(name: str, description: str, gender: str, preview_path: Path | None = None,
                 sample: str | None = None) -> str:
    """Тавсифдан янги овоз ясайди ва ElevenLabs ҳисобига сақлайди. voice_id ни қайтаради."""
    text = sample or SAMPLE_TEXT.get(gender, SAMPLE_TEXT["male"])
    data = _post("/text-to-voice/design", {
        "voice_description": description[:1000],
        "model_id": os.environ.get("ELEVENLABS_VOICE_DESIGN_MODEL", "eleven_ttv_v3"),
        "text": text,
    }).json()
    previews = data.get("previews") or []
    if not previews:
        raise RuntimeError(f"Voice Design вариант қайтармади: {str(data)[:300]}")
    best = previews[0]
    if preview_path is not None and best.get("audio_base_64"):
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_bytes(base64.b64decode(best["audio_base_64"]))
    created = _post("/text-to-voice", {
        "voice_name": name[:100],
        "voice_description": description[:1000],
        "generated_voice_id": best["generated_voice_id"],
    }).json()
    return created["voice_id"]


def build_voice_map(plan, path: Path, create: bool = False, previews_dir: Path | None = None) -> dict:
    """voices.json ни тузади/янгилайди. create=True бўлса, voice_id йўқ персонажларга овоз яратади.

    Қўлда ёзилган voice_id ва созламалар сақланади.
    """
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    voices: dict = {}
    entries = [("narrator", "Рассказчик", plan.narrator_voice)] + [(c.id, c.name, c.voice) for c in plan.characters]
    for cid, name, spec in entries:
        entry = {"name": name, "gender": spec.gender, "age": spec.age,
                 "description": spec.description, "voice_id": ""}
        entry.update(existing.get(cid, {}))
        if create and not entry.get("voice_id"):
            print(f"🎙  Овоз яратилмоқда: {name}")
            sample = NARRATOR_SAMPLE if cid == "narrator" else None
            preview = previews_dir / f"{cid}.mp3" if previews_dir else None
            entry["voice_id"] = design_voice(f"{plan.series_title[:40]} — {name}", spec.description,
                                             spec.gender, preview, sample)
        voices[cid] = entry
        # Ҳар овоз яратилгач сақланади: жараён узилса, яратилган овозлар йўқолмайди
        write_text_atomic(path, json.dumps(voices | {k: v for k, v in existing.items() if k not in voices},
                                           ensure_ascii=False, indent=2))
    return voices


# ----------------------------- Нутқ -----------------------------

def _tagged_text(text: str, delivery: str) -> str:
    tags = [t.strip().strip("[]") for t in (delivery or "").split(",") if t.strip()]
    tags = [t for t in tags if t.lower() not in ("neutral", "calm", "normal")][:2]
    return "".join(f"[{t}] " for t in tags) + text


def synthesize(text: str, voice: dict, delivery: str, out: Path) -> Path:
    """Битта репликани русча овозлаштиради (mp3)."""
    voice_id = voice.get("voice_id")
    if not voice_id:
        raise RuntimeError(f"voices.json да «{voice.get('name')}» учун voice_id йўқ: python serial.py voices")
    model = os.environ.get("ELEVENLABS_MODEL", "eleven_v3")
    payload = {
        "text": _tagged_text(text, delivery) if "v3" in model else text,
        "model_id": model,
        "voice_settings": {"stability": float(voice.get("stability", 0.5)),
                           "similarity_boost": float(voice.get("similarity_boost", 0.75))},
    }
    lang = os.environ.get("ELEVENLABS_LANGUAGE_CODE", "ru")
    params = {"output_format": os.environ.get("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")}
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = _post(f"/text-to-speech/{voice_id}", payload | ({"language_code": lang} if lang else {}), params)
    except RuntimeError as exc:
        msg = str(exc)
        if lang and (" 400" in msg or "language" in msg.lower()):
            # Баъзи моделлар language_code ни қабул қилмайди — усиз қайта уринамиз
            r = _post(f"/text-to-speech/{voice_id}", payload, params)
        else:
            raise
    tmp = out.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(out)
    return out


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())
````

---

## 13. `sound.py`

Жой муҳити, эффектлар, мусиқа · ўзгармаган

````python
"""Товуш дизайни (ElevenLabs): жой муҳити (ambience), кадр эффектлари (SFX) ва қисм мусиқаси.

- ambience — ҳар жой учун бир марта, айланма (loop) товуш: шу жойдаги барча кадрлар остида узлуксиз
  чалади, кадрлар алмашганда муҳит «узилмайди».
- SFX — кадрдаги аниқ товушлар (қадам, эшик, от кишнаши).
- мусиқа — ҳар қисм учун алоҳида басталанган инструментал мусиқа (реплика пайтида пасаяди).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dubbing import _post

logger = logging.getLogger(__name__)

SFX_MODEL = "eleven_text_to_sound_v2"


def _save(content: bytes, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.replace(out)
    return out


def sound_effect(prompt: str, seconds: float, out: Path, loop: bool = False) -> Path:
    """Матн тавсифидан товуш эффекти (0.5–30 сония)."""
    payload = {
        "text": prompt[:450],
        "duration_seconds": round(max(0.5, min(30.0, seconds)), 1),
        "prompt_influence": 0.45,
        "model_id": os.environ.get("ELEVENLABS_SFX_MODEL", SFX_MODEL),
    }
    if loop:
        payload["loop"] = True
    r = _post("/sound-generation", payload, params={"output_format": "mp3_44100_128"})
    return _save(r.content, out)


def ambience(prompt: str, out: Path) -> Path:
    """Жой муҳити: 25 сониялик айланма товуш (кадрлар остида керакли узунликкача такрорланади)."""
    return sound_effect(f"{prompt}. Continuous ambient background, no music, no speech, no voices.", 25, out, loop=True)


def music(prompt: str, seconds: float, out: Path) -> Path | None:
    """Қисм учун инструментал мусиқа. Хато бўлса None қайтаради (қисм мусиқасиз йиғилади)."""
    try:
        r = _post("/music", {
            "prompt": prompt[:2000],
            "music_length_ms": int(max(10, min(300, seconds)) * 1000),
            "model_id": os.environ.get("ELEVENLABS_MUSIC_MODEL", "music_v1"),
            "force_instrumental": True,
        }, params={"output_format": "mp3_44100_128"}, timeout=600)
    except RuntimeError as exc:
        logger.warning("Мусиқа яратилмади, қисм мусиқасиз йиғилади: %s", exc)
        print(f"   ⚠️  Мусиқа яратилмади: {str(exc)[:200]}")
        return None
    return _save(r.content, out)
````

---

## 14. `episode_builder.py`

Қисмни йиғиш: видео, товуш, субтитр, ранг · тузатилган

````python
"""Битта қисмни йиғиш: вертикал 1080×1920, YouTube Shorts ва Instagram Reels учун.

Ҳар кадр учун:  русча овоз → калит расм (эталонлар билан) → расмдан видео → лаб синхрони (гапираётган
юз кўринса) → кадр қисми.  Кейин бутун қисм учун алоҳида товуш йўлаклари йиғилади:
  dialogue  — репликалар (ўз вақтида),
  foley     — кадр эффектлари (SFX),
  ambience  — жой муҳити (бир жойдаги кадрлар остида узлуксиз),
  music     — қисм мусиқаси (реплика пайтида автоматик пасаяди),
сўнг ранг (grade), русча субтитр, бош титр ва охирги «Продолжение следует…» қўшилади.

Ҳамма оралиқ файллар сақланади: қайта ишга туширилганда тайёрлари қайта ясалмайди (пул тежалади).
  clips/shot_NN.png  — калит расм   (ўчирсангиз — янгиси ва видео ҳам қайта ясалади)
  clips/shot_NN.mp4  — видео         (ўчирсангиз — фақат видео қайта ясалади)
  audio/…            — реплика овозлари (матн ўзгарса, автоматик янгиланади)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import sound
import visuals
from dubbing import audio_duration, synthesize
from series_planner import Character, EpisodeScript, Line, Location, SeriesPlan, Shot

logger = logging.getLogger(__name__)

W, H, FPS = 1080, 1920, 24
LEAD_IN = 0.3        # кадр бошидан биринчи репликагача
LINE_GAP = 0.3       # репликалар орасидаги пауза
TAIL = 0.45          # охирги репликадан кейин
MAX_STRETCH = 1.3    # видео нутқдан қисқа бўлса, шунча мартагача секинлаштирилади
SHORTS_LIMIT = 179.0 # Shorts/Reels: 3 дақиқадан кам

VOLUME = {"foley": 0.6, "ambience": 0.22, "music": 0.3}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


# ----------------------------- ffmpeg ёрдамчилари -----------------------------

def _run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg хатоси:\n{' '.join(cmd)[:3000]}\n{result.stderr[-3000:]}")


def media_duration(path: Path) -> float:
    return audio_duration(path)


def has_audio(path: Path) -> bool:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                             "stream=index", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(result.stdout.strip())


def _sha(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]


@dataclass
class Placed:
    """Товуш йўлагига жойлаштириладиган файл."""
    path: Path
    start: float
    length: float | None = None
    fade_in: float = 0.0
    fade_out: float = 0.0
    volume: float = 1.0
    loop: bool = False


def place_track(items: list[Placed], total: float, out: Path) -> Path:
    """Файлларни вақт бўйича битта стерео WAV йўлагига жойлаштиради (узунлиги total)."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    filters, labels = [], ["[0:a]"]
    for k, it in enumerate(items, 1):
        if it.loop:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", str(it.path)]
        chain = f"[{k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
        if it.length:
            chain += f",atrim=0:{it.length:.3f},asetpts=PTS-STARTPTS"
        if it.fade_in:
            chain += f",afade=t=in:st=0:d={it.fade_in:.2f}"
        if it.fade_out and it.length:
            chain += f",afade=t=out:st={max(0.0, it.length - it.fade_out):.3f}:d={it.fade_out:.2f}"
        if it.volume != 1.0:
            chain += f",volume={it.volume:.3f}"
        ms = max(0, int(round(it.start * 1000)))
        chain += f",adelay={ms}|{ms}"
        filters.append(chain + f"[a{k}]")
        labels.append(f"[a{k}]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,"
                   f"atrim=0:{total:.3f}[out]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(out)]
    _run(cmd)
    return out


# ----------------------------- Субтитрлар (ASS) -----------------------------

def _ass_time(t: float) -> str:
    cs = max(0, int(round(t * 100)))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def _caption_chunks(text: str, max_chars: int) -> list[str]:
    """Матнни аввал гап, кейин вергул, охири сўз чегарасидан max_chars дан қисқа бўлакларга бўлади."""
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = [text]
    for pattern in (r"(?<=[.!?…])\s+", r"(?<=[,;:])\s+|\s+(?=[—–]\s)", r"\s+"):
        parts = [p for p in re.split(pattern, text) if p]
        if len(parts) > 1:
            break
    if len(parts) == 1:
        return parts
    chunks: list[str] = []
    for p in parts:
        if chunks and len(chunks[-1]) + 1 + len(p) <= max_chars:
            chunks[-1] += " " + p
        else:
            chunks.append(p)
    out: list[str] = []
    for c in chunks:
        out += _caption_chunks(c, max_chars) if len(c) > max_chars and c != text else [c]
    return out


def split_caption(text: str, start: float, end: float, max_chars: int = 42) -> list[tuple[float, float, str]]:
    """Репликани экранда кўпи билан 2 қатор бўладиган субтитрларга бўлади (вақт белгилар сонига қараб)."""
    chunks = _caption_chunks(" ".join(text.split()), max_chars)
    total = sum(len(c) for c in chunks) or 1
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


# ----------------------------- Эталонлар -----------------------------

def ref_path(serial_dir: Path, key: str) -> Path:
    if key.startswith("@"):
        return serial_dir / "refs" / f"loc_{key[1:]}.png"
    return serial_dir / "refs" / f"{key}.png"


def ensure_references(plan: SeriesPlan, serial_dir: Path, redo: set[str] = frozenset(),
                      workers: int = 4) -> list[tuple[str, Path]]:
    """Барча персонаж ва жойлар учун эталон расмлар (йўқларини ясайди). [(изоҳ, файл)] қайтаради."""
    jobs: list[tuple[str, Character | Location, Path, str]] = []
    for c in plan.characters:
        jobs.append((c.id, c, ref_path(serial_dir, c.id), f"{c.name} — {c.role}"))
    for loc in plan.locations:
        jobs.append(("@" + loc.id, loc, ref_path(serial_dir, "@" + loc.id), f"📍 {loc.name}"))
    for key, _, path, _ in jobs:
        if key in redo or key.lstrip("@") in redo:
            path.unlink(missing_ok=True)
    missing = [(key, item, path) for key, item, path, _ in jobs if not path.exists()]

    def make(job):
        key, item, path = job
        print(f"🖼  Эталон: {key}")
        path.parent.mkdir(parents=True, exist_ok=True)
        visuals.make_reference(plan, item, path)

    if missing:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(make, missing))
    return [(caption, path) for _, _, path, caption in jobs if path.exists()]


# ----------------------------- Қисм йиғувчи -----------------------------

@dataclass
class Voiced:
    path: Path
    dur: float
    text: str
    speaker: str
    offset: float = 0.0


@dataclass
class ShotResult:
    shot: Shot
    part: Path
    length: float
    lines: list[Voiced]
    foley: Path | None = None
    start: float = 0.0
    lipsynced: bool = False
    notes: list[str] = field(default_factory=list)


class EpisodeBuilder:
    def __init__(self, plan: SeriesPlan, voices: dict, serial_dir: Path, episode_dir: Path):
        self.plan = plan
        self.voices = voices
        self.serial_dir = serial_dir
        self.dir = episode_dir
        self.locations = {loc.id: loc for loc in plan.locations}
        self.workers = max(1, int(os.environ.get("VISUAL_WORKERS", "4")))
        for sub in ("clips", "audio", "sound", "parts"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        (serial_dir / "sound").mkdir(parents=True, exist_ok=True)

    # ---------- овоз ----------

    def _voice(self, speaker: str) -> dict:
        return self.voices.get(speaker) or self.voices["narrator"]

    def voice_lines(self, key: str, lines: list[Line]) -> list[Voiced]:
        voiced: list[Voiced] = []
        # Овоз файли номида овозга таъсир қиладиган ҳамма созламалар бор: бирортаси ўзгарса,
        # реплика янгидан ясалади ва бир қисмда эски ва янги овоз аралашиб қолмайди.
        settings = (os.environ.get("ELEVENLABS_MODEL", "eleven_v3"), os.environ.get("ELEVENLABS_LANGUAGE_CODE", "ru"))
        t = LEAD_IN
        for i, line in enumerate(lines, 1):
            voice = self._voice(line.speaker)
            tag = _sha(line.text, line.delivery, voice.get("voice_id"), voice.get("stability", 0.5),
                       voice.get("similarity_boost", 0.75), *settings)
            path = self.dir / "audio" / f"{key}_{i:02d}_{tag}.mp3"
            if not path.exists():
                synthesize(line.text, voice, line.delivery, path)
            v = Voiced(path, audio_duration(path), line.text, line.speaker, t)
            t += v.dur + LINE_GAP
            voiced.append(v)
        return voiced

    @staticmethod
    def speech_length(voiced: list[Voiced]) -> float:
        return voiced[-1].offset + voiced[-1].dur + TAIL if voiced else 0.0

    # ---------- кадр ----------

    def refs_for(self, shot: Shot) -> list[tuple[str, Path]]:
        keys = list(shot.characters_in_shot) + ([f"@{shot.location_id}"] if shot.location_id else [])
        return [(k, p) for k in keys if (p := ref_path(self.serial_dir, k)).exists()]

    def keyframe(self, shot: Shot) -> Path:
        path = self.dir / "clips" / f"shot_{shot.number:02d}.png"
        if not path.exists():
            print(f"    🖼  кадр {shot.number}: {shot.description}")
            visuals.make_keyframe(self.plan, shot, self.refs_for(shot), path)
        return path

    def _ambience(self, location_id: str) -> Path | None:
        loc = self.locations.get(location_id)
        if not loc or not loc.ambience:
            return None
        path = self.serial_dir / "sound" / f"amb_{location_id}.mp3"
        if not path.exists():
            try:
                sound.ambience(loc.ambience, path)
            except Exception as exc:
                logger.warning("Муҳит товуши ясалмади (%s): %s", location_id, exc)
                return None
        return path

    def build_shot(self, shot: Shot) -> ShotResult:
        n = shot.number
        voiced = self.voice_lines(f"s{n:02d}", shot.lines)
        speech = self.speech_length(voiced)
        length = max(float(shot.duration_seconds), speech)
        key = self.keyframe(shot)

        clip = self.dir / "clips" / f"shot_{n:02d}.mp4"
        native = os.environ.get("VIDEO_NATIVE_AUDIO", "0") == "1" and not shot.lines
        if not clip.exists() or clip.stat().st_mtime < key.stat().st_mtime:
            seconds = visuals.clip_seconds(length)
            print(f"    🎥 кадр {n}: видео {seconds:g} с")
            amb = self.locations[shot.location_id].ambience if shot.location_id in self.locations else ""
            visuals.make_clip(self.plan, shot, key, seconds, clip, native, amb)
        clip_len = media_duration(clip)

        result = ShotResult(shot, self.dir / "parts" / f"shot_{n:02d}.mp4", length, voiced)
        video = clip
        if shot.speaker_on_screen and os.environ.get("LIPSYNC", "1") == "1":
            mine = [v for v in voiced if v.speaker == shot.speaker_on_screen]
            if mine:
                lips_len = max(clip_len, speech)
                lips = place_track([Placed(v.path, v.offset) for v in mine], lips_len,
                                   self.dir / "audio" / f"shot_{n:02d}_lips.wav")
                synced = self.dir / "clips" / f"shot_{n:02d}_ls_{_sha(hashlib.sha1(lips.read_bytes()).hexdigest(), clip.stat().st_mtime)}.mp4"
                if not synced.exists():
                    print(f"    👄 кадр {n}: лаб синхрони")
                    visuals.lipsync(clip, lips, synced)
                video = synced
                result.lipsynced = True

        vlen = media_duration(video)
        # Кадр узунлиги: нутқ видеога сиғса — видеодан узун бўлмайди (қотиб қолган кадр бўлмаслиги учун,
        # масалан script.json да duration оширилган, видео эса аввал қисқароқ ясалган бўлса).
        # Нутқ сиғмаса — видео секинлаштирилади (лаб синхрони йўқ кадрда), охири ушлаб турилади.
        length = min(length, vlen) if speech <= vlen else speech
        result.length = length
        factor = 1.0
        if not result.lipsynced and length > vlen:
            factor = min(MAX_STRETCH, length / vlen)
        if length > vlen * factor + 0.05:
            result.notes.append(f"видео {vlen:.1f}с, нутқ {speech:.1f}с — охирги кадр ушлаб турилади")
        vf = (f"setpts={factor:.4f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration=30,format=yuv420p")
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-an", "-vf", vf, "-t", f"{length:.3f}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", str(FPS), str(result.part)])

        # Эффектлар: видео моделининг ўз товуши ёки ElevenLabs SFX
        if native and has_audio(clip):
            result.foley = self.dir / "sound" / f"shot_{n:02d}_native.wav"
            _run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-ac", "2", "-ar", "48000", str(result.foley)])
        elif shot.sound:
            sfx = self.dir / "sound" / f"shot_{n:02d}_sfx_{_sha(shot.sound, round(length, 1))}.mp3"
            if not sfx.exists():
                try:
                    sound.sound_effect(shot.sound, length, sfx)
                except Exception as exc:
                    logger.warning("SFX ясалмади (кадр %s): %s", n, exc)
            result.foley = sfx if sfx.exists() else None
        return result

    # ---------- раскадровка ----------

    def storyboard(self, script: EpisodeScript) -> Path:
        """Фақат калит расмлар (арзон): видеога пул сарфлашдан олдин кўриб чиқиш учун."""
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            list(ex.map(self.keyframe, script.shots))
        rows = math.ceil(len(script.shots) / 6)
        out = self.dir / "storyboard.jpg"
        font = next((f for f in [os.environ.get("FONT_FILE", "")] + FONT_CANDIDATES if f and Path(f).exists()), None)
        if font:
            shutil.copy(font, self.dir / "sheet_font.ttf")
        sheet = self.dir / "sheet"
        shutil.rmtree(sheet, ignore_errors=True)
        sheet.mkdir()
        # Ҳар расмга кадрнинг ҳақиқий рақами ёзилади (сценарийдан кадр ўчирилган бўлса ҳам тўғри)
        for i, shot in enumerate(script.shots, 1):
            label = (f",drawtext=fontfile=sheet_font.ttf:text='{int(shot.number)}':x=12:y=10:fontsize=44:"
                     "fontcolor=white:borderw=3:bordercolor=black") if font else ""
            _run(["ffmpeg", "-y", "-v", "error", "-i", f"clips/shot_{shot.number:02d}.png",
                  "-vf", f"scale=270:480{label}", "-q:v", "3", f"sheet/{i:03d}.jpg"], cwd=self.dir)
        _run(["ffmpeg", "-y", "-v", "error", "-framerate", "1", "-i", "sheet/%03d.jpg",
              "-vf", f"tile=6x{rows}:padding=6:margin=6", "-frames:v", "1", "-q:v", "3", out.name], cwd=self.dir)
        shutil.rmtree(sheet, ignore_errors=True)
        return out

    # ---------- йиғиш ----------

    def build(self, script: EpisodeScript, is_last: bool = False, music_file: Path | None = None) -> Path:
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            results = list(ex.map(self.build_shot, script.shots))
        t = 0.0
        for r in results:
            r.start = t
            t += r.length
            for note in r.notes:
                print(f"    ⚠️  кадр {r.shot.number}: {note}")
        shots_end = t

        # Охирги лавҳа: «Продолжение следует…» ва диктор жумласи
        teaser = self.voice_lines("end", [Line(speaker="narrator", text=script.next_episode_teaser, delivery="")]) \
            if script.next_episode_teaser else []
        end_len = max(3.5, (self.speech_length(teaser) + 0.6) if teaser else 0.0)
        end_part = self._end_card(results[-1].part, end_len)
        total = shots_end + end_len
        if total > SHORTS_LIMIT:
            print(f"   ⚠️  Қисм {total:.0f} сония — Shorts/Reels 3 дақиқадан узунини қабул қилмайди. "
                  "Сценарийни қисқартиринг (script.json) ёки --minutes ни камайтиринг.")

        # Видео
        (self.dir / "parts.txt").write_text(
            "".join(f"file 'parts/{p.name}'\n" for p in [r.part for r in results] + [end_part]), encoding="utf-8")
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "parts.txt", "-c", "copy",
              "video_raw.mp4"], cwd=self.dir)

        # Товуш йўлаклари
        dialogue = [Placed(v.path, r.start + v.offset) for r in results for v in r.lines]
        dialogue += [Placed(v.path, shots_end + v.offset + 0.2) for v in teaser]
        place_track(dialogue, total, self.dir / "dialogue.wav")
        foley = [Placed(r.foley, r.start, r.length, 0.05, 0.25, VOLUME["foley"]) for r in results if r.foley]
        place_track(foley, total, self.dir / "foley.wav")
        place_track(self._ambience_runs(results, shots_end), total, self.dir / "ambience.wav")
        music = music_file or self._music(script, total)

        self._subtitles(script, results, teaser, shots_end, total, is_last)
        out = self._final_mix(total, music)
        self._timeline(script, results, total)
        print(f"   ✓ {total:.0f} сония, {len(results)} кадр, "
              f"{sum(r.lipsynced for r in results)} тасида лаб синхрони")
        return out

    def _end_card(self, last_part: Path, length: float) -> Path:
        still = self.dir / "parts" / "last.png"
        _run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", str(last_part), "-frames:v", "1",
              "-update", "1", str(still)])
        out = self.dir / "parts" / "end.mp4"
        _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(still), "-t", f"{length:.3f}",
              "-vf", f"scale={W}:{H},gblur=sigma=14,eq=brightness=-0.16:saturation=0.55,format=yuv420p",
              "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", str(FPS), str(out)])
        return out

    def _ambience_runs(self, results: list[ShotResult], shots_end: float) -> list[Placed]:
        """Бир жойдаги кетма-кет кадрлар остида узлуксиз муҳит товуши (чегараларда силлиқ ўтиш)."""
        runs: list[list] = []
        for r in results:
            if runs and runs[-1][0] == r.shot.location_id:
                runs[-1][2] = r.start + r.length
            else:
                runs.append([r.shot.location_id, r.start, r.start + r.length])
        items = []
        for i, (loc, start, end) in enumerate(runs):
            path = self._ambience(loc)
            if not path:
                continue
            if i == len(runs) - 1:
                end = shots_end + 2.0  # охирги лавҳада ҳам секин сўнади
            s = max(0.0, start - 0.4)
            length = end - s + 0.4
            items.append(Placed(path, s, length, 0.4 if i else 0.0, 0.8, VOLUME["ambience"], loop=True))
        return items

    def _music(self, script: EpisodeScript, total: float) -> Path | None:
        if os.environ.get("MUSIC", "1") != "1" or not script.music_prompt:
            return None
        prompt = f"{script.music_prompt}. Style: {self.plan.music_style}. Instrumental film score, no vocals."
        path = self.dir / "sound" / f"music_{_sha(prompt, round(total))}.mp3"
        if path.exists():
            return path
        print("    🎵 мусиқа басталанмоқда...")
        return sound.music(prompt, total + 2, path)

    def _font(self) -> tuple[str, str]:
        """(шрифт номи, fontsdir параметри). FONT_FILE берилса — ўша файл ишлатилади."""
        name = os.environ.get("SUB_FONT", "")
        file = os.environ.get("FONT_FILE", "")
        if file and Path(file).exists():
            fonts = self.dir / "fonts"
            fonts.mkdir(exist_ok=True)
            shutil.copy(file, fonts / Path(file).name)
            if not name:
                probe = subprocess.run(["fc-scan", "--format", "%{family[0]}", file], capture_output=True, text=True) \
                    if shutil.which("fc-scan") else None
                name = (probe.stdout.strip() if probe and probe.returncode == 0 else "") or Path(file).stem
            return name, ":fontsdir=fonts"
        return name or ("Arial" if os.name == "nt" else "DejaVu Sans"), ""

    def _subtitles(self, script: EpisodeScript, results: list[ShotResult], teaser: list[Voiced],
                   shots_end: float, total: float, is_last: bool) -> None:
        font, _ = self._font()
        margin = int(os.environ.get("SUB_MARGIN", "520"))  # пастдан: Shorts/Reels тугмалари ва ёзуви тагида қолмасин
        head = (
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Sub,{font},62,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1.5,2,90,90,{margin},204\n"
            f"Style: Narr,{font},58,&H00E8F0F5,&H000000FF,&H00101010,&H80000000,0,-1,0,0,100,100,0,0,1,4,1.5,2,90,90,{margin},204\n"
            f"Style: Title,{font},92,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,8,70,70,250,204\n"
            f"Style: Episode,{font},56,&H00E0E0E0,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,1,0,1,4,1.5,8,70,70,370,204\n"
            f"Style: End,{font},70,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,5,80,80,0,204\n"
            "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        events = []

        def add(a: float, b: float, style: str, text: str, fx: str = "") -> None:
            events.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},{style},,0,0,0,,{fx}{_ass_text(text)}")

        def caption(text: str, a: float, b: float, style: str) -> None:
            pieces = split_caption(text, a, b)
            for i, (s, e, chunk) in enumerate(pieces):
                add(s, e + (0.15 if i == len(pieces) - 1 else 0.0), style, chunk)  # охиргиси бироз узоқроқ

        if os.environ.get("BURN_SUBTITLES", "1") == "1":
            for r in results:
                for v in r.lines:
                    a = r.start + v.offset
                    caption(v.text, a, a + v.dur, "Narr" if v.speaker == "narrator" else "Sub")
            for v in teaser:
                a = shots_end + v.offset + 0.2
                caption(v.text, a, a + v.dur, "Narr")
        title_end = min(3.4, results[0].length if results else 3.4)
        add(0.15, title_end, "Title", self.plan.series_title.upper(), r"{\fad(300,400)}")
        add(0.35, title_end, "Episode", f"Серия {script.number} · «{script.title}»", r"{\fad(300,400)}")
        add(shots_end + 0.1, total, "End", "Конец" if is_last else "Продолжение следует…", r"{\fad(400,300)}")
        (self.dir / "subs.ass").write_text(head + "\n".join(events) + "\n", encoding="utf-8")

    def _final_mix(self, total: float, music: Path | None) -> Path:
        _, fontsdir = self._font()
        grade = ""
        if os.environ.get("GRADE", "film") == "film":
            # Барча кадрларга ягона «кино» ранги: бироз контраст, юмшоқ виньетка, енгил плёнка доначаси
            grade = "eq=contrast=1.05:saturation=0.95:gamma=0.98,vignette=PI/5,noise=c0s=3:c0f=t,"
        vf = (f"[0:v]{grade}subtitles=subs.ass{fontsdir},fade=t=in:st=0:d=0.25,"
              f"fade=t=out:st={max(0.0, total - 0.5):.3f}:d=0.5,format=yuv420p[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", "video_raw.mp4", "-i", "dialogue.wav", "-i", "foley.wav",
               "-i", "ambience.wav"]
        if music:
            cmd += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
            af = (
                "[1:a]asplit=2[dlg][sc];"
                f"[4:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{total:.3f},"
                f"asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.5,afade=t=out:st={max(0.0, total - 2.5):.3f}:d=2.5,"
                f"volume={VOLUME['music']}[m0];"
                "[sc]aformat=sample_fmts=fltp:channel_layouts=stereo[sc2];"
                "[m0][sc2]sidechaincompress=threshold=0.015:ratio=8:attack=20:release=450[mus];"
                "[dlg][2:a][3:a][mus]amix=inputs=4:normalize=0:duration=first,"
            )
        else:
            af = "[1:a][2:a][3:a]amix=inputs=3:normalize=0:duration=first,"
        af += "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
        # Аввал вақтинчалик файлга ёзилади: жараён узилса, чала видео «тайёр қисм» бўлиб қолмайди
        tmp = self.dir / "episode.tmp.mp4"
        tmp.unlink(missing_ok=True)
        cmd += ["-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
                tmp.name]
        try:
            _run(cmd, cwd=self.dir)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        if media_duration(tmp) < total - 1.0:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Йиғилган видео кутилганидан қисқа чиқди ({total:.1f} с бўлиши керак эди)")
        os.replace(tmp, self.dir / "episode.mp4")
        return self.dir / "episode.mp4"

    def _timeline(self, script: EpisodeScript, results: list[ShotResult], total: float) -> None:
        data = {
            "episode": script.number, "duration": round(total, 2),
            "shots": [{
                "shot": r.shot.number, "start": round(r.start, 2), "length": round(r.length, 2),
                "type": r.shot.shot_type, "location": r.shot.location_id, "lipsync": r.lipsynced,
                "lines": [{"at": round(r.start + v.offset, 2), "speaker": v.speaker, "text": v.text} for v in r.lines],
            } for r in results],
        }
        (self.dir / "timeline.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
````

---

## 15. `telegram_sender.py`

Telegram'га юбориш · ўзгармаган

````python
"""Telegram Bot API: хабар/видео юбориш, каналга жойлаш, ботга юборилган файлни олиш.

TELEGRAM_CHAT_ID    — сизнинг (админ) чатингиз: олдиндан кўриш ва хабарлар учун
TELEGRAM_CHANNEL_ID — сериал чиқадиган канал (@kanal_nomi). Бот канал админи бўлиши керак.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

TG_LIMIT = 4000  # Telegram хабари 4096 белгигача


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ўрнатилмаган")
    return token


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{_token()}/{method}"


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} ўрнатилмаган (.env файлига қўшинг)")
    return value


def admin_chat() -> str:
    return _env("TELEGRAM_CHAT_ID")


def channel() -> str:
    return _env("TELEGRAM_CHANNEL_ID")


def _check(r: requests.Response) -> dict:
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram хатоси: {data.get('description')}")
    return data["result"]


def send_text(text: str, chat_id: str | None = None) -> None:
    chat_id = chat_id or admin_chat()
    for start in range(0, len(text), TG_LIMIT):
        _check(requests.post(_api("sendMessage"), data={"chat_id": chat_id, "text": text[start:start + TG_LIMIT]}, timeout=60))


def send_video(video: Path, caption: str = "", chat_id: str | None = None) -> dict:
    with open(video, "rb") as f:
        return _check(requests.post(
            _api("sendVideo"),
            data={"chat_id": chat_id or admin_chat(), "caption": caption[:1000], "supports_streaming": "true"},
            files={"video": (video.name, f, "video/mp4")},
            timeout=900,
        ))


def send_document(path: Path, caption: str = "", chat_id: str | None = None) -> None:
    with open(path, "rb") as f:
        _check(requests.post(
            _api("sendDocument"),
            data={"chat_id": chat_id or admin_chat(), "caption": caption[:1000]},
            files={"document": (path.name, f)},
            timeout=300,
        ))


def send_photo(path: Path, caption: str = "", chat_id: str | None = None) -> None:
    with open(path, "rb") as f:
        _check(requests.post(
            _api("sendPhoto"),
            data={"chat_id": chat_id or admin_chat(), "caption": caption[:1000]},
            files={"photo": (path.name, f)},
            timeout=300,
        ))


def send_album(items: list[tuple[Path, str]], chat_id: str | None = None) -> None:
    """Расмларни 10 тадан альбом қилиб юборади: items = [(файл, изоҳ)]."""
    for start in range(0, len(items), 10):
        batch = items[start:start + 10]
        if len(batch) == 1:
            send_photo(batch[0][0], batch[0][1], chat_id)
            continue
        media, files, handles = [], {}, []
        try:
            for i, (path, caption) in enumerate(batch):
                name = f"photo{i}"
                handles.append(open(path, "rb"))
                files[name] = (path.name, handles[-1])
                media.append({"type": "photo", "media": f"attach://{name}", "caption": caption[:1000]})
            _check(requests.post(
                _api("sendMediaGroup"),
                data={"chat_id": chat_id or admin_chat(), "media": json.dumps(media, ensure_ascii=False)},
                files=files,
                timeout=600,
            ))
        finally:
            for h in handles:
                h.close()


def send_audio(path: Path, caption: str = "", chat_id: str | None = None) -> None:
    with open(path, "rb") as f:
        _check(requests.post(
            _api("sendAudio"),
            data={"chat_id": chat_id or admin_chat(), "caption": caption[:1000]},
            files={"audio": (path.name, f)},
            timeout=300,
        ))


def latest_document_from_admin() -> dict | None:
    """Админ чатидан ботга юборилган охирги файл (document)."""
    updates = _check(requests.get(_api("getUpdates"), params={"allowed_updates": '["message"]'}, timeout=60))
    admin = str(admin_chat())
    for update in reversed(updates):
        msg = update.get("message") or {}
        if str(msg.get("chat", {}).get("id")) == admin and msg.get("document"):
            return msg["document"]
    return None


def download_file(file_id: str, dest: Path) -> Path:
    """Бот API орқали 20 МБ гача файлни юклаб олади."""
    info = _check(requests.get(_api("getFile"), params={"file_id": file_id}, timeout=60))
    url = f"https://api.telegram.org/file/bot{_token()}/{info['file_path']}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for part in r.iter_content(1 << 20):
                f.write(part)
    return dest
````

---

## 16. `video.py`

Telegram учун сиқиш + эски трейлер режими видеоси · тузатилган

````python
"""Видео генерация (fal.ai орқали Kling ва бошқа моделлар) ва клипларни бирлаштириш."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


def _retry(func, what: str, attempts: int = 4, base_delay: float = 3.0):
    """Тармоқ хатоси ёки вақтинчалик 429/5xx да экспоненциал кутиш билан қайта уриниш."""
    for attempt in range(1, attempts + 1):
        try:
            resp = func()
            if getattr(resp, "status_code", 200) in RETRY_STATUSES and attempt < attempts:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # Доимий хато (400, 401, 403 ва ҳ.к.) — қайта урини маслик
            if isinstance(exc, requests.HTTPError) and status is not None and status not in RETRY_STATUSES:
                raise
            if attempt == attempts:
                logger.error("%s: %d уринишдан кейин ҳам муваффақиятсиз: %s", what, attempts, exc)
                raise
            delay = base_delay * 2 ** (attempt - 1)
            logger.warning("%s: уриниш %d/%d хато (%s). %.0f сонидан кейин қайта.", what, attempt, attempts, exc, delay)
            time.sleep(delay)

FAL_QUEUE_URL = "https://queue.fal.run"
DEFAULT_FAL_MODEL = "fal-ai/kling-video/v2.1/standard/text-to-video"


def _kling_duration(duration: int) -> int:
    """Kling фақат 5 ёки 10 секундни қабул қилади."""
    return 10 if int(duration) >= 8 else 5


def _headers() -> dict[str, str]:
    key = os.environ.get("FAL_KEY")
    if not key:
        raise RuntimeError("FAL_KEY ўрнатилмаган (.env файлига қўшинг)")
    return {"Authorization": f"Key {key}", "Content-Type": "application/json"}


XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_GROK_MODEL = "grok-imagine-video-1.5-lite"


def _grok_generate(
    prompt: str,
    out_path: Path,
    duration: int,
    aspect_ratio: str,
    timeout_s: int = 1200,
    poll_every_s: int = 5,
) -> Path:
    """xAI Grok Imagine видео. Ҳужжат: docs.x.ai/developers/model-capabilities/video/generation"""
    key = os.environ.get("XAI_API_KEY")
    if not key:
        raise RuntimeError("XAI_API_KEY ўрнатилмаган (.env файлига қўшинг)")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    payload = {
        "model": os.environ.get("GROK_MODEL", DEFAULT_GROK_MODEL),
        "prompt": prompt,
        "duration": max(1, min(15, int(duration))),
        "aspect_ratio": aspect_ratio,
        "resolution": os.environ.get("GROK_RESOLUTION", "720p"),
        # Ўз овозини яратмасин: ўзбекча дубляж фақат бизнинг TTS овози бўлсин
        "generate_audio": False,
    }

    # 1) Сўровни юбориш → request_id
    started = time.time()
    resp = _retry(
        lambda: requests.post(f"{XAI_BASE_URL}/videos/generations", json=payload, headers=headers, timeout=60),
        "Grok сўров юбориш",
    )
    resp.raise_for_status()
    request_id = resp.json()["request_id"]
    logger.info("Grok видео сўрови юборилди: %s (%ss, %s)", request_id, payload["duration"], payload["model"])

    # 2) Тайёр бўлишини кутиш: pending → done | failed
    deadline = time.time() + timeout_s
    while True:
        data = _retry(
            lambda: requests.get(f"{XAI_BASE_URL}/videos/{request_id}", headers=headers, timeout=60),
            "Grok статус",
        ).json()
        state = data.get("status")
        if state == "done":
            logger.info("Grok видео тайёр: %s (%.0f сония)", request_id, time.time() - started)
            break
        if state == "failed":
            raise RuntimeError(f"Grok видео хатоси: {data.get('error')}")
        if time.time() > deadline:
            raise TimeoutError(f"Grok видео {timeout_s} сонияда тайёр бўлмади: {request_id}")
        time.sleep(poll_every_s)

    # 3) Видео ҳаволасини юклаб олиш (ҳавола вақтинчалик, дарров сақлаймиз)
    video_url = (data.get("video") or {}).get("url")
    if not video_url:
        raise RuntimeError(f"Жавобда видео ҳаволаси йўқ: {data}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Аввал вақтинчалик файлга юкланади: узилган юклаш тайёр кадр сифатида қолмайди
    tmp_path = out_path.with_suffix(".part")
    with requests.get(video_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for part in r.iter_content(chunk_size=1 << 20):
                f.write(part)
    tmp_path.replace(out_path)
    return out_path


def generate_clip(
    prompt: str,
    out_path: Path,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    timeout_s: int = 1200,
    poll_every_s: int = 10,
) -> Path:
    """Битта клипни генерация қилади ва .mp4 сифатида сақлайди.

    VIDEO_PROVIDER=grok (стандарт) ёки kling. Grok учун XAI_API_KEY, Kling учун FAL_KEY керак.
    """
    provider = os.environ.get("VIDEO_PROVIDER", "grok").lower()
    if provider == "grok":
        return _grok_generate(prompt, out_path, duration, aspect_ratio, timeout_s, poll_every_s)
    if provider != "kling":
        raise ValueError(f"Номаълум VIDEO_PROVIDER: {provider} (grok ёки kling бўлиши керак)")

    model = os.environ.get("FAL_MODEL", DEFAULT_FAL_MODEL)
    payload = {
        "prompt": prompt,
        "duration": str(_kling_duration(duration)),
        "aspect_ratio": aspect_ratio,
        "negative_prompt": "text, subtitles, watermark, logo, blurry, distorted faces",
    }

    # 1) Навбатга қўйиш
    resp = _retry(
        lambda: requests.post(f"{FAL_QUEUE_URL}/{model}", json=payload, headers=_headers(), timeout=60),
        "Kling сўров юбориш",
    )
    resp.raise_for_status()
    job = resp.json()
    status_url = job["status_url"]
    response_url = job["response_url"]

    # 2) Тайёр бўлишини кутиш
    deadline = time.time() + timeout_s
    while True:
        status = _retry(
            lambda: requests.get(status_url, headers=_headers(), timeout=60),
            "Kling статус",
        ).json()
        state = status.get("status")
        if state == "COMPLETED":
            break
        if state in ("FAILED", "ERROR", "CANCELLED"):
            raise RuntimeError(f"Видео генерация хатоси: {status}")
        if time.time() > deadline:
            raise TimeoutError(f"Видео {timeout_s} сонияда тайёр бўлмади: {status_url}")
        time.sleep(poll_every_s)

    # 3) Натижани олиш ва юклаб олиш
    result = requests.get(response_url, headers=_headers(), timeout=60).json()
    video_url = (result.get("video") or {}).get("url")
    if not video_url:
        raise RuntimeError(f"Жавобда видео ҳаволаси йўқ: {result}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".part")
    with requests.get(video_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for part in r.iter_content(chunk_size=1 << 20):
                f.write(part)
    tmp_path.replace(out_path)
    return out_path


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    """ffmpeg ёрдамида клипларни битта трейлерга бирлаштиради."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg топилмади. Ўрнатинг: https://ffmpeg.org/download.html")

    list_file = out_path.with_suffix(".txt")
    # ffmpeg concat рўйхатида апострофни '\'' кўринишда экранлаш керак
    lines = []
    for c in clips:
        safe = c.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe}'\n")
    list_file.write_text("".join(lines), encoding="utf-8")

    # Клиплар бир моделдан бўлгани учун одатда тез нусхалаш (-c copy) етарли
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)]
    first = subprocess.run(cmd, capture_output=True)
    if first.returncode != 0:
        # Биринчи уриниш нега йиқилганини логлаймиз, акс ҳолда сабаб йўқолади
        logger.warning("FFmpeg -c copy муваффақиятсиз: %s", first.stderr.decode("utf-8", "ignore")[-500:])
        # Формат фарқ қилса — қайта кодлаш
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_path)]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg қайта кодлаш хатоси: {res.stderr.decode('utf-8', 'ignore')[-1500:]}")
    list_file.unlink(missing_ok=True)
    return out_path


def compress_for_telegram(video: Path, max_mb: int = 49) -> Path:
    """Telegram бот API 50 МБ гача файл қабул қилади — каттасини сиқади."""
    if video.stat().st_size <= max_mb * 1024 * 1024:
        return video
    out = video.with_name(video.stem + "_tg.mp4")
    # Қисқа томони 720 px бўлади (вертикал видео 720×1280, горизонтал 1280×720)
    scale = "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'"
    rate = ["-crf", "26"]
    for _ in range(2):
        res = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video), "-vf", scale, "-c:v", "libx264", *rate, "-preset", "medium",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)],
            capture_output=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg сиқиш хатоси: {res.stderr.decode('utf-8', 'ignore')[-1500:]}")
        if out.stat().st_size <= max_mb * 1024 * 1024:
            break
        # Ҳали ҳам катта — узунликка қараб битрейтни ҳисоблаймиз
        seconds = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
            capture_output=True, text=True).stdout.strip() or 60)
        kbps = int(max_mb * 8 * 1024 * 0.9 / seconds) - 128
        rate = ["-b:v", f"{max(300, kbps)}k", "-maxrate", f"{max(300, kbps)}k", "-bufsize", f"{2 * max(300, kbps)}k"]
    return out
````

---

## 17. `check_script.py`

Сценарий текшируви · тузатилган

````python
"""Сценарий текшируви: кетма-кет такрорланган сўзлар, бир хил репликалар ва кўп учрайдиган иборалар.

Ишлатиш:
    python check_script.py output\\serials\\otgan_kunlar\\episode_01\\script.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from series_planner import MAX_SPEECH_PER_SHOT, long_speech_shots

WORD = re.compile(r"[\w'ʻ’]+", re.UNICODE)
PHRASE_LEN = 3          # нечта сўзли иборалар текширилади
PHRASE_MIN_COUNT = 3    # шунча ва ундан кўп учраса — огоҳлантирамиз


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def collect(script: dict) -> list[tuple[str, str]]:
    """(жой, матн) жуфтлари: ҳар репликани ва диктор матнини йиғади."""
    items: list[tuple[str, str]] = []
    items.append(("recap", script.get("recap", "")))
    items.append(("teaser", script.get("next_episode_teaser", "")))
    for shot in script.get("shots", []):
        for line in shot.get("lines", []):
            items.append((f"кадр {shot.get('number')} / {line.get('speaker')}", line.get("text", "")))
    return items


def check(script: dict) -> list[str]:
    problems: list[str] = []
    items = collect(script)

    # 1) Кетма-кет такрорланган сўзлар: "бу бу", "ҳа ҳа"
    for where, text in items:
        ws = words(text)
        for a, b in zip(ws, ws[1:]):
            if a == b and len(a) > 1:
                problems.append(f"[кетма-кет] {where}: «{a} {b}» — «{text[:80]}»")

    # 2) Бир хил ёки деярли бир хил репликалар
    seen: dict[str, str] = {}
    for where, text in items:
        key = " ".join(words(text))
        if len(key) < 12:
            continue
        if key in seen:
            problems.append(f"[такрор реплика] {where} = {seen[key]}: «{text[:80]}»")
        else:
            seen[key] = where

    # 3) Бутун сериал бўйича кўп учрайдиган иборалар
    counter: Counter = Counter()
    for _, text in items:
        ws = words(text)
        for i in range(len(ws) - PHRASE_LEN + 1):
            phrase = " ".join(ws[i:i + PHRASE_LEN])
            if all(len(w) > 2 for w in ws[i:i + PHRASE_LEN]):
                counter[phrase] += 1
    for phrase, n in counter.most_common():
        if n < PHRASE_MIN_COUNT:
            break
        problems.append(f"[кўп учрайди] «{phrase}» — {n} марта")

    # 4) Кадрга сиғмайдиган нутқ (serial.py билан бир хил қоида)
    for number, seconds in long_speech_shots(script):
        problems.append(f"[узун нутқ] кадр {number}: ~{seconds} с нутқ (кадрга {MAX_SPEECH_PER_SHOT:g} с гача сиғади) "
                        "— репликани қисқартиринг ёки кадрни иккига бўлинг")

    return problems


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = Path(sys.argv[1])
    script = json.loads(path.read_text(encoding="utf-8"))
    problems = check(script)
    if not problems:
        print("✓ Сценарийда такрорлар топилмади.")
        return 0
    print(f"⚠ Топилган муаммолар: {len(problems)}")
    for p in problems:
        print(" -", p)
    return 2


if __name__ == "__main__":
    sys.exit(main())
````

---

## 18. `main.py`

Эски трейлер режими (сериалга алоқаси йўқ) · тузатилган

````python
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
````

---

## 19. `scenario.py`

Эски трейлер режими сценарийси (сериалга алоқаси йўқ) · тузатилган

````python
"""Claude ёрдамида китобни таҳлил қилиш ва трейлер сценарийсини яратиш."""

from __future__ import annotations

from pydantic import BaseModel, Field

from book_reader import split_into_chunks
from claude_client import structured, text

# Claude Opus 5.5 контексти 1M токен. Кирилл матни ~2-3 белги/токен,
# шунинг учун 800 минг белгигача бўлган китоб бир сўровда юборилади.
# Ундан узун бўлса — аввал бўлакма-бўлак қисқача мазмун олинади.
MAX_CHARS_SINGLE_REQUEST = 800_000
CHUNK_CHARS = 300_000


class Scene(BaseModel):
    number: int = Field(description="Саҳна тартиб рақами, 1 дан бошлаб")
    title: str = Field(description="Саҳна номи (китоб тилида)")
    what_happens: str = Field(description="Китобда бу саҳнада нима бўлади (китоб тилида, 1-3 жумла)")
    narration: str = Field(description="Диктор матни ёки экрандаги ёзув (китоб тилида, 1-2 қисқа жумла)")
    video_prompt: str = Field(
        description=(
            "Видео модели (Kling/Veo) учун ИНГЛИЗ тилидаги батафсил промпт: "
            "кадр, камера ҳаракати, ёруғлик, муҳит, персонажлар ташқи кўриниши, кайфият, кино услуби. "
            "Матн, ёзув ва логотипларни сўрама."
        )
    )
    duration_seconds: int = Field(description="Клип узунлиги: фақат 5 ёки 10")


class TrailerScript(BaseModel):
    book_title: str
    language: str = Field(description="Китоб тили: uzbek, russian, english ва ҳ.к.")
    logline: str = Field(description="Бир жумлали асосий ғоя (китоб тилида)")
    visual_style: str = Field(description="Барча клиплар учун умумий визуал услуб (инглизча)")
    characters: str = Field(description="Асосий персонажлар ташқи кўриниши (инглизча), барча клипларда бир хил бўлиши учун")
    full_script: str = Field(description="Тўлиқ трейлер сценарийси (китоб тилида)")
    scenes: list[Scene]


SYSTEM_PROMPT = """Сен тажрибали кино сценаристи ва трейлер монтажчисисан.
Вазифанг — берилган китоб асосида қисқа кинематографик трейлер сценарийсини тузиш.

Қоидалар:
- Китобнинг энг кучли, визуал жиҳатдан таъсирли саҳналарини танла; сюжетнинг охирини (спойлер) очма.
- Саҳналар трейлер мантиқида бўлсин: таништириш → зиддият → кескинлик ошиши → сирли якун.
- narration, title, what_happens, logline ва full_script — китоб ёзилган тилда бўлсин.
- video_prompt — доим инглиз тилида, бир саҳнани тасвирловчи мустақил промпт бўлсин:
  видео модели олдинги саҳналарни билмайди, шунинг учун ҳар промптга персонаж ташқи кўриниши
  ва умумий визуал услубни қайта ёз (персонажлар клиплар орасида бир хил кўриниши учун).
- video_prompt да экрандаги матн, ёзув, субтитр ёки логотип сўрама.
- duration_seconds фақат 5 ёки 10 бўлсин."""


def _summarize_chunk(chunk: str, index: int, total: int) -> str:
    """Жуда узун китоб учун: битта бўлакнинг батафсил қисқача мазмуни."""
    return text(
        f"Бу китобнинг {index}/{total}-қисми. Уни китоб тилида батафсил қисқача баён қил: "
        "воқеалар кетма-кетлиги, персонажлар (ташқи кўриниши билан), жойлар, "
        "энг визуал ва драматик лаҳзалар.\n\n"
        f"<book_part>\n{chunk}\n</book_part>",
        effort="medium", max_tokens=16000,
    )


def create_trailer_script(book_text: str, num_scenes: int = 6, extra_wishes: str = "") -> TrailerScript:
    if len(book_text) <= MAX_CHARS_SINGLE_REQUEST:
        book_block = f"<book>\n{book_text}\n</book>"
    else:
        chunks = split_into_chunks(book_text, CHUNK_CHARS)
        summaries = []
        for i, chunk in enumerate(chunks, 1):
            print(f"  • Китоб қисми {i}/{len(chunks)} таҳлил қилинмоқда...")
            summaries.append(_summarize_chunk(chunk, i, len(chunks)))
        joined = "\n\n".join(f"<part index=\"{i}\">\n{s}\n</part>" for i, s in enumerate(summaries, 1))
        book_block = f"<book_summary>\n{joined}\n</book_summary>"

    wishes = f"\n\nҚўшимча истаклар: {extra_wishes}" if extra_wishes else ""
    prompt = (
        f"{book_block}\n\n"
        f"Шу китоб асосида {num_scenes} та саҳнадан иборат трейлер сценарийсини туз.{wishes}"
    )

    script: TrailerScript = structured(
        SYSTEM_PROMPT, prompt, TrailerScript, effort="high", max_tokens=64000,
        hint="Саҳналар сонини камайтиринг.",
    )

    # Видео модели фақат 5 ёки 10 сония қабул қилади
    for scene in script.scenes:
        scene.duration_seconds = 10 if scene.duration_seconds >= 8 else 5
    return script
````
