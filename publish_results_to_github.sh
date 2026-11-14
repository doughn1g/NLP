#!/usr/bin/env bash
set -euo pipefail

# Publish the curated four-model result snapshot to doughn1g/NLP.
# Clone first, then edit only README's marked results section and the snapshot.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE="${PUBLISH_REMOTE:-https://github.com/doughn1g/NLP.git}"
if ! command -v git >/dev/null 2>&1; then
  PORTABLE_GIT="$PROJECT_ROOT/.local-tools/git/usr/bin/git"
  if [[ ! -x "$PORTABLE_GIT" ]]; then
    echo "Git is unavailable. Run 'bash install_portable_git.sh' in a networked terminal first." >&2
    exit 1
  fi
  export PATH="$(dirname "$PORTABLE_GIT"):$PATH"
  export GIT_EXEC_PATH="$PROJECT_ROOT/.local-tools/git/usr/lib/git-core"
fi

WORK_DIR="$(mktemp -d /tmp/nlpproj-results-push.XXXXXX)"
REPO_DIR="$WORK_DIR/repo"
echo "Working copy: $WORK_DIR"
git clone -- "$REMOTE" "$REPO_DIR"

mkdir -p "$REPO_DIR/published_results/idioms_to_en_75"
cp -a "$PROJECT_ROOT/published_results/idioms_to_en_75/." "$REPO_DIR/published_results/idioms_to_en_75/"
cp "$PROJECT_ROOT/publish_results_to_github.sh" "$REPO_DIR/publish_results_to_github.sh"

python3 - "$PROJECT_ROOT/README.md" "$REPO_DIR/README.md" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
remote_path = Path(sys.argv[2])
remote = remote_path.read_text(encoding="utf-8") if remote_path.exists() else "# Idiom translation comparison\n"
begin = "<!-- BEGIN PUBLIC RESULTS -->"
end = "<!-- END PUBLIC RESULTS -->"
if source.count(begin) != 1 or source.count(end) != 1:
    raise SystemExit("Local README must have exactly one marked results section")
section = source[source.index(begin):source.index(end) + len(end)]
if begin in remote or end in remote:
    if remote.count(begin) != 1 or remote.count(end) != 1:
        raise SystemExit("Remote README has incomplete or repeated results markers; review manually")
    updated = remote[:remote.index(begin)] + section + remote[remote.index(end) + len(end):]
else:
    lines = remote.splitlines(keepends=True)
    insert_at = 1 if lines and lines[0].startswith("# ") else 0
    lines.insert(insert_at, "\n" + section + "\n")
    updated = "".join(lines)
remote_path.write_text(updated, encoding="utf-8")
PY

git -C "$REPO_DIR" add -- README.md published_results/idioms_to_en_75 publish_results_to_github.sh
if git -C "$REPO_DIR" diff --cached --quiet; then
  echo "The published results and README section are already current."
  exit 0
fi

echo "Files staged for the commit:"
git -C "$REPO_DIR" diff --cached --stat
if [[ -n "${PUBLISH_AUTHOR_NAME:-}" || -n "${PUBLISH_AUTHOR_EMAIL:-}" ]]; then
  if [[ -z "${PUBLISH_AUTHOR_EMAIL:-}" ]]; then
    echo "PUBLISH_AUTHOR_EMAIL is required when overriding the commit identity." >&2
    exit 1
  fi
  git -C "$REPO_DIR" config user.name "${PUBLISH_AUTHOR_NAME:-doughn1g}"
  git -C "$REPO_DIR" config user.email "$PUBLISH_AUTHOR_EMAIL"
elif ! git -C "$REPO_DIR" var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
  git -C "$REPO_DIR" config user.name "doughn1g"
  git -C "$REPO_DIR" config user.email "doughn1g@users.noreply.github.com"
fi
git -C "$REPO_DIR" commit -m "Publish preliminary four-model idiom results"
git -C "$REPO_DIR" push -u origin HEAD
echo "Pushed commit $(git -C "$REPO_DIR" rev-parse --short HEAD) to $REMOTE"
