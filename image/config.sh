#!/usr/bin/env bash
# Source from the image builder; keep Git state in the disposable build cache.

prepare_config_source() {
    local version=$1 destination=$2
    local repository=${3:-https://github.com/Nortica-Linux/config.git} commit
    if [[ ! $version =~ ^[[:alnum:]][[:alnum:]._/-]*$ || $version == *..* ]]; then
        printf 'Invalid CONFIG_VERSION: use a config tag, commit, or latest.\n' >&2
        return 2
    fi
    if [[ ! -d $destination/.git ]]; then
        git clone --no-checkout "$repository" "$destination" || return
    else
        git -C "$destination" remote set-url origin "$repository" || return
    fi
    if [[ $version == latest ]]; then
        git -C "$destination" fetch --no-tags origin main || return
        commit=$(git -C "$destination" rev-parse --verify 'FETCH_HEAD^{commit}') || return
    elif ! commit=$(git -C "$destination" rev-parse --verify --quiet --end-of-options "$version^{commit}"); then
        git -C "$destination" fetch --no-tags origin "$version" || return
        commit=$(git -C "$destination" rev-parse --verify 'FETCH_HEAD^{commit}') || return
    fi
    git -C "$destination" checkout --detach --force "$commit" || return
    git -C "$destination" clean -ffd || return
    printf 'Using Nortica config %s (%s).\n' "$version" "$commit"
}
