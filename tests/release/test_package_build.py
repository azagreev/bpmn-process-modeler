import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "bpmn-process-modeler"


def build_skill_package(temp_dir):
    temp_path = Path(temp_dir)
    package_root = temp_path / "build" / PACKAGE_NAME
    package_root.mkdir(parents=True)

    for name in ("SKILL.md", "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md"):
        shutil.copy2(REPO_ROOT / name, package_root / name)
    shutil.copytree(REPO_ROOT / "references", package_root / "references")

    archive_path = temp_path / "bpmn-process-modeler.skill"
    subprocess.run(
        ["zip", "-r", str(archive_path), PACKAGE_NAME],
        cwd=temp_path / "build",
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return archive_path, package_root


class PackageBuildTests(unittest.TestCase):
    def test_skill_archive_integrity_and_required_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path, _ = build_skill_package(temp_dir)
            result = subprocess.run(
                ["unzip", "-t", str(archive_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            with zipfile.ZipFile(archive_path) as zf:
                names = set(zf.namelist())

            top_level = {PurePosixPath(name).parts[0] for name in names if name}
            self.assertEqual(top_level, {PACKAGE_NAME})

            required = {
                f"{PACKAGE_NAME}/SKILL.md",
                f"{PACKAGE_NAME}/README.md",
                f"{PACKAGE_NAME}/LICENSE",
                f"{PACKAGE_NAME}/CONTRIBUTING.md",
                f"{PACKAGE_NAME}/SECURITY.md",
                f"{PACKAGE_NAME}/references/camunda-knowledge-snapshot.md",
            }
            missing = sorted(required - names)
            self.assertEqual(missing, [])

            industry_files = sorted(
                name
                for name in names
                if name.startswith(f"{PACKAGE_NAME}/references/industry-patterns/")
                and name.endswith(".md")
            )
            self.assertEqual(len(industry_files), 8, industry_files)

            forbidden = sorted(
                name
                for name in names
                if name.startswith(f"{PACKAGE_NAME}/tests/")
                or "__pycache__" in PurePosixPath(name).parts
                or name.endswith(".pyc")
            )
            self.assertEqual(forbidden, [])


if __name__ == "__main__":
    unittest.main()
