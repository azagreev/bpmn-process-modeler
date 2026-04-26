import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "references" / "input-classification.md"
DIAGRAM_CONVERTER_URL = (
    "https://docs.camunda.io/docs/guides/migrating-from-camunda-7/"
    "migration-tooling/diagram-converter/"
)


def classify_input(input_text="", filename=None, binary_header=b""):
    text = input_text or ""
    filename = filename or ""
    lower_name = filename.lower()
    lower_text = text.lower()

    if not text.strip() and not filename and not binary_header:
        return {"mode": "reject", "reason": "Empty input", "has_xml": False, "mixed": False, "reuse_id": False}

    if lower_name.endswith((".drawio", ".vsdx", ".png", ".jpg", ".pdf")) or binary_header.startswith((b"\x89PNG", b"%PDF")):
        return {"mode": "reject", "reason": "unsupported format", "has_xml": False, "mixed": False, "reuse_id": False}

    has_xml = "<?xml" in text or "<bpmn:" in text or lower_name.endswith(".bpmn")
    if "xmlns:zeebe=" in text or "zeebe:" in text:
        return {"mode": "reject", "reason": f"Diagram Converter: {DIAGRAM_CONVERTER_URL}", "has_xml": True, "mixed": False, "reuse_id": False}

    if has_xml and text.strip().startswith("<?xml"):
        try:
            ET.fromstring(text)
        except ET.ParseError as exc:
            return {"mode": "reject", "reason": f"parse error: {exc}", "has_xml": True, "mixed": False, "reuse_id": False}

    update_triggers = ("обнови", "дополни", "измени", "расширь существующий")
    has_update_trigger = any(trigger in lower_text for trigger in update_triggers)
    plain_text_sentences = [part for part in text.replace("\n", " ").split(".") if part.strip()]
    mixed = (has_xml and len(plain_text_sentences) > 2) or (has_xml and has_update_trigger)

    if mixed or has_xml:
        return {"mode": "generate", "reason": "mixed input", "has_xml": True, "mixed": True, "reuse_id": True}
    return {"mode": "generate", "reason": "pure text", "has_xml": False, "mixed": False, "reuse_id": False}


class InputClassificationTests(unittest.TestCase):
    def test_step0_routing_cases(self):
        cases = [
            ("Опишу процесс одобрения заявки клиентом и менеджером банка.", None, b"", "generate", {"has_xml": False, "mixed": False, "reuse_id": False}),
            ("Обнови процесс. Добавь проверку. Сохрани ID. <?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>", None, b"", "generate", {"has_xml": True, "mixed": True, "reuse_id": True}),
            ("<?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL' xmlns:zeebe='http://camunda.org/schema/zeebe/1.0'/>", None, b"", "reject", {"has_xml": True}),
            ("diagram.drawio", "diagram.drawio", b"", "reject", {"has_xml": False}),
            ("process.vsdx", "process.vsdx", b"", "reject", {"has_xml": False}),
            ("", "screen.png", b"\x89PNG\r\n\x1a\n", "reject", {"has_xml": False}),
            ("<?xml version='1.0'?><bpmn:definitions>", None, b"", "reject", {"has_xml": True}),
            ("", None, b"", "reject", {"has_xml": False, "mixed": False, "reuse_id": False}),
            ("Нужно расширить схему. Добавить путь. Сохранить элементы. <?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>", None, b"", "generate", {"has_xml": True, "mixed": True, "reuse_id": True}),
            ("дополни <?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>", None, b"", "generate", {"has_xml": True, "mixed": True, "reuse_id": True}),
        ]
        for input_text, filename, header, expected_mode, expected_attrs in cases:
            with self.subTest(input_text=input_text[:40], filename=filename):
                result = classify_input(input_text, filename=filename, binary_header=header)
                self.assertEqual(result["mode"], expected_mode)
                for key, expected in expected_attrs.items():
                    self.assertEqual(result[key], expected)

    def test_negative_variants_and_reference_contract(self):
        self.assertFalse(classify_input("Смоделируй процесс.")["reuse_id"])
        zeebe = classify_input("<?xml version='1.0'?><bpmn:definitions xmlns:zeebe='http://camunda.org/schema/zeebe/1.0'/>")
        self.assertEqual(zeebe["mode"], "reject")
        self.assertIn("Diagram Converter", zeebe["reason"])
        self.assertEqual(classify_input(filename="process.bpmn")["mode"], "generate")

        text = DOC_PATH.read_text(encoding="utf-8")
        for section in ("Purpose", "Detection heuristics", "Routing rules", "Edge cases"):
            self.assertIn(section, text)
        for scenario in ("Pure text", "Mixed input", "zeebe namespace", "Unsupported format", "Invalid XML"):
            self.assertIn(scenario, text)
        self.assertIn(DIAGRAM_CONVERTER_URL, text)
        self.assertIn("Validate/Fix mode is planned for v2.4.0", text)


if __name__ == "__main__":
    unittest.main()
