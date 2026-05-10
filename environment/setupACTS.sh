#!/usr/bin/env bash
#
# One-time ACTS checkout + CMake configure + build, under the repo root.
# Produces <repo>/ACTS/source/ (the cloned repo, checked out to ACTS_VERSION)
# and <repo>/ACTS/source/build/ (the CMake build tree used by build.sh).
#
# Environment variables (all optional):
#   ACTS_VERSION       — git tag to check out (default: v44.0.0)
#   ACTS_BUILD_JOBS    — build parallelism (default: nproc)
#   ACTS_GPERF_DIR     — gperftools install prefix (default: $HOME/usr/local)
#   GIT_LFS_VERSION    — git-lfs release tag to install (default: v3.5.1)
#   GIT_LFS_PREFIX     — dir that git-lfs is installed into if missing
#                        (default: $HOME/usr/local/bin; already on PATH after
#                        environment/setup.sh via the gperftools config)

# If sourced, re-run the body in a subshell so the caller's shell survives
# any errexit failures (LCG source, git submodule init, cmake, ...).
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  bash "${BASH_SOURCE[0]}" "$@"
  return $?
fi

set -euo pipefail

ACTS_VERSION="${ACTS_VERSION:-v44.0.0}"
JOBS="${ACTS_BUILD_JOBS:-$(nproc)}"
GPERF_DIR="${ACTS_GPERF_DIR:-$HOME/usr/local}"
GIT_LFS_VERSION="${GIT_LFS_VERSION:-v3.5.1}"
GIT_LFS_PREFIX="${GIT_LFS_PREFIX:-$HOME/usr/local/bin}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ACTS_DIR="$REPO_ROOT/ACTS"
ACTS_SOURCE="$ACTS_DIR/source"
LCG_SETUP="/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/setup.sh"

if [[ ! -f "$LCG_SETUP" ]]; then
  echo "error: LCG setup file not found: $LCG_SETUP" >&2
  echo "  (is CVMFS mounted and the Apptainer image configured?)" >&2
  exit 1
fi

if [[ ! -d "$GPERF_DIR/lib" ]]; then
  echo "warning: gperftools not found at $GPERF_DIR (lib/ missing)." >&2
  echo "  ACTS will still configure, but ACTS_ENABLE_CPU_PROFILING may fail." >&2
fi

echo "Starting ACTS setup."
echo "  repo root : $REPO_ROOT"
echo "  ACTS dir  : $ACTS_DIR"
echo "  version   : $ACTS_VERSION"
echo "  jobs      : $JOBS"

mkdir -p "$ACTS_DIR"
cd "$ACTS_DIR"
mkdir -p source build

if [[ -x "$GIT_LFS_PREFIX/git-lfs" ]]; then
  export PATH="$GIT_LFS_PREFIX:$PATH"
  echo "git-lfs already at $GIT_LFS_PREFIX: $(git-lfs --version 2>&1 | head -n1)"
elif command -v git-lfs >/dev/null 2>&1; then
  echo "git-lfs already on PATH: $(git-lfs --version 2>&1 | head -n1)"
else
  case "$(uname -m)" in
    x86_64)  _lfs_arch="amd64" ;;
    aarch64) _lfs_arch="arm64" ;;
    *) echo "error: no git-lfs binary for $(uname -m)" >&2; exit 1 ;;
  esac
  _lfs_tarball="git-lfs-linux-${_lfs_arch}-${GIT_LFS_VERSION}.tar.gz"
  _lfs_url="https://github.com/git-lfs/git-lfs/releases/download/${GIT_LFS_VERSION}/${_lfs_tarball}"
  _lfs_tmp="$(mktemp -d)"
  echo "git-lfs not on PATH — installing ${GIT_LFS_VERSION} to ${GIT_LFS_PREFIX} ..."
  if ! curl -fsSL "$_lfs_url" -o "$_lfs_tmp/$_lfs_tarball"; then
    echo "error: failed to download $_lfs_url" >&2
    rm -rf "$_lfs_tmp"
    exit 1
  fi
  tar -xzf "$_lfs_tmp/$_lfs_tarball" -C "$_lfs_tmp"
  mkdir -p "$GIT_LFS_PREFIX"
  cp "$_lfs_tmp/git-lfs-${GIT_LFS_VERSION#v}/git-lfs" "$GIT_LFS_PREFIX/git-lfs"
  chmod +x "$GIT_LFS_PREFIX/git-lfs"
  rm -rf "$_lfs_tmp"
  export PATH="$GIT_LFS_PREFIX:$PATH"
  echo "git-lfs installed: $(git-lfs --version 2>&1 | head -n1)"
fi

git lfs install --skip-repo >/dev/null
echo "git-lfs filters registered."

if [[ ! -d source/.git ]]; then
  git clone --recursive https://github.com/acts-project/acts.git source/
  echo "ACTS repository was successfully cloned."
else
  echo "ACTS repository already exists, skipping clone."
fi

cd "$ACTS_SOURCE"

set +u
source "$LCG_SETUP"
set -u
echo "LCG was successfully sourced."

git fetch --tags
echo "ACTS tags were successfully fetched."

git checkout "$ACTS_VERSION"
echo "ACTS version $ACTS_VERSION was successfully checked out."

git submodule update --init --recursive
echo "ACTS submodules were successfully updated."

git submodule foreach --recursive 'git lfs pull || true'
echo "git-lfs content pulled across submodules."

cmake -B build -S . \
  -DCMAKE_BUILD_TYPE=Release \
  -DACTS_BUILD_EXAMPLES=ON \
  -DACTS_BUILD_EXAMPLES_PYTHON_BINDINGS=ON \
  -DACTS_BUILD_EXAMPLES_PYTHIA8=ON \
  -DACTS_BUILD_EXAMPLES_ROOT=ON \
  -DACTS_BUILD_EXAMPLES_DD4HEP=ON \
  -DACTS_BUILD_PLUGIN_DD4HEP=ON \
  -DACTS_BUILD_PLUGIN_JSON=ON \
  -DACTS_BUILD_PLUGIN_ROOT=ON \
  -DACTS_BUILD_PLUGIN_ONNX=ON \
  -DACTS_BUILD_FATRAS=ON \
  -DACTS_BUILD_ODD=ON \
  -DACTS_ENABLE_CPU_PROFILING=ON \
  -DACTS_GPERF_INSTALL_DIR="$GPERF_DIR"
echo "ACTS CMake configuration was successfully completed."

cmake --build build -j"$JOBS"
echo "ACTS build was successfully completed."

echo "ACTS setup finished successfully."
echo "Next: source environment/setup.sh to use the bindings from this shell."
