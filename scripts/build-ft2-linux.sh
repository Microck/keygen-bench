#!/usr/bin/env bash
# Pinned Linux/no-MIDI build used by benchmark/Dockerfile.
set -euo pipefail
pin=6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d
repo=https://github.com/mova77/fast-tracker2.git
root=${1:-/tmp/keygen-ft2-build}
[[ $(uname -s) == Linux ]] || { echo 'This recipe is Linux-only.' >&2; exit 1; }
[[ ! -e "$root" ]] || { echo 'Choose a new build directory; refusing overwrite.' >&2; exit 1; }
for tool in git pkg-config "${CC:-cc}"; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
pkg-config --exists sdl2 libmicrohttpd || {
  echo 'Install SDL2 and libmicrohttpd development packages first.' >&2; exit 1;
}
git clone --no-checkout "$repo" "$root"
git -C "$root" checkout --detach "$pin"
[[ $(git -C "$root" rev-parse HEAD) == "$pin" ]]
cd "$root"
mkdir -p release/other
# These are compiler flags, intentionally expanded into separate arguments.
read -r -a cflags <<< "$(pkg-config --cflags sdl2 libmicrohttpd)"
read -r -a libs <<< "$(pkg-config --libs sdl2 libmicrohttpd)"
"${CC:-cc}" -DNDEBUG -O2 -pthread "${cflags[@]}" \
  src/gfxdata/*.c src/mixer/*.c src/scopes/*.c \
  src/modloaders/*.c src/smploaders/*.c src/*.c \
  "${libs[@]}" -lm -o release/other/ft2-clone
printf 'Source commit: %s\nBinary: %s/release/other/ft2-clone\n' "$pin" "$PWD"
printf 'Next: run tools/ft2_smoke.py from the Keygen Bench repository.\n'
