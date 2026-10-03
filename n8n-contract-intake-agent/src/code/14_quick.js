// Быстрые действия без ИИ: статус, отмена, исправление, неактуальная кнопка, вне темы.
const ctx = $json;
const kind = ctx.quick || ctx.mode;
const esc = (s) => String(s === undefined || s === null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const money = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
const CUR = { RUB: '₽', USD: '$', EUR: '€', CNY: '¥', KZT: '₸', OTHER: '' };
const STATUS = {
  collecting: 'сбор данных',
  awaiting_confirmation: 'ждёт подтверждения',
  registered: 'зарегистрирована, идёт согласование',
  cancelled: 'отменена',
  escalated: 'требует помощи администратора',
};

const base = { request_uid: ctx.request_uid, chat_id: ctx.chat_id, user_name: ctx.user_name };
let text = '';
let save = null;

switch (kind) {
  case 'status': {
    const rows = ctx.rows_brief || [];
    if (!rows.length) {
      text = '📋 У вас пока нет заявок. Опишите договор — и я оформлю заявку.';
      break;
    }
    const lines = rows.map((r, i) => {
      let card = {};
      try { card = JSON.parse(r.card_json || '{}'); } catch (e) { card = {}; }
      const who = esc(card.counterparty_name || 'контрагент не указан');
      const sum = card.amount ? ' · ' + money(card.amount) + ' ' + (CUR[card.currency] || '') : '';
      const id = r.reg_number ? '№ ' + esc(r.reg_number) : 'черновик';
      return (i + 1) + '. ' + id + ' · ' + who + sum + ' — ' + (STATUS[r.status] || esc(r.status)) + (r.status === 'registered' && r.route ? '\n    маршрут: ' + esc(r.route) : '');
    });
    text = '📋 <b>Ваши заявки</b> (последние ' + rows.length + ')\n' + lines.join('\n');
    break;
  }
  case 'cancel':
    text = '❌ Заявка отменена. Чтобы создать новую, опишите договор или отправьте /new.';
    save = { ...base, status: 'cancelled' };
    break;
  case 'new':
    text = '🆕 Начинаем новую заявку' + (ctx.has_session ? ' (предыдущий черновик закрыт)' : '') + '. Опишите договор: тип, контрагент (название и ИНН), предмет, сумма, срок, условия оплаты.';
    if (ctx.has_session) save = { ...base, status: 'cancelled' };
    break;
  case 'edit':
    text = '✏️ Что нужно исправить? Напишите изменения одним сообщением, например: «сумма 15 млн, срок до 31.12.2027».';
    save = { ...base, status: 'collecting' };
    break;
  case 'idle_cancel':
    text = 'Сейчас нет активной заявки. Опишите договор, чтобы начать.';
    break;
  case 'confirm_not_ready':
    text = 'Пока нечего подтверждать — карточка ещё не готова. Ответьте на вопросы выше или отправьте /cancel.';
    break;
  case 'off_topic':
    text = ctx.has_session
      ? 'Это не похоже на данные по договору. Заявка сохранена — отправьте недостающие данные или /cancel, чтобы отменить.'
      : 'Я помогаю оформлять заявки на согласование договоров. Опишите договор: тип, контрагент, предмет, сумма и срок. Справка — /help.';
    break;
  default:
    text = 'Эта кнопка уже неактуальна: заявка обработана или отменена. Отправьте /new, чтобы создать новую.';
}

return [{ json: { chat_id: ctx.chat_id, text, keyboard: null, save } }];
