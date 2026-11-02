#!/usr/bin/env bash
# One-command, idempotent development environment setup. Safe to run
# repeatedly and after every pull.
set -euo pipefail

cd "$(dirname "$0")/.."

log() { printf '==> %s\n' "$*"; }
die() { printf 'bootstrap: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v uv >/dev/null || die "uv is required: https://docs.astral.sh/uv/getting-started/installation/"

log "installing the pinned Python and the locked dependencies"
uv sync --frozen --group dev

log "verifying"
uv run ruff check -q .
uv run pytest -q

log "bootstrap complete"
