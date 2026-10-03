// RAG: поиск релевантных фрагментов регламента (BM25 по корпусу) — модель отвечает только по найденным фрагментам.
const ref = $('Справочники и регламент').first().json.ref;
const P = { ...$json };
const query = String(P.question_text || P.text || '');

const STOP = new Set(['что', 'как', 'какой', 'какие', 'какая', 'какое', 'нужно', 'нужны', 'нужен', 'надо', 'для', 'при', 'или', 'это', 'если', 'есть', 'мне', 'мой', 'где', 'когда', 'почему', 'сколько', 'можно', 'будет', 'кто', 'все', 'всех', 'чтобы', 'тоже', 'ещё', 'уже', 'так']);
const tokenize = (s) => (String(s).toLowerCase().match(/[a-zа-яё0-9]+/g) || [])
  .filter((w) => w.length > 2 && !STOP.has(w))
  .map((w) => w.slice(0, 5));

const docs = ref.regulation.map((r) => ({ r, toks: tokenize(r.title + ' ' + r.text) }));
const N = docs.length;
const avgdl = docs.reduce((s, d) => s + d.toks.length, 0) / N;
const qt = Array.from(new Set(tokenize(query)));
const df = {};
qt.forEach((t) => { df[t] = docs.filter((d) => d.toks.includes(t)).length; });

const k1 = 1.5;
const b = 0.75;
const chunks = docs
  .map((d) => {
    const tf = {};
    d.toks.forEach((t) => { tf[t] = (tf[t] || 0) + 1; });
    let score = 0;
    for (const t of qt) {
      if (!tf[t]) continue;
      const idf = Math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5));
      score += idf * ((tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + (b * d.toks.length) / avgdl)));
    }
    return { id: d.r.id, title: d.r.title, text: d.r.text, score: Math.round(score * 100) / 100 };
  })
  .filter((x) => x.score > 0)
  .sort((a, z) => z.score - a.score)
  .slice(0, 3);

return [{ json: { ...P, rag_query: query, chunks } }];
