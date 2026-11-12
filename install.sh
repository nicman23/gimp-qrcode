#!/bin/sh
# Install the plug-in to ~/.local/share/gimp-barcode and link it into GIMP's
# plug-in folder, so the git clone can be moved or deleted afterwards.
set -e
src=$(dirname "$0")/gimp-barcode.py
dest=${XDG_DATA_HOME:-$HOME/.local/share}/gimp-barcode/gimp-barcode.py
ver=$(gimp-console --version 2>/dev/null | grep -o '[0-9]*\.[0-9]*' | head -1)
plugins=${XDG_CONFIG_HOME:-$HOME/.config}/GIMP/${ver:-3.2}/plug-ins/gimp-barcode

install -Dm755 "$src" "$dest"
mkdir -p "$plugins"
ln -sf "$dest" "$plugins/gimp-barcode.py"
echo "Installed $dest, linked from $plugins. Restart GIMP."
python3 -c 'import qrcode' 2>/dev/null || echo "Note: QR codes need the qrcode library (pacman -S python-qrcode)."
