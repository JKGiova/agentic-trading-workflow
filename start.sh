#!/usr/bin/env bash
# Install the locked runtime dependencies, then start the research terminal.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$project_dir"

uv_bin="$(command -v uv || true)"
if [[ -z "$uv_bin" ]]; then
    for candidate in "$project_dir/.tradebot/tools/uv" "${HOME:-}/.local/bin/uv" "${HOME:-}/.cargo/bin/uv"; do
        if [[ -x "$candidate" ]]; then
            uv_bin="$candidate"
            break
        fi
    done
fi

if [[ -z "$uv_bin" ]]; then
    printf 'Installing uv from Astral into .tradebot/tools...\n' >&2
    installer="$(mktemp "${TMPDIR:-/tmp}/tradebot-uv.XXXXXX")"
    trap 'rm -f -- "$installer"' EXIT
    if command -v curl >/dev/null 2>&1; then
        curl --fail --silent --show-error --location --retry 3 \
            https://astral.sh/uv/install.sh --output "$installer"
    elif command -v wget >/dev/null 2>&1; then
        wget --quiet --output-document="$installer" https://astral.sh/uv/install.sh
    else
        printf 'Install curl or wget, then run start.sh again.\n' >&2
        exit 1
    fi
    UV_UNMANAGED_INSTALL="$project_dir/.tradebot/tools" sh "$installer" >&2
    rm -f -- "$installer"
    trap - EXIT
    uv_bin="$project_dir/.tradebot/tools/uv"
    if [[ ! -x "$uv_bin" ]]; then
        printf 'uv installation failed: executable not found.\n' >&2
        exit 1
    fi
fi

printf 'Installing/checking locked dependencies (Python %s)...\n' "${TRADEBOT_PYTHON:-3.12}" >&2
"$uv_bin" sync --locked --no-dev --inexact --python "${TRADEBOT_PYTHON:-3.12}" >&2

if [[ $# -eq 0 ]]; then
    printf 'Starting the synthetic offline demo. Ctrl+Q exits.\n' >&2
    set -- --demo
fi
exec "$uv_bin" run --no-sync tradebot "$@"
