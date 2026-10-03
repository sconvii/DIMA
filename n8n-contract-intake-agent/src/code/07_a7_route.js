// A7. Подбор маршрута согласования: матрица согласования по сумме, типу, риску контрагента и нестандартным условиям (правила — в коде, не у модели).
const ref = $('Справочники и регламент').first().json.ref;
const P = { ...$json };
const c = P.card || {};
const check = P.check || { complete: false, missing: [], warnings: [], total: 0, filled: 0 };
const th = ref.thresholds;

const esc = (s) => String(s === undefined || s === null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const money = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
const CUR = { RUB: '₽', USD: '$', EUR: '€', CNY: '¥', KZT: '₸', OTHER: '' };
const ruDate = (iso) => (iso ? String(iso).split('-').reverse().join('.') : '');

// ---- маршрут ----
const amount = Number(c.amount || 0);
const rate = ref.rates_rub[c.currency || 'RUB'] || 1;
const amount_rub = Math.round(amount * rate);
const isNda = c.contract_type === 'nda';
const foreign = c.counterparty_is_foreign === true;
const known = c.counterparty_known === true;
const risk = c.counterparty_risk || 'unknown';
const nonStd = (c.non_standard_terms || []).length > 0;

const reasons = [];
const parallel = ['Юридический отдел'];
if (!isNda) parallel.push('Финансовый контролёр');

const sbWhy = [];
if (c.counterparty_name && !known) sbWhy.push('контрагент новый (нет в справочнике)');
if (foreign) sbWhy.push('иностранный контрагент');
if (risk === 'medium' || risk === 'high') sbWhy.push('риск контрагента: ' + (risk === 'high' ? 'высокий' : 'средний'));
if (amount_rub >= th.sb_amount) sbWhy.push('сумма ' + money(amount_rub) + ' ₽ ≥ ' + money(th.sb_amount) + ' ₽');
if (sbWhy.length) {
  parallel.push('Служба безопасности');
  reasons.push('СБ: ' + sbWhy.join('; '));
}

const sequential = ['Руководитель подразделения' + (c.initiator_department ? ' (' + c.initiator_department + ')' : '')];
const topWhy = [];
if (amount_rub >= th.top_amount) topWhy.push('сумма ' + money(amount_rub) + ' ₽ ≥ ' + money(th.top_amount) + ' ₽');
if (risk === 'high') topWhy.push('высокий риск контрагента');
if (nonStd && amount_rub >= th.top_nonstandard_amount) topWhy.push('нестандартные условия при сумме ≥ ' + money(th.top_nonstandard_amount) + ' ₽');
if (foreign && amount_rub >= th.top_foreign_amount) topWhy.push('иностранный контрагент при сумме ≥ ' + money(th.top_foreign_amount) + ' ₽');
if (topWhy.length) {
  sequential.push('Топ-менеджмент');
  reasons.push('Топ-менеджмент: ' + topWhy.join('; '));
}
if (nonStd) reasons.push('Юристы: нестандартные условия — углублённая экспертиза');

// ---- срок (рабочие дни) ----
const sla = ref.sla_days;
const expertiseDays = nonStd || foreign ? sla.expertise_extended : sla.expertise;
const totalDays = expertiseDays + sla.manager + (topWhy.length ? sla.top : 0);
const due = new Date();
let left = totalDays;
while (left > 0) {
  due.setDate(due.getDate() + 1);
  const wd = due.getDay();
  if (wd !== 0 && wd !== 6) left -= 1;
}
const dueIso = due.toISOString().slice(0, 10);

const route = {
  parallel,
  sequential,
  reasons,
  amount_rub,
  sla_days: totalDays,
  due_date: dueIso,
  template: ref.templates[c.contract_type] || null,
  text: parallel.join(' + ') + ' → ' + sequential.join(' → '),
};

// ---- блоки для сообщений ----
const rows = [];
rows.push('📄 <b>Карточка заявки</b> · заполнено ' + check.filled + ' из ' + check.total);
rows.push('Тип: ' + esc(ref.types[c.contract_type] || '—'));
let cp = esc(c.counterparty_name || '—');
if (c.counterparty_inn) cp += ', ИНН ' + esc(c.counterparty_inn);
if (c.counterparty_is_foreign && c.counterparty_country) cp += ', ' + esc(c.counterparty_country);
if (c.counterparty_known === true) cp += ' ✔ в справочнике';
if (c.counterparty_known === false) cp += ' ⚠ нет в справочнике';
rows.push('Контрагент: ' + cp);
rows.push('Предмет: ' + esc(c.subject || '—'));
if (!isNda) {
  rows.push('Сумма: ' + (c.amount ? money(c.amount) + ' ' + (CUR[c.currency] || esc(c.currency || '')) + (c.vat_included === true ? ' (с НДС)' : c.vat_included === false ? ' (без НДС)' : '') : '—'));
  rows.push('Оплата: ' + esc(c.payment_terms || '—'));
}
rows.push('Срок: ' + esc(c.end_date ? (c.start_date ? ruDate(c.start_date) + ' — ' : 'до ') + ruDate(c.end_date) : (c.term_text || '—')));
rows.push('Подразделение: ' + esc(c.initiator_department || '—'));
const base = c.uses_standard_template === true
  ? 'типовой шаблон' + (route.template ? ' ' + route.template : '')
  : (c.uses_standard_template === false || (c.files || []).some((f) => f.type === 'draft_contract') ? 'проект контрагента' : '—');
rows.push('Основа договора: ' + esc(base));
const fl = (c.files || []).map((f) => esc(f.name) + (f.type !== 'other' ? ' (' + esc(ref.attachment_labels[f.type] || f.type) + ')' : ''));
const cl = (c.attachments_claimed || []).filter((k) => !(c.files || []).some((f) => f.type === k)).map((k) => esc(ref.attachment_labels[k] || k) + ' (со слов инициатора)');
if (fl.length || cl.length) rows.push('Документы: ' + fl.concat(cl).join(', '));
(c.non_standard_terms || []).forEach((t) => rows.push('⚠ Нестандартное условие: ' + esc(t)));
(P.notes || []).forEach((t) => rows.push('ℹ️ ' + esc(t)));
const card_html = rows.join('\n');

const rt = [];
rt.push('🧭 <b>Маршрут согласования</b>');
rt.push('1. Параллельная экспертиза: ' + parallel.map(esc).join(' · '));
rt.push('2. ' + sequential.map(esc).join(' → '));
if (reasons.length) rt.push('Почему так: ' + reasons.map(esc).join(' | '));
rt.push('⏱ Плановый срок: ' + totalDays + ' раб. дн. (до ' + ruDate(dueIso) + ')');
const route_html = rt.join('\n');

return [{ json: { ...P, route, card_html, route_html } }];
