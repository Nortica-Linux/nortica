# Nortica

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="branding/logo-horizontal-dark.svg">
  <img src="branding/logo-horizontal-light.svg" alt="Nortica" width="420">
</picture>

## Build an image

Requires an amd64 Linux host, Docker, GNU Make, `flock` and internet access.

```sh
git clone --recurse-submodules https://github.com/Nortica-Linux/nortica.git
cd nortica
make iso                  # make does the same
make clean                # remove build files and caches; keep iso/
```

Output: `iso/nortica-live-amd64-YYYYMMDDTHHMMSSZ.iso` and a matching `.iso.sha256`.
Timestamps are UTC; previous images are kept.
Set `CONFIG_VERSION` in `Makefile` to a config release tag, commit or `latest`
(current `main`). Build caches persist in `.build/`.
See [build details](image/README.md). Brand assets and their integration points
are documented in [`branding/`](branding/README.md).

### Desktop tools

The amd64 desktop includes [sms](https://github.com/foelkdavid/sms) (files,
Super+E), [dzi](https://github.com/foelkdavid/dzi) (images), and
[mzp](https://github.com/foelkdavid/mzp) (PDFs), instead of Thunar.
Release versions and SHA-256 hashes are pinned in
`deploy/scripts/install-tools.py`. The image caches the archives for both live
and target deployment; standalone deployment downloads them. Binaries, launchers,
icons, PDFium and license notices install under `/usr/local`.

The desktop configuration is pinned to config `v1.2.0`. The builder rejects
older configurations that still launch Thunar. Existing installations are not
purged of previously installed Thunar packages automatically.

## Use it

1. Verify the image: `cd iso && sha256sum -c *.iso.sha256`.
2. Write the ISO to a USB drive using an image writer.
3. Boot it in **x86-64 UEFI mode with Secure Boot disabled**.
4. Open **Nortica Install** from the launcher, or run `nortica-install`.
5. Configure the installation and explicitly confirm the disks to erase.
6. Reboot without the USB and log in as your configured user.

Installation requires internet access. Desktop setup is optional; when enabled,
Hyprland starts after interactive login on TTY1. Legacy BIOS installation is
not supported. Logs: `/var/log/nortica-install/`.

For standard Debian 13 live media, clone this repository with submodules and
run `sudo ./install.sh`. See the [installation guide](step-by-step.md).
