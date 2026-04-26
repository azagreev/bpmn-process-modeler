import unittest

from tests.release.test_package_build import REPO_ROOT


class DocsContractTests(unittest.TestCase):
    def test_readme_release_notes_contract(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Покрытие отраслей (34 процесса в 8 reference-файлах)", readme)
        self.assertNotIn("Покрытие отраслей (24 процесса", readme)
        self.assertNotIn("Первый публичный релиз через GitHub Releases", readme)
        self.assertIn("исторический GitHub Release v1.1.0", readme)

    def test_security_and_contributing_contract(self):
        security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("v2.0.x", security)
        self.assertIn("https://github.com/azagreev/bpmn-process-modeler/issues", contributing)


if __name__ == "__main__":
    unittest.main()
