#!/usr/bin/env bash
set -Eeuo pipefail
set +x
umask 022

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=deploy/vars.sh
source "$ROOT/deploy/vars.sh"
IMAGE_ROOT="$ROOT/image"
BUILD_ROOT=${NORTICA_BUILD_DIR:-/tmp/nortica-live-build}
APT_CACHE="$BUILD_ROOT/apt-cache"
REPO_ROOT="$BUILD_ROOT/cache-repo"
CONFIG_ROOT="$BUILD_ROOT/live-config"
CONFIG_SOURCE_DIR="$BUILD_ROOT/nortica-config-source"
DEBIAN_MIRROR=https://deb.debian.org/debian
RELEASE=trixie

[[ $EUID == 0 ]] || { echo 'Run image/build.sh as root inside Debian Trixie.' >&2; exit 1; }
[[ $(dpkg --print-architecture) == amd64 ]] || { echo 'The live image currently supports amd64 only.' >&2; exit 1; }
source /etc/os-release
[[ ${ID:-} == debian && ${VERSION_CODENAME:-} == trixie ]] || {
    echo 'Build in a Debian 13 Trixie environment.' >&2
    exit 1
}
CONFIG_VERSION=${NORTICA_CONFIG_VERSION:?Build via make iso; set CONFIG_VERSION in Makefile.}

# Cache package downloads across disposable container runs.
install -d "$BUILD_ROOT/build-apt-cache/partial"
printf 'Dir::Cache::archives "%s";\n' "$BUILD_ROOT/build-apt-cache" \
    > /etc/apt/apt.conf.d/80-nortica-cache
rm -f /etc/apt/apt.conf.d/docker-clean

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git

# shellcheck source=image/config.sh
source "$IMAGE_ROOT/config.sh"
prepare_config_source "$CONFIG_VERSION" "$CONFIG_SOURCE_DIR"
if grep -qi thunar "$CONFIG_SOURCE_DIR/dotfiles/hypr/hyprland.lua"; then
    echo 'Selected config still launches Thunar. Publish the sms config and update CONFIG_VERSION before building.' >&2
    exit 1
fi

# Rebuild generated configuration and roots, retaining live-build's bootstrap
# and package caches. Never reuse a previously configured desktop root.
install -d "$CONFIG_ROOT"
find "$CONFIG_ROOT" -mindepth 1 -maxdepth 1 ! -name cache -exec rm -rf -- {} +
install -d "$APT_CACHE/partial" "$REPO_ROOT/pool" "$CONFIG_ROOT/config/package-lists" \
    "$CONFIG_ROOT/config/archives" "$CONFIG_ROOT/config/includes.chroot/opt/nortica-install" \
    "$CONFIG_ROOT/config/hooks/normal"
{
    printf 'deb %s %s main contrib non-free non-free-firmware\n' "$DEBIAN_MIRROR" "$RELEASE"
    printf 'deb http://deb.debian.org/debian %s-backports main contrib non-free non-free-firmware\n' "$RELEASE"
    printf 'deb %s %s-updates main contrib non-free non-free-firmware\n' "$DEBIAN_MIRROR" "$RELEASE"
    printf 'deb https://security.debian.org/debian-security %s-security main contrib non-free non-free-firmware\n' "$RELEASE"
} > /etc/apt/sources.list.d/nortica-image-build.list
rm -f /etc/apt/sources.list.d/debian.sources
curl --fail --location --retry 3 --output "$BUILD_ROOT/nickh-archive-keyring.deb" \
    https://pkg.noctalia.dev/deb/nickh-archive-keyring.deb
curl --fail --location --retry 3 --output /etc/apt/sources.list.d/noctalia-trixie.sources \
    https://pkg.noctalia.dev/deb/noctalia-trixie.sources
dpkg -i "$BUILD_ROOT/nickh-archive-keyring.deb"
apt-get update

backports_packages=("${BACKPORTS_PACKAGES[@]/%//trixie-backports}")
mapfile -t base_packages < <(bash "$IMAGE_ROOT/package-manifest.sh" base)
apt-get --download-only --reinstall -o "Dir::Cache::archives=$APT_CACHE" \
    -o APT::Get::Assume-Yes=true install "${base_packages[@]}"

for profile in intel amd nvidia nouveau vm; do
    printf 'Caching Debian and desktop packages for %s...\n' "$profile"
    GPU_DRIVER=$profile VM_GUEST=qemu VM_SOFTWARE_RENDERING=false \
        bash "$ROOT/deploy/deploy.sh" --dry-run > "$BUILD_ROOT/deploy-$profile.txt"
    mapfile -t cache_packages < <(bash "$IMAGE_ROOT/package-manifest.sh" cache "$profile")
    cache_packages+=("${backports_packages[@]}")
    apt-get --download-only --reinstall \
        -o "Dir::Cache::archives=$APT_CACHE" \
        -o APT::Get::Assume-Yes=true \
        -t trixie-backports install "${cache_packages[@]}"
done
# Keep both VM guest integrations because the profile is selected at install time.
for guest_package in qemu-guest-agent open-vm-tools; do
    apt-get --download-only --reinstall -o "Dir::Cache::archives=$APT_CACHE" \
        -o APT::Get::Assume-Yes=true install "$guest_package"
done
# Keep the NVIDIA profile on the supported stock Trixie kernel track.
apt-get --download-only --reinstall -o "Dir::Cache::archives=$APT_CACHE" \
    -o APT::Get::Assume-Yes=true install linux-image-amd64 linux-headers-amd64

# Resolve target packages before installed build helpers constrain the solver.
apt-get install -y --no-install-recommends \
    live-build debootstrap xorriso squashfs-tools syslinux-common isolinux \
    grub-pc-bin grub-efi-amd64-bin dpkg-dev apt-utils git rsync python3 python3-pil

find "$APT_CACHE" -maxdepth 1 -type f -name '*.deb' -exec cp -n -t "$REPO_ROOT/pool" -- {} +
[[ -n $(find "$REPO_ROOT/pool" -maxdepth 1 -type f -name '*.deb' -print -quit) ]] || {
    echo 'APT did not create any cached package files.' >&2; exit 1;
}
(
    cd "$REPO_ROOT"
    dpkg-scanpackages pool /dev/null > Packages
)
python3 "$ROOT/deploy/scripts/install-tools.py" --download-only --cache "$REPO_ROOT/tools"
gzip -9 -c "$REPO_ROOT/Packages" > "$REPO_ROOT/Packages.gz"
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin=Nortica \
    -o APT::FTPArchive::Release::Label=Nortica \
    -o APT::FTPArchive::Release::Suite=trixie \
    -o APT::FTPArchive::Release::Codename=trixie \
    -o APT::FTPArchive::Release::Components=main \
    release "$REPO_ROOT" > "$REPO_ROOT/Release"

if [[ ! -s $REPO_ROOT/debootstrap-trixie-amd64.tar ]]; then
    debootstrap --make-tarball="$REPO_ROOT/debootstrap-trixie-amd64.tar" \
        --arch=amd64 --components=main,contrib,non-free,non-free-firmware \
        "$RELEASE" "$BUILD_ROOT/debootstrap-base" "$DEBIAN_MIRROR"
fi

mapfile -t live_packages < <(bash "$IMAGE_ROOT/package-manifest.sh" live)
printf '%s\n' "${live_packages[@]}" > "$CONFIG_ROOT/config/package-lists/nortica.list.chroot"
printf 'deb http://deb.debian.org/debian %s-backports main contrib non-free non-free-firmware\n' \
    "$RELEASE" > "$CONFIG_ROOT/config/archives/debian-backports.list.chroot"
rsync -a --exclude='/.git/' --exclude='/AGENTS.md' --exclude='/dist/' \
    --exclude='/.build/' --exclude='/iso/' \
    --exclude='/tests/' --exclude='/image/' --exclude='__pycache__/' --exclude='*.pyc' \
    --exclude='/.image-build-work/' \
    --exclude='/.agents/' --exclude='/.aws/' --exclude='/.codex/' \
    "$ROOT/" "$CONFIG_ROOT/config/includes.chroot/opt/nortica-install/"
rm -rf "$CONFIG_ROOT/config/includes.chroot/opt/nortica-install/config"
git clone --local --no-hardlinks "$CONFIG_SOURCE_DIR" \
    "$CONFIG_ROOT/config/includes.chroot/opt/nortica-install/config"
git clone --local --no-hardlinks "$CONFIG_SOURCE_DIR" \
    "$CONFIG_ROOT/config/includes.chroot/opt/nortica-config"
install -D -m 644 "$IMAGE_ROOT/live-assets/nortica-install.png" \
    "$CONFIG_ROOT/config/includes.chroot/usr/share/pixmaps/nortica-install.png"
install -D -m 644 "$IMAGE_ROOT/live-assets/nortica-install.desktop" \
    "$CONFIG_ROOT/config/includes.chroot/usr/share/nortica-live/nortica-install.desktop"
install -d "$CONFIG_ROOT/config/includes.chroot/opt/nortica-install/cache"
cp -a "$REPO_ROOT/." "$CONFIG_ROOT/config/includes.chroot/opt/nortica-install/cache/"
cat > "$CONFIG_ROOT/config/hooks/normal/0100-nortica-live.hook.chroot" <<'HOOK'
#!/bin/bash
set -Eeuo pipefail
set +x
getent group sudo >/dev/null || groupadd sudo
id liveuser >/dev/null 2>&1 || useradd --create-home --groups sudo --shell /bin/bash liveuser
systemctl --root=/ --no-reload enable NetworkManager.service
systemctl --root=/ --no-reload disable \
    systemd-networkd.service systemd-networkd.socket \
    systemd-networkd-wait-online.service systemd-resolved.service networking.service
systemctl --root=/ --no-reload mask \
    systemd-networkd.service systemd-networkd.socket systemd-resolved.service \
    networking.service
install -d -m 755 /etc/tmpfiles.d
printf '%s\n' 'L+ /etc/resolv.conf - - - - /run/NetworkManager/resolv.conf' \
    > /etc/tmpfiles.d/nortica-network.conf
install -d -o liveuser -g liveuser -m 755 /opt/media/wall
install -o liveuser -g liveuser -m 644 \
    /opt/nortica-install/config/wallpapers/nortica.png \
    /opt/media/wall/nortica.png
install -d -m 755 /etc/sudoers.d
printf 'liveuser ALL=(root) NOPASSWD: /opt/nortica-install/install.sh\n' \
    > /etc/sudoers.d/nortica-live-installer
chmod 440 /etc/sudoers.d/nortica-live-installer
cat > /usr/local/bin/nortica-install <<'EOF'
#!/bin/sh
exec sudo /opt/nortica-install/install.sh "$@"
EOF
chmod 755 /usr/local/bin/nortica-install
install -d -m 755 /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin liveuser --noclear %I $TERM
EOF
install -d -o liveuser -g liveuser -m 755 /home/liveuser/.local
git clone --local --no-hardlinks /opt/nortica-config \
    /home/liveuser/.local/nortica-config
git -C /home/liveuser/.local/nortica-config remote set-url origin \
    https://github.com/Nortica-Linux/config.git
git -C /home/liveuser/.local/nortica-config checkout -B main HEAD
git -C /home/liveuser/.local/nortica-config config branch.main.remote origin
git -C /home/liveuser/.local/nortica-config config branch.main.merge refs/heads/main
chown -R liveuser:liveuser /home/liveuser/.local/nortica-config
GPU_DRIVER=intel VM_GUEST=none VM_SOFTWARE_RENDERING=false \
    NORTICA_CONFIG_DIR=/home/liveuser/.local/nortica-config \
    bash /opt/nortica-install/deploy/deploy.sh --chroot liveuser
python3 /opt/nortica-install/deploy/scripts/disable-live-lock.py \
    /home/liveuser/.local/state/noctalia/settings.toml
chown liveuser:liveuser /home/liveuser/.local/state/noctalia/settings.toml
printf 'FRAMEBUFFER=y\n' > /etc/initramfs-tools/conf.d/plymouth
plymouth-set-default-theme spinner
update-initramfs -u -k all
install -d -o liveuser -g liveuser -m 755 /home/liveuser/.local/share/applications
install -o liveuser -g liveuser -m 644 \
    /usr/share/nortica-live/nortica-install.desktop \
    /home/liveuser/.local/share/applications/nortica-install.desktop
HOOK
chmod 755 "$CONFIG_ROOT/config/hooks/normal/0100-nortica-live.hook.chroot"

cd "$CONFIG_ROOT"
python3 "$IMAGE_ROOT/prepare-boot-menu.py" \
    "$CONFIG_SOURCE_DIR/wallpapers/nortica.png" "$CONFIG_ROOT/config/bootloaders"
lb config \
    --distribution "$RELEASE" \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --cache true --cache-stages bootstrap \
    --bootappend-live 'boot=live components quiet splash hostname=nortica username=liveuser' \
    --archive-areas 'main contrib non-free non-free-firmware' \
    --apt-recommends false \
    --apt-indices false \
    --debian-installer false \
    --memtest none \
    --iso-application 'Nortica' \
    --iso-publisher 'Nortica' \
    --iso-volume 'NORTICA'
lb build

# Publish only after a successful build; never replace an earlier image.
install -d "$ROOT/iso"
stem="nortica-live-amd64-$(date -u +%Y%m%dT%H%M%SZ)"
filename="$stem.iso"
suffix=0
while [[ -e $ROOT/iso/$filename || -L $ROOT/iso/$filename ||
         -e $ROOT/iso/$filename.sha256 || -L $ROOT/iso/$filename.sha256 ]]; do
    ((suffix += 1))
    filename="$stem-$suffix.iso"
done
output=$(mktemp -d "$ROOT/iso/.publish.XXXXXX")
trap 'rm -rf -- "$output"' EXIT
find "$CONFIG_ROOT" -maxdepth 1 -type f -name '*.iso' -exec install -m 644 {} "$output/$filename" \;
[[ -s "$output/$filename" ]] || { echo 'live-build produced no ISO.' >&2; exit 1; }
(
    cd "$output"
    sha256sum "$filename" > "$filename.sha256"
)
if [[ -n ${NORTICA_OUTPUT_UID:-} && -n ${NORTICA_OUTPUT_GID:-} ]]; then
    chown "$NORTICA_OUTPUT_UID:$NORTICA_OUTPUT_GID" "$output/"*
fi
# Hard links publish complete files and refuse to clobber an existing name,
# even if another publisher bypasses Make's build lock.
ln -- "$output/$filename" "$ROOT/iso/$filename"
ln -- "$output/$filename.sha256" "$ROOT/iso/$filename.sha256"
printf 'Built %s (%s bytes).\n' "$ROOT/iso/$filename" \
    "$(stat -c %s "$ROOT/iso/$filename")"
