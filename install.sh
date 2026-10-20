#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
bin_dir="$HOME/.local/bin"

missing=""
for pkg in python3-gi python3-gi-cairo gir1.2-gtk-3.0; do
    dpkg -s "$pkg" >/dev/null 2>&1 || missing="$missing $pkg"
done
[ -z "$missing" ] || sudo apt-get install -y $missing
/usr/bin/python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null || {
    echo "GTK bindings are not available to /usr/bin/python3." >&2
    exit 1
}

mkdir -p "$bin_dir" "$HOME/.config/autostart" "$HOME/.local/share/applications"
ln -sf "$root/bin/shotool" "$bin_dir/shotool"

cat > "$HOME/.config/autostart/shotool.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Shotool
Exec=$bin_dir/shotool daemon
NoDisplay=true
X-GNOME-Autostart-enabled=true
DESKTOP

cat > "$HOME/.local/share/applications/shotool.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Shotool
Comment=Smart screenshot tool
Exec=$bin_dir/shotool capture
Icon=applets-screenshooter
Categories=Utility;
DESKTOP

"$bin_dir/shotool" quit >/dev/null 2>&1 || true
sleep 0.6
if [ $# -gt 0 ]; then
    "$bin_dir/shotool" hotkey "$1"
else
    "$bin_dir/shotool" hotkey
fi
echo "Installed."
