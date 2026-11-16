#!/usr/bin/env python3
"""Host-safe Makefile, config-selection, cache and publication regressions."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
IDENTITY = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid")


def git(*args, cwd):
    return subprocess.check_output(["git", *args], cwd=cwd,
                                   stderr=subprocess.DEVNULL, text=True).strip()


class MakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nortica-make-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copyfile(REPO / "Makefile", self.root / "Makefile")
        git("init", "-q", cwd=self.root)
        self.pin = "1234567890abcdef1234567890abcdef12345678"
        git("update-index", "--add", "--cacheinfo", "160000", self.pin, "config", cwd=self.root)
        git(*IDENTITY, "commit", "-qm", "config pin", cwd=self.root)
        self.mock = self.root / "docker"
        self.mock.write_text('''#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, os, shutil, sys
args = sys.argv[1:]
with open(os.environ['MOCK_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if os.environ.get('MOCK_STATUS'):
    sys.exit(int(os.environ['MOCK_STATUS']))
mounts = [args[i + 1] for i, arg in enumerate(args) if arg == '--volume']
cache = Path(next(m.rsplit(':', 1)[0] for m in mounts if m.endswith(':/build')))
if args[-2:] == ['bash', 'image/build.sh']:
    (cache / 'reused').write_text('yes' if (cache / 'cached').exists() else 'no')
    (cache / 'cached').touch()
    output = Path(next(m.rsplit(':', 1)[0] for m in mounts if m.endswith(':/workspace/iso')))
    data = b'fixture ISO'
    (output / 'nortica-live-amd64.iso').write_bytes(data)
    (output / 'SHA256SUMS').write_text(hashlib.sha256(data).hexdigest() + '  nortica-live-amd64.iso\\n')
else:
    assert args[-2:] == ['-c', 'find /build -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +']
    for child in cache.iterdir():
        if child.is_dir() and not child.is_symlink(): shutil.rmtree(child)
        else: child.unlink()
''')
        self.mock.chmod(0o755)
        self.log = self.root / "docker.jsonl"

    def make(self, *args, success=True, **extra_env):
        env = dict(os.environ, TERM="xterm", MOCK_LOG=str(self.log))
        for name in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL", "NO_COLOR"):
            env.pop(name, None)
        env.update(extra_env)
        result = subprocess.run(["make", "--no-print-directory", f"DOCKER={self.mock}", *args],
                                cwd=self.root, env=env, capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_default_is_iso_with_pinned_config_and_persistent_cache(self):
        first = self.make()
        self.assertIn("\x1b[1;34m[Build]", first.stdout)
        self.assertEqual((self.root / ".build/reused").read_text(), "no")
        self.make("iso")
        self.assertEqual((self.root / ".build/reused").read_text(), "yes")
        self.assertEqual(self.calls()[0], self.calls()[1])
        args = self.calls()[0]
        for expected in ("--privileged", "--init", "host", f"NORTICA_CONFIG_VERSION={self.pin}",
                         f"{self.root}:/workspace:ro", f"{self.root}/.build:/build",
                         f"{self.root}/iso:/workspace/iso", f"NORTICA_OUTPUT_UID={os.getuid()}",
                         f"NORTICA_OUTPUT_GID={os.getgid()}"):
            self.assertIn(expected, args)
        self.assertTrue((self.root / "iso/nortica-live-amd64.iso").is_file())

    def test_config_override_and_no_color(self):
        for version in ("latest", "v1.2.3", self.pin):
            result = self.make("iso", f"CONFIG_VERSION={version}", NO_COLOR="1")
            self.assertNotIn("\x1b", result.stdout)
            self.assertIn(f"NORTICA_CONFIG_VERSION={version}", self.calls()[-1])

    def test_clean_removes_hidden_and_nested_caches_but_preserves_all_iso_files(self):
        self.make("iso")
        (self.root / ".build/.hidden").mkdir()
        (self.root / ".build/.hidden/cache").touch()
        before = {p.name: p.read_bytes() for p in (self.root / "iso").iterdir()}
        self.make("clean")
        self.assertFalse((self.root / ".build").exists())
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "iso").iterdir()}, before)
        self.make("clean")
        self.assertEqual(len(self.calls()), 2)

    def test_docker_failures_propagate_without_success_or_iso_changes(self):
        self.make("iso")
        iso = self.root / "iso/nortica-live-amd64.iso"
        before = iso.read_bytes()
        result = self.make("iso", success=False, MOCK_STATUS="73")
        self.assertNotIn("[Done]", result.stdout)
        self.assertEqual(iso.read_bytes(), before)
        self.make("clean", success=False, MOCK_STATUS="74")
        self.assertTrue((self.root / ".build/cached").is_file())
        self.assertEqual(iso.read_bytes(), before)

    def test_clean_needs_no_docker_when_nothing_exists(self):
        self.make("clean", "DOCKER=/nonexistent/docker")
        self.assertEqual(self.calls(), [])

    def test_symlinked_cache_is_never_built_into_or_cleaned(self):
        outside = self.root / "keep"
        outside.mkdir()
        marker = outside / "important"
        marker.touch()
        (self.root / ".build").symlink_to(outside, target_is_directory=True)
        for target in ("iso", "clean"):
            self.make(target, success=False)
            self.assertTrue(marker.exists())
        self.assertEqual(self.calls(), [])

    def test_symlinked_output_is_rejected(self):
        outside = self.root / "keep"
        outside.mkdir()
        (self.root / "iso").symlink_to(outside, target_is_directory=True)
        self.make("iso", success=False)
        self.assertEqual(self.calls(), [])

    def test_build_and_clean_share_a_nonblocking_lock(self):
        with (self.root / ".git/nortica-build.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            for target in ("iso", "clean"):
                result = self.make(target, success=False)
                self.assertIn("Another build or clean is running", result.stderr)
        self.assertEqual(self.calls(), [])


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nortica-config-build-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin"
        self.origin.mkdir()
        self.cache = self.root / "cached-config"
        git("init", "-q", "--initial-branch=main", cwd=self.origin)
        self.first = self.commit("pinned")
        git("tag", "v1.0.0", cwd=self.origin)
        self.second = self.commit("newer")
        git("tag", "v2.0.0", cwd=self.origin)

    def commit(self, contents):
        (self.origin / "deploy.sh").write_text(contents + "\n")
        git("add", ".", cwd=self.origin)
        git(*IDENTITY, "commit", "-qm", contents, cwd=self.origin)
        return git("rev-parse", "HEAD", cwd=self.origin)

    def prepare(self, version, success=True):
        result = subprocess.run([
            "bash", "-Eeuo", "pipefail", "-c",
            'source "$1"; prepare_config_source "$2" "$3" "$4"; echo CONFIG_READY',
            "fixture", str(REPO / "image/config.sh"), version, str(self.cache), str(self.origin)],
            capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("CONFIG_READY", result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("CONFIG_READY", result.stdout)
        return result

    def test_tag_and_commit_pins_ignore_newer_versions(self):
        for version in ("v1.0.0", self.first, "refs/tags/v1.0.0"):
            self.prepare(version)
            self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), self.first)
            self.assertEqual((self.cache / "deploy.sh").read_text(), "pinned\n")

    def test_latest_fetches_new_commits_using_existing_checkout(self):
        self.prepare("latest")
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), self.second)
        third = self.commit("latest")
        (self.cache / "stale").touch()
        self.prepare("latest")
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), third)
        self.assertFalse((self.cache / "stale").exists())
        self.prepare("v1.0.0")
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), self.first)

    def test_cached_pin_can_be_reused_without_network(self):
        self.prepare(self.first)
        self.origin.rename(self.root / "unavailable")
        self.prepare(self.first)
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), self.first)

    def test_new_remote_tag_is_fetched(self):
        self.prepare(self.first)
        third = self.commit("new tag")
        git("tag", "v3.0.0", cwd=self.origin)
        self.prepare("v3.0.0")
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), third)

    def test_missing_version_does_not_fall_back_to_old_config(self):
        self.prepare(self.first)
        self.prepare("v404.0.0", success=False)
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.cache), self.first)

    def test_invalid_versions_fail_before_creating_checkout(self):
        for version in ("", "--help", "../other", "v1; touch bad", "main^{tree}"):
            self.prepare(version, success=False)
            self.assertFalse(self.cache.exists())


class BuildOutputTests(unittest.TestCase):
    def test_generated_root_is_reset_but_live_build_cache_survives(self):
        build = (REPO / "image/build.sh").read_text()
        start = build.index('install -d "$CONFIG_ROOT"\n')
        end = build.index('\ninstall -d "$APT_CACHE', start)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "cache").mkdir()
            (root / "cache/bootstrap").touch()
            (root / "chroot").mkdir()
            (root / "chroot/old-config").touch()
            (root / ".build-stamp").touch()
            subprocess.run(["bash", "-Eeuo", "pipefail", "-c", build[start:end]],
                           env=dict(os.environ, CONFIG_ROOT=str(root)), check=True)
            self.assertEqual([p.name for p in root.iterdir()], ["cache"])
            self.assertTrue((root / "cache/bootstrap").exists())
        self.assertIn("--cache true --cache-stages bootstrap", build)
        self.assertIn("--exclude='/.build/' --exclude='/iso/'", build)

    def test_publication_preserves_old_iso_on_failure_and_writes_checksum_on_success(self):
        build = (REPO / "image/build.sh").read_text()
        snippet = build[build.index("# Publish only after") :]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generated = root / "generated"
            generated.mkdir()
            output = root / "iso"
            output.mkdir()
            iso = output / "nortica-live-amd64.iso"
            sums = output / "SHA256SUMS"
            iso.write_bytes(b"old ISO")
            sums.write_text("old checksum\n")
            env = dict(os.environ, ROOT=str(root), CONFIG_ROOT=str(generated),
                       NORTICA_OUTPUT_UID=str(os.getuid()), NORTICA_OUTPUT_GID=str(os.getgid()))
            failed = subprocess.run(["bash", "-Eeuo", "pipefail", "-c", snippet],
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(iso.read_bytes(), b"old ISO")
            self.assertEqual(sums.read_text(), "old checksum\n")
            self.assertEqual(list(output.glob(".publish.*")), [])
            data = b"new fixture ISO"
            (generated / "live-image.iso").write_bytes(data)
            subprocess.run(["bash", "-Eeuo", "pipefail", "-c", snippet],
                           env=env, check=True, capture_output=True, text=True)
            self.assertEqual(iso.read_bytes(), data)
            self.assertEqual(sums.read_text(), hashlib.sha256(data).hexdigest() + "  nortica-live-amd64.iso\n")
            self.assertEqual(iso.stat().st_uid, os.getuid())
            self.assertEqual(list(output.glob(".publish.*")), [])


if __name__ == "__main__":
    unittest.main()
