// A3. Проверка комплектности пакета (Quick Win №2): детерминированный чек-лист обязательных полей и приложений.
// Решение о полноте принимает код, а не модель: результат воспроизводим и проверяем.
const ref = $('Справочники и регламент').first().json.ref;
const P = { ...$json };
const c = P.card || {};
const T = c.contract_type || null;
const isNda = T === 'nda';
const foreign = c.counterparty_is_foreign === true;
const files = Array.isArray(c.files) ? c.files : [];
const claimed = Array.isArray(c.attachments_claimed) ? c.attachments_claimed : [];
const has = (code) => files.some((f) => f.type === code) || claimed.includes(code);

const checks = [];
const req = (code, ok, label, hint) => checks.push({ code, ok: !!ok, label, hint: hint || '' });
const warnings = [];

// контрольная сумма ИНН (10 цифр — организация, 12 — ИП/физлицо)
const innValid = (inn) => {
  if (!/^\d+$/.test(inn || '')) return false;
  const d = inn.split('').map(Number);
  const sum = (w, n) => w.reduce((s, k, i) => s + k * d[i], 0) % 11 % 10;
  if (d.length === 10) return sum([2, 4, 10, 3, 5, 9, 4, 6, 8]) === d[9];
  if (d.length === 12) return sum([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === d[10] && sum([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === d[11];
  return false;
};

req('contract_type', T, 'Тип договора', 'поставка / услуги / подряд / аренда / NDA');
req('counterparty_name', c.counterparty_name, 'Контрагент', 'наименование организации');

if (foreign) {
  req('counterparty_country', c.counterparty_country, 'Страна регистрации контрагента', '');
} else if (!c.counterparty_inn) {
  req('counterparty_inn', false, 'ИНН контрагента', '10 цифр для организации, 12 — для ИП');
} else if (!innValid(c.counterparty_inn)) {
  req('counterparty_inn', false, 'Корректный ИНН контрагента', 'указанный ' + c.counterparty_inn + ' не проходит проверку контрольной суммы — проверьте цифры');
} else {
  req('counterparty_inn', true, 'ИНН контрагента');
}

req('subject', c.subject, 'Предмет договора', 'что поставляется / оказывается / арендуется');

if (!isNda) {
  const amountOk = typeof c.amount === 'number' && c.amount > 0 && c.amount < 1e12;
  req('amount', amountOk, 'Сумма договора', c.amount ? 'значение выглядит ошибочным: ' + c.amount : 'число и валюта, например «12 млн руб.»');
  req('currency', !amountOk || c.currency, 'Валюта договора', 'RUB / USD / EUR / CNY');
  req('payment_terms', c.payment_terms, 'Условия оплаты', 'например: оплата в течение 30 дней после приёмки');
}

let termOk = !!(c.end_date || c.term_text);
let termHint = 'дата окончания или период (например, «12 месяцев»)';
const today = new Date().toISOString().slice(0, 10);
if (c.start_date && c.end_date && c.end_date < c.start_date) {
  termOk = false;
  termHint = 'дата окончания ' + c.end_date + ' раньше даты начала ' + c.start_date;
} else if (c.end_date && c.end_date < today) {
  termOk = false;
  termHint = 'дата окончания ' + c.end_date + ' уже в прошлом';
}
req('term', termOk, 'Срок действия договора', termHint);

req('initiator_department', c.initiator_department, 'Подразделение-инициатор', 'нужно, чтобы определить руководителя для согласования');

// основа договора: типовой шаблон или проект контрагента
if (c.uses_standard_template === true) {
  req('template', true, 'Основа договора');
} else if (c.uses_standard_template === false) {
  req('draft_contract', has('draft_contract'), 'Проект договора контрагента', 'приложите файл');
} else {
  req('template', has('draft_contract'), 'Основа договора', 'типовой шаблон компании или проект контрагента (приложите файлом)');
}

// обязательные приложения по типу договора
for (const code of (ref.required_attachments[T] || [])) {
  req('att_' + code, has(code), 'Приложение: ' + ref.attachment_labels[code], 'приложите файл или напишите, что документ уже есть');
}
// новый контрагент — учредительные документы
if (c.counterparty_known === false && c.counterparty_name) {
  req('att_charter_docs', has('charter_docs'), 'Приложение: ' + ref.attachment_labels.charter_docs, 'контрагент новый — приложите файл');
}

// предупреждения (не блокируют запуск)
if ((c.non_standard_terms || []).length) warnings.push('Нестандартные условия: ' + c.non_standard_terms.join('; ') + ' — потребуется углублённая юридическая экспертиза');
if (c.counterparty_risk === 'high') warnings.push('Контрагент в перечне повышенного риска');
if (isNda && c.amount) warnings.push('Для NDA сумма не требуется — значение учтено только справочно');
if (P.comment) warnings.push(P.comment);

const missing = checks.filter((x) => !x.ok).map((x) => ({ code: x.code, label: x.label, hint: x.hint }));
const filled = checks.length - missing.length;
// прогресс = после ответа пользователя заполнено больше пунктов, чем раньше (для первой проверки прогресс засчитывается)
const progress = c._filled === undefined || c._filled === null ? true : filled > Number(c._filled);
const check = {
  complete: missing.length === 0,
  missing,
  warnings,
  total: checks.length,
  filled,
  progress,
};

return [{ json: { ...P, card: { ...c, _filled: filled }, check } }];
