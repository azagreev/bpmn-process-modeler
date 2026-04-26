---
name: bpmn-process-modeler
description: Converts prose, transcripts, notes, process memos, or mixed text + existing BPMN into valid BPMN 2.0 XML for Camunda Platform 7, with Russian labels and optional Excel specification. Use when the user asks to model, draw, map, diagram, convert to BPMN/Camunda/.bpmn/XML, create pools and lanes, export an Excel process table, уточни процесс перед моделированием, обнови существующий BPMN, дополни BPMN, расширь схему, or генерируй с допущениями. The skill classifies input, loads Camunda docs, runs the Wizard when needed, validates XML, asks for approval, then exports a reconciled UTF-8 Excel specification.
version: 2.3.0
snapshot_version: 1.0
snapshot_date: 2026-04-26
snapshot_expiry: 2026-10-23
min_claude_version: "4.6"
requires_mcp: "camunda-docs.mcp.kapa.ai"
runtime: "claude.ai"
---

# BPMN Process Modeler

Turn unstructured prose about a business process into a clean, readable, Camunda-compatible BPMN 2.0 diagram in Russian, and — on user approval — into an Excel specification table reconciled against the diagram.

The skill solves a recurring problem: business analysts and product managers receive process descriptions as meeting transcripts, Confluence pages, or free-form memos. Converting these into executable BPMN by hand is slow and error-prone. The skill automates the hard parts — choosing topology (pools vs lanes vs flat), deciding when to decompose into subprocesses, ensuring the XML imports into Camunda Modeler, keeping labels in Russian, and surfacing open questions on the canvas rather than hiding them.

---

## Primacy — hard rules that never bend

Violating any of these means the deliverable is broken. Treat them as preconditions, not preferences.

1. **Camunda knowledge loaded BEFORE XML generation.** Primary source — call `search_camunda_knowledge_sources` on the Camunda MCP server. Fallback — read `references/camunda-knowledge-snapshot.md` if MCP is unreachable. One of the two MUST succeed before generating any XML. If both fail (extremely rare — missing snapshot in archive), HALT and report the issue.
2. **UTF-8 encoding everywhere.** BPMN XML declaration MUST be `<?xml version="1.0" encoding="UTF-8"?>`. The `.bpmn` file and the `.xlsx` file MUST be saved as UTF-8 without BOM. No cp1251, no UTF-16, no Windows-1251.
3. **Russian for all semantic labels.** Every human-readable `name` attribute (participants, lanes, tasks, events, gateways, flows, subprocesses, annotations) is in Russian. Gateway branch labels («Да/Нет», «Одобрено/Отклонено», «Сумма более 100 000 ₽») are in Russian. Product and brand names stay verbatim (Camunda, SBM, n11, Fibabanka). Technical XML attributes (`id`, `sourceRef`, `targetRef`) remain in Latin per BPMN spec.
4. **No invented BPMN elements.** Every tag must exist in BPMN 2.0. If unsure, consult Camunda docs via the MCP.
5. **DI section is mandatory.** Every flow node, sequence flow, message flow, text annotation, and association has a corresponding `BPMNShape` or `BPMNEdge`. Without DI the diagram renders blank in Camunda Modeler.
6. **Target platform is Camunda 7 (Platform).** All generated XML uses `camunda:*` extensions (not `zeebe:*`). Do not ask the user which platform — it is fixed. If the user explicitly mentions Camunda 8 or Zeebe, tell them this skill generates C7 XML only and offer to continue on that basis.
7. **Open questions live on the canvas.** When the input is ambiguous, attach a `<textAnnotation>` with prefix «⚠ Уточнить:» to the relevant node. Never bury open questions in XML comments — the reviewer must see them on the diagram.
8. **Excel export requires explicit approval.** Never generate the `.xlsx` before the user confirms the diagram. Always end Step 7 with the approval question.
9. **Excel is not presented before reconciliation.** After saving the workbook, run 9-check reconciliation against the BPMN and report status to the user BEFORE calling `present_files`.

---

## The workflow — Generate mode in fixed order

### Step 0 — Input classification

Classify the user input before loading Camunda knowledge or generating XML. Use
`references/input-classification.md` as the routing source of truth.

Route pure text to Generate, mixed text + BPMN/XML to Generate with reuse-ID,
Camunda 8 / `zeebe:*` XML to REJECT with Diagram Converter guidance, unsupported
formats to REJECT, and invalid XML to RECOVER or REJECT with the parse error.

#### Update scenario (mixed input)

When Step 0 detects mixed input (text + .bpmn), workflow becomes:

1. Step 0: detected as mixed input
2. Reuse-ID extraction: parse old BPMN, build ID index
3. Step 1: Camunda knowledge load (unchanged)
4. Step 1.5: Wizard runs only on new/changed parts (per `references/reuse-id-rules.md`)
5. Steps 2-9: generate new BPMN preserving existing IDs where appropriate
6. Output:
   - Final BPMN (with reused + new IDs)
   - Excel spec (per existing template, +«Допущения» sheet if applicable)
   - Diff-summary text block (see reuse-id-rules.md)

**Cross-references:**
- `references/reuse-id-rules.md` — full ID reuse rules
- `references/clarification-wizard.md` — Wizard behavior in Update scenario

### Step 1 — Load current Camunda documentation (with fallback)

Before producing any BPMN XML, acquire Camunda knowledge. Try in order:

If `snapshot_date > snapshot_expiry`, warn user.

**Option A — Live MCP (preferred).** Call `search_camunda_knowledge_sources` on the Camunda MCP server. Run at minimum these four queries, plus one domain-specific query derived from the input:

1. `BPMN 2.0 XML elements Camunda executable attributes`
2. `BPMN collaboration pools lanes message flow syntax`
3. `BPMN subprocess expanded collapsed BPMNDI layout`
4. `BPMN text annotation association syntax`
5. Domain-specific — for fintech: `BPMN payment authorization compensation`; for e-commerce: `BPMN order fulfillment`; adjust per detected industry.

At top of generated XML:
```xml
<!-- Camunda knowledge: MCP (live, date=YYYY-MM-DD), queries: <source_1>, <source_2>, ... -->
```

**Option B — Snapshot fallback.** If MCP is not reachable (tool call fails or returns no response), read `references/camunda-knowledge-snapshot.md`. Proceed with it as the source of truth for Camunda 7 syntax, extension elements, DI rules, and best practices.

At top of generated XML:
```xml
<!-- Camunda knowledge: snapshot v1.0 (2026-04-26), MCP unavailable. Before prod deploy, verify critical elements against live docs. -->
```

**Option C — HALT (extremely rare).** If neither MCP nor snapshot available (snapshot file missing from archive — indicates a broken installation):

> «Camunda MCP недоступен, и локальный knowledge snapshot не найден. Проверьте установку скилла (Settings → Capabilities → Skills → переустановите архив) и активацию Camunda MCP (Settings → Connectors, URL: https://camunda-docs.mcp.kapa.ai).»

**In degraded mode (Option B):** proceed with the full workflow (Steps 2-9) as normal, but flag the degraded status in Step 7 approval prompt (see Step 7).

### Step 1.5 — Clarification Wizard

Run the Wizard after Camunda knowledge is available and before parsing the
process into BPMN elements. Use `references/clarification-wizard.md` as the
source of truth.

Branching:
- If 0 missing facts are detected: skip Wizard, inform user "Всё понятно, перехожу к генерации", proceed to Step 2.
- If 1-5 missing facts are detected: ask targeted questions in priority order, then proceed to Step 2.
- If 6+ missing facts are detected: offer more detail or "with assumptions" mode, then proceed to Step 2.

Assumption mode trigger phrases include "делай с допущениями", "генерируй с предположениями", "не задавай вопросов", "as is", "as-is", and "just do it".

#### Discipline rules for Wizard (Step 1.5)

**Do NOT:**
- Ask questions when answer is in the source text (anti-hallucination)
- Mark as `⚠ Допущение:` what is trivially derivable (e.g., task type from verb)
- Ask more than 5 questions in one pass
- Skip Wizard silently — always inform user "Всё понятно, перехожу к генерации"

**Do:**
- Detect all 6 categories before deciding routing
- Respect priority order (topology first, data_ownership last)
- Use category default if user skips ("не знаю / пропустить")
- Mark every accepted assumption with `⚠ Допущение:` annotation + Excel row

### Step 2 — Parse and classify the input

Extract and state explicitly before modeling:

- **Industry / domain** — pick one from the table below. If the input matches several, pick the best fit and mark the others in assumptions.
- **Participants** — every actor, role, system, external organization. Deduplicate. Classify each as internal-role / external-org / system.
- **Activities** — classify each as User Task, Service Task, Manual Task, Send Task, Receive Task, Business Rule Task, or Script Task.
- **Events** — start (triggers: message, timer, signal, conditional), intermediate (timer, message, error, escalation, signal), end (one per distinct outcome — success, rejection, cancellation, compensation).
- **Gateways** — exclusive (XOR), parallel (AND), inclusive (OR), event-based. Derive from conditional language: «если», «в зависимости от», «параллельно», «одновременно», «либо…либо», «пока не», «как только».
- **Artifacts** — documents, data objects, messages exchanged between participants.

After domain is identified, read the matching industry-patterns file for domain-specific processes and compliance annotations:

| Detected domain | Read this reference file |
|---|---|
| fintech / banking / wallet / payments / lending / BNPL / leasing / factoring / merchant services / regulatory reporting | `references/industry-patterns/fintech-patterns.md` |
| e-commerce / marketplace / logistics / fulfillment / seller journey / cross-border retail | `references/industry-patterns/marketplace-patterns.md` |
| project finance / construction lending / retail mortgage / SPV financing / infrastructure / workout loans | `references/industry-patterns/project-finance-patterns.md` |
| healthcare / medical / pharma | `references/industry-patterns/healthcare-patterns.md` |
| manufacturing / production / MES | `references/industry-patterns/manufacturing-patterns.md` |
| HR / employee onboarding / leave / compensation | `references/industry-patterns/hr-patterns.md` |
| public sector / government services / МФЦ / Госуслуги | `references/industry-patterns/public-sector-patterns.md` |
| IT ops / incident management / change management / SRE | `references/industry-patterns/it-ops-patterns.md` |

Read only the matching file — do not load all industry references at once. If no file matches the detected domain, proceed with generic BPMN patterns from `bpmn-patterns.md` alone.

### Step 3 — Choose topology by rule

Decide by structure, not by feel:

| Condition | Topology |
|---|---|
| ≥ 2 distinct organizations exchanging messages (buyer ↔ seller ↔ bank) | Collaboration with multiple pools + message flows between pools |
| 1 organization, ≥ 2 internal roles/departments | Single pool, multiple lanes |
| 1 actor/system, no role handoffs | Flat process (single `<process>`, no pool/lane) |

State the chosen topology and the one-sentence reason before producing XML.

### Step 4 — Choose decomposition by rule

Apply the 7 ± 2 readability rule:

- If flat process would contain > 9 flow nodes OR > 2 levels of gateway nesting → **hierarchical**:
  - **Level 0 (overview)**: 3 to 7 collapsed subprocesses (`<subProcess>` with `BPMNShape isExpanded="false"`), each representing a phase.
  - **Level 1 (drill-down)**: one expanded diagram per collapsed subprocess, showing detailed tasks, events, and gateways.
- Otherwise → **flat single diagram**. State explicitly: «Иерархическая декомпозиция не нужна — процесс укладывается в один уровень.»

For hierarchical models, deliver the Level 0 diagram first, then each Level 1 subprocess. Each level gets its own `<process>` element in the same BPMN file (preferred) or a separate `.bpmn` file if collaboration topology forces it.

### Step 5 — Generate BPMN 2.0 XML

Read [references/bpmn-patterns.md](references/bpmn-patterns.md) for ready-made XML snippets for common patterns (approval loop, 4-eyes, parallel review, timer escalation, compensation, B2B message exchange).

Read [references/annotation-style-guide.md](references/annotation-style-guide.md) for when to use `<textAnnotation>` vs renaming the node, and Russian phrasing templates for SLA, regulatory, business-rule, integration, and open-question callouts.

Mandatory elements in every XML:

- Full namespace declarations: `bpmn`, `bpmndi`, `dc`, `di`, `camunda`
- `isExecutable="true"` on executable processes
- Complete `<bpmndi:BPMNDiagram>` with coordinates for every flow node, sequence/message flow, text annotation, and association
- Unique IDs following the convention: `Activity_<verb>`, `Gateway_<decision>`, `Event_<trigger>`, `Flow_<from>_<to>`, `Participant_<org>`, `Lane_<role>`, `TextAnnotation_<n>`, `Association_<n>`
- `name` attributes in Russian on every semantic element
- Before attaching Camunda extensions, choose the BPMN task type by real business semantics. A mismatch between task type and extensions causes `unknown attribute` warnings in Camunda Modeler.

| Semantics | BPMN type | Allowed `camunda:*` attributes |
|---|---|---|
| Human performs the work by hand, approves, checks, signs, or sends email manually | `userTask` | `assignee`, `candidateUsers`, `candidateGroups`, `dueDate`, `followUpDate`, `formKey`, `priority` |
| Automatic message send to an external participant | `sendTask` | `camunda:type="external"` + `camunda:topic`, `camunda:class`, `camunda:delegateExpression`, `camunda:expression`, `camunda:resultVariable` |
| Automated service / integration / internal processing | `serviceTask` | `camunda:type="external"` + `camunda:topic`, `camunda:class`, `camunda:delegateExpression`, `camunda:expression`, `camunda:resultVariable` |
| DMN decision | `businessRuleTask` | `camunda:decisionRef`, `camunda:resultVariable`, `camunda:mapDecisionResult` |
| Inline script | `scriptTask` | `scriptFormat` + inline `<script>` or `camunda:resource` |
| Wait for an incoming message | `receiveTask` | assignment-style attributes are not used |

**Anti-pattern:** `camunda:candidateGroups` on `sendTask`. If the action is performed by a human via Tasklist, model it as `userTask`, not `sendTask`.

**Naming and granularity rules (prevent unreadable diagrams):**

1. Task names should be 2-4 words, infinitive + object. Put long explanations into `<bpmn:documentation>`.
2. Never change BPMNShape size just to fit long text.
   - `userTask` / `serviceTask` / `sendTask`: `100x80`
   - event: `36x36`
   - gateway: `50x50`
   - collapsed `subProcess`: `100x80`
3. Granularity is one task = one action. Decompose compound tasks joined by "and".
4. Expand abbreviations in lane names and glossary annotations.
5. Put source details and regulatory context into `<bpmn:documentation>`.
6. Use `<bpmn:textAnnotation>` for cross-cutting rules, constraints, and `⚠ Уточнить` notes.

**Camunda 7 extensions where applicable:**
  - User tasks: `camunda:assignee` or `camunda:candidateUsers` or `camunda:candidateGroups`
  - Service tasks (external worker pattern): `camunda:type="external"` + `camunda:topic`
  - Service tasks (internal Java): `camunda:delegateExpression` or `camunda:class` or `camunda:expression`
  - Business rule tasks: `camunda:decisionRef` + `camunda:resultVariable`
  - Script tasks: `scriptFormat` attribute + inline `<script>` body, or `camunda:resource`

Target platform is Camunda 7 (Platform) — do not generate `zeebe:*` extensions.

### Step 6 — Validate the XML

Run all 7 blocking checks and the optional best practices, output an explicit pass/fail table. See [references/validation-checklist.md](references/validation-checklist.md) for the full procedure with examples of each failure mode and its fix.

| # | Check | What it verifies |
|---|---|---|
| 1 | Well-formedness | XML parses without error; proper XML declaration; escaped special chars or CDATA in FEEL expressions |
| 2 | BPMN schema conformance | Every element valid per BPMN 2.0 XSD; no invented tags; no C7/C8 namespace mixing; `targetNamespace` set |
| 3 | Structural integrity | sequenceFlow refs exist; ≥ 1 start and ≥ 1 end event per process; all paths reach an end; gateway fan-in/fan-out matches semantics; no uncontrolled loops; all error/message/signal/escalation references resolve; boundary events attach correctly; no duplicate IDs; subprocess types consistent (embedded vs event subprocess); data objects/references connected |
| 4 | Message flows и Collaboration | Message flows cross pool boundaries only; participants link to processes correctly; lane flowNodeRef membership consistent |
| 5 | Camunda 7 executability | User tasks have assignee/candidateUsers/candidateGroups; send/service tasks have type+topic or delegateExpression/class/expression; businessRuleTask has decisionRef; callActivity has calledElement; timer events have ISO 8601 / cron; FEEL reserved words not used as variable names; multi-instance has inputCollection; conditional events have condition expression; negative check: assignment attributes stay on userTask, technical attributes stay on serviceTask/sendTask/businessRuleTask/scriptTask |
| 6 | DI completeness | Every flow node has BPMNShape; every flow has BPMNEdge with ≥ 2 waypoints; shapes follow standard sizes; `isHorizontal="true"` on pools/lanes; `isMarkerVisible="true"` on XOR gateways; labels positioned |
| 7 | Language conformance | Every `name` attribute in Russian (whitelist of abbreviations/brands exempt); no English leftovers like «Start», «End», «Approved» |

If any blocking check (1-7) fails → fix the XML → re-run all checks. Loop until all 7 pass.

**Optional best practices (WARN, не блокируют):** 11 additional recommendations and checks — see validation-checklist.md sections 8-18 for details.

### Step 7 — Present to the user and ask for approval

Output in this exact order:

1. **Classification summary** — 5 to 10 bullets in Russian: industry, participants, topology + reason, decomposition + reason, key assumptions, Camunda platform target.
2. **BPMN XML** — in a code block. If hierarchical, multiple blocks clearly labeled `overview.bpmn`, `subprocess_<name>.bpmn`.
3. **Validation report** — the 7-check pass/fail table.
4. **Open questions** — what the input did not specify and was assumed (deadlines, error paths, escalation, data ownership, retry policy). Cross-reference each to its «⚠ Уточнить» annotation ID in the XML.
5. **Degraded-mode warning (ONLY if Step 1 used snapshot fallback, Option B).** Insert before the approval prompt:

   > ⚠ **Внимание:** Camunda MCP был недоступен в этой сессии. Диаграмма сгенерирована на основе локального snapshot от 2026-04-26. Перед деплоем в prod рекомендуется: (1) активировать MCP и перегенерировать XML, либо (2) открыть XML в Camunda Modeler 7.x и довериться его валидатору, либо (3) вручную пройтись по `validation-checklist.md` Check 5 (Camunda executability).

6. **Approval prompt** — end the message with this exact question (verbatim):

> **Схема корректна? После подтверждения могу выгрузить спецификацию процесса в Excel-таблицу.**

### Step 8 — Excel export (only after explicit user approval)

Gate: do nothing until the user confirms. Triggers for proceeding: «да», «ок», «утверждено», «выгружай», «сделай таблицу», or equivalent. If the user requests edits instead, loop back to Step 5 → Step 6 → Step 7.

When approved, invoke the `xlsx` skill at `/mnt/skills/public/xlsx/SKILL.md`. If it is not available, fall back to `openpyxl` directly.

Read [references/excel-spec-template.md](references/excel-spec-template.md) for the 9-column template, per-column rules, the mapping from BPMN element type to row content, and a worked example on a BNPL approval process.

**Encoding:** workbook saved as UTF-8 (native to `.xlsx` — verify by reading back a known Cyrillic string round-trips byte-for-byte). No BOM in shared strings. If any `UnicodeDecodeError` or `UnicodeEncodeError` occurs, HALT and report the offending cell.

**Output path:** `/mnt/user-data/outputs/<process_name>_specification.xlsx`.

Do NOT call `present_files` yet — proceed to Step 9 first.

### Step 9 — Reconcile Excel spec against the BPMN diagram

After the workbook is saved, reopen it from disk with `openpyxl` and reconcile against the source BPMN XML. This is a hard step — the file is not presented to the user until reconciliation runs and its status is reported.

Read [references/reconciliation-procedure.md](references/reconciliation-procedure.md) for the full algorithm with Python code stubs for each check.

The 9 reconciliation checks:

1. **Node count parity** — rows in «Спецификация» sheet = flow nodes in BPMN (start events + intermediate events + end events + tasks + gateways + subprocesses). Sequence and message flows are NOT counted as rows.
2. **ID-level mapping** — every BPMN flow node `id` appears in the Excel (via hidden `_BPMN_ID` column or via exact Название + Тип match). Report missing IDs in both directions.
3. **Name parity** — Excel «Название элемента» equals BPMN `name` attribute byte-for-byte (whitespace-normalized).
4. **Lane/Pool parity** — Excel «Участник» matches the BPMN `<lane>` + `<participant>` assignment.
5. **Gateway decision rule present** — every row whose «Тип элемента» is a gateway has a non-empty «Описание / Бизнес-правила» that references the outgoing flow conditions.
6. **End event outcome coverage** — every BPMN `endEvent` has a row with populated «Выходные данные / Результат».
7. **Annotation coverage** — every `<textAnnotation>` attached to a flow node is reflected in the «Примечания» column; every «⚠ Уточнить» appears on sheet «Открытые вопросы».
8. **Execution order sanity** — row № follows a valid topological traversal from start event (no row references a node whose predecessor has a higher №, except on explicit loops).
9. **UTF-8 integrity** — re-read the file and assert a known Cyrillic sample round-trips intact. No mojibake («Ð‰Ð°Ð¹»), no «?» replacement chars.

**Status report — output BEFORE `present_files`, in this exact format (Russian):**

```
📋 Сверка BPMN ↔ Excel

✅/❌ Количество узлов:              BPMN=<N>, Excel=<M>
✅/❌ Соответствие ID:               <k> совпало, <a> только в BPMN, <b> только в Excel
✅/❌ Соответствие названий:         <k> совпало, <d> расхождений
✅/❌ Назначение Lane/Pool:          <k> совпало, <e> расхождений
✅/❌ Правила на шлюзах:             <k>/<total_gateways> заполнено
✅/❌ Итоги на End-событиях:         <k>/<total_end_events> заполнено
✅/❌ Аннотации на диаграмме:        <k>/<total_annotations> перенесено
✅/❌ Порядок выполнения:            согласован / нарушен на шагах [№, №]
✅/❌ Кодировка UTF-8:               корректна / обнаружены артефакты

ИТОГ: ✅ ПОЛНОЕ СООТВЕТСТВИЕ | ⚠ ЧАСТИЧНОЕ (см. расхождения выше) | ❌ КРИТИЧЕСКИЕ РАСХОЖДЕНИЯ
```

**On failure:**

- Try one automatic correction (re-populate missing cells, fix encoding, re-order rows). Re-run all 9 checks.
- If failure persists, present the file WITH the failure report and an explicit recommendation:
  > «Требуется ручная проверка строк [№, №, …] перед использованием спецификации.»
- Never silently hide a discrepancy.

**After reconciliation:** call `present_files` with the `.xlsx` path. End with:

> «Спецификация готова. Статус сверки — см. выше. Нужны изменения?»

---

## Reference files — read when needed

Do not load all references at once. Read only the one you need for the current step.

| File | Read when |
|---|---|
| [references/camunda-knowledge-snapshot.md](references/camunda-knowledge-snapshot.md) | At Step 1 — if Camunda MCP is unreachable. Fallback with curated BPMN 2.0 + Camunda 7 knowledge (root structure, tasks, events, gateways, subprocesses, DI, text annotations, best practices) |
| [references/bpmn-patterns.md](references/bpmn-patterns.md) | At Step 5 — writing XML; need a pattern for approval loop, 4-eyes, parallel review, timer escalation, compensation, or B2B message exchange |
| `references/industry-patterns/*.md` | At Step 2 — after domain is classified. See the domain → file table in Step 2 for routing. Read only the matching file. |
| [references/annotation-style-guide.md](references/annotation-style-guide.md) | At Step 5 — deciding between renaming a node vs adding a text annotation, or phrasing an annotation in Russian |
| [references/validation-checklist.md](references/validation-checklist.md) | At Step 6 — running the 7 validation checks and fixing failures |
| [references/excel-spec-template.md](references/excel-spec-template.md) | At Step 8 — building the 9-column specification sheet, looking up the worked BNPL example |
| [references/reconciliation-procedure.md](references/reconciliation-procedure.md) | At Step 9 — running the 9 reconciliation checks with Python/openpyxl |

---

## Why the structure is this way

The skill is long because process-to-BPMN is a workflow, not a question. The value comes from doing the right steps in the right order — docs first, then classification, then topology and decomposition, then XML, then validation, then approval, then Excel, then reconciliation. Skipping any step produces a deliverable that looks right but fails when the user opens it in Camunda Modeler or spots a row in the Excel that does not match the diagram.

The language rule (Russian for labels) is not stylistic — the user is a Russian-speaking product manager whose business analysts and stakeholders read the diagram. English labels mean extra translation work downstream and mistakes in regulatory communication. Keeping product/brand names verbatim (Camunda, SBM, n11, Fibabanka) avoids translating proper nouns into awkward Russian.

Open questions on the canvas (not in XML comments) is the single most important UX decision — reviewers look at the diagram, not at the source. A question hidden in a comment gets lost; a question on the canvas gets answered.

Reconciliation before presenting the Excel exists because a spec table that drifts from the diagram is worse than no table — it creates false confidence. The 9 checks are cheap; the cost of a wrong spec in production is high.
