// Конверт «карточка на подтверждение»: показывает собранную карточку и маршрут, ждёт решения инициатора (кнопки).
const P = $('A7 Подбор маршрута').first().json;

let text = P.card_html + '\n\n' + P.route_html;
(P.check.warnings || []).forEach((w) => {
  if (!text.includes(w)) text += '\n⚠ ' + String(w).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
});
text += '\n\n✅ <b>Пакет полный.</b> Проверьте данные и подтвердите — заявка будет зарегистрирована, а маршрут запущен автоматически. Если что-то неверно, нажмите «Исправить» или просто напишите правку.';
if (text.length > 3900) text = text.slice(0, 3890) + '…';

return [{
  json: {
    chat_id: P.chat_id,
    text,
    keyboard: 'confirm',
    save: {
      request_uid: P.request_uid,
      chat_id: P.chat_id,
      user_name: P.user_name,
      status: 'awaiting_confirmation',
      card_json: JSON.stringify(P.card),
      request_text: P.request_text,
      attempts: Number(P.attempts || 0),
      route: P.route.text,
    },
  },
}];
