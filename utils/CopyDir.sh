#!/usr/bin/env bash

# Copy a flattened acts-overrides variant onto ACTS/source/.
# Files are stored flat with '/' encoded as '_'; this script decodes
# the path back and copies into ACTS/source/.

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    echo "Please run this script, do not source it."
    return 1
fi

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 <variant>"
    exit 1
fi

variant="$1"
source_base="acts-overrides"
target_base="ACTS/source"

source_dir="$source_base/$variant"

if [[ ! -d "$source_dir" ]]; then
    echo "Error: directory '$source_dir' does not exist."
    exit 1
fi

nested_files="$(find "$source_dir" -mindepth 2 -type f \
    \( -name "*.cpp" -o -name "*.hpp" -o -name "*.h" -o -name "*.ipp" \
       -o -name "*.py" -o -name "CMakeLists.txt" \) -print)"
if [[ -n "$nested_files" ]]; then
    echo "Error: variant '$variant' has source files in subdirectories:"
    while IFS= read -r nested; do
        echo "    $nested"
    done <<< "$nested_files"
    echo "  CopyDir.sh expects flat top-level files with underscore-encoded paths,"
    echo "  e.g. Core/src/Foo.cpp -> Core_src_Foo.cpp at the variant root."
    echo "  Rename or delete these files (and remove the now-empty subdirs)."
    exit 1
fi

if [[ ! -d "$target_base" ]]; then
    echo "Error: target base directory '$target_base' does not exist."
    exit 1
fi

copied_any=0
skipped_any=0

while IFS= read -r -d '' file; do
    encoded="$(basename -- "$file")"
    decoded="${encoded//_/\/}"

    target_file="$target_base/$decoded"
    target_dir="$(dirname -- "$target_file")"

    mkdir -p -- "$target_dir"

    # cp bumps mtime, which would force a full cmake rebuild every time
    # build_environment() runs. Skip identical files to preserve mtime.
    if [[ -f "$target_file" ]] && cmp -s -- "$file" "$target_file"; then
        skipped_any=$((skipped_any + 1))
        continue
    fi

    cp -- "$file" "$target_file"

    echo "Copied '$file' -> '$target_file'"
    copied_any=1
done < <(find "$source_dir" -maxdepth 1 -type f -print0)

if [[ "$copied_any" -eq 0 && "$skipped_any" -eq 0 ]]; then
    echo "No files were copied from '$source_dir'."
elif [[ "$skipped_any" -gt 0 ]]; then
    echo "Skipped $skipped_any unchanged file(s) from '$source_dir' (mtime preserved)."
fi
