#!/usr/bin/env bash
# Real Docker/Make plumbing test using a synthetic builder, never an installer.
set -Eeuo pipefail
REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
TEST=$(mktemp -d -t nortica-make-container.XXXXXX)
cleanup() {
    local result=$?
    trap - EXIT
    if make --no-print-directory -C "$TEST" clean; then
        rm -rf -- "$TEST"
    else
        printf 'Fixture cleanup failed; retained at %s\n' "$TEST" >&2
        ((result != 0)) || result=1
    fi
    exit "$result"
}
trap cleanup EXIT
cp "$REPO/Makefile" "$TEST/Makefile"
mkdir -p "$TEST/image"
git -C "$TEST" init -q
git -C "$TEST" update-index --add --cacheinfo 160000 \
    1234567890abcdef1234567890abcdef12345678 config
git -C "$TEST" -c user.name=Fixture -c user.email=fixture@example.invalid \
    commit -qm 'Fixture config pin'
python3 - "$REPO/image/build.sh" "$TEST/image/build.sh" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).read_text()
publish = source[source.index("# Publish only after"):]
Path(sys.argv[2]).write_text('''#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/workspace
CONFIG_ROOT=/build/generated
if touch /workspace/should-be-readonly 2>/dev/null; then
    echo 'Source mount is writable' >&2
    exit 1
fi
[[ $NORTICA_BUILD_DIR == /build && -n $NORTICA_CONFIG_VERSION ]]
if [[ -f /build/root-only/cached ]]; then
    printf 'REUSED_CACHE\\n'
fi
mkdir -p /build/root-only "$CONFIG_ROOT"
chmod 700 /build/root-only
printf 'cached\\n' > /build/root-only/cached
printf 'synthetic ISO\\n' > "$CONFIG_ROOT/live-image.iso"
''' + publish)
PY
make --no-print-directory -C "$TEST" iso
make --no-print-directory -C "$TEST" > "$TEST/rebuild.log"
grep -q '^REUSED_CACHE$' "$TEST/rebuild.log"
images=("$TEST"/iso/*.iso)
[[ ${#images[@]} == 2 ]]
for image in "${images[@]}"; do
    [[ $(stat -c %u "$image") == "$(id -u)" ]]
    [[ $(stat -c %g "$image") == "$(id -g)" ]]
    [[ -s $image.sha256 ]]
done
(cd "$TEST/iso" && sha256sum -c ./*.iso.sha256)
make --no-print-directory -C "$TEST" clean
[[ ! -e $TEST/.build ]]
for image in "${images[@]}"; do [[ -s $image && -s $image.sha256 ]]; done
make --no-print-directory -C "$TEST" clean
printf 'PASS: Docker read-only source, cache reuse, output ownership and complete clean preserving ISO\n'
