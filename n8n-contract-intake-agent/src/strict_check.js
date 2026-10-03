// Проверка JSON Schema на соответствие ограничениям строгого режима OpenAI (Structured Outputs, strict: true).
const P = require('./prompts');
const BAD = ['minLength', 'maxLength', 'pattern', 'format', 'minimum', 'maximum', 'multipleOf', 'patternProperties', 'unevaluatedProperties', 'propertyNames', 'minProperties', 'maxProperties', 'unevaluatedItems', 'contains', 'minContains', 'maxContains', 'minItems', 'maxItems', 'uniqueItems', 'default', '$ref', 'oneOf', 'allOf', 'not'];
const errs = [];
function walk(sch, p) {
  if (!sch || typeof sch !== 'object') return;
  for (const k of Object.keys(sch)) if (BAD.includes(k)) errs.push(p + ': запрещённое ключевое слово ' + k);
  const t = sch.type;
  const types = Array.isArray(t) ? t : t ? [t] : [];
  if (types.includes('object') || sch.properties) {
    if (sch.additionalProperties !== false) errs.push(p + ': additionalProperties должен быть false');
    const keys = Object.keys(sch.properties || {});
    const req = sch.required || [];
    for (const k of keys) if (!req.includes(k)) errs.push(p + ': свойство ' + k + ' не в required');
    for (const k of req) if (!keys.includes(k)) errs.push(p + ': required содержит неизвестное свойство ' + k);
    for (const k of keys) walk(sch.properties[k], p + '.' + k);
  }
  if (types.includes('array') || sch.items) walk(sch.items, p + '[]');
  if (sch.anyOf) sch.anyOf.forEach((s, i) => walk(s, p + '|' + i));
  if (sch.enum && types.length && !types.includes('null') && sch.enum.includes(null)) errs.push(p + ': enum содержит null без типа null');
}
for (const [name, sch] of [['EXTRACT_SCHEMA', P.EXTRACT_SCHEMA], ['QUESTIONS_SCHEMA', P.QUESTIONS_SCHEMA]]) {
  if (sch.type !== 'object') errs.push(name + ': корень должен быть object');
  walk(sch, name);
}
console.log(errs.length ? 'ОШИБКИ:\n' + errs.join('\n') : 'Схемы соответствуют строгому режиму OpenAI (strict: true)');
process.exitCode = errs.length ? 1 : 0;
