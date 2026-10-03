// A5/A6. Конверт «уточняющие вопросы»: формулировки от ИИ сверяются с чек-листом; если ИИ не ответил или не покрыл пункт — берётся шаблон.
const P = $('A7 Подбор маршрута').first().json;
const ref = $('Справочники и регламент').first().json.ref;
const esc = (s) => String(s === undefined || s === null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

let llm = $json.output && $json.output[0] && $json.output[0].content && $json.output[0].content[0]
  ? $json.output[0].content[0].text
  : null;
if (typeof llm === 'string') {
  try { llm = JSON.parse(llm); } catch (e) { llm = null; }
}

let lead = '';
const byCode = {};
if (llm && typeof llm === 'object') {
  if (typeof llm.lead === 'string') lead = llm.lead.trim().slice(0, 300);
  for (const q of Array.isArray(llm.questions) ? llm.questions : []) {
    if (q && typeof q.code === 'string' && typeof q.text === 'string' && q.text.trim().length >= 5) {
      byCode[q.code] = q.text.trim().slice(0, 240);
    }
  }
}

const lines = P.check.missing.map((m, i) => {
  const fallback = m.label + (m.hint ? ' — ' + m.hint : '');
  return (i + 1) + '. ' + esc(byCode[m.code] || fallback);
});

// счётчик считает подряд идущие ответы БЕЗ прогресса; любой прогресс обнуляет его
const attempt = P.check.progress ? 0 : Number(P.attempts || 0) + 1;
let text = P.card_html + '\n\n';
if (lead) text += esc(lead) + '\n\n';
text += '❗ <b>Чтобы запустить согласование, уточните:</b>\n' + lines.join('\n');
text += '\n\nОтветьте одним сообщением (можно списком) или прикрепите файлы.';
if (attempt > 0) text += ' Ответов без прогресса: ' + attempt + ' из ' + ref.max_attempts + ' — после ' + ref.max_attempts + '-го заявка уйдёт администратору СЭД.';
text += ' /cancel — отменить.';
if (text.length > 3900) text = text.slice(0, 3890) + '…';

return [{
  json: {
    chat_id: P.chat_id,
    text,
    keyboard: null,
    save: {
      request_uid: P.request_uid,
      chat_id: P.chat_id,
      user_name: P.user_name,
      status: 'collecting',
      card_json: JSON.stringify(P.card),
      request_text: P.request_text,
      attempts: attempt,
      route: P.route.text,
    },
  },
}];
