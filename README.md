# BPMN Process Modeler

📬 Feedback: GitHub Issues | Telegram @zagreev

Скилл для Claude, который превращает неструктурированное описание процесса в читаемую BPMN 2.0 схему (Camunda 7, Platform) и — по запросу — в Excel-спецификацию, сверенную со схемой.

**Версия:** 2.0.1
**Автор:** Andrey Zagreev — [@zagreev](https://t.me/zagreev)
**Лицензия:** [MIT](#лицензия)
**Целевая платформа:** Camunda 7 (Platform)
**Источники правил:** Camunda Best-practices (docs.camunda.io), bpmnlint rules, Camunda 7 Platform documentation

---

## Содержание

- [Для кого](#для-кого)
- [Что делает](#что-делает)
- [Когда скилл сработает](#когда-скилл-сработает)
- [Требования](#требования)
- [Установка](#установка)
- [Типовой сценарий использования](#типовой-сценарий-использования)
- [Как работает внутри (9 шагов)](#как-работает-внутри-9-шагов)
- [Что внутри архива](#что-внутри-архива)
- [Что гарантировано](#что-гарантировано)
- [Чего скилл НЕ делает](#чего-скилл-не-делает)
- [Известные ограничения](#известные-ограничения)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Обратная связь и итерации](#обратная-связь-и-итерации)
- [Contributing](CONTRIBUTING.md)
- [Changelog](#changelog)
- [Благодарности](#благодарности)
- [Лицензия](#лицензия)

---

## Для кого

Продуктовые менеджеры, бизнес-аналитики и процесс-оунеры, которые регулярно получают описания процессов в виде транскрибаций встреч, страниц в Confluence, писем, меморандумов. Вместо ручной отрисовки в Camunda Modeler — один запрос к Claude с этим скиллом.

## Что делает

**На входе** — произвольный текст, описывающий бизнес-процесс. Например:

> «Клиент подаёт заявку на BNPL через мобильное приложение. Скоринговая система проверяет кредитную историю и внутренние правила. Если балл выше 700 — одобряем автоматически, от 600 до 699 — ручная проверка риск-менеджером, ниже — отказ. При одобрении списываем 25% предоплаты…»

**На выходе** — рабочая BPMN-схема:

- Валидный XML, который открывается в Camunda Modeler с первого раза (без «пустого холста»)
- Все подписи на русском, продуктовые и бренд-названия сохраняются как есть
- Текстовые аннотации на схеме для SLA, регуляторных ссылок, бизнес-правил и открытых вопросов
- Автоматический выбор топологии (пулы / лэйны / плоская) и декомпозиции (иерархия с подпроцессами, если узлов больше 9)
- 7 блокирующих проверок корректности XML + 10 рекомендательных best practices перед показом

**После одобрения схемы** — Excel-спецификация:

- Лист «Спецификация» — по одной строке на каждый узел BPMN (задачи, события, шлюзы, подпроцессы)
- 9 колонок: №, Элемент BPMN, Название, Тип, Участник, Описание/Бизнес-правила, Входные данные, Выходные данные, Примечания/Compliance
- Лист «Участники» — пулы и лэйны с описанием ролей
- Лист «Открытые вопросы» — все пометки «⚠ Уточнить», сведённые в чек-лист для следующей встречи
- 9 проверок соответствия таблицы исходной схеме с явным статус-отчётом

## Когда скилл сработает

Скилл автоматически активируется на запросах вроде:

- «Нарисуй BPMN по этой транскрибации»
- «Сделай схему процесса в Camunda»
- «Смоделируй процесс одобрения BNPL»
- «Вот описание процесса, нужна диаграмма с пулами»
- «Преврати это в .bpmn файл»
- «Нужна Excel-таблица по этому BPMN»

Не сработает на запросах про UML, sequence-диаграммы, ER-диаграммы, Mermaid, Excalidraw — у них своя специфика.

## Требования

**Обязательно:**
- **Camunda MCP** (либо активный, либо недоступность переживается через fallback на snapshot) — MCP даёт живую документацию Camunda и всегда предпочтителен. URL: `https://camunda-docs.mcp.kapa.ai`. Активируется в Settings → Connectors.
- **Локальный snapshot Camunda docs** — в архив скилла включён файл `references/camunda-knowledge-snapshot.md` с курированной выжимкой Camunda 7 документации. Используется автоматически, если MCP недоступен. Версия snapshot'а — см. заголовок файла.

**Желательно:**
- **Встроенный `xlsx` скилл** — обычно уже активен по умолчанию в claude.ai. Нужен для выгрузки Excel-спецификации.

**Что происходит в degraded mode (MCP недоступен, скилл работает на snapshot):**
- Генерация XML, валидация, Excel-экспорт идут как обычно
- Перед вопросом одобрения схемы скилл явно предупреждает, что использован snapshot
- В заголовке XML указано `<!-- Camunda knowledge: snapshot v1.0 (2026-04-23) -->`
- Перед prod-деплоем рекомендуется активировать MCP и перегенерировать, либо свериться с live docs вручную

## Установка

1. Скачайте `bpmn-process-modeler.skill`
2. В claude.ai: **Settings → Capabilities → Skills → Upload skill**
3. Выберите файл `.skill` — он развернётся автоматически
4. Активируйте **Camunda MCP** в **Settings → Connectors** (URL: `https://camunda-docs.mcp.kapa.ai`)
5. Убедитесь, что **xlsx** скилл активен (обычно включён по умолчанию)

После установки скилл будет триггериться автоматически — отдельно его вызывать не нужно.

## Типовой сценарий использования

1. Копируете транскрибацию встречи или описание процесса в чат с Claude
2. Пишете: «Смоделируй этот процесс в BPMN» или «Нарисуй схему в Camunda»
3. Claude отдаёт:
   - Классификацию (отрасль, участники, выбранная топология, выбранная декомпозиция)
   - XML-код схемы (или несколько файлов, если иерархия)
   - Отчёт о прохождении 7 валидаций + статус 10 рекомендательных best practices
   - Список открытых вопросов, которые нужно уточнить
   - Вопрос: «Схема корректна? После подтверждения могу выгрузить спецификацию в Excel»
4. Открываете XML в Camunda Modeler, проверяете
5. Если нужны правки — пишете их Claude, получаете обновлённую схему
6. Если всё ок — пишете «да» / «выгружай» / «сделай таблицу»
7. Claude генерирует `.xlsx`, прогоняет 9 проверок сверки, показывает статус-отчёт, отдаёт файл

## Как работает внутри (9 шагов)

1. **Загрузка документации Camunda** через MCP — синтаксис BPMN, extension-элементы, паттерны пулов, аннотации, сабпроцессы
2. **Классификация входа** — отрасль, участники, активности, события, шлюзы, артефакты
3. **Выбор топологии** по правилу: несколько организаций → collaboration с пулами; один бизнес с ролями → пул с лэйнами; один актёр → плоский процесс
4. **Выбор декомпозиции** по правилу 7±2: больше 9 узлов или 2+ уровня вложенных шлюзов → overview + drill-down подпроцессы
5. **Генерация BPMN XML** в UTF-8, с русскими подписями, BPMN DI, Camunda extensions, текстовыми аннотациями для SLA / регуляторки / открытых вопросов
6. **Валидация XML**: 7 блокирующих проверок (well-formedness, BPMN schema, структурная целостность + infinite loop + event references + boundary events + duplicate IDs + subprocess types + data objects, message flows + collaboration, Camunda 7 executability, DI completeness, соответствие русского языка) + 10 рекомендательных best practices (technical ID naming, happy path, business vs technical errors, sentence case и др.)
7. **Показ пользователю**: классификация + XML + отчёт валидации + открытые вопросы + вопрос про Excel
8. **Excel-выгрузка** (только после одобрения схемы) в UTF-8, с цветовой кодировкой типов BPMN, скрытой колонкой `_BPMN_ID` для сверки
9. **Сверка Excel ↔ BPMN** — 9 проверок: количество узлов, ID-маппинг, названия, лэйны, правила на шлюзах, итоги на end-событиях, аннотации, порядок выполнения, UTF-8. Статус показывается перед выдачей файла

## Что внутри архива

```
bpmn-process-modeler/
├── README.md                            — это описание
├── SKILL.md                             — основная логика скилла
└── references/
    ├── bpmn-patterns.md                 — 8 готовых XML-паттернов (approval loop, 4-eyes, параллельное согласование, таймерная эскалация, компенсация, B2B-обмен сообщениями, DMN, event-based gateway)
    ├── camunda-knowledge-snapshot.md    — fallback-snapshot Camunda docs на случай недоступности MCP (~1170 строк, версия 1.0 от 2026-04-23); BPMN 2.0 + Camunda 7 extensions + DI + best practices + методология построения (happy path first, explicit modeling, декомпозиция, anti-patterns)
    ├── industry-patterns/               — отраслевые паттерны, по одному файлу на domain; модель читает ТОЛЬКО соответствующий файл на Step 2
    │   ├── fintech-patterns.md          — 17 процессов: KYC / KYB / Seller KYB / BaaS onboarding / Payment auth / 3DS / P2P / Chargeback / Refund / BNPL / Collection / Leasing / Factoring / Seller lending / RBF (Merchant Cash Advance) / Settlement-payout / Regulatory reporting
    │   ├── marketplace-patterns.md      — 5 процессов: Order-to-cash / Returns / Pick-Pack-Ship / Seller discovery / Cross-border marketplace
    │   ├── project-finance-patterns.md  — 4 процесса: розничная ипотека / кредитование застройщиков (214-ФЗ) / проектное финансирование (SPV, IC) / Workout
    │   ├── healthcare-patterns.md       — приём пациента, диспансеризация
    │   ├── manufacturing-patterns.md    — производственный заказ
    │   ├── hr-patterns.md               — онбординг, отпуск
    │   ├── public-sector-patterns.md    — государственная услуга (ФЗ-210)
    │   └── it-ops-patterns.md           — incident management, change management
    ├── annotation-style-guide.md        — когда использовать textAnnotation + шаблоны фраз на русском; отдельный подраздел про особенности аннотирования шлюзов (XOR / OR / event-based / parallel, default flow, FEEL-condition, вынесение логики в DMN)
    ├── validation-checklist.md          — 7 блокирующих проверок XML с Python-кодом + 10 рекомендательных best practices (на основе Camunda bpmnlint и docs)
    ├── excel-spec-template.md           — 9-колоночный шаблон + worked example на BNPL
    └── reconciliation-procedure.md      — 9 проверок сверки Excel и BPMN с openpyxl-кодом
```

## Что гарантировано

- **Рендерится в Modeler с первого раза** — BPMN DI есть для всех узлов, стрелок, аннотаций; корректные координаты; `isHorizontal="true"` на пулах/лэйнах, `isMarkerVisible="true"` на XOR-шлюзах
- **Подписи на русском** — для всех задач, событий, шлюзов, пулов, лэйнов, условий на стрелках (продуктовые названия из whitelist сохраняются)
- **Текстовые аннотации с источниками** — SLA, регуляторные ссылки (ФЗ-115, PSD2, GDPR, и т.д.), бизнес-правила, интеграционные детали, открытые вопросы с префиксом «⚠ Уточнить:»
- **Camunda 7 executability** — для User Tasks: `camunda:assignee` / `camunda:candidateGroups`; для Service Tasks: `camunda:type="external"` + `camunda:topic` либо `camunda:delegateExpression`; для Business Rule Tasks: `camunda:decisionRef`
- **Excel совпадает с XML byte-for-byte** — 9 проверок сверки прогоняются перед выдачей файла; любые расхождения фиксируются в статус-отчёте
- **Весь Excel на русском** — категории, приоритеты, типы элементов переведены; латиница только для whitelist (аббревиатуры, бренды, валюты, ISO durations, технические BPMN IDs в скрытых колонках)
- **Отказоустойчивость при недоступности MCP** — скилл продолжает работать на локальном snapshot (`references/camunda-knowledge-snapshot.md`) с явным предупреждением в выводе; HALT только при повреждённом архиве

## Чего скилл НЕ делает

- Не придумывает бизнес-правила, которых нет в исходном тексте — вместо этого добавляет «⚠ Уточнить» на схему
- Не выдаёт Excel без предварительного одобрения схемы
- Не скрывает расхождения между XML и Excel — если сверка нашла проблему, она в статус-отчёте
- Не даёт юридических выводов — регуляторные ссылки на схеме всегда указывают статью/пункт документа, но без трактовки
- Не генерирует XML для Camunda 8 / Zeebe — целевая платформа зафиксирована как Camunda 7 (Platform)

## Известные ограничения

- **Размер процесса.** Оптимальный: 8–25 узлов на одном уровне. Больше — DI-координаты начинают пересекаться, нужна декомпозиция (Level 0 + Level 1 + …). При 40+ узлах в плоской структуре качество layout падает.
- **Язык.** Только русский для семантических меток. Смешанные диаграммы (часть подписей на английском) не поддерживаются.
- **Платформа.** Только Camunda 7 Platform. Camunda 8 / Zeebe, Flowable, Activiti, jBPM, Bonita — не поддерживаются.
- **BPMN coverage.** Покрываются задачи (все подтипы), события (все стандартные), шлюзы (XOR / AND / OR / event-based), подпроцессы (embedded / event / call activity), data objects/stores. НЕ покрываются: BPMN Choreography diagrams, BPMN Conversations, ad-hoc subprocesses (экспериментально), transaction subprocesses.
- **Объём iterations.** Для сложных процессов (15+ узлов, 3+ уровня иерархии, 5+ пулов) — может потребоваться 2–3 итерации правок перед получением корректного результата.
- **MCP-предпочтение.** Camunda MCP — предпочтительный источник live-документации; при его недоступности скилл переходит в degraded mode на локальный snapshot (подробнее в секции «Требования»). Snapshot обновляется вручную — инструкция ниже.

## Refresh snapshot procedure

Локальный `references/camunda-knowledge-snapshot.md` — курированная выжимка Camunda docs. Рекомендуется обновлять раз в 6 месяцев или после мажорного обновления Camunda 7.

**Как обновить:**

1. Проверить дату в шапке snapshot-файла (`snapshot_date`).
2. Если > 6 месяцев — открыть чат с Claude, где активен Camunda MCP.
3. Сказать: «Обнови snapshot Camunda knowledge. Сохрани новую версию в `references/camunda-knowledge-snapshot.md`. Увеличь `snapshot_version` и `snapshot_date`.»
4. Claude пройдётся по разделам snapshot'а, сверит каждый с live MCP-ответом, обновит изменившиеся куски и увеличит версию.
5. Пересобрать `.skill` архив и перераспространить.

Следующее плановое обновление: см. `maintenance_note` в заголовке snapshot-файла.

## Troubleshooting / FAQ

**Camunda MCP не подключается.** Проверьте в Settings → Connectors, что URL указан точно: `https://camunda-docs.mcp.kapa.ai`. Перезапустите чат, иногда connector-сессия истекает. Если проблема сохраняется — убедитесь, что у вас актуальный план Claude.ai (MCP доступен на Pro и выше). **Если MCP недоступен — скилл продолжит работать на локальном snapshot** (`references/camunda-knowledge-snapshot.md`), но перед prod-деплоем рекомендуется активировать MCP и перегенерировать XML, либо свериться с live docs. Скилл явно предупредит в выводе, когда работает в degraded mode.

**XML не открывается в Camunda Modeler — «пустой холст».** Обычно означает проблему с BPMN DI. Запросите у Claude: «Проверь DI в XML — не все ли узлы имеют BPMNShape?». Скилл пересоберёт DI-секцию. Если проблема сохраняется — приложите XML и скриншот Modeler в чат, Claude попросит фрагмент ошибки.

**Excel частично на английском.** Не должно случаться — 10-я проверка reconciliation ловит это и автоматически правит. Если всё же пролетело: укажите Claude, какие именно ячейки на английском (лист, колонка, значение) — перегенерирует с корректным переводом.

**Сгенерировался `zeebe:*` вместо `camunda:*`.** Целевая платформа захардкожена как Camunda 7, но теоретически может проскочить. Напишите Claude: «В XML есть zeebe-атрибуты. Платформа Camunda 7, замени на camunda». Скилл перегенерирует.

**Диаграмма с 30+ узлами визуально «сломана».** Скилл должен был сделать декомпозицию на Step 4, но пропустил. Попросите: «Разложи процесс на overview + drill-down подпроцессы; 5–7 фаз в overview, детали в каждом». Обычно после этого получается читаемый результат.

**Открытых вопросов «⚠ Уточнить» слишком много (10+).** Это не баг, это feature — скилл честно показывает, где в исходном тексте недостаточно деталей. Пройдитесь по листу «Открытые вопросы» в Excel с доменным экспертом, дополните, перегенерируйте.

## Обратная связь и итерации

Если скилл сработал неидеально — пропустил узел, неправильно выбрал топологию, ошибся в названии типа задачи, сгенерировал невалидный XML — напишите автору в Telegram [@zagreev](https://t.me/zagreev). Приложите:

- Текст исходника (транскрибацию / описание процесса)
- Что получилось (XML или Excel)
- Что ожидалось
- Версию скилла (см. заголовок README)

Рекомендуется итерировать на 2–3 реальных процессах из своей предметной области перед тем, как отдавать коллегам.

## Changelog

### v2.0.1 — апрель 2026

Release hygiene patch.

- Подтверждён состав `.skill`-архива: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` присутствуют в публикуемом артефакте.
- Добавлен пакет release/package-тестов (`tests/release/`): проверка version metadata, состава архива, markdown-ссылок внутри пакета, документационного контракта, компилируемости Python-сниппетов и парсинга XML-сниппетов.
- CI-gate: новые тесты прогоняются и в `release-checks.yml`, и в `build-skill.yml` перед публикацией.
- Dry-run `.skill` прикрепляется к каждому CI-run как артефакт для визуальной проверки состава.
- Поведение BPMN-генерации, валидации и Excel-выгрузки не изменялось.

### v2.0 — апрель 2026

Поддерживаемый публичный релиз с воспроизводимым `.skill`-артефактом и полной релизной документацией.

**Про нумерацию.** Версии 1.0 и 1.1 существовали как внутренние отметки в процессе разработки и ранней публикации. исторический GitHub Release v1.1.0 был создан автоматически без релизных заметок и без полного пакета метаданных. v2.0 — первая поддерживаемая публичная точка скачивания с описанным артефактом, changelog и release notes. Внутренние changelog-секции v1.0 и v1.1 сохранены ниже как история разработки.

**Что в релизе.**

Основной workflow:
- 9-шаговый pipeline: загрузка Camunda knowledge → классификация входа → выбор топологии → выбор декомпозиции → генерация BPMN 2.0 XML → валидация → показ пользователю с approval gate → Excel-выгрузка → reconciliation BPMN ↔ Excel
- Целевая платформа: Camunda 7 (Platform), все extension elements в namespace `camunda:*`
- Полная локализация: семантические метки BPMN (имена пулов, лэйнов, задач, событий, шлюзов, условий на стрелках) — на русском; продуктовые и бренд-названия из whitelist (Camunda, SBM, n11, Fibabanka и др.) сохраняются как есть; технические BPMN id остаются в латинице

Отказоустойчивость:
- Трёхступенчатый fallback при загрузке Camunda knowledge: Camunda MCP (preferred, live docs) → локальный snapshot `camunda-knowledge-snapshot.md` (~1170 строк, hybrid-выжимка Camunda 7 docs) → HALT только при повреждённой установке
- Degraded-mode warning в Step 7: при использовании snapshot — явное предупреждение пользователю с рекомендациями для prod-деплоя
- Дата обновления snapshot вынесена в H1-заголовок файла; инструкция по обновлению — в секции «Refresh snapshot procedure» README

Валидация и качество:
- 7 блокирующих проверок XML: well-formedness, BPMN schema conformance, structural integrity (10 подпунктов: sequence flows, start/end events, reachability, gateway fan-in/out, infinite loops, event references, boundary events, duplicate IDs, subprocess types, data objects), message flows и collaboration, Camunda 7 executability, DI completeness, language conformance
- 10 рекомендательных best practices (на основе Camunda bpmnlint и docs): technical ID naming, business-side event labels, business vs technical errors, happy path emphasis, sentence case, один executable process в collaboration, alignment имени файла с process ID, unused resources, empty process, circular call activity detection
- 9 проверок reconciliation Excel ↔ BPMN перед выдачей файла: node count parity, ID-level mapping, name parity, lane/pool parity, gateway decision rules, end event outcomes, annotation coverage, execution order sanity, UTF-8 integrity

Excel-спецификация:
- 9-колоночный лист «Спецификация»: №, Элемент BPMN, Название, Тип, Участник, Описание/Бизнес-правила, Входные данные, Выходные данные, Примечания/Compliance
- Лист «Участники»: пулы и лэйны с описанием ролей и количеством задач
- Лист «Открытые вопросы»: все аннотации «⚠ Уточнить» — сведённый чек-лист для следующей встречи с категорией и приоритетом
- Цветовая кодировка типов BPMN, скрытая колонка `_BPMN_ID` для сверки, freeze panes, wrap text
- Excel-выгрузка только после явного approval пользователем диаграммы

Покрытие отраслей (34 процесса в 8 reference-файлах):
- **fintech-patterns.md** — 17 процессов: KYC (retail) / KYB / Seller KYB / BaaS onboarding / Payment authorization / 3DS-SCA / P2P-cross-border / Chargeback / Refund / BNPL / Collection / Leasing / Factoring / Settlement-payout / Regulatory reporting / Seller lending / RBF (Merchant Cash Advance)
- **marketplace-patterns.md** — 5 процессов: Order-to-cash / Returns / Pick-Pack-Ship / Seller discovery / Cross-border marketplace
- **project-finance-patterns.md** — 4 процесса: Розничная ипотека / Кредитование застройщиков (214-ФЗ) / Проектное финансирование (SPV, IC) / Workout
- **healthcare-patterns.md** — 2 процесса: приём пациента, диспансеризация
- **manufacturing-patterns.md** — 1 процесс: производственный заказ
- **hr-patterns.md** — 2 процесса: онбординг, отпуск
- **public-sector-patterns.md** — 1 процесс: государственная услуга (210-ФЗ)
- **it-ops-patterns.md** — 2 процесса: incident management, change management

Compliance-рамка покрывает: РФ (115-ФЗ, 353-ФЗ, 161-ФЗ, 102-ФЗ, 214-ФЗ, 151-ФЗ, 230-ФЗ, 152-ФЗ, 54-ФЗ, 63-ФЗ, 210-ФЗ, ГК РФ, НК РФ, Положения ЦБ РФ 266-П, 383-П, 499-П, 590-П, 611-П, 4212-У), ЕАЭС (UZ ЗРУ-765, KZ ARDFM AEIR cap, BY), Турция (BDDK, Закон 6493, Закон 6502, Yönetmelik R.G. 31704), Эфиопия (NBE Directive ONPS/10/2025, Reg. 586/2026), США (HIPAA), ЕС (GDPR, PSD2, EHDS, Directive 2011/83/EU), международные стандарты (FATF 40 Recommendations, IFC Performance Standards, ISO 9001, IATF 16949, GMP, ITIL 4, PCI DSS).

Артефакт `bpmn-process-modeler.skill` собирается автоматически через GitHub Actions (`.github/workflows/build-skill.yml`) при push любого тега `v*` и публикуется в GitHub Release.

### v1.1 — апрель 2026

Отказоустойчивость при недоступности Camunda MCP + методология построения в snapshot.

- Добавлен `references/camunda-knowledge-snapshot.md` (~1170 строк) — hybrid-выжимка Camunda 7 документации: корневая XML-структура, все 8 типов задач, все события и шлюзы с примерами, subprocesses + multi-instance, collaboration, DI с размерами и координатами, textAnnotation, error / message / timer / compensation events, best practices, FEEL reserved words, whitelist токенов, **методология построения (раздел 18): happy path first, explicit modeling, симметрия, reading direction, декомпозиция, сводный список anti-patterns**
- Дата обновления snapshot вынесена в H1-заголовок файла (заметна сразу при открытии)
- Step 1 переработан: трёхступенчатый fallback — MCP (preferred) → snapshot → HALT (только при повреждённом архиве). Скилл больше не останавливается при недоступности MCP
- Hard rule №1 обновлён соответственно: одна из двух опций (MCP или snapshot) ОБЯЗАНА успеть до генерации XML
- Step 7 получил явный warning в degraded mode — перед approval prompt выводится сообщение про использование snapshot и рекомендации для prod-деплоя
- В README добавлены секции «Refresh snapshot procedure» (инструкция ручного обновления раз в 6 месяцев) и обновлённый troubleshooting по MCP

### v1.0 — апрель 2026
Первый публичный релиз.

- 9-шаговый workflow: Camunda MCP → классификация → топология → декомпозиция → XML → валидация → показ → Excel → reconciliation
- 7 блокирующих проверок XML + 10 рекомендательных best practices (на базе Camunda bpmnlint)
- 9-колоночная Excel-спецификация + лист «Участники» + лист «Открытые вопросы»
- Поддержка 24 отраслевых процессов в 8 reference-файлах (финтех, маркетплейс, проектное финансирование, и др.)
- Полная локализация: все семантические метки BPMN и все пользовательские ячейки Excel — на русском; whitelist для аббревиатур / брендов / ISO-форматов
- Camunda 7 Platform executability (`camunda:*` extensions, без `zeebe:*`)

## Благодарности

- **Camunda team** — за подробную документацию [docs.camunda.io](https://docs.camunda.io), особенно Best-practices раздел, который стал основой большинства правил скилла
- **bpmn-io team** — за open-source `bpmnlint` и `bpmn-js`, чьи правила валидации использованы в Check 3 и Check 6

## Лицензия

MIT License

Copyright (c) 2026 Andrey Zagreev

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
