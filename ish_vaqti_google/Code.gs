/**
 * ИШ ВАҚТИ — Телеграм бот + Google Таблица (серверсиз).
 *
 * Планшетдаги Телеграмда ходимлар «✅ Ном келдим» / «🏁 Ном кетдим» тугмасини босади.
 * Раҳбарга хабар боради, соатлар Google Таблицага ёзилади.
 *
 * Ўрнатиш: README.md га қаранг. Қисқача:
 *   1) setup  функциясини ишга туширинг (варақлар яратилади)
 *   2) «Созламалар» варағига BOT_TOKEN ёзинг
 *   3) Web app сифатида deploy қилинг, URL ни WEBAPP_URL га ёзинг
 *   4) ulash  функциясини ишга туширинг
 */

const TZ = 'Asia/Tashkent';
const SH_SET = 'Созламалар';
const SH_WORK = 'Ходимлар';
const SH_LOG = 'Журнал';

const OYLAR = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль',
  'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
const KUNLAR = ['Якшанба', 'Душанба', 'Сешанба', 'Чоршанба', 'Пайшанба', 'Жума', 'Шанба'];

const DEFAULTS = [
  ['BOT_TOKEN', '', 'BotFather берган токен'],
  ['WEBAPP_URL', '', 'Deploy қилгандан кейинги Web app манзили (…/exec)'],
  ['RELAY_URL', '', 'Cloudflare Worker манзили (…workers.dev). Телеграм шу манзилга уланади'],
  ['ADMIN_IDS', '', 'Хабар оладиган раҳбарлар (бўш бўлса — ботга биринчи /start ёзган одам)'],
  ['PLANSHET_IDS', '', 'Тугмалар ишлайдиган Телеграм аккаунтлар (бот орқали рухсат берилади)'],
  ['ISH_BOSHLANISH', '09:00', 'Иш бошланиши — кечикишни ҳисоблаш учун'],
  ['ISH_TUGASH', '18:00', '«Кетдим» босилмаса шу вақтгача ҳисобланади'],
  ['KELMAGANLAR_VAQTI', '09:30', 'Шу вақтда «ким келмади» хабари келади'],
  ['ESLATMA_VAQTI', '19:00', 'Шу вақтда «кетдим босилмади» эслатмаси келади'],
  ['KUNLIK_HISOBOT', '20:00', 'Кунлик ҳисобот вақти'],
  ['DAM_OLISH', 'Якшанба', 'Дам олиш кунлари (вергул билан), бу кунлари «келмади» хабари келмайди'],
];
const DEFAULT_WORKERS = ['Баходир', 'Тулаган', 'Иброхим', 'Шавкат'];

// Агар Apps Script таблица ичидан эмас, алоҳида очилган бўлса — таблица ID сини шу ерга ёзинг
// (таблица манзилидаги /d/ ва /edit орасидаги матн). Таблица ичидан очилган бўлса — бўш қолдиринг.
const SPREADSHEET_ID = '';

// ====================================================================== ёрдамчилар

function fmt(d, p) { return Utilities.formatDate(d, TZ, p); }
function todayStr() { return fmt(new Date(), 'yyyy-MM-dd'); }
function nowHM() { return fmt(new Date(), 'HH:mm'); }
function pad(n) { return (n < 10 ? '0' : '') + n; }
function toMin(hm) { const p = hm.split(':'); return Number(p[0]) * 60 + Number(p[1]); }
function maxHM(a, b) { return toMin(a) >= toMin(b) ? a : b; }
function minHM(a, b) { return toMin(a) <= toMin(b) ? a : b; }
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

function dur(start, end) {
  let d = toMin(end) - toMin(start);
  if (d < 0) d += 1440; // ярим тундан кейин кетган бўлса
  return d;
}

function fmtDur(min) {
  const h = Math.floor(min / 60), m = min % 60;
  if (h && m) return h + ' соат ' + m + ' дақ';
  if (h) return h + ' соат';
  return m + ' дақ';
}

function normHM(s) {
  const m = String(s).trim().match(/^(\d{1,2})[:.](\d{2})$/);
  if (!m) return null;
  const h = Number(m[1]), mi = Number(m[2]);
  if (h > 23 || mi > 59) return null;
  return pad(h) + ':' + m[2];
}

/** «05.11» ёки «05.11.2026» → «2026-11-05» */
function parseDay(s) {
  const m = String(s || '').trim().match(/^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$/);
  if (!m) return null;
  const y = m[3] ? Number(m[3]) : Number(todayStr().slice(0, 4));
  const mo = Number(m[2]), d = Number(m[1]);
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  return y + '-' + pad(mo) + '-' + pad(d);
}

function dayTitle(ds) {
  const p = ds.split('-').map(Number);
  const wd = new Date(Date.UTC(p[0], p[1] - 1, p[2], 12)).getUTCDay();
  return pad(p[2]) + '.' + pad(p[1]) + '.' + p[0] + ', ' + KUNLAR[wd];
}
function shortDay(ds) { const p = ds.split('-'); return p[2] + '.' + p[1]; }

function addDays(ds, n) {
  const p = ds.split('-').map(Number);
  const d = new Date(Date.UTC(p[0], p[1] - 1, p[2] + n, 12));
  return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate());
}
function weekday(ds) { const p = ds.split('-').map(Number); return new Date(Date.UTC(p[0], p[1] - 1, p[2], 12)).getUTCDay(); }
function daysInMonth(y, m) { return new Date(Date.UTC(y, m, 0)).getUTCDate(); }

// ====================================================================== таблица

function ss() {
  const id = PropertiesService.getScriptProperties().getProperty('SS_ID');
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
}
function sh(name) { return ss().getSheetByName(name); }

let CFG_CACHE = null;
function cfg() {
  if (CFG_CACHE) return CFG_CACHE;
  const s = sh(SH_SET);
  const rows = s.getRange(2, 1, Math.max(s.getLastRow() - 1, 1), 2).getDisplayValues();
  const kv = {};
  rows.forEach(r => { if (r[0]) kv[String(r[0]).trim()] = String(r[1]).trim(); });
  const ids = v => (v || '').split(/[,\s]+/).filter(Boolean).map(String);
  const w = sh(SH_WORK);
  const workers = w.getRange(2, 1, Math.max(w.getLastRow() - 1, 1), 1).getDisplayValues()
    .map(r => String(r[0]).trim()).filter(Boolean);
  CFG_CACHE = {
    token: kv.BOT_TOKEN || '',
    url: kv.WEBAPP_URL || '',
    relay: kv.RELAY_URL || '',
    admins: ids(kv.ADMIN_IDS),
    tablets: ids(kv.PLANSHET_IDS),
    workStart: normHM(kv.ISH_BOSHLANISH) || '09:00',
    workEnd: normHM(kv.ISH_TUGASH) || '18:00',
    absentTime: normHM(kv.KELMAGANLAR_VAQTI) || '09:30',
    remindTime: normHM(kv.ESLATMA_VAQTI) || '19:00',
    reportTime: normHM(kv.KUNLIK_HISOBOT) || '20:00',
    restDays: (kv.DAM_OLISH || '').split(',').map(x => x.trim().toLowerCase()).filter(Boolean),
    workers: workers,
  };
  return CFG_CACHE;
}

function setCfg(key, val) {
  const s = sh(SH_SET);
  const keys = s.getRange(2, 1, Math.max(s.getLastRow() - 1, 1), 1).getDisplayValues();
  for (let i = 0; i < keys.length; i++) {
    if (String(keys[i][0]).trim() === key) { s.getRange(i + 2, 2).setValue(val); CFG_CACHE = null; return; }
  }
  s.appendRow([key, val, '']);
  CFG_CACHE = null;
}

/** Журнал: A ID | B Ходим | C Сана | D Келди | E Кетди | F Ишлади (соат) | G Изоҳ */
function loadSessions() {
  const s = sh(SH_LOG);
  const n = s.getLastRow() - 1;
  if (n < 1) return [];
  return s.getRange(2, 1, n, 7).getDisplayValues().map((r, i) => ({
    row: i + 2, id: String(r[0]), worker: String(r[1]).trim(), date: String(r[2]).trim(),
    start: normHM(r[3]), end: normHM(r[4]), note: String(r[6] || ''),
  })).filter(x => x.worker && x.date && x.start);
}

function nextId(list) {
  let mx = 0;
  list.forEach(x => { const n = Number(x.id); if (n > mx) mx = n; });
  return mx + 1;
}

function hoursNum(min) { return Math.round(min / 60 * 100) / 100; }

function addSession(worker, date, start, end, note) {
  const id = nextId(loadSessions());
  const hrs = end ? hoursNum(dur(start, end)) : '';
  sh(SH_LOG).appendRow([String(id), worker, date, start, end || '', hrs, note || '']);
  return id;
}

function findSession(id) { return loadSessions().filter(x => x.id === String(id))[0] || null; }

function updateSession(s, start, end, note) {
  const sheet = sh(SH_LOG);
  sheet.getRange(s.row, 4, 1, 4).setValues([[start, end || '', end ? hoursNum(dur(start, end)) : '', note]]);
}

function deleteSessionRow(row) { sh(SH_LOG).deleteRow(row); }

/** «Кетдим» босилмаган сессия учун ҳисобланадиган тугаш вақти. */
function effectiveEnd(s) {
  if (s.end) return s.end;
  const c = cfg();
  const capped = maxHM(c.workEnd, s.start);
  if (s.date === todayStr()) return minHM(nowHM(), capped);
  return capped;
}
function sessionMin(s) { return dur(s.start, effectiveEnd(s)); }

/** Ўтган кунлардан очиқ қолган сессияларни ISH_TUGASH вақти билан ёпади. */
function closeStale() {
  const today = todayStr(), c = cfg();
  loadSessions().forEach(s => {
    if (!s.end && s.date < today) {
      const end = maxHM(c.workEnd, s.start);
      updateSession(s, s.start, end, 'кетдим босилмаган — автоматик ' + end);
    }
  });
}

// ====================================================================== келди / кетди

function lateText(start) {
  const d = toMin(start) - toMin(cfg().workStart);
  return d > 1 ? ' ⚠️ ' + fmtDur(d) + ' кечикди' : '';
}

/** Ходимнинг бугунги ёзувлари (вақт бўйича). */
function todaySessions(worker) {
  const today = todayStr();
  return loadSessions().filter(s => s.worker === worker && s.date === today)
    .sort((a, b) => toMin(a.start) - toMin(b.start));
}

/** «Келдим» — кунига фақат бир марта. Қайта босилса раҳбарга хабар бормайди. */
function checkIn(worker) {
  closeStale();
  const t = nowHM();
  const list = todaySessions(worker);
  if (list.length) {
    const first = list[0], last = list[list.length - 1];
    return { ok: false, msg: last.end
      ? worker + ', сиз бугун ' + first.start + ' да келиб, ' + last.end + ' да кетгансиз.'
      : worker + ', сиз бугун ' + first.start + ' да «Келдим» босгансиз.' };
  }
  addSession(worker, todayStr(), t, '', '');
  notifyAdmins('✅ <b>' + esc(worker) + '</b> ишга келди — ' + t + lateText(t));
  return { ok: true, msg: '✅ Хуш келибсиз, ' + worker + '! (' + t + ')' };
}

/** «Кетдим» — кунига фақат бир марта. Қайта босилса раҳбарга хабар бормайди. */
function checkOut(worker) {
  closeStale();
  const t = nowHM(), today = todayStr();
  const list = todaySessions(worker);
  const open = list.filter(s => !s.end)[0];
  if (!list.length) {
    // «Келдим» босмай «Кетдим» босди — раҳбарга кунига бир марта огоҳлантириш
    const P = PropertiesService.getScriptProperties(), key = 'warn_' + today + '_' + worker;
    if (!P.getProperty(key)) {
      P.setProperty(key, '1');
      notifyAdmins('⚠️ <b>' + esc(worker) + '</b> «Кетдим» босди (' + t + '), лекин бугун «Келдим» босмаган.\n' +
        'Тўғирлаш: <code>/tuzat ' + esc(worker) + ' ' + shortDay(today) + ' 09:00 ' + t + '</code>');
    }
    return { ok: false, msg: worker + ', сиз бугун «Келдим» босмагансиз. Раҳбарга хабар берилди.' };
  }
  if (!open) {
    return { ok: false, msg: worker + ', сиз бугун ' + list[list.length - 1].end + ' да «Кетдим» босгансиз.' };
  }
  updateSession(open, open.start, t, open.note);
  const total = daySummary(today)[worker].min;
  notifyAdmins('🏁 <b>' + esc(worker) + '</b> ишдан кетди — ' + t + '\n' +
    'Келган: ' + open.start + ', ишлади: ' + fmtDur(dur(open.start, t)) + '\n' +
    'Бугун жами: ' + fmtDur(total));
  return { ok: true, msg: '🏁 Хайр, ' + worker + '! Бугун ' + fmtDur(total) + ' ишладингиз.' };
}

// ====================================================================== ҳисоботлар

function daySummary(ds) {
  const res = {};
  cfg().workers.forEach(w => res[w] = { sessions: [], min: 0, open: false });
  loadSessions().filter(s => s.date === ds).forEach(s => {
    const r = res[s.worker] || (res[s.worker] = { sessions: [], min: 0, open: false });
    r.sessions.push(s);
    r.min += sessionMin(s);
    if (!s.end) r.open = true;
  });
  Object.keys(res).forEach(w => res[w].sessions.sort((a, b) => toMin(a.start) - toMin(b.start)));
  return res;
}

function reportDay(ds) {
  const sum = daySummary(ds), today = todayStr(), c = cfg();
  const came = [], absent = [];
  let total = 0;
  Object.keys(sum).forEach(w => {
    const r = sum[w];
    if (!r.sessions.length) { absent.push(w); return; }
    total += r.min;
    const parts = r.sessions.map(s => s.start + '–' + (s.end || '…'));
    let flag = '';
    if (r.open) {
      flag = (ds === today && toMin(nowHM()) <= toMin(c.workEnd)) ? ' 🟢 ишда'
        : ' ⚠️ кетдим босилмаган (' + c.workEnd + ' гача ҳисобланди)';
    }
    if (r.sessions.some(s => /автоматик/.test(s.note))) flag += ' ⚠️ кетдим босилмаган';
    if (r.sessions.some(s => /тузатилди/.test(s.note))) flag += ' ✏️';
    came.push('👤 <b>' + esc(w) + '</b>: ' + fmtDur(r.min) + flag + '\n     ' + parts.join(', ') +
      lateText(r.sessions[0].start));
  });
  let out = '📋 <b>' + dayTitle(ds) + '</b>\n\n';
  if (came.length) out += '✅ <b>Келганлар:</b>\n' + came.join('\n') + '\n\n';
  out += absent.length ? '❌ <b>Келмаганлар:</b> ' + absent.map(esc).join(', ') + '\n' : '🎉 Ҳамма келди!\n';
  out += '\n⏱ Жами: ' + fmtDur(total);
  return out;
}

function reportRange(d1, d2, title) {
  const st = {};
  cfg().workers.forEach(w => st[w] = { min: 0, days: {}, forgot: 0 });
  loadSessions().filter(s => s.date >= d1 && s.date <= d2).forEach(s => {
    const r = st[s.worker] || (st[s.worker] = { min: 0, days: {}, forgot: 0 });
    r.min += sessionMin(s);
    r.days[s.date] = 1;
    if (/автоматик/.test(s.note)) r.forgot++;
  });
  const lines = ['📊 <b>' + title + '</b>', shortDay(d1) + '.' + d1.slice(0, 4) + ' — ' + shortDay(d2) + '.' + d2.slice(0, 4), ''];
  let total = 0;
  Object.keys(st).sort((a, b) => st[b].min - st[a].min).forEach(w => {
    const r = st[w], n = Object.keys(r.days).length;
    total += r.min;
    let line = '👤 <b>' + esc(w) + '</b>: ' + fmtDur(r.min) + ' (' + n + ' кун';
    if (n) line += ', ўртача ' + fmtDur(Math.round(r.min / n)) + '/кун';
    line += ')';
    if (r.forgot) line += '\n     ⚠️ «Кетдим» босилмаган: ' + r.forgot + ' марта';
    lines.push(line);
  });
  lines.push('', '⏱ Жами: ' + fmtDur(total));
  return lines.join('\n');
}

function reportMonth(y, m) {
  const d1 = y + '-' + pad(m) + '-01';
  let d2 = y + '-' + pad(m) + '-' + pad(daysInMonth(y, m));
  const today = todayStr();
  if (d1 <= today && today < d2) d2 = today;
  return reportRange(d1, d2, OYLAR[m] + ' ' + y + ' — ойлик ҳисобот');
}

/** Ой бўйича жадвал варағи: ходимлар × кунлар (соат). */
function buildMonthSheet(y, m) {
  const name = y + '-' + pad(m);
  const book = ss();
  const s = book.getSheetByName(name) || book.insertSheet(name);
  s.clear();
  const n = daysInMonth(y, m);
  const header = ['Ходим'];
  for (let d = 1; d <= n; d++) header.push(d);
  header.push('Жами (соат)', 'Иш кунлари');
  const per = {};
  const sessions = loadSessions().filter(x => x.date.slice(0, 7) === name);
  sessions.forEach(x => { const k = x.worker + '|' + x.date; per[k] = (per[k] || 0) + sessionMin(x); });
  const workers = cfg().workers.slice();
  sessions.forEach(x => { if (workers.indexOf(x.worker) < 0) workers.push(x.worker); });
  const rows = workers.map(w => {
    const row = [w];
    let tot = 0, days = 0;
    for (let d = 1; d <= n; d++) {
      const v = per[w + '|' + name + '-' + pad(d)] || 0;
      tot += v; if (v) days++;
      row.push(v ? hoursNum(v) : '');
    }
    row.push(hoursNum(tot), days);
    return row;
  });
  s.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
  if (rows.length) s.getRange(2, 1, rows.length, header.length).setValues(rows);
  s.setFrozenRows(1);
  return book.getUrl() + '#gid=' + s.getSheetId();
}

// ====================================================================== Телеграм

function tg(method, payload) {
  const token = cfg().token;
  if (!token) { console.warn('BOT_TOKEN йўқ'); return {}; }
  const r = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/' + method, {
    method: 'post', contentType: 'application/json',
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  let j = {};
  try { j = JSON.parse(r.getContentText()); } catch (e) { }
  if (!j.ok) console.warn(method + ': ' + r.getContentText());
  return j;
}

function send(chatId, text, extra) {
  const p = { chat_id: chatId, text: text, parse_mode: 'HTML', disable_web_page_preview: true };
  if (extra) Object.keys(extra).forEach(k => p[k] = extra[k]);
  return tg('sendMessage', p);
}

function notifyAdmins(text, extra) { cfg().admins.forEach(id => send(id, text, extra)); }

function tabletKeyboard() {
  return {
    keyboard: cfg().workers.map(w => [{ text: '✅ ' + w + ' келдим' }, { text: '🏁 ' + w + ' кетдим' }]),
    resize_keyboard: true, is_persistent: true,
  };
}

const ADMIN_BTNS = {
  '📋 Бугун': '/bugun', '📅 Кеча': '/kecha', '🗓 Ҳафта': '/hafta',
  '📊 Шу ой': '/oy', '✏️ Тузатиш': '/tuzat', '📑 Жадвал': '/jadval',
};
function adminKeyboard() {
  return {
    keyboard: [[{ text: '📋 Бугун' }, { text: '📅 Кеча' }, { text: '🗓 Ҳафта' }],
               [{ text: '📊 Шу ой' }, { text: '✏️ Тузатиш' }, { text: '📑 Жадвал' }]],
    resize_keyboard: true, is_persistent: true,
  };
}

const ADMIN_COMMANDS = [
  { command: 'bugun', description: 'Бугунги ҳисобот' },
  { command: 'kecha', description: 'Кечаги ҳисобот' },
  { command: 'hafta', description: 'Шу ҳафта' },
  { command: 'oy', description: 'Шу ой' },
  { command: 'jadval', description: 'Ойлик жадвал' },
  { command: 'tuzat', description: 'Вақтни тўғирлаш' },
];

/** Командалар менюси: ҳамма учун бўш, фақат раҳбарда тўлиқ, планшетларда бўш. */
function setMenus() {
  tg('setMyCommands', { commands: [], scope: { type: 'all_private_chats' } });
  cfg().admins.forEach(id => tg('setMyCommands', { commands: ADMIN_COMMANDS, scope: { type: 'chat', chat_id: Number(id) } }));
  cfg().tablets.forEach(id => clearMenu(id));
}

/** Битта планшет чатидан менюни ўчиради. */
function clearMenu(id) {
  tg('setMyCommands', { commands: [], scope: { type: 'chat', chat_id: Number(id) } });
}

const HELP =
  '🤖 <b>Иш вақти боти</b>\n\n' +
  '/bugun — бугун ким келди, ким келмади\n' +
  '/kecha — кечаги ҳисобот\n' +
  '/kun 05.11 — исталган кун\n' +
  '/hafta — шу ҳафта соатлари\n' +
  '/oy — шу ой соатлари (/oy 2026-10 — бошқа ой)\n' +
  '/jadval — ойлик жадвални Google Таблицада очиш\n' +
  '/tuzat — вақтларни тўғирлаш\n\n' +
  '<b>Тўғирлаш мисоллари:</b>\n' +
  '<code>/tuzat Шавкат 05.11 08:50 18:00</code> — ўша кунни шу вақтлар билан ёзиш\n' +
  '<code>/tuzat Шавкат 05.11 келмади</code> — ўша кунни ўчириш';

// ---------------------------------------------------------------------- webhook

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(25000);
    const upd = JSON.parse(e.postData.contents);
    const cache = CacheService.getScriptCache();
    const key = 'upd_' + upd.update_id;
    if (!cache.get(key)) {          // Google баъзан бир хабарни икки марта юборади
      cache.put(key, '1', 21600);
      handleUpdate(upd);
    }
  } catch (err) {
    console.error(err && err.stack || err);
  } finally {
    try { lock.releaseLock(); } catch (e2) { }
  }
  return ContentService.createTextOutput('ok');
}

function doGet() { return ContentService.createTextOutput('Иш вақти боти ишлаяпти ✅'); }

function isAdmin(id) { return cfg().admins.indexOf(String(id)) >= 0; }
function isTablet(id) { return cfg().tablets.indexOf(String(id)) >= 0; }

function handleUpdate(upd) {
  if (upd.callback_query) return handleCallback(upd.callback_query);
  const msg = upd.message;
  if (!msg || !msg.text) return;
  const chatId = String(msg.chat.id);
  // Кўринмас белгиларни (эмодзи ичидаги вариация белгиси ва бошқалар) олиб ташлаймиз
  const text = msg.text.replace(/[\uFE0F\u200B-\u200D\u2060]/g, '').replace(/\s+/g, ' ').trim();
  const c = cfg();

  // Биринчи /start ёзган одам — раҳбар (ADMIN_IDS бўш бўлса)
  if (!c.admins.length && /^\/start/.test(text)) {
    setCfg('ADMIN_IDS', chatId);
    setMenus();
    send(chatId, '👑 Сиз раҳбар сифатида белгиландингиз.\n\n' + HELP, { reply_markup: adminKeyboard() });
    return;
  }

  // Планшет тугмалари: «✅ Баходир келдим» / «🏁 Баходир кетдим»
  const m = text.match(/^(?:✅|🏁)?\s*(.+?)\s+(келдим|кетдим)$/i);
  if (m && c.workers.indexOf(m[1].trim()) >= 0) {
    if (!isTablet(chatId) && !isAdmin(chatId)) return send(chatId, '⛔ Рухсат йўқ. /start босинг.');
    const r = m[2].toLowerCase() === 'келдим' ? checkIn(m[1].trim()) : checkOut(m[1].trim());
    return send(chatId, r.msg, isTablet(chatId) ? { reply_markup: tabletKeyboard() } : undefined);
  }

  if (isAdmin(chatId)) return handleAdmin(chatId, text);

  if (isTablet(chatId)) {
    return send(chatId, 'Пастдаги тугмалардан фойдаланинг 👇', { reply_markup: tabletKeyboard() });
  }

  // Нотаниш одам → раҳбардан рухсат сўраймиз
  if (/^\/start/.test(text)) {
    const who = [msg.from && msg.from.first_name, msg.from && msg.from.last_name].filter(Boolean).join(' ');
    notifyAdmins('📱 Янги қурилма ботга уланмоқчи:\n<b>' + esc(who || '—') + '</b> (ID <code>' + chatId + '</code>)\n\n' +
      'Бу ишхонадаги планшет бўлса, рухсат беринг:',
      { reply_markup: { inline_keyboard: [[{ text: '✅ Планшет сифатида рухсат бериш', callback_data: 'p|' + chatId }]] } });
    send(chatId, 'Сизнинг ID: <code>' + chatId + '</code>\nРаҳбарга рухсат сўрови юборилди. Рухсат берилгач, тугмалар пайдо бўлади.');
  }
}

function handleAdmin(chatId, text) {
  const cache = CacheService.getScriptCache();

  // Тузатиш учун вақт кутилаётган бўлса
  const waiting = cache.get('await_' + chatId);
  const hm = normHM(text);
  if (waiting && hm) {
    cache.remove('await_' + chatId);
    const w = JSON.parse(waiting);
    return send(chatId, applyFix(w.id, w.field, hm), { reply_markup: adminKeyboard() });
  }

  if (ADMIN_BTNS[text]) text = ADMIN_BTNS[text];
  const parts = text.split(/\s+/);
  const cmd = parts[0].split('@')[0].toLowerCase();
  const args = parts.slice(1);
  const today = todayStr();

  switch (cmd) {
    case '/start': case '/help': case '/yordam':
      return send(chatId, HELP, { reply_markup: adminKeyboard() });
    case '/bugun': return send(chatId, reportDay(today));
    case '/kecha': return send(chatId, reportDay(addDays(today, -1)));
    case '/kun': {
      const d = parseDay(args[0]);
      return send(chatId, d ? reportDay(d) : 'Формат: /kun 05.11');
    }
    case '/hafta': {
      const wd = (weekday(today) + 6) % 7; // душанба = 0
      return send(chatId, reportRange(addDays(today, -wd), today, 'Шу ҳафта'));
    }
    case '/oy': {
      const ym = parseMonth(args[0]);
      return send(chatId, ym ? reportMonth(ym[0], ym[1]) : 'Формат: /oy 2026-10');
    }
    case '/jadval': {
      const ym = parseMonth(args[0]);
      if (!ym) return send(chatId, 'Формат: /jadval 2026-10');
      const url = buildMonthSheet(ym[0], ym[1]);
      return send(chatId, '📑 <a href="' + url + '">' + OYLAR[ym[1]] + ' ' + ym[0] + ' — жадвални очиш</a>');
    }
    case '/tuzat': return tuzatCommand(chatId, args);
  }
  return send(chatId, HELP, { reply_markup: adminKeyboard() });
}

function parseMonth(a) {
  const t = todayStr();
  if (!a) return [Number(t.slice(0, 4)), Number(t.slice(5, 7))];
  const p = a.replace(/[./]/g, '-').split('-');
  if (p.length !== 2) return null;
  let y = Number(p[0]), m = Number(p[1]);
  if (p[0].length !== 4) { y = Number(p[1]); m = Number(p[0]); }
  if (!y || m < 1 || m > 12) return null;
  return [y, m];
}

// ---------------------------------------------------------------------- тузатиш

function findWorker(name) {
  const n = String(name || '').toLowerCase();
  return cfg().workers.filter(w => w.toLowerCase() === n)[0] || null;
}

function tuzatCommand(chatId, args) {
  if (!args.length) {
    // Сўнгги 2 кун сессиялари — тугма орқали тўғирлаш
    const today = todayStr(), yest = addDays(today, -1);
    const list = loadSessions().filter(s => s.date === today || s.date === yest)
      .sort((a, b) => (a.date + a.start < b.date + b.start ? 1 : -1));
    const kb = list.slice(0, 20).map(s => [{
      text: s.worker + ' ' + shortDay(s.date) + '  ' + s.start + '–' + (s.end || '…'),
      callback_data: 'e|' + s.id,
    }]);
    let t = '✏️ <b>Тузатиш</b>\n\n';
    t += kb.length ? 'Кеча ва бугунги ёзувлар. Тўғирлаш учун танланг 👇\n\n' : 'Кеча ва бугун ёзув йўқ.\n\n';
    t += 'Бошқа кунлар учун:\n<code>/tuzat Шавкат 05.11 08:50 18:00</code>\n<code>/tuzat Шавкат 05.11 келмади</code>';
    return send(chatId, t, kb.length ? { reply_markup: { inline_keyboard: kb } } : undefined);
  }
  const worker = findWorker(args[0]);
  const day = parseDay(args[1]);
  if (!worker) return send(chatId, '❌ Бундай ходим йўқ: ' + esc(args[0]) + '\nХодимлар: ' + cfg().workers.map(esc).join(', '));
  if (!day) return send(chatId, '❌ Сана нотўғри. Мисол: <code>/tuzat ' + esc(worker) + ' 05.11 08:50 18:00</code>');
  if (day > todayStr()) return send(chatId, '❌ Келажакдаги санани киритиб бўлмайди.');

  // ўша кундаги эски ёзувларни ўчирамиз (пастдан юқорига)
  const old = loadSessions().filter(s => s.worker === worker && s.date === day).sort((a, b) => b.row - a.row);

  if (/^келмади$/i.test(args[2] || '')) {
    old.forEach(s => deleteSessionRow(s.row));
    return send(chatId, '🗑 ' + esc(worker) + ', ' + dayTitle(day) + ' — ёзув ўчирилди (келмаган).');
  }
  const start = normHM(args[2]), end = args[3] ? normHM(args[3]) : null;
  if (!start || (args[3] && !end)) {
    return send(chatId, '❌ Вақт нотўғри. Мисол: <code>/tuzat ' + esc(worker) + ' ' + shortDay(day) + ' 08:50 18:00</code>');
  }
  old.forEach(s => deleteSessionRow(s.row));
  addSession(worker, day, start, end, 'тузатилди');
  const msg = '✏️ ' + esc(worker) + ', ' + dayTitle(day) + ': ' + start + '–' + (end || '…') +
    (end ? ' (' + fmtDur(dur(start, end)) + ')' : '');
  return send(chatId, msg + '\n✅ Сақланди.');
}

function applyFix(id, field, hm) {
  const s = findSession(id);
  if (!s) return '❌ Ёзув топилмади (ўчирилган бўлиши мумкин).';
  let start = s.start, end = s.end;
  if (field === 'start') start = hm; else end = hm;
  if (end && toMin(end) < toMin(start)) {
    return '❌ Кетиш вақти келиш вақтидан олдин бўлиши мумкин эмас.';
  }
  updateSession(s, start, end, 'тузатилди');
  return '✏️ <b>' + esc(s.worker) + '</b>, ' + dayTitle(s.date) + ':\n' + start + '–' + (end || '…') +
    (end ? ' — ' + fmtDur(dur(start, end)) : '') + '\n✅ Сақланди.';
}

function handleCallback(q) {
  const chatId = String(q.message.chat.id);
  const msgId = q.message.message_id;
  tg('answerCallbackQuery', { callback_query_id: q.id });
  if (!isAdmin(chatId)) return;
  const p = String(q.data).split('|');
  const cache = CacheService.getScriptCache();
  const edit = t => tg('editMessageText', { chat_id: chatId, message_id: msgId, text: t, parse_mode: 'HTML' });

  if (p[0] === 'p') {                                  // планшетга рухсат
    const ids = cfg().tablets;
    if (ids.indexOf(p[1]) < 0) setCfg('PLANSHET_IDS', ids.concat([p[1]]).join(','));
    clearMenu(p[1]);                                   // планшетда меню бўлмайди
    edit('✅ Планшет уланди (ID <code>' + p[1] + '</code>).');
    send(p[1], '✅ Рухсат берилди! Ходимлар пастдаги тугмаларни босади 👇', { reply_markup: tabletKeyboard() });
    return;
  }
  if (p[0] === 'f') {                                  // эслатмадан: «18:00 да кетган»
    edit(applyFix(p[1], 'end', p[2]));
    return;
  }
  const s = findSession(p[1]);
  if (!s) return edit('❌ Ёзув топилмади.');
  const label = '<b>' + esc(s.worker) + '</b>, ' + dayTitle(s.date) + ': ' + s.start + '–' + (s.end || '…');

  if (p[0] === 'e') {                                  // нимани тўғирлаймиз?
    return tg('editMessageText', {
      chat_id: chatId, message_id: msgId, parse_mode: 'HTML', text: '✏️ ' + label + '\n\nНимани ўзгартирамиз?',
      reply_markup: { inline_keyboard: [
        [{ text: '🕘 Келиш вақти', callback_data: 'k|' + s.id }, { text: '🏁 Кетиш вақти', callback_data: 'a|' + s.id }],
        [{ text: '🗑 Ўчириш', callback_data: 'd|' + s.id }],
      ] },
    });
  }
  if (p[0] === 'k' || p[0] === 'a') {                  // вақтни ёзишни кутамиз
    cache.put('await_' + chatId, JSON.stringify({ id: s.id, field: p[0] === 'k' ? 'start' : 'end' }), 1800);
    edit('✏️ ' + label + '\n\n' + (p[0] === 'k' ? 'Келиш' : 'Кетиш') +
      ' вақтини ёзинг, масалан <code>' + (p[0] === 'k' ? '09:00' : '18:00') + '</code>');
    return;
  }
  if (p[0] === 'd') {
    deleteSessionRow(s.row);
    edit('🗑 Ўчирилди: ' + label);
  }
}

// ====================================================================== вақт бўйича иш

/** Ҳар 5 дақиқада ишлайди (ulash() триггер яратади). */
function tick() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return;
  try {
    const c = cfg();
    if (!c.token || !c.admins.length) return;
    closeStale();
    const P = PropertiesService.getScriptProperties();
    const today = todayStr(), hm = nowHM();
    const rest = c.restDays.indexOf(KUNLAR[weekday(today)].toLowerCase()) >= 0;
    P.getKeys().forEach(k => { if (k.indexOf('warn_') === 0 && k.indexOf('warn_' + today) !== 0) P.deleteProperty(k); });

    if (hm >= c.absentTime && P.getProperty('sent_absent') !== today) {
      P.setProperty('sent_absent', today);
      if (!rest) {
        const sum = daySummary(today);
        const absent = c.workers.filter(w => !sum[w].sessions.length);
        notifyAdmins(absent.length
          ? '⏰ Соат ' + c.absentTime + ' ҳолатига ҳали келмаганлар:\n❌ ' + absent.map(esc).join(', ')
          : '⏰ Соат ' + c.absentTime + ': ҳамма ишга келди ✅');
      }
    }

    if (hm >= c.remindTime && P.getProperty('sent_remind') !== today) {
      P.setProperty('sent_remind', today);
      loadSessions().filter(s => s.date === today && !s.end).forEach(s => {
        const end = maxHM(c.workEnd, s.start);
        notifyAdmins('⚠️ <b>' + esc(s.worker) + '</b> «Кетдим»ни босмади (келган: ' + s.start + ').\n' +
          'Ҳеч нарса қилмасангиз, ' + end + ' гача ҳисобланади.\nҲали ишда бўлса — тегманг.',
          { reply_markup: { inline_keyboard: [[
            { text: '✅ ' + end + ' да кетган', callback_data: 'f|' + s.id + '|' + end },
            { text: '✏️ Бошқа вақт', callback_data: 'a|' + s.id },
          ]] } });
      });
    }

    if (hm >= c.reportTime && P.getProperty('sent_report') !== today) {
      P.setProperty('sent_report', today);
      const anyone = loadSessions().some(s => s.date === today);
      if (!rest || anyone) notifyAdmins(reportDay(today));
      if (addDays(today, 1).slice(5, 7) !== today.slice(5, 7)) {   // ойнинг охирги куни
        const y = Number(today.slice(0, 4)), m = Number(today.slice(5, 7));
        const url = buildMonthSheet(y, m);
        notifyAdmins(reportMonth(y, m) + '\n\n📑 <a href="' + url + '">Жадвални очиш</a>');
      }
    }
  } finally {
    lock.releaseLock();
  }
}

// ====================================================================== ўрнатиш

/** 1-қадам: варақларни яратади. */
function setup() {
  const book = SPREADSHEET_ID ? SpreadsheetApp.openById(SPREADSHEET_ID) : SpreadsheetApp.getActiveSpreadsheet();
  PropertiesService.getScriptProperties().setProperty('SS_ID', book.getId());
  book.setSpreadsheetTimeZone(TZ);

  let s = book.getSheetByName(SH_SET);
  if (!s) {
    s = book.insertSheet(SH_SET);
    s.getRange(1, 1, 1, 3).setValues([['Созлама', 'Қиймати', 'Изоҳ']]).setFontWeight('bold');
    s.getRange(2, 2, DEFAULTS.length, 1).setNumberFormat('@');
    s.getRange(2, 1, DEFAULTS.length, 3).setValues(DEFAULTS);
    s.setFrozenRows(1);
  }
  let w = book.getSheetByName(SH_WORK);
  if (!w) {
    w = book.insertSheet(SH_WORK);
    w.getRange(1, 1).setValue('Ходим (исм)').setFontWeight('bold');
    w.getRange(2, 1, DEFAULT_WORKERS.length, 1).setValues(DEFAULT_WORKERS.map(x => [x]));
    w.setFrozenRows(1);
  }
  let l = book.getSheetByName(SH_LOG);
  if (!l) {
    l = book.insertSheet(SH_LOG);
    l.getRange(1, 1, 1, 7).setValues([['ID', 'Ходим', 'Сана', 'Келди', 'Кетди', 'Ишлади (соат)', 'Изоҳ']])
      .setFontWeight('bold');
    l.getRange(2, 1, 5000, 5).setNumberFormat('@');   // сана ва вақтлар матн бўлиб қолсин
    l.setFrozenRows(1);
  }
  const first = book.getSheetByName('Sheet1') || book.getSheetByName('Лист1') || book.getSheetByName('Варақ1');
  if (first && book.getSheets().length > 1 && first.getLastRow() === 0) book.deleteSheet(first);
  console.log('✅ Тайёр. Энди «Созламалар» варағига BOT_TOKEN ёзинг ва Web app сифатида deploy қилинг.');
}

/** 2-қадам: ботни Web app га улайди ва таймерни ёқади. */
function ulash() {
  CFG_CACHE = null;
  const c = cfg();
  if (!c.token) throw new Error('«Созламалар» варағида BOT_TOKEN бўш.');
  const url = c.url || ScriptApp.getService().getUrl();
  if (!url || !/\/exec$/.test(url)) throw new Error('WEBAPP_URL нотўғри. Deploy → Web app манзилини (…/exec) ёзинг.');
  if (c.relay && !/^https:\/\/\S+$/.test(c.relay)) throw new Error('RELAY_URL нотўғри (https://… бўлиши керак).');
  // Google доим «302» жавоб қайтаради, Телеграм буни хато деб ҳисоблаб хабарларни тиқиб қўяди.
  // Шунинг учун Телеграм Cloudflare воситачисига (RELAY_URL) уланади, у хабарни Google га узатади.
  const hook = c.relay || url;
  const r = tg('setWebhook', { url: hook, drop_pending_updates: true, allowed_updates: ['message', 'callback_query'] });
  if (!r.ok) throw new Error('Телеграмга уланмади: ' + JSON.stringify(r));
  setMenus();

  ScriptApp.getProjectTriggers().forEach(t => { if (t.getHandlerFunction() === 'tick') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('tick').timeBased().everyMinutes(5).create();

  // Бугунги вақти ўтиб кетган хабарларни юбормаслик
  const P = PropertiesService.getScriptProperties(), today = todayStr(), hm = nowHM();
  if (hm >= c.absentTime) P.setProperty('sent_absent', today);
  if (hm >= c.remindTime) P.setProperty('sent_remind', today);
  if (hm >= c.reportTime) P.setProperty('sent_report', today);

  const me = tg('getMe', {});
  console.log('✅ Бот уланди: @' + (me.result && me.result.username) +
    (c.relay ? '\nCloudflare орқали: ' + c.relay : '\n⚠️ RELAY_URL бўш — хабарлар тиқилиб қолиши мумкин.') +
    '\nТелеграмда ботга /start ёзинг — сиз раҳбар бўласиз.');
}

/** Текширув: Телеграм ботга қандай уланганини кўрсатади (pending_update_count, last_error_message). */
function tekshir() {
  console.log(JSON.stringify(tg('getWebhookInfo', {}), null, 2));
}
