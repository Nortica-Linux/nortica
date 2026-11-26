"""Host-safe tool packaging and checksum regressions."""
import hashlib
import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tools_installer", REPO / "deploy/scripts/install-tools.py")
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class ToolsTests(unittest.TestCase):
    def test_cached_archives_install_and_reject_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "cache"
            cache.mkdir()
            for app, (version, _) in tools.RELEASES.items():
                name = f"{app}-{version}-linux-x64-wayland"
                source = root / name
                binary = source / (f"bin/{app}" if app == "mzp" else app)
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b"fixture binary")
                (source / f"{app}.svg").write_text("icon")
                (source / f"{app}.desktop").write_text(f"[Desktop Entry]\nExec={app}\n")
                notices = source / "licenses"
                notices.mkdir()
                (notices / "LICENSE").write_text("notice")
                if app == "mzp":
                    lib = source / "lib/mzp/libpdfium.so"
                    lib.parent.mkdir(parents=True)
                    lib.write_bytes(b"pdfium")
                archive = cache / f"{name}.tar.gz"
                with tarfile.open(archive, "w:gz") as tar:
                    tar.add(source, arcname=name)
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                with patch.dict(tools.RELEASES, {app: (version, digest)}), patch.object(tools.subprocess, "run") as run:
                    self.assertEqual(tools.fetch(app, cache), (archive, name))
                    run.assert_not_called()
                    prefix = root / "prefix"
                    tools.install(app, archive, name, prefix)
                    tools.install(app, archive, name, prefix)
                    self.assertEqual((prefix / "bin" / app).stat().st_mode & 0o777, 0o755)
                    self.assertEqual((prefix / "share" / app / "licenses/LICENSE").read_text(), "notice")
                    if app == "sms":
                        desktop = (prefix / "share/applications/sms.desktop").read_text()
                        self.assertIn("Exec=sms --dir %f", desktop)
                        self.assertIn("MimeType=inode/directory;", desktop)
                    archive.write_bytes(b"corrupt")
                    with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                        tools.fetch(app, cache)
                    run.assert_not_called()

    def test_desktop_configuration_uses_sms(self):
        hyprland = (REPO / "config/dotfiles/hypr/hyprland.lua").read_text()
        self.assertNotIn("Thunar", hyprland)
        self.assertIn('hl.dsp.exec_cmd("sms")', hyprland)
        self.assertNotIn("thunar", (REPO / "deploy/vars.sh").read_text())
