// Иш вақти боти — Cloudflare воситачиси (relay).
//
// Нима учун керак: Google Apps Script ҳар доим «302» жавоб қайтаради.
// Телеграм буни хато деб ҳисоблаб, хабарни қайта-қайта юборади ва янги хабарларни
// навбатда ушлаб туради (бот «қотиб» қолади). Бу воситачи Телеграмга дарҳол «OK»
// деб жавоб беради ва хабарни Google Apps Script'га узатади.
//
// Қуйидаги қаторга «Созламалар» варағидаги WEBAPP_URL ни (…/exec) қўйинг:
const GAS_URL = 'https://script.google.com/macros/s/ШУ_ЕРГА_ЎЗИНГИЗНИКИНИ/exec';

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'POST') {
      const body = await request.text();
      // Google'га орқа фонда узатамиз, Телеграм жавобни кутиб қолмайди
      ctx.waitUntil(fetch(GAS_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body,
        redirect: 'manual',
      }));
      return new Response('ok');
    }
    return new Response('Иш вақти воситачиси ишлаяпти ✅');
  },
};
