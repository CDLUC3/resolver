#!/usr/bin/env bash

#
# Author: Jake Zimmerman <jake@zimmerman.io>
#
# A simple script to build an HTML file using Pandoc
#
# Modified by Dave V for this project.

set -euo pipefail

usage() {
  echo "usage: $0 <source.md> <dest.html>"
}

# ----- args and setup -----

src="${1:-}"
dest="${2:-}"
if [ "$src" = "" ] || [ "$dest" = "" ]; then
  2>&1 usage
  exit 1
fi

case "$src" in
  -h|--help)
    usage
    exit
    ;;
esac

if command -v grealpath &> /dev/null; then
  realpath="grealpath"
elif command -v realpath &> /dev/null; then
  realpath="realpath"
else
  2>&1 echo "$0: This script requires GNU realpath. Install it with:"
  2>&1 echo "    brew install coreutils"
  exit 1
fi

# ----- main -----

dest_dir="$(dirname "$dest")"
mkdir -p "$dest_dir"

echo "DEST = ${dest}"
echo "SRC = ${src}"

codebraid \
   pandoc \
  --katex \
  --from markdown+tex_math_single_backslash+all_symbols_escapable \
  --to gfm \
  --toc \
  -s \
  --wrap=none \
  --output "$dest" \
  --overwrite \
  "$src"