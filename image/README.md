# Image build

`make` / `make iso` runs the builder in a disposable privileged Debian 13
container. Source is mounted read-only; only `.build/` and `iso/` are writable.
Build and clean operations share a lock and cannot run concurrently.

- `CONFIG_VERSION`: config tag or commit. Defaults to the main repository's
  pinned `config` submodule commit. `latest` fetches config's current `main`.
- `.build/`: downloaded packages, config checkout, bootstrap archive and
  live-build caches. Generated roots are rebuilt so configuration changes apply.
- `iso/`: completed ISO and `SHA256SUMS`, owned by the invoking user.
- `make clean`: removes `.build/`, including root-owned files; preserves `iso/`.
  Shared Docker images are not deleted.

Both live and installed desktops use the selected config commit. The developer's
submodule checkout is not changed. Packages are resolved at build time; builds
are not byte-for-byte reproducible. A failed build does not publish an image.

Desktop packages are listed in [`deploy/vars.sh`](../deploy/vars.sh). Boot menus
are under [`boot-menu/`](boot-menu/). The live account is `liveuser`; installed
accounts do not autologin.

For a native build, run `bash image/build.sh` as root in a disposable Debian 13
Trixie amd64 VM. Override its cache path with `NORTICA_BUILD_DIR` and config
selection with `NORTICA_CONFIG_VERSION`. Never run it directly on a workstation:
it changes APT sources and installs packages.

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
