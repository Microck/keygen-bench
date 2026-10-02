"""Convert the original FastTracker II bitmap fonts (ft2-clone src/gfxdata/bmp, by Magnus "Vogue"
Hogdahl / 8bitbubsy, CC BY-NC-SA 4.0) into pixel-outline web fonts so DOM text can use them too.

    python web/classic/build_fonts.py   # reads core/ft2gfx/*.png, writes core/fonts/ft2-*.woff2

font1 (8x10, proportional via font1Widths) -> "FT2"        at 10px/em: 1 font px = 1 CSS px at font-size 10px
font3 (4x7, 0-9 A-Z)                    -> "FT2 Tiny"   at 7px/em
font2 (16x20, proportional)             -> "FT2 Big"    at 20px/em
"""
import json
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image

HERE = Path(__file__).resolve().parent
GFX = HERE / "core/ft2gfx"
OUT = HERE / "core/fonts"
UNIT = 100  # font units per pixel


def bitmap(name):
    im = Image.open(GFX / f"{name}.png").convert("RGBA")
    w, h = im.size
    px = im.load()
    return w, h, lambda x, y: px[x, y][3] > 127


def build(family, glyph_cells, cell_h, baseline_row, out_name):
    """glyph_cells: {codepoint: (x0, y0, w, advance_px, on)}; baseline_row = rows above baseline."""
    upm = cell_h * UNIT
    names = [".notdef"] + [f"u{cp:04X}" for cp in glyph_cells]
    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap({cp: f"u{cp:04X}" for cp in glyph_cells})
    glyphs, metrics = {}, {}
    empty = TTGlyphPen(None)
    glyphs[".notdef"] = empty.glyph()
    metrics[".notdef"] = (UNIT * 4, 0)
    for cp, (x0, y0, w, adv, on) in glyph_cells.items():
        pen = TTGlyphPen(None)
        for y in range(cell_h):
            for x in range(w):
                if on(x0 + x, y0 + y):
                    # y grows downward in the bitmap; baseline at baseline_row
                    top = (baseline_row - y) * UNIT
                    left = x * UNIT
                    pen.moveTo((left, top - UNIT))
                    pen.lineTo((left, top))
                    pen.lineTo((left + UNIT, top))
                    pen.lineTo((left + UNIT, top - UNIT))
                    pen.closePath()
        glyphs[f"u{cp:04X}"] = pen.glyph()
        metrics[f"u{cp:04X}"] = (adv * UNIT, 0)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    asc, desc = baseline_row * UNIT, (cell_h - baseline_row) * UNIT
    fb.setupHorizontalHeader(ascent=asc, descent=-desc)
    fb.setupOS2(sTypoAscender=asc, sTypoDescender=-desc, sTypoLineGap=0, usWinAscent=asc, usWinDescent=desc)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupPost()
    fb.font.flavor = "woff2"
    fb.save(OUT / out_name)
    print("wrote", OUT / out_name, len(glyph_cells), "glyphs")


def main():
    OUT.mkdir(exist_ok=True)
    tables = json.loads((GFX / "tables.json").read_text())
    w, h, on1 = bitmap("font1")
    build("FT2", {c: (c * 8, 0, 8, tables["font1"][c], on1) for c in range(32, 127)}, 10, 8, "ft2-font1.woff2")
    w, h, on2 = bitmap("font2")
    build("FT2 Big", {c: (c * 16, 0, 16, tables["font2"][c], on2) for c in range(32, 127)}, 20, 16, "ft2-font2.woff2")
    w, h, on3 = bitmap("font3")
    tiny = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    cells = {ord(ch): (i * 4, 0, 4, 4, on3) for i, ch in enumerate(tiny)}
    cells.update({ord(ch.lower()): (i * 4, 0, 4, 4, on3) for i, ch in enumerate(tiny) if ch.isalpha()})
    cells[ord(" ")] = (0, 0, 0, 4, on3)
    cells[ord("-")] = (36 * 4, 0, 4, 4, on3)
    cells[ord(".")] = (42 * 4, 0, 4, 4, on3)
    build("FT2 Tiny", cells, 7, 7, "ft2-font3.woff2")


if __name__ == "__main__":
    main()
