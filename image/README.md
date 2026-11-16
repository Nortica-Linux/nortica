# Image build

Run [`build.sh`](build.sh) in a disposable Debian 13 Trixie amd64 environment
as root. The Docker command in the [root README](../README.md) provides one.
Never run the builder directly on a workstation: it changes APT sources and
installs packages in its build environment.

- Output: `dist/nortica-live-amd64.iso` and `dist/SHA256SUMS`.
- Working files: `/tmp/nortica-live-build`, overridable with `NORTICA_BUILD_DIR`.
- Desktop packages: [`deploy/vars.sh`](../deploy/vars.sh).
- User configuration: the exact commit checked out in the `config` submodule.
  Initialize it with `git submodule update --init --recursive` before building.
- Boot menus: [`boot-menu/`](boot-menu/); backgrounds use the bundled wallpaper.

The image includes a Debian bootstrap archive and a local APT repository for
all installer GPU profiles. Installation still needs network access. Packages
are resolved at build time; builds are not byte-for-byte reproducible.

The live account is `liveuser`. TTY1 autologin starts Hyprland; the installer
runs through a restricted sudo launcher. Installed accounts do not autologin.
The live desktop uses NetworkManager, Mesa and the stock Plymouth spinner.

## Releases

Pushing a `v*` tag runs [the image workflow](../.github/workflows/live-image.yml)
and publishes the ISO and checksums. Large images are split into numbered
assets. Download every part and `SHA256SUMS`, then run:

```sh
cat nortica-live-amd64.iso.part.* > nortica-live-amd64.iso
sha256sum -c SHA256SUMS
```

Only x86-64 UEFI with Secure Boot disabled is supported. Image generation does
not establish physical GPU compatibility; see [validation](../tests/README.md).
