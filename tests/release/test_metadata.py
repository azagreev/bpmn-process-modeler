import os
import re
import unittest
from datetime import date

from tests.release.test_package_build import REPO_ROOT


def parse_skill_frontmatter():
    text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        raise AssertionError("SKILL.md frontmatter not found")

    values = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


class MetadataTests(unittest.TestCase):
    def test_version_metadata_is_consistent(self):
        frontmatter = parse_skill_frontmatter()
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_version = re.search(r"^\*\*Версия:\*\* (.+)$", readme, re.MULTILINE)

        self.assertIsNotNone(readme_version)
        self.assertEqual(frontmatter["version"], readme_version.group(1))

        if os.environ.get("GITHUB_REF_TYPE") == "tag":
            ref_name = os.environ.get("GITHUB_REF_NAME", "")
            if ref_name.startswith("v"):
                self.assertEqual(ref_name, "v" + frontmatter["version"])

    def test_changelog_has_current_version_section(self):
        frontmatter = parse_skill_frontmatter()
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        expected = rf"^### v{re.escape(frontmatter['version'])}\b"
        self.assertIsNotNone(re.search(expected, readme, re.MULTILINE))

    def test_snapshot_metadata_is_valid(self):
        frontmatter = parse_skill_frontmatter()
        for key in ("snapshot_version", "snapshot_date", "snapshot_expiry"):
            self.assertIn(key, frontmatter)

        snapshot_date = date.fromisoformat(frontmatter["snapshot_date"])
        snapshot_expiry = date.fromisoformat(frontmatter["snapshot_expiry"])
        self.assertLess(snapshot_date, snapshot_expiry)


if __name__ == "__main__":
    unittest.main()
