#!/usr/bin/env python3
"""Build DIMA_Suit_Final_Print_Check.pdf - a screen proof of the layout.

This is a PREVIEW document (rasterised, RGB) for quick visual approval; the
production file is DIMA_Suit_Final_Print.pdf, which is vector and DeviceCMYK.
"""
import sys, os, io, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from render import RICH_BLACK, GREY_TXT, PURPLE, PURPLE_DK, WHITE, composite_grey, text, fill

MM = 72 / 25.4
SRC = 'DIMA_Suit_Final_v3.pdf'
OUT = 'DIMA_Suit_Final_v3_Check.pdf'
A3 = (1190.6, 842.0)
TMP = '/tmp/claude-0/-home-user-DIMA/edc8a053-88ad-5a72-8239-043b986ec5ab/scratchpad'


def render(page_no, dpi, clip=None):
    d = pymupdf.open(SRC)
    pix = d[page_no].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, clip=clip)
    im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    d.close()
    return im


def place(c, im, x, y, w, h):
    """Fit `im` inside the box, centred, preserving aspect."""
    s = min(w / im.width, h / im.height)
    iw, ih = im.width * s, im.height * s
    c.drawImage(ImageReader(im), x + (w - iw) / 2, y + (h - ih) / 2, iw, ih,
                preserveAspectRatio=True, anchor='c')
    return iw, ih


def head(c, title, sub, n, total):
    text(c, 16 * MM, A3[1] - 16 * MM, title, 15, RICH_BLACK, bold=True)
    text(c, 16 * MM, A3[1] - 22 * MM, sub, 8.5, GREY_TXT)
    text(c, A3[0] - 16 * MM, A3[1] - 16 * MM,
         'ПРОВЕРОЧНЫЙ ЛИСТ %d/%d - экранная копия, не для печати' % (n, total),
         8, GREY_TXT, align='right')
    c.setStrokeColor(GREY_TXT); c.setLineWidth(0.5)
    c.line(16 * MM, A3[1] - 25 * MM, A3[0] - 16 * MM, A3[1] - 25 * MM)


def main():
    TOTAL = 4
    c = canvas.Canvas(OUT, pagesize=A3)
    c.setTitle('DIMA - SQD K-3 Art - проверочный лист макета')

    # ---- 1. reference vs layout ------------------------------------------
    head(c, 'DIMA  -  SQD K-3 Art  -  сверка с референсом',
         'слева - DIMA.jpeg (референс дизайна); справа - готовый макет, лист 1 (перед / спинка / боковины)', 1, TOTAL)
    ref = Image.open('DIMA.jpeg').convert('RGB')
    lay = render(0, 190, pymupdf.Rect(290, 95, 930, 755))
    top, bot = A3[1] - 32 * MM, 22 * MM
    place(c, ref, 18 * MM, bot, 0.30 * A3[0], top - bot)
    place(c, lay, 0.34 * A3[0], bot, 0.62 * A3[0], top - bot)
    text(c, 18 * MM + 0.15 * A3[0], bot - 6 * MM, 'DIMA.jpeg', 8, GREY_TXT, align='center')
    text(c, 0.34 * A3[0] + 0.31 * A3[0], bot - 6 * MM,
         'DIMA_Suit_Final_v3.pdf, лист 1', 8, GREY_TXT, align='center')
    c.showPage()

    # ---- 2. detail comparison --------------------------------------------
    head(c, 'Сверка узлов', 'грудь со слэшем и «взрыв» на спине - референс над макетом', 2, TOTAL)
    W, H = A3[0], A3[1]
    boxes = [
        ('Грудь: осколки + белый слэш', (0.20, 0.09, 0.47, 0.30), pymupdf.Rect(330, 120, 570, 330)),
        ('Спина: «взрыв» + имя гонщика', (0.58, 0.09, 0.90, 0.30), pymupdf.Rect(640, 110, 900, 330)),
    ]
    bw = (W - 2 * 18 * MM - 20 * MM) / 2
    for i, (lbl, rf, cl) in enumerate(boxes):
        x = 18 * MM + i * (bw + 20 * MM)
        rc = ref.crop((int(rf[0] * ref.width), int(rf[1] * ref.height),
                       int(rf[2] * ref.width), int(rf[3] * ref.height)))
        lc = render(0, 300, cl)
        colh = (H - 40 * MM - 26 * MM) / 2
        place(c, rc, x, H - 34 * MM - colh, bw, colh)
        place(c, lc, x, H - 34 * MM - 2 * colh - 8 * MM, bw, colh)
        text(c, x + bw / 2, H - 34 * MM - 2 * colh - 14 * MM, lbl, 8.5, RICH_BLACK, align='center')
    c.showPage()

    # ---- 3. all sheets ----------------------------------------------------
    head(c, 'Все листы производственного файла',
         '1 - общий лист A3; 2..7 - детали в размерах панелей производителя; 8 - спецификация', 3, TOTAL)
    names = ['1 общий лист A3', '2 перед', '3 спинка', '4 бок левый', '5 бок правый',
             '6 рукав левый', '7 рукав правый', '8 спецификация']
    cols, rows = 4, 2
    gw = (A3[0] - 2 * 16 * MM) / cols
    gh = (A3[1] - 40 * MM - 14 * MM) / rows
    for i in range(8):
        im = render(i, 46)
        cx = 16 * MM + (i % cols) * gw
        cy = A3[1] - 34 * MM - (i // cols + 1) * gh
        place(c, im, cx + 3 * MM, cy + 8 * MM, gw - 6 * MM, gh - 12 * MM)
        text(c, cx + gw / 2, cy + 3 * MM, names[i], 7.5, GREY_TXT, align='center')
    c.showPage()

    # ---- 4. pre-flight readout -------------------------------------------
    head(c, 'Результат предпечатной проверки',
         'вывод build/verify.py по файлу DIMA_Suit_Final_Print.pdf', 4, TOTAL)
    try:
        out = subprocess.run([sys.executable, 'build/verify.py'], capture_output=True,
                             text=True, timeout=300).stdout
    except Exception as e:
        out = 'verify.py failed: %s' % e
    y = A3[1] - 34 * MM
    for line in out.splitlines():
        if y < 16 * MM:
            break
        bold = line.startswith('==')
        col = RICH_BLACK if (bold or '[FAIL]' in line or line.startswith('RESULT')) else GREY_TXT
        text(c, 16 * MM, y, line.replace('\t', '    ')[:150], 6.6, col, bold=bold)
        y -= 3.5 * MM
    c.showPage()
    c.save()
    print('wrote', OUT)


if __name__ == '__main__':
    main()
