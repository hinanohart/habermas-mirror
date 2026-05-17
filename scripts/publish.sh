#!/usr/bin/env bash
#
# publish.sh — operator-side ship script for habermas-mirror 0.0.1.
#
# Why this exists: the Apache-2.0 decision to publish source under a
# specific GitHub identity is a human decision, not an autonomous one,
# so the project deliberately does NOT push to GitHub from any automated
# build or development path. This script bundles every remaining manual
# step into one ordered transcript so the maintainer can review and
# execute it from one terminal.
#
# Safety contract:
#   * No API token, password, or SSH key value is ever read into a
#     variable in this script. We only ever invoke `gh` (which uses its
#     own keyring) and `git push` (which uses the user's existing
#     credentials helper or SSH agent).
#   * Every destructive step prompts for explicit confirmation unless
#     `--yes` is passed.
#   * `--dry-run` prints the intended action set and exits 0 without
#     touching anything.
#
# Usage:
#   scripts/publish.sh                 # interactive, confirm each step
#   scripts/publish.sh --dry-run       # print plan and exit
#   scripts/publish.sh --yes           # non-interactive (CI-friendly)
#
# Preconditions checked at runtime:
#   - working tree clean, on branch `main`
#   - `gh` CLI installed and authenticated (we run `gh auth status`,
#     which never prints the token value)
#   - 29/29 pytest pass and `web/dist/` builds — the script reminds you
#     to run these manually rather than running them itself, because
#     they are slow and reviewers should see their output in the same
#     shell they are using to ship.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TAG="v0.0.1"
REPO_NAME="habermas-mirror"
REPO_DESCRIPTION="Self-hostable re-implementation of the prompted Habermas Machine (Tessler et al., Science 2024)."
RELEASE_NOTES_FILE="RELEASE_NOTES.md"
RELEASE_TITLE="habermas-mirror 0.0.1"

DRY_RUN=0
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y)  ASSUME_YES=1 ;;
    -h|--help)
      sed -n '2,40p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "publish.sh: unknown argument: $arg" >&2
      exit 64
      ;;
  esac
done

confirm() {
  local prompt="$1"
  if [[ "$ASSUME_YES" -eq 1 ]]; then
    echo "  [--yes] auto-confirmed: $prompt"
    return 0
  fi
  read -r -p "  $prompt [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

step() {
  echo
  echo "==> $1"
}

run() {
  local description="$1"
  shift
  echo "  $ $*"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    return 0
  fi
  "$@"
}

#
# Step 1 — preflight
#
step "Preflight: working tree, branch, and gh auth status"

if ! git -C "$REPO_ROOT" diff --quiet || ! git -C "$REPO_ROOT" diff --cached --quiet; then
  echo "FATAL: working tree has uncommitted changes. Commit or stash before publish." >&2
  exit 1
fi

current_branch="$(git -C "$REPO_ROOT" symbolic-ref --short HEAD)"
if [[ "$current_branch" != "main" ]]; then
  echo "FATAL: must be on branch 'main' (you are on '$current_branch')." >&2
  exit 1
fi

if git -C "$REPO_ROOT" remote get-url origin >/dev/null 2>&1; then
  echo "NOTE: an 'origin' remote already exists — skipping 'gh repo create'."
  REMOTE_EXISTS=1
else
  REMOTE_EXISTS=0
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "FATAL: 'gh' CLI not found. Install from https://cli.github.com and run 'gh auth login'." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "FATAL: 'gh auth status' failed. Run 'gh auth login' interactively (NOT inside this script)." >&2
  exit 1
fi

echo "  preflight OK (branch=main, clean, gh authed)"

#
# Step 2 — manual reminders (we deliberately do NOT run these)
#
step "Reminders the maintainer should have already done"
cat <<'EOF'
  [ ] pytest    : ran inside venv, expected 29/29 green
  [ ] vite      : `cd web && npm install && npm run build` shows '✓ built in ...'
  [ ] CHANGELOG : 'Post-audit hardening' and 'Post-final-audit polish' sections present
  [ ] LICENSE   : Apache-2.0, NOTICE attribution unchanged
  [ ] DB files  : `git status` shows no *.db / *.db-wal / *.db-shm
  [ ] author    : `git log -1 --format='%an <%ae>'` is the human maintainer, not "Claude"
EOF

#
# Step 3 — plan
#
step "Plan (in order)"
if [[ "$REMOTE_EXISTS" -eq 0 ]]; then
  echo "  1. gh repo create --public --source=. --remote=origin"
else
  echo "  1. (skipped — origin remote already configured)"
fi
echo "  2. git push -u origin main"
echo "  3. git tag -a $TAG -m '$RELEASE_TITLE'"
echo "  4. git push origin $TAG"
echo "  5. gh release create $TAG -F $RELEASE_NOTES_FILE --title '$RELEASE_TITLE'"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo
  echo "--dry-run: stopping here without executing."
  exit 0
fi

if [[ "$ASSUME_YES" -eq 0 ]]; then
  confirm "Proceed with all five steps above?" || { echo "Aborted."; exit 0; }
fi

#
# Step 4 — execute
#
if [[ "$REMOTE_EXISTS" -eq 0 ]]; then
  step "Creating GitHub repository"
  if confirm "gh repo create '$REPO_NAME' --public — make it PUBLIC?"; then
    run "create remote repo" gh repo create "$REPO_NAME" \
      --public \
      --source="$REPO_ROOT" \
      --remote=origin \
      --description="$REPO_DESCRIPTION" \
      --disable-issues=false \
      --disable-wiki=true
  else
    echo "Aborted before 'gh repo create'."
    exit 0
  fi
fi

step "Pushing main"
confirm "git push -u origin main?" && \
  run "push main" git -C "$REPO_ROOT" push -u origin main

step "Tagging $TAG"
if git -C "$REPO_ROOT" rev-parse "$TAG" >/dev/null 2>&1; then
  echo "  tag $TAG already exists locally — skipping create."
else
  confirm "git tag -a $TAG?" && \
    run "create tag" git -C "$REPO_ROOT" tag -a "$TAG" -m "$RELEASE_TITLE"
fi

step "Pushing $TAG"
confirm "git push origin $TAG?" && \
  run "push tag" git -C "$REPO_ROOT" push origin "$TAG"

step "Creating GitHub Release"
confirm "gh release create $TAG -F $RELEASE_NOTES_FILE?" && \
  run "create release" gh release create "$TAG" \
    -F "$RELEASE_NOTES_FILE" \
    --title "$RELEASE_TITLE"

step "Done"
echo "  habermas-mirror $TAG published. Verify in browser:"
gh repo view --web --json url --jq .url 2>/dev/null || echo "  (gh repo view --web)"
