"""Extract vector geometry from the SQD K-3 Art technical sketch (CorelDRAW PDF).

Design space == source PDF page space, y measured DOWNWARD from the top-left
corner (PyMuPDF convention).  Everything downstream works in this space so that
coordinates can be read straight off a rendered preview of the source sheet.
"""
import pymupdf

SRC = 'Suit_SQD-K-3art-ЭСКИЗ.pdf'


def load():
    doc = pymupdf.open(SRC)
    page = doc[0]
    return doc, page, page.get_drawings(), page.rect


def path_of(group):
    """PyMuPDF drawing group -> [subpath, ...]; subpath = ('M',x,y) + segments."""
    subs, cur = [], None
    for it in group['items']:
        op = it[0]
        if op == 'l':
            p0, p1 = it[1], it[2]
            if cur is None or _far(cur[-1], p0):
                if cur:
                    subs.append(cur)
                cur = [('M', p0.x, p0.y)]
            cur.append(('L', p1.x, p1.y))
        elif op == 'c':
            p0, c1, c2, p1 = it[1], it[2], it[3], it[4]
            if cur is None or _far(cur[-1], p0):
                if cur:
                    subs.append(cur)
                cur = [('M', p0.x, p0.y)]
            cur.append(('C', c1.x, c1.y, c2.x, c2.y, p1.x, p1.y))
        elif op == 're':
            r = it[1]
            if cur:
                subs.append(cur)
                cur = None
            subs.append([('M', r.x0, r.y0), ('L', r.x1, r.y0),
                         ('L', r.x1, r.y1), ('L', r.x0, r.y1), ('Z',)])
        elif op == 'qu':
            q = it[1]
            if cur:
                subs.append(cur)
                cur = None
            subs.append([('M', q.ul.x, q.ul.y), ('L', q.ur.x, q.ur.y),
                         ('L', q.lr.x, q.lr.y), ('L', q.ll.x, q.ll.y), ('Z',)])
    if cur:
        subs.append(cur)
    return subs


def _far(seg, pt, tol=0.05):
    x, y = (seg[-2], seg[-1]) if seg[0] != 'Z' else (None, None)
    if x is None:
        return True
    return abs(x - pt.x) > tol or abs(y - pt.y) > tol


def close_all(subs):
    return [s + [('Z',)] if s[-1][0] != 'Z' else s for s in subs]


def bbox(subs):
    xs, ys = [], []
    for s in subs:
        for seg in s:
            v = seg[1:]
            xs += list(v[0::2])
            ys += list(v[1::2])
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def flatten(subs, n=24):
    """Subpaths -> list of point lists (polylines)."""
    out = []
    for s in subs:
        pts, cx, cy = [], 0.0, 0.0
        for seg in s:
            if seg[0] == 'M':
                cx, cy = seg[1], seg[2]
                pts.append((cx, cy))
            elif seg[0] == 'L':
                cx, cy = seg[1], seg[2]
                pts.append((cx, cy))
            elif seg[0] == 'C':
                x1, y1, x2, y2, x3, y3 = seg[1:7]
                for i in range(1, n + 1):
                    t = i / n
                    u = 1 - t
                    pts.append((u**3 * cx + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
                                u**3 * cy + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3))
                cx, cy = x3, y3
        if pts:
            out.append(pts)
    return out


def span_at(subs, y):
    """Min/max x where the (closed) outline crosses horizontal line `y`."""
    xs = []
    for poly in flatten(subs):
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            if (y0 - y) * (y1 - y) < 0 or y0 == y:
                if y1 != y0:
                    xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
                else:
                    xs.append(x0)
    return (min(xs), max(xs)) if xs else None


def crossings_at(subs, y):
    xs = []
    for poly in flatten(subs):
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            if (y0 - y) * (y1 - y) < 0:
                xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return sorted(xs)
