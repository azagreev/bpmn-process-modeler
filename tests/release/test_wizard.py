import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "wizard"
WIZARD_DOC = REPO_ROOT / "references" / "clarification-wizard.md"
ANNOTATION_DOC = REPO_ROOT / "references" / "annotation-style-guide.md"

PRIORITY = ["topology", "participants", "happy_path", "exception_paths", "slas", "data_ownership"]
ASSUMPTION_TRIGGERS = (
    "делай с допущениями",
    "генерируй с предположениями",
    "не задавай вопросов",
    "генерируй без вопросов",
    "as is",
    "as-is",
    "just do it",
)


def load_text(relative_path):
    return (FIXTURES / relative_path).read_text(encoding="utf-8")


def load_json(relative_path):
    return json.loads((FIXTURES / relative_path).read_text(encoding="utf-8"))


def detects_assumption_mode(text):
    lowered = text.lower()
    return any(trigger in lowered for trigger in ASSUMPTION_TRIGGERS)


def detect_missing_categories(text):
    lowered = text.lower()
    missing = []

    if not re.search(r"\b(пул|пуле|пула|лэйн|лэйны|lane|pool|collaboration|message flows?)\b", lowered):
        missing.append("topology")
    says_participants_missing = re.search(r"(участники не|роли неизвестны|исполнители не)", lowered)
    if not re.search(r"(клиент|менеджер|аналитик|risk engine|система|исполнитель|отдел|банк)", lowered) or says_participants_missing:
        missing.append("participants")
    says_happy_path_missing = re.search(r"(успешный путь не|happy path не)", lowered)
    if not re.search(r"(сначала|затем|после|потом|при одобрении|успешн|пода[её]т)", lowered) or says_happy_path_missing:
        missing.append("happy_path")
    says_exception_missing = re.search(r"(исключения .*не|отказы не|ошибки не)", lowered)
    if not re.search(r"(при отказ|отказ|если|таймаут|ошиб|закрывается|эскалац)", lowered) or says_exception_missing:
        missing.append("exception_paths")
    has_sla = re.search(r"(24 часа|3 рабочих|sla:|срок выполнения|таймаут \d+)", lowered)
    says_sla_missing = re.search(r"(сроки .*не|не указаны .*срок|sla не|сроки и sla не)", lowered)
    if not has_sla or says_sla_missing:
        missing.append("slas")
    has_data = re.search(r"\b(los|crm|сэд|master data|source system|хранятся|владелец данных)\b", lowered)
    says_data_missing = re.search(r"(где хранятся|владельц[а-я ]+не|источники .*не выбраны)", lowered)
    if not has_data or says_data_missing:
        missing.append("data_ownership")

    return [category for category in PRIORITY if category in missing]


def route_wizard(text, assumption_command=False):
    missing = detect_missing_categories(text)
    if assumption_command or detects_assumption_mode(text):
        return {
            "missing_categories": missing,
            "questions": [],
            "wizard_invoked": False,
            "offer_assumption_mode": False,
            "assumptions_marked": bool(missing),
        }
    if len(missing) == 0:
        return {"missing_categories": missing, "questions": [], "wizard_invoked": False}
    if len(missing) >= 6:
        return {
            "missing_categories": missing,
            "questions": [],
            "wizard_invoked": False,
            "offer_assumption_mode": True,
        }
    return {
        "missing_categories": missing,
        "questions": missing[:5],
        "wizard_invoked": True,
        "offer_assumption_mode": False,
    }


def build_assumption_annotation():
    return """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_Test">
    <bpmn:userTask id="Activity_Manual_Review" name="Проверить заявку"/>
    <bpmn:textAnnotation id="TextAnnotation_Assumption_1">
      <bpmn:text>⚠ Допущение: SLA на ручную проверку — 24 часа.
В исходнике срок не указан, принят default из category slas.</bpmn:text>
    </bpmn:textAnnotation>
    <bpmn:association id="Association_Assumption_1"
      sourceRef="Activity_Manual_Review"
      targetRef="TextAnnotation_Assumption_1"/>
  </bpmn:process>
</bpmn:definitions>"""


@pytest.mark.parametrize(
    "category, text",
    [
        ("topology", "Клиент подаёт заявку, менеджер проверяет документы за 24 часа, при отказе заявка закрывается, данные хранятся в LOS."),
        ("participants", "В одном пуле с лэйнами выполняется заявка: сначала проверка, затем решение, при отказе закрытие, SLA 24 часа, данные в LOS."),
        ("happy_path", "В одном пуле банк и клиент участвуют в процессе, менеджер отвечает за действия, при отказе закрытие, SLA 24 часа, данные в LOS."),
        ("exception_paths", "В одном пуле менеджер сначала проверяет заявку, затем одобряет договор за 24 часа, данные хранятся в LOS."),
        ("slas", "В одном пуле менеджер сначала проверяет заявку, затем принимает решение, при отказе закрывает процесс, данные в LOS."),
        ("data_ownership", "В одном пуле менеджер сначала проверяет заявку за 24 часа, затем принимает решение, при отказе закрывает процесс."),
    ],
)
def test_category_detection_individual_missing(category, text):
    assert category in detect_missing_categories(text)


def test_complete_input_skips_wizard():
    expected = load_json("complete_input/expected_wizard_skipped.json")
    result = route_wizard(load_text("complete_input/full_bnpl_process.txt"))

    assert result["missing_categories"] == expected["missing_categories"]
    assert len(result["questions"]) == expected["questions_count"]
    assert result["wizard_invoked"] is expected["wizard_invoked"]


@pytest.mark.parametrize(
    "fixture, expected_fixture",
    [
        ("partial_input/missing_sla.txt", "partial_input/expected_questions_missing_sla.json"),
        ("partial_input/missing_sla_and_data.txt", "partial_input/expected_questions_missing_sla_and_data.json"),
    ],
)
def test_partial_input_asks_one_or_two_questions(fixture, expected_fixture):
    expected = load_json(expected_fixture)
    result = route_wizard(load_text(fixture))

    assert result["missing_categories"] == expected["missing_categories"]
    assert len(result["questions"]) == expected["questions_count"]
    assert result["wizard_invoked"] is True


def test_sparse_input_uses_priority_order_and_hard_limit():
    expected = load_json("sparse_input/expected_questions.json")
    result = route_wizard(load_text("sparse_input/happy_path_only.txt"))

    assert result["questions"] == expected["expected_priority_order"]
    assert len(result["questions"]) == 5
    assert result["wizard_invoked"] is True


def test_catastrophic_input_offers_assumption_mode():
    expected = load_json("catastrophic_input/expected_assumption_mode_offer.json")
    result = route_wizard(load_text("catastrophic_input/one_sentence_description.txt"))

    assert result["missing_categories"] == expected["missing_categories"]
    assert result["offer_assumption_mode"] is True
    assert result["wizard_invoked"] is False


@pytest.mark.parametrize("trigger", ASSUMPTION_TRIGGERS)
def test_assumption_mode_trigger_phrases(trigger):
    result = route_wizard(f"{trigger}. Смоделируй процесс продаж.")

    assert result["wizard_invoked"] is False
    assert result["assumptions_marked"] is True


def test_assumption_annotation_xml_contract():
    xml = build_assumption_annotation()
    root = ET.fromstring(xml)
    text = root.find(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}text").text
    association = root.find(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}association")

    assert text.startswith("⚠ Допущение:")
    assert association.attrib["sourceRef"] == "Activity_Manual_Review"
    assert association.attrib["targetRef"] == "TextAnnotation_Assumption_1"


def test_skip_command_skips_wizard_without_questions():
    result = route_wizard("генерируй без вопросов. Процесс: заявка поступает.")

    assert result["wizard_invoked"] is False
    assert result["questions"] == []


def test_wizard_docs_contract():
    wizard = WIZARD_DOC.read_text(encoding="utf-8")
    annotation = ANNOTATION_DOC.read_text(encoding="utf-8")

    assert "Maximum 5 questions" in wizard
    assert "1 question = 1 category" in wizard
    assert "Sheet «Допущения»" in wizard
    assert "Annotation prefix: ⚠ Допущение:" in annotation
    assert "When NOT to mark as Допущение" in annotation
