#!/usr/bin/env bash
# Scaffold a new domain pack from _template
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ID="${1:?Usage: new-domain.sh <domain-id> <Display Name>}"
NAME="${2:-$ID}"
DEST="$ROOT/domains/$ID"
if [[ -d "$DEST" ]]; then
  echo "exists: $DEST" >&2
  exit 1
fi
cp -R "$ROOT/domains/_template" "$DEST"
sed -i '' "s/_template/$ID/g" "$DEST/domain-config.yaml" 2>/dev/null || sed -i "s/_template/$ID/g" "$DEST/domain-config.yaml"
sed -i '' "s/Template Domain/$NAME/g" "$DEST/domain-config.yaml" 2>/dev/null || sed -i "s/Template Domain/$NAME/g" "$DEST/domain-config.yaml"
mkdir -p "$ROOT/knowledge/$ID"
echo "Created $DEST and knowledge/$ID"
echo "Next: register in config/domains.yaml"
