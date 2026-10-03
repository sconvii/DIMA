// Состояние диалога: «память» агента. Берёт заявки чата из Data Table, находит активную сессию и решает, что делать с входом.
const inp = $('Нормализация входа').first().json;

const rows = $input.all()
  .map((i) => i.json)
  .filter((r) => r && r.id !== undefined && r.id !== null && r.id !== '');
rows.sort((a, b) => Number(b.id) - Number(a.id));

const ACTIVE = ['collecting', 'awaiting_confirmation'];
const STALE_MS = 24 * 60 * 60 * 1000;

const latest = rows[0] || null;
let session = null;
let stale_dropped = false;
if (latest && ACTIVE.includes(latest.status)) {
  const t = Date.parse(latest.updatedAt || latest.createdAt || '');
  if (t && Date.now() - t > STALE_MS) stale_dropped = true;
  else session = latest;
}

let card = {};
if (session && session.card_json) {
  try { card = JSON.parse(session.card_json); } catch (e) { card = {}; }
}

const awaiting = !!session && session.status === 'awaiting_confirmation';

// action: content — разбор сообщения; confirm — финальная проверка и регистрация; quick — ответ без ИИ
let action = 'content';
let quick = '';
switch (inp.input_type) {
  case 'status':
    action = 'quick'; quick = 'status'; break;
  case 'new':
    action = 'quick'; quick = 'new'; break;
  case 'cancel':
  case 'cb_cancel':
    action = 'quick'; quick = session ? 'cancel' : 'idle_cancel'; break;
  case 'cb_edit':
    action = 'quick'; quick = session ? 'edit' : 'stale'; break;
  case 'cb_confirm':
    if (awaiting) action = 'confirm';
    else if (inp.via_text) action = 'content';
    else { action = 'quick'; quick = session ? 'confirm_not_ready' : 'stale'; }
    break;
  default:
    action = 'content';
}

const rand = Math.random().toString(36).slice(2, 6);
const request_uid = session && session.request_uid ? session.request_uid : 'R' + Date.now().toString(36) + rand;

return [{
  json: {
    ...inp,
    action,
    quick,
    mode: action === 'confirm' ? 'confirm' : 'process',
    has_session: !!session,
    session_status: session ? session.status : null,
    row_id: session ? session.id : null,
    request_uid,
    attempts: session ? Number(session.attempts || 0) : 0,
    request_text: session ? String(session.request_text || '') : '',
    card,
    stale_dropped,
    rows_brief: rows.slice(0, 5).map((r) => ({
      id: r.id,
      status: r.status,
      reg_number: r.reg_number || '',
      route: r.route || '',
      card_json: r.card_json || '',
      updatedAt: r.updatedAt || '',
    })),
  },
}];
