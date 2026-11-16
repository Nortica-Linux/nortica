#!/usr/bin/env python3
"""Host-safe checks for project naming and the image's config pin."""
from pathlib import Path
import os
import subprocess
import tempfile
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
            # Deleted paths can remain in the index until the rename is staged.
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

    def test_image_config_uses_checked_out_commit_not_latest_tag(self):
        build = (REPO / "image/build.sh").read_text()
        start = build.index("config_commit=$(")
        end = build.index('\nrm -rf -- "$CONFIG_ROOT"', start)
        snippet = build[start:end]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            origin = root / "origin"
            checkout = root / "source/config"
            destination = root / "image-config"

            def git(*args, cwd=None):
                return subprocess.check_output(["git", *args], cwd=cwd,
                                               stderr=subprocess.DEVNULL, text=True).strip()

            git("init", "-q", str(origin))
            (origin / "deploy.sh").write_text("pinned\n")
            git("add", ".", cwd=origin)
            identity = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid")
            git(*identity, "commit", "-qm", "pinned", cwd=origin)
            pinned = git("rev-parse", "HEAD", cwd=origin)
            (origin / "deploy.sh").write_text("newer\n")
            git("add", ".", cwd=origin)
            git(*identity, "commit", "-qm", "newer", cwd=origin)
            git("tag", "v999.0.0", cwd=origin)
            git("clone", "-q", str(origin), str(checkout))
            git("checkout", "-q", "--detach", pinned, cwd=checkout)
            # Redirect only the network clone; all pin and checkout operations
            # execute real Git against disposable repositories.
            wrapper = '''
git() {
    if [[ $1 == clone ]]; then
        [[ $2 == https://github.com/Nortica-Linux/config.git ]] || return 91
        command git clone "$FIXTURE_ORIGIN" "$3"
    else
        command git "$@"
    fi
}
'''
            subprocess.run(["bash", "-Eeuo", "pipefail", "-c", wrapper + snippet],
                           env=dict(os.environ, ROOT=str(checkout.parent),
                                    CONFIG_SOURCE_DIR=str(destination),
                                    FIXTURE_ORIGIN=str(origin)),
                           check=True, capture_output=True, text=True)
            self.assertEqual(git("rev-parse", "HEAD", cwd=destination), pinned)
            self.assertEqual((destination / "deploy.sh").read_text(), "pinned\n")


if __name__ == "__main__":
    unittest.main()
