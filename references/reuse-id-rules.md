# Reuse-ID rules (Mixed input / Update scenario)

## Purpose

When Generate mode receives mixed input (text + old .bpmn), the model extracts existing element IDs and preserves them where semantically appropriate.

## Rules

| Case | Action |
|---|---|
| Node from old XML present in new BPMN by meaning (same name, same type) | **Reuse ID** |
| Node renamed (new name, same type, same graph position) | **Reuse ID + diff-summary entry** |
| Node deleted (in old, not in new) | **Drop ID + explicit summary entry** |
| Node added (in new, not in old) | **New ID per naming convention** |
| Node changed type (e.g., `task` → `userTask`) | **DO NOT reuse — new ID + summary entry** |
| ID collision (new ID matches deleted old ID) | **Append `_2` suffix, fail loudly with warning** |

## Diff-summary format

After generation, output a text block (not XLSX in Variant C):

```text
ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО ИСХОДНОГО BPMN:
- Сохранено ID: <N> узлов (<list of IDs>)
- Переименовано (ID сохранены): <N> узлов
  - <Old name> → <New name> (id: <ID>)
- Добавлено новых: <N> узлов
  - <New ID>: <name>, <type>
- Удалено: <N> узлов
  - <Deleted ID>: <name>, <type>
- Тип изменён (новый ID): <N> узлов
  - Old: <Old ID>, <old type> → New: <New ID>, <new type>
```

## Wizard interaction in Update scenario

- Wizard runs only on NEW or CHANGED parts of the process
- Existing facts (from old BPMN) are NOT re-asked
- If user adds a new step but doesn't specify SLA → Wizard asks about SLA only for the new step
- If user renames an existing step → no new questions; ID preserved

## Edge cases

**EC1. Old BPMN has duplicate IDs.** Model MUST treat this as invalid input. Reject with: "Исходный BPMN содержит дубликаты ID: <list>. Исправьте перед обновлением."

**EC2. User explicitly asks to rename an ID.** Honor the request, log in diff-summary as "rename: old_id → new_id".

**EC3. Old BPMN has zeebe namespace.** Reject (per T-201 conflict handling).
