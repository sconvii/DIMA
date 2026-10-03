// Конверт «ответ по регламенту»: ответ модели (только по найденным фрагментам) либо запасной вариант — текст лучшего фрагмента.
const P = $('Поиск по регламенту (RAG)').first().json;
const esc = (s) => String(s === undefined || s === null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

let ans = $json.output && $json.output[0] && $json.output[0].content && $json.output[0].content[0]
  ? $json.output[0].content[0].text
  : null;
if (ans && typeof ans === 'object') ans = JSON.stringify(ans);
if (typeof ans !== 'string' || !ans.trim()) ans = null;

let text;
if (ans) {
  text = '📘 ' + esc(ans.trim().slice(0, 1400));
} else if (P.chunks.length) {
  text = '📘 По регламенту — <b>' + esc(P.chunks[0].title) + '</b>:\n' + esc(P.chunks[0].text);
} else {
  text = '📘 В регламенте нет ответа на этот вопрос — уточните его у юридического отдела.';
}
if (P.chunks.length) text += '\n\n<i>Источник: регламент, ' + P.chunks.map((c) => c.id).join(', ') + '</i>';
if (P.has_session) text += '\n\nЗаявка не потеряна: отправьте недостающие данные или /cancel, чтобы отменить.';
if (text.length > 3900) text = text.slice(0, 3890) + '…';

return [{ json: { chat_id: P.chat_id, text, keyboard: null, save: null } }];
