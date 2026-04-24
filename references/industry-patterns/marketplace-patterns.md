# Marketplace Patterns — e-commerce, логистика, cross-border retail

Читается на Step 2, когда domain определён как e-commerce, marketplace, logistics, fulfillment, seller journey или cross-border retail.

Для денежных процессов (refund, chargeback, merchant payout, BNPL) — параллельно читать `fintech-patterns.md`: здесь товарная и логистическая часть, там денежная.

---

## Содержание

1. [Order-to-cash](#1-order-to-cash)
2. [Returns / товарные возвраты](#2-returns)
3. [Pick-Pack-Ship (fulfillment)](#3-pick-pack-ship)
4. [Seller discovery + onboarding journey](#4-seller-discovery)
5. [Cross-border marketplace flow](#5-cross-border-marketplace)

---

## 1. Order-to-cash

Каноничные этапы (сохраняй названия близкими к этим, стейкхолдеры их узнают):

1. Оформление заказа — User Task (клиент)
2. Оплата — Service Task с компенсацией (refund)
3. Подтверждение продавцом — User Task + Timer (обычно 24 ч) → эскалация отмена
4. Сборка — User Task (склад)
5. Передача в доставку — Send Task
6. Доставка — длительный sub-process, может быть отдельной диаграммой
7. Подтверждение получения — Message Catch Event
8. Финальный расчёт с продавцом (payout) — см. `fintech-patterns.md` #14

**Особенности моделирования:**
- Часто нужен отдельный пул «Продавец» в collaboration — через message flows
- На шаге 2 компенсация обязательна: если последующие шаги падают, возврат средств автоматический
- Для BNPL-оплат шаг 2 — сложнее: запускается под-процесс из `fintech-patterns.md` #10

---

## 2. Returns

Товарная часть возврата. Денежная часть — в `fintech-patterns.md` #9 (Refund).

1. Заявка на возврат — User Task (клиент через ЛК)
2. Одобрение — XOR: автоматически (Business Rule Task по причине и категории товара) или вручную (User Task для sensitive категорий)
3. Генерация возвратного документа (возвратная накладная, ETIR для EU) — Script Task
4. Получение товара — Message Catch Event (ТК / ПВЗ / self-ship)
5. Проверка состояния товара — User Task (склад)
6. XOR: товар в порядке → возврат средств (см. `fintech-patterns.md` #9); товар повреждён / подменён → sub-process dispute с клиентом

**Compliance:**
- РФ: Закон о защите прав потребителей ст. 18 (14 дней на возврат товара надлежащего качества), ст. 25 (непродовольственные товары)
- ЕС: Directive 2011/83/EU — 14 дней cooling-off для online purchases
- Турция: Закон № 6502 о защите потребителей

**Особенности моделирования:**
- Обязательная петля (rework loop) на шаге 5: если проверка выявила расхождение, возврат на шаг 1 с новой причиной
- Для маркетплейса в РФ: 54-ФЗ — при возврате средств также генерируется чек возврата (Service Task)

---

## 3. Pick-Pack-Ship

Логистический sub-process внутри Order-to-cash. Часто моделируется с лэйнами: Складской работник / Контролёр / Логист.

1. Получение заказа — Message Start Event
2. Allocation (резерв товара на складе) — Service Task
3. Picking (сборка) — User Task с привязкой `camunda:candidateGroups="Комплектовщики"`
4. Quality check — User Task (Контролёр)
5. Packing — User Task
6. Labeling + загрузка в ТК — Service Task (интеграция с курьерской службой: СДЭК, Boxberry, Почта России, PTT, DHL)
7. Передача курьеру — Send Task

**Особенности моделирования:**
- Для высоко-SLA заказов (same-day, next-day): добавляется Timer Boundary на каждом шаге с эскалацией
- Для сборных / многопозиционных заказов — inclusive gateway (OR) после allocation: не все позиции могут быть на одном складе, часть идёт на dropshipping
- Интеграция с WMS/MES — через external worker pattern в Camunda 7

---

## 4. Seller discovery

Предлежащий KYB-процессу исследовательский / маркетинговый процесс онбординга селлера. Применяется при расширении маркетплейса в новый регион (пример: WB Uzbekistan, Belarus, Ethiopia).

1. Identification — Service Task: выгрузка целевых продавцов из открытых реестров / соцсетей / отраслевых справочников
2. Outreach — Send Task (email / cold call / WhatsApp)
3. Initial interest — User Task + Message Catch (продавец откликнулся) + Timer Boundary (если не откликнулся → Re-outreach после периода)
4. Discovery call — User Task: интервью по AJTBD / Job Map методологии
5. Качественная оценка соответствия — Business Rule Task (размер бизнеса, готовность к онбордингу, продуктовая категория)
6. XOR: подходит → переход на процесс 3 (Seller/Merchant KYB в fintech) / не подходит → End Event / требует дополнительного сопровождения → User Task (account manager)

**Особенности моделирования:**
- Этот процесс — часто не BPMN, а CRM-воронка. Переводится в BPMN, когда компания хочет формализовать и автоматизировать часть этапов
- На шаге 3 обязателен non-interrupting Timer Boundary: дать продавцу время откликнуться, но не застревать в ожидании
- Для международной экспансии collaboration pool добавляется: «Маркетплейс HQ» + «Локальный партнёр / представительство» + «Селлер»

---

## 5. Cross-border marketplace

Трансграничный маркетплейсовый заказ: клиент в одной стране, продавец в другой, товар физически пересекает границу. Применяется для WB Ethiopia B2C, AliExpress, локальных трансграничных моделей.

Сложный многоучастный процесс. Рекомендуется иерархическая декомпозиция (overview + drill-down).

**Overview (Level 0):**

1. Заказ — Message Start Event (клиент)
2. Оплата в локальной валюте — Service Task (см. `fintech-patterns.md` #5)
3. Передача в фулфилмент в стране продавца — sub-process (expanded в Level 1 #A)
4. Международная доставка + таможенная очистка — sub-process (expanded в Level 1 #B)
5. Локальная доставка в стране клиента — sub-process (expanded в Level 1 #C)
6. Подтверждение получения + закрытие заказа — Message Catch Event

**Level 1 #B: Таможенная очистка**
1. Экспортная декларация в стране продавца — Service Task
2. Транзит (авиа / ж/д / авто) — Send Task
3. Импортная декларация в стране клиента — Service Task (интеграция с ФТС / локальной таможней)
4. Уплата пошлин и НДС (от пороговых значений) — Service Task с компенсацией
5. Физическая проверка (выборочная) — User Task (сотрудник таможни)
6. Выпуск в свободное обращение — Message Event

**Compliance-аннотации:**
- РФ: ТК ЕАЭС + 289-ФЗ; порог беспошлинного ввоза — актуальный на дату (меняется регулярно, аннотация «⚠ Уточнить порог»)
- Эфиопия: Income Tax Amendment 1395/2025, VAT 1341/2024, Reg. 586/2026 (отмена zero-rate tax holidays)
- Для data flow клиентских данных: отдельная схема data flow с cross-border data transfer (152-ФЗ + локальные законы)

**Особенности моделирования:**
- Обязательно collaboration pool с 4+ участниками: Клиент, Маркетплейс, Продавец, Логистика, Таможня страны-импортёра, часто — локальная компания-импортёр of record
- Message flows между каждой парой, где есть обмен документами / статусами
- Компенсация на шаге 4 (уплата пошлин) — если заказ отменяется после очистки, rollback пошлин возможен не всегда (зависит от юрисдикции) — критичная аннотация
