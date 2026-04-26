# Input classification (Step 0)

## 1. Purpose

Classify user input before generation into one of 5 routing scenarios for v2.3.0.

Step 0 runs before Camunda knowledge loading and before any BPMN XML is generated.
It decides whether the skill can continue in Generate mode, should continue with
reuse-ID behavior, or must reject the input with a clear explanation.

Variant C keeps a single Generate mode. Validate and Fix are intentionally deferred
to v2.4.0, so Step 0 never routes into a separate Validate or Fix workflow.

## 2. Detection heuristics

### 2.1 Pure text

Pure text is the default scenario for a new BPMN model.

Signals:
- No `<?xml` marker in the input
- No `<bpmn:` marker in the input
- No attached file with `.bpmn` extension
- Input is prose, transcript, notes, or a written process description

### 2.2 Mixed input (text + BPMN)

Mixed input means the user provided an existing BPMN/XML model and a prose request
to update or extend it.

Signals:
- Input contains `<?xml` or `<bpmn:` markers AND more than 2 sentences of plain text
- OR `.bpmn` file attached plus text body
- OR trigger phrases in the user request:
  - `обнови`
  - `дополни`
  - `измени`
  - `расширь существующий`

Routing result: Generate with reuse-ID.

### 2.3 zeebe namespace (Camunda 8)

Zeebe/Camunda 8 XML is outside the scope of this skill because the target platform
is fixed to Camunda 7.

Signals:
- XML contains `xmlns:zeebe=`
- OR root element has `zeebe:*` attributes
- OR BPMN elements use Zeebe extension elements

Routing result: REJECT.

Required response:

```text
Skill generates Camunda 7. Use Camunda Diagram Converter for C7->C8 migration:
https://docs.camunda.io/docs/guides/migrating-from-camunda-7/migration-tooling/diagram-converter/
```

### 2.4 Unsupported format

Unsupported binary or diagramming formats must be rejected before attempting BPMN
generation.

Signals:
- File extension in: `.drawio`, `.vsdx`, `.png`, `.jpg`, `.pdf`
- OR binary file headers are detected, for example PNG or PDF magic bytes
- OR the file is an image/screenshot rather than BPMN XML

Routing result: REJECT.

Required response:

```text
Format not supported. Supported: text process descriptions, .bpmn / XML files.
```

### 2.5 Invalid XML

Invalid XML applies when the input appears to contain BPMN/XML, but parsing fails.

Signals:
- XML parsing fails
- BPMN is truncated or malformed
- Closing tags are missing
- Namespace declarations are broken

Routing result: RECOVER or REJECT.

Recovery rule:
- Try to recover well-formed XML only when the fix is obvious and local
- If recovery is uncertain, reject with the parse error message
- Do not invent missing BPMN content during recovery

### 2.6 Mixed input (text + BPMN, Update scenario)

**Detection:**
- User message contains `<?xml` or `<bpmn:` markers
- AND has more than 2 sentences of plain text outside the XML block
- OR `.bpmn` file attached plus text body
- OR explicit trigger phrases: `обнови`, `дополни`, `измени`, `расширь существующий`

**Routing:**
- Mixed input → Generate with reuse-ID → Wizard (if missing facts in additions)

**Conflict handling:**
- User provided XML but did not say "update" → in Variant C, default to Generate with reuse-ID (no Validate/Fix prompt)
- User provided XML AND said "validate" or "fix" → inform user about Variant C limitations, route to Generate with reuse-ID

## 3. Routing rules

| Signal | Mode | Notes |
|---|---|---|
| Pure text | Generate | Pass through Wizard |
| Mixed input | Generate with reuse-ID | Pass through Wizard for new/changed parts only |
| zeebe namespace | REJECT | Output Camunda Diagram Converter guidance |
| Unsupported format | REJECT | Output supported input formats |
| Invalid XML | RECOVER or REJECT | Try well-formed recovery; otherwise reject with parse error |

Priority order when multiple signals are present:

1. Empty input wins over all other signals.
2. Unsupported binary format wins over XML heuristics.
3. Zeebe namespace wins over mixed input.
4. Invalid XML wins over mixed input.
5. Mixed input wins over pure text.

## 4. Edge cases

### 4.1 Empty input

Reject with:

```text
Empty input. Provide a process description or BPMN file.
```

### 4.2 XML without explicit "update" trigger

In Variant C, route to Generate with reuse-ID by default. Do not ask whether the
user wants Validate or Fix mode because these modes are not implemented in v2.3.0.

### 4.3 Multiple .bpmn files attached

Accept only the first `.bpmn` file. Warn that all other BPMN files are ignored.

### 4.4 Text mentions "validate" or "fix"

In Variant C, these capabilities are not yet implemented. Inform the user and
route to Generate with reuse-ID when BPMN/XML is present.

Required response pattern:

```text
Validate/Fix mode is planned for v2.4.0. In v2.3.0 I can regenerate the BPMN
with reuse-ID rules and preserve existing IDs where appropriate.
```

### 4.5 Plain text with update verbs but no BPMN

If the user says `обнови` or `дополни` but provides no BPMN/XML, treat the input
as pure text Generate. Mention that no existing IDs can be preserved because no
source BPMN was provided.
