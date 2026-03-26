#!/usr/bin/env bash
# ============================================================
# cost-guard.sh — PreToolUse hook for Bash commands
# PURPOSE: Block commands that generate excessive token output
#          (wildcard greps, massive tree reads, large cat dumps).
# EXIT 0  = allow the command
# EXIT 2  = block the command (stderr is shown to the agent)
# ============================================================

set -euo pipefail

# The full tool input JSON is passed as $1.
# Extract the actual command string from the JSON payload.
TOOL_INPUT="${1:-}"
COMMAND=$(echo "$TOOL_INPUT" | grep -oP '"command"\s*:\s*"\K[^"]+' 2>/dev/null || echo "$TOOL_INPUT")

# -----------------------------------------------
# BLOCKLIST — patterns that are token-expensive
# -----------------------------------------------

BLOCKED_PATTERNS=(
  # 1. Recursive wildcard greps without file-type filters
  'grep -r [^|]*\.\*'
  'grep -rn [^|]*\.\*'
  'grep --include=\* -r'
  'rg -uu'

  # 2. Full directory tree dumps (depth-unlimited)
  'find / '
  'find \. -name'
  'tree [^-]'
  'tree$'
  'ls -lR'

  # 3. Catting potentially huge files without head/tail
  'cat .*\.log'
  'cat .*\.csv'
  'cat .*\.json'
  'cat .*\.xml'

  # 4. Dumping entire virtual environments or node_modules
  'ls.*venv'
  'ls.*node_modules'
  'find.*node_modules'
  'find.*__pycache__'
  'find.*\.git '

  # 5. Unrestricted pip/poetry output
  'pip list'
  'pip freeze'

  # 6. Docker / system-level heavy reads
  'docker logs [^|]*$'
  'journalctl [^|]*$'
  'dmesg$'
)

# -----------------------------------------------
# CHECK — iterate over blocked patterns
# -----------------------------------------------

for pattern in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo "❌ BLOCKED by cost-guard hook." >&2
    echo "   Pattern matched: $pattern" >&2
    echo "   Original command: $COMMAND" >&2
    echo "" >&2
    echo "💡 Suggestion: Narrow the scope of your command." >&2
    echo "   • Use file-type filters (e.g., --include='*.py')" >&2
    echo "   • Limit depth (e.g., -maxdepth 2, tree -L 2)" >&2
    echo "   • Pipe through head/tail (e.g., | head -100)" >&2
    echo "   • Target specific directories instead of root" >&2
    exit 2
  fi
done

# -----------------------------------------------
# SAFEGUARD — warn on commands likely to produce >5000 lines
# -----------------------------------------------

if echo "$COMMAND" | grep -qE '(find|grep|rg|ag|ack)' && \
   ! echo "$COMMAND" | grep -qE '(head|tail|wc|-maxdepth|-L |--max-count|-m )'; then
  echo "⚠️  WARNING: Search/find command without output limiter detected." >&2
  echo "   Command: $COMMAND" >&2
  echo "   Consider adding: | head -100  or  -maxdepth 2" >&2
  # Allow but warn — exit 0 still permits execution
fi

exit 0
