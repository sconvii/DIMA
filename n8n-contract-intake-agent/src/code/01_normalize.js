// Нормализация входа: превращает любое обновление Telegram (текст, файл, кнопка) в единый плоский объект.
const upd = $input.first().json;
const cb = upd.callback_query || null;
const m = upd.message || {};
const msg = cb ? (cb.message || {}) : m;
const from = (cb ? cb.from : m.from) || {};
const chat = msg.chat || {};

const MAX_LEN = 3500;
const rawText = cb ? '' : String(m.text || m.caption || '');
let text = rawText.trim();
const truncated = text.length > MAX_LEN;
if (truncated) text = text.slice(0, MAX_LEN);

const attachments = [];
if (m.document) {
  attachments.push({
    name: String(m.document.file_name || 'document'),
    mime: String(m.document.mime_type || ''),
    size: Number(m.document.file_size || 0),
    kind: 'document',
  });
}
if (Array.isArray(m.photo) && m.photo.length) {
  const best = m.photo[m.photo.length - 1] || {};
  attachments.push({ name: 'photo_' + (m.message_id || '') + '.jpg', mime: 'image/jpeg', size: Number(best.file_size || 0), kind: 'photo' });
}

const CONFIRM_WORDS = /^(да|подтверждаю|подтвердить|верно|всё верно|все верно|ок|окей|ok|okay|согласен|согласна|регистрируй|регистрируйте|зарегистрировать)[.!\s]*$/i;
const CANCEL_WORDS = /^(отмена|отменить|отмени|cancel|стоп|не нужно|не надо)[.!\s]*$/i;
const COMMANDS = { '/start': 'start', '/help': 'start', '/new': 'new', '/cancel': 'cancel', '/status': 'status' };
const BUTTONS = { confirm: 'confirm', edit: 'edit', cancel: 'cancel' };

let input_type = 'unsupported';
let command = '';
let via_text = false;
if (cb) {
  input_type = BUTTONS[String(cb.data || '')] ? 'cb_' + BUTTONS[String(cb.data)] : 'unsupported';
} else if (text.startsWith('/')) {
  command = text.split(/[\s@]/)[0].toLowerCase();
  input_type = COMMANDS[command] || 'start';
} else if (attachments.length === 0 && CONFIRM_WORDS.test(text)) {
  input_type = 'cb_confirm';
  via_text = true;
} else if (attachments.length === 0 && CANCEL_WORDS.test(text)) {
  input_type = 'cb_cancel';
  via_text = true;
} else if (text || attachments.length) {
  input_type = 'content';
}

const user_name = [from.first_name, from.last_name].filter(Boolean).join(' ') || from.username || '';

return [{
  json: {
    chat_id: String(chat.id !== undefined ? chat.id : (from.id || '')),
    user_id: String(from.id || ''),
    user_name,
    input_type,
    command,
    via_text,
    text,
    truncated,
    attachments,
    callback_query_id: cb ? cb.id : null,
    callback_data: cb ? String(cb.data || '') : '',
    callback_message_id: cb && cb.message ? cb.message.message_id : null,
    callback_message_text: cb && cb.message ? String(cb.message.text || '') : '',
    message_id: m.message_id || null,
    update_id: upd.update_id || null,
  },
}];
