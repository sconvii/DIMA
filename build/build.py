#!/usr/bin/env python3
"""Build DIMA_Suit_Final_Print.pdf - production layout, DeviceCMYK, all vector.

Geometry comes from Suit_SQD-K-3art-ЭСКИЗ.pdf (every contour is reused, never
re-guessed); the livery comes from DIMA.jpeg.  Each source object is walked in
its original z-order so the finished silhouette matches the sketch exactly.
"""
import sys, os, math, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor
import suitsrc as S
import shards as SH
import design as D
import art as A
import textcurves as TC
from render import (RICH_BLACK, PURPLE, PURPLE_DK, WHITE, SEAM, TECH, GREY_TXT, HATCH,
                    composite_grey, fill, fill_pts, stroke, add, Clip, text)

MM = 72.0 / 25.4
OUT = 'DIMA_Suit_Final_v4.pdf'

doc, page, DR, SRECT = S.load()
PW, PH = SRECT.width, SRECT.height          # 1192.6 x 843.8 pt  (A3 landscape)

# --------------------------------------------------------------- helpers ---
def subs(i, closed=True):
    p = S.path_of(DR[i])
    return S.close_all(p) if closed else p


def union(*idx):
    out = []
    for i in idx:
        out += subs(i)
    return out


def rgb2cmyk(rgb):
    """Source RGB -> DeviceCMYK.

    Near-blacks become the specified rich black and neutral greys become
    composite builds; no flat-K neutral is ever emitted.
    """
    r, g, b = rgb
    if max(rgb) < 0.16:
        return RICH_BLACK
    if max(rgb) - min(rgb) < 0.02:                 # neutral grey
        return composite_grey(1 - max(rgb))
    k = 1 - max(rgb)
    if k >= 0.999:
        return RICH_BLACK
    c = (1 - r - k) / (1 - k)
    m = (1 - g - k) / (1 - k)
    y = (1 - b - k) / (1 - k)
    return CMYKColor(max(0, min(1, c)), max(0, min(1, m)),
                     max(0, min(1, y)), max(0, min(1, k)))


# ------------------------------------------------------------ object sets ---
ELASTIC = set(range(50, 56)) | set(range(58, 76)) | set(range(81, 87)) | \
          {100, 101} | set(range(104, 116)) | {161, 166, 167}
FURNITURE = set(range(0, 50)) | set(range(168, 232))
DROP = {88, 89, 92, 93}                      # stray CorelDRAW guide strokes

FRONT_BODY = {80}
FRONT_SL_WL = {78, 79}                       # wearer's LEFT  -> violet sleeve
FRONT_SL_WR = {76, 77}                       # wearer's RIGHT -> black sleeve
BACK_TORSO = {153, 155, 156}
BACK_LEGS = {151, 152}
BACK_SL_WL = {157, 158}
BACK_SL_WR = {159, 160}
SIDE_WR = {57, 91, 98, 103, 117}             # left-hand figure  = wearer's RIGHT
SIDE_WL = {56, 87, 97, 102, 116}             # right-hand figure = wearer's LEFT
COLLARS = {121, 125, 128, 129, 130, 164, 165}
BELT = {122}
EPAULETTE = {119, 120, 162, 163}
EPA_FRONT_L = set(range(131, 141))
EPA_FRONT_R = set(range(141, 151))
EPA_CLIP = {}
TECHLINE = {90, 94, 95, 96, 99, 105, 108, 118, 123, 124, 126, 127, 140, 150, 154}





# ================================================================= paints ===
# Base colour, then TRACED artwork from art.py.  No graphic path is authored
# here: the chest, back, sleeve, leg and side-panel paths all come from
# tracing REFERENCE_MASTER_2D.
def bigrect(c, x0, y0, x1, y1, col):
    fill(c, [[('M', x0, y0), ('L', x1, y0), ('L', x1, y1), ('L', x0, y1), ('Z',)]], col)


def paint_front_body(c):
    bigrect(c, 250, 80, 650, 790, RICH_BLACK)          # BASE_BLACK
    fill(c, A.front_torso_purple(), PURPLE, eo=True)   # CHEST_GRAPHICS
    fill(c, A.front_legs_purple(), PURPLE, eo=True)    # FRONT_LEG_GRAPHICS
    fill(c, A.front_torso_white(), WHITE, eo=True)     # WHITE_GRAPHICS


def paint_front_sleeve_wl(c):                          # wearer's LEFT -> violet
    bigrect(c, 490, 130, 610, 470, PURPLE)             # BASE_PURPLE
    fill(c, A.sleeve_marks('purple', 'front'), RICH_BLACK, eo=True)
    # the shoulder yoke is torso artwork that crosses the armhole
    fill(c, A.front_torso_purple(), PURPLE, eo=True)
    fill(c, A.front_torso_white(), WHITE, eo=True)


def paint_front_sleeve_wr(c):                          # wearer's RIGHT -> black
    bigrect(c, 280, 130, 400, 470, RICH_BLACK)         # BASE_BLACK
    fill(c, A.sleeve_marks('black', 'front'), PURPLE, eo=True)
    fill(c, A.front_torso_purple(), PURPLE, eo=True)
    fill(c, A.front_torso_white(), WHITE, eo=True)


def paint_back_torso(c):
    bigrect(c, 580, 80, 960, 790, RICH_BLACK)
    fill(c, A.back_torso_purple(), PURPLE, eo=True)    # BACK_GRAPHICS
    fill(c, A.back_torso_white(), WHITE, eo=True)


def paint_back_legs(c):
    bigrect(c, 580, 330, 960, 790, RICH_BLACK)
    fill(c, A.back_legs_purple(), PURPLE, eo=True)     # BACK_LEG_GRAPHICS


def paint_back_sleeve_wl(c):                           # viewer-left on the back
    bigrect(c, 600, 130, 720, 470, PURPLE)
    fill(c, A.sleeve_marks('purple', 'back'), RICH_BLACK, eo=True)
    fill(c, A.back_torso_purple(), PURPLE, eo=True)
    fill(c, A.back_torso_white(), WHITE, eo=True)


def paint_back_sleeve_wr(c):
    bigrect(c, 820, 130, 950, 470, RICH_BLACK)
    fill(c, A.sleeve_marks('black', 'back'), PURPLE, eo=True)
    fill(c, A.back_torso_purple(), PURPLE, eo=True)
    fill(c, A.back_torso_white(), WHITE, eo=True)


# ---- side views -------------------------------------------------------------
def _side_body(c, mirror):
    box = (955, 80, 1105, 790) if mirror else (118, 80, 268, 790)
    bigrect(c, *box, RICH_BLACK)                       # stays predominantly black
    fill(c, A.side_purple('R' if mirror else 'L'), PURPLE, eo=True)


def paint_side_wr(c):
    _side_body(c, mirror=False)


def paint_side_wl(c):
    _side_body(c, mirror=True)


def paint_side_sleeve(c, wearer, mirror):
    box = (955, 96, 1105, 470) if mirror else (118, 96, 268, 470)
    bigrect(c, *box, PURPLE if wearer == 'L' else RICH_BLACK)


def paint_collar(c, i):
    """Black stand with the violet band and white cord from the sketch edge."""
    sb = subs(i)
    r = DR[i]['rect']
    bigrect(c, r.x0 - 8, r.y0 - 8, r.x1 + 8, r.y1 + 8, RICH_BLACK)
    top = []
    for y in [r.y0 + 0.6 + k * 0.55 for k in range(9)]:
        cr = S.crossings_at(sb, y)
        if len(cr) >= 2:
            top.append((y, min(cr), max(cr)))
    if len(top) >= 4:
        y_w = top[min(2, len(top) - 1)][0]
        y_p = top[min(7, len(top) - 1)][0]
        bigrect(c, r.x0 - 8, y_w, r.x1 + 8, y_p, WHITE)
        bigrect(c, r.x0 - 8, y_p, r.x1 + 8, y_p + 3.0, PURPLE)


def paint_belt(c):
    r = DR[122]['rect']
    bigrect(c, r.x0 - 4, r.y0 - 4, r.x1 + 4, r.y1 + 4, RICH_BLACK)
    bigrect(c, r.x0 - 4, r.y0 + 1.0, r.x1 + 4, r.y0 + 2.0, WHITE)
    bigrect(c, r.x0 - 4, r.y1 - 2.0, r.x1 + 4, r.y1 - 1.0, WHITE)


# ================================================================== sheet ===
# The sketch stacks the side-view arm behind the torso, which is invisible when
# every panel is white.  With the arm and the body in different colours it has
# to come forward - the outer silhouette is their union either way, so nothing
# about the geometry changes.  Only these six objects move; the elastics,
# hatching and trims keep the sketch's own order.
SIDE_ARM = [87, 90, 97, 91, 94, 98]

# Texture hatching from the sketch is stroke-only and, on the side views, runs
# past the panel it belongs to.  Clip each one to its own garment silhouette so
# nothing strays outside the layout.
HATCH_CLIP = {105: (56, 87, 97, 102, 116), 108: (57, 91, 98, 103, 117),
              111: (110,), 114: (113,), 51: (50,), 54: (53,),
              59: (58,), 62: (61,), 65: (64,), 68: (67,),
              71: (70,), 74: (73,), 82: (81,), 85: (84,)}


def hatch_clip_path(i):
    return union(*HATCH_CLIP[i]) if i in HATCH_CLIP else None


def sheet_order():
    order = [i for i in range(len(DR)) if i not in SIDE_ARM]
    at = order.index(117) + 1
    return order[:at] + SIDE_ARM + order[at:]


def draw_sheet(c, furniture=True, keep=None):
    """Every source object, in source z-order, wearing the DIMA livery."""
    for i in sheet_order():
        if i in DROP:
            continue
        if keep is not None and i not in keep:
            continue
        if i in FURNITURE and not furniture:
            continue
        draw_object(c, i, DR[i])


def draw_object(c, i, g):
    if i in FURNITURE:
        col = g.get('fill') or g.get('color')
        if col is None:
            return
        sb = subs(i, closed=(g['type'] != 's'))
        if g['type'] == 's':
            stroke(c, sb, rgb2cmyk(g['color']), g.get('width') or 0.5)
        else:
            fill(c, sb, rgb2cmyk(col), eo=True)
        return

    sb = subs(i)
    if i in ELASTIC:
        # Rib and armhole hatching are stroke-only texture paths: filling them
        # would smear black across the panel, and at full weight they read as
        # print rather than as the annotation they are.
        if g['type'] == 's':
            clip = hatch_clip_path(i)
            w = min(g.get('width') or 0.3, 0.35)
            if clip:
                with Clip(c, clip):
                    stroke(c, S.path_of(DR[i]), HATCH, w)
            else:
                stroke(c, S.path_of(DR[i]), HATCH, w)
        else:
            fill(c, sb, RICH_BLACK)
            stroke(c, sb, TECH, 0.5)
        return
    if i in TECHLINE:
        col = SEAM if i in (99, 118, 154) else TECH
        dash = g.get('dashes')
        dl = None
        if dash and dash not in ('[] 0', '[ ] 0'):
            try:
                inner = dash[dash.index('[') + 1: dash.index(']')].split()
                dl = [float(v) for v in inner] or None
            except Exception:
                dl = None
        stroke(c, S.path_of(DR[i]), col, max(g.get('width') or 0.5, 0.45), dash=dl)
        return

    painter = None
    if i in FRONT_BODY:      painter = paint_front_body
    elif i in FRONT_SL_WL:   painter = paint_front_sleeve_wl
    elif i in FRONT_SL_WR:   painter = paint_front_sleeve_wr
    elif i in BACK_TORSO:    painter = paint_back_torso
    elif i in BACK_LEGS:     painter = paint_back_legs
    elif i in BACK_SL_WL:    painter = paint_back_sleeve_wl
    elif i in BACK_SL_WR:    painter = paint_back_sleeve_wr
    elif i == 91 or i == 98: painter = lambda cc: paint_side_sleeve(cc, 'R', False)
    elif i == 87 or i == 97: painter = lambda cc: paint_side_sleeve(cc, 'L', True)
    elif i in SIDE_WR:       painter = paint_side_wr
    elif i in SIDE_WL:       painter = paint_side_wl
    elif i in COLLARS:       painter = (lambda k: (lambda cc: paint_collar(cc, k)))(i)
    elif i in BELT:          painter = lambda cc: paint_belt(cc)
    elif i in EPAULETTE or i in EPA_FRONT_L or i in EPA_FRONT_R:
        # DIMA.jpeg: plain black tab with a white cord outline.  The tab's
        # SQD wordmark from the sketch is kept, tone-on-tone and clipped
        # inside the tab so it cannot spill past the epaulette.
        fillc = g.get('fill')
        if fillc is not None and max(fillc) > 0.7 and min(fillc) > 0.7 and \
           abs(fillc[0] - fillc[2]) < 0.02 and DR[i]['rect'].width > 20:
            fill(c, sb, RICH_BLACK)
            stroke(c, sb, WHITE, 0.9 if i in (119, 120) else 1.6, join=1)
            EPA_CLIP[i // 10] = sb
        elif g['type'] == 's' and DR[i]['rect'].width > 20:
            stroke(c, sb, WHITE, 1.5, join=1)
        elif fillc is not None and max(fillc) < 0.9:
            clip = EPA_CLIP.get(i // 10)      # skip the white halo layer
            if clip:
                with Clip(c, clip):
                    fill(c, sb, PURPLE_DK, eo=True)
        return

    if painter is None:
        col = g.get('fill') or g.get('color')
        if col is not None:
            fill(c, sb, rgb2cmyk(col), eo=True)
        return

    with Clip(c, sb):
        painter(c)
    if g['type'] in ('s', 'fs'):
        stroke(c, S.path_of(DR[i]), TECH, max(g.get('width') or 0.5, 0.42))




def page_full(c):
    c.saveState()
    c.translate(0, PH); c.scale(1, -1)
    draw_sheet(c, furniture=True)
    c.restoreState()
    c.showPage()


# ------------------------------------------------------------ detail pages ---
# Manufacturer's panel sizes for L/XL: body 80 x 60 cm, sleeves 80 x 30 cm.
BODY_SHEET = (60 * 10 * MM, 80 * 10 * MM)
NARROW_SHEET = (30 * 10 * MM, 80 * 10 * MM)

DETAILS = [
    ('1. ПЕРЕД / FRONT', BODY_SHEET,
     (296, 92, 596, 750), FRONT_BODY | FRONT_SL_WL | FRONT_SL_WR |
     {58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 99, 118, 122, 123, 124,
      125, 126, 127, 128, 129, 130, 167} | EPA_FRONT_L | EPA_FRONT_R),
    ('2. СПИНКА / BACK', BODY_SHEET,
     (618, 92, 918, 750), BACK_TORSO | BACK_LEGS | BACK_SL_WL | BACK_SL_WR |
     {70, 71, 72, 73, 74, 75, 81, 82, 83, 84, 85, 86, 121, 154, 161, 162, 163, 166}
     | set(range(168, 181))),
    ('3. БОК ЛЕВЫЙ / LEFT SIDE (wearer)', NARROW_SHEET,
     (950, 92, 1092, 750), SIDE_WL | {50, 51, 52, 87, 90, 95, 97, 100, 104, 105,
      106, 110, 111, 112, 119, 164}),
    ('4. БОК ПРАВЫЙ / RIGHT SIDE (wearer)', NARROW_SHEET,
     (120, 92, 262, 750), SIDE_WR | {53, 54, 55, 91, 94, 96, 98, 101, 107, 108,
      109, 113, 114, 115, 120, 165}),
    ('5. РУКАВ ЛЕВЫЙ / LEFT SLEEVE (wearer)', NARROW_SHEET,
     (515, 140, 600, 460), FRONT_SL_WL | {67, 68, 69}),
    ('6. РУКАВ ПРАВЫЙ / RIGHT SLEEVE (wearer)', NARROW_SHEET,
     (300, 140, 385, 460), FRONT_SL_WR | {64, 65, 66}),
]


def draw_subset(c, keep):
    draw_sheet(c, furniture=True, keep=keep)


def page_detail(c, title, sheet, box, keep, idx, total):
    PWd, PHd = sheet
    c.setPageSize(sheet)
    x0, y0, x1, y1 = box
    pad = 26 * MM
    top = 30 * MM
    sx = (PWd - 2 * pad) / (x1 - x0)
    sy = (PHd - pad - top) / (y1 - y0)
    sc = min(sx, sy)
    ox = (PWd - (x1 - x0) * sc) / 2.0
    oy = pad + ((PHd - pad - top) - (y1 - y0) * sc) / 2.0

    c.saveState()
    c.translate(ox, oy + (y1 - y0) * sc)
    c.scale(sc, -sc)
    c.translate(-x0, -y0)
    draw_subset(c, keep)
    c.restoreState()

    title_block(c, PWd, PHd, title, sc, idx, total)
    c.showPage()


def title_block(c, PWd, PHd, title, sc, idx, total):
    c.saveState()
    text(c, 14 * MM, PHd - 15 * MM, 'DIMA  -  SQD K-3 Art  -  D. FEDOROV', 11, RICH_BLACK, bold=True)
    text(c, 14 * MM, PHd - 21 * MM, title, 9, RICH_BLACK)
    text(c, PWd - 14 * MM, PHd - 15 * MM,
         'DeviceCMYK - вектор - лист %d/%d' % (idx, total), 7, GREY_TXT, align='right')
    text(c, PWd - 14 * MM, PHd - 20 * MM,
         'лист %.0f x %.0f мм - масштаб x%.3f от эскиза' % (PWd / MM, PHd / MM, sc),
         7, GREY_TXT, align='right')
    c.setStrokeColor(GREY_TXT)
    c.setLineWidth(0.4)
    c.line(14 * MM, PHd - 24 * MM, PWd - 14 * MM, PHd - 24 * MM)
    swatch_row(c, 14 * MM, 9 * MM)
    c.restoreState()


SWATCHES = [('violet', PURPLE, 'C72 M86 Y0 K16'),
            ('violet shade', PURPLE_DK, 'C82 M95 Y5 K42'),
            ('rich black', RICH_BLACK, 'C40 M40 Y40 K100'),
            ('white', WHITE, 'C0 M0 Y0 K0')]


def swatch_row(c, x, y):
    for name, col, spec in SWATCHES:
        c.setFillColor(col)
        c.rect(x, y, 9 * MM, 5 * MM, stroke=0, fill=1)
        c.setStrokeColor(GREY_TXT); c.setLineWidth(0.3)
        c.rect(x, y, 9 * MM, 5 * MM, stroke=1, fill=0)
        text(c, x, y - 3 * MM, spec, 5.5, GREY_TXT)
        x += 30 * MM



SHOW_TEXT = re.compile(rb"(?<![A-Za-z0-9])(Tj|TJ)(?![A-Za-z0-9])")
EMPTY_TEXT_BLOCK = re.compile(rb"BT\s+[^)]*?ET", re.S)


def strip_unused_fonts(path):
    """ReportLab opens an empty BT/Tf/ET block and attaches a default Helvetica
    resource to every page even when nothing is set in type.  All our lettering
    is outlines, so drop both - a production file should reference no font."""
    import pymupdf
    doc = pymupdf.open(path)
    for page in doc:
        if SHOW_TEXT.search(page.read_contents()):
            doc.close()
            raise SystemExit('refusing to strip fonts: a page really draws text')
    for page in doc:
        raw = page.read_contents()
        cleaned = EMPTY_TEXT_BLOCK.sub(b'', raw)
        if cleaned != raw:
            xref = page.get_contents()[0]
            doc.update_stream(xref, cleaned)
        page.set_contents(page.get_contents()[0])
        res = doc.xref_get_key(page.xref, 'Resources')
        if res and res[0] == 'dict' and '/Font' in res[1]:
            doc.xref_set_key(page.xref, 'Resources/Font', 'null')
    doc.save(path + '.tmp', garbage=4, deflate=True, clean=True)
    doc.close()
    os.replace(path + '.tmp', path)


# ---------------------------------------------------------------- spec page --
SPEC_ROWS = [
    ('Изделие / Garment', 'Комбинезон SQD K-3 Art, размер L/XL'),
    ('Гонщик / Driver', 'D. FEDOROV'),
    ('Источник геометрии', 'Suit_SQD-K-3art-ЭСКИЗ.pdf (CorelDRAW 2019), A3 420,7 x 297,7 мм'),
    ('Источник дизайна', 'DIMA.jpeg, 1102 x 1280 px, RGB'),
    ('Цветовая модель', 'DeviceCMYK во всём документе, объектов RGB нет'),
    ('Чёрный', 'Составной: C40 M40 Y40 K100 (по требованию производителя)'),
    ('Растровые элементы', 'Отсутствуют - макет полностью векторный'),
    ('Шрифты', 'Отсутствуют - все надписи переведены в кривые'),
    ('Печать', 'Сублимация по полиэфирному полотну'),
    ('Панели L/XL', 'Корпус 80 x 60 см, рукав 80 x 30 см'),
    ('Эластичные элементы', 'Манжеты, пояс спинки, ластовица - только чёрный, без дизайна'),
]


def page_spec(c, total):
    c.setPageSize((PW, PH))
    M = 18 * MM
    text(c, M, PH - M, 'DIMA  -  SQD K-3 Art  -  техническая спецификация макета',
         16, RICH_BLACK, bold=True)
    text(c, PW - M, PH - M, 'лист %d/%d' % (total, total), 8, GREY_TXT, align='right')
    c.setStrokeColor(GREY_TXT); c.setLineWidth(0.5)
    c.line(M, PH - M - 6 * MM, PW - M, PH - M - 6 * MM)

    y = PH - M - 16 * MM
    for k, v in SPEC_ROWS:
        text(c, M, y, k, 8, RICH_BLACK, bold=True)
        text(c, M + 52 * MM, y, v, 8, GREY_TXT)
        y -= 7.2 * MM

    # colour card, with a generous chip for on-press comparison
    y -= 6 * MM
    text(c, M, y, 'Цветовая карта / colour card', 10, RICH_BLACK, bold=True)
    y -= 6 * MM
    x = M
    card = [('ФИОЛЕТОВЫЙ основной', PURPLE, 'C72 M86 Y0 K16', 'RGB 88 58 135  /  #583A87'),
            ('ФИОЛЕТОВЫЙ тень', PURPLE_DK, 'C82 M95 Y5 K42', 'осколки внутри поля'),
            ('ЧЁРНЫЙ составной', RICH_BLACK, 'C40 M40 Y40 K100', 'основа изделия'),
            ('БЕЛЫЙ', WHITE, 'C0 M0 Y0 K0', 'кант, слэш, надпись')]
    for name, col, spec_s, note in card:
        c.setFillColor(col)
        c.rect(x, y - 34 * MM, 46 * MM, 32 * MM, stroke=0, fill=1)
        c.setStrokeColor(GREY_TXT); c.setLineWidth(0.4)
        c.rect(x, y - 34 * MM, 46 * MM, 32 * MM, stroke=1, fill=0)
        text(c, x, y - 39 * MM, name, 7, RICH_BLACK, bold=True)
        text(c, x, y - 43 * MM, spec_s, 7, GREY_TXT)
        text(c, x, y - 46.5 * MM, note, 6, GREY_TXT)
        x += 56 * MM

    # notes
    ny = y - 58 * MM
    text(c, M, ny, 'Примечания / notes', 10, RICH_BLACK, bold=True)
    ny -= 6 * MM
    notes = [
        '1. Геометрия, контуры, швы и строчки взяты непосредственно из векторных объектов исходного эскиза - ни один контур не перерисован «на глаз».',
        '2. Дизайн перенесён с DIMA.jpeg: цвета измерены по изображению, графика перерисована в вектор. Складки ткани, тени и фон фотографии не переносились.',
        '3. Рисунок задан один раз в общей системе координат и обрезается по каждой детали, поэтому графика непрерывна на стыках перед-бок-спинка и корпус-рукав.',
        '4. Дизайн асимметричен по образцу: левый рукав (носителя) фиолетовый, правый чёрный; всплеск на груди - слева, «взрыв» на спине - от левого плеча.',
        '5. Исходный файл является эскизом (схематичным), а не лекалом 1:1 - см. дисклеймер производителя на листе 1. Масштаб деталей задан относительно эскиза.',
        '6. Боковые детали присутствовали в исходном эскизе как виды сбоку и полностью прорисованы: фиолетовая обёртка бокового шва состыкована с передом и спинкой.',
    ]
    for t in notes:
        text(c, M, ny, t, 7.4, GREY_TXT)
        ny -= 5.4 * MM
    c.showPage()


if __name__ == '__main__':
    c = canvas.Canvas(OUT, pagesize=(PW, PH))
    c.setTitle('DIMA - SQD K-3 Art racing suit - production layout')
    c.setAuthor('SQDRA')
    c.setSubject('Sublimation print layout for D. FEDOROV, DeviceCMYK, all vector')
    c.setKeywords('sublimation, CMYK, racing suit, SQD K-3 Art, DIMA')
    total = 1 + len(DETAILS) + 1
    page_full(c)
    for n, (title, sheet, box, keep) in enumerate(DETAILS, start=2):
        page_detail(c, title, sheet, box, keep, n, total)
    page_spec(c, total)
    c.save()
    strip_unused_fonts(OUT)
    print('wrote', OUT, '-', total, 'pages')
