import re
import tempfile
import unittest
from pathlib import Path

from tests.release.test_package_build import build_skill_package


LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#][^)]+)\)")


class MarkdownLinkTests(unittest.TestCase):
    def test_package_markdown_links_resolve_inside_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, package_root = build_skill_package(temp_dir)
            package_root = package_root.resolve()
            failures = []

            for path in sorted(package_root.rglob("*.md")):
                text = path.read_text(encoding="utf-8")
                for match in LINK_RE.finditer(text):
                    target = match.group(1)
                    if "://" in target or target.startswith("mailto:") or target.startswith("#"):
                        continue

                    resolved = (path.parent / target).resolve()
                    try:
                        resolved.relative_to(package_root)
                    except ValueError:
                        failures.append(f"{path.relative_to(package_root)} links outside package: {target}")
                        continue

                    if not resolved.exists():
                        line = text.count("\n", 0, match.start()) + 1
                        failures.append(f"{path.relative_to(package_root)}:{line} missing {target}")

            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
