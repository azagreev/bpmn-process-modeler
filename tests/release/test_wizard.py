import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "wizard"
WIZARD_DOC = REPO_ROOT / "references" / "clarification-wizard.md"
ANNOTATION_DOC = REPO_ROOT / "references" / "annotation-style-guide.md"

PRIORITY = ["topology", "participants", "happy_path", "exception_paths", "slas", "data_ownership"]
ASSUMPTION_TRIGGERS = ("делай с допущениями", "генерируй с предположениями", "не задавай вопросов", "генерируй без вопросов", "as is", "as-is", "just do it")


def load_text(relative_path):
    return (FIXTURES / relative_path).read_text(encoding="utf-8")


def load_json(relative_path):
    return json.loads((FIXTURES / relative_path).read_text(encoding="utf-8"))


def detects_assumption_mode(text):
    return any(trigger in text.lower() for trigger in ASSUMPTION_TRIGGERS)


def detect_missing_categories(text):
    lowered = text.lower()
    missing = []
    if not re.search(r"\b(пул|пуле|пула|лэйн|лэйны|lane|pool|collaboration|message flows?)\b", lowered):
        missing.append("topology")
    if not re.search(r"(клиент|менеджер|аналитик|risk engine|система|исполнитель|отдел|банк)", lowered) or re.search(r"(участники не|роли неизвестны|исполнители не)", lowered):
        missing.append("participants")
    if not re.search(r"(сначала|затем|после|потом|при одобрении|успешн|пода[её]т)", lowered) or re.search(r"(успешный путь не|happy path не)", lowered):
        missing.append("happy_path")
    if not re.search(r"(при отказ|отказ|если|таймаут|ошиб|закрывается|эскалац)", lowered) or re.search(r"(исключения .*не|отказы не|ошибки не)", lowered):
        missing.append("exception_paths")
    if not re.search(r"(24 часа|3 рабочих|sla:|срок выполнения|таймаут \d+)", lowered) or re.search(r"(сроки .*не|не указаны .*срок|sla не|сроки и sla не)", lowered):
        missing.append("slas")
    if not re.search(r"\b(los|crm|сэд|master data|source system|хранятся|владелец данных)\b", lowered) or re.search(r"(где хранятся|владельц[а-я ]+не|источники .*не выбраны)", lowered):
        missing.append("data_ownership")
    return [category for category in PRIORITY if category in missing]


def route_wizard(text):
    missing = detect_missing_categories(text)
    if detects_assumption_mode(text):
        return {"missing_categories": missing, "questions": [], "wizard_invoked": False, "offer_assumption_mode": False, "assumptions_marked": bool(missing)}
    if not missing:
        return {"missing_categories": missing, "questions": [], "wizard_invoked": False}
    if len(missing) >= 6:
        return {"missing_categories": missing, "questions": [], "wizard_invoked": False, "offer_assumption_mode": True}
    return {"missing_categories": missing, "questions": missing[:5], "wizard_invoked": True, "offer_assumption_mode": False}


class WizardTests(unittest.TestCase):
    def test_category_detection_individual_missing(self):
        cases = [
            ("topology", "Клиент подаёт заявку, менеджер проверяет документы за 24 часа, при отказе заявка закрывается, данные хранятся в LOS."),
            ("participants", "В одном пуле с лэйнами выполняется заявка: сначала проверка, затем решение, при отказе закрытие, SLA 24 часа, данные в LOS."),
            ("happy_path", "В одном пуле банк и клиент участвуют в процессе, менеджер отвечает за действия, при отказе закрытие, SLA 24 часа, данные в LOS."),
            ("exception_paths", "В одном пуле менеджер сначала проверяет заявку, затем одобряет договор за 24 часа, данные хранятся в LOS."),
            ("slas", "В одном пуле менеджер сначала проверяет заявку, затем принимает решение, при отказе закрывает процесс, данные в LOS."),
            ("data_ownership", "В одном пуле менеджер сначала проверяет заявку за 24 часа, затем принимает решение, при отказе закрывает процесс."),
        ]
        for category, text in cases:
            with self.subTest(category=category):
                self.assertIn(category, detect_missing_categories(text))

    def test_wizard_routing_by_completeness(self):
        complete = route_wizard(load_text("complete_input/full_bnpl_process.txt"))
        self.assertEqual(complete["missing_categories"], load_json("complete_input/expected_wizard_skipped.json")["missing_categories"])
        self.assertFalse(complete["wizard_invoked"])

        for fixture, expected_fixture in (
            ("partial_input/missing_sla.txt", "partial_input/expected_questions_missing_sla.json"),
            ("partial_input/missing_sla_and_data.txt", "partial_input/expected_questions_missing_sla_and_data.json"),
        ):
            expected = load_json(expected_fixture)
            result = route_wizard(load_text(fixture))
            self.assertEqual(result["missing_categories"], expected["missing_categories"])
            self.assertEqual(len(result["questions"]), expected["questions_count"])

        sparse = route_wizard(load_text("sparse_input/happy_path_only.txt"))
        self.assertEqual(sparse["questions"], load_json("sparse_input/expected_questions.json")["expected_priority_order"])
        self.assertEqual(len(sparse["questions"]), 5)

        catastrophic = route_wizard(load_text("catastrophic_input/one_sentence_description.txt"))
        self.assertTrue(catastrophic["offer_assumption_mode"])

    def test_assumption_mode_and_skip_command(self):
        for trigger in ASSUMPTION_TRIGGERS:
            with self.subTest(trigger=trigger):
                result = route_wizard(f"{trigger}. Смоделируй процесс продаж.")
                self.assertFalse(result["wizard_invoked"])
                self.assertTrue(result["assumptions_marked"])
        self.assertEqual(route_wizard("генерируй без вопросов. Процесс: заявка поступает.")["questions"], [])

    def test_assumption_annotation_xml_contract(self):
        xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_Test">
    <bpmn:userTask id="Activity_Manual_Review" name="Проверить заявку"/>
    <bpmn:textAnnotation id="TextAnnotation_Assumption_1">
      <bpmn:text>⚠ Допущение: SLA на ручную проверку — 24 часа.
В исходнике срок не указан, принят default из category slas.</bpmn:text>
    </bpmn:textAnnotation>
    <bpmn:association id="Association_Assumption_1" sourceRef="Activity_Manual_Review" targetRef="TextAnnotation_Assumption_1"/>
  </bpmn:process>
</bpmn:definitions>"""
        root = ET.fromstring(xml)
        text = root.find(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}text").text
        association = root.find(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}association")
        self.assertTrue(text.startswith("⚠ Допущение:"))
        self.assertEqual(association.attrib["sourceRef"], "Activity_Manual_Review")

    def test_wizard_docs_contract(self):
        wizard = WIZARD_DOC.read_text(encoding="utf-8")
        annotation = ANNOTATION_DOC.read_text(encoding="utf-8")
        self.assertIn("Maximum 5 questions", wizard)
        self.assertIn("1 question = 1 category", wizard)
        self.assertIn("Sheet «Допущения»", wizard)
        self.assertIn("Annotation prefix: ⚠ Допущение:", annotation)
        self.assertIn("When NOT to mark as Допущение", annotation)


if __name__ == "__main__":
    unittest.main()
