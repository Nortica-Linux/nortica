#!/usr/bin/env python3
"""Host-safe checks for project naming and concise entry-point documentation."""
from pathlib import Path
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[1]


class NamingTests(unittest.TestCase):
    def test_sources_and_paths_use_current_name(self):
        old_names = ("debian" + "zfs", "debian-zfs", "docs.debian.foelk.com")
        paths = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=REPO).decode().split("\0")
        config_paths = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=REPO / "config").decode().split("\0")
        paths += ["config/" + path for path in config_paths if path]
        for relative in paths:
            if not relative or relative == "AGENTS.md" or relative.startswith("tests/"):
                continue
            path = REPO / relative
            if not path.is_file():
                continue
            with self.subTest(path=relative):
                for name in old_names:
                    self.assertNotIn(name, relative.lower())
                try:
                    text = path.read_text().lower()
                except UnicodeDecodeError:
                    continue
                for name in old_names:
                    self.assertNotIn(name, text)

    def test_readme_has_only_build_and_usage_sections(self):
        headings = [line for line in (REPO / "README.md").read_text().splitlines()
                    if line.startswith("## ")]
        self.assertEqual(headings, ["## Build an image", "## Use it"])


if __name__ == "__main__":
    unittest.main()
