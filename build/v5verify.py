"""Pre-flight for DIMA_Suit_Final_v5.pdf.

Checks what a sublimation printer would reject the file for - a stray RGB or
flat-K object, an unembedded font, a low-resolution raster, art outside the
trim - and then proves by pixel difference that the artwork really is REF.pdf
plus exactly the one correction the brief asked for.
"""
import re
import collections
import numpy as np
import pymupdf

OUT = 'DIMA_Suit_Final_v5.pdf'
REF = 'REF.pdf'

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)'
CMYK = re.compile((r'(%s)\s+(%s)\s+(%s)\s+(%s)\s+(k|K)\b' % ((NUM,) * 4)).encode())
RGB_OPS = re.compile(rb'(?<![A-Za-z0-9])(rg|RG|sc|SC|scn|SCN|g|G)(?![A-Za-z0-9])')
SHOW_TEXT = re.compile(rb'(?<![A-Za-z0-9])(Tj|TJ|\'|")(?![A-Za-z0-9])')

RICH_BLACK = (0.4, 0.4, 0.4, 1.0)

ok = True


def say(good, label, detail=''):
    global ok
    if not good:
        ok = False
    print(f'  [{"OK" if good else "!!"}] {label}' + (f'   {detail}' if detail else ''))


def streams(doc):
    """Every content stream in the file: pages and the Form XObjects they use."""
    seen = set()
    for page in doc:
        yield f'page {page.number + 1}', page.read_contents()
        for xref, *_ in page.get_xobjects():
            if xref in seen:
                continue
            seen.add(xref)
            try:
                yield f'xobject {xref}', doc.xref_stream(xref)
            except Exception:
                pass


def main():
    doc = pymupdf.open(OUT)
    print(f'{OUT}  -  {doc.page_count} pages')
    for p in doc:
        print(f'   {p.number + 1}: {p.rect.width / 72 * 25.4:6.1f} x '
              f'{p.rect.height / 72 * 25.4:6.1f} mm')

    print('\n1. Structure')
    say(all(not p.get_images() for p in doc), 'no raster images anywhere',
        'the file is 100 % vector, so resolution is unlimited')
    say(all(not p.get_fonts() for p in doc), 'no font resources on any page')

    fonts = []
    for page in doc:
        for xref, *_ in page.get_xobjects():
            res = doc.xref_get_key(xref, 'Resources')
            if res and res[0] == 'dict' and '/Font' in res[1]:
                fonts.append(xref)
    say(not fonts, 'no font resources in any Form XObject', str(fonts))
    say(not any(SHOW_TEXT.search(s) for _, s in streams(doc)),
        'no text-showing operators - every glyph is an outline')

    print('\n2. Colour')
    bad = [(w, RGB_OPS.findall(s)) for w, s in streams(doc)]
    bad = [(w, collections.Counter(x.decode() for x in f)) for w, f in bad if f]
    say(not bad, 'no RGB / DeviceGray / ICC colour operators', str(bad[:4]))

    fills, strokes = collections.Counter(), collections.Counter()
    for _, s in streams(doc):
        for m in CMYK.finditer(s):
            v = tuple(round(float(x), 4) for x in m.groups()[:4])
            (fills if m.group(5) == b'k' else strokes)[v] += 1
    print('     fills:')
    for v, n in fills.most_common():
        print(f'       C{v[0]*100:6.2f} M{v[1]*100:6.2f} Y{v[2]*100:6.2f} K{v[3]*100:6.2f}  x{n}')
    print('     strokes:')
    for v, n in strokes.most_common():
        print(f'       C{v[0]*100:6.2f} M{v[1]*100:6.2f} Y{v[2]*100:6.2f} K{v[3]*100:6.2f}  x{n}')

    allc = set(fills) | set(strokes)
    flat = [c for c in allc if c[3] > 0.05 and c[0] == c[1] == c[2] == 0]
    say(not flat, 'no flat-K neutrals - every grey and black is composite', str(flat))
    say(RICH_BLACK in fills, 'rich black present as C40 M40 Y40 K100',
        f'{fills[RICH_BLACK]} fills')
    heavy = [c for c in allc if sum(c) > 3.2]
    say(not heavy, 'total ink coverage within 320 %', str(heavy))

    print('\n3. Trim and transparency group')
    for page in doc:
        pm = page.get_pixmap(dpi=60, colorspace=pymupdf.csGRAY)
        a = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width)
        edge = min(a[0].min(), a[-1].min(), a[:, 0].min(), a[:, -1].min())
        say(edge > 250, f'page {page.number + 1}: no artwork runs off the trim edge',
            f'darkest edge pixel {edge}')
    groups = [p.number + 1 for p in doc
              if doc.xref_get_key(p.xref, 'Group/CS')[1] != '/DeviceCMYK']
    say(not groups, 'every page blends in a DeviceCMYK transparency group',
        f'pages without it: {groups}')

    print('\n4. Overlay / difference against REF.pdf')
    ref = pymupdf.open(REF)
    DPI = 150
    a = ref[0].get_pixmap(dpi=DPI, colorspace=pymupdf.csRGB)
    b = doc[0].get_pixmap(dpi=DPI, colorspace=pymupdf.csRGB)
    A = np.frombuffer(a.samples, np.uint8).reshape(a.height, a.width, 3).astype(np.int16)
    B = np.frombuffer(b.samples, np.uint8).reshape(b.height, b.width, 3).astype(np.int16)
    say(A.shape == B.shape, 'page 1 has the master sheet\'s exact geometry',
        f'{a.width}x{a.height} vs {b.width}x{b.height}')
    d = np.abs(A - B).max(axis=2)
    same = (d == 0).mean()
    print(f'     identical pixels {same * 100:.3f} %   mean abs difference {d.mean():.3f}')

    sc, PH = DPI / 72.0, ref[0].rect.height
    ys, xs = np.nonzero(d > 8)
    if len(xs):
        box = (302, 100, 446, 505)          # the image-LEFT front leg
        inside = ((xs / sc >= box[0]) & (xs / sc <= box[2])
                  & (PH - ys / sc >= box[1]) & (PH - ys / sc <= box[3]))
        say(inside.mean() > 0.995,
            'the only difference from REF.pdf is the image-LEFT front leg',
            f'{(~inside).sum()} stray pixels, '
            f'changed area x[{xs.min()/sc:.0f},{xs.max()/sc:.0f}] '
            f'y[{PH-ys.max()/sc:.0f},{PH-ys.min()/sc:.0f}]')

    print('\n5. Front legs carry the same elongated triangle')
    AXIS = 444.927
    page = doc[0]
    L = pymupdf.Rect(AXIS - 115, PH - 500, AXIS, PH - 100)
    R = pymupdf.Rect(AXIS, PH - 500, AXIS + 115, PH - 100)
    pl = page.get_pixmap(dpi=200, clip=L, colorspace=pymupdf.csRGB)
    pr = page.get_pixmap(dpi=200, clip=R, colorspace=pymupdf.csRGB)
    PL = np.frombuffer(pl.samples, np.uint8).reshape(pl.height, pl.width, 3)
    PR = np.frombuffer(pr.samples, np.uint8).reshape(pr.height, pr.width, 3)[:, ::-1]
    h, w = min(PL.shape[0], PR.shape[0]), min(PL.shape[1], PR.shape[1])
    dd = np.abs(PL[:h, :w].astype(np.int16) - PR[:h, :w].astype(np.int16)).max(axis=2)
    say(dd.mean() < 12, 'left leg matches the mirrored right leg',
        f'mean abs difference {dd.mean():.2f}, identical {(dd == 0).mean() * 100:.1f} %')

    print('\n6. The element stays a narrow band, not a lampas')
    pm = page.get_pixmap(dpi=200, colorspace=pymupdf.csRGB)
    img = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width, 3)
    s2 = 200 / 72.0
    purple = (np.abs(img.astype(np.int16) - np.array([89, 59, 136])).max(axis=2) < 30)
    garment = img.max(axis=2) < 250
    print(f'     {"y, pt":>7} {"leg":>6} {"деталь, pt":>11} {"фиолет, pt":>11} '
          f'{"доля":>7} {"полос":>6}')
    worst = 0.0
    for ydev in (460, 420, 380, 340, 300, 260, 220, 180, 150):
        r = int((PH - ydev) * s2)
        for name, (x0, x1) in (('left', (330, 445)), ('right', (445, 560))):
            row_p = purple[r, int(x0 * s2):int(x1 * s2)]
            row_g = garment[r, int(x0 * s2):int(x1 * s2)]
            if row_g.sum() < 4:
                continue
            runs, run = [], 0
            for v in row_p:
                if v:
                    run += 1
                elif run:
                    runs.append(run)
                    run = 0
            if run:
                runs.append(run)
            frac = row_p.sum() / row_g.sum()
            worst = max(worst, frac)
            print(f'     {ydev:7d} {name:>6} {row_g.sum()/s2:11.1f} {row_p.sum()/s2:11.1f} '
                  f'{frac*100:6.1f}% {len(runs):6d}')
    say(worst < 0.42, 'violet never takes more than 42 % of a leg\'s width',
        f'widest {worst*100:.1f} %')

    print('\n' + ('PASS - the file is production ready.' if ok else
                  'FAIL - see the marked lines above.'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
