from pathlib import Path
import xml.etree.ElementTree as ET

import pytest


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
        return {
            "mode": "reject",
            "reason": "Empty input. Provide a process description or BPMN file.",
            "has_xml": False,
            "mixed": False,
            "reuse_id": False,
        }

    unsupported_exts = (".drawio", ".vsdx", ".png", ".jpg", ".pdf")
    if lower_name.endswith(unsupported_exts) or binary_header.startswith((b"\x89PNG", b"%PDF")):
        return {
            "mode": "reject",
            "reason": "unsupported format",
            "has_xml": False,
            "mixed": False,
            "reuse_id": False,
        }

    has_xml = "<?xml" in text or "<bpmn:" in text or lower_name.endswith(".bpmn")
    if "xmlns:zeebe=" in text or "zeebe:" in text:
        return {
            "mode": "reject",
            "reason": f"Diagram Converter: {DIAGRAM_CONVERTER_URL}",
            "has_xml": True,
            "mixed": False,
            "reuse_id": False,
        }

    if has_xml and text.strip().startswith("<?xml"):
        try:
            ET.fromstring(text)
        except ET.ParseError as exc:
            return {
                "mode": "reject",
                "reason": f"parse error: {exc}",
                "has_xml": True,
                "mixed": False,
                "reuse_id": False,
            }

    update_triggers = ("обнови", "дополни", "измени", "расширь существующий")
    has_update_trigger = any(trigger in lower_text for trigger in update_triggers)
    plain_text_sentences = [part for part in text.replace("\n", " ").split(".") if part.strip()]
    mixed = (has_xml and len(plain_text_sentences) > 2) or (
        has_xml and has_update_trigger
    )

    if mixed:
        return {
            "mode": "generate",
            "reason": "mixed input",
            "has_xml": True,
            "mixed": True,
            "reuse_id": True,
        }

    if has_xml:
        return {
            "mode": "generate",
            "reason": "xml without explicit update trigger defaults to reuse-ID",
            "has_xml": True,
            "mixed": True,
            "reuse_id": True,
        }

    return {
        "mode": "generate",
        "reason": "pure text",
        "has_xml": False,
        "mixed": False,
        "reuse_id": False,
    }


@pytest.mark.parametrize(
    "input_text, filename, binary_header, expected_mode, expected_attrs",
    [
        (
            "Опишу процесс одобрения заявки клиентом и менеджером банка.",
            None,
            b"",
            "generate",
            {"has_xml": False, "mixed": False, "reuse_id": False},
        ),
        (
            "Обнови процесс. Добавь проверку. Сохрани существующие ID. "
            "<?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>",
            None,
            b"",
            "generate",
            {"has_xml": True, "mixed": True, "reuse_id": True},
        ),
        (
            "<?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL' xmlns:zeebe='http://camunda.org/schema/zeebe/1.0'/>",
            None,
            b"",
            "reject",
            {"has_xml": True, "mixed": False, "reuse_id": False},
        ),
        ("diagram.drawio", "diagram.drawio", b"", "reject", {"has_xml": False}),
        ("process.vsdx", "process.vsdx", b"", "reject", {"has_xml": False}),
        ("", "screen.png", b"\x89PNG\r\n\x1a\n", "reject", {"has_xml": False}),
        ("<?xml version='1.0'?><bpmn:definitions>", None, b"", "reject", {"has_xml": True}),
        ("", None, b"", "reject", {"has_xml": False, "mixed": False, "reuse_id": False}),
        (
            "Нужно расширить схему. Добавить второй путь. Сохранить прежние элементы. "
            "<?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>",
            None,
            b"",
            "generate",
            {"has_xml": True, "mixed": True, "reuse_id": True},
        ),
        (
            "дополни <?xml version='1.0'?><bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>",
            None,
            b"",
            "generate",
            {"has_xml": True, "mixed": True, "reuse_id": True},
        ),
    ],
)
def test_step0_routing(input_text, filename, binary_header, expected_mode, expected_attrs):
    result = classify_input(input_text, filename=filename, binary_header=binary_header)

    assert result["mode"] == expected_mode
    for key, expected in expected_attrs.items():
        assert result[key] == expected


def test_pure_text_negative_variant_has_no_reuse_id():
    result = classify_input("Смоделируй простой процесс регистрации клиента.")

    assert result["mode"] == "generate"
    assert result["has_xml"] is False
    assert result["reuse_id"] is False


def test_zeebe_namespace_rejected_with_converter_guidance():
    result = classify_input(
        "<?xml version='1.0'?><bpmn:definitions "
        "xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL' "
        "xmlns:zeebe='http://camunda.org/schema/zeebe/1.0'/>"
    )

    assert result["mode"] == "reject"
    assert "Diagram Converter" in result["reason"]
    assert DIAGRAM_CONVERTER_URL in result["reason"]


def test_unsupported_format_negative_variant_allows_bpmn_extension():
    result = classify_input(filename="process.bpmn")

    assert result["mode"] == "generate"
    assert result["reuse_id"] is True


def test_invalid_xml_negative_variant_accepts_well_formed_xml():
    result = classify_input(
        "<?xml version='1.0'?><bpmn:definitions "
        "xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL'/>"
    )

    assert result["mode"] == "generate"
    assert result["has_xml"] is True


def test_input_classification_reference_contract():
    text = DOC_PATH.read_text(encoding="utf-8")

    for section in ("Purpose", "Detection heuristics", "Routing rules", "Edge cases"):
        assert section in text
    for scenario in ("Pure text", "Mixed input", "zeebe namespace", "Unsupported format", "Invalid XML"):
        assert scenario in text
    assert DIAGRAM_CONVERTER_URL in text
    assert "Validate/Fix mode is planned for v2.4.0" in text
