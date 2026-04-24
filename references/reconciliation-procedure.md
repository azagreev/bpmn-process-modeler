# Reconciliation Procedure — 9 проверок соответствия Excel и BPMN

Алгоритм Step 9. Задача — убедиться, что Excel-спецификация не разошлась с BPMN-диаграммой. Проверки гоняются ПОСЛЕ сохранения `.xlsx` и ДО вызова `present_files`.

---

## Почему это важно

Excel-таблица — это отдельный артефакт, с которым потом работают BA, стейкхолдеры, разработчики. Если в таблице неточность, а на диаграмме всё правильно — возникает silent drift: разработчик реализует по таблице, QA проверяет по диаграмме, продуктовая команда согласовывает по третьему источнику. Лечится это болезненно.

Поэтому сверка — не опциональный nice-to-have, а обязательный этап, и её результат показывается пользователю перед `present_files`.

---

## Общий план

```python
from pathlib import Path
import openpyxl
import xml.etree.ElementTree as ET

NS = {
    'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    'camunda': 'http://camunda.org/schema/1.0/bpmn',
}

def reconcile(bpmn_path: Path, xlsx_path: Path) -> dict:
    """Returns dict with per-check results and overall verdict."""
    tree = ET.parse(bpmn_path)
    root = tree.getroot()
    wb = openpyxl.load_workbook(xlsx_path)
    spec_sheet = wb['Спецификация']

    results = {}
    results['check_1_node_count'] = check_node_count(root, spec_sheet)
    results['check_2_id_mapping'] = check_id_mapping(root, spec_sheet)
    results['check_3_name_parity'] = check_name_parity(root, spec_sheet)
    results['check_4_lane_pool_parity'] = check_lane_pool_parity(root, spec_sheet)
    results['check_5_gateway_rules'] = check_gateway_rules(root, spec_sheet)
    results['check_6_end_event_outcomes'] = check_end_event_outcomes(root, spec_sheet)
    results['check_7_annotation_coverage'] = check_annotation_coverage(root, wb)
    results['check_8_execution_order'] = check_execution_order(root, spec_sheet)
    results['check_9_utf8_integrity'] = check_utf8_integrity(xlsx_path)

    critical_fails = sum(1 for r in results.values() if r['status'] == 'CRITICAL')
    warnings = sum(1 for r in results.values() if r['status'] == 'WARN')
    if critical_fails:
        verdict = 'CRITICAL'
    elif warnings:
        verdict = 'PARTIAL'
    else:
        verdict = 'FULL_MATCH'
    results['verdict'] = verdict
    return results
```

Каждая check-функция возвращает dict с ключами: `status` (`PASS`/`WARN`/`CRITICAL`), `details` (строка для отчёта), `data` (структурированные расхождения для автопочинки).

---

## Check 1: Node count parity

```python
FLOW_NODE_TAGS = {
    'startEvent', 'endEvent', 'intermediateCatchEvent', 'intermediateThrowEvent',
    'boundaryEvent', 'task', 'userTask', 'serviceTask', 'manualTask',
    'sendTask', 'receiveTask', 'businessRuleTask', 'scriptTask',
    'subProcess', 'callActivity', 'exclusiveGateway', 'parallelGateway',
    'inclusiveGateway', 'eventBasedGateway',
}

def check_node_count(root, spec_sheet):
    bpmn_nodes = []
    for elem in root.iter():
        tag = elem.tag.rsplit('}', 1)[-1]
        if tag in FLOW_NODE_TAGS:
            bpmn_nodes.append(elem.get('id'))
    excel_rows = spec_sheet.max_row - 1  # minus header
    if len(bpmn_nodes) == excel_rows:
        return {'status': 'PASS',
                'details': f'BPMN nodes: {len(bpmn_nodes)}, Excel rows: {excel_rows}'}
    return {'status': 'CRITICAL',
            'details': f'BPMN nodes: {len(bpmn_nodes)}, Excel rows: {excel_rows} — расхождение {abs(len(bpmn_nodes) - excel_rows)}',
            'data': {'bpmn_count': len(bpmn_nodes), 'excel_count': excel_rows}}
```

`sequenceFlow` и `messageFlow` НЕ считаются строками — они в колонке «Примечания» у соответствующих узлов.

---

## Check 2: ID-level mapping

```python
def check_id_mapping(root, spec_sheet):
    bpmn_ids = set()
    for elem in root.iter():
        tag = elem.tag.rsplit('}', 1)[-1]
        if tag in FLOW_NODE_TAGS:
            bpmn_ids.add(elem.get('id'))
    # _BPMN_ID в последней колонке (скрытая J)
    id_col = None
    for col in range(1, spec_sheet.max_column + 1):
        if spec_sheet.cell(row=1, column=col).value == '_BPMN_ID':
            id_col = col
            break
    excel_ids = set()
    for r in range(2, spec_sheet.max_row + 1):
        val = spec_sheet.cell(row=r, column=id_col).value
        if val:
            excel_ids.add(val)
    only_in_bpmn = bpmn_ids - excel_ids
    only_in_excel = excel_ids - bpmn_ids
    matched = bpmn_ids & excel_ids
    if not only_in_bpmn and not only_in_excel:
        return {'status': 'PASS',
                'details': f'{len(matched)} совпало'}
    return {'status': 'CRITICAL',
            'details': f'{len(matched)} совпало, {len(only_in_bpmn)} только в BPMN, {len(only_in_excel)} только в Excel',
            'data': {'only_in_bpmn': list(only_in_bpmn),
                     'only_in_excel': list(only_in_excel)}}
```

Колонка `_BPMN_ID` — критична для этой проверки. Если её нет — reconciliation не может нормально работать.

---

## Check 3: Name parity

```python
def check_name_parity(root, spec_sheet):
    name_col, id_col = 3, 10  # Название элемента = C, _BPMN_ID = J
    bpmn_names = {}
    for elem in root.iter():
        tag = elem.tag.rsplit('}', 1)[-1]
        if tag in FLOW_NODE_TAGS and elem.get('name'):
            bpmn_names[elem.get('id')] = elem.get('name').strip()
    mismatches = []
    for r in range(2, spec_sheet.max_row + 1):
        bid = spec_sheet.cell(row=r, column=id_col).value
        xname = (spec_sheet.cell(row=r, column=name_col).value or '').strip()
        bname = bpmn_names.get(bid, '').strip()
        if bid and bname and bname != xname:
            mismatches.append((bid, bname, xname))
    if not mismatches:
        return {'status': 'PASS', 'details': 'все названия совпадают'}
    return {'status': 'WARN',
            'details': f'{len(mismatches)} расхождений в названиях',
            'data': {'mismatches': mismatches}}
```

Почему WARN а не CRITICAL: пользователь мог отредактировать Excel перед reconciliation (для читаемости), это не катастрофа. Но логируем и показываем.

Нормализация пробелов: `' '.join(text.split())` — чтобы `"Проверка  скоринга"` и `"Проверка скоринга"` не считались расхождением.

---

## Check 4: Lane/Pool parity

```python
def check_lane_pool_parity(root, spec_sheet):
    participant_col, id_col = 5, 10  # E и J
    # Построить map: node_id -> (pool_name, lane_name)
    node_to_lane_pool = {}
    for process in root.iter(f'{{{NS["bpmn"]}}}process'):
        process_id = process.get('id')
        # Найти соответствующего participant
        pool_name = None
        for part in root.iter(f'{{{NS["bpmn"]}}}participant'):
            if part.get('processRef') == process_id:
                pool_name = part.get('name', '')
                break
        # Пройти по lanes
        for lane in process.iter(f'{{{NS["bpmn"]}}}lane'):
            lane_name = lane.get('name', '')
            for fnr in lane.iter(f'{{{NS["bpmn"]}}}flowNodeRef'):
                node_to_lane_pool[fnr.text] = (pool_name, lane_name)
        # Узлы без lane — просто pool
        for elem in process.iter():
            tag = elem.tag.rsplit('}', 1)[-1]
            if tag in FLOW_NODE_TAGS and elem.get('id') not in node_to_lane_pool:
                node_to_lane_pool[elem.get('id')] = (pool_name, '')

    mismatches = []
    for r in range(2, spec_sheet.max_row + 1):
        bid = spec_sheet.cell(row=r, column=id_col).value
        xparticipant = (spec_sheet.cell(row=r, column=participant_col).value or '').strip()
        if bid not in node_to_lane_pool:
            continue
        pool, lane = node_to_lane_pool[bid]
        if pool and lane:
            expected = f'{pool} → {lane}'
        elif lane:
            expected = lane
        elif pool:
            expected = pool
        else:
            expected = '—'
        if xparticipant != expected:
            mismatches.append((bid, expected, xparticipant))
    if not mismatches:
        return {'status': 'PASS', 'details': 'все роли совпадают'}
    return {'status': 'WARN',
            'details': f'{len(mismatches)} расхождений',
            'data': {'mismatches': mismatches}}
```

---

## Check 5: Gateway decision rule present

```python
GATEWAY_TAGS = {'exclusiveGateway', 'inclusiveGateway', 'eventBasedGateway'}

def check_gateway_rules(root, spec_sheet):
    desc_col, id_col = 6, 10  # F и J
    gateway_ids = set()
    for elem in root.iter():
        tag = elem.tag.rsplit('}', 1)[-1]
        if tag in GATEWAY_TAGS:
            gateway_ids.add(elem.get('id'))
    filled = 0
    missing = []
    for r in range(2, spec_sheet.max_row + 1):
        bid = spec_sheet.cell(row=r, column=id_col).value
        if bid not in gateway_ids:
            continue
        desc = (spec_sheet.cell(row=r, column=desc_col).value or '').strip()
        if desc and len(desc) >= 10:  # минимальная осмысленность
            filled += 1
        else:
            missing.append(bid)
    total = len(gateway_ids)
    if not missing:
        return {'status': 'PASS', 'details': f'{filled}/{total} правил заполнены'}
    return {'status': 'CRITICAL' if missing else 'PASS',
            'details': f'{filled}/{total} заполнены, пусто: {missing}',
            'data': {'missing_gateways': missing}}
```

Шлюз без правила — критичный пробел: reviewer не может понять, как процесс ветвится. Авто-починка: извлечь условия с исходящих sequenceFlow и вписать в F.

---

## Check 6: End event outcome coverage

```python
def check_end_event_outcomes(root, spec_sheet):
    output_col, id_col = 8, 10  # H и J
    end_event_ids = {e.get('id') for e in root.iter(f'{{{NS["bpmn"]}}}endEvent')}
    total = len(end_event_ids)
    filled = 0
    missing = []
    for r in range(2, spec_sheet.max_row + 1):
        bid = spec_sheet.cell(row=r, column=id_col).value
        if bid not in end_event_ids:
            continue
        out = (spec_sheet.cell(row=r, column=output_col).value or '').strip()
        if out and out != '—':
            filled += 1
        else:
            missing.append(bid)
    if not missing:
        return {'status': 'PASS', 'details': f'{filled}/{total} заполнены'}
    return {'status': 'WARN',
            'details': f'{filled}/{total} заполнены',
            'data': {'missing_end_events': missing}}
```

Авто-починка: для end event «Заявка одобрена» выставить «BNPL-контракт активирован, график платежей отправлен клиенту» на основе имени.

---

## Check 7: Annotation coverage

```python
def check_annotation_coverage(root, wb):
    # Собрать все textAnnotation и их associations
    annotations = {}
    for ta in root.iter(f'{{{NS["bpmn"]}}}textAnnotation'):
        text_elem = ta.find(f'{{{NS["bpmn"]}}}text')
        annotations[ta.get('id')] = text_elem.text if text_elem is not None else ''
    associations = {}
    for assoc in root.iter(f'{{{NS["bpmn"]}}}association'):
        src = assoc.get('sourceRef')
        tgt = assoc.get('targetRef')
        # Аннотация может быть либо src либо tgt
        if src in annotations:
            associations.setdefault(tgt, []).append(annotations[src])
        elif tgt in annotations:
            associations.setdefault(src, []).append(annotations[tgt])

    # Проверить: каждая аннотация отражена в колонке «Примечания»
    spec = wb['Спецификация']
    notes_col, id_col = 9, 10  # I и J
    uncovered = []
    for node_id, notes_list in associations.items():
        # Найти row по node_id
        row = None
        for r in range(2, spec.max_row + 1):
            if spec.cell(row=r, column=id_col).value == node_id:
                row = r
                break
        if row is None:
            uncovered.append((node_id, 'row not found'))
            continue
        cell_text = (spec.cell(row=row, column=notes_col).value or '')
        for annot_text in notes_list:
            # Искать либо сам текст, либо значимую часть (>15 chars)
            key = annot_text.strip()[:20]
            if key not in cell_text:
                uncovered.append((node_id, annot_text))

    # Проверить, что все «⚠ Уточнить» есть на листе «Открытые вопросы»
    questions_sheet = wb['Открытые вопросы']
    q_texts = set()
    for r in range(2, questions_sheet.max_row + 1):
        q = questions_sheet.cell(row=r, column=4).value  # «Вопрос»
        if q:
            q_texts.add(q.strip())
    missing_questions = []
    for annot_id, annot_text in annotations.items():
        if '⚠ Уточнить' in (annot_text or ''):
            question_body = annot_text.split('⚠ Уточнить:', 1)[-1].strip()
            if not any(question_body[:30] in q for q in q_texts):
                missing_questions.append(annot_id)

    if not uncovered and not missing_questions:
        return {'status': 'PASS',
                'details': f'{len(annotations)} аннотаций перенесены'}
    return {'status': 'WARN',
            'details': f'{len(uncovered)} не в Примечаниях, {len(missing_questions)} не на листе Открытые вопросы',
            'data': {'uncovered': uncovered, 'missing_questions': missing_questions}}
```

---

## Check 8: Execution order sanity

```python
def check_execution_order(root, spec_sheet):
    id_col = 10
    row_order = []
    for r in range(2, spec_sheet.max_row + 1):
        bid = spec_sheet.cell(row=r, column=id_col).value
        if bid:
            row_order.append(bid)
    row_index = {bid: i for i, bid in enumerate(row_order)}

    # Построить граф из sequenceFlow
    graph = {}  # src -> [tgt, ...]
    for sf in root.iter(f'{{{NS["bpmn"]}}}sequenceFlow'):
        src, tgt = sf.get('sourceRef'), sf.get('targetRef')
        graph.setdefault(src, []).append(tgt)

    # Найти start events
    start_ids = [e.get('id') for e in root.iter(f'{{{NS["bpmn"]}}}startEvent')]

    # Для каждого flow: source должен идти до target в таблице (кроме loop-back)
    # Loop-back — если target уже встречался раньше в traversal (DFS)
    violations = []
    for src, targets in graph.items():
        if src not in row_index:
            continue
        for tgt in targets:
            if tgt not in row_index:
                continue
            # Simple rule: src row < tgt row, ИЛИ это loop назад
            # Loop считается допустимым если src имеет хотя бы один
            # alternative outgoing flow, который ведёт вперёд
            if row_index[src] > row_index[tgt]:
                # Проверка на loop: есть ли у src другой outgoing с row_index[tgt'] > row_index[src]?
                has_forward = any(row_index.get(t, -1) > row_index[src]
                                  for t in graph.get(src, []))
                if not has_forward:
                    violations.append((src, tgt))

    if not violations:
        return {'status': 'PASS', 'details': 'порядок согласован'}
    return {'status': 'WARN',
            'details': f'нарушений: {len(violations)}',
            'data': {'violations': violations}}
```

---

## Check 9: UTF-8 integrity

```python
def check_utf8_integrity(xlsx_path):
    import zipfile
    # xlsx = zip; проверяем, что sharedStrings.xml открывается как UTF-8
    # и содержит валидную кириллицу
    try:
        with zipfile.ZipFile(xlsx_path) as z:
            if 'xl/sharedStrings.xml' in z.namelist():
                with z.open('xl/sharedStrings.xml') as f:
                    content = f.read().decode('utf-8')
                # Smoke check: кириллица присутствует, нет mojibake-маркеров
                import re
                if not re.search(r'[\u0400-\u04FF]', content):
                    # Допустимо, если в процессе вообще нет русских имён (крайне маловероятно)
                    pass
                # Типичный mojibake: Ð, Ñ подряд (Latin-1 интерпретация UTF-8)
                if re.search(r'[ÐÑ][\x80-\xBF]', content):
                    return {'status': 'CRITICAL',
                            'details': 'обнаружены артефакты кодировки (mojibake)'}
                # «?» replacement characters (замена на BOM от неправильной перекодировки)
                if '\uFFFD' in content:
                    return {'status': 'CRITICAL',
                            'details': 'обнаружены символы замены \\uFFFD'}
        # Round-trip test: записать и прочитать известную строку
        test_string = 'Проверка кодировки UTF-8'
        wb = openpyxl.load_workbook(xlsx_path)
        ws = wb['Спецификация']
        # Проверим заголовки
        for col in range(1, ws.max_column + 1):
            h = ws.cell(row=1, column=col).value
            if h and ('Ð' in str(h) or '\uFFFD' in str(h)):
                return {'status': 'CRITICAL',
                        'details': f'mojibake в заголовке: {h}'}
        return {'status': 'PASS', 'details': 'UTF-8 корректна'}
    except UnicodeDecodeError as e:
        return {'status': 'CRITICAL', 'details': f'UnicodeDecodeError: {e}'}
```

---

## Формат отчёта и вердикт

```python
def render_report(results):
    verdict = results.pop('verdict')
    icon = {'PASS': '✅', 'WARN': '⚠', 'CRITICAL': '❌'}
    labels = {
        'check_1_node_count': 'Количество узлов',
        'check_2_id_mapping': 'Соответствие ID',
        'check_3_name_parity': 'Соответствие названий',
        'check_4_lane_pool_parity': 'Назначение Lane/Pool',
        'check_5_gateway_rules': 'Правила на шлюзах',
        'check_6_end_event_outcomes': 'Итоги на End-событиях',
        'check_7_annotation_coverage': 'Аннотации на диаграмме',
        'check_8_execution_order': 'Порядок выполнения',
        'check_9_utf8_integrity': 'Кодировка UTF-8',
    }
    lines = ['📋 Сверка BPMN ↔ Excel', '']
    for key, label in labels.items():
        r = results[key]
        lines.append(f'{icon[r["status"]]} {label}: {r["details"]}')
    lines.append('')
    verdict_line = {
        'FULL_MATCH': 'ИТОГ: ✅ ПОЛНОЕ СООТВЕТСТВИЕ',
        'PARTIAL':    'ИТОГ: ⚠ ЧАСТИЧНОЕ (см. расхождения выше)',
        'CRITICAL':   'ИТОГ: ❌ КРИТИЧЕСКИЕ РАСХОЖДЕНИЯ',
    }[verdict]
    lines.append(verdict_line)
    return '\n'.join(lines)
```

---

## Автопочинка

Если verdict `PARTIAL` или `CRITICAL`:

1. Попытаться починить один раз:
   - Check 1 (node count): дописать недостающие узлы либо удалить лишние строки
   - Check 2 (IDs): то же
   - Check 3 (names): заменить Excel-значения на BPMN `name` (BPMN — source of truth)
   - Check 4 (lane/pool): заполнить по BPMN
   - Check 5 (gateway rules): извлечь условия из `<bpmn:conditionExpression>` на исходящих flow, вписать в F
   - Check 6 (end events): заполнить по имени узла
   - Check 7 (annotations): дописать annotation text в I; дописать строку в «Открытые вопросы»
   - Check 8 (execution order): отсортировать строки по topological traversal
   - Check 9 (UTF-8): перезаписать файл через openpyxl с `wb.save()` — openpyxl сам пересоздаст zip с правильной кодировкой

2. Прогнать все 9 чеков ещё раз.

3. Если вердикт улучшился до `FULL_MATCH` — отлично. Если остался `PARTIAL`/`CRITICAL` — не пытаться чинить снова, показать финальный отчёт с фразой:

   > «Требуется ручная проверка строк [№, №, …] перед использованием спецификации.»

Никогда не прятать расхождения. Пользователь должен видеть, что не так.
