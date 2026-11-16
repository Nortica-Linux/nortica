# Nortica

## Build an image

Requires an amd64 Linux host, Docker, GNU Make, `flock` and internet access.

```sh
git clone --recurse-submodules https://github.com/Nortica-Linux/nortica.git
cd nortica
make iso                  # make does the same
make iso CONFIG_VERSION=latest
make clean                # remove build files and caches; keep iso/
```

Output: `iso/nortica-live-amd64.iso` and `iso/SHA256SUMS`.
`CONFIG_VERSION` defaults to the pinned config submodule commit; override it
with a config tag, commit or `latest` (current `main`). Build caches persist in
`.build/`. See [build details](image/README.md).

## Use it

1. Verify the image: `cd iso && sha256sum -c SHA256SUMS`.
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
