// Лёгкий прогон Code-нод вне n8n: имитация $input / $json / $('Node').
const fs = require('fs');
const path = require('path');

function load(name) { return fs.readFileSync(path.join(__dirname, 'code', name), 'utf8'); }

function run(file, { json = {}, items = null, nodes = {} } = {}) {
  const src = load(file);
  const inputItems = items || [{ json }];
  const $input = { all: () => inputItems, first: () => inputItems[0], last: () => inputItems[inputItems.length - 1] };
  const $ = (name) => {
    if (!(name in nodes)) throw new Error('Node not executed in test: ' + name);
    const arr = nodes[name];
    return { first: () => arr[0], all: () => arr, last: () => arr[arr.length - 1], isExecuted: true };
  };
  const fn = new Function('$input', '$json', '$', 'return (function(){' + src + '\n})();');
  return fn($input, inputItems[0].json, $);
}

module.exports = { run };

if (require.main === module) {
  const T = (cond, msg) => { console.log((cond ? 'OK   ' : 'FAIL ') + msg); if (!cond) process.exitCode = 1; };

  // --- 01 нормализация ---
  const mk = (extra) => ({ update_id: 1, message: { message_id: 5, from: { id: 42, first_name: 'Анна', last_name: 'Иванова' }, chat: { id: 42 }, ...extra } });
  const norm = (u) => run('01_normalize.js', { json: u })[0].json;
  T(norm(mk({ text: '/start' })).input_type === 'start', 'start');
  T(norm(mk({ text: '/status' })).input_type === 'status', 'status');
  T(norm(mk({ text: '/foo' })).input_type === 'start', 'unknown command -> help');
  T(norm(mk({ text: 'Да' })).input_type === 'cb_confirm' && norm(mk({ text: 'Да' })).via_text, 'text confirm');
  T(norm(mk({ text: 'отмена' })).input_type === 'cb_cancel', 'text cancel');
  T(norm(mk({ text: 'Нужен договор поставки' })).input_type === 'content', 'content');
  T(norm(mk({ voice: { file_id: 'x' } })).input_type === 'unsupported', 'voice unsupported');
  T(norm(mk({ document: { file_name: 'Спецификация.pdf', mime_type: 'application/pdf', file_size: 100 } })).attachments.length === 1, 'document attachment');
  const cbU = { update_id: 2, callback_query: { id: 'cb1', from: { id: 42 }, data: 'confirm', message: { message_id: 9, text: 'x', chat: { id: 42 } } } };
  T(norm(cbU).input_type === 'cb_confirm' && norm(cbU).callback_query_id === 'cb1', 'callback confirm');
  T(norm(mk({ text: 'x'.repeat(5000) })).truncated === true, 'truncate');

  // --- pipeline ---
  const ctx0 = {
    chat_id: '42', user_name: 'Анна', input_type: 'content', text: '', attachments: [],
    action: 'content', quick: '', has_session: false, session_status: null, row_id: null,
    request_uid: 'R1', attempts: 0, request_text: '', card: {}, rows_brief: [],
  };
  const refNode = run('03_reference.js', { json: ctx0 })[0].json;
  const ref = refNode.ref;
  const nodes = { 'Состояние диалога': [{ json: ctx0 }], 'Справочники и регламент': [{ json: refNode }] };

  const llm = (obj) => ({ output: [{ content: [{ text: obj }] }] });
  const base = {
    intent: 'provide_info', contract_type: null, counterparty_name: null, counterparty_inn: null, counterparty_is_foreign: null,
    counterparty_country: null, subject: null, amount: null, currency: null, vat_included: null, start_date: null, end_date: null,
    term_text: null, payment_terms: null, initiator_department: null, uses_standard_template: null,
    non_standard_terms: [], attachments_claimed: [], question_text: null, comment: '',
  };

  function pipeline(ctx, ex) {
    const n2 = { ...nodes, 'Состояние диалога': [{ json: ctx }] };
    const merged = run('04_merge.js', { json: llm(ex), nodes: n2 })[0].json;
    const a1 = run('05_a1_directory.js', { json: merged, nodes: n2 })[0].json;
    const a3 = run('06_a3_check.js', { json: a1, nodes: n2 })[0].json;
    const a7 = run('07_a7_route.js', { json: a3, nodes: n2 })[0].json;
    return { merged, a1, a3, a7, n3: { ...n2, 'A7 Подбор маршрута': [{ json: a7 }] } };
  }

  // 1. полная заявка, известный контрагент, 12 млн, спецификация приложена файлом
  const full = {
    ...base, contract_type: 'supply', counterparty_name: 'ООО «Ромашка»', counterparty_inn: '7701234560', subject: 'поставка серверного оборудования',
    amount: 12000000, currency: 'RUB', vat_included: true, end_date: '2027-12-31', payment_terms: 'оплата в течение 30 дней после приёмки',
    initiator_department: 'ИТ', uses_standard_template: true,
  };
  let p = pipeline({ ...ctx0, attachments: [{ name: 'Спецификация.pdf', mime: 'application/pdf', size: 1, kind: 'document' }] }, full);
  T(p.a3.check.complete === true, 'full: complete -> ' + JSON.stringify(p.a3.check.missing));
  T(p.a7.route.parallel.includes('Служба безопасности') && p.a7.route.sequential.includes('Топ-менеджмент'), 'full: SB + top (12M)');
  console.log(p.a7.card_html + '\n' + p.a7.route_html + '\n');

  // 2. аренда без деталей
  p = pipeline(ctx0, { ...base, contract_type: 'lease', subject: 'аренда офиса' });
  T(p.a3.check.complete === false && p.a3.check.missing.length >= 6, 'lease: incomplete (' + p.a3.check.missing.map((m) => m.code).join(',') + ')');
  const ask = run('08_env_ask.js', { json: { output: [{ content: [{ text: { lead: 'Спасибо!', questions: [{ code: 'counterparty_name', text: 'Как называется контрагент?' }] } }] }] }, nodes: p.n3 })[0].json;
  T(/Как называется контрагент/.test(ask.text) && ask.save.status === 'collecting' && ask.save.attempts === 0, 'ask: llm question used + fallback for rest');
  console.log(ask.text + '\n');
  const askFallback = run('08_env_ask.js', { json: { error: 'x' }, nodes: p.n3 })[0].json;
  T(/Контрагент/.test(askFallback.text), 'ask: fallback templates when LLM failed');

  // 3. неверный ИНН
  p = pipeline({ ...ctx0, text: 'Контрагент ООО Ромашка, ИНН 7701234561' }, { ...full, counterparty_inn: '7701234561' });
  T(p.a3.check.missing.some((m) => m.code === 'counterparty_inn'), 'bad INN flagged');
  // 3b. LLM выдумал ИНН, которого нет в тексте пользователя -> отбрасывается
  p = pipeline({ ...ctx0, text: 'Нужен договор поставки с Ромашкой' }, { ...full, counterparty_inn: '7701234560' });
  T(!p.merged.card.counterparty_inn || p.a1.card.counterparty_inn === '7701234560', 'hallucinated INN is not kept from the model alone: ' + String(p.merged.card.counterparty_inn));

  // 4. NDA без суммы
  p = pipeline(ctx0, { ...base, contract_type: 'nda', counterparty_name: 'АО «ТехноСнаб»', subject: 'обмен техдокументацией', term_text: '3 года', initiator_department: 'ИТ', uses_standard_template: true });
  T(p.a3.check.complete === true, 'nda complete without amount: ' + JSON.stringify(p.a3.check.missing));
  T(!p.a7.route.parallel.includes('Финансовый контролёр'), 'nda: no fin controller');

  // 5. иностранный нестандарт
  p = pipeline({ ...ctx0, attachments: [{ name: 'ТЗ.docx', size: 1 }, { name: 'Учредительные документы.pdf', size: 1 }] },
    { ...base, contract_type: 'services', counterparty_name: 'GreenTech Ltd', subject: 'разработка ПО', amount: 100000, currency: 'USD', end_date: '2027-06-30', payment_terms: 'предоплата 100%', initiator_department: 'ИТ', uses_standard_template: true, non_standard_terms: ['предоплата 100%'] });
  T(p.a1.card.counterparty_known === true && p.a1.card.counterparty_is_foreign === true, 'foreign recognised via directory');
  T(p.a3.check.complete === true, 'foreign complete: ' + JSON.stringify(p.a3.check.missing));
  T(p.a7.route.sequential.includes('Топ-менеджмент') && p.a7.route.parallel.includes('Служба безопасности'), 'foreign: top + SB (9M rub)');

  // 6. регистрация
  const reg = run('10_a8_register.js', { json: {}, nodes: { 'A7 Подбор маршрута': [{ json: { ...p.a7, row_id: 12 } }] } })[0].json;
  T(/ЗД-\d{4}-00012/.test(reg.text) && reg.save.status === 'registered', 'register number');

  // 7. RAG
  const rag = run('12_rag.js', { json: { ...ctx0, question_text: 'Какие документы нужны для договора аренды?' }, nodes })[0].json;
  T(rag.chunks.length > 0 && rag.chunks.some((c) => c.id === 'R5'), 'rag finds lease chunk: ' + rag.chunks.map((c) => c.id).join(','));
  const rag2 = run('12_rag.js', { json: { ...ctx0, question_text: 'Кто утверждает договор на 20 млн рублей?' }, nodes })[0].json;
  T(rag2.chunks.some((c) => c.id === 'R10'), 'rag finds top mgmt chunk: ' + rag2.chunks.map((c) => c.id).join(','));

  // 8. state
  const stateRows = [{ id: 7, status: 'awaiting_confirmation', request_uid: 'RX', card_json: '{"subject":"s"}', attempts: 1, updatedAt: new Date().toISOString() }];
  const st = run('02_state.js', { items: stateRows.map((r) => ({ json: r })), nodes: { 'Нормализация входа': [{ json: { ...ctx0, input_type: 'cb_confirm' } }] } })[0].json;
  T(st.action === 'confirm' && st.row_id === 7, 'state: confirm with awaiting session');
  const st2 = run('02_state.js', { items: [{ json: {} }], nodes: { 'Нормализация входа': [{ json: { ...ctx0, input_type: 'cb_confirm' } }] } })[0].json;
  T(st2.action === 'quick' && st2.quick === 'stale', 'state: stale button without session');
}
