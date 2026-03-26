#!/usr/bin/env bash
# ============================================================
# auto-test.sh — PostToolUse hook for Write/Edit actions
# PURPOSE: Auto-run pytest after any file mutation so the
#          agent gets immediate pass/fail feedback.
# EXIT 0  = tests passed (or non-Python file, skip gracefully)
# EXIT 1  = tests failed (stderr feedback sent to agent)
# ============================================================

set -uo pipefail

FILE_PATH="${1:-}"

# -----------------------------------------------
# SKIP — only run tests for Python file changes
# -----------------------------------------------

if [[ ! "$FILE_PATH" =~ \.py$ ]]; then
  echo "ℹ️  Skipping auto-test: non-Python file changed ($FILE_PATH)" >&2
  exit 0
fi

# -----------------------------------------------
# SKIP — ignore changes to test config / non-source files
# -----------------------------------------------

SKIP_PATTERNS=(
  'conftest.py'
  'setup.py'
  'setup.cfg'
  'pyproject.toml'
  '__init__.py'
  'migrations/'
  'alembic/'
)

for skip in "${SKIP_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -q "$skip"; then
    echo "ℹ️  Skipping auto-test: config/migration file ($FILE_PATH)" >&2
    exit 0
  fi
done

# -----------------------------------------------
# GUARD — check that the tests/ directory exists
# -----------------------------------------------

if [[ ! -d "tests/" ]]; then
  echo "⚠️  No tests/ directory found. Skipping auto-test." >&2
  exit 0
fi

# -----------------------------------------------
# RUN — execute pytest with strict limits
# -----------------------------------------------

echo "🧪 Auto-test triggered by change to: $FILE_PATH" >&2
echo "   Running: python -m pytest tests/ --maxfail=1 --timeout=30 -q" >&2

TEST_OUTPUT=$(python -m pytest tests/ --maxfail=1 --timeout=30 -q 2>&1) || TEST_EXIT=$?
TEST_EXIT=${TEST_EXIT:-0}

if [[ $TEST_EXIT -ne 0 ]]; then
  echo "" >&2
  echo "❌ TESTS FAILED (exit code: $TEST_EXIT)" >&2
  echo "────────────────────────────────────────" >&2
  # Limit output to last 40 lines to avoid token bloat
  echo "$TEST_OUTPUT" | tail -40 >&2
  echo "────────────────────────────────────────" >&2
  echo "💡 Fix the failing test before continuing." >&2
  exit 1
fi

echo "✅ All tests passed." >&2
exit 0
