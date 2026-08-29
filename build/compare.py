#!/usr/bin/env python3
"""Objective check: classify scanlines of the reference photo and of the
finished layout into violet / black / white runs and compare the proportions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pymupdf
from PIL import Image


def masks(a, alpha=None):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    L = a @ np.array([0.299, 0.587, 0.114], np.float32)
    mx_, mn_ = a.max(2), a.min(2)
    sat = np.where(mx_ > 0, (mx_ - mn_) / np.maximum(mx_, 1e-6), 0)
    bg = (alpha < 128) if alpha is not None else ((sat < 0.10) & (L > 0.38) & (L < 0.78))
    return (b - r > 0.030) & ~bg, (L > 0.62) & (sat < 0.22) & ~bg, bg


def runs_a(a, alpha, y, x0, x1):
    P, W, BG = masks(a, alpha)
    row = ['.' if BG[y, x] else ('W' if W[y, x] else ('P' if P[y, x] else 'K'))
           for x in range(x0, x1)]
    out, cur, n = [], row[0], 1
    for ch in row[1:]:
        if ch == cur:
            n += 1
        else:
            out.append((cur, n)); cur, n = ch, 1
    out.append((cur, n))
    return [(c, k) for c, k in out if k >= 2]


def runs(a, y, x0, x1):
    P, W, BG = masks(a)
    row = []
    for x in range(x0, x1):
        row.append('.' if BG[y, x] else ('W' if W[y, x] else ('P' if P[y, x] else 'K')))
    out, cur, n = [], row[0], 1
    for ch in row[1:]:
        if ch == cur:
            n += 1
        else:
            out.append((cur, n)); cur, n = ch, 1
    out.append((cur, n))
    return [(c, k) for c, k in out if k >= 2]


def fractions(rr):
    tot = sum(n for c, n in rr if c != '.')
    if not tot:
        return 0, 0, 0
    p = sum(n for c, n in rr if c == 'P') / tot
    w = sum(n for c, n in rr if c == 'W') / tot
    return p, w, 1 - p - w


REF_ROWS = [('shoulder', .134), ('chest hi', .170), ('chest', .209), ('chest lo', .250),
            ('waist hi', .300), ('waist', .345), ('belt', .390), ('hip', .440),
            ('thigh', .520), ('knee', .620), ('calf', .720), ('low calf', .820)]
# design-space y for the same landmarks on the sheet
# landmark-anchored: shoulder 0.115->155, belt 0.383->340, ankle cuff 0.885->713
OUT_Y = [168, 193, 220, 248, 283, 314, 345, 382, 442, 516, 590, 665]


def main():
    ref = np.asarray(Image.open('DIMA.jpeg').convert('RGB')).astype(np.float32) / 255.
    RH, RW, _ = ref.shape
    doc = pymupdf.open('DIMA_Suit_Final_Print.pdf')
    pg = doc[0]
    dpi = 200
    pix = pg.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=True)
    raw = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 4)
    out = raw[..., :3].astype(np.float32) / 255.
    oal = raw[..., 3]
    s = dpi / 72.

    print('%-10s | %-28s | %-28s' % ('row', 'REFERENCE  P / W / K', 'LAYOUT  P / W / K'))
    print('-' * 76)
    for view, (rx0, rx1), (ox0, ox1) in (('FRONT', (0.02, 0.50), (296, 596)),
                                         ('BACK', (0.52, 1.00), (618, 918))):
        print(f'== {view} ==')
        for (name, ry), oy in zip(REF_ROWS, OUT_Y):
            rr = runs(ref, int(ry * RH), int(rx0 * RW), int(rx1 * RW))
            oo = runs_a(out, oal, int(oy * s), int(ox0 * s), int(ox1 * s))
            rp, rw, rk = fractions(rr)
            op, ow, ok = fractions(oo)
            flag = '  <-- ' if abs(rp - op) > 0.14 else ''
            print(f'{name:10s} | P{rp*100:5.1f}%  W{rw*100:4.1f}%  K{rk*100:5.1f}%   '
                  f'| P{op*100:5.1f}%  W{ow*100:4.1f}%  K{ok*100:5.1f}%{flag}')
        print()


if __name__ == '__main__':
    main()
