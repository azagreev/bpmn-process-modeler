# Excel Specification Template — 9 колонок + 2 доп. листа

Шаблон таблицы, которую скилл выгружает на Step 8 после одобрения пользователем диаграммы.

---

## Лист 1: «Спецификация»

### Структура колонок

| # | Колонка | Что записываем |
|---|---|---|
| A | № | Порядковый номер в порядке обхода от start event. Для иерархии — сквозная нумерация: 1, 2, 3… для overview; 1.1, 1.2… для первого подпроцесса; 2.1, 2.2… для второго и т.д. |
| B | Элемент BPMN | Каноничное имя BPMN-элемента на английском: Start Event, End Event, Task, User Task, Service Task, Send Task, Receive Task, Business Rule Task, Script Task, Manual Task, Exclusive Gateway, Parallel Gateway, Inclusive Gateway, Event-based Gateway, Subprocess, Call Activity |
| C | Название элемента | Значение атрибута `name` из XML. На русском. |
| D | Тип элемента | BPMN-подтип на английском: Message Start Event, Timer Start Event, Terminate End Event, XOR Gateway, Timer Intermediate Catch Event, Error Boundary Event, и т.д. |
| E | Участник (Lane / Pool) | «Пул → Лэйн» или «Лэйн» если один пул. «—» если узел вне лэйнов. |
| F | Описание / Бизнес-правила | На русском. Описание из исходного текста + содержимое всех `textAnnotation`, прикреплённых к узлу. Для шлюзов — ОБЯЗАТЕЛЬНО: условия ветвления с отсылкой к продуктовому правилу. |
| G | Входные данные | На русском. Что приходит в узел: data objects, сообщения, артефакты. «—» если ничего. |
| H | Выходные данные / Результат | На русском. Что производит узел: data object, результат решения, терминальное состояние (для end events). |
| I | Примечания / Исключения / Compliance | На русском. Регуляторные ссылки, SLA, обработка ошибок, интеграционные детали, открытые вопросы («⚠ Уточнить: …»). |

### Форматирование

- **Заморозить первую строку** (freeze panes row 1)
- **Шапка**: bold, заливка светло-серая или синяя, wrap text, центрирование
- **Ширина колонок**: auto-fit с минимумом 15 символов, максимум 60
- **Wrap text** в колонках F, G, H, I
- **Цветовая кодировка колонки D** (Тип элемента) — заливка по категории:
  - События (Start/Intermediate/End Event, Boundary Event): зелёный `#E8F5E9`
  - Задачи (User/Service/Send/Receive/Business Rule/Script/Manual): синий `#E3F2FD`
  - Шлюзы (Exclusive/Parallel/Inclusive/Event-based): жёлто-оранжевый `#FFF3E0`
  - Подпроцессы (Subprocess, Call Activity): фиолетовый `#F3E5F5`
  - End Events (для акцента): красный `#FFEBEE`
- **Скрытая колонка J** с именем `_BPMN_ID` — хранит `id` из XML для сверки на Step 9. Скрываем (`sheet.column_dimensions['J'].hidden = True`), но не удаляем — колонка критична для reconciliation.

---

## Лист 2: «Участники»

Один ряд — один пул или лэйн. Цель — дать reviewer'у понимание, кто делает что и где границы ответственности.

| Колонка | Содержание |
|---|---|
| Тип | Pool / Lane |
| Имя | Название пула или лэйна на русском |
| Относится к пулу | Для лэйна — имя родительского пула. Для пула — «—» |
| Описание роли | На русском. Что делает этот участник в процессе, из каких задач состоит его зона ответственности |
| Количество задач | Сколько узлов принадлежит этому лэйну/пулу |

Сортировать: сначала пулы, потом лэйны внутри каждого пула.

---

## Лист 3: «Открытые вопросы»

Все аннотации с префиксом «⚠ Уточнить:» — отдельным списком, чтобы BA и PO могли пройтись по ним на следующей встрече.

| Колонка | Содержание |
|---|---|
| № строки в Спецификации | Номер ряда в листе «Спецификация», к которому относится вопрос. Для cross-reference. |
| Узел BPMN (название) | Русское название узла |
| Узел BPMN (ID) | Технический id из XML |
| Вопрос | Полный текст аннотации без префикса «⚠ Уточнить:» |
| Категория | Авто-классификация: SLA / Regulatory / Business rule / Integration / Data / Other — по ключевым словам в тексте |
| Приоритет | High / Medium / Low — High для блокеров запуска (отсутствует обработчик ошибки, нет SLA на критичный шаг), Medium для важных, но некритичных, Low для nice-to-have уточнений |
| Ответственный | Пусто (заполняется вручную на ревью) |
| Статус | «Открыт» по умолчанию |

---

## Sheet 4: Допущения (Assumptions)

### Purpose

Review checklist for the user: what the model assumed during Clarification Wizard or "with assumptions" mode. Each row = one explicitly accepted assumption, synchronized with `<bpmn:textAnnotation>` in BPMN-XML via ID.

### When the sheet is generated

| Scenario | Sheet generated? |
|---|---|
| Wizard NOT invoked (0 missing facts) | No |
| Wizard invoked, all questions answered | No |
| Wizard invoked, ≥1 answer was "skip" | Yes |
| "With assumptions" mode activated | Yes |
| Update scenario, Wizard refined only additions | Yes |

**Rule:** if final assumption count = 0 — sheet is NOT created (no empty sheets).

### Column structure

| # | Column | Type | Required | Example | Purpose |
|---|---|---|---|---|---|
| 1 | `ID допущения` | text | yes | `Assumption_3` | Maps to `<bpmn:textAnnotation>` in XML |
| 2 | `Целевой узел BPMN` | text | yes | `Activity_Manual_Review` | ID of node the assumption applies to |
| 3 | `Тип целевого узла` | enum | yes | `userTask` | task / userTask / serviceTask / gateway / event / pool / lane / process |
| 4 | `Категория` | enum | yes | `slas` | One of 6: topology / participants / happy_path / exception_paths / slas / data_ownership |
| 5 | `Текст допущения` | text | yes | "SLA на ручную проверку — 24 часа" | What was assumed |
| 6 | `Обоснование` | text | yes | "В исходнике срок не указан, принят default из category SLA" | Why this value |
| 7 | `Risk` | enum | yes | `medium` | low / medium / high (per Risk model below) |
| 8 | `Источник default'а` | text | **no (optional)** | `clarification-wizard.md §3.4` | Reference where default was taken |
| 9 | `Статус ревью` | enum | yes | `pending` | Always pre-fills to `pending`. User updates: pending / accepted / rejected / modified |

### Excel formatting

- Header row: bold, fill `#efeae0`
- `Risk = high` rows: cell fill `#fde2e2` (light red) on Risk column
- `Risk = medium` rows: cell fill `#fff3d6` (light gold) on Risk column
- `Risk = low` rows: no fill
- Columns 5 and 6: wrap text, width 40
- Column 9 (Статус ревью): data validation dropdown with 4 values
- Freeze pane: row 1

### BPMN reconciliation

ID mapping rule: Excel `Assumption_N` ↔ BPMN `TextAnnotation_Assumption_N`.

Example:

```xml
<bpmn:textAnnotation id="TextAnnotation_Assumption_3">
  <bpmn:text>⚠ Допущение: SLA на ручную проверку — 24 часа.
В исходнике срок не указан, принят по типичной практике.</bpmn:text>
</bpmn:textAnnotation>

<bpmn:association id="Association_Assumption_3"
  sourceRef="Activity_Manual_Review"
  targetRef="TextAnnotation_Assumption_3"/>
```

| Excel column | XML location |
|---|---|
| `ID допущения` | `textAnnotation/@id` (without `TextAnnotation_` prefix) |
| `Целевой узел BPMN` | `association/@sourceRef` |
| `Тип целевого узла` | derived from BPMN element with `id=sourceRef` |
| `Текст допущения` | line 1 of `textAnnotation/text/text()` (after `⚠ Допущение:` prefix) |
| `Обоснование` | line 2+ of `textAnnotation/text/text()` |
| `Категория`, `Risk`, `Источник default'а`, `Статус ревью` | Excel-only (not in BPMN) |

### Risk model

**Default Risk by category** + override conditions:

| Category | Default Risk | Override → high | Override → medium | Override → low |
|---|---|---|---|---|
| topology | high | external partner assumed | — | name-only assumption (no structural change) |
| participants | medium | external partner / regulator | — | — |
| happy_path | medium | entire step invented (not in source) | — | — |
| exception_paths | high | — | only missing escalation path | — |
| slas | medium | SLA <1h or >7d (atypical) | — | — |
| data_ownership | low | PII/KYC data | — | — |

**Risk meaning:** "how much BPMN to redo if this assumption is wrong" + "is there compliance/regulatory risk".

**Rule:** if 30%+ of assumptions are `Risk = high` — model must warn user in final message: "Высокая концентрация high-risk допущений. Рекомендую запустить Wizard повторно с расширенным вводом."

### Sheet template (5-row example)

| ID | Целевой узел | Тип | Категория | Текст допущения | Обоснование | Risk | Источник | Статус |
|---|---|---|---|---|---|---|---|---|
| Assumption_1 | Pool_BNPL_Operator | pool | participants | Operator — внутренний отдел операционного риска | В тексте упомянут "оператор", конкретный отдел не указан | medium | clarification-wizard.md §3.2 | pending |
| Assumption_2 | Activity_Document_Verify | userTask | participants | Документы проверяет junior credit officer | Не указан исполнитель, default из category participants | low | clarification-wizard.md §3.2 | pending |
| Assumption_3 | Activity_Manual_Review | userTask | slas | SLA на ручную проверку — 24 часа | Срок не указан, default из category SLA | medium | clarification-wizard.md §3.5 | pending |
| Assumption_4 | Gateway_Risk_Score | exclusiveGateway | exception_paths | При rejected → process end (без эскалации) | Не описан альтернативный путь, выбран наиболее частый сценарий | high | clarification-wizard.md §3.4 | pending |
| Assumption_5 | DataObject_Loan_Application | dataObject | data_ownership | Owner объекта — система LOS | Owner не указан, по контексту определена как LOS | low | clarification-wizard.md §3.6 | pending |

### Edge cases

**E1. Assumption about absence of element.** `Целевой узел` = main gateway where alternative path was expected. Text: "Альтернативный путь после Gateway_X не предусмотрен."

**E2. Process-level assumption (no specific node).** `Целевой узел` = `(process root)`, `Тип` = `process`. In BPMN: `<bpmn:textAnnotation>` without `<bpmn:association>` (or association on the root process element).

**E3. Cascading assumptions.** If one assumption produces another ("Operator = internal department" → "Operator has access to LOS"), record as 2 separate rows. Second row's `Обоснование` references first: "Следствие из Assumption_1."

**E4. Assumption rejected after generation.** User changes `Статус ревью` to `rejected`. Does NOT trigger automatic regeneration. Reconciliation report shows warning: "Assumption_3 rejected — требуется регенерация процесса с уточнённым SLA."

### Changes to other sheets when «Допущения» exists

**Sheet 1 (Спецификация):** add (optional) column "Связанные допущения" — list of Assumption_N IDs affecting this row. Format: `Assumption_1, Assumption_3`. Empty if none.

**Sheet 2 (Участники):** if a participant comes from a `participants`-category assumption, add row with `Источник` column = `Допущение: Assumption_N`.

**Sheet 3 (Открытые вопросы):** do NOT duplicate assumption content. Open questions = unresolved gaps in source. Assumptions = facts model accepted on user's behalf. Different entities.

### Reconciliation checks (extends `references/reconciliation-procedure.md`)

| # | Check | Violation | Severity |
|---|---|---|---|
| R-10 | Each row in «Допущения» has matching `<bpmn:textAnnotation>` in BPMN | Allegation without annotation | ERROR |
| R-11 | Each `<bpmn:textAnnotation>` with `⚠ Допущение:` prefix has Excel row | Annotation without record | ERROR |
| R-12 | `Целевой узел BPMN` exists in schema (id from `association.sourceRef` resolves) | Assumption points to nonexistent node | ERROR |
| R-13 | `Тип целевого узла` in Excel matches actual BPMN element type | Type mismatch | WARNING |

### Anti-hallucination rules

**Do NOT include in «Допущения»:**
- Facts explicitly stated in source
- Trivially derivable from context (task type from verb)
- Standard BPMN conventions
- Meta-information about model's working approach

**Do include:**
- Any SLA not in source but present in BPMN
- Any assumed executor/role
- Any alternative path not described
- Any assumed data owner
- Any topology assumption (single vs collaboration)

**Control question for the model:** "If user rejects this assumption now, what in BPMN must change?" If answer is "nothing" → don't add. If "≥1 element" → add.

---

## Mapping: BPMN element → row content

Таблица соответствий, чтобы заполнение колонок было одинаковым для одинаковых элементов.

| BPMN элемент | Колонка B (Элемент BPMN) | Колонка D (Тип элемента) | Что писать в F (Описание) |
|---|---|---|---|
| `<startEvent>` без event def | Start Event | None Start Event | «Процесс запускается вручную / инициатор: …» |
| `<startEvent><messageEventDefinition/>` | Start Event | Message Start Event | «Триггер: входящее сообщение … от …» |
| `<startEvent><timerEventDefinition/>` | Start Event | Timer Start Event | «Триггер: расписание / повторение …» |
| `<endEvent>` без event def | End Event | None End Event | Колонка H: терминальное состояние |
| `<endEvent><terminateEventDefinition/>` | End Event | Terminate End Event | Прерывает ВСЕ ветки процесса |
| `<endEvent><errorEventDefinition errorRef=.../>` | End Event | Error End Event | Код ошибки + сообщение |
| `<userTask>` | Task | User Task | Что делает человек + форма, если есть |
| `<serviceTask camunda:type="external">` | Task | Service Task (External) | Topic + интеграция |
| `<serviceTask camunda:delegateExpression=...>` | Task | Service Task (Internal) | Класс / bean / expression |
| `<sendTask>` | Task | Send Task | Что и кому отправляется |
| `<receiveTask>` | Task | Receive Task | От кого и что ожидается |
| `<businessRuleTask>` | Task | Business Rule Task | Имя DMN + версия |
| `<scriptTask>` | Task | Script Task | Язык + краткое описание логики |
| `<manualTask>` | Task | Manual Task | Что делается вне системы |
| `<exclusiveGateway>` | Gateway | XOR Gateway | Условие + все ветви с условиями |
| `<parallelGateway>` split | Gateway | Parallel Gateway (Split) | Какие параллельные ветки запускаются |
| `<parallelGateway>` join | Gateway | Parallel Gateway (Join) | Какие ветки ждём |
| `<inclusiveGateway>` | Gateway | Inclusive Gateway | Условия для каждой ветки |
| `<eventBasedGateway>` | Gateway | Event-based Gateway | Какие события ждём |
| `<subProcess triggeredByEvent="false">` | Subprocess | Embedded Subprocess | Роль подпроцесса в общем потоке + ссылка на Level 1 диаграмму |
| `<callActivity>` | Subprocess | Call Activity | Имя вызываемого процесса |
| `<intermediateCatchEvent><timerEventDefinition/>` | Event | Timer Intermediate Catch Event | ISO 8601 duration + что ждём |
| `<intermediateCatchEvent><messageEventDefinition/>` | Event | Message Intermediate Catch Event | Какое сообщение и от кого |
| `<boundaryEvent cancelActivity="true">` + timer | Event | Timer Boundary Event (Interrupting) | Таймаут + куда переход |
| `<boundaryEvent cancelActivity="false">` | Event | Non-interrupting Boundary Event | Таймаут + параллельная ветка |

---

## Worked example — BNPL approval

Допустим, на выходе Step 5 мы имеем процесс BNPL с 6 узлами. Лист «Спецификация» выглядит так:

| № | Элемент BPMN | Название элемента | Тип элемента | Участник | Описание / Бизнес-правила | Входные | Выходные / Результат | Примечания |
|---|---|---|---|---|---|---|---|---|
| 1 | Start Event | Поступление заявки на BNPL | Message Start Event | Клиент | Клиент подаёт заявку через мобильное приложение | Заявка (ID, сумма, срок) | Заявка создана | KYC check обязателен при первой сделке |
| 2 | Task | Проверка скоринга | Service Task (External) | Risk / Underwriting | Автоматический запрос в бюро + внутренняя модель | ID клиента, сумма | Скоринговый балл + решение bureau | Интеграция: Kafka topic scoring.request; SLA 2 сек; ⚠ Уточнить: fallback при недоступности бюро |
| 3 | Gateway | Решение по заявке | XOR Gateway | Risk / Underwriting | Балл ≥ 700 И просрочек 0 → одобрено; 600–699 → ручная проверка; иначе → отказ | Скоринговый балл | Выбор ветки | Логирование отказа по ФЗ-353 |
| 4 | Task | Списание первого платежа | Service Task (External) | Платёжный шлюз | Списание 25% от суммы заказа | ID клиента, сумма, карта | Платёж проведён / ошибка | Compensation: возврат средств; PSD2 SCA если сумма ≥ 30 EUR |
| 5 | End Event | Заявка одобрена | None End Event | Клиент | — | — | BNPL-контракт активирован, график платежей отправлен клиенту | — |
| 6 | End Event | Заявка отклонена | None End Event | Клиент | — | — | Отказ с кодом причины отправлен клиенту | Согласно ФЗ-353 — хранение решения 5 лет |

---

## Python-скелет генерации (openpyxl)

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Спецификация"

headers = ["№", "Элемент BPMN", "Название элемента", "Тип элемента",
           "Участник (Lane / Pool)", "Описание / Бизнес-правила",
           "Входные данные", "Выходные данные / Результат",
           "Примечания / Исключения / Compliance", "_BPMN_ID"]
ws.append(headers)

# Header formatting
header_fill = PatternFill("solid", fgColor="D0E4F5")
header_font = Font(bold=True)
for col in range(1, len(headers) + 1):
    c = ws.cell(row=1, column=col)
    c.fill = header_fill
    c.font = header_font
    c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")

# Freeze top row
ws.freeze_panes = "A2"

# Hide _BPMN_ID column
ws.column_dimensions[get_column_letter(len(headers))].hidden = True

# Populate rows from bpmn_nodes list
CATEGORY_FILL = {
    "Event": "E8F5E9", "Task": "E3F2FD",
    "Gateway": "FFF3E0", "Subprocess": "F3E5F5",
    "EndEvent": "FFEBEE",
}
for idx, node in enumerate(bpmn_nodes, start=1):
    row = [idx, node["bpmn_kind"], node["name"], node["subtype"],
           node["lane_pool"], node["description"], node["inputs"],
           node["outputs"], node["notes"], node["id"]]
    ws.append(row)
    fill_color = CATEGORY_FILL.get(node["category"])
    if fill_color:
        ws.cell(row=idx + 1, column=4).fill = PatternFill("solid", fgColor=fill_color)

# Auto-width + wrap text for description columns
WRAP_COLS = [6, 7, 8, 9]
for col in range(1, len(headers) + 1):
    max_len = max(len(str(ws.cell(row=r, column=col).value or ""))
                  for r in range(1, ws.max_row + 1))
    ws.column_dimensions[get_column_letter(col)].width = min(max(max_len + 2, 15), 60)
    if col in WRAP_COLS:
        for r in range(2, ws.max_row + 1):
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top")

# Sheets 2 and 3: participants and open questions (analogous structure)
wb.create_sheet("Участники")
wb.create_sheet("Открытые вопросы")

wb.save("/mnt/user-data/outputs/<process_name>_specification.xlsx")
```

`openpyxl` сохраняет в UTF-8 по умолчанию — специальные действия не нужны. Проверка кодировки на Step 9 всё равно обязательна.
