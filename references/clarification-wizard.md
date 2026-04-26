# Clarification Wizard

## 1. Purpose

Clarification Wizard is Step 1.5 in Generate mode. It detects missing process
facts before BPMN generation and either asks targeted questions or proceeds with
explicit assumptions.

The Wizard is not a separate mode. It sits between Camunda knowledge loading and
Parse & classify. Its goal is to prevent silent invention while keeping the
generation flow fast for complete inputs.

## 2. Workflow (5 steps)

1. Read the user input and Step 0 classification result.
2. Scan the input for the 6 missing-facts categories from Section 3.
3. Count missing categories and route by Section 4.
4. Ask targeted questions or activate "with assumptions" mode.
5. Pass answered facts and accepted assumptions to Step 2.

Output of the Wizard:
- `missing_categories`: ordered list by priority
- `answered_facts`: facts supplied by the user
- `accepted_assumptions`: defaults accepted by skip or assumption mode
- `wizard_invoked`: true when questions were asked
- `assumption_mode`: true when questions were skipped by explicit command

## 3. Missing-facts categories (6)

Priority order is fixed: topology, participants, happy_path, exception_paths,
slas, data_ownership.

### Category 1: topology (priority: high)

**Trigger words for detection:**
- отдел
- команда
- партнёр
- организация
- филиал
- collaboration
- message
- pool
- lane

**Detection heuristic:**
Category is "missing" if the text does not reveal whether the process has one
organization, several internal roles, or multiple organizations exchanging
messages.

Category is "present" if pools, lanes, organizations, departments, or message
exchange boundaries are explicitly described.

**Default assumption (if user skips):**
Single pool, no collaboration.

**Question template:**
"Какая топология процесса нужна? Выбери вариант или впиши свой:"
- Option A: Один пул без лэйнов
- Option B: Один пул с лэйнами по ролям
- Option C: Несколько пулов с message flows
- Free-form: "Другое: ___"

### Category 2: participants (priority: high)

**Trigger words for detection:**
- менеджер
- оператор
- система
- должность
- role
- исполнитель
- клиент
- банк
- регулятор

**Detection heuristic:**
Category is "missing" if the process describes actions but does not name who or
what performs them.

Category is "present" if each major action has an actor, role, department,
system, customer, partner, or regulator.

**Default assumption (if user skips):**
Use placeholder participant "Внутренний исполнитель".

**Question template:**
"Кто выполняет основные действия? Выбери вариант или впиши свой:"
- Option A: Внутренний исполнитель
- Option B: Клиент + внутренний исполнитель
- Option C: Внутренний отдел + внешняя система
- Free-form: "Другое: ___"

### Category 3: happy_path (priority: high)

**Trigger words for detection:**
- сначала
- затем
- после
- готово
- отправлено
- утверждено
- завершено
- подписано
- одобрено

**Detection heuristic:**
Category is "missing" if the text names a process goal but does not describe the
main successful sequence from start to end.

Category is "present" if the input gives an ordered sequence of successful
states, tasks, or handoffs.

**Default assumption (if user skips):**
Linear sequence, single end event.

**Question template:**
"Как выглядит основной успешный путь? Выбери вариант или впиши свой:"
- Option A: Линейный путь без ветвлений
- Option B: Проверка → решение → успешное завершение
- Option C: Параллельная подготовка нескольких материалов → объединение
- Free-form: "Другое: ___"

### Category 4: exception_paths (priority: medium)

**Trigger words for detection:**
- если не
- при ошибке
- отказ
- таймаут
- исключение
- эскалация
- отмена
- просрочка
- недоступен

**Detection heuristic:**
Category is "missing" if the text has only the happy path and does not say what
happens on rejection, timeout, validation failure, or unavailable system.

Category is "present" if at least one rejection, timeout, cancellation,
escalation, or error path is described.

**Default assumption (if user skips):**
No alternative path; process ends on error or rejection.

**Question template:**
"Какие исключения нужно показать? Выбери вариант или впиши свой:"
- Option A: Только отказ с завершением процесса
- Option B: Отказ + ручная эскалация
- Option C: Таймаут + повторная попытка
- Free-form: "Другое: ___"

### Category 5: slas (priority: medium)

**Trigger words for detection:**
- срок
- дедлайн
- в течение
- рабочих дней
- часов
- вовремя
- SLA
- таймер
- просрочка

**Detection heuristic:**
Category is "missing" if the process contains manual or waiting steps but no
explicit time limits, deadlines, or timeout behavior.

Category is "present" if the source gives deadlines, durations, timeout rules,
business-day limits, or explicit "no SLA" wording.

**Default assumption (if user skips):**
Use "По регламенту" with no specific timer.

**Question template:**
"Какие сроки важны для процесса? Выбери вариант или впиши свой:"
- Option A: По регламенту, без конкретного таймера в BPMN
- Option B: 24 часа на ручную проверку
- Option C: 3 рабочих дня на полный цикл
- Free-form: "Другое: ___"

### Category 6: data_ownership (priority: low)

**Trigger words for detection:**
- документ
- файл
- информация
- хранится
- передаётся
- owner
- владелец
- источник
- система

**Detection heuristic:**
Category is "missing" if documents or data objects are mentioned but no source
system, owner, or storage point is specified.

Category is "present" if documents, files, records, or process variables have a
named owner, source system, or storage location.

**Default assumption (if user skips):**
Source system not specified.

**Question template:**
"Где живут ключевые данные процесса? Выбери вариант или впиши свой:"
- Option A: Source system not specified
- Option B: CRM / LOS является источником данных
- Option C: Документы хранятся в СЭД
- Free-form: "Другое: ___"

## 4. Routing by missing count (4 scenarios)

### Algorithm

1. After Step 1 (Camunda knowledge load), scan input for all 6 categories.
2. Count categories that are "missing" per Section 3 heuristics.
3. Sort missing categories by priority.
4. Route by count:

| Missing count | Action |
|---|---|
| 0 | Skip Wizard, inform user "Всё понятно, перехожу к генерации", proceed to Step 2 |
| 1-2 | Ask all missing as questions |
| 3-5 | Ask top-N missing in priority order |
| 6+ | Offer choice: provide more details OR continue "with assumptions" |

### Question composition rule

- 1 question = 1 category.
- Never group categories in one question.
- Each question ends with: "Выбери вариант или впиши свой:"
- Each question has 2-4 pre-built options and one "Другое: ___" slot.

### Hard limits

- Maximum 5 questions per Wizard pass, with no exceptions.
- Rationale: the skill must not turn generation into a long interview.
- If 6+ categories are missing, ask no more than top-5 by priority.
- Missing facts below the cutoff become `⚠ Допущение:` after generation if the
  user accepts assumption mode.

### 4.1 Zero missing -> skip

Transcript:
- User: "Смоделируй процесс: клиент подаёт заявку, менеджер проверяет документы
  за 24 часа, при отказе заявка закрывается, данные хранятся в CRM."
- Wizard: "Всё понятно, перехожу к генерации."

### 4.2 1-2 missing -> targeted questions

Transcript:
- User: "Клиент подаёт заявку. Менеджер проверяет документы и отправляет договор."
- Wizard: "Какие сроки важны для процесса? Выбери вариант или впиши свой:"
- User: "24 часа на проверку."

### 4.3 3-5 missing -> priority-ordered questions

Transcript:
- User: "Смоделируй одобрение заявки: проверка, решение, подпись."
- Wizard asks, in order: topology, participants, exception_paths, slas,
  data_ownership.
- User answers only topology and participants; skipped facts use defaults.

### 4.4 6+ missing -> offer "with assumptions" mode

Transcript:
- User: "Смоделируй процесс продаж."
- Wizard: "Недостаточно данных по 6 категориям. Можешь добавить описание или
  продолжить с допущениями."
- User: "Делай с допущениями."
- Wizard proceeds without questions and marks accepted defaults as
  `⚠ Допущение:`.

## 5. "With assumptions" mode

### 5.1 Trigger phrases

The user explicitly opts into assumption mode by saying any of:
- `делай с допущениями`
- `генерируй с предположениями`
- `не задавай вопросов`
- `генерируй без вопросов`
- `as is`
- `as-is`
- `just do it`

When activated:
- Wizard does not ask questions
- Each missing fact becomes a `⚠ Допущение:` annotation in BPMN
- Each assumption is eligible for the Excel sheet «Допущения»

### 5.2 Annotation generation rules

For each missing fact:
1. Determine the target BPMN node where the assumption applies.
2. Create `<bpmn:textAnnotation>` with id `TextAnnotation_Assumption_<N>`.
3. Use two-line text: assumption first, justification second.
4. Create `<bpmn:association>` from target node to annotation.
5. Add an Excel row in sheet «Допущения» when Excel export is approved.

### 5.3 Edge case: 0 missing facts + assumption mode active

If assumption mode is active but no missing facts are detected, create no
annotations. Inform the user: "В тексте нет пробелов, допущения не требуются."

### 5.4 Mixing user-answered + skipped + assumed

One Wizard session may contain:
- answered questions, which create no `⚠ Допущение:`
- skipped questions, which use category defaults and create assumptions
- low-priority missing facts below the question cutoff, which become assumptions

## 6. Discipline rules

- Maximum 5 questions per pass.
- Do not ask about facts already present in the text.
- Do not mark as `⚠ Допущение:` what is trivially derivable.
- Do not group several missing categories into one question.
- Always respect priority order.
- Use category defaults only after skip, cutoff, or explicit assumption mode.
- In mixed input, ask only about new or changed parts.

## 7. Annotation template

```xml
<bpmn:textAnnotation id="TextAnnotation_Assumption_1">
  <bpmn:text>⚠ Допущение: SLA на ручную проверку — 24 часа.
В исходнике срок не указан, принят default из category slas.</bpmn:text>
</bpmn:textAnnotation>

<bpmn:association id="Association_Assumption_1"
  sourceRef="Activity_Manual_Review"
  targetRef="TextAnnotation_Assumption_1"/>
```

## 8. Full session example

### Input

```text
Смоделируй процесс одобрения BNPL-заявки. Клиент подаёт заявку в приложении.
Менеджер проверяет документы и принимает решение. При одобрении договор
отправляется клиенту на подпись.
```

### Detection

Detected facts:
- participants: клиент, менеджер
- happy_path: заявка -> проверка документов -> решение -> подпись

Missing categories:
- topology
- exception_paths
- slas
- data_ownership

### Wizard questions

1. Какая топология процесса нужна?
2. Какие исключения нужно показать?
3. Какие сроки важны для процесса?
4. Где живут ключевые данные процесса?

### User answers

```text
Один пул с лэйнами. Исключение — отказ. Сроки и owner данных не знаю.
```

### Result

Answered facts:
- topology = one pool with lanes
- exception_paths = rejection path

Accepted assumptions:
- slas = "По регламенту"
- data_ownership = "Source system not specified"

Generated BPMN includes two `⚠ Допущение:` annotations linked to the relevant
task or data object. If Excel export is approved, sheet «Допущения» contains one
row per accepted assumption.
