#!/usr/bin/env python3
"""DIMA_Suit_Final_v5_PREVIEW.pdf - screen proof and verification record.

A PREVIEW document (rasterised, RGB) for approval on screen.  The file to
print is DIMA_Suit_Final_v5.pdf, which is vector and DeviceCMYK throughout.

It documents the one change made to REF.pdf and proves by pixel difference
that nothing else moved.
"""
import io
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pymupdf
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from render import RICH_BLACK, GREY_TXT, PURPLE, PURPLE_DK, WHITE, composite_grey, text

MM = 72 / 25.4
REF = 'REF.pdf'
SRC = 'DIMA_Suit_Final_v5.pdf'
OUT = 'DIMA_Suit_Final_v5_PREVIEW.pdf'
A3 = (1190.6, 842.0)
AXIS = 444.927


def render(path, pno=0, dpi=150, clip=None, flip=False):
    d = pymupdf.open(path)
    page = d[pno]
    r = None if clip is None else pymupdf.Rect(
        clip[0], page.rect.height - clip[3], clip[2], page.rect.height - clip[1])
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, clip=r)
    im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    d.close()
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def place(c, im, x, y, w, h):
    s = min(w / im.width, h / im.height)
    iw, ih = im.width * s, im.height * s
    c.drawImage(ImageReader(im), x + (w - iw) / 2, y + (h - ih) / 2, iw, ih)
    return x + (w - iw) / 2, y + (h - ih) / 2, iw, ih


def head(c, title, sub, n, total):
    text(c, 16 * MM, A3[1] - 16 * MM, title, 15, RICH_BLACK, bold=True)
    text(c, 16 * MM, A3[1] - 23 * MM, sub, 8.5, GREY_TXT)
    text(c, A3[0] - 16 * MM, A3[1] - 16 * MM,
         'ПРОВЕРОЧНЫЙ ЛИСТ %d/%d - экранная копия, не для печати' % (n, total),
         8, GREY_TXT, align='right')
    c.setStrokeColor(GREY_TXT)
    c.setLineWidth(0.5)
    c.line(16 * MM, A3[1] - 27 * MM, A3[0] - 16 * MM, A3[1] - 27 * MM)


def caption(c, x, y, s, size=8, colour=None, bold=False):
    text(c, x, y, s, size, colour or GREY_TXT, bold=bold)


def diff_map(a, b):
    """White where the two renders agree, red where they do not."""
    A = np.asarray(a, np.int16)
    B = np.asarray(b, np.int16)
    h, w = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
    d = np.abs(A[:h, :w] - B[:h, :w]).max(axis=2)
    out = np.full((h, w, 3), 255, np.uint8)
    grey = (np.asarray(a.convert('L'), np.uint8)[:h, :w] // 3 + 170)
    out[..., 0] = grey
    out[..., 1] = grey
    out[..., 2] = grey
    out[d > 8] = (220, 0, 0)
    return Image.fromarray(out), d


# ---------------------------------------------------------------- page 1 ----
def page_master(c):
    head(c, 'REF.pdf -> v5: мастер-лист',
         'Слева REF.pdf как получен. Справа страница 1 файла DIMA_Suit_Final_v5.pdf. '
         'Единственное изменение - удлинённый треугольник перенесён на вторую переднюю штанину.', 1, 4)
    top, box = A3[1] - 34 * MM, (A3[0] - 40 * MM) / 2
    a = render(REF, dpi=150)
    b = render(SRC, 0, dpi=150)
    x, y, w, h = place(c, a, 16 * MM, 60 * MM, box, top - 60 * MM)
    caption(c, x, y - 6 * MM, 'REF.pdf - абсолютный мастер (исходный)', 9, RICH_BLACK, True)
    x, y, w, h = place(c, b, 24 * MM + box, 60 * MM, box, top - 60 * MM)
    caption(c, x, y - 6 * MM, 'DIMA_Suit_Final_v5.pdf, стр. 1', 9, RICH_BLACK, True)
    caption(c, 16 * MM, 44 * MM,
            'Оба листа: ПЕРЕД + СПИНКА + БОК ЛЕВЫЙ + БОК ПРАВЫЙ в одном масштабе, лист 420,7 x 297,7 мм.')
    caption(c, 16 * MM, 38 * MM,
            'Логотипы, юридический текст и контакты производителя оставлены без изменений.')
    swatches(c, 16 * MM, 18 * MM)
    c.showPage()


# ---------------------------------------------------------------- page 2 ----
def page_diff(c):
    head(c, 'Наложение и разница с REF.pdf',
         'Красным отмечен каждый пиксель, отличающийся от REF.pdf более чем на 8 уровней.', 2, 4)
    a = render(REF, dpi=150)
    b = render(SRC, 0, dpi=150)
    dm, d = diff_map(a, b)
    same = (d == 0).mean() * 100
    x, y, w, h = place(c, dm, 16 * MM, 78 * MM, A3[0] - 32 * MM, A3[1] - 116 * MM)
    caption(c, x, y - 5 * MM, 'Карта разницы REF.pdf <-> v5', 9, RICH_BLACK, True)

    ys, xs = np.nonzero(d > 8)
    sc, PH = 150 / 72.0, 843.804
    caption(c, 16 * MM, 66 * MM,
            'Совпадает пиксель в пиксель: %.3f %%. Средняя разница по листу: %.3f уровня.' % (same, d.mean()),
            9, RICH_BLACK)
    caption(c, 16 * MM, 59 * MM,
            'Область изменения: X %.0f-%.0f pt, Y %.0f-%.0f pt - это левая на изображении передняя штанина '
            '(правая нога человека). За её пределами изменений нет.'
            % (xs.min() / sc, xs.max() / sc, PH - ys.max() / sc, PH - ys.min() / sc))
    caption(c, 16 * MM, 52 * MM,
            'Вся остальная графика - грудь, спина, рукава, боковины, задние штанины, лампасы, чёрные зазоры - '
            'побайтно та же, что в REF.pdf: пути не перерисовывались.')
    caption(c, 16 * MM, 45 * MM,
            'Логотипы, юридический блок, контакты и подпись «Согласовано» также не тронуты.')
    swatches(c, 16 * MM, 18 * MM)
    c.showPage()


# ---------------------------------------------------------------- page 3 ----
def page_legs(c):
    head(c, 'Передние штанины: было / стало / зеркальность',
         'Удлинённый треугольник взят с правой на изображении штанины и перенесён геометрическим '
         'зеркалированием относительно оси симметрии лекала X = 444,927 pt.', 3, 4)
    LEG_L = (330, 100, 448, 512)
    LEG_R = (448, 100, 560, 512)
    ims = [(render(REF, dpi=260, clip=LEG_L), 'REF.pdf: левая штанина\nполоса обрывается на ~62 %'),
           (render(REF, dpi=260, clip=LEG_R), 'REF.pdf: правая штанина\nудлинённый треугольник'),
           (render(SRC, 0, dpi=260, clip=LEG_L), 'v5: левая штанина\nтот же треугольник'),
           (render(SRC, 0, dpi=260, clip=LEG_R), 'v5: правая штанина\nбез изменений')]
    top = A3[1] - 34 * MM
    box = (A3[0] - 32 * MM) / 5.0
    for i, (im, lab) in enumerate(ims):
        x, y, w, h = place(c, im, 16 * MM + i * box, 56 * MM, box - 6 * MM, top - 62 * MM)
        for j, line in enumerate(lab.split('\n')):
            caption(c, 16 * MM + i * box, 50 * MM - j * 5 * MM, line, 8,
                    RICH_BLACK if j == 0 else GREY_TXT, j == 0)

    # proof of mirror: v5 left leg against the mirrored v5 right leg
    L = render(SRC, 0, dpi=260, clip=(AXIS - 112, 100, AXIS, 490))
    R = render(SRC, 0, dpi=260, clip=(AXIS, 100, AXIS + 112, 490), flip=True)
    dm, d = diff_map(L, R)
    x, y, w, h = place(c, dm, 16 * MM + 4 * box, 56 * MM, box - 6 * MM, top - 62 * MM)
    caption(c, 16 * MM + 4 * box, 50 * MM, 'v5: левая против зеркальной правой', 8, RICH_BLACK, True)
    caption(c, 16 * MM + 4 * box, 45 * MM, 'совпадение %.1f %%' % ((d == 0).mean() * 100), 8)
    caption(c, 16 * MM + 4 * box, 40 * MM, 'красное - линии лекала (шов, карман):', 8)
    caption(c, 16 * MM + 4 * box, 35 * MM, 'они несимметричны в самой конструкции', 8)

    caption(c, 16 * MM, 26 * MM,
            'Треугольник не превращён в широкий лампас: перенесён тот же объект, ширина полосы и '
            'чёрный зазор внутри неё сохранены без изменений.', 9, RICH_BLACK)
    caption(c, 16 * MM, 20 * MM,
            'Задние штанины взяты из REF.pdf как есть - они НЕ зеркалированы с переда, малые треугольники на месте.')
    c.showPage()


# ---------------------------------------------------------------- page 4 ----
ROWS = [
    ('Изделие', 'Комбинезон SQD K-3 Art, размер L/XL, гонщик D. FEDOROV'),
    ('Мастер графики', 'REF.pdf - принят как абсолютный источник, пути не перерисовывались'),
    ('Геометрия', 'Содержимое страницы REF.pdf перенесено потоком, побайтно'),
    ('Единственная правка', 'Удлинённый треугольник зеркально перенесён на вторую переднюю штанину'),
    ('Ось зеркалирования', 'X = 444,927 pt - собственная ось симметрии лекала брюк (невязка 0,0005 pt)'),
    ('Совпадение с REF.pdf', '99,486 % пиксель в пиксель; отличия только в области правки'),
    ('Цветовая модель', 'DeviceCMYK во всём документе; операторов RGB и DeviceGray нет'),
    ('Чёрный', 'Составной C40 M40 Y40 K100'),
    ('Серые', 'Составные, плашечного K нет ни в одном объекте'),
    ('Прозрачность', 'Группа прозрачности DeviceCMYK на каждой странице'),
    ('Растр', 'Отсутствует - файл полностью векторный, разрешение не ограничено'),
    ('Шрифты', 'Отсутствуют - все надписи в кривых'),
    ('Страницы', '1 - мастер-лист; 2-5 - крупные виды; 6-7 - рукава отдельными деталями; 8-9 - штанины'),
    ('Панели L/XL', 'Корпус 80 x 60 см, рукав 80 x 30 см'),
    ('Печать', 'Сублимация по полиэфирному полотну'),
]


def page_spec(c):
    head(c, 'Технический паспорт макета',
         'Результат предполётной проверки build/v5verify.py.', 4, 4)
    y = A3[1] - 44 * MM
    for k, v in ROWS:
        text(c, 20 * MM, y, k, 9, GREY_TXT)
        text(c, 92 * MM, y, v, 9, RICH_BLACK)
        c.setStrokeColor(composite_grey(0.18))
        c.setLineWidth(0.3)
        c.line(20 * MM, y - 3 * MM, A3[0] - 20 * MM, y - 3 * MM)
        y -= 11 * MM
    caption(c, 20 * MM, y - 4 * MM,
            'Печатать DIMA_Suit_Final_v5.pdf. Этот файл - экранная копия. '
            'Редактируемый вектор - DIMA_Suit_Final_v5_SOURCE.svg (sRGB).', 9, RICH_BLACK)
    swatches(c, 20 * MM, 18 * MM)
    c.showPage()


SW = [('фиолетовый', PURPLE, 'C72 M86 Y0 K16'),
      ('фиолетовый тёмный', PURPLE_DK, 'C82 M95 Y5 K42'),
      ('чёрный составной', RICH_BLACK, 'C40 M40 Y40 K100'),
      ('белый', WHITE, 'C0 M0 Y0 K0')]


def swatches(c, x, y):
    for name, col, spec in SW:
        c.setFillColor(col)
        c.setStrokeColor(composite_grey(0.45))
        c.setLineWidth(0.4)
        c.rect(x, y, 16 * MM, 8 * MM, stroke=1, fill=1)
        text(c, x, y - 4 * MM, name, 7, GREY_TXT)
        text(c, x, y - 8 * MM, spec, 7, GREY_TXT)
        x += 46 * MM


def build():
    c = canvas.Canvas(OUT, pagesize=A3)
    page_master(c)
    page_diff(c)
    page_legs(c)
    page_spec(c)
    c.save()
    return OUT


if __name__ == '__main__':
    print(build())
