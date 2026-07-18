#!/usr/bin/env bash
#
# Executive Distribution — self-host update script.
#
# ‼️  DATA SAFETY: This script ONLY updates application CODE. It NEVER touches
#     MongoDB or the uploads volume, so all user, admin, and site data — plus any
#     settings you changed in the admin dashboard — persist across every update.
#     Do NOT add any `mongo`, `dropDatabase`, `rm -rf uploads`, or reseed commands here.
#
# Point the backend env var UPDATE_SCRIPT at this file to enable the dashboard
# "Apply update" button on self-hosted deployments:
#     UPDATE_SCRIPT=/app/deploy/update.sh
#
# Configure these to match your server:
REPO_DIR="${REPO_DIR:-/app}"              # working tree that is a git checkout of your repo
BRANCH="${UPDATE_BRANCH:-main}"

set -euo pipefail
echo "[update] $(date -u) starting update on branch ${BRANCH}"

cd "${REPO_DIR}"

# 1) Pull latest code only (leaves databases & volumes untouched)
git fetch --all --prune
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

# 2) Backend dependencies
if [ -f backend/requirements.txt ]; then
  echo "[update] installing backend deps"
  pip install -r backend/requirements.txt
fi

# 3) Frontend build
if [ -f frontend/package.json ]; then
  echo "[update] building frontend"
  ( cd frontend && yarn install --frozen-lockfile && yarn build )
fi

# 4) Restart services (data stores are external and keep running)
echo "[update] restarting services"
sudo supervisorctl restart backend frontend || true

echo "[update] $(date -u) update complete — data preserved"
