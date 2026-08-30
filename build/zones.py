"""Control points that carry each traced zone onto its technical panel.

The transform per zone is a SIMILARITY: one uniform scale plus a translation.
Nothing is stretched to fill a pattern that has different proportions - the
whole group moves together, so element widths, angles, spacings and the black
gaps between them survive exactly as traced.

Scale is taken from each panel's WIDTH, because the artwork is width-driven
(band widths and the gaps between them); the anchor is a landmark the artwork
actually hangs off - the crotch for legs, the shoulder for torsos, the cuff for
sleeves.
"""
import numpy as np
import trace as T
import suitsrc as S

# ---------------------------------------------------------------- reference --
M = T.masks()
GAR = M['garment']
REF_H, REF_W = GAR.shape

VIEW = {                      # blocks measured off the reference layout
    'front': (168, 20, 548, 800),
    'back': (686, 20, 1075, 800),
    'side_a': (548, 290, 616, 782),
    'side_b': (620, 290, 692, 782),
    'sleeve_black': (30, 118, 136, 500),
    'sleeve_purple': (1100, 118, 1210, 500),
}


def _rows(box):
    return T.panel_rows(GAR, box)


def _span(box, y):
    return T.panel_span(GAR, box, y)


def _runs(box, y):
    """Contiguous garment runs on row y - two runs means the legs have split."""
    x0, y0, x1, y1 = box
    row = GAR[y, x0:x1]
    out, start = [], None
    for i, v in enumerate(row):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start > 4:
                out.append((x0 + start, x0 + i))
            start = None
    if start is not None:
        out.append((x0 + start, x0 + len(row)))
    return out


def crotch_y(view):
    """First row below mid-height where the view splits into two legs."""
    box = VIEW[view]
    y0, y1 = _rows(box)
    for y in range((y0 + y1) // 2, y1):
        if len(_runs(box, y)) >= 2:
            return y
    return (y0 + y1) // 2


def ankle_y(view):
    """Where the cuff starts - the width drops off a cliff."""
    box = VIEW[view]
    y0, y1 = _rows(box)
    widths = [(y, sum(b - a for a, b in _runs(box, y))) for y in range(y0, y1)]
    lo = int((y1 - y0) * 0.80) + y0
    ref = np.median([w for y, w in widths if lo - 60 < y < lo])
    for y, w in widths:
        if y > lo and w < ref * 0.72:
            return y
    return y1


def leg_box(view, side):
    """Bounding box of one leg in the reference, below the crotch."""
    box = VIEW[view]
    cy, ay = crotch_y(view), ankle_y(view)
    runs = _runs(box, (cy + ay) // 2)
    if len(runs) < 2:
        runs = _runs(box, cy + 8)
    runs.sort()
    a, b = (runs[0], runs[-1])
    r = a if side == 'L' else b
    return (r[0] - 4, cy, r[1] + 4, ay + 2)


def leg_width(view, side, frac=0.40):
    """Leg width at a fixed fraction of the crotch-to-ankle run."""
    cy, ay = crotch_y(view), ankle_y(view)
    y = int(cy + (ay - cy) * frac)
    runs = _runs(VIEW[view], y)
    runs.sort()
    if len(runs) < 2:
        return None
    r = runs[0] if side == 'L' else runs[-1]
    return r[1] - r[0], r


def torso_width(view, frac=0.30):
    """Body width across the chest, arms included - the whole view is scaled."""
    box = VIEW[view]
    y0, y1 = _rows(box)
    cy = crotch_y(view)
    y = int(y0 + (cy - y0) * frac)
    sp = _span(box, y)
    return sp[1] - sp[0], sp, y


def sleeve_metrics(view):
    box = VIEW[view]
    y0, y1 = _rows(box)
    y = int(y0 + (y1 - y0) * 0.55)
    sp = _span(box, y)
    return {'rows': (y0, y1), 'mid_y': y, 'span': sp, 'width': sp[1] - sp[0]}


def side_metrics(view):
    box = VIEW[view]
    y0, y1 = _rows(box)
    y = int(y0 + (y1 - y0) * 0.35)
    sp = _span(box, y)
    return {'rows': (y0, y1), 'ref_y': y, 'span': sp, 'width': sp[1] - sp[0]}


class Similarity:
    """p_pattern = (p_ref - ref_anchor) * scale + pat_anchor, y flipped as needed."""

    def __init__(self, scale, ref_anchor, pat_anchor, flip_x=False):
        self.s = scale
        self.ra = np.asarray(ref_anchor, float)
        self.pa = np.asarray(pat_anchor, float)
        self.flip = flip_x

    def __call__(self, pts):
        p = np.asarray(pts, float) - self.ra
        if self.flip:
            p = p * np.array([-1.0, 1.0])
        return p * self.s + self.pa

    def __repr__(self):
        return 'Similarity(scale=%.4f ref=%s pat=%s flip=%s)' % (
            self.s, tuple(np.round(self.ra, 1)), tuple(np.round(self.pa, 1)), self.flip)


# ------------------------------------------------------------------ pattern --
_doc, _page, DR, SRECT = S.load()
FCX, BCX, MIRROR = 445.2, 767.0, 606.0
PAT = {                      # design-space landmarks of the technical sketch
    'front': {'body': 80, 'cx': FCX, 'crotch': 445.0, 'ankle': 713.0, 'top': 127.5},
    'back': {'body': None, 'cx': BCX, 'crotch': 345.0, 'ankle': 713.0, 'top': 124.0},
}


def _cl(i):
    return S.close_all(S.path_of(DR[i]))


def pat_leg(view, side):
    """(outer edge x at the crotch, width at 40 % of the crotch-ankle run)."""
    if view == 'front':
        idx, cx = 80, FCX
        cy, ay = 452.0, 713.0
    else:
        idx, cx = (151 if side == 'L' else 152), BCX
        cy, ay = 348.0, 713.0
    y = cy + (ay - cy) * 0.40
    xs = S.crossings_at(_cl(idx), y)
    if view == 'front':
        sel = [x for x in xs if x < cx] if side == 'L' else [x for x in xs if x > cx]
    else:
        sel = xs
    lo, hi = min(sel), max(sel)
    outer = lo if side == 'L' else hi
    xs0 = S.crossings_at(_cl(idx), cy + 6)
    if view == 'front':
        s0 = [x for x in xs0 if x < cx] if side == 'L' else [x for x in xs0 if x > cx]
    else:
        s0 = xs0
    outer0 = min(s0) if side == 'L' else max(s0)
    return outer0, cy, abs(hi - lo), outer


def pat_torso(view):
    """Body width across the chest and the shoulder anchor."""
    idx = 80 if view == 'front' else 153
    cx = FCX if view == 'front' else BCX
    y = 200.0
    xs = S.crossings_at(_cl(idx), y)
    return min(xs), max(xs), y, cx


def pat_sleeve(idxs):
    """Sleeve panel: width at mid height and the cuff anchor."""
    xs_all, ys_all = [], []
    for i in idxs:
        r = DR[i]['rect']
        xs_all += [r.x0, r.x1]
        ys_all += [r.y0, r.y1]
    x0, x1, y0, y1 = min(xs_all), max(xs_all), min(ys_all), max(ys_all)
    y = y0 + (y1 - y0) * 0.55
    xs = []
    for i in idxs:
        xs += S.crossings_at(_cl(i), y)
    return {'box': (x0, y0, x1, y1), 'mid_y': y,
            'span': (min(xs), max(xs)) if xs else (x0, x1),
            'width': (max(xs) - min(xs)) if xs else (x1 - x0)}


def pat_side(idxs):
    xs_all, ys_all = [], []
    for i in idxs:
        r = DR[i]['rect']
        xs_all += [r.x0, r.x1]
        ys_all += [r.y0, r.y1]
    x0, x1, y0, y1 = min(xs_all), max(xs_all), min(ys_all), max(ys_all)
    return {'box': (x0, y0, x1, y1)}


def pat_view_span(view, y):
    """Full silhouette width of a pattern view at height y, sleeves included."""
    idxs = ({'front': [76, 77, 78, 79, 80], 'back': [153, 157, 158, 159, 160]})[view]
    xs = []
    for i in idxs:
        xs += S.crossings_at(_cl(i), y)
    return (min(xs), max(xs)) if xs else None


PAT_TOP = {'front': 127.5, 'back': 124.0}
PAT_CROTCH = {'front': 452.0, 'back': 348.0}


def view_transform(view):
    """Similarity for a whole view: scale from silhouette width, anchored on the
    crotch - the landmark both sources agree on."""
    box = VIEW[view]
    ry0, ry1 = _rows(box)
    rcy = crotch_y(view)
    ry = int(ry0 + (rcy - ry0) * 0.55)
    rsp = _span(box, ry)
    rw = rsp[1] - rsp[0]

    pty = PAT_TOP[view] + (PAT_CROTCH[view] - PAT_TOP[view]) * 0.55
    psp = pat_view_span(view, pty)
    pw = psp[1] - psp[0]

    s = pw / rw
    rcx = (rsp[0] + rsp[1]) / 2.0
    pcx = (psp[0] + psp[1]) / 2.0
    return Similarity(s, (rcx, rcy), (pcx, PAT_CROTCH[view])), {
        'ref_w': rw, 'pat_w': pw, 'ref_row': ry, 'pat_row': pty}


def leg_transform(view, side):
    """Similarity for one leg: scale from the leg's own width, anchored on the
    outer edge at the crotch, so band widths and gaps transfer unchanged."""
    rw, rrun = leg_width(view, side)
    rcy = crotch_y(view)
    runs = _runs(VIEW[view], rcy + 8)
    runs.sort()
    r0 = runs[0] if side == 'L' else runs[-1]
    r_outer = r0[0] if side == 'L' else r0[1]

    p_outer0, pcy, pw, _ = pat_leg(view, side)
    s = pw / rw
    return Similarity(s, (r_outer, rcy), (p_outer0, pcy)), {'ref_w': rw, 'pat_w': pw}


def sleeve_transform(ref_view, pat_idxs, flip=False):
    rm = sleeve_metrics(ref_view)
    pm = pat_sleeve(pat_idxs)
    s = pm['width'] / rm['width']
    rcx = (rm['span'][0] + rm['span'][1]) / 2.0
    pcx = (pm['span'][0] + pm['span'][1]) / 2.0
    # anchor on the cuff: that is where the artwork sits
    return Similarity(s, (rcx, rm['rows'][1]), (pcx, pm['box'][3])), {
        'ref_w': rm['width'], 'pat_w': pm['width']}


SIDE_SEAM = {'L': 192.5, 'R': 2 * MIRROR - 192.5}


def side_transform(ref_view, side):
    """The reference gives a narrow side GUSSET; the sketch draws a full side
    VIEW of the figure.  Scaling the gusset up to fill the view would distort
    it, so it is placed at the SAME scale as the legs, centred on the side seam.
    That keeps its internal geometry, keeps it continuous with the front and
    back legs, and leaves the rest of the side view black - as the reference
    panel is (71-73 % black).
    """
    rm = side_metrics(ref_view)
    _, info = leg_transform('front', 'L')
    s = info['pat_w'] / info['ref_w']
    rcx = (rm['span'][0] + rm['span'][1]) / 2.0
    # the gusset spans the crotch-to-ankle run, same as the legs
    return Similarity(s, (rcx, rm['rows'][0]), (SIDE_SEAM[side], 352.0)), {
        'ref_w': rm['width'], 'scale': s}
