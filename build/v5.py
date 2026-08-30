"""DIMA_Suit_Final_v5.pdf - production layout built on REF.pdf.

Page 1 is REF.pdf's own sheet (FRONT + BACK + both SIDES at one scale) with a
single correction: the elongated triangle from the image-RIGHT front leg is
also present on the image-LEFT front leg, produced by geometric mirroring of
the existing element (build/v5master.py).

Every later page places that same corrected page as a Form XObject, clipped
and scaled.  The artwork on a detail page is therefore not a redraw - it is
the identical object, so it cannot drift from the master.
"""
import os
import re
import pymupdf
from reportlab.pdfgen import canvas

import v5master
from render import (RICH_BLACK, PURPLE, PURPLE_DK, WHITE, GREY_TXT,
                    composite_grey, text)

MM = 72.0 / 25.4
OUT = 'DIMA_Suit_Final_v5.pdf'
MASTER = 'build/v5_master.pdf'
ARTONLY = 'build/v5_art.pdf'
FRAMES = 'build/v5_frames.pdf'

SHOW_TEXT = re.compile(rb"(?<![A-Za-z0-9])(Tj|TJ)(?![A-Za-z0-9])")
EMPTY_TEXT_BLOCK = re.compile(rb"BT\s+[^)]*?ET", re.S)

# Manufacturer's panel sizes for L/XL: body 80 x 60 cm, sleeve 80 x 30 cm.
BODY = (60 * 10 * MM, 80 * 10 * MM)
NARROW = (30 * 10 * MM, 80 * 10 * MM)
WIDE = (80 * 10 * MM, 60 * 10 * MM)

# Boxes in the master's page space, y-UP, measured off the sheet itself
# (garment ink spans y 102.1 .. 744.4; the sheet furniture sits outside).
V_FRONT = (302, 99, 588, 749)
V_BACK = (624, 99, 910, 749)
V_SIDE_L = (958, 99, 1085, 749)          # wearer's LEFT  (violet sleeve)
V_SIDE_R = (126, 99, 253, 749)           # wearer's RIGHT (black sleeve)
SL_L_FRONT = (496, 382, 592, 722)        # wearer's LEFT sleeve, front half
SL_L_BACK = (614, 382, 710, 722)         # wearer's LEFT sleeve, back half
SL_R_FRONT = (302, 382, 398, 722)        # wearer's RIGHT sleeve, front half
SL_R_BACK = (814, 382, 910, 722)         # wearer's RIGHT sleeve, back half
LEGS_FRONT = (302, 99, 588, 528)
LEGS_BACK = (624, 99, 910, 528)

PAGES = [
    ('2. ПЕРЕД / FRONT', BODY, [V_FRONT], None),
    ('3. СПИНКА / BACK', BODY, [V_BACK], None),
    ('4. БОК ЛЕВЫЙ / LEFT SIDE (wearer)', NARROW, [V_SIDE_L], None),
    ('5. БОК ПРАВЫЙ / RIGHT SIDE (wearer)', NARROW, [V_SIDE_R], None),
    ('6. РУКАВ ЛЕВЫЙ / LEFT SLEEVE (wearer) - отдельная деталь', NARROW,
     [SL_L_FRONT, SL_L_BACK], ('перед / front', 'спинка / back')),
    ('7. РУКАВ ПРАВЫЙ / RIGHT SLEEVE (wearer) - отдельная деталь', NARROW,
     [SL_R_FRONT, SL_R_BACK], ('перед / front', 'спинка / back')),
    ('8. НОГИ, ПЕРЕД / FRONT LEGS', WIDE, [LEGS_FRONT], None),
    ('9. НОГИ, СПИНКА / BACK LEGS', WIDE, [LEGS_BACK], None),
]

# REF.pdf marks its page as a DeviceCMYK transparency group, so blending
# happens in CMYK rather than the viewer's default RGB.  PyMuPDF drops the key
# when a page is copied, so it is written back onto every page of the output.
GROUP = '<</CS/DeviceCMYK/I false/K false/S/Transparency>>'

PAD = 22 * MM
TOP = 34 * MM
FOOT = 16 * MM

SWATCHES = [('фиолетовый', PURPLE, 'C72 M86 Y0 K16'),
            ('фиолетовый тёмный', PURPLE_DK, 'C82 M95 Y5 K42'),
            ('чёрный составной', RICH_BLACK, 'C40 M40 Y40 K100'),
            ('белый', WHITE, 'C0 M0 Y0 K0')]


def placement(sheet, boxes):
    """Uniform scale + offsets that fit `boxes` side by side on `sheet`.

    One scale for every box on the page, so a sleeve's front and back halves
    stay comparable and nothing is stretched.
    """
    PWd, PHd = sheet
    gap = 12 * MM if len(boxes) > 1 else 0
    tw = sum(b[2] - b[0] for b in boxes) + gap * (len(boxes) - 1)
    th = max(b[3] - b[1] for b in boxes)
    sc = min((PWd - 2 * PAD) / tw, (PHd - FOOT - TOP) / th)
    x = (PWd - tw * sc) / 2.0
    out = []
    for b in boxes:
        w, h = (b[2] - b[0]) * sc, (b[3] - b[1]) * sc
        y = FOOT + ((PHd - FOOT - TOP) - h) / 2.0
        out.append((b, pymupdf.Rect(x, PHd - y - h, x + w, PHd - y)))
        x += w + gap
    return sc, out


# ------------------------------------------------------------- frame layer ---
def swatch_row(c, x, y):
    for name, col, spec in SWATCHES:
        c.setFillColor(col)
        c.setStrokeColor(composite_grey(0.45))
        c.setLineWidth(0.4)
        c.rect(x, y, 11 * MM, 6 * MM, stroke=1, fill=1)
        text(c, x, y - 3.6 * MM, name, 5.6, GREY_TXT)
        text(c, x, y - 6.6 * MM, spec, 5.6, GREY_TXT)
        x += 34 * MM


def frame(c, sheet, title, sc, idx, total, boxes, labels):
    PWd, PHd = sheet
    c.setPageSize(sheet)
    text(c, PAD, PHd - 15 * MM, 'DIMA  -  SQD K-3 Art  -  D. FEDOROV', 11,
         RICH_BLACK, bold=True)
    text(c, PAD, PHd - 22 * MM, title, 9, RICH_BLACK)
    text(c, PWd - PAD, PHd - 15 * MM, 'DeviceCMYK - вектор - лист %d/%d' % (idx, total),
         7, GREY_TXT, align='right')
    text(c, PWd - PAD, PHd - 20 * MM,
         'лист %.0f x %.0f мм - масштаб x%.3f от мастер-листа REF.pdf' % (PWd / MM, PHd / MM, sc),
         7, GREY_TXT, align='right')
    c.setStrokeColor(GREY_TXT)
    c.setLineWidth(0.4)
    c.line(PAD, PHd - 26 * MM, PWd - PAD, PHd - 26 * MM)
    if labels:
        for (b, r), lab in zip(boxes, labels):
            text(c, (r.x0 + r.x1) / 2.0, PHd - r.y1 + 3 * MM, lab, 7,
                 GREY_TXT, align='center')
    swatch_row(c, PAD, 11 * MM)
    c.showPage()


def build_frames(total):
    c = canvas.Canvas(FRAMES, pagesize=BODY)
    for i, (title, sheet, boxes, labels) in enumerate(PAGES, start=2):
        sc, placed = placement(sheet, boxes)
        frame(c, sheet, title, sc, i, total, placed, labels)
    c.save()
    strip_unused_fonts(FRAMES)


def strip_unused_fonts(path):
    """ReportLab attaches a default Helvetica to every page even when nothing
    is set in type.  All lettering here is outlines, so drop it - a production
    file must reference no font at all."""
    doc = pymupdf.open(path)
    for page in doc:
        if SHOW_TEXT.search(page.read_contents()):
            doc.close()
            raise SystemExit('refusing to strip fonts: a page really draws text')
    for page in doc:
        raw = page.read_contents()
        cleaned = EMPTY_TEXT_BLOCK.sub(b'', raw)
        if cleaned != raw:
            doc.update_stream(page.get_contents()[0], cleaned)
        page.set_contents(page.get_contents()[0])
        res = doc.xref_get_key(page.xref, 'Resources')
        if res and res[0] == 'dict' and '/Font' in res[1]:
            doc.xref_set_key(page.xref, 'Resources/Font', 'null')
    doc.save(path + '.tmp', garbage=4, deflate=True, clean=True)
    doc.close()
    os.replace(path + '.tmp', path)


# ---------------------------------------------------------------- assembly ---
def build():
    v5master.build()
    v5master.build_art()
    total = 1 + len(PAGES)
    build_frames(total)

    master = pymupdf.open(MASTER)
    art = pymupdf.open(ARTONLY)
    frames = pymupdf.open(FRAMES)
    MH = master[0].rect.height

    out = pymupdf.open()
    out.insert_pdf(master, from_page=0, to_page=0)          # page 1: the master

    for i, (title, sheet, boxes, labels) in enumerate(PAGES):
        sc, placed = placement(sheet, boxes)
        page = out.new_page(width=sheet[0], height=sheet[1])
        for b, rect in placed:
            clip = pymupdf.Rect(b[0], MH - b[3], b[2], MH - b[1])
            page.show_pdf_page(rect, art, 0, clip=clip)
        page.show_pdf_page(page.rect, frames, i)

    for page in out:
        x = out.get_new_xref()
        out.update_object(x, GROUP)
        out.xref_set_key(page.xref, 'Group', f'{x} 0 R')

    out.set_metadata({'title': 'DIMA - SQD K-3 Art - D. FEDOROV - production v5',
                      'author': 'SQDRA', 'subject': 'Sublimation print layout, DeviceCMYK',
                      'creator': 'build/v5.py', 'producer': 'PyMuPDF'})
    out.save(OUT, garbage=4, deflate=True)
    out.close()
    return OUT, total


if __name__ == '__main__':
    p, n = build()
    print(f'{p}: {n} pages')
