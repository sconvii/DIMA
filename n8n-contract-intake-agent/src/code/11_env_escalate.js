// Конверт «эскалация»: после исчерпания попыток уточнения заявка передаётся администратору СЭД (человек остаётся в контуре).
const P = $('A7 Подбор маршрута').first().json;
const ref = $('Справочники и регламент').first().json.ref;
const esc = (s) => String(s === undefined || s === null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

let text = P.card_html + '\n\n';
text += '🆘 <b>Не удалось собрать полный пакет: ' + ref.max_attempts + ' ответа подряд не продвинули заявку.</b>\n';
text += 'Заявка сохранена со статусом «требует помощи» — администратор СЭД свяжется с вами. Пока не хватает:\n';
text += P.check.missing.map((m, i) => (i + 1) + '. ' + esc(m.label)).join('\n');
text += '\n\nЧтобы начать заново, отправьте /new.';
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
      status: 'escalated',
      card_json: JSON.stringify(P.card),
      request_text: P.request_text,
      attempts: Number(P.attempts || 0) + 1,
      route: P.route.text,
    },
  },
}];
