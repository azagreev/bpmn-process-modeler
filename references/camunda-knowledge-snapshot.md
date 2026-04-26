# Camunda Knowledge Snapshot — v1.0 (обновлён 2026-04-26)

```yaml
snapshot_version: 1.0
snapshot_date: 2026-04-26
source: docs.camunda.io, Camunda 7 Platform documentation + Best Practices + bpmnlint rules
target_platform: Camunda 7 (Platform)
maintenance_note: Refresh recommended every 6 months. Next refresh due: 2026-10-26.
refresh_procedure: See README.md section "Refresh snapshot procedure"
```

**Назначение.** Этот файл — fallback на случай, когда Camunda MCP (`https://camunda-docs.mcp.kapa.ai`) временно недоступен. Содержит курированную выжимку критических знаний из Camunda docs для генерации корректного Camunda 7 BPMN 2.0 XML. При активном MCP используется живая документация; этот файл — страховка.

**Что покрыто полностью (hybrid glass, production-grade):** базовая XML-структура, все типы задач с extension elements, все типы событий, все шлюзы, subprocesses, collaboration, DI-координаты и размеры, textAnnotation. Часто используемые элементы (~95% финтех-кейсов).

**Что покрыто в minimum-формате (base rules only):** ad-hoc subprocess, transaction subprocess, complex gateway, conditional events, compensation throw event. Редко используемые — базовый синтаксис + ссылка на live docs.

**Что не покрыто:** domain-specific примеры (Payment auth compensation и т.п.) — в degraded mode модель опирается на собственные `industry-patterns/fintech-patterns.md` и другие industry-файлы.

---

## 1. Корневая XML-структура

Минимально рабочий BPMN 2.0 файл для Camunda 7 Platform:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions
    xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
    xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
    xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
    xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
    id="Definitions_1"
    targetNamespace="http://bpmn.io/schema/bpmn"
    exporter="bpmn-process-modeler skill"
    exporterVersion="2.0">

  <bpmn:process id="Process_1" name="..." isExecutable="true">
    <!-- Flow nodes здесь -->
  </bpmn:process>

  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <!-- BPMNShape и BPMNEdge здесь -->
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
```

**Обязательные атрибуты `<bpmn:definitions>`:**
- `xmlns:bpmn`, `xmlns:bpmndi`, `xmlns:dc`, `xmlns:di`, `xmlns:xsi` — базовые BPMN-namespaces
- `xmlns:camunda="http://camunda.org/schema/1.0/bpmn"` — Camunda 7 extension elements (всегда используем для C7)
- `id` — уникальный id definitions block
- `targetNamespace` — любой URI, принято `http://bpmn.io/schema/bpmn`

**НЕ использовать** для Camunda 7:
- `xmlns:zeebe` (это Camunda 8 / Zeebe, другая платформа)
- Атрибут `modeler:executionPlatform="Camunda Cloud"` (только для C8)

**Уникальность ID.** Каждый атрибут `id` во всём документе должен быть уникальным. Дубликаты → Camunda Engine возвращает `DUPLICATE_ID` при деплое.

---

## 2. Задачи (Tasks)

### 2.1 User Task (пользовательская задача)

```xml
<bpmn:userTask id="Task_ReviewApplication" name="Рассмотреть заявку"
               camunda:assignee="${applicant.manager}"
               camunda:candidateGroups="riskManagers,underwriters">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:userTask>
```

**Обязательно для runtime (один из):**
- `camunda:assignee` — прямой assignee по ID
- `camunda:candidateUsers` — список кандидатов, один claim'ит задачу
- `camunda:candidateGroups` — роль / группа, члены могут claim'ить

Без любого из трёх — task-instance повиснет навсегда, никто не увидит её в Tasklist.

**Опциональные атрибуты:**
- `camunda:formKey="embedded:deployment:review-form.html"` — связать с Camunda Forms
- `camunda:dueDate="${dueDate}"` — срок выполнения
- `camunda:followUpDate` — напоминание
- `camunda:priority="50"` — 0..100

### 2.2 Service Task (сервисная задача)

**Внешний воркер (external task pattern — рекомендуемый):**

```xml
<bpmn:serviceTask id="Task_ChargeCard" name="Списать платёж"
                  camunda:type="external"
                  camunda:topic="payment-charge">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:serviceTask>
```

**Внутренний (Java delegate):**

```xml
<bpmn:serviceTask id="Task_ValidateOrder" name="Валидировать заказ"
                  camunda:delegateExpression="${orderValidator}">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:serviceTask>
```

**Альтернативы internal:**
- `camunda:class="com.example.MyDelegate"` — Java class напрямую
- `camunda:expression="${bean.method(execution)}"` — EL expression

**Обязательно:** один из `camunda:type="external"`+`camunda:topic`, `camunda:delegateExpression`, `camunda:class`, `camunda:expression`.

### 2.3 Send Task

```xml
<bpmn:sendTask id="Task_NotifyCustomer" name="Уведомить клиента"
               camunda:type="external" camunda:topic="send-notification"
               messageRef="Message_CustomerNotification">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:sendTask>

<bpmn:message id="Message_CustomerNotification" name="CustomerNotification"/>
```

Поведение — как serviceTask, но семантически означает «отправка сообщения». `messageRef` — опциональный link на объявленный message.
Assignment-атрибуты (`camunda:assignee`, `camunda:candidateUsers`, `camunda:candidateGroups`) на `sendTask`
не используем: если действие делает человек, это уже `userTask`.

### 2.4 Receive Task

```xml
<bpmn:receiveTask id="Task_WaitForPayment" name="Ожидать поступление оплаты"
                  messageRef="Message_PaymentReceived">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:receiveTask>

<bpmn:message id="Message_PaymentReceived" name="PaymentReceived"/>
```

Блокирует процесс до получения message с matching name через API correlation.

### 2.5 Business Rule Task (DMN)

```xml
<bpmn:businessRuleTask id="Task_CreditScoring" name="Скоринг заявки"
                       camunda:decisionRef="credit-scoring"
                       camunda:resultVariable="scoringResult"
                       camunda:mapDecisionResult="singleEntry">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:businessRuleTask>
```

**Обязательно:** `camunda:decisionRef` — ID DMN decision для вызова. `camunda:resultVariable` — имя процессной переменной для результата.

**`camunda:mapDecisionResult`** определяет формат вывода:
- `singleEntry` — один output (один столбец)
- `singleResult` — одна строка (много столбцов)
- `collectEntries` — список значений
- `resultList` — список мап (по умолчанию)

### 2.6 Script Task

```xml
<bpmn:scriptTask id="Task_CalculateInterest" name="Рассчитать проценты"
                 scriptFormat="javascript">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
  <bpmn:script><![CDATA[
    var principal = execution.getVariable('principal');
    var rate = execution.getVariable('rate');
    execution.setVariable('interest', principal * rate / 100);
  ]]></bpmn:script>
</bpmn:scriptTask>
```

**Обязательно:** `scriptFormat` (javascript / groovy / python) + inline `<bpmn:script>` ИЛИ `camunda:resource="classpath:script.js"`.

### 2.7 Manual Task

```xml
<bpmn:manualTask id="Task_DeliverEnvelope" name="Доставить конверт курьером">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:manualTask>
```

Выполняется вне системы, движок просто помечает как выполненный при next step. Runtime-атрибуты не нужны.

### 2.8 Call Activity

```xml
<bpmn:callActivity id="CallActivity_RunKYC" name="Провести KYC"
                   calledElement="KYCProcess"
                   camunda:calledElementBinding="latest"
                   camunda:calledElementVersion=""
                   camunda:calledElementTenantId=""
                   camunda:variableMappingClass=""
                   camunda:inheritVariables="true">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:callActivity>
```

**Обязательно:** `calledElement` — ID другого process definition для вызова. Без него runtime error `Cannot resolve called element`.

**`camunda:calledElementBinding`:** `latest` (default) / `deployment` / `version`.

---

## 3. События (Events)

### 3.1 Start Events

**None (без триггера, manual start):**
```xml
<bpmn:startEvent id="StartEvent_Manual" name="Начало процесса">
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:startEvent>
```

**Message Start Event (триггер — сообщение):**
```xml
<bpmn:startEvent id="StartEvent_ApplicationReceived" name="Заявка получена">
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
  <bpmn:messageEventDefinition messageRef="Message_Application"/>
</bpmn:startEvent>
<bpmn:message id="Message_Application" name="ApplicationReceived"/>
```

**Timer Start Event:**
```xml
<bpmn:startEvent id="StartEvent_DailyBatch" name="Ежедневный batch">
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
  <bpmn:timerEventDefinition>
    <bpmn:timeCycle xsi:type="bpmn:tFormalExpression">0 0 2 * * ?</bpmn:timeCycle>
  </bpmn:timerEventDefinition>
</bpmn:startEvent>
```

Варианты timer: `<bpmn:timeDuration>PT15M</bpmn:timeDuration>` (ISO 8601 duration), `<bpmn:timeDate>2026-12-31T23:59:00</bpmn:timeDate>` (конкретная дата), `<bpmn:timeCycle>0 0 2 * * ?</bpmn:timeCycle>` (cron) или `R3/PT10M` (ISO 8601 repeating).

**Signal Start Event:**
```xml
<bpmn:startEvent id="StartEvent_Emergency">
  <bpmn:signalEventDefinition signalRef="Signal_Emergency"/>
</bpmn:startEvent>
<bpmn:signal id="Signal_Emergency" name="EmergencyRaised"/>
```

**Conditional Start Event:**
```xml
<bpmn:startEvent id="StartEvent_Overdue">
  <bpmn:conditionalEventDefinition>
    <bpmn:condition xsi:type="bpmn:tFormalExpression">${daysOverdue > 30}</bpmn:condition>
  </bpmn:conditionalEventDefinition>
</bpmn:startEvent>
```

### 3.2 End Events

**None End Event (обычное завершение):**
```xml
<bpmn:endEvent id="EndEvent_Approved" name="Заявка одобрена">
  <bpmn:incoming>Flow_In</bpmn:incoming>
</bpmn:endEvent>
```

**Terminate End Event (прерывает ВСЕ ветки процесса):**
```xml
<bpmn:endEvent id="EndEvent_Cancelled" name="Отменено">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:terminateEventDefinition/>
</bpmn:endEvent>
```

**Error End Event (бросает business error):**
```xml
<bpmn:endEvent id="EndEvent_CreditDenied" name="В кредите отказано">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:errorEventDefinition errorRef="Error_CreditDenied"/>
</bpmn:endEvent>
<bpmn:error id="Error_CreditDenied" name="CreditDenied" errorCode="CREDIT_DENIED"/>
```

Обязательно: `<bpmn:error>` на уровне `<definitions>` с `errorCode` — иначе catch event не сможет поймать.

**Message End Event (отправляет message):**
```xml
<bpmn:endEvent id="EndEvent_NotifySender">
  <bpmn:messageEventDefinition messageRef="Message_Response"/>
</bpmn:endEvent>
```

**Cancel End Event** (только внутри transaction subprocess) — кодом опущен, используется редко.

**Compensate End Event** (триггерит compensation):
```xml
<bpmn:endEvent id="EndEvent_RollBack">
  <bpmn:compensateEventDefinition activityRef="Task_Charge"/>
</bpmn:endEvent>
```

### 3.3 Intermediate Catch Events

**Timer Intermediate Catch:**
```xml
<bpmn:intermediateCatchEvent id="Event_Wait15Min" name="Пауза 15 минут">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT15M</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:intermediateCatchEvent>
```

**Message Intermediate Catch:**
```xml
<bpmn:intermediateCatchEvent id="Event_WaitPayment" name="Ожидание оплаты">
  <bpmn:messageEventDefinition messageRef="Message_PaymentReceived"/>
</bpmn:intermediateCatchEvent>
```

**Signal Intermediate Catch:**
```xml
<bpmn:intermediateCatchEvent id="Event_WaitSignal">
  <bpmn:signalEventDefinition signalRef="Signal_Go"/>
</bpmn:intermediateCatchEvent>
```

### 3.4 Intermediate Throw Events

**Message Throw:**
```xml
<bpmn:intermediateThrowEvent id="Event_SendUpdate" name="Отправить статус">
  <bpmn:messageEventDefinition messageRef="Message_StatusUpdate"
                               camunda:type="external" camunda:topic="send-msg"/>
</bpmn:intermediateThrowEvent>
```

**Signal Throw:**
```xml
<bpmn:intermediateThrowEvent id="Event_Broadcast">
  <bpmn:signalEventDefinition signalRef="Signal_Ready"/>
</bpmn:intermediateThrowEvent>
```

**Escalation Throw** (не прерывает процесс):
```xml
<bpmn:intermediateThrowEvent id="Event_Escalate">
  <bpmn:escalationEventDefinition escalationRef="Escalation_SLAMissed"/>
</bpmn:intermediateThrowEvent>
<bpmn:escalation id="Escalation_SLAMissed" name="SLAMissed" escalationCode="SLA_MISSED"/>
```

### 3.5 Boundary Events

**Interrupting Timer (прерывает задачу):**
```xml
<bpmn:boundaryEvent id="Boundary_Timeout" name="Таймаут 24ч"
                    attachedToRef="Task_Review"
                    cancelActivity="true">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT24H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:boundaryEvent>
```

**Non-interrupting Timer (эскалация, не прерывает):**
```xml
<bpmn:boundaryEvent id="Boundary_Reminder" name="Напомнить через 4ч"
                    attachedToRef="Task_Review"
                    cancelActivity="false">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT4H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:boundaryEvent>
```

**Error Boundary (ВСЕГДА interrupting, `cancelActivity="true"` — по BPMN spec):**
```xml
<bpmn:boundaryEvent id="Boundary_PaymentFailed" name="Ошибка платежа"
                    attachedToRef="Task_Charge"
                    cancelActivity="true">
  <bpmn:errorEventDefinition errorRef="Error_Payment"/>
</bpmn:boundaryEvent>
```

**Message Boundary, Signal Boundary, Escalation Boundary, Compensation Boundary** — аналогично, замена `timerEventDefinition` на соответствующую.

**Правила для boundary:**
- `attachedToRef` — существующая activity (task / subprocess / callActivity)
- Нельзя прикрепить к шлюзу или событию
- Error boundary всегда interrupting

---

## 4. Шлюзы (Gateways)

### 4.1 Exclusive Gateway (XOR) — выбор одного пути

```xml
<bpmn:exclusiveGateway id="Gateway_CreditDecision" name="Решение по заявке"
                       default="Flow_Manual">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Approved</bpmn:outgoing>
  <bpmn:outgoing>Flow_Rejected</bpmn:outgoing>
  <bpmn:outgoing>Flow_Manual</bpmn:outgoing>
</bpmn:exclusiveGateway>

<bpmn:sequenceFlow id="Flow_Approved" name="Одобрено"
                   sourceRef="Gateway_CreditDecision" targetRef="Task_Disburse">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">${score >= 700}</bpmn:conditionExpression>
</bpmn:sequenceFlow>
<bpmn:sequenceFlow id="Flow_Rejected" name="Отказ"
                   sourceRef="Gateway_CreditDecision" targetRef="EndEvent_Rejected">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">${score &lt; 600}</bpmn:conditionExpression>
</bpmn:sequenceFlow>
<bpmn:sequenceFlow id="Flow_Manual" name="Ручная проверка"
                   sourceRef="Gateway_CreditDecision" targetRef="Task_ManualReview"/>
```

**Обязательно:**
- Атрибут `default="Flow_id"` — fallback-стрелка, если ни одно условие не сработало. Без default → incident в runtime, процесс останавливается.
- На default-стрелке НЕТ `<conditionExpression>`.
- На остальных — `<conditionExpression xsi:type="bpmn:tFormalExpression">${...}</bpmn:conditionExpression>`.
- Спецсимволы в expression экранируются: `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`.

**Именование:** XOR — вопрос («Решение по заявке», «Одобрено?»). Метки на стрелках — ответы («Одобрено», «Отказ», «Ручная»).

### 4.2 Parallel Gateway (AND) — все пути одновременно

**Split:**
```xml
<bpmn:parallelGateway id="Gateway_ParallelSplit">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_BranchA</bpmn:outgoing>
  <bpmn:outgoing>Flow_BranchB</bpmn:outgoing>
</bpmn:parallelGateway>
```

**Join:**
```xml
<bpmn:parallelGateway id="Gateway_ParallelJoin">
  <bpmn:incoming>Flow_BranchA_Done</bpmn:incoming>
  <bpmn:incoming>Flow_BranchB_Done</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:parallelGateway>
```

Стрелки из AND не имеют conditionExpression. Именование — не нужно (Camunda: avoid naming parallel gateways).

### 4.3 Inclusive Gateway (OR) — несколько путей

```xml
<bpmn:inclusiveGateway id="Gateway_Courses" name="Какие курсы выбраны?"
                       default="Flow_Salad">
  <bpmn:outgoing>Flow_Pasta</bpmn:outgoing>
  <bpmn:outgoing>Flow_Steak</bpmn:outgoing>
  <bpmn:outgoing>Flow_Salad</bpmn:outgoing>
</bpmn:inclusiveGateway>
```

Каждая стрелка (кроме default) — с `<conditionExpression>`. Срабатывает 0, 1 или несколько веток одновременно (в отличие от XOR — только одна).

### 4.4 Event-based Gateway — ожидание первого события

```xml
<bpmn:eventBasedGateway id="Gateway_WaitForAnswer">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_ToMsgCatch</bpmn:outgoing>
  <bpmn:outgoing>Flow_ToTimer</bpmn:outgoing>
</bpmn:eventBasedGateway>

<bpmn:intermediateCatchEvent id="Event_MsgAnswer">
  <bpmn:messageEventDefinition messageRef="Message_Answer"/>
</bpmn:intermediateCatchEvent>

<bpmn:intermediateCatchEvent id="Event_Timeout48h">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration>PT48H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:intermediateCatchEvent>
```

**Правила:**
- Из event-based gateway идут ТОЛЬКО intermediate catch events (message / timer / signal / condition)
- Не userTask, не serviceTask, не обычные задачи
- Именование шлюза не нужно (Camunda: avoid naming event-based gateways). Ориентир — последующие события.

---

## 5. Subprocesses

### 5.1 Embedded Subprocess (встроенный)

```xml
<bpmn:subProcess id="Subprocess_Order" name="Обработка заказа">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>

  <bpmn:startEvent id="StartEvent_InSub">
    <bpmn:outgoing>Flow_Sub1</bpmn:outgoing>
  </bpmn:startEvent>
  <!-- Внутренний flow -->
  <bpmn:endEvent id="EndEvent_InSub">
    <bpmn:incoming>Flow_SubN</bpmn:incoming>
  </bpmn:endEvent>
</bpmn:subProcess>
```

**Правила:**
- Внутренний StartEvent — типа **None** (без event definition). С message / timer / signal не деплоится.
- Внутри должен быть хотя бы один EndEvent.
- Все переменные наследуются из parent process, если не задан input/output mapping.

### 5.2 Event Subprocess

```xml
<bpmn:subProcess id="EventSub_Error" name="Обработчик ошибок"
                 triggeredByEvent="true">
  <bpmn:startEvent id="StartEvent_ErrorCatch" isInterrupting="true">
    <bpmn:outgoing>Flow_Handle</bpmn:outgoing>
    <bpmn:errorEventDefinition errorRef="Error_Any"/>
  </bpmn:startEvent>
  <!-- Обработка -->
</bpmn:subProcess>
```

**Правила:**
- Обязательно `triggeredByEvent="true"` на `<subProcess>`
- Обязательно event definition на startEvent (message / timer / signal / error / escalation / compensation / conditional)
- `isInterrupting="true"` (дефолт) — прерывает parent; `false` — параллельная ветка
- Event subprocess можно вкладывать в обычный subprocess или в корневой process

### 5.3 Call Activity — вызов другого процесса

См. раздел 2.8.

### 5.4 Multi-Instance (loop)

```xml
<bpmn:serviceTask id="Task_ProcessInvoices" name="Обработать инвойсы"
                  camunda:type="external" camunda:topic="process-invoice">
  <bpmn:multiInstanceLoopCharacteristics isSequential="false"
      camunda:collection="${invoices}"
      camunda:elementVariable="invoice">
    <bpmn:completionCondition xsi:type="bpmn:tFormalExpression">
      ${nrOfCompletedInstances >= 10}
    </bpmn:completionCondition>
  </bpmn:multiInstanceLoopCharacteristics>
</bpmn:serviceTask>
```

**Обязательно:**
- `isSequential="true"` или `"false"` — явно (по дефолту false)
- `camunda:collection` — expression на process variable с коллекцией, ИЛИ `<bpmn:loopCardinality>N</bpmn:loopCardinality>` для фиксированного числа итераций
- `camunda:elementVariable` — имя локальной переменной для текущего элемента (опционально, но полезно)
- `<bpmn:completionCondition>` — опционально, «первый выполнил — все завершены»

### 5.5 Ad-hoc и Transaction Subprocess

**Ad-hoc** (`<adHocSubProcess>`) — задачи выполняются в произвольном порядке. Редко используется в финтехе. Базовый синтаксис:

```xml
<bpmn:adHocSubProcess id="AdHoc_Review" name="Ad-hoc ревью">
  <!-- Задачи без fixed sequence flow -->
</bpmn:adHocSubProcess>
```

**Transaction** (`<transaction>`) — для ACID-транзакций с compensation. Специфический случай, минимум: `<bpmn:transaction method="compensate">...</bpmn:transaction>`.

Обе конструкции — если встретились, подтягивай live docs через MCP (в degraded mode используй только общие BPMN-правила).

---

## 6. Collaboration (пулы и лэйны)

```xml
<bpmn:collaboration id="Collaboration_1">
  <bpmn:participant id="Participant_Customer" name="Клиент"
                    processRef="Process_Customer"/>
  <bpmn:participant id="Participant_Bank" name="Банк"
                    processRef="Process_Bank"/>

  <bpmn:messageFlow id="MessageFlow_Application"
                    sourceRef="Task_Submit"
                    targetRef="StartEvent_ReceiveApp"
                    messageRef="Message_Application"/>
</bpmn:collaboration>

<bpmn:process id="Process_Customer" isExecutable="false">
  <!-- черный ящик или полный процесс -->
</bpmn:process>

<bpmn:process id="Process_Bank" isExecutable="true">
  <bpmn:laneSet id="LaneSet_Bank">
    <bpmn:lane id="Lane_Frontoffice" name="Фронт-офис">
      <bpmn:flowNodeRef>Task_ReceiveApp</bpmn:flowNodeRef>
    </bpmn:lane>
    <bpmn:lane id="Lane_Risk" name="Риск-менеджмент">
      <bpmn:flowNodeRef>Task_Score</bpmn:flowNodeRef>
    </bpmn:lane>
  </bpmn:laneSet>
  <!-- flow nodes -->
</bpmn:process>
```

**Правила:**
- Message flow — ТОЛЬКО между разными пулами, не внутри
- Sequence flow — ТОЛЬКО внутри одного пула, не между
- `isExecutable="true"` обычно на одном процессе в коллаборейшене (обычно свой банк/наш процесс); партнёрские пулы — `isExecutable="false"` или без атрибута
- `<lane>` с `<flowNodeRef>` — узлы того же процесса
- Один `<laneSet>` на процесс
- Black box pool — `<participant>` без `processRef`, представляет внешнюю систему без visibility

---

## 7. BPMN DI (визуализация)

### 7.1 Стандартные размеры shapes (дефолт Camunda Modeler)

| Элемент | Width × Height |
|---|---|
| `userTask`, `sendTask`, `serviceTask`, `businessRuleTask`, `scriptTask`, `manualTask` | 100 × 80 |
| `subProcess` (collapsed) | 100 × 80 |
| `subProcess` (expanded) | зависит от содержимого |
| `callActivity` | 100 × 80 |
| `startEvent`, `endEvent`, `intermediateCatchEvent`, `intermediateThrowEvent`, `boundaryEvent` | 36 × 36 |
| `exclusiveGateway`, `parallelGateway`, `inclusiveGateway`, `eventBasedGateway`, `complexGateway` | 50 × 50 |
| `dataObject`, `dataObjectReference` | 36 × 50 |
| `dataStoreReference` | 50 × 50 |
| `textAnnotation` | flexible |
| `participant` (pool) | flexible |
| `lane` | flexible |

### 7.2 Пример BPMNShape для event

```xml
<bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
  <dc:Bounds x="179" y="99" width="36" height="36"/>
  <bpmndi:BPMNLabel>
    <dc:Bounds x="162" y="142" width="70" height="14"/>
  </bpmndi:BPMNLabel>
</bpmndi:BPMNShape>
```

### 7.3 Пример BPMNShape для задачи

```xml
<bpmndi:BPMNShape id="Task_Review_di" bpmnElement="Task_Review">
  <dc:Bounds x="270" y="77" width="100" height="80"/>
  <bpmndi:BPMNLabel/>
</bpmndi:BPMNShape>
```

Для task пустой `<bpmndi:BPMNLabel/>` — подпись центрируется внутри shape (рамка достаточно большая).

### 7.4 Пример BPMNShape для XOR gateway

```xml
<bpmndi:BPMNShape id="Gateway_Decision_di" bpmnElement="Gateway_Decision"
                  isMarkerVisible="true">
  <dc:Bounds x="425" y="92" width="50" height="50"/>
  <bpmndi:BPMNLabel>
    <dc:Bounds x="425" y="62" width="50" height="14"/>
  </bpmndi:BPMNLabel>
</bpmndi:BPMNShape>
```

**Критично:** `isMarkerVisible="true"` для XOR — без него рисуется пустой ромб, визуально неотличимый от inclusive OR.

### 7.5 Pool / Lane с обязательным isHorizontal

```xml
<bpmndi:BPMNShape id="Participant_Bank_di" bpmnElement="Participant_Bank"
                  isHorizontal="true">
  <dc:Bounds x="140" y="50" width="1200" height="450"/>
</bpmndi:BPMNShape>

<bpmndi:BPMNShape id="Lane_Risk_di" bpmnElement="Lane_Risk"
                  isHorizontal="true">
  <dc:Bounds x="170" y="220" width="1170" height="180"/>
</bpmndi:BPMNShape>
```

**Критично:** `isHorizontal="true"` на pool и lane. Без него Modeler рендерит вертикально.

### 7.6 BPMNEdge

```xml
<bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
  <di:waypoint x="215" y="117"/>
  <di:waypoint x="270" y="117"/>
  <bpmndi:BPMNLabel>
    <dc:Bounds x="230" y="99" width="30" height="14"/>
  </bpmndi:BPMNLabel>
</bpmndi:BPMNEdge>
```

**Обязательно:** минимум 2 `<di:waypoint>`. Для изгибов (L-, S-forms) — 3+ точек.

### 7.7 Heuristics для координат (генерация с нуля)

- Горизонтальный happy path: `y = 100`, шаг `x`: 130–150 px между узлами
- Events центрируются: `y` события = `y` соседней задачи + 22 (т.к. event 36×36, task 100×80)
- XOR gateway: `y = 115`, `x` перед задачей-бранчем на 80 px
- Lane: высота 180, узлы внутри — `y = y_lane + 60`
- Text annotation: обычно над узлом, `y = node_y - 80`, ширина 180

---

## 8. Text Annotation и Association

```xml
<bpmn:textAnnotation id="TextAnnotation_SLA">
  <bpmn:text>SLA: 24 часа согласно Внутреннему регламенту одобрения v2.1</bpmn:text>
</bpmn:textAnnotation>

<bpmn:association id="Association_SLA"
                  sourceRef="Task_Approve"
                  targetRef="TextAnnotation_SLA"/>
```

В DI:
```xml
<bpmndi:BPMNShape id="TextAnnotation_SLA_di" bpmnElement="TextAnnotation_SLA">
  <dc:Bounds x="380" y="30" width="180" height="60"/>
</bpmndi:BPMNShape>

<bpmndi:BPMNEdge id="Association_SLA_di" bpmnElement="Association_SLA">
  <di:waypoint x="320" y="77"/>
  <di:waypoint x="400" y="90"/>
</bpmndi:BPMNEdge>
```

**Правила:**
- Каждая textAnnotation имеет уникальный id
- Association с уникальным id + sourceRef (узел) + targetRef (textAnnotation)
- Без BPMNShape + BPMNEdge в DI — аннотация не отрисуется

---

## 9. Camunda 7 Extension Elements (обзорно)

Все Camunda-атрибуты работают через namespace `xmlns:camunda="http://camunda.org/schema/1.0/bpmn"`.

| Элемент | Атрибут | Назначение |
|---|---|---|
| userTask | `camunda:assignee` | Прямой assignee по user ID |
| userTask | `camunda:candidateUsers` | Список кандидатов |
| userTask | `camunda:candidateGroups` | Роль / группа |
| userTask | `camunda:formKey` | Link на Camunda Form |
| userTask | `camunda:dueDate` | Срок выполнения |
| userTask | `camunda:priority` | 0..100 |
| sendTask | `camunda:type="external"` | Тип external worker для отправки сообщения |
| sendTask | `camunda:topic` | Topic для job worker |
| sendTask | `camunda:class` | Internal Java class |
| sendTask | `camunda:delegateExpression` | Internal Java bean |
| sendTask | `camunda:expression` | EL expression |
| sendTask | `camunda:resultVariable` | Имя var для результата |
| serviceTask | `camunda:type="external"` | Тип external worker |
| serviceTask | `camunda:topic` | Topic для job worker |
| serviceTask | `camunda:delegateExpression` | Internal Java bean |
| serviceTask | `camunda:class` | Internal Java class |
| serviceTask | `camunda:expression` | EL expression |
| businessRuleTask | `camunda:decisionRef` | DMN decision ID |
| businessRuleTask | `camunda:resultVariable` | Имя var для результата |
| businessRuleTask | `camunda:mapDecisionResult` | singleEntry / singleResult / collectEntries / resultList |
| scriptTask | `scriptFormat` | javascript / groovy / python |
| scriptTask | `camunda:resource` | Путь к файлу со скриптом |
| callActivity | `calledElement` | ID вызываемого процесса |
| callActivity | `camunda:calledElementBinding` | latest / deployment / version |
| всё | `camunda:async-before / -after` | Async continuations |
| всё | `camunda:exclusive` | Exclusive lock job |
| всё | `<bpmn:extensionElements>` | Контейнер для сложных ext: input/output mappings, execution listeners |

### 9.1 Camunda 7 attribute compatibility matrix

`unknown attribute` warnings в Camunda Modeler обычно означают, что `camunda:*` атрибут попал не на тот BPMN-элемент.

| Атрибут | Допустимо на |
|---|---|
| `camunda:assignee` | userTask, manualTask* |
| `camunda:candidateUsers` | userTask, manualTask* |
| `camunda:candidateGroups` | userTask, manualTask* |
| `camunda:dueDate` | userTask, manualTask* |
| `camunda:followUpDate` | userTask, manualTask* |
| `camunda:formKey` | userTask, startEvent |
| `camunda:priority` | userTask, manualTask* |
| `camunda:type` | serviceTask, sendTask, businessRuleTask |
| `camunda:topic` | serviceTask, sendTask, businessRuleTask, scriptTask (when `camunda:type="external"`) |
| `camunda:class` | serviceTask, sendTask, businessRuleTask, scriptTask |
| `camunda:delegateExpression` | serviceTask, sendTask, businessRuleTask, scriptTask |
| `camunda:expression` | serviceTask, sendTask, businessRuleTask, scriptTask |
| `camunda:resultVariable` | serviceTask, sendTask, businessRuleTask, scriptTask |
| `camunda:decisionRef` | businessRuleTask |
| `camunda:mapDecisionResult` | businessRuleTask |
| `camunda:resource` | scriptTask, businessRuleTask |
| `camunda:calledElement` | callActivity |

* `manualTask` only if you deliberately keep that legacy modeling pattern.

### Execution listeners (для audit / мониторинга)

```xml
<bpmn:userTask id="Task_Foo">
  <bpmn:extensionElements>
    <camunda:executionListener event="start" delegateExpression="${startListener}"/>
    <camunda:executionListener event="end" class="com.example.EndListener"/>
  </bpmn:extensionElements>
</bpmn:userTask>
```

### Input / Output mappings

```xml
<bpmn:serviceTask id="Task_Charge">
  <bpmn:extensionElements>
    <camunda:inputOutput>
      <camunda:inputParameter name="amount">${orderTotal}</camunda:inputParameter>
      <camunda:outputParameter name="paymentId">${result.id}</camunda:outputParameter>
    </camunda:inputOutput>
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

---

## 10. Error Events (подробнее)

```xml
<!-- Объявление errors на уровне definitions -->
<bpmn:error id="Error_InsufficientFunds" name="InsufficientFunds"
            errorCode="INSUFFICIENT_FUNDS"/>
<bpmn:error id="Error_FraudDetected" name="FraudDetected"
            errorCode="FRAUD_DETECTED"/>

<!-- Throw error (end event) -->
<bpmn:endEvent id="EndEvent_NoFunds">
  <bpmn:errorEventDefinition errorRef="Error_InsufficientFunds"/>
</bpmn:endEvent>

<!-- Catch error (boundary) -->
<bpmn:boundaryEvent id="Boundary_NoFunds"
                    attachedToRef="Task_Charge"
                    cancelActivity="true">
  <bpmn:errorEventDefinition errorRef="Error_InsufficientFunds"/>
</bpmn:boundaryEvent>

<!-- Catch-all error (опускает errorRef, ловит любую) -->
<bpmn:boundaryEvent id="Boundary_AnyError"
                    attachedToRef="Subprocess_Payment"
                    cancelActivity="true">
  <bpmn:errorEventDefinition/>
</bpmn:boundaryEvent>
```

**Правила:**
- `<bpmn:error>` объявляется на уровне `<definitions>` с `errorCode`
- Без `errorCode` catch event не сможет match'ить error
- Одинаковый `errorCode` — матч между throw и catch
- Error boundary — ВСЕГДА interrupting
- Error в scope subprocess ловится только там, где scope обрамляет throw; иначе propagation вверх

**Business vs technical errors (Camunda recommendation):**
- Business (недостаточно средств, превышен лимит, отклонено скорингом) → моделируй как error event
- Technical (network timeout, 500 от API, connection refused) → НЕ моделируй в BPMN, используй retries + incidents на уровне движка

---

## 11. Message Events (подробнее)

```xml
<!-- Объявление message на уровне definitions -->
<bpmn:message id="Message_Payment" name="PaymentReceived"/>

<!-- Start event по message -->
<bpmn:startEvent id="StartEvent_Trigger">
  <bpmn:messageEventDefinition messageRef="Message_Payment"/>
</bpmn:startEvent>

<!-- Intermediate catch -->
<bpmn:intermediateCatchEvent id="Event_WaitPayment">
  <bpmn:messageEventDefinition messageRef="Message_Payment"/>
</bpmn:intermediateCatchEvent>

<!-- Message flow между пулами -->
<bpmn:messageFlow sourceRef="Task_Send" targetRef="Event_WaitPayment"
                  messageRef="Message_Payment"/>
```

**Правила:**
- `<bpmn:message>` имеет `id` (tech, для ссылок) и `name` (бизнес-имя для API correlation)
- `name` используется для correlation — два message с одинаковым `name` но разными `id` создадут неоднозначность
- messageFlow идёт только через границу пула

---

## 12. Timer Events (подробнее)

```xml
<bpmn:timerEventDefinition>
  <!-- Вариант 1: Duration (ISO 8601) -->
  <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT15M</bpmn:timeDuration>

  <!-- Вариант 2: Date (ISO 8601) -->
  <bpmn:timeDate xsi:type="bpmn:tFormalExpression">2026-12-31T23:59:00</bpmn:timeDate>

  <!-- Вариант 3: Cycle (cron) -->
  <bpmn:timeCycle xsi:type="bpmn:tFormalExpression">0 0 2 * * ?</bpmn:timeCycle>

  <!-- Вариант 4: Repeating (ISO 8601 R) -->
  <bpmn:timeCycle xsi:type="bpmn:tFormalExpression">R3/PT10M</bpmn:timeCycle>
</bpmn:timerEventDefinition>
```

**ISO 8601 duration формат:** `P[n]Y[n]M[n]DT[n]H[n]M[n]S`

| Нужно | Формат |
|---|---|
| 15 минут | `PT15M` |
| 2 часа | `PT2H` |
| 3 дня | `P3D` |
| Неделя | `P1W` |
| Год | `P1Y` |
| 1 день 6 часов | `P1DT6H` |

**Cron Camunda 7** (6 полей, с секундами): `0 0 2 * * ?` = каждый день в 2:00. Поля: секунды минуты часы день месяц день_недели. `?` = «не важно», `*` = «каждый».

---

## 13. Compensation

**Scenario:** Заплатили — надо отменить платёж при ошибке дальше по процессу.

```xml
<!-- Основная задача — платёж -->
<bpmn:serviceTask id="Task_Charge" name="Списать платёж"
                  camunda:type="external" camunda:topic="charge"/>

<!-- Compensation handler (isForCompensation="true") -->
<bpmn:serviceTask id="Task_Refund" name="Вернуть платёж"
                  isForCompensation="true"
                  camunda:type="external" camunda:topic="refund"/>

<!-- Compensation boundary event -->
<bpmn:boundaryEvent id="Boundary_Compensate"
                    attachedToRef="Task_Charge">
  <bpmn:compensateEventDefinition/>
</bpmn:boundaryEvent>

<!-- Association boundary → handler -->
<bpmn:association associationDirection="One"
                  sourceRef="Boundary_Compensate"
                  targetRef="Task_Refund"/>

<!-- Triggering compensation (end event или throw event) -->
<bpmn:endEvent id="EndEvent_Rollback">
  <bpmn:compensateEventDefinition activityRef="Task_Charge"/>
</bpmn:endEvent>
```

**Правила:**
- Compensation handler имеет `isForCompensation="true"` — не попадает в обычный flow
- Compensation boundary — без `cancelActivity` (это не про прерывание)
- Trigger — `<endEvent>` или `<intermediateThrowEvent>` с `<compensateEventDefinition>`; `activityRef` указывает целевую задачу (опционально — триггерит все handlers в scope)
- Association направлена от boundary к handler
- Handler не связан обычным sequenceFlow

---

## 14. Best Practices (по Camunda docs)

### Именование

| Элемент | Конвенция именования |
|---|---|
| Activity (task, subprocess) | Object + verb в инфинитиве: «Рассмотреть заявку», «Провести KYC» |
| Start event | Trigger, что запускает: «Заявка получена» |
| End event | Бизнес-результат: «Заявка одобрена», «Платёж выполнен» |
| Intermediate event | State, в котором процесс: «Платёж получен», «Срок истёк» |
| XOR / Inclusive gateway | Question: «Одобрено?», «Тип клиента?» |
| Parallel gateway | Не именовать |
| Event-based gateway | Не именовать |
| Joining gateway | Не именовать |
| Sequence flow с условием | Короткий ответ: «Да» / «Нет», «Одобрено» / «Отклонено» |
| Pool | Object + verb в номинализированной форме: «Обработка заявки», либо орг. роль: «Банк» |
| Lane | Роль: «Риск-менеджмент», «Фронт-офис» |

**Sentence case:** первая буква заглавная, остальные строчные, кроме аббревиатур и имён собственных.

### Technical IDs (рекомендация Camunda)

| BPMN element | Префикс ID |
|---|---|
| process | `Process_` |
| startEvent | `StartEvent_` |
| endEvent | `EndEvent_` |
| userTask | `Task_` или `UserTask_` |
| serviceTask | `Task_` или `ServiceTask_` |
| exclusiveGateway | `Gateway_` |
| sequenceFlow | `Flow_` |
| boundaryEvent | `BoundaryEvent_` |
| message | `Message_` |
| error | `Error_` |
| participant | `Participant_` |
| lane | `Lane_` |

После префикса — PascalCase для бизнес-значения: `Task_ReviewApplication`, `Gateway_CreditDecision`, `Flow_Approved`.

**Лимит длины id**: < 256 символов для RDBMS backend, до 32К для Elasticsearch. Лучше держать короче.

### Читаемость диаграммы

- Happy path — прямая линия слева направо в центре диаграммы
- Ошибки / исключения — выше или ниже центра
- Modelar explicit (gateways, не conditional flows; явные start/end; splitting vs joining отдельными шлюзами)
- Симметрия: пары splitting/joining шлюзов образуют визуальный блок
- 7±2 элементов на одном уровне максимум — иначе декомпозируй в subprocesses
- Collaboration pools предпочтительнее lanes для operational level
- Не моделировать retry-логику в BPMN — это runtime concern (Camunda job workers + incidents)

---

## 15. FEEL Reserved Words (не использовать как var names)

```
true, false, null, function, if, then, else, for, between, instance, of
```

Попытка использовать как variable name → runtime error. Переименовать: `isActive`, `isDeleted` вместо `true`/`false`.

---

## 16. Частые ошибки деплоя

- `Duplicate ID` — несколько узлов с одинаковым id
- `Cannot resolve called element` — callActivity без `calledElement` или ссылка на несуществующий process
- `DEPLOYMENT: No topic defined on service task` — serviceTask external без `camunda:topic`
- `Error with id 'X' not found` — errorEventDefinition ссылается на не-объявленный error
- `No default flow on gateway` — XOR/inclusive без `default="Flow_id"`, и ни одно условие не сработало
- `Straight-through processing loop` — цикл в процессе без разрывателя (userTask/timer/receiveTask). Добавить разрыватель.
- `Reserved words in FEEL expressions` — see раздел 15

---

## 17. Whitelist технических токенов (для консистентности с language conformance check)

**Бренды / продукты (не переводятся):** Camunda, Zeebe, Kafka, PostgreSQL, Redis, Sumsub, SBM, n11, Fibabanka, Telebirr, Papara, Hepsipay, Trendyol, M-PESA, Android, iOS, AWS, GCP, Docker, Kubernetes, HUMO, Uzcard, Kaspi, Halyk, Mир.

**Аббревиатуры / стандарты:** BPMN, DMN, FEEL, JUEL, XOR, AND, OR, SLA, KYC, AML, API, SDK, REST, SOAP, JSON, XML, URL, UUID, HTTP, HTTPS, GDPR, HIPAA, PSD2, BDDK, ITIL, PHI, PEP, SCA, BNPL, POS, P2P, CoD, CJM, JTBD, EMI, BaaS, UTC, ISO, SMS, PII, KPI, OKR, CI, CD, PDF, SWIFT, CIPS, SPFS.

**ISO 8601 durations:** PT15M, PT24H, P1D, P1W, P1Y, R3/PT10M.

**Валюты:** EUR, USD, RUB, UZS, KZT, TRY, ETB, ₽, ₸, ₺.

**Технические префиксы BPMN IDs (в скрытых колонках):** `Activity_*`, `Gateway_*`, `Event_*`, `Flow_*`, `Participant_*`, `Lane_*`, `TextAnnotation_*`, `Association_*`, `Process_*`, `Collaboration_*`, `MessageFlow_*`, `BoundaryEvent_*`, `Message_*`, `Error_*`.

Whitelist синхронизирован с `excel-spec-template.md` и `annotation-style-guide.md`.

---

## 18. Методология построения диаграмм

Этот раздел — не синтаксис, а **как** подходить к задаче с BPMN-точки зрения. Остальные разделы snapshot отвечают «какие теги использовать»; этот отвечает «в каком порядке принимать решения». Критически важен в degraded mode, когда Camunda MCP недоступен и модель не может консультироваться с живой документацией.

### 18.1 Happy path first

Сначала моделируй успешный сценарий полностью, только потом добавляй исключения.

Порядок действий:
1. **End event (desired outcome).** Определи целевой бизнес-результат: «Заявка одобрена», «Платёж выполнен», «Товар доставлен». Что хочет получить клиент/процесс при успехе?
2. **Start event (trigger).** Что запускает процесс? Получено сообщение? Наступила дата? Клиент подал заявку вручную?
3. **Activities.** Какие задачи ВСЕГДА нужны для достижения end event? Без них успех невозможен?
4. **Intermediate milestones.** Опционально — промежуточные состояния процесса (message events между шагами для очень длинных процессов).
5. **Exceptions — incremental.** Добавляй по одному типу проблем за раз. Сначала — самый критичный (финансовый убыток, регуляторный риск). Потом — менее критичные.

Применимость: всегда. Особенно критично в финтех, где альтернативных regulatory-путей много, и соблазн моделировать все сценарии параллельно ведёт к каше.

### 18.2 Modeling explicitly

Всегда предпочитай явное BPMN-моделирование неявным shortcut'ам. Camunda формально рекомендует:

- **Gateway вместо conditional flow.** Если путь ветвится — всегда ставь явный gateway-символ (XOR / AND / OR). Conditional flows (стрелка с условием без gateway) — валидный BPMN, но reviewer'ы не всегда понимают семантику, лучше избегать.
- **Явные start и end events.** Процесс без start/end НЕ деплоится в Camunda Engine. Даже если BPMN spec формально это разрешает, избегай.
- **Split и join — разными шлюзами.** Не делай один XOR-шлюз с 2 incoming и 2 outgoing стрелками одновременно (он делает и merge, и split). Reviewer увидит только одну роль, вторую пропустит. Разделяй на два XOR-шлюза: один merging, другой splitting.

Применимость: всегда. Подкреплено Check 3d в `validation-checklist.md`.

### 18.3 Modeling symmetrically

Пары splitting/joining шлюзов образуют визуальные блоки. Читатель легче воспринимает диаграмму, если блоки визуально балансируются.

Правила:
- XOR-split → задачи в ветках → XOR-join в конце (парный)
- AND-split → параллельные задачи → AND-join
- Inclusive split → OR-join (именно inclusive join, не XOR)
- Вложенные блоки — внутри внешних (не пересекаются)
- Пары шлюзов — на одной вертикальной линии (y-coordinate близкий), чтобы блок воспринимался как один сгусток

Антипаттерн: splitting gateway в одном месте, joining gateway на большом расстоянии справа, в середине ещё XOR с совершенно другой семантикой. Визуально хаос.

Применимость: для диаграмм с ≥ 2 gateway-блоками. Для простых линейных процессов — не актуально.

### 18.4 Reading direction (left-to-right)

Основной поток — слева направо. Обоснование: западная аудитория читает в этом направлении, human field of vision оптимизирован под горизонтальные мониторы.

Правила:
- Happy path — горизонтальная линия по центру диаграммы, y ≈ 100-120
- Exception paths (error handling, timeouts, альтернативные ветки) — выше или ниже центра, y < 60 или y > 180
- Joining gateway — правее splitting gateway (не слева и не ниже)
- Длинные процессы (> 1000px по x): использовать **link events** для разрыва:
  - Throw link в одном месте → Catch link с тем же именем в другом
  - Позволяет продолжить процесс с новой строки без тянущейся через всю диаграмму стрелки

**Не надо:**
- Sequence flow справа-налево (против reading direction)
- Flows, пересекающие несколько лэйнов без нужды
- Пересечения sequence flow друг с другом (если можно переупорядочить узлы)

Применимость: всегда. Прямо влияет на DI-координаты из раздела 7 snapshot.

### 18.5 Decomposition (7±2)

Правило Миллера: человек удерживает в рабочей памяти 7±2 объекта. Для BPMN это значит:

- **≤ 7 узлов на одном уровне** — читаемо
- **> 9 узлов на одном уровне** → декомпозируй в subprocess
- **> 2 уровней вложенных шлюзов** → тоже декомпозируй (визуально слишком сложно)

Паттерн «Overview + Drill-down»:

- **Level 0 (overview):** 3-7 collapsed subprocesses, каждый представляет фазу жизненного цикла процесса. Пример для BNPL: «Подача заявки» → «Проверка и скоринг» → «Одобрение» → «Выдача» → «Погашение»
- **Level 1 (drill-down):** каждая фаза раскрыта в отдельной диаграмме с операционными деталями. 7-15 узлов — норма.
- **Level 2 (если нужен):** очень редко, только для экстремально сложных подпроцессов

На какой уровень что помещать:
- **Level 0:** SLA всего процесса, ключевые compliance-ограничения, owner, общая архитектура
- **Level 1:** конкретные бизнес-правила, интеграционные детали, error handling для конкретной фазы, открытые вопросы по шагам

Антипаттерн: на Level 0 детальные бизнес-правила («Одобряется при скоринге ≥ 700…»). Они принадлежат Level 1.

Применимость: при процессах > 9 узлов. Малые процессы (5-8 узлов) — оставляй плоскими.

### 18.6 Consolidated anti-patterns

Сводный список частых ошибок построения (для быстрого review перед Step 6 валидацией):

1. **Retry-логика в диаграмме.** Сетевые сбои, временная недоступность API — это runtime concern, не бизнес-процесс. Camunda Engine делает retries автоматически через job workers и incidents. В BPMN — не моделировать. Реальные retry-циклы бизнес-логики (например: «клиент не ответил → напомнить через 3 дня → напомнить ещё раз через неделю → закрыть») — это escalation pattern, а не retry.

2. **Каскад XOR для бизнес-правил.** Если логика ветвления имеет > 2 критериев с комбинациями (категория AND сумма AND скоринг) — выноси в DMN (Business Rule Task) и ветвись одним XOR по результату. Иначе правила растут экспоненциально и становятся неподдерживаемыми. Подробнее: `annotation-style-guide.md` раздел «Сложная логика — в DMN, а не в шлюзе».

3. **Технические детали на overview-уровне.** «DMN credit-scoring-v2.3.dmn», «Kafka topic payments.authorize.v2», «SLA 3 сек» — это Level 1 детали. На Level 0 — только процесс-целиковый контекст (SLA end-to-end, ФЗ, owner).

4. **Слишком много lanes (≥ 5).** Если в одном пуле 5+ ролей — подумай, не стоит ли перейти на collaboration с отдельными пулами. Межпульные message flows часто читаются лучше, чем большая матрица lane × activity. Camunda: lanes затрудняют maintenance, collaboration — предпочтительнее для operational level.

5. **Пулы без message flows между ними.** Если пулы не общаются — зачем они separate? Вероятно, хватит lanes в одном пуле. Пулы имеют смысл, когда показывают внешний обмен (клиент ↔ банк, маркетплейс ↔ фулфилмент).

6. **Message flow внутри одного пула.** Это нарушение BPMN spec. Внутри пула — sequence flow, между пулами — message flow. Часть Check 4 в validation-checklist.

7. **Conditional flow вместо gateway.** Валидно синтаксически, но неявно для reviewer'а. Всегда ставь gateway, даже для простых «Да/Нет».

8. **Параллельные ветки без явного AND-split/join.** Если две задачи должны выполниться параллельно — явный AND-split вначале, AND-join перед слиянием. Без join token не дождётся второй ветки, процесс может вести себя непредсказуемо.

9. **Default flow отсутствует на XOR/inclusive gateway.** Если ни одно условие не сработало в runtime → Camunda Engine создаёт incident, процесс останавливается. Всегда определяй default flow через атрибут `default="Flow_id"` на шлюзе.

10. **Open questions в XML-комментариях, а не на канвасе.** Reviewer смотрит диаграмму, а не источник. Все неопределённости выносить в `<textAnnotation>` с префиксом «⚠ Уточнить:».

Применимость: как checklist при self-review перед Step 6.

---

## Приложение — источники

Этот snapshot выжимка из следующих разделов Camunda docs:
- `docs.camunda.io/docs/components/modeler/bpmn/bpmn-primer` — структура BPMN
- `docs.camunda.io/docs/components/best-practices/modeling/` — Best Practices (Creating readable process models, Naming BPMN elements, Naming technically relevant IDs, Modeling with situation patterns, Dealing with problems and exceptions, Modeling beyond the happy path)
- `docs.camunda.io/docs/components/modeler/reference/modeling-guidance/rules/` — bpmnlint rules (called-element, element-type, error-reference, escalation-reference, feel, message-reference, no-loop)
- Camunda 7 User Guide — extension elements, runtime attributes

Для актуальных живых данных используй `search_camunda_knowledge_sources` через MCP. Этот файл — страховка на случай недоступности MCP.
