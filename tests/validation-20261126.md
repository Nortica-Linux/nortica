# Validation — 2026-11-26

## Automated checks

- 89 host-safe unit tests passed, including tool checksums, packaging, brand
  assets, wallpaper and boot-menu generation.
- Disposable Debian 13 container deployment checks passed for all graphics
  profiles, including user ownership, offline services and failure cleanup.
- Real APT transaction simulations passed for Intel, AMD, NVIDIA, Nouveau and VM.
- The synthetic Make/Docker cache, mount and cleanup fixture passed.

## Tool integration: `8af799a`, config `v1.1.0`

Built and checksum-verified `nortica-live-amd64-20261126T225254Z.iso`.
Booted in an isolated UEFI/KVM VM with accelerated Virtio graphics:

- Hyprland and Noctalia started; Thunar was absent.
- Super+E opened sms; dzi displayed the wallpaper.
- Opening a sample PDF through `xdg-open` launched mzp and rendered the document.
- A fixture using the installer's real functions completed an installation to a
  new, serial-number-guarded 40 GiB virtual disk (single disk, no encryption or
  swap, VM graphics profile, DHCP).
- After removing the ISO, the target booted from `zroot/ROOT/debian` with kernel
  `6.12.118+deb13-amd64`. Logging in on TTY1 started Hyprland and Noctalia.
  Networking was active and folder/image/PDF associations selected sms/dzi/mzp.
- A test-only serial debug shell was removed/disabled after collecting evidence.

## Branding: `f50c0ad` / release `v1.1.0`, config `v1.2.0`

Built and checksum-verified `nortica-live-amd64-20261126T230932Z.iso`.
Booted this image in UEFI/KVM and visually checked the branded GRUB menu and
live desktop. Super+E opened sms and Hyprland reported no configuration errors.
The installed wallpaper and installer-icon hashes matched the supplied assets.
This branded image was boot-tested; the full installation/reboot test above
used the immediately preceding tool-integration image.

These checks do not establish physical GPU compatibility, Secure Boot support,
or mirror/encryption/swap installation coverage. They also do not exercise the
complete guided installation UI. See [the validation guide](README.md) for the
remaining matrix.
