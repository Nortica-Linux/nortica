# Config release tag/commit, or latest to follow config's main branch.
CONFIG_VERSION = v1.1.0
DOCKER ?= docker

.DEFAULT_GOAL := iso
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.NOTPARALLEL:

BLUE  := \033[1;34m
GREEN := \033[1;32m
RED   := \033[1;31m
RESET := \033[0m
ifneq ($(strip $(NO_COLOR)$(filter dumb,$(TERM))),)
BLUE  :=
GREEN :=
RED   :=
RESET :=
endif

LOCK := $(shell git rev-parse --git-path nortica-build.lock)

.PHONY: iso clean

iso:
	@exec 9>"$(LOCK)"
	flock -n 9 || { printf 'Another build or clean is running.\n' >&2; exit 1; }
	printf '$(BLUE)[Build]$(RESET) Nortica ISO · config %s\n' "$(CONFIG_VERSION)"
	[[ ! -L .build && ! -L iso ]] || { printf 'Refusing symlinked build/output directories.\n' >&2; exit 1; }
	mkdir -p .build iso
	$(DOCKER) run --rm --init --privileged --network host \
	  --volume "$(CURDIR):/workspace:ro" \
	  --volume "$(CURDIR)/.build:/build" \
	  --volume "$(CURDIR)/iso:/workspace/iso" \
	  --workdir /workspace \
	  --env NORTICA_BUILD_DIR=/build \
	  --env NORTICA_CONFIG_VERSION="$(CONFIG_VERSION)" \
	  --env NORTICA_OUTPUT_UID="$$(id -u)" --env NORTICA_OUTPUT_GID="$$(id -g)" \
	  debian:trixie-slim bash image/build.sh
	printf '$(GREEN)[Done]$(RESET) Timestamped ISO and checksum in iso/\n'

clean:
	@exec 9>"$(LOCK)"
	flock -n 9 || { printf 'Another build or clean is running.\n' >&2; exit 1; }
	printf '$(RED)[Clean]$(RESET) Build files and caches (keeping iso/)\n'
	[[ ! -L .build ]] || { printf 'Refusing a symlinked build directory.\n' >&2; exit 1; }
	if [[ -d .build ]]; then
	  $(DOCKER) run --rm --volume "$(CURDIR)/.build:/build" \
	    debian:trixie-slim sh -c 'find /build -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +'
	  rmdir .build
	fi
