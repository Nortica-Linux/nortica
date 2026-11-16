# Desktop deployment

`deploy.sh` installs Debian 13 desktop packages and configures services.
User configuration lives in [`config/`](../config), installed permanently at
`~/.local/nortica-config`. Package deployment scripts are staged temporarily
inside the target and removed before reboot.

## Usage

Run standalone as a normal sudo-capable Debian 13 user with a config checkout
at `~/.local/nortica-config`:

```sh
GPU_DRIVER=amd ./deploy/deploy.sh --dry-run
GPU_DRIVER=amd ./deploy/deploy.sh
```

The installer invokes explicit root-only chroot mode:

```sh
GPU_DRIVER=vm VM_GUEST=qemu VM_SOFTWARE_RENDERING=false \
  bash /opt/nortica-deploy/deploy.sh --chroot USER
```

Profiles: `intel`, `amd`, `nvidia`, `nouveau`, `vm`.
VM integration: `VM_GUEST=auto|qemu|vmware|none`; chroot requires a resolved value.
Set `VM_SOFTWARE_RENDERING=true` for software-rendered VMs. NVIDIA requires
stock Trixie kernels below 6.16 and matching headers; physical NVIDIA hardware
has not been validated.

Packages and services are listed in [`vars.sh`](vars.sh). Services are enabled
offline; a temporary `policy-rc.d` suppresses package-triggered starts and is
restored on success or failure. User setup runs with the selected user's HOME,
XDG paths and ownership, without passwordless sudo.

NetworkManager manages networking. Hyprland starts after interactive TTY1
login, not automatically at boot. Settings persist in
`~/.local/state/nortica/settings.sh`. To refresh only dotfiles and user setup,
run `~/.local/nortica-config/deploy.sh` as the desktop user.
