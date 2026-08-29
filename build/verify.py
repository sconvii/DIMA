#!/usr/bin/env python3
"""Pre-flight the finished layout: colour space, fonts, rasters, geometry."""
import re, sys, os
import pymupdf
import numpy as np

PDF = 'DIMA_Suit_Final_Print.pdf'
RGB_OPS = re.compile(rb'(?<![A-Za-z0-9])(rg|RG)(?![A-Za-z0-9])')
GRAY_OPS = re.compile(rb'(?<![A-Za-z0-9])(g|G)(?![A-Za-z0-9])')
CMYK_OPS = re.compile(rb'(?<![A-Za-z0-9])(k|K)(?![A-Za-z0-9])')
CS_OPS = re.compile(rb'(?<![A-Za-z0-9])(cs|CS)(?![A-Za-z0-9])')

fails, warns = [], []


def ok(msg):
    print('  [ok]   ' + msg)


def bad(msg):
    fails.append(msg)
    print('  [FAIL] ' + msg)


def warn(msg):
    warns.append(msg)
    print('  [warn] ' + msg)


def main():
    if not os.path.exists(PDF):
        bad('%s does not exist' % PDF)
        return 1
    doc = pymupdf.open(PDF)
    print('== structure ==')
    ok('opens without error, %d pages, %.1f KB' % (doc.page_count, os.path.getsize(PDF) / 1024))
    for i, p in enumerate(doc):
        r = p.rect
        print('   page %d: %.1f x %.1f pt = %.1f x %.1f mm'
              % (i + 1, r.width, r.height, r.width / 72 * 25.4, r.height / 72 * 25.4))

    print('== colour space ==')
    n_rgb = n_gray = n_cmyk = 0
    for i, p in enumerate(doc):
        raw = p.read_contents()
        r = len(RGB_OPS.findall(raw))
        k = len(CMYK_OPS.findall(raw))
        # 'g'/'G' also appear inside other tokens; count standalone only
        gsel = len([m for m in GRAY_OPS.finditer(raw)
                    if raw[max(0, m.start() - 1):m.start()] in (b' ', b'\n', b'\r', b'\t')])
        n_rgb += r; n_cmyk += k; n_gray += gsel
        if r:
            bad('page %d contains %d RGB colour operators' % (i + 1, r))
    if not n_rgb:
        ok('no RGB (rg/RG) colour operators anywhere; %d DeviceCMYK (k/K) operators' % n_cmyk)
    if n_gray:
        warn('%d DeviceGray (g/G) operators found' % n_gray)
    else:
        ok('no DeviceGray colour operators')

    print('== fonts ==')
    total_fonts = 0
    for i, p in enumerate(doc):
        f = p.get_fonts(full=True)
        total_fonts += len(f)
        for ff in f:
            print('     page %d font: %s' % (i + 1, ff))
    if total_fonts == 0:
        ok('no font resources at all - every glyph is vector outlines')
    else:
        for i, p in enumerate(doc):
            for ff in p.get_fonts(full=True):
                if ff[1] == 'n/a':
                    bad('page %d: font %s is NOT embedded' % (i + 1, ff[3]))

    print('== raster images ==')
    total_img = 0
    for i, p in enumerate(doc):
        imgs = p.get_images(full=True)
        total_img += len(imgs)
        for im in imgs:
            xref, _, w, h = im[0], im[1], im[2], im[3]
            pr = p.get_image_rects(xref)
            if pr:
                bx = pr[0]
                dpi_x = w / (bx.width / 72.0) if bx.width else 0
                dpi_y = h / (bx.height / 72.0) if bx.height else 0
                lbl = 'page %d image %dx%d px at %.0f x %.0f dpi' % (i + 1, w, h, dpi_x, dpi_y)
                if min(dpi_x, dpi_y) < 150:
                    bad(lbl + '  (below the 150 dpi minimum)')
                else:
                    ok(lbl)
    if total_img == 0:
        ok('no raster images - the layout is 100% vector, so resolution is unlimited')

    print('== geometry / bleed ==')
    for i, p in enumerate(doc):
        r = p.rect
        marks = p.get_drawings()
        outside = 0
        for m in marks:
            b = m['rect']
            if (b.x1 < -1 or b.y1 < -1 or b.x0 > r.width + 1 or b.y0 > r.height + 1):
                outside += 1
        if outside:
            warn('page %d has %d drawing groups entirely outside the page' % (i + 1, outside))
        else:
            ok('page %d: no artwork outside the trim box (%d vector groups)' % (i + 1, len(marks)))

    print('== render check ==')
    for i, p in enumerate(doc):
        try:
            pix = p.get_pixmap(dpi=72, colorspace=pymupdf.csRGB, alpha=True)
            a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 4)
            cov = (a[..., 3] > 8).mean()
            if cov < 0.01:
                bad('page %d renders essentially empty (%.3f coverage)' % (i + 1, cov))
            else:
                ok('page %d renders, %.1f%% of the sheet carries artwork' % (i + 1, cov * 100))
        except Exception as e:
            bad('page %d failed to render: %s' % (i + 1, e))

    print('== black build ==')
    raw = doc[0].read_contents()
    quads = set(re.findall(rb'([\d]*\.?[\d]+) ([\d]*\.?[\d]+) ([\d]*\.?[\d]+) ([\d]*\.?[\d]+) k', raw))
    def num(v):
        return float(v.decode())
    rich = [q for q in quads if abs(num(q[3]) - 1.0) < 1e-6]
    if any(all(abs(num(v) - 0.4) < 1e-6 for v in q[:3]) for q in rich):
        ok('black is the specified rich build C40 M40 Y40 K100')
    else:
        bad('no C40 M40 Y40 K100 fill found; blacks are %s' % sorted(rich))
    plain_k = [q for q in quads if all(num(v) == 0 for v in q[:3]) and num(q[3]) > 0]
    if plain_k:
        warn('flat K-only fills present (fine for annotation): %s' % sorted(plain_k))
    print('   distinct CMYK fills on page 1: %d' % len(quads))
    for q in sorted(quads):
        print('     C%-5s M%-5s Y%-5s K%-5s' % tuple(v.decode() for v in q))

    print()
    if fails:
        print('RESULT: %d FAILURE(S), %d warning(s)' % (len(fails), len(warns)))
        for f in fails:
            print('   - ' + f)
        return 1
    print('RESULT: PASS  (%d warning(s))' % len(warns))
    for w in warns:
        print('   - ' + w)
    return 0


if __name__ == '__main__':
    sys.exit(main())
