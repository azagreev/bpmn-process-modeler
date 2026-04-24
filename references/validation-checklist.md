# Validation Checklist — 7 блокирующих проверок BPMN XML + опциональные best practices

Каждая проверка — с описанием, примером ошибки и способом починки. Все 7 блокирующих обязаны пройти PASS до показа пользователю в Step 7. Опциональные best practices формируют WARN — не блокируют показ, но выводятся отдельно в итоговом отчёте.

Источники: Camunda Best-practices (Modeling, Dealing with problems and exceptions, Naming technically relevant IDs), Camunda Modeling Guidance rules (реализованы через библиотеку bpmnlint: called-element, element-type, error-reference, escalation-reference, feel, message-reference, no-loop), Camunda 7 Platform documentation.

---

## 1. Well-formedness

**Что проверяем:** XML парсится стандартным парсером без ошибок.

**Как проверить (Python):**
```python
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('process.bpmn')
    print('PASS: well-formed')
except ET.ParseError as e:
    print(f'FAIL: {e}')
```

**Типовые ошибки:**
- Отсутствие XML declaration в первой строке. Обязательно: `<?xml version="1.0" encoding="UTF-8"?>` — без этого ряд инструментов (в том числе Camunda Modeler некоторых версий) откажется открывать файл.
- Незакрытые теги, несбалансированные кавычки в атрибутах.
- Неэкранированные `<`, `>`, `&`, `"`, `'` в атрибутах (в названиях узлов на русском это редко, но в условиях шлюзов вроде `${amount > 1000}` и в FEEL-выражениях `= totalPrice > 100` — часто). Экранировать как `&lt;`, `&gt;`, `&amp;`, `&quot;`, `&apos;`.
- Отсутствие namespace-декларации при использовании префикса (`bpmndi:BPMNDiagram` без объявления `xmlns:bpmndi`).
- Для сложных FEEL-выражений со множеством спецсимволов можно использовать CDATA: `<bpmn:conditionExpression><![CDATA[= totalPrice > 100 and customer.type = "premium"]]></bpmn:conditionExpression>`. В этом случае экранирование не требуется.

**Починка:** запустить форматтер (например `xmllint --format`), прочитать ошибку парсера, починить указанную строку.

---

## 2. BPMN schema conformance

**Что проверяем:** каждый тег валиден по BPMN 2.0 XSD. Нет придуманных элементов. `targetNamespace` задан на `<bpmn:definitions>`. Все используемые префиксы объявлены.

**Как проверить:** прогнать через xmllint против XSD:
```bash
xmllint --noout --schema https://www.omg.org/spec/BPMN/20100524/DI.xsd process.bpmn
```

Для Camunda 7 extension elements — дополнительный namespace: `xmlns:camunda="http://camunda.org/schema/1.0/bpmn"`.

**Типовые ошибки:**
- `<bpmn:task name="...">` без `xsi:type` — допустимо только для generic Task. Конкретизируй: `<bpmn:userTask>`, `<bpmn:serviceTask>`.
- Придуманные атрибуты: `<bpmn:userTask priority="high">` — `priority` не в BPMN 2.0. Использовать `camunda:priority` (с объявленным namespace) или вынести в `<textAnnotation>`.
- `<bpmn:exclusiveGateway>` с `default` на несуществующий flow.
- Camunda-атрибуты без namespace: `<serviceTask type="external">` вместо `<bpmn:serviceTask camunda:type="external">`.
- **Смешивание C7 и C8 namespaces в одном файле.** Цель скилла — только Camunda 7. Использовать `camunda:*` атрибуты. Обнаружение `zeebe:*` — критичная ошибка.
- Отсутствие `targetNamespace` на `<bpmn:definitions>` — по XSD обязателен. Допускается `targetNamespace="http://bpmn.io/schema/bpmn"` (дефолт Camunda Modeler) или любой URI.

**Починка:** при сомнениях в элементе — вызвать `search_camunda_knowledge_sources` с конкретным вопросом.

---

## 3. Structural integrity

**Что проверяем:** граф процесса корректен. 10 подпунктов:

### 3a. Все sequenceFlow ссылаются на существующие узлы

```python
flow_nodes = {elem.get('id') for elem in root.iter() if elem.tag.endswith(('Task', 'Event', 'Gateway', 'subProcess'))}
for flow in root.iter('{*}sequenceFlow'):
    src, tgt = flow.get('sourceRef'), flow.get('targetRef')
    assert src in flow_nodes, f'Dangling sourceRef: {src}'
    assert tgt in flow_nodes, f'Dangling targetRef: {tgt}'
```

### 3b. Минимум 1 start и 1 end event в каждом процессе

```python
for process in root.iter('{*}process'):
    starts = list(process.iter('{*}startEvent'))
    ends = list(process.iter('{*}endEvent'))
    assert len(starts) >= 1, f'Process {process.get("id")} has no startEvent'
    assert len(ends) >= 1, f'Process {process.get("id")} has no endEvent'
```

### 3c. Все пути из start достигают end

BFS от каждого startEvent по исходящим `sequenceFlow`. Если узел не достигается ни от одного старта — orphan. Если из узла нет outgoing и он не endEvent — dead-end.

### 3d. Fan-in/fan-out шлюзов соответствует типу

| Тип шлюза | Разрешённые outgoing | Разрешённые incoming |
|---|---|---|
| exclusiveGateway (XOR) | 1 или N (splitting) | 1 или N (merging) |
| parallelGateway (AND) split | N | 1 |
| parallelGateway (AND) join | 1 | N |
| inclusiveGateway (OR) | N (с условиями) | N |
| eventBasedGateway | N (только intermediate catch events как target) | 1 |

**Типовые ошибки:**
- XOR с 1 outgoing — бессмысленный, удалить или заменить sequenceFlow напрямую
- AND split с 1 outgoing и 1 incoming — аналогично
- eventBasedGateway, из которого идёт userTask — нарушение спецификации

### 3e. Infinite loop detection (по bpmnlint `no-loop` rule)

Camunda Engine отказывается деплоить процессы со straight-through processing loops — автоматическими циклами без human interaction, timer, или external event. Без перерыва цикл может вызвать endless execution и exhaust cluster resources.

Обнаружение: DFS по графу sequence flows, поиск циклов, проверка что в каждом цикле есть хотя бы один «разрыватель»: `userTask`, `manualTask`, `receiveTask`, intermediate catch event (timer / message / signal).

```python
def detect_uncontrolled_loops(root):
    # Построить граф
    graph = {}  # node_id -> set of successor node_ids
    for flow in root.iter('{*}sequenceFlow'):
        graph.setdefault(flow.get('sourceRef'), set()).add(flow.get('targetRef'))

    # Собрать breaker nodes (те, которые разрешают цикл)
    BREAKER_TAGS = {'userTask', 'manualTask', 'receiveTask',
                    'intermediateCatchEvent'}
    breakers = set()
    for tag in BREAKER_TAGS:
        for n in root.iter(f'{{*}}{tag}'):
            breakers.add(n.get('id'))

    # DFS + cycle detection (Tarjan-like)
    def find_cycles(start, visited, path):
        if start in path:
            cycle = path[path.index(start):]
            if not any(n in breakers for n in cycle):
                return [cycle]  # uncontrolled loop
            return []
        if start in visited:
            return []
        visited.add(start)
        results = []
        for nxt in graph.get(start, []):
            results += find_cycles(nxt, visited, path + [start])
        return results

    # Запустить от start events
    uncontrolled = []
    for start in root.iter('{*}startEvent'):
        uncontrolled += find_cycles(start.get('id'), set(), [])
    return uncontrolled
```

**Починка:** добавить в цикл userTask (ручная проверка), timer event (пауза перед retry), или message receive event (ожидание внешнего триггера).

### 3f. Event reference integrity

Все catch/throw events с ссылками должны указывать на определённые ресурсы. Правило из bpmnlint: `error-reference`, `message-reference`, `escalation-reference`.

- Каждый error event с `errorRef` → ссылка на существующий `<bpmn:error>` с атрибутом `errorCode`
- Каждый message event с `messageRef` → ссылка на существующий `<bpmn:message>` с атрибутом `name`
- Каждый escalation event с `escalationRef` → ссылка на существующий `<bpmn:escalation>` с атрибутом `escalationCode`
- Каждый signal event с `signalRef` → ссылка на существующий `<bpmn:signal>` с атрибутом `name`

**Типовая ошибка:**
```xml
<bpmn:endEvent id="Event_Fail">
  <bpmn:errorEventDefinition errorRef="Error_Rejected"/>
</bpmn:endEvent>
<!-- но <bpmn:error id="Error_Rejected" .../> не определён на уровне definitions -->
```

Runtime ошибка: "Error with id 'Error_Rejected' not found".

**Совет по signal name:** два `<bpmn:signal>` с одинаковым `name` но разными `id` — источник трудноотлавливаемых багов message correlation. Ловим дубликаты `name`.

### 3g. Boundary event correctness

- `attachedToRef` обязателен и должен указывать на существующий `<task>`, `<subProcess>` или `<callActivity>`
- Error boundary event ДОЛЖЕН быть interrupting (`cancelActivity="true"` — дефолт). Non-interrupting error event — нарушение BPMN spec
- Timer boundary event и message boundary event могут быть interrupting или non-interrupting (`cancelActivity="false"`)
- Boundary event нельзя прикрепить к шлюзу или событию — только к activity

### 3h. Duplicate ID check

BPMN 2.0 XSD требует уникальность id через `xsd:ID`. Стандартный xml.etree парсер **не ловит дубликаты** — проверять явно.

```python
from collections import Counter
all_ids = [elem.get('id') for elem in root.iter() if elem.get('id')]
duplicates = [i for i, count in Counter(all_ids).items() if count > 1]
if duplicates:
    print(f'FAIL: Duplicate IDs: {duplicates}')
```

Camunda Engine при деплое возвращает `DUPLICATE_ID` error. Чинится переименованием.

### 3i. Subprocess type consistency

Embedded subprocess и event subprocess — разные режимы работы `<subProcess>`.

- **Embedded subprocess** (без `triggeredByEvent` или с `triggeredByEvent="false"`):
  - StartEvent ДОЛЖЕН быть типа None (без event definition внутри)
  - Если поставить `messageEventDefinition` / `timerEventDefinition` / `signalEventDefinition` — deploy fail
- **Event subprocess** (`triggeredByEvent="true"`):
  - StartEvent ОБЯЗАН иметь event definition (message / timer / signal / error / escalation / compensation / conditional)
  - Атрибут `isInterrupting` на startEvent: true (дефолт) или false
  - Event subprocess может быть вложен в другой subprocess или процесс на верхнем уровне

**Типовая ошибка:** embedded subprocess с message start event — модель визуально выглядит корректно в Modeler, но deploy fail с сообщением о невалидной start event.

### 3j. Data objects и references

Если в модели используются data objects:
- `<dataObject>` и `<dataObjectReference>` должны иметь уникальные id
- `<dataObjectReference>` с `dataObjectRef` → существующий `<dataObject>` в том же scope (process или subprocess)
- `<dataStoreReference>` с `dataStoreRef` → существующий `<dataStore>` (обычно на уровне definitions)
- `<association>` между узлами и data references — корректные `sourceRef` / `targetRef`

Data objects не обязательны, но если есть — должны быть связаны корректно, иначе на диаграмме окажутся висящие элементы.

---

## 4. Message flows и Collaboration structure

**Что проверяем:** если есть collaboration с пулами, все `messageFlow` идут МЕЖДУ разными пулами. Связи participant → process корректные. Lane membership соблюдён.

### 4a. Message flow направление

```python
participant_by_process = {p.get('processRef'): p.get('id') for p in root.iter('{*}participant')}

def pool_of(node_id):
    for process in root.iter('{*}process'):
        for elem in process.iter():
            if elem.get('id') == node_id:
                return participant_by_process.get(process.get('id'))

for mf in root.iter('{*}messageFlow'):
    src_pool = pool_of(mf.get('sourceRef'))
    tgt_pool = pool_of(mf.get('targetRef'))
    assert src_pool != tgt_pool, f'messageFlow {mf.get("id")} внутри одного пула — это sequenceFlow'
```

**Типовые ошибки:**
- Художник перепутал `sequenceFlow` и `messageFlow` — внутри пула надо первый, между пулами — второй.
- Message flow идёт в pool (participant) вместо конкретного receive task / message start event. Допустимо в BPMN 2.0, но непонятно какой узел получит сообщение — предупреждение.

### 4b. Participant ↔ Process linking

- Каждый `<participant>` в `<collaboration>`:
  - Либо имеет `processRef` на существующий `<process>` (обычный executable pool)
  - Либо без `processRef` (black box pool — внешняя система, у нас нет visibility в процесс)
- Black box pool не должен содержать flow nodes в XML (он только граница коммуникации)
- Не должно быть двух `<participant>` с одинаковым `processRef` — один процесс = один пул

### 4c. Lane membership

- Внутри `<laneSet>` каждый `<lane>` с `<flowNodeRef>` должен ссылаться на узлы того же `<process>`
- Один flow node — в одном lane (пересечений не бывает)
- `<laneSet>` может быть только один на `<process>` (по BPMN spec)

```python
for process in root.iter('{*}process'):
    process_node_ids = {n.get('id') for n in process.iter() if n.get('id')}
    for lane_set in process.iter('{*}laneSet'):
        for lane in lane_set.iter('{*}lane'):
            for ref in lane.iter('{*}flowNodeRef'):
                if ref.text not in process_node_ids:
                    print(f'FAIL: Lane {lane.get("id")} references node {ref.text} not in process {process.get("id")}')
```

---

## 5. Camunda 7 executability

**Что проверяем:** если `isExecutable="true"`, все задачи корректно сконфигурированы для runtime.

Целевая платформа — Camunda 7 (Platform). Обязательные атрибуты по типу задачи:

| Тип задачи | Обязательный атрибут |
|---|---|
| userTask | `camunda:assignee` ИЛИ `camunda:candidateUsers` ИЛИ `camunda:candidateGroups` |
| serviceTask (external) | `camunda:type="external"` + `camunda:topic` |
| serviceTask (internal) | `camunda:delegateExpression` ИЛИ `camunda:class` ИЛИ `camunda:expression` |
| businessRuleTask | `camunda:decisionRef` + `camunda:resultVariable` |
| scriptTask | `scriptFormat` + inline `<script>` ИЛИ `camunda:resource` |
| callActivity | `camunda:calledElement` |

### 5a. Timer events — формат ISO 8601 или cron

Timer events обязаны иметь корректный `<timeDuration>`, `<timeDate>` или `<timeCycle>`:

- ISO 8601 duration: `PT15M` (15 минут), `PT2H` (2 часа), `P3D` (3 дня), `P1W` (неделя), `P1Y` (год)
- ISO 8601 дата: `2026-12-31T23:59:00`
- Cron: `0 0 9 ? * MON-FRI` (по будням в 9:00)

**Типовая ошибка:** `<timeDuration>15 minutes</timeDuration>` — не ISO 8601, runtime fail. Должно быть `PT15M`.

### 5b. Error throw events

`errorEventDefinition` в end event или intermediate throw event:
- Ссылается на `<bpmn:error errorRef="..."/>` (см. 3f)
- Соответствующий `<bpmn:error>` имеет `errorCode` — без него catch event не сможет его поймать

### 5c. FEEL reserved words в variables

Нельзя использовать как имена переменных (из Camunda docs, Expression timeout rules):
`true`, `false`, `null`, `function`, `if`, `then`, `else`, `for`, `between`, `instance`, `of`.

Проверка: в expressions `${variable_name}` и FEEL `= variable_name`, переменные из output mappings — не должны совпадать с reserved words.

### 5d. Multi-instance loop characteristics

Если есть `<multiInstanceLoopCharacteristics>`:

- Атрибут `isSequential` задан явно (`true` — sequential execution, `false` — parallel). Дефолт false, но полагаться на дефолт плохая практика.
- Для Camunda 7: `camunda:collection` (expression на process variable, содержащую коллекцию) ОБЯЗАТЕЛЬНА, либо задан `loopCardinality` (фиксированное число итераций)
- `camunda:elementVariable` опционально (имя локальной переменной для current element)
- Если есть `outputCollection` — должна быть `outputElement` (expression, извлекающий результат из instance)
- `completionCondition` опционально (для «первый закончил — все закончились»)

```xml
<!-- Пример для референса -->
<bpmn:serviceTask id="Task_ProcessInvoice" name="Обработать инвойс">
  <bpmn:multiInstanceLoopCharacteristics isSequential="false"
      camunda:collection="${invoices}"
      camunda:elementVariable="invoice"/>
</bpmn:serviceTask>
```

### 5e. Conditional events

Если используются `<conditionalEventDefinition>` (редко, но встречается):
- Обязателен дочерний `<condition>` с FEEL/JUEL-выражением
- Выражение непустое, не reserved word
- Для Camunda 7: язык expressions обычно JUEL `${amount > 1000}`

### 5f. Прочие best practices

- `isExecutable="true"` на `<process>` — обязательно для деплоя. Без него в Modeler откроется, но не деплоится.
- `exporter="..."` и `exporterVersion="..."` на `<definitions>` — опциональны, но помогают при диагностике (Camunda Modeler заполняет автоматически).

**Типовые ошибки:**
- Забыли `isExecutable="true"` — не деплоится.
- userTask без assignee/candidateGroups — process instance повиснет навсегда, никто не получит задачу.
- Service task без `camunda:type="external"` и без `camunda:delegateExpression` — движок не знает, что исполнять.
- callActivity без `camunda:calledElement` — runtime `Cannot resolve called element`.
- Multi-instance без коллекции или loopCardinality — активность не создаёт инстансы, виснет.

---

## 6. DI completeness

**Что проверяем:** каждый элемент, который должен отображаться, имеет фигуру или ребро в `<bpmndi:BPMNDiagram>` с корректными координатами и атрибутами.

```python
shape_refs = {s.get('bpmnElement') for s in root.iter('{*}BPMNShape')}
edge_refs = {e.get('bpmnElement') for e in root.iter('{*}BPMNEdge')}

# Flow nodes must have BPMNShape
for tag in ('startEvent', 'endEvent', 'intermediateCatchEvent', 'intermediateThrowEvent',
            'task', 'userTask', 'serviceTask', 'manualTask', 'sendTask', 'receiveTask',
            'businessRuleTask', 'scriptTask', 'subProcess', 'callActivity',
            'exclusiveGateway', 'parallelGateway', 'inclusiveGateway', 'eventBasedGateway',
            'textAnnotation', 'participant', 'lane', 'dataObjectReference', 'dataStoreReference'):
    for node in root.iter(f'{{*}}{tag}'):
        node_id = node.get('id')
        if node_id and node_id not in shape_refs:
            print(f'FAIL: {tag} {node_id} has no BPMNShape')

# Flows must have BPMNEdge
for tag in ('sequenceFlow', 'messageFlow', 'association'):
    for flow in root.iter(f'{{*}}{tag}'):
        flow_id = flow.get('id')
        if flow_id and flow_id not in edge_refs:
            print(f'FAIL: {tag} {flow_id} has no BPMNEdge')
```

**Типовые ошибки:**
- Сгенерировали XML без DI — открывается как пустой холст в Camunda Modeler
- Добавили `<textAnnotation>`, но забыли `BPMNShape` для неё — текст не виден
- Забыли координаты на `<bpmndi:BPMNLabel>` у шлюза — подпись условия на стрелке пропала

### 6a. Стандартные размеры shapes (Camunda Modeler defaults)

| Тип элемента | Width × Height |
|---|---|
| Event (start / end / intermediate / boundary) | 36 × 36 |
| Task (все подтипы) | 100 × 80 |
| Gateway (все подтипы) | 50 × 50 |
| Subprocess (expanded) | 350 × 200 (минимум) |
| Subprocess (collapsed) | 100 × 80 |
| Call Activity | 100 × 80 |
| Pool | width = до 1500+, height = по сумме lanes |
| Lane | width = pool_width − 30 (отступ на header пула), height = 180 типично |
| Text Annotation | 100 × 30 (типично, допускается варьировать) |
| Data Object / Data Store Reference | 36 × 50 |

Несоответствие размеров — не fail, но сильно ломает визуал в Modeler. При auto-layout корректируется, но лучше сразу правильно.

### 6b. Pool / Lane: `isHorizontal="true"`

На BPMNShape для pool и lane — обязательный атрибут:
```xml
<bpmndi:BPMNShape id="Participant_di" bpmnElement="Participant_Bank" isHorizontal="true">
```

Без `isHorizontal="true"` Modeler по дефолту рендерит вертикально — layout ломается для типовых финтех-диаграмм (которые читаются слева направо).

### 6c. Exclusive Gateway: `isMarkerVisible="true"`

На BPMNShape для XOR gateway — обязательный атрибут:
```xml
<bpmndi:BPMNShape id="Gateway_Approval_di" bpmnElement="Gateway_Approval" isMarkerVisible="true">
```

Без него XOR рисуется как пустой ромб — визуально неотличим от inclusive OR. `isMarkerVisible="true"` включает знак «×» внутри ромба.

Для parallel и inclusive — маркер рисуется автоматически, атрибут не требуется.

### 6d. BPMNEdge waypoints — минимум 2

Каждый `<bpmndi:BPMNEdge>` должен содержать минимум 2 `<di:waypoint>` (начало и конец). Для изогнутых стрелок (L-форма, S-форма, loop-back) — 3+ waypoints.

```xml
<!-- Прямая стрелка: 2 waypoints -->
<bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
  <di:waypoint x="215" y="117" />
  <di:waypoint x="270" y="117" />
</bpmndi:BPMNEdge>

<!-- L-образная стрелка с возвратом: 4 waypoints -->
<bpmndi:BPMNEdge id="Flow_Loopback_di" bpmnElement="Flow_Loopback">
  <di:waypoint x="680" y="195" />
  <di:waypoint x="680" y="140" />
  <di:waypoint x="330" y="140" />
  <di:waypoint x="330" y="180" />
</bpmndi:BPMNEdge>
```

Edge с 0 или 1 waypoint — невалидный, Modeler не рендерит.

### 6e. BPMNLabel позиционирование

BPMNLabel — дочерний опциональный элемент BPMNShape и BPMNEdge. Определяет где рисовать подпись (`name` атрибут). Без него позиция вычисляется автоматически, часто перекрывает узлы.

Типовые координаты (относительно shape):
- Для events (36×36): label ниже shape, `x = shape_x - 24, y = shape_y + 42, width ≈ 84, height ≈ 27`
- Для tasks: обычно `<bpmndi:BPMNLabel />` без явных bounds — тогда подпись центрируется внутри shape (рамка задачи достаточно большая)
- Для gateways (50×50): label справа или ниже — `x = gateway_x + 55, y = gateway_y + 18`
- Для sequence flows: label посередине edge — берём средний waypoint, `y = mid_y - 20` (над линией)

Пример:
```xml
<bpmndi:BPMNShape id="Event_1_di" bpmnElement="StartEvent_1">
  <dc:Bounds x="179" y="99" width="36" height="36" />
  <bpmndi:BPMNLabel>
    <dc:Bounds x="155" y="141" width="84" height="27" />
  </bpmndi:BPMNLabel>
</bpmndi:BPMNShape>
```

**Починка DI с нуля:** если DI полностью отсутствует или поломан — проще импортировать XML без DI в Camunda Modeler вручную и дать ему auto-layout. Но лучше сразу генерировать DI с разумными координатами:
- Горизонтальный поток: `x` растёт слева направо, шаг 120–150 px
- Вертикальное выравнивание: задачи на `y=100`, шлюзы на `y=100`, события на `y=108` (события меньше, центрировать)
- Лэйны: высота 180 px, сверху вниз; `y` узла внутри лэйна = y_lane + 60

---

## 7. Language conformance

**Что проверяем:** все `name` атрибуты на семантических элементах — на русском. Проверяется отдельно потому что языковая ошибка не ловится XSD-валидатором.

```python
import re
CYRILLIC = re.compile(r'[\u0400-\u04FF]')
BRAND_WHITELIST = {'Camunda', 'SBM', 'n11', 'Fibabanka', 'Sumsub', 'GDPR', 'HIPAA',
                   'PSD2', 'AML', 'KYC', 'DMN', 'BPMN', 'SLA', 'API', 'FEEL', 'JUEL',
                   'UUID', 'ISO', 'BDDK', 'BNPL', 'SCA', 'SWIFT', 'CIPS', 'SPFS',
                   'HUMO', 'Uzcard', 'Kaspi', 'Halyk', 'Mir', 'Мир'}

for elem in root.iter():
    name = elem.get('name')
    if not name:
        continue
    stripped = name
    for brand in BRAND_WHITELIST:
        stripped = stripped.replace(brand, '')
    stripped = re.sub(r'[0-9\W_]', '', stripped)
    if not stripped:
        continue  # only whitelist/digits/punctuation — OK
    if not CYRILLIC.search(stripped):
        print(f'FAIL: name="{name}" on {elem.tag} — no Cyrillic, likely English')
```

**Типовые ошибки:**
- Забыли перевести: `name="Start"`, `name="End"`, `name="Approved"`, `name="Send Email"`
- Смешанный язык без причины: `name="Проверка customer KYC"` → заменить на «Проверка KYC клиента» (KYC — в whitelist)
- Имя пула по-английски: `name="Bank"` → «Банк»

**Не считается ошибкой:**
- Продуктовые названия: `name="Интеграция с Camunda"`, `name="Передача в n11"`
- Технические аббревиатуры из whitelist: KYC, AML, API, SLA, BPMN, DMN, GDPR, HIPAA, PSD2 (полный список — см. `excel-spec-template.md` и `annotation-style-guide.md`, whitelist синхронизирован)

---

# Optional best practices (WARN, не блокируют показ)

Это рекомендации Camunda и наблюдения по типовым анти-паттернам. Несоответствие — повод улучшить модель, но не останавливать показ пользователю. Выводятся в отчёте отдельным блоком с префиксом `⚠ WARN`.

## 8. Technical ID naming convention

Camunda рекомендует префиксы, соответствующие типу элемента (Best-practices: Naming technically relevant IDs):

| XML element | Префикс |
|---|---|
| `<process>/@id` | `Process_` (например, `Process_BNPLApproval`) |
| `<startEvent>/@id` | `StartEvent_` |
| `<endEvent>/@id` | `EndEvent_` |
| `<userTask>/@id` | `Task_` или `UserTask_` |
| `<serviceTask>/@id` | `Task_` или `ServiceTask_` |
| `<exclusiveGateway>/@id` | `Gateway_` |
| `<sequenceFlow>/@id` | `Flow_` или `SequenceFlow_` |
| `<boundaryEvent>/@id` | `BoundaryEvent_` |
| `<message>/@id` | `Message_` |
| `<error>/@id` | `Error_` |
| `<bpmn:participant>/@id` | `Participant_` |
| `<lane>/@id` | `Lane_` |

После префикса — PascalCase, отражающий бизнес-смысл (`StartEvent_NewTweetWritten`, `Task_ReviewTweet`, `Gateway_TweetApproved`).

Длина id < 256 символов — лимит для RDBMS-backed Camunda (Oracle/PostgreSQL). Для Elasticsearch лимит 32,768, но лучше держать короче — id попадают в логи.

## 9. Event labels business-side

Camunda: «describe which state an object is in when the process is about to leave the event».

- Start event: что триггерит процесс. «Заявка подана», не «Start».
- End event: финальное бизнес-состояние. «Заявка одобрена», «Заявка отклонена», не «End».
- Intermediate event: промежуточное состояние. «Платёж получен», «Срок истёк».

Антипаттерн: «Start», «End», «Finish», «Done», «Process started».

## 10. Business vs technical errors

Camunda: «retrying technical problems should not be modeled in the diagram».

- Technical ошибки (сетевые сбои, временный отказ внешнего API) — НЕ моделировать в BPMN. Обрабатываются через Camunda job retries + incidents.
- Business ошибки (правила бизнес-процесса: товар недоступен, превышен лимит, скоринг не пройден) — моделировать через error events с errorCode.

Антипаттерн: цикл retry в модели с boundary timer event на каждом сервисном вызове.

## 11. Happy path emphasis

Camunda: «place tasks, events, and gateways belonging to the happy path on a straight sequence flow in the center of the diagram».

Основной успешный путь — прямая линия слева направо по центру. Исключения и обработка ошибок — отклонения вверх/вниз.

Проверяется визуально (статический анализ затруднён). Эвристика: happy path — это путь от startEvent до первого endEvent без событий об ошибке, минимум gateway-ветвлений.

## 12. Sentence case

Camunda recommended: первая буква заглавная, остальные строчные, кроме аббревиатур и имён собственных.

- Правильно: «Проверить заявку», «Требуется ли SCA?»
- Неправильно: «ПРОВЕРИТЬ ЗАЯВКУ», «Проверить Заявку»

## 13. Один executable process в collaboration

В коллаборейшен-модели с несколькими пулами обычно только один `<process>` имеет `isExecutable="true"` — это тот, который мы собираемся деплоить. Остальные — participant pools без `isExecutable`, представляющие внешние системы / контрагентов.

Антипаттерн: `isExecutable="true"` на всех процессах в коллаборейшене. Путаница, какой деплоится.

## 14. Filename aligned with process ID

Camunda recommended: если процесс `BNPLApprovalProcess`, то файл `BNPLApprovalProcess.bpmn`. Облегчает поиск, diff, версионирование.

## 15. Unused resources

`<bpmn:message>`, `<bpmn:error>`, `<bpmn:signal>`, `<bpmn:escalation>` объявлены на уровне `<definitions>`, но ни одно событие на них не ссылается. Не ошибка, но признак неполной доработки модели или остатка после рефакторинга.

```python
all_messages = {m.get('id') for m in root.iter('{*}message')}
referenced = {e.get('messageRef') for e in root.iter('{*}messageEventDefinition')}
unused = all_messages - referenced
if unused:
    print(f'WARN: unused messages: {unused}')
```

## 16. Empty process

Процесс содержит только `<startEvent>` → `<endEvent>` без промежуточных задач / шлюзов. Деплоится, выполняется, но бессмыслен.

```python
for process in root.iter('{*}process'):
    activities = list(process.iter('{*}task')) + \
                 [t for t in process.iter() if any(t.tag.endswith(suf) for suf in
                  ('UserTask', 'ServiceTask', 'ManualTask', 'SendTask', 'ReceiveTask',
                   'BusinessRuleTask', 'ScriptTask', 'subProcess', 'callActivity'))]
    if not activities:
        print(f'WARN: empty process {process.get("id")} has no activities')
```

## 17. Circular call activity detection

Call Activity A вызывает process B, а B содержит call activity на process A. Runtime stack overflow.

Статический анализ: построить граф call-зависимостей (для каждого `<callActivity camunda:calledElement="...">` — ребро от текущего process id к calledElement), найти циклы через DFS.

Актуально, если в одном файле несколько `<process>` (один файл — multi-process deployment).

---

## Формат отчёта на выход

```
📋 Валидация BPMN XML

Блокирующие проверки (все PASS — ГОТОВО):
✅ 1. Well-formedness
✅ 2. BPMN schema conformance
✅ 3. Structural integrity (10 подпунктов: seq flows / start-end / reachability / gateways / loops / event refs / boundary / duplicate IDs / subprocess type / data objects)
✅ 4. Message flows и Collaboration structure (direction / participant links / lane membership)
✅ 5. Camunda 7 executability (N tasks, M gateways, timer format, FEEL reserved words, multi-instance)
✅ 6. DI completeness (shapes / isHorizontal / isMarkerVisible / waypoints / labels)
✅ 7. Language conformance (все N имён на русском, K whitelist)

Рекомендательные (WARN, не блокируют):
✅ 8. Technical ID naming
⚠ 9. Event labels (3 события названы "Start" / "End" — стоит переформулировать business-side)
✅ 10. Business vs technical errors
✅ 11. Happy path emphasis
⚠ 12. Sentence case (2 label'а в ALL CAPS)
✅ 13. Один executable process
✅ 14. Filename aligned
✅ 15. Unused resources
✅ 16. Empty process
✅ 17. Circular call activity

ИТОГ: ✅ ГОТОВО К ПОКАЗУ ПОЛЬЗОВАТЕЛЮ (7/7 блокирующих PASS, 8/10 рекомендательных PASS)
```

При FAIL на блокирующих — после каждого `❌` идёт конкретика: какой элемент, какой атрибут, почему не прошёл. Затем — автоматическая починка, повторный прогон, обновление отчёта.

При WARN на рекомендательных — без автопочинки; выводятся как советы по улучшению модели, не блокируют показ.
