# IT Ops Patterns — управление ИТ-сервисами

Читается на Step 2, когда domain определён как IT ops, incident management, change management, SRE, service desk.

Базовая рамка — ITIL 4 и SRE-practices. Процессы типично реализуются в Jira Service Management / ServiceNow / внутренних системах.

---

## 1. Incident management (ITIL)

1. Alert received — Message Start Event (из monitoring: Prometheus alert / PagerDuty / end-user report в service desk)
2. Классификация — Business Rule Task (DMN): priority (P1/P2/P3/P4), category, assignment group
3. Priority routing — XOR по priority
4. Диагностика — User Task (dedicated on-call engineer для P1/P2, обычный engineer для P3/P4)
5. Эскалация по таймеру (boundary event) — для P1 типично 15 мин, для P2 — 1 час; при истечении — notify to manager / wake up next level
6. Resolution — User Task + Service Task: применение fix / workaround
7. Post-mortem — sub-process для P1 (и часто P2)

**Особенности моделирования:**
- На шаге 5 Timer Boundary с `cancelActivity="false"` (non-interrupting) — основная задача продолжается, эскалация идёт параллельно
- Для SLA-контракта с клиентом — timer на всём процессе (Response Time + Resolution Time по SLA); при нарушении — отдельное compensation событие
- Post-mortem для P1 — отдельная диаграмма: root cause analysis, action items, distribute to org

---

## 2. Change management

Approval loop + scheduled window (Timer Intermediate Catch Event) + rollback pattern через compensation.

1. Change request — User Task (инициатор: разработчик / DevOps)
2. CAB review (Change Advisory Board) — User Task (approval для major / standard changes)
3. Scheduled window — Timer Intermediate Catch Event (изменение выполняется только в разрешённое окно)
4. Execute change — Service Task с compensation (откат изменения)
5. Verification — User Task + monitoring
6. XOR — успех → End Event «Closed»; неудача → триггер compensation → rollback → инцидент

Референс для BPMN-паттерна: `bpmn-patterns.md` #5 (error boundary + compensation).

**Особенности моделирования:**
- Для standard / normal / emergency changes — разные sub-flows; XOR gateway по типу change
- Rollback — это compensation event, не просто backward sequence flow
