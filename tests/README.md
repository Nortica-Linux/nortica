# Validation

## Host-safe tests

Requires Bash, GNU Make, `flock`, Python 3, Git, Lua 5.4, Pillow and `pyte`.
On Debian, the Python dependencies are `python3-pil` and `python3-pyte`.

```sh
python3 -m unittest discover -v -s tests -p 'test_*.py'
```

Tests cover configuration and confirmation guards, GPU profiles, mocked disk
operations, failure propagation, cleanup, networking, config tags/commits/latest,
Make targets, cache reuse, ISO publication, user setup, Hyprland callbacks,
boot assets and terminal redraw/resize/interrupts.
They never install to host disks. Run as a normal user to exercise user setup.

```sh
for file in install.sh image/*.sh lib/*.sh deploy/*.sh deploy/scripts/*.sh \
  config/*.sh config/scripts/*/*.sh tests/*.sh; do bash -n "$file"; done
shellcheck -x install.sh image/*.sh lib/*.sh deploy/*.sh deploy/scripts/*.sh \
  config/*.sh config/scripts/*/*.sh tests/*.sh
```

With Docker available, test the real Make/Docker mounts and root-owned cache
cleanup using a synthetic builder (no real image build or disk operations):

```sh
bash tests/make-container.sh
```

## Disposable container tests

Mount the checkout read-only at `/repo` inside a fresh Debian Trixie container.
Never run these fixtures on the host:

- `bash /repo/tests/container-check.sh`: real user ownership, offline systemd
  links, all graphics profiles, login guards and failure-policy restoration.
  Requires `zsh`, `systemd`, `sudo`, `python3`, `xdg-user-dirs` and `procps`.
- `bash /repo/tests/package-plans.sh`: real APT transaction simulations for all
  profiles. Requires root and network access; does not install the desktop.

## Installation tests

Use disposable UEFI VMs with new virtual disks, no host block devices and no
writable host service-manager sockets. Copy the checkout into the guest before
running it; do not edit source while installation is executing.

Check clean and desktop installs, single/mirrored disks, encryption and swap
on/off, then reboot and verify unlock, login, networking and TTY1 desktop startup.
For mirrors, verify both ESPs and boot with either disk unavailable. Keep serial
transcripts and `/var/log/nortica-install/` logs. Unit tests and image generation
are not substitutes for these installation checks or physical GPU testing.

`nvme-storage.sh` is a destructive storage-only fixture for a disposable UEFI
Debian live guest. It requires two new virtual NVMe disks with serials
`INSTALLER_TEST_A` and `INSTALLER_TEST_B` (12 GiB or larger). It tests residual
filesystem signatures across single/mirror, swap and encryption combinations.
It does not establish full-install or reboot compatibility.
