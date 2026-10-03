// Слияние с карточкой: проверяет ответ ИИ (JSON), нормализует значения и аккуратно сливает их с карточкой из памяти.
const ctx = $('Состояние диалога').first().json;
const ref = $('Справочники и регламент').first().json.ref;

// 1. Ответ модели: объект (JSON Schema разобран узлом) или строка с JSON; иначе — ошибка разбора
let ex = $json.output && $json.output[0] && $json.output[0].content && $json.output[0].content[0]
  ? $json.output[0].content[0].text
  : null;
if (typeof ex === 'string') {
  // модель могла обернуть JSON в ```-блок или добавить пояснение — вырезаем сам объект
  const t = ex.trim().replace(/^```(?:json)?\s*|\s*```$/g, '');
  try { ex = JSON.parse(t); } catch (e) {
    const m = t.match(/\{[\s\S]*\}/);
    try { ex = m ? JSON.parse(m[0]) : null; } catch (e2) { ex = null; }
  }
}
const llm_ok = !!ex && typeof ex === 'object' && !Array.isArray(ex);
if (!llm_ok) ex = {};

const INTENTS = ['provide_info', 'new_request', 'question', 'off_topic'];
let intent = INTENTS.includes(ex.intent) ? ex.intent : 'provide_info';
// загрузка файла — всегда часть заявки, а не «вне темы»
if (intent === 'off_topic' && (ctx.attachments || []).length) intent = 'provide_info';
const fresh = intent === 'new_request';

const card = fresh ? {} : { ...(ctx.card || {}) };

// 2. Скалярные поля: только непустые новые значения перекрывают старые
const isIsoDate = (s) => /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(Date.parse(s));
const put = (k, v) => { card[k] = v; };
const clean = (v) => (typeof v === 'string' ? v.trim() : v);

if (ref.types[ex.contract_type]) put('contract_type', ex.contract_type);
if (clean(ex.counterparty_name)) {
  const normN = (x) => String(x || '').toLowerCase().replace(/[^a-zа-яё0-9]/g, '');
  // сменили контрагента, а новый ИНН не назвали — старые реквизиты к новому названию не относятся
  if (card.counterparty_name && normN(card.counterparty_name) !== normN(ex.counterparty_name) && !ex.counterparty_inn) {
    delete card.counterparty_inn;
    delete card.counterparty_country;
    delete card.counterparty_is_foreign;
  }
  put('counterparty_name', clean(ex.counterparty_name));
}
let innDropped = false;
if (ex.counterparty_inn !== null && ex.counterparty_inn !== undefined) {
  const digits = String(ex.counterparty_inn).replace(/\D/g, '');
  // защита от «выдуманного» моделью ИНН: цифры должны реально присутствовать в сообщении пользователя
  const userDigits = String(ctx.text || '').replace(/\D/g, '');
  if (digits && userDigits.includes(digits)) put('counterparty_inn', digits);
  else if (digits) innDropped = true;
}
if (typeof ex.counterparty_is_foreign === 'boolean') put('counterparty_is_foreign', ex.counterparty_is_foreign);
if (clean(ex.counterparty_country)) put('counterparty_country', clean(ex.counterparty_country));
if (clean(ex.subject)) put('subject', clean(ex.subject));
if (typeof ex.amount === 'number' && isFinite(ex.amount) && ex.amount > 0) put('amount', ex.amount);
if (clean(ex.currency)) {
  const cur = String(ex.currency).toUpperCase();
  put('currency', ref.rates_rub[cur] !== undefined ? cur : 'OTHER');
}
if (typeof ex.vat_included === 'boolean') put('vat_included', ex.vat_included);
if (ex.start_date && isIsoDate(ex.start_date)) put('start_date', ex.start_date);
if (ex.end_date && isIsoDate(ex.end_date)) put('end_date', ex.end_date);
if (clean(ex.term_text)) put('term_text', clean(ex.term_text));
if (clean(ex.payment_terms)) put('payment_terms', clean(ex.payment_terms));
if (clean(ex.initiator_department)) put('initiator_department', clean(ex.initiator_department));
if (typeof ex.uses_standard_template === 'boolean') put('uses_standard_template', ex.uses_standard_template);

// 3. Списки объединяются без дублей
const union = (a, b) => {
  const out = [];
  const seen = new Set();
  for (const x of [].concat(a || [], b || [])) {
    const s = String(x).trim();
    const key = s.toLowerCase();
    if (s && !seen.has(key)) { seen.add(key); out.push(s); }
  }
  return out;
};
card.non_standard_terms = union(card.non_standard_terms, ex.non_standard_terms);
const claimed = Array.isArray(ex.attachments_claimed) ? ex.attachments_claimed.filter((c) => ref.attachment_labels[c]) : [];
card.attachments_claimed = union(card.attachments_claimed, claimed);

// 4. Файлы из Telegram: тип документа определяется по имени файла (детерминированные правила)
const ATT_RULES = [
  ['specification', /специф|specif/i],
  ['terms_of_reference', /(^|[\s_\-.])тз([\s_\-.]|$)|техзад|техническ\S*\s*задан|terms.?of.?ref/i],
  ['estimate', /смет|estimate/i],
  ['property_docs', /егрн|собственн|право.?устан|свидетельств/i],
  ['charter_docs', /устав|егрюл|огрн|учредит|charter/i],
  ['power_of_attorney', /доверенн/i],
  ['draft_contract', /договор|контракт|проект|contract|agreement|соглашен/i],
];
const classify = (name) => {
  for (const [code, re] of ATT_RULES) if (re.test(name)) return code;
  return 'other';
};
const files = Array.isArray(card.files) ? card.files.slice() : [];
for (const a of ctx.attachments || []) {
  if (!files.some((f) => f.name === a.name)) files.push({ name: a.name, type: classify(a.name) });
}
card.files = files;

// 5. Режим дальнейшей обработки
let mode = 'process';
if (!llm_ok) mode = 'error';
else if (intent === 'question') mode = 'question';
else if (intent === 'off_topic') mode = 'off_topic';

const prev = fresh ? '' : String(ctx.request_text || '');
const added = ctx.text || (ctx.attachments && ctx.attachments.length ? '[файл] ' + ctx.attachments.map((a) => a.name).join(', ') : '');
const request_text = ((prev ? prev + '\n---\n' : '') + added).slice(-6000);

const rand = Math.random().toString(36).slice(2, 6);
return [{
  json: {
    ...ctx,
    mode,
    intent,
    llm_ok,
    card,
    comment: (typeof ex.comment === 'string' ? ex.comment : '') + (innDropped ? ' ИНН из ответа ИИ не найден в вашем сообщении и проигнорирован.' : ''),
    question_text: typeof ex.question_text === 'string' && ex.question_text ? ex.question_text : (ctx.text || ''),
    request_text,
    attempts: fresh ? 0 : ctx.attempts,
    row_id: fresh ? null : ctx.row_id,
    request_uid: fresh ? 'R' + Date.now().toString(36) + rand : ctx.request_uid,
    session_status: fresh ? null : ctx.session_status,
    has_session: fresh ? false : ctx.has_session,
    new_session: fresh,
  },
}];
