#!/usr/bin/env bash
set -euo pipefail

# Publish only the nlpproj source to the requested GitHub repository.
# Run in a VS Code terminal with Git and GitHub authentication available.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE="https://github.com/doughn1g/NLP.git"
if ! command -v git >/dev/null 2>&1; then
  PORTABLE_GIT="$PROJECT_ROOT/.local-tools/git/usr/bin/git"
  if [[ ! -x "$PORTABLE_GIT" ]]; then
    echo "Git is unavailable. Run 'bash install_portable_git.sh' in a networked terminal first." >&2
    exit 1
  fi
  export PATH="$(dirname "$PORTABLE_GIT"):$PATH"
  export GIT_EXEC_PATH="$PROJECT_ROOT/.local-tools/git/usr/lib/git-core"
fi

WORK_DIR="$(mktemp -d /tmp/nlpproj-push.XXXXXX)"
REPO_DIR="$WORK_DIR/repo"
SOURCE_ARCHIVE="$WORK_DIR/source.tar"
echo "Working copy: $WORK_DIR"

git clone -- "$REMOTE" "$REPO_DIR"

sources=(
  .gitignore AGENTS.md AGENTS.override.md README.md USAGE_GUIDE.md requirements.txt
  baseline.py build_idiom_draft.py export_excel.py
  prepare_models.sh download_new_models.sh run_four_idioms.sh
  install_portable_git.sh publish_to_github.sh
  data tests legacy
)
tar -C "$PROJECT_ROOT" --exclude='*/__pycache__' --exclude='*.pyc' \
  -cf "$SOURCE_ARCHIVE" "${sources[@]}"

conflicts=0
while IFS= read -r item; do
  [[ "$item" == */ ]] && continue
  source="$PROJECT_ROOT/$item"
  target="$REPO_DIR/$item"
  if [[ -e "$target" ]] && ! cmp -s -- "$source" "$target"; then
    echo "Existing repository file differs: $item" >&2
    conflicts=1
  fi
done < <(tar -tf "$SOURCE_ARCHIVE")
if (( conflicts )); then
  echo "Stopped before changing or pushing the repository. Review the existing files in $REPO_DIR." >&2
  exit 1
fi

tar -C "$REPO_DIR" -xf "$SOURCE_ARCHIVE"
git -C "$REPO_DIR" add -- "${sources[@]}"
if git -C "$REPO_DIR" diff --cached --quiet; then
  echo "No source changes to push."
  exit 0
fi

echo "Files staged for the commit:"
git -C "$REPO_DIR" diff --cached --stat
if [[ -n "${PUBLISH_AUTHOR_NAME:-}" || -n "${PUBLISH_AUTHOR_EMAIL:-}" ]]; then
  git -C "$REPO_DIR" config user.name "${PUBLISH_AUTHOR_NAME:-doughn1g}"
  if [[ -z "${PUBLISH_AUTHOR_EMAIL:-}" ]]; then
    echo "PUBLISH_AUTHOR_EMAIL is required when overriding the commit identity." >&2
    exit 1
  fi
  git -C "$REPO_DIR" config user.email "$PUBLISH_AUTHOR_EMAIL"
elif ! git -C "$REPO_DIR" var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
  git -C "$REPO_DIR" config user.name "${PUBLISH_AUTHOR_NAME:-doughn1g}"
  git -C "$REPO_DIR" config user.email "${PUBLISH_AUTHOR_EMAIL:-doughn1g@users.noreply.github.com}"
fi
git -C "$REPO_DIR" commit -m "Add four-model idiom translation baseline"
git -C "$REPO_DIR" push -u origin HEAD
echo "Pushed commit $(git -C "$REPO_DIR" rev-parse --short HEAD) to $REMOTE"
