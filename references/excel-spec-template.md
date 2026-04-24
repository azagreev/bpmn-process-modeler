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
