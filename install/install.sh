#!/usr/bin/env bash
# Install /rdw slash commands and skills for Claude Code, Cursor, and Codex/agents.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
RDW_ROOT="$(cd "$INSTALL_DIR/.." && pwd)"
RDW_ROOT_ESC="${RDW_ROOT//\//\\/}"

substitute() {
  sed "s|__RDW_ROOT__|${RDW_ROOT}|g" "$1"
}

echo "RDW_ROOT=${RDW_ROOT}"

# --- Claude Code ---
CLAUDE_CMD="${HOME}/.claude/commands"
CLAUDE_SKILL="${HOME}/.claude/skills/research-domain-writing"
mkdir -p "$CLAUDE_CMD" "$CLAUDE_SKILL"

substitute "${INSTALL_DIR}/claude-commands/rdw.md" > "${CLAUDE_CMD}/rdw.md"
substitute "${INSTALL_DIR}/claude-commands/rdw-batch.md" > "${CLAUDE_CMD}/rdw-batch.md"
echo "Wrote ${CLAUDE_CMD}/rdw.md and rdw-batch.md"

rm -rf "$CLAUDE_SKILL"
ln -sfn "$RDW_ROOT" "$CLAUDE_SKILL"
echo "Linked ${CLAUDE_SKILL} -> ${RDW_ROOT}"

# --- Cursor (user-global) ---
CURSOR_SKILL="${HOME}/.cursor/skills"
mkdir -p "${CURSOR_SKILL}/rdw" "${CURSOR_SKILL}/rdw-batch"
substitute "${INSTALL_DIR}/cursor-skills/rdw/SKILL.md" > "${CURSOR_SKILL}/rdw/SKILL.md"
substitute "${INSTALL_DIR}/cursor-skills/rdw-batch/SKILL.md" > "${CURSOR_SKILL}/rdw-batch/SKILL.md"
echo "Wrote ${CURSOR_SKILL}/rdw and rdw-batch"

# --- Cursor (optional project-local install) ---
if [[ -n "${RDW_PROJECT_ROOT:-}" ]]; then
  PROJ_CURSOR="${RDW_PROJECT_ROOT}/.cursor/skills"
  mkdir -p "${PROJ_CURSOR}/rdw" "${PROJ_CURSOR}/rdw-batch"
  substitute "${INSTALL_DIR}/cursor-skills/rdw/SKILL.md" > "${PROJ_CURSOR}/rdw/SKILL.md"
  substitute "${INSTALL_DIR}/cursor-skills/rdw-batch/SKILL.md" > "${PROJ_CURSOR}/rdw-batch/SKILL.md"
  echo "Wrote project .cursor/skills under ${RDW_PROJECT_ROOT}"
fi

# --- Agents / Codex discovery ---
AGENTS_SKILL="${HOME}/.agents/skills/research-domain-writing"
mkdir -p "$(dirname "$AGENTS_SKILL")"
rm -rf "$AGENTS_SKILL"
ln -sfn "$RDW_ROOT" "$AGENTS_SKILL"
echo "Linked ${AGENTS_SKILL} -> ${RDW_ROOT}"

# --- Optional env ---
ENV_FILE="${HOME}/.config/research-domain-writing/env"
mkdir -p "$(dirname "$ENV_FILE")"
echo "RDW_ROOT=${RDW_ROOT}" > "$ENV_FILE"
echo "Wrote ${ENV_FILE}"

cat <<EOF

Installed slash commands:
  Claude Code:  /rdw, /rdw-batch
  Cursor:       /rdw, /rdw-batch  (user skills; restart Cursor if menu does not refresh)
  Agents/Codex: skill rdw (symlinked)

Optional project-local Cursor install:
  RDW_PROJECT_ROOT=/path/to/project ./install/install.sh

Examples:
  /rdw Task: Stat read for Brunson 2024-25 domain=basketball entity="Jalen Brunson" output-type=stat_interpretation depth=standard
  /rdw-batch examples/batch-tasks.yaml

Uninstall: rm ~/.claude/commands/rdw.md ~/.claude/commands/rdw-batch.md \\
           rm ~/.claude/skills/research-domain-writing \\
           rm -rf ~/.cursor/skills/rdw ~/.cursor/skills/rdw-batch \\
           rm -rf ~/.agents/skills/research-domain-writing
EOF
