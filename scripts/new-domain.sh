#!/usr/bin/env bash
# Compatibility wrapper for `rdw new-domain`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m rdw.cli new-domain "$@" --root "$ROOT"
