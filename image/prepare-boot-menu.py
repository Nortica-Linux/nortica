#!/usr/bin/env python3
"""Prepare native live-build overrides from the selected config wallpaper."""
from pathlib import Path
import argparse
import shutil

from PIL import Image, ImageEnhance, ImageOps


def prepare(wallpaper, destination, logo=None):
    templates = Path(__file__).resolve().parent / "boot-menu"
    shutil.copytree(templates, destination, dirs_exist_ok=True)
    logo = logo or Path(__file__).resolve().parents[1] / "branding/logo-horizontal-dark.png"
    with Image.open(wallpaper) as source, Image.open(logo) as brand:
        for directory, size in [("grub-pc", (800, 600)),
                                ("syslinux_common", (640, 480))]:
            # Letterbox rather than crop: the wallpaper includes a branded footer.
            background = ImageOps.pad(source.convert("RGB"), size,
                                      Image.Resampling.LANCZOS, color="#282828")
            background = ImageEnhance.Brightness(background).enhance(0.55)
            # Keep the wordmark above the menu and at its original contrast.
            mark = ImageOps.contain(brand.convert("RGBA"),
                                    (int(size[0] * 0.48), int(size[1] * 0.20)),
                                    Image.Resampling.LANCZOS)
            position = ((size[0] - mark.width) // 2, int(size[1] * 0.15))
            background.paste(mark, position, mark)
            background.save(destination / directory / "splash.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wallpaper", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--logo", type=Path, help="Override the bundled Nortica wordmark")
    args = parser.parse_args()
    prepare(args.wallpaper, args.destination, args.logo)
