# Image build

`make` / `make iso` runs the builder in a disposable privileged Debian 13
container. Source is mounted read-only; only `.build/` and `iso/` are writable.
Build and clean operations share a lock and cannot run concurrently.

- `CONFIG_VERSION` in `Makefile`: config release tag or commit.
  Set it to `latest` to fetch config's current `main`.
- `.build/`: downloaded packages, config checkout, bootstrap archive and
  live-build caches. Generated roots are rebuilt so configuration changes apply.
- `iso/`: UTC-timestamped ISOs and matching `.iso.sha256` files, owned by the
  invoking user. Earlier builds are never overwritten; same-second collisions
  receive a numeric suffix.
- `make clean`: removes `.build/`, including root-owned files; preserves `iso/`.
  Shared Docker images are not deleted.

Both live and installed desktops use the selected config commit. The developer's
submodule checkout is not changed. Packages are resolved at build time; builds
are not byte-for-byte reproducible. A failed build does not publish an image.

Desktop packages are listed in [`deploy/vars.sh`](../deploy/vars.sh). Boot menus
are under [`boot-menu/`](boot-menu/). The live account is `liveuser`; installed
accounts do not autologin.

`image/build.sh` is the internal container entry point. Use Make rather than
running it on a workstation: it changes APT sources and installs packages.

## Releases

Pushing a `v*` tag runs [the image workflow](../.github/workflows/live-image.yml)
and publishes the ISO and checksums. Large images are split into numbered
assets. Download every part and the matching `.iso.sha256` file. Using the
actual timestamped image name:

```sh
image=nortica-live-amd64-20261116T120000Z.iso
cat "$image".part.* > "$image"
sha256sum -c "$image.sha256"
```

Only x86-64 UEFI with Secure Boot disabled is supported. Image generation does
not establish physical GPU compatibility; see [validation](../tests/README.md).
