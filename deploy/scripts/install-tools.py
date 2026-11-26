#!/usr/bin/env python3
"""Fetch checksum-pinned amd64 releases; install without executing vendor scripts."""
import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile

RELEASES = {
    "dzi": ("0.2.1", "dcfa618a3a55ca9ea474c8b278ec6c2a2a7423bd5c9fe8e98573c59c32732c06"),
    "sms": ("0.2.0", "eadb9e461aa9c9c99358526472a367839c530e6fc53e219b862ccba6698e8eef"),
    "mzp": ("0.2.1", "ddcf19c75bea565fd36bed3db99505cd1e300c2025b15860266f6db68e6c7dfb"),
}


def fetch(app, cache):
    version, digest = RELEASES[app]
    name = f"{app}-{version}-linux-x64-wayland"
    archive = cache / f"{name}.tar.gz"
    cache.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            download = Path(temporary) / "download"
            subprocess.run(["curl", "--fail", "--location", "--retry", "3", "--output", str(download),
                            f"https://github.com/foelkdavid/{app}/releases/download/v{version}/{archive.name}"], check=True)
            verify(download, digest)
            download.replace(archive)
    verify(archive, digest)
    return archive, name


def verify(path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Checksum mismatch: {path}; remove it and retry")


def install(app, archive, name, prefix):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        with tarfile.open(archive) as tar:
            tar.extractall(root, filter="data")
        source = root / name
        files = [(source / (f"bin/{app}" if app == "mzp" else app), prefix / "bin" / app, 0o755),
                 (source / f"{app}.svg", prefix / f"share/icons/hicolor/scalable/apps/{app}.svg", 0o644)]
        if app == "mzp":
            files.append((source / "lib/mzp/libpdfium.so", prefix / "lib/mzp/libpdfium.so", 0o755))
        for notice in (source / "licenses").rglob("*"):
            if notice.is_file():
                files.append((notice, prefix / "share" / app / "licenses" / notice.relative_to(source / "licenses"), 0o644))
        for src, dest, mode in files:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as staged:
                stage = Path(staged.name)
            try:
                shutil.copyfile(src, stage)
                stage.chmod(mode)
                stage.replace(dest)
            finally:
                stage.unlink(missing_ok=True)
        desktop = (source / f"{app}.desktop").read_text()
        if app == "sms":
            desktop = desktop.replace("Exec=sms\n", "Exec=sms --dir %f\n") + "MimeType=inode/directory;\n"
        dest = prefix / f"share/applications/{app}.desktop"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(desktop)
        dest.chmod(0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--prefix", type=Path, default=Path("/usr/local"))
    args = parser.parse_args()
    if platform.machine() not in ("x86_64", "amd64"):
        parser.error("dzi, sms and mzp releases require amd64")
    archives = [(app, *fetch(app, args.cache)) for app in RELEASES]
    if not args.download_only:
        for app, archive, name in archives:
            install(app, archive, name, args.prefix)


if __name__ == "__main__":
    main()
