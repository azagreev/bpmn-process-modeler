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

    def test_changelog_release_date_is_filled(self):
        """Current version's changelog section must have a real release date."""
        frontmatter = parse_skill_frontmatter()
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        pattern = rf"^### v{re.escape(frontmatter['version'])} — (.+)$"
        match = re.search(pattern, readme, re.MULTILINE)
        self.assertIsNotNone(
            match,
            f"Current version v{frontmatter['version']} section not found "
            f"in README changelog with em-dash separator",
        )
        date_field = match.group(1).strip().lower()
        forbidden_markers = (
            "tbd",
            "дата релиза tbd",
            "release date tbd",
            "<дата",
        )
        for marker in forbidden_markers:
            self.assertNotIn(
                marker,
                date_field,
                f"Release date for v{frontmatter['version']} contains "
                f"placeholder {marker!r}: {match.group(1).strip()!r}. "
                f"Fill in the actual date before tagging.",
            )

    def test_historic_changelog_dates_are_filled(self):
        """All published changelog sections must have real dates (no TBD)."""
        frontmatter = parse_skill_frontmatter()
        current_version = frontmatter["version"]
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        section_pattern = r"^### v(\d+\.\d+(?:\.\d+)?) — (.+)$"
        sections = re.findall(section_pattern, readme, re.MULTILINE)
        self.assertGreater(
            len(sections),
            0,
            "No version sections found in README changelog",
        )

        forbidden = ("tbd", "дата релиза tbd", "release date tbd")
        for version, date_field in sections:
            if version == current_version:
                # Current version is covered by test_changelog_release_date_is_filled
                continue
            normalized = date_field.strip().lower()
            for marker in forbidden:
                self.assertNotIn(
                    marker,
                    normalized,
                    f"Historic section v{version} has placeholder "
                    f"{marker!r}: {date_field.strip()!r}",
                )

    def test_readme_snapshot_date_matches_frontmatter(self):
        """README snapshot dates must match SKILL.md frontmatter snapshot_date."""
        frontmatter = parse_skill_frontmatter()
        snapshot_date = frontmatter["snapshot_date"]
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        # Pattern 1: degraded mode XML comment in Requirements section
        comment_matches = list(re.finditer(
            r"snapshot v1\.0 \((\d{4}-\d{2}-\d{2})\)",
            readme,
        ))
        self.assertGreater(
            len(comment_matches),
            0,
            "README missing 'snapshot v1.0 (YYYY-MM-DD)' marker",
        )
        for match in comment_matches:
            self.assertEqual(
                match.group(1),
                snapshot_date,
                f"README XML-comment snapshot date {match.group(1)!r} does "
                f"not match SKILL.md frontmatter snapshot_date "
                f"{snapshot_date!r}",
            )

        # Pattern 2: archive contents description "версия 1.0 от YYYY-MM-DD"
        archive_matches = list(re.finditer(
            r"версия 1\.0 от (\d{4}-\d{2}-\d{2})",
            readme,
        ))
        self.assertGreater(
            len(archive_matches),
            0,
            "README missing 'версия 1.0 от YYYY-MM-DD' marker",
        )
        for match in archive_matches:
            self.assertEqual(
                match.group(1),
                snapshot_date,
                f"README archive snapshot date {match.group(1)!r} does not "
                f"match SKILL.md frontmatter snapshot_date {snapshot_date!r}",
            )

    def test_readme_bpmn_patterns_count_matches_source(self):
        """README claim 'N готовых XML-паттернов' must equal actual `## N.` count."""
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        patterns_doc = (REPO_ROOT / "references" / "bpmn-patterns.md").read_text(
            encoding="utf-8",
        )

        # Count top-level numbered patterns: "## N. Title"
        actual_count = len(re.findall(r"^## \d+\. ", patterns_doc, re.MULTILINE))
        self.assertGreater(
            actual_count,
            0,
            "references/bpmn-patterns.md has no numbered '## N.' sections",
        )

        # README claim
        claim_match = re.search(r"(\d+) готовых XML-паттернов", readme)
        self.assertIsNotNone(
            claim_match,
            "README missing 'N готовых XML-паттернов' claim",
        )
        claimed_count = int(claim_match.group(1))

        self.assertEqual(
            claimed_count,
            actual_count,
            f"README claims {claimed_count} BPMN patterns, but "
            f"references/bpmn-patterns.md has {actual_count} numbered sections",
        )

    def test_readme_best_practices_count_matches_validation_checklist(self):
        """Current README sections must claim correct number of optional best practices.

        Optional best practices are sections numbered >= 8 in
        references/validation-checklist.md (sections 1-7 are blocking checks).
        Section 9 uses '###' instead of '##' in the source file, so the regex
        accepts both heading levels.

        Historic changelog sections (v1.0, v1.1) are intentionally excluded
        from the check because their counts reflect the state at that release.
        """
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        checklist = (REPO_ROOT / "references" / "validation-checklist.md").read_text(
            encoding="utf-8",
        )

        # Count all top-level numbered sections in checklist, then filter to >= 8.
        all_section_numbers = re.findall(
            r"^#{2,3} (\d+)\. ",
            checklist,
            re.MULTILINE,
        )
        actual_count = sum(1 for n in all_section_numbers if int(n) >= 8)
        self.assertGreater(
            actual_count,
            0,
            "references/validation-checklist.md has no optional sections (>= 8)",
        )

        # Cut off README at first historic section marker `### v1.` so we only
        # check current claims.
        cutoff_match = re.search(r"^### v1\.", readme, re.MULTILINE)
        current_part = readme[: cutoff_match.start()] if cutoff_match else readme

        claims = re.findall(
            r"(\d+) рекомендательных best practices",
            current_part,
        )
        self.assertGreater(
            len(claims),
            0,
            "No 'N рекомендательных best practices' claims found in current "
            "README sections",
        )

        for claim in claims:
            self.assertEqual(
                int(claim),
                actual_count,
                f"Current README section claims {claim} best practices, but "
                f"references/validation-checklist.md has {actual_count} "
                f"optional sections (>= 8)",
            )

    def test_release_md_has_current_version_section(self):
        """RELEASE.md must have a pre-release checklist section for current version."""
        frontmatter = parse_skill_frontmatter()
        release_md = (REPO_ROOT / "RELEASE.md").read_text(encoding="utf-8")
        expected = rf"^### v{re.escape(frontmatter['version'])}\b"
        self.assertIsNotNone(
            re.search(expected, release_md, re.MULTILINE),
            f"RELEASE.md missing pre-release checklist section for "
            f"v{frontmatter['version']}",
        )

    def test_snapshot_metadata_is_valid(self):
        frontmatter = parse_skill_frontmatter()
        for key in ("snapshot_version", "snapshot_date", "snapshot_expiry"):
            self.assertIn(key, frontmatter)

        snapshot_date = date.fromisoformat(frontmatter["snapshot_date"])
        snapshot_expiry = date.fromisoformat(frontmatter["snapshot_expiry"])
        self.assertLess(snapshot_date, snapshot_expiry)


if __name__ == "__main__":
    unittest.main()
