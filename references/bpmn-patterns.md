# BPMN Patterns — готовые XML-сниппеты

Библиотека паттернов, которые встречаются в 80% бизнес-процессов. Копируй сниппет, меняй ID и `name` на русском — и получаешь рабочий фрагмент BPMN.

Все сниппеты — Camunda 7 (Platform) compatible.

> **Перед копированием сниппета:** проверь, что выбранный BPMN-тип задачи (`userTask` / `sendTask` /
> `serviceTask` / `businessRuleTask` / `scriptTask`) совместим с прикрепляемыми `camunda:*`
> атрибутами. Матрица совместимости — в `references/validation-checklist.md`, Check 5b.
> Самая частая ошибка — `camunda:candidateGroups` на `sendTask` (валиден только на `userTask`).

---

## Table of Contents

1. [Approval loop (цикл согласования с возможным возвратом)](#1-approval-loop)
2. [4-eyes principle (двойная проверка)](#2-4-eyes-principle)
3. [Parallel review (параллельное согласование)](#3-parallel-review)
4. [Timer-based escalation (эскалация по таймеру)](#4-timer-based-escalation)
5. [Error boundary with compensation (обработка ошибок с компенсацией)](#5-error-boundary-compensation)
6. [B2B message exchange between pools](#6-b2b-message-exchange)
7. [Business Rule Task via DMN](#7-business-rule-dmn)
8. [Event-based gateway (ожидание одного из событий)](#8-event-based-gateway)
9. [Documentation pattern](#9-documentation-pattern)
10. [Glossary annotation pattern](#10-glossary-annotation-pattern)

---

## 1. Approval loop

Задача уходит на согласование. Если отклонена — возвращается исполнителю на доработку. Если одобрена — идёт дальше.

```xml
<bpmn:userTask id="Activity_Prepare" name="Подготовить документ"
               camunda:candidateGroups="Инициаторы">
  <bpmn:incoming>Flow_Start_Prepare</bpmn:incoming>
  <bpmn:outgoing>Flow_Prepare_Review</bpmn:outgoing>
</bpmn:userTask>

<bpmn:userTask id="Activity_Review" name="Согласовать документ"
               camunda:candidateGroups="Согласующие">
  <bpmn:incoming>Flow_Prepare_Review</bpmn:incoming>
  <bpmn:outgoing>Flow_Review_Gateway</bpmn:outgoing>
</bpmn:userTask>

<bpmn:exclusiveGateway id="Gateway_Approved" name="Одобрено?">
  <bpmn:incoming>Flow_Review_Gateway</bpmn:incoming>
  <bpmn:outgoing>Flow_Approved</bpmn:outgoing>
  <bpmn:outgoing>Flow_Rejected</bpmn:outgoing>
</bpmn:exclusiveGateway>

<bpmn:sequenceFlow id="Flow_Approved" name="Да" sourceRef="Gateway_Approved" targetRef="Event_End_Approved">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">${approved == true}</bpmn:conditionExpression>
</bpmn:sequenceFlow>
<bpmn:sequenceFlow id="Flow_Rejected" name="Нет, на доработку" sourceRef="Gateway_Approved" targetRef="Activity_Prepare">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">${approved == false}</bpmn:conditionExpression>
</bpmn:sequenceFlow>
```

Добавь `<textAnnotation>` на шлюз с бизнес-правилом: «Максимум 3 итерации возврата — далее эскалация руководителю».

---

## 2. 4-eyes principle

Два независимых согласователя. Оба должны одобрить. Используется в compliance-чувствительных операциях (крупные платежи, KYC, выдача кредитов).

Реализуется через **параллельный шлюз** + две `userTask` с разными `candidateGroups` + **сливающий шлюз** + XOR на результат:

```xml
<bpmn:parallelGateway id="Gateway_Split_4Eyes" name="Параллельное согласование"/>

<bpmn:userTask id="Activity_Review_First" name="Первая подпись"
               camunda:candidateGroups="Менеджер"/>
<bpmn:userTask id="Activity_Review_Second" name="Вторая подпись"
               camunda:candidateGroups="Риск-менеджер"/>

<bpmn:parallelGateway id="Gateway_Join_4Eyes"/>

<bpmn:exclusiveGateway id="Gateway_Both_Approved" name="Обе подписи?">
  <!-- outgoing: both_yes -> Activity_Execute; any_no -> End_Rejected -->
</bpmn:exclusiveGateway>
```

Обязательная аннотация: «Согласно внутреннему регламенту — 4-eyes для сумм свыше X ₽».

---

## 3. Parallel review

Несколько независимых проверок (легал, финансы, безопасность). Ждём все результаты, затем агрегируем.

```xml
<bpmn:parallelGateway id="Gateway_Split_Review"/>
  <!-- 3 outgoing flows -->

<bpmn:userTask id="Activity_Legal_Review" name="Проверка юриста"
               camunda:candidateGroups="Legal"/>
<bpmn:userTask id="Activity_Finance_Review" name="Проверка финансов"
               camunda:candidateGroups="Finance"/>
<bpmn:userTask id="Activity_Security_Review" name="Проверка безопасности"
               camunda:candidateGroups="Security"/>

<bpmn:parallelGateway id="Gateway_Join_Review"/>
  <!-- 3 incoming flows, 1 outgoing -->
```

Отличие от 4-eyes: здесь три разные проверки по содержанию, а не две одинаковые подписи.

---

## 4. Timer-based escalation

Если задача не выполнена за N времени — эскалация. Реализуется через **boundary timer event** на задаче.

```xml
<bpmn:userTask id="Activity_Manager_Approve" name="Одобрение руководителя"
               camunda:candidateGroups="Менеджер"/>

<bpmn:boundaryEvent id="Event_Timeout_24h" name="SLA 24 часа истёк"
                    attachedToRef="Activity_Manager_Approve"
                    cancelActivity="false">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT24H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:boundaryEvent>

<bpmn:sequenceFlow sourceRef="Event_Timeout_24h" targetRef="Activity_Escalate_To_Director"/>
```

- `cancelActivity="false"` — non-interrupting (задача продолжается, эскалация идёт параллельно)
- `cancelActivity="true"` — interrupting (задача отменяется, процесс идёт по эскалационной ветке)

ISO 8601 duration formats: `PT15M` (15 минут), `PT24H` (24 часа), `P3D` (3 дня), `P1W` (неделя).

---

## 5. Error boundary with compensation

Платёж прошёл, но позже отменяется. Нужна компенсация (возврат средств).

```xml
<bpmn:serviceTask id="Activity_Charge_Payment" name="Списать средства"
                  camunda:type="external" camunda:topic="payment-charge"
                  isForCompensation="false">
  <bpmn:outgoing>Flow_To_Ship</bpmn:outgoing>
</bpmn:serviceTask>

<bpmn:boundaryEvent id="Event_Compensation" attachedToRef="Activity_Charge_Payment">
  <bpmn:compensateEventDefinition/>
</bpmn:boundaryEvent>

<bpmn:serviceTask id="Activity_Refund_Payment" name="Вернуть средства"
                  camunda:type="external" camunda:topic="payment-refund"
                  isForCompensation="true"/>

<bpmn:association associationDirection="One"
                  sourceRef="Event_Compensation" targetRef="Activity_Refund_Payment"/>

<bpmn:endEvent id="Event_End_Cancel">
  <bpmn:compensateEventDefinition/>
</bpmn:endEvent>
```

Триггер компенсации — end event с `compensateEventDefinition` либо intermediate throw event.

---

## 6. B2B message exchange

Два пула (например, Маркетплейс ↔ Банк). Сообщения пересекают границу пула.

```xml
<bpmn:collaboration id="Collaboration_1">
  <bpmn:participant id="Participant_Marketplace" name="Маркетплейс" processRef="Process_Marketplace"/>
  <bpmn:participant id="Participant_Bank" name="Банк" processRef="Process_Bank"/>

  <bpmn:messageFlow id="MessageFlow_Request" name="Запрос на авторизацию"
                    sourceRef="Activity_Send_Auth_Request"
                    targetRef="Event_Receive_Auth_Request"/>

  <bpmn:messageFlow id="MessageFlow_Response" name="Результат авторизации"
                    sourceRef="Activity_Send_Auth_Response"
                    targetRef="Event_Receive_Auth_Response"/>
</bpmn:collaboration>
```

Правило: `messageFlow` всегда идёт МЕЖДУ пулами, никогда внутри одного пула (внутри — `sequenceFlow`).

---

## 7. Business Rule Task via DMN

Сложная табличная логика (матрица решений по скорингу, правила тарификации) — выносится в DMN-таблицу.

```xml
<bpmn:businessRuleTask id="Activity_Calculate_Score" name="Рассчитать скоринг"
                       camunda:decisionRef="credit-scoring"
                       camunda:resultVariable="scoringResult"
                       camunda:mapDecisionResult="singleEntry"/>
```

Аннотация обязательна: «DMN-таблица credit-scoring.dmn — актуальна на <дата>».

---

## 8. Event-based gateway

Ожидание одного из нескольких событий. Первое случившееся — определяет путь.

```xml
<bpmn:eventBasedGateway id="Gateway_Wait_For_Response" name="Ждём ответ клиента"/>

<bpmn:intermediateCatchEvent id="Event_Client_Confirmed" name="Клиент подтвердил">
  <bpmn:messageEventDefinition messageRef="Message_ClientConfirmation"/>
</bpmn:intermediateCatchEvent>

<bpmn:intermediateCatchEvent id="Event_Timer_Expired" name="Истёк срок 48 часов">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration>PT48H</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:intermediateCatchEvent>
```

После event-based gateway идут ТОЛЬКО intermediate catch events (message, timer, signal, conditional) — задачи и другие шлюзы запрещены BPMN-спецификацией.

## 9. Documentation pattern

Короткое имя + `<bpmn:documentation>` для длинной прозы о том, что именно происходит в задаче.

```xml
<bpmn:userTask id="Activity_T7_SendVisaTask" name="Направить ПС на визирование"
               camunda:candidateGroups="КСКБ">
  <bpmn:documentation>КСКБ направляет в ПС пакет документов через СЭД: визовый PDF Соглашения,
заключение ПС о правоспособности, чек-лист актуализации (приложение № 4), документы Клиента,
выписка ЕГРЮЛ и нотариально удостоверенная доверенность представителя при необходимости (п. 5.23).</bpmn:documentation>
</bpmn:userTask>
```

Лучше всего работает так:
- имя задачи 2-4 слова;
- прозу держать в 2-4 предложениях;
- в конце указывать пункт регламента / ВНД / закона;
- не дублировать имя задачи;
- использовать это поле для деталей, которые не помещаются в коробку BPMN.

## 10. Glossary annotation pattern

Один общий `<bpmn:textAnnotation>` с глоссарием аббревиатур для всей диаграммы.

```xml
<bpmn:textAnnotation id="TextAnnotation_Glossary">
  <bpmn:text>Глоссарий аббревиатур: УП — Управление продажами | КСКБ — Корпоративный сегмент
кредитного бизнеса | ПС — Правовая служба | ОСКБ — Операционно-складской контроль бизнеса |
УКЭП — Усиленная квалифицированная электронная подпись</bpmn:text>
</bpmn:textAnnotation>
```

Правила:
- annotation относится к диаграмме целиком, а не к одной задаче;
- не дублируй в ней длинную прозу из `<bpmn:documentation>`;
- размещай её в свободной зоне диаграммы, обычно внизу под пулом;
- если в модели есть аббревиатуры, glossary annotation должна быть одна и понятная.
