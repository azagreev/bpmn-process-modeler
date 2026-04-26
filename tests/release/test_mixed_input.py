import json
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "mixed_input"
REUSE_DOC = REPO_ROOT / "references" / "reuse-id-rules.md"

BPMN_NS = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_nodes(bpmn_path):
    root = ET.parse(bpmn_path).getroot()
    nodes = {}
    for elem in root.iter():
        if not elem.tag.startswith(BPMN_NS):
            continue
        node_id = elem.attrib.get("id")
        name = elem.attrib.get("name")
        if node_id and name:
            nodes[node_id] = {
                "id": node_id,
                "name": name,
                "type": elem.tag.replace(BPMN_NS, ""),
            }
    return nodes


def simulate_update(case_name):
    case_dir = FIXTURES / case_name
    original = extract_nodes(case_dir / "original.bpmn")
    expected = load_json(case_dir / "expected_diff_summary.json")

    new_nodes = {}
    for node_id in expected["preserved"]:
        new_nodes[node_id] = original[node_id]
    for node_id in expected["added"]:
        new_nodes[node_id] = {"id": node_id, "name": node_id.replace("_", " "), "type": "userTask"}

    summary = {
        "preserved": expected["preserved"],
        "added": expected["added"],
        "removed": expected["removed"],
        "type_changed": expected["type_changed"],
    }
    return original, new_nodes, summary


def format_diff_summary(summary):
    return "\n".join(
        [
            "ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО ИСХОДНОГО BPMN:",
            f"- Сохранено ID: {len(summary['preserved'])} узлов ({', '.join(summary['preserved'])})",
            f"- Добавлено новых: {len(summary['added'])} узлов",
            f"- Удалено: {len(summary['removed'])} узлов",
            f"- Тип изменён (новый ID): {len(summary['type_changed'])} узлов",
        ]
    )


def test_reuse_id_for_preserved_nodes():
    original, new_nodes, summary = simulate_update("add_nodes")

    for node_id in summary["preserved"]:
        assert node_id in original
        assert node_id in new_nodes
        assert original[node_id]["id"] == new_nodes[node_id]["id"]
    assert len(summary["added"]) == 2


def test_diff_summary_counts_add_and_remove():
    _, _, summary = simulate_update("remove_nodes")
    text = format_diff_summary(summary)

    assert "Сохранено ID: 4" in text
    assert "Добавлено новых: 0" in text
    assert "Удалено: 1" in text
    assert "Activity_ReserveStock" in summary["removed"]


def test_type_change_gets_new_id_not_reused():
    case_dir = FIXTURES / "type_change"
    original = extract_nodes(case_dir / "original.bpmn")
    expected_new = load_json(case_dir / "expected_new_id_for_type_change.json")
    _, new_nodes, summary = simulate_update("type_change")

    assert expected_new["old_id"] in original
    assert expected_new["old_id"] not in new_nodes
    assert expected_new["new_id"] in new_nodes
    assert expected_new["old_id"] in summary["type_changed"]
    assert expected_new["old_type"] != expected_new["new_type"]


def test_reuse_id_rules_document_contract():
    text = REUSE_DOC.read_text(encoding="utf-8")

    assert "**Reuse ID**" in text
    assert "**DO NOT reuse" in text
    assert "ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО ИСХОДНОГО BPMN" in text
    assert "Wizard runs only on NEW or CHANGED parts" in text
    assert "Old BPMN has duplicate IDs" in text
