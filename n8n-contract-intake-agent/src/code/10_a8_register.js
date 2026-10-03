// A8. Регистрация заявки: присваивает регистрационный номер, фиксирует статус и формирует уведомление о запуске маршрута.
const P = $('A7 Подбор маршрута').first().json;
const year = new Date().getFullYear();
const seq = P.row_id !== null && P.row_id !== undefined ? Number(P.row_id) : Date.now() % 100000;
const reg_number = 'ЗД-' + year + '-' + String(seq).padStart(5, '0');

let text = '🎉 <b>Заявка зарегистрирована: № ' + reg_number + '</b>\n\n';
text += P.route_html;
if (P.route.template) text += '\n📎 Шаблон договора: ' + P.route.template;
text += '\n\nМаршрут запущен. Статус заявки — по команде /status. Новая заявка — /new.';

return [{
  json: {
    chat_id: P.chat_id,
    text,
    keyboard: null,
    save: {
      request_uid: P.request_uid,
      chat_id: P.chat_id,
      user_name: P.user_name,
      status: 'registered',
      card_json: JSON.stringify(P.card),
      request_text: P.request_text,
      attempts: Number(P.attempts || 0),
      route: P.route.text,
      reg_number,
    },
  },
}];
