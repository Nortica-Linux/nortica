"""Validate the shipped brand kit and its desktop/boot integrations."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
BRAND = REPO / "branding"


class BrandingTests(unittest.TestCase):
    def test_editable_and_exported_brand_assets_are_valid(self):
        for name in ("logo-horizontal-dark", "logo-horizontal-light", "app-icon-dark",
                     "symbol-dark", "avatar-dark", "banner-dark", "social-dark", "favicon"):
            root = ET.parse(BRAND / f"{name}.svg").getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        for path in BRAND.glob("*.png"):
            with self.subTest(path=path.name), Image.open(path) as image:
                image.verify()
        readme = (REPO / "README.md").read_text()
        self.assertIn("branding/logo-horizontal-dark.svg", readme)
        self.assertIn("branding/logo-horizontal-light.svg", readme)

    def test_launchers_and_wallpaper_use_the_supplied_assets(self):
        icon = (BRAND / "app-icon-dark-512.png").read_bytes()
        for name in ("nortica-help", "nortica-ticket"):
            path = REPO / f"config/scripts/help-shortcuts/pngs/{name}.png"
            self.assertEqual(path.read_bytes(), icon)
        build = (REPO / "image/build.sh").read_text()
        self.assertIn('"$ROOT/branding/app-icon-dark-512.png"', build)
        self.assertNotIn('live-assets/nortica-install.png', build)
        with Image.open(REPO / "config/wallpapers/nortica.png") as wallpaper:
            self.assertEqual(wallpaper.size, (1672, 941))
            wallpaper.verify()

    def test_menu_preserves_wallpaper_edges_and_wordmark_contrast(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wallpaper = Image.new("RGB", (1600, 900), "red")
            wallpaper.save(root / "wallpaper.png")
            Image.new("RGBA", (100, 40), (0, 255, 0, 255)).save(root / "logo.png")
            subprocess.run([sys.executable, str(REPO / "image/prepare-boot-menu.py"),
                            str(root / "wallpaper.png"), str(root / "boot"),
                            "--logo", str(root / "logo.png")], check=True)
            with Image.open(root / "boot/grub-pc/splash.png") as menu:
                self.assertEqual(menu.size, (800, 600))
                self.assertEqual(menu.getpixel((0, 0)), (22, 22, 22))
                self.assertEqual(menu.getpixel((1, 520)), (140, 0, 0))
                self.assertEqual(menu.getpixel((400, 100)), (0, 255, 0))
