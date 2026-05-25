#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="multitenant-backend"
ROOT="$(cd "$(dirname "$0")" && pwd)"
GH_BIN="$ROOT/.tools/gh"

install_gh() {
  if [[ -x "$GH_BIN" ]]; then
    return
  fi
  echo "Installing GitHub CLI..."
  mkdir -p "$ROOT/.tools"
  local version
  version=$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['tag_name'].lstrip('v'))")
  local arch zip_name extract_dir
  arch=$(uname -m)
  if [[ "$arch" == "arm64" ]]; then
    zip_name="gh_${version}_macOS_arm64.zip"
  else
    zip_name="gh_${version}_macOS_amd64.zip"
  fi
  curl -fsSL -o /tmp/gh.zip "https://github.com/cli/cli/releases/download/v${version}/${zip_name}"
  unzip -qo /tmp/gh.zip -d /tmp/gh_extract
  extract_dir="/tmp/gh_extract/gh_${version}_macOS_${arch/arm64/arm64}"
  extract_dir="${extract_dir/_amd64/amd64}"
  if [[ "$arch" != "arm64" ]]; then
    extract_dir="/tmp/gh_extract/gh_${version}_macOS_amd64"
  fi
  install -m 755 "${extract_dir}/bin/gh" "$GH_BIN"
  rm -rf /tmp/gh.zip /tmp/gh_extract
}

install_gh

if ! "$GH_BIN" auth status &>/dev/null; then
  echo ""
  echo ">>> Log in to GitHub (browser will open). Approve access, then return here."
  echo ""
  "$GH_BIN" auth login -h github.com -p https -w
fi

cd "$ROOT"

if "$GH_BIN" repo view "$REPO_NAME" &>/dev/null; then
  echo "Repository $REPO_NAME already exists."
  if ! git remote get-url origin &>/dev/null; then
    origin=$("$GH_BIN" repo view "$REPO_NAME" --json url -q .url)
    git remote add origin "${origin}.git"
  fi
  git push -u origin main
else
  echo "Creating private repo $REPO_NAME and pushing..."
  "$GH_BIN" repo create "$REPO_NAME" --private --source=. --remote=origin --push
fi

echo ""
echo "Done. Repo URL:"
"$GH_BIN" repo view "$REPO_NAME" --json url -q .url
echo ""
echo "Next: deploy on Render → https://dashboard.render.com"
echo "  Connect this repo, start command:"
echo "  uvicorn main:app --host 0.0.0.0 --port \$PORT"
