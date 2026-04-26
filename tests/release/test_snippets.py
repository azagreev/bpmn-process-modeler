import re
import unittest
import xml.etree.ElementTree as ET

from tests.release.test_package_build import REPO_ROOT


FENCE_RE = re.compile(r"```([A-Za-z0-9_+.-]*)\n(.*?)```", re.DOTALL)


class SnippetTests(unittest.TestCase):
    def test_markdown_files_are_utf8(self):
        failures = []
        for path in self._markdown_files():
            try:
                path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                failures.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
        self.assertEqual(failures, [])

    def test_python_snippets_compile(self):
        failures = []
        for path, index, source in self._snippets("python"):
            if "# noqa: snippet" in source:
                continue
            try:
                compile(source, f"{path.relative_to(REPO_ROOT)} snippet {index}", "exec")
            except SyntaxError as exc:
                failures.append(f"{path.relative_to(REPO_ROOT)} snippet {index}: {exc}")
        self.assertEqual(failures, [])

    def test_full_xml_snippets_parse(self):
        failures = []
        for path, index, source in self._snippets("xml"):
            stripped = source.strip()
            if "<!-- snippet:fragment -->" in stripped:
                continue
            if not self._looks_like_full_xml(stripped):
                continue
            try:
                ET.fromstring(stripped)
            except ET.ParseError as exc:
                failures.append(f"{path.relative_to(REPO_ROOT)} snippet {index}: {exc}")
        self.assertEqual(failures, [])

    def _markdown_files(self):
        root_files = sorted(REPO_ROOT.glob("*.md"))
        reference_files = sorted((REPO_ROOT / "references").rglob("*.md"))
        return root_files + reference_files

    def _snippets(self, language):
        for path in self._markdown_files():
            text = path.read_text(encoding="utf-8")
            for index, match in enumerate(FENCE_RE.finditer(text), start=1):
                if match.group(1).lower() == language:
                    yield path, index, match.group(2)

    def _looks_like_full_xml(self, source):
        return (
            source.startswith("<?xml")
            or source.startswith("<bpmn:definitions")
            or source.startswith("<bpmn definitions")
        )


if __name__ == "__main__":
    unittest.main()
