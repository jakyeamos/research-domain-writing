#!/usr/bin/env bash
# Compatibility wrapper for `rdw install`.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
RDW_ROOT="$(cd "$INSTALL_DIR/.." && pwd)"
ARGS=(install --target all --source-root "$RDW_ROOT")
if [[ -n "${RDW_PROJECT_ROOT:-}" ]]; then
  ARGS+=(--project-root "$RDW_PROJECT_ROOT")
fi
PYTHONPATH="$RDW_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m rdw.cli "${ARGS[@]}"
