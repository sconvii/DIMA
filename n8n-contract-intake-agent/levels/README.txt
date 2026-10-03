Запасные мини-воркфлоу к домашнему заданию «Соберите свой первый воркфлоу»
=======================================================================

level1_minimum_trigger_llm_editfields.json
    Минимум из задания: Telegram Trigger -> OpenAI (Message a model, JSON Schema) -> Edit Fields.
    Бот принимает сообщение, ИИ извлекает тип договора, контрагента, сумму, валюту и предмет,
    Edit Fields раскладывает их по полям.

level2_branching_if.json
    То же + поле ready, узел IF «Данных достаточно?» и два ответа в Telegram (принято / нужны уточнения).

levelB_basic_llm_chain_structured_output_parser.json
    Вариант с узлами Basic LLM Chain + OpenAI Chat Model + Structured Output Parser -> Edit Fields.

Как использовать
----------------
1. В n8n: новый воркфлоу -> «...» -> Import... -> Import from file... -> выберите файл.
2. Telegram: создайте Credential «Telegram API» с токеном бота (имя оставьте «Telegram account» — тогда он подставится сам).
3. OpenAI: на n8n Cloud используются управляемые кредиты; если у узла красная метка — выберите свой OpenAI API credential.
4. Execute workflow (или Publish) и напишите боту, например:
   «Нужен договор поставки с ООО «Ромашка» на 12 млн руб., оборудование для офиса».

ВАЖНО: Telegram разрешает один вебхук на бота. Одновременно может быть опубликован только один воркфлоу
с этим ботом — основной (contract_intake_agent.n8n.json) или один из этих. Перед запуском одного
снимите публикацию (Unpublish) с другого.
