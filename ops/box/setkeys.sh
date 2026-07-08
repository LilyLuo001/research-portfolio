#!/usr/bin/env bash
# setkeys.sh — enter the L1 API keys the easy, safe way.
#
# Prompts for each key one at a time with the input HIDDEN (like a password
# field), and writes them to ops/box/.env (git-ignored, chmod 600). The keys
# never echo to the screen, never enter a chat, and never touch the repo.
#
# Re-runnable: press Enter to KEEP the current value for a key (shown as …abcd),
# so you can update just one without retyping the rest.
#
#   ops/box/setkeys.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENVFILE="$ROOT/ops/box/.env"
VARS=(DEEPSEEK_API_KEY KIMI_API_KEY GLM_API_KEY QWEN_API_KEY GEMINI_API_KEY)

# load any existing values so a blank answer keeps them
declare -A cur
if [ -f "$ENVFILE" ]; then
  while IFS='=' read -r k v; do
    [[ "$k" =~ ^[A-Z_]+$ ]] && cur["$k"]="$v"
  done < "$ENVFILE"
fi

echo "Enter your L1 API keys (input is hidden). Press Enter to keep the current value."
echo

declare -A vals
for var in "${VARS[@]}"; do
  existing="${cur[$var]:-}"
  hint=""
  [ -n "$existing" ] && hint=" [keep …${existing: -4}]"
  printf '  %s%s: ' "$var" "$hint" >&2
  IFS= read -rs val || true
  echo >&2                                   # newline after the hidden input
  [ -z "$val" ] && val="$existing"
  vals["$var"]="$val"
done

# write atomically, owner-only perms
umask 177
tmp="$(mktemp "${ENVFILE}.XXXXXX")"
{
  echo "# L1 API keys — box-only, git-ignored. Managed by ops/box/setkeys.sh"
  for var in "${VARS[@]}"; do
    printf '%s=%s\n' "$var" "${vals[$var]}"
  done
} > "$tmp"
mv "$tmp" "$ENVFILE"
chmod 600 "$ENVFILE"

# gentle, non-blocking format sanity checks (no secret is printed)
warn() { printf '  ! %s\n' "$*" >&2; }
[ -n "${vals[GEMINI_API_KEY]}" ] && [[ "${vals[GEMINI_API_KEY]}" != AIza* ]] && \
  warn "GEMINI_API_KEY doesn't look like an AI-Studio key (AIza…); if auth fails, get an API key at aistudio.google.com."
for v in DEEPSEEK_API_KEY KIMI_API_KEY QWEN_API_KEY; do
  [ -n "${vals[$v]}" ] && [[ "${vals[$v]}" != sk-* ]] && warn "$v usually starts with 'sk-' — double-check it."
done

echo
echo "Wrote $ENVFILE (chmod 600). Set keys:"
for var in "${VARS[@]}"; do
  if [ -n "${vals[$var]}" ]; then echo "  ✓ $var  …${vals[$var]: -4}"; else echo "  · $var  (blank)"; fi
done
echo
echo "Next:  python ops/runner/dispatch.py --workers    # each provided key should read LIVE"
