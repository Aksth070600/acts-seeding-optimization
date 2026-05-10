#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$REPO_ROOT/ACTS/source/build"
JOBS="${ACTS_BUILD_JOBS:-$(nproc)}"

if [[ ! -d "$BUILD_DIR" ]]; then
  echo "error: build directory not found: $BUILD_DIR" >&2
  echo "Run environment/setupACTS.sh first to create the initial build." >&2
  exit 1
fi

cmake --build "$BUILD_DIR" -j"$JOBS"
