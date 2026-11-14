#!/usr/bin/env bash
set -euo pipefail

# Install Git under this project without sudo. Requires an Ubuntu package mirror.
# Run from a networked terminal: bash install_portable_git.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$PROJECT_ROOT/.local-tools/git"
PACKAGE_DIR="$PROJECT_ROOT/.local-tools/packages"
APT_LISTS="$PROJECT_ROOT/.local-tools/apt-lists"

if command -v git >/dev/null 2>&1; then
  git --version
  exit 0
fi
if [[ -x "$TOOLS_DIR/usr/bin/git" ]]; then
  "$TOOLS_DIR/usr/bin/git" --version
  exit 0
fi
if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "This portable installer needs apt-get and dpkg-deb." >&2
  exit 1
fi

mkdir -p "$PACKAGE_DIR" "$TOOLS_DIR" "$APT_LISTS/partial"
cd "$PACKAGE_DIR"
apt-get -o "Dir::State::lists=$APT_LISTS" update
apt-get -o "Dir::State::lists=$APT_LISTS" download git
packages=(git_*_amd64.deb)
if [[ ! -f "${packages[0]}" ]]; then
  echo "Git package download did not produce an amd64 .deb file." >&2
  exit 1
fi
dpkg-deb -x "${packages[0]}" "$TOOLS_DIR"
export GIT_EXEC_PATH="$TOOLS_DIR/usr/lib/git-core"
"$TOOLS_DIR/usr/bin/git" --version
if [[ ! -x "$GIT_EXEC_PATH/git-remote-https" ]]; then
  echo "The downloaded Git package lacks HTTPS support." >&2
  exit 1
fi
echo "Portable Git is ready. Run: bash publish_to_github.sh"
