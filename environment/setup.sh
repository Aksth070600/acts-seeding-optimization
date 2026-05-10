#!/usr/bin/env bash
# Override the gperftools install prefix with ACTS_GPERF_DIR
# (default: $HOME/usr/local). Matches environment/setupACTS.sh.

HOME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
ACTS_SOURCE="$HOME_DIR/ACTS/source"
PYTHON_SETUP_REL="build/python/setup.sh"
CVMFS_SETUP="/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/setup.sh"
GPERF_DIR="${ACTS_GPERF_DIR:-$HOME/usr/local}"

# Save caller shell options so we can restore them before returning.
__SETUP_OLD_OPTS="$(set +o 2>/dev/null || true)"

setup_env() {
  local oldpwd rc odd_src odd_lib fetched
  oldpwd="$(pwd 2>/dev/null || printf '%s' "$HOME")"

  # Never let setup failures kill the shell
  set +e +u
  set +o pipefail 2>/dev/null || true

  # 1. LCG / CVMFS
  if [[ ! -f "$CVMFS_SETUP" ]]; then
    echo "LCG setup file not found: $CVMFS_SETUP"
    echo "  (is CVMFS mounted and the Apptainer image configured?)"
    return 0
  fi

  source "$CVMFS_SETUP" >/dev/null 2>&1
  rc=$?
  set +e +u
  set +o pipefail 2>/dev/null || true

  if [[ $rc -eq 0 ]]; then
    echo "LCG was successfully sourced."
  else
    echo "LCG sourcing failed (rc=$rc)."
    return 0
  fi

  # 2. ACTS Python setup
  if [[ ! -d "$ACTS_SOURCE" || ! -f "$ACTS_SOURCE/$PYTHON_SETUP_REL" ]]; then
    echo "ACTS Python setup not found at $ACTS_SOURCE/$PYTHON_SETUP_REL."
    echo "  Run: bash environment/setupACTS.sh"
    return 0
  fi

  cd "$ACTS_SOURCE" >/dev/null 2>&1 || {
    echo "ACTS environment setup failed: cannot cd $ACTS_SOURCE"
    cd "$oldpwd" >/dev/null 2>&1 || true
    return 0
  }

  source "$PYTHON_SETUP_REL" >/dev/null 2>&1
  rc=$?
  set +e +u
  set +o pipefail 2>/dev/null || true

  if [[ $rc -eq 0 ]]; then
    echo "ACTS environment was successfully sourced."
  else
    echo "ACTS environment setup failed (rc=$rc)."
    cd "$oldpwd" >/dev/null 2>&1 || true
    return 0
  fi

  cd "$HOME_DIR" >/dev/null 2>&1 || cd "$oldpwd" >/dev/null 2>&1 || true

  # 3. OpenDataDetector (optional)
  odd_src=""
  odd_lib=""

  if [[ -d "$ACTS_SOURCE/thirdparty/OpenDataDetector/data" ]]; then
    odd_src="$ACTS_SOURCE/thirdparty/OpenDataDetector"
    if [[ -d "$ACTS_SOURCE/build/thirdparty/OpenDataDetector/factory" ]]; then
      odd_lib="$ACTS_SOURCE/build/thirdparty/OpenDataDetector/factory"
    elif [[ -d "$ACTS_SOURCE/build/thirdparty/OpenDataDetector" ]]; then
      odd_lib="$ACTS_SOURCE/build/thirdparty/OpenDataDetector"
    fi
  elif [[ -d "$ACTS_SOURCE/build/_deps" ]]; then
    fetched="$(find "$ACTS_SOURCE/build/_deps" -maxdepth 2 -type d -name odd-src 2>/dev/null | head -n 1)"
    if [[ -n "$fetched" ]]; then
      odd_src="$fetched"
      if [[ -d "$ACTS_SOURCE/build/_deps/odd-build/factory" ]]; then
        odd_lib="$ACTS_SOURCE/build/_deps/odd-build/factory"
      elif [[ -d "$ACTS_SOURCE/build/_deps/odd-build" ]]; then
        odd_lib="$ACTS_SOURCE/build/_deps/odd-build"
      fi
    fi
  fi

  if [[ -n "$odd_src" ]]; then
    export ODD_PATH="$odd_src"
    if [[ -n "$odd_lib" && -d "$odd_lib" ]]; then
      export LD_LIBRARY_PATH="$odd_lib:${LD_LIBRARY_PATH:-}"
    fi
    echo "OpenDataDetector environment was successfully configured."
  else
    unset ODD_PATH >/dev/null 2>&1 || true
    echo "OpenDataDetector not found, skipping setup."
  fi

  # 4. gperftools (optional)
  if [[ -d "$GPERF_DIR/lib" ]]; then
    export LD_LIBRARY_PATH="$GPERF_DIR/lib:${LD_LIBRARY_PATH:-}"
    export PATH="$GPERF_DIR/bin:${PATH:-}"
    echo "gperftools environment was successfully configured."
  else
    echo "gperftools not found at $GPERF_DIR, skipping setup."
  fi

  # 5. Verify bindings file exists
  if ! compgen -G "$ACTS_SOURCE/build/python/acts/ActsPythonBindings*.so" >/dev/null; then
    echo "ACTS Python bindings file not found under $ACTS_SOURCE/build/python/acts/."
    echo "  Try running: source environment/build.sh"
    return 0
  fi

  # 6. Verify Python import
  if python3 -c "import acts" >/dev/null 2>&1; then
    echo "ACTS Python bindings verified successfully."
  else
    echo "ACTS Python bindings verification failed."
    echo "  Try running: source environment/build.sh"
  fi

  return 0
}

setup_env

eval "$__SETUP_OLD_OPTS" >/dev/null 2>&1 || true
set +e +u
set +o pipefail 2>/dev/null || true

return 0 2>/dev/null || exit 0
