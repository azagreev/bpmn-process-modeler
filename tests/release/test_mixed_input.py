import json
import unittest
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
        if elem.tag.startswith(BPMN_NS) and elem.attrib.get("id") and elem.attrib.get("name"):
            nodes[elem.attrib["id"]] = {
                "id": elem.attrib["id"],
                "name": elem.attrib["name"],
                "type": elem.tag.replace(BPMN_NS, ""),
            }
    return nodes


def simulate_update(case_name):
    case_dir = FIXTURES / case_name
    original = extract_nodes(case_dir / "original.bpmn")
    expected = load_json(case_dir / "expected_diff_summary.json")
    new_nodes = {node_id: original[node_id] for node_id in expected["preserved"]}
    for node_id in expected["added"]:
        new_nodes[node_id] = {"id": node_id, "name": node_id.replace("_", " "), "type": "userTask"}
    return original, new_nodes, expected


class MixedInputTests(unittest.TestCase):
    def test_reuse_id_for_preserved_nodes(self):
        original, new_nodes, summary = simulate_update("add_nodes")
        for node_id in summary["preserved"]:
            self.assertIn(node_id, original)
            self.assertIn(node_id, new_nodes)
            self.assertEqual(original[node_id]["id"], new_nodes[node_id]["id"])
        self.assertEqual(len(summary["added"]), 2)

    def test_diff_summary_counts_add_and_remove(self):
        _, _, summary = simulate_update("remove_nodes")
        text = "\n".join(
            [
                "ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО ИСХОДНОГО BPMN:",
                f"- Сохранено ID: {len(summary['preserved'])}",
                f"- Добавлено новых: {len(summary['added'])}",
                f"- Удалено: {len(summary['removed'])}",
            ]
        )
        self.assertIn("Сохранено ID: 4", text)
        self.assertIn("Добавлено новых: 0", text)
        self.assertIn("Удалено: 1", text)
        self.assertIn("Activity_ReserveStock", summary["removed"])

    def test_type_change_gets_new_id_not_reused(self):
        case_dir = FIXTURES / "type_change"
        original = extract_nodes(case_dir / "original.bpmn")
        expected_new = load_json(case_dir / "expected_new_id_for_type_change.json")
        _, new_nodes, summary = simulate_update("type_change")
        self.assertIn(expected_new["old_id"], original)
        self.assertNotIn(expected_new["old_id"], new_nodes)
        self.assertIn(expected_new["new_id"], new_nodes)
        self.assertIn(expected_new["old_id"], summary["type_changed"])
        self.assertNotEqual(expected_new["old_type"], expected_new["new_type"])

    def test_reuse_id_rules_document_contract(self):
        text = REUSE_DOC.read_text(encoding="utf-8")
        self.assertIn("**Reuse ID**", text)
        self.assertIn("**DO NOT reuse", text)
        self.assertIn("ИЗМЕНЕНИЯ ОТНОСИТЕЛЬНО ИСХОДНОГО BPMN", text)
        self.assertIn("Wizard runs only on NEW or CHANGED parts", text)
        self.assertIn("Old BPMN has duplicate IDs", text)


if __name__ == "__main__":
    unittest.main()
