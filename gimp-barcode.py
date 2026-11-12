#!/usr/bin/env python3
"""
GIMP 3 plug-in: create EAN-13 barcodes and QR codes as new images.

Isman Siete, 2016 (original GIMP 2 QR plug-in)
2026: ported to GIMP 3, EAN-13 added
"""

import sys

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, GObject, GLib

# EAN-13 encoding tables. R is the bitwise complement of L, G is R reversed.
L_CODES = ["0001101", "0011001", "0010011", "0111101", "0100011",
           "0110001", "0101111", "0111011", "0110111", "0001011"]
R_CODES = [c.translate(str.maketrans("01", "10")) for c in L_CODES]
G_CODES = [c[::-1] for c in R_CODES]
PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
          "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]
QUIET_LEFT, QUIET_RIGHT = 11, 7  # modules, per GS1 spec


def ean13_check_digit(digits12):
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits12))
    return str((10 - s % 10) % 10)


def ean13_normalize(code):
    """Return the full 13-digit code; accepts 12 digits (check digit added) or 13 (verified)."""
    code = code.strip().replace(" ", "").replace("-", "")
    if not code.isdigit() or len(code) not in (12, 13):
        raise ValueError(f"EAN-13 needs 12 or 13 digits, got {code!r}")
    check = ean13_check_digit(code[:12])
    if len(code) == 13 and code[12] != check:
        raise ValueError(f"Bad check digit in {code}: expected {check}")
    return code[:12] + check


def ean13_modules(code):
    """95-module bar pattern ('1' = bar) for a 13-digit code."""
    left = "".join((L_CODES if p == "L" else G_CODES)[int(d)]
                   for p, d in zip(PARITY[int(code[0])], code[1:7]))
    right = "".join(R_CODES[int(d)] for d in code[7:])
    return "101" + left + "01010" + right + "101"


def fill_rects(image, layer, rects, color):
    """Fill the given (x, y, w, h) rectangles on layer with color."""
    image.select_rectangle(Gimp.ChannelOps.REPLACE, 0, 0, 0, 0)
    for x, y, w, h in rects:
        image.select_rectangle(Gimp.ChannelOps.ADD, x, y, w, h)
    Gimp.context_push()
    Gimp.context_set_foreground(color)
    layer.edit_fill(Gimp.FillType.FOREGROUND)
    Gimp.context_pop()
    Gimp.Selection.none(image)


def new_image(width, height, back):
    image = Gimp.Image.new(width, height, Gimp.ImageBaseType.RGB)
    layer = Gimp.Layer.new(image, "Background", width, height,
                           Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.NORMAL)
    image.insert_layer(layer, None, 0)
    Gimp.context_push()
    Gimp.context_set_background(back)
    layer.fill(Gimp.FillType.BACKGROUND)
    Gimp.context_pop()
    return image, layer


def make_ean13(code, module, height, show_text, color, back):
    bits = ean13_modules(code)
    guard = {0, 1, 2, 45, 46, 47, 48, 49, 92, 93, 94}
    text_px = round(module * 9) if show_text else 0
    width = (QUIET_LEFT + 95 + QUIET_RIGHT) * module
    image, layer = new_image(width, height + text_px + 2 * module, back)

    top = module  # small margin above the bars
    rects = []
    for i, b in enumerate(bits):
        if b == "1":
            # guard bars run down into the digit line, data bars stop above it
            h = height + (text_px // 2 if (i in guard and show_text) else 0)
            rects.append(((QUIET_LEFT + i) * module, top, module, h))
    fill_rects(image, layer, rects, color)

    if show_text:
        font = Gimp.Font.get_by_name("Sans-serif")
        y = top + height
        # (text, centre x in modules): first digit in the quiet zone, then the two halves
        for text, cx in ((code[0], QUIET_LEFT / 2), (code[1:7], QUIET_LEFT + 24),
                         (code[7:], QUIET_LEFT + 71)):
            tl = Gimp.TextLayer.new(image, text, font, text_px, Gimp.Unit.pixel())
            image.insert_layer(tl, None, 0)
            tl.set_color(color)
            tl.set_offsets(round(cx * module - tl.get_width() / 2), y)
        image.flatten()
    return image


# Code 128 bar/space widths for symbol values 0-105, then the stop pattern.
CODE128 = """
212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232
122132 122231 113222 123122 123221 223211 221132 221231 213212 223112 312131 311222 321122
321221 312212 322112 322211 212123 212321 232121 111323 131123 131321 112313 132113 132311
211313 231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 231131 213113
213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 111422
121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111
241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121
412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412
211214 211232 2331112""".split()
START_B, START_C = 104, 105


def code128_modules(text):
    """Bar pattern ('1' = bar) for text: code set C for an even run of digits, else set B."""
    if not text:
        raise ValueError("Code 128 needs some text")
    if text.isdigit() and len(text) % 2 == 0:
        values = [START_C] + [int(text[i:i + 2]) for i in range(0, len(text), 2)]
    elif all(32 <= ord(c) <= 126 for c in text):
        values = [START_B] + [ord(c) - 32 for c in text]
    else:
        raise ValueError("Code 128 (set B) takes printable ASCII only")
    check = (values[0] + sum(i * v for i, v in enumerate(values) if i)) % 103
    widths = "".join(CODE128[v] for v in values + [check]) + CODE128[-1]
    return "".join(("1" if i % 2 == 0 else "0") * int(w) for i, w in enumerate(widths))


def make_code128(text, module, height, show_text, color, back):
    bits = code128_modules(text)
    quiet = 10  # modules each side
    text_px = round(module * 9) if show_text else 0
    image, layer = new_image((2 * quiet + len(bits)) * module, height + text_px + 2 * module, back)
    fill_rects(image, layer, [((quiet + i) * module, module, module, height)
                              for i, b in enumerate(bits) if b == "1"], color)
    if show_text:
        tl = Gimp.TextLayer.new(image, text, Gimp.Font.get_by_name("Sans-serif"), text_px, Gimp.Unit.pixel())
        image.insert_layer(tl, None, 0)
        tl.set_color(color)
        tl.set_offsets(round((image.get_width() - tl.get_width()) / 2), module + height)
        image.flatten()
    return image


def make_qr(text, module, border, correction, color, back):
    import qrcode
    qr = qrcode.QRCode(error_correction=getattr(qrcode.constants, "ERROR_CORRECT_" + correction),
                       box_size=1, border=border)
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()  # includes the border
    size = len(matrix) * module
    image, layer = new_image(size, size, back)
    fill_rects(image, layer, [(x * module, y * module, module, module)
                              for y, row in enumerate(matrix)
                              for x, on in enumerate(row) if on], color)
    return image


class Barcode(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False

    def do_query_procedures(self):
        return ["python-fu-ean13", "python-fu-code128", "python-fu-qrcode"]

    def do_create_procedure(self, name):
        procedure = Gimp.Procedure.new(self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        procedure.set_attribution("Isman Siete", "Isman Siete", "2016, 2026")
        procedure.add_enum_argument("run-mode", "Run mode", "The run mode", Gimp.RunMode,
                                    Gimp.RunMode.NONINTERACTIVE, GObject.ParamFlags.READWRITE)
        Gegl.init(None)  # as foggify does, before creating colors
        black, white = Gegl.Color.new("black"), Gegl.Color.new("white")
        rw = GObject.ParamFlags.READWRITE

        if name == "python-fu-ean13":
            procedure.set_menu_label("EAN-13 _Barcode...")
            procedure.add_menu_path("<Image>/File/Create")
            procedure.set_documentation("Create an EAN-13 barcode",
                                        "12 digits (check digit added) or 13 digits (check digit verified)", name)
            procedure.add_string_argument("code", "_Code", "12 or 13 digits", "590123412345", rw)
        elif name == "python-fu-code128":
            procedure.set_menu_label("Code _128 Barcode...")
            procedure.add_menu_path("<Image>/File/Create")
            procedure.set_documentation("Create a Code 128 barcode",
                                        "Printable ASCII text (code set B; even-length digit strings use set C)", name)
            procedure.add_string_argument("code", "_Text", "Text to encode", "Hello 2026", rw)
        else:
            procedure.set_menu_label("_QR Code...")
            procedure.add_menu_path("<Image>/File/Create")
            procedure.set_documentation("Create a QR code", "Create a QR code from a text string", name)
            procedure.add_string_argument("text", "_Text", "Text to encode", "I'm a QR code!", rw)
            procedure.add_int_argument("module", "_Box size (px)", "Size of one QR box", 1, 1000, 10, rw)
            procedure.add_int_argument("border", "_Border (boxes)", "Quiet zone width", 0, 20, 4, rw)
            correction = Gimp.Choice.new()
            for i, level in enumerate("LMQH"):
                correction.add(level, i, level, "")
            procedure.add_choice_argument("correction", "_Error correction", "Error correction level",
                                          correction, "Q", rw)

        if name != "python-fu-qrcode":
            procedure.add_int_argument("module", "_Module width (px)", "Width of the narrowest bar", 1, 100, 4, rw)
            procedure.add_int_argument("height", "Bar _height (px)", "Bar height", 10, 10000, 250, rw)
            procedure.add_boolean_argument("show-text", "Show te_xt", "Print the text under the bars", True, rw)
        procedure.add_color_argument("color", "_Foreground", "Bar color", False, black, rw)
        procedure.add_color_argument("back", "B_ackground", "Background color", False, white, rw)
        procedure.add_image_return_value("image", "Image", "The new image", False, rw)
        return procedure

    def run(self, procedure, config, data):
        if config.get_property("run-mode") == Gimp.RunMode.INTERACTIVE:
            gi.require_version('GimpUi', '3.0')
            from gi.repository import GimpUi
            GimpUi.init("gimp-barcode")
            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)
            dialog.fill(None)
            ok = dialog.run()
            dialog.destroy()
            if not ok:
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        p = config.get_property
        # GIMP 3.2 drops color defaults for non-interactive calls (even foggify's),
        # handing over transparent black; treat that as "unset"
        color, back = (c if c.get_rgba().alpha > 0 else Gegl.Color.new(d)
                       for c, d in ((p("color"), "black"), (p("back"), "white")))
        try:
            if procedure.get_name() == "python-fu-ean13":
                image = make_ean13(ean13_normalize(p("code")), p("module"), p("height"),
                                   p("show-text"), color, back)
            elif procedure.get_name() == "python-fu-code128":
                image = make_code128(p("code"), p("module"), p("height"), p("show-text"), color, back)
            else:
                image = make_qr(p("text"), p("module"), p("border"), p("correction"),
                                color, back)
        except ValueError as e:
            return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, GLib.Error(str(e)))

        if config.get_property("run-mode") == Gimp.RunMode.INTERACTIVE:
            Gimp.Display.new(image)
            Gimp.displays_flush()
        retval = procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
        retval.remove(1)
        retval.insert(1, GObject.Value(Gimp.Image, image))
        return retval


if __name__ == "__main__":
    if sys.argv[1:] == ["test"]:
        assert ean13_normalize("400638133393") == "4006381333931"
        assert ean13_normalize("5901234123457") == "5901234123457"
        for bad in ("5901234123458", "12345", "abcdefghijkl"):
            try:
                ean13_normalize(bad)
                raise AssertionError(bad)
            except ValueError:
                pass
        m = ean13_modules("5901234123457")
        assert len(m) == 95 and m.startswith("101") and m[45:50] == "01010"
        assert len(CODE128) == 107 and all(sum(map(int, w)) == 11 for w in CODE128[:-1])
        assert len(code128_modules("1234")) == 11 * 4 + 13  # set C: start, 2 pairs, check, stop
        for bad in ("", "café"):
            try:
                code128_modules(bad)
                raise AssertionError(bad)
            except ValueError:
                pass
        print("ok")
    else:
        Gimp.main(Barcode.__gtype__, sys.argv)
