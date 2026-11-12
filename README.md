# gimp-qrcode

A GIMP 3 Python plug-in that creates EAN-13 and Code 128 barcodes and QR codes as new images.

- **File → Create → EAN-13 Barcode...**: 12 digits (check digit is added) or 13 digits (check digit is verified), module width, bar height, optional digits under the bars.
- **File → Create → Code 128 Barcode...**: printable ASCII text (code set B; an even-length string of digits uses the more compact set C), same size options as EAN-13.
- **File → Create → QR Code...**: text, box size, border, error correction level.

EAN-13 and Code 128 need nothing beyond GIMP. QR codes need the `qrcode` Python library (`pacman -S python-qrcode` / `pip install qrcode`).

## Install

GIMP wants the plug-in in a folder of the same name:

```sh
mkdir -p ~/.config/GIMP/3.2/plug-ins/gimp-barcode
ln -s "$PWD/gimp-barcode.py" ~/.config/GIMP/3.2/plug-ins/gimp-barcode/
chmod +x gimp-barcode.py
```

Restart GIMP. `python3 gimp-barcode.py test` runs the EAN-13 and Code 128 self-checks.

Originally a GIMP 2 QR plug-in by Isman Siete (2016).
