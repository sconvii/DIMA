// A1. Справочник контрагента (имитация CRM/ERP): находит контрагента по ИНН или названию, подставляет реквизиты и профиль риска.
const ref = $('Справочники и регламент').first().json.ref;
const P = { ...$json };
const card = { ...(P.card || {}) };
const notes = [];

// сбрасываем производные поля — они пересчитываются при каждом проходе
delete card.counterparty_known;
delete card.counterparty_risk;
delete card.counterparty_dir_id;

const normName = (s) => String(s || '')
  .toLowerCase()
  .replace(/[«»"'“”().,]/g, ' ')
  .replace(/(^|\s)(ооо|оао|зао|пао|ао|ип|ltd|llc|inc|gmbh)(?=\s|$)/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

let hit = null;
let matchedBy = '';
if (card.counterparty_inn) {
  hit = ref.directory.find((d) => d.inn && d.inn === card.counterparty_inn) || null;
  if (hit) matchedBy = 'inn';
}
if (!hit && card.counterparty_name) {
  const n = normName(card.counterparty_name);
  if (n.length >= 4) {
    hit = ref.directory.find((d) => d.aliases.some((a) => n.includes(a) || (n.length >= 6 && a.includes(n)))) || null;
    if (hit) matchedBy = 'name';
  }
}

if (hit) {
  card.counterparty_known = true;
  card.counterparty_risk = hit.risk;
  card.counterparty_dir_id = hit.id;
  if (!card.counterparty_name) card.counterparty_name = hit.name;
  if (matchedBy === 'name' && hit.inn) {
    if (!card.counterparty_inn) {
      card.counterparty_inn = hit.inn;
      notes.push('ИНН подставлен из справочника: ' + hit.inn);
    } else if (card.counterparty_inn !== hit.inn) {
      notes.push('ИНН в заявке (' + card.counterparty_inn + ') не совпадает с ИНН «' + hit.name + '» в справочнике (' + hit.inn + ') — проверьте');
    }
  }
  if (hit.foreign) {
    card.counterparty_is_foreign = true;
    if (!card.counterparty_country) card.counterparty_country = hit.country;
  } else if (card.counterparty_is_foreign === undefined || card.counterparty_is_foreign === null) {
    card.counterparty_is_foreign = false;
  }
  notes.push('Контрагент найден в справочнике: ' + hit.name + ' (риск: ' + ({ low: 'низкий', medium: 'средний', high: 'высокий' }[hit.risk] || hit.risk) + ')');
  if (hit.note) notes.push('Справочник: ' + hit.note);
} else if (card.counterparty_name || card.counterparty_inn) {
  card.counterparty_known = false;
  card.counterparty_risk = 'unknown';
  notes.push('Контрагент не найден в справочнике — считается новым: потребуются учредительные документы и проверка СБ');
}

if (P.truncated) notes.push('Сообщение длиннее 3500 символов — обработана только его первая часть');

return [{ json: { ...P, card, notes } }];
