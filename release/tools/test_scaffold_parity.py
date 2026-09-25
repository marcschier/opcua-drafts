"""Cross-submodule scaffold parity; private checkouts are optional in public CI."""
import hashlib
import json
import configparser
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
REPOS = ("OPC10000-Core", "OPC10100-WoT", "OPC12000-Metaverse", "OPC30450-CloudIntegration")
FILES = (
    ".config/dotnet-tools.json", ".config/spec-scaffold.json",
    ".gitattributes", ".gitignore", ".markdownlint-cli2.yaml",
    ".github/pull_request_template.md", ".github/workflows/publish.yml",
    ".github/workflows/content-validation.yml", "AUTHORING.md",
    "install-tools.ps1", "install-tools.sh", "legal.md",
    "skills/opcua-companion-spec/SKILL.md", "skills/opcua-word-to-markdown/SKILL.md",
    "source/agreement-of-use.md", "source/logo-left.jpg",
    "source/figures/README.md", "source/figures/uashapes-library.drawio.xml",
    "tools/office-to-svg.ps1", "tools/office-to-svg.sh",
)


class ScaffoldParityTests(unittest.TestCase):
    def test_new_core_registration_keeps_all_existing_submodules(self):
        config = configparser.ConfigParser()
        config.read(ROOT / ".gitmodules", encoding="utf-8")
        expected = {"OPC10000-Core", "OPC10100-WoT", "OPC12000-Metaverse",
                    "OPC30450-CloudIntegration", "spec-drafts"}
        self.assertEqual({config[section]["path"] for section in config.sections()}, expected)
        self.assertEqual(config['submodule "OPC10000-Core"']["url"],
                         "https://github.com/OPCF-Members/OPC10000-Core.git")

    def test_four_active_scaffolds_are_identical_when_checkouts_are_available(self):
        if not all((ROOT / repo / ".git").exists() for repo in REPOS):
            self.skipTest("Member-only submodules are not initialized in this public checkout")
        for path in FILES:
            with self.subTest(path=path):
                hashes = {hashlib.sha256((ROOT / repo / path).read_bytes()).hexdigest() for repo in REPOS}
                self.assertEqual(len(hashes), 1)
                modes = set()
                for repo in REPOS:
                    entry = subprocess.check_output(
                        ["git", "-C", str(ROOT / repo), "ls-files", "--stage", "--", path], text=True)
                    self.assertTrue(entry, f"unstaged shared file: {repo}/{path}")
                    modes.add(entry.split()[0])
                self.assertEqual(len(modes), 1)
        for repo in REPOS:
            contract = json.loads((ROOT / repo / "extras/ci/scaffold-files.json").read_text())
            self.assertEqual(set(contract), set(FILES))
            for path, expected in contract.items():
                canonical = subprocess.check_output(["git", "-C", str(ROOT / repo), "show", ":" + path])
                self.assertEqual(hashlib.sha256(canonical).hexdigest(), expected["sha256"])
                entry = subprocess.check_output(
                    ["git", "-C", str(ROOT / repo), "ls-files", "--stage", "--", path], text=True)
                self.assertEqual(entry.split()[0], expected["mode"])
        expected = {path for path in FILES if path.startswith(".github/")}
        for repo in REPOS:
            actual = {path.relative_to(ROOT / repo).as_posix()
                      for path in (ROOT / repo / ".github").rglob("*") if path.is_file()}
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
