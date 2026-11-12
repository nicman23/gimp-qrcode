# gimp-qrcode

A GIMP 3 Python plug-in that creates EAN-13 barcodes and QR codes as new images.

- **File → Create → EAN-13 Barcode...**: 12 digits (check digit is added) or 13 digits (check digit is verified), module width, bar height, optional digits under the bars.
- **File → Create → QR Code...**: text, box size, border, error correction level.

EAN-13 needs nothing beyond GIMP. QR codes need the `qrcode` Python library (`pacman -S python-qrcode` / `pip install qrcode`).

## Install

GIMP wants the plug-in in a folder of the same name:

```sh
mkdir -p ~/.config/GIMP/3.2/plug-ins/gimp-barcode
ln -s "$PWD/gimp-barcode.py" ~/.config/GIMP/3.2/plug-ins/gimp-barcode/
chmod +x gimp-barcode.py
```

Restart GIMP. `python3 gimp-barcode.py test` runs the EAN-13 self-check.

Originally a GIMP 2 QR plug-in by Isman Siete (2016).
