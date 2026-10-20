#!/usr/bin/env bash
set -u

bin_dir="$HOME/.local/bin"

"$bin_dir/shotool" hotkey --remove 2>/dev/null
"$bin_dir/shotool" quit >/dev/null 2>&1
rm -f "$bin_dir/shotool" \
    "$HOME/.config/autostart/shotool.desktop" \
    "$HOME/.local/share/applications/shotool.desktop"

echo "Removed."
