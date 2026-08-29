"""Design geometry derived from the sketch contours.

Every band is expressed as a FRACTION of the panel's own width at each height,
measured from the panel edge, using proportions read off DIMA.jpeg by scanline
analysis.  Deriving it from the contours (instead of hard-coding coordinates)
keeps the artwork inside the panels and makes the front/side/back joins line up.
"""
import suitsrc as S

doc, page, DR, SRECT = S.load()

FCX, BCX, MIRROR = 445.2, 767.0, 606.0


def _cl(i):
    return S.close_all(S.path_of(DR[i]))


def edges(idx, y, pick='outer', side='L', centre=None):
    """x of the panel edge at height y.  `pick`='outer' -> away from `centre`."""
    xs = S.crossings_at(_cl(idx), y)
    if not xs:
        return None
    if centre is None:
        return (min(xs), max(xs))
    left = [x for x in xs if x < centre]
    right = [x for x in xs if x > centre]
    if side == 'L':
        return (min(left) if left else min(xs), max(left) if left else min(xs))
    return (min(right) if right else max(xs), max(right) if right else max(xs))


def profile(idx, ys, centre=None, side='L'):
    """[(y, x_outer, x_inner), ...] for one half of a panel."""
    out = []
    for y in ys:
        xs = S.crossings_at(_cl(idx), y)
        if not xs:
            continue
        if centre is None:
            out.append((y, min(xs), max(xs)))
        elif side == 'L':
            lo = [x for x in xs if x <= centre]
            hi = [x for x in xs if x > centre]
            if not lo:
                continue
            out.append((y, min(lo), (max(lo) if len(lo) > 1 else (min(hi) if hi else centre))))
        else:
            lo = [x for x in xs if x < centre]
            hi = [x for x in xs if x >= centre]
            if not hi:
                continue
            out.append((y, max(hi), (min(hi) if len(hi) > 1 else (max(lo) if lo else centre))))
    return out


def band_edge(prof, frac, side='L'):
    """Inner boundary of a band `frac` of the panel width in from the edge."""
    pts = []
    for (y, xo, xi), f in zip(prof, frac):
        w = abs(xi - xo)
        pts.append((xo + f * w if side == 'L' else xo - f * w, y))
    return pts


def mid_spine(prof, inner, side='L'):
    """Centre line between the panel edge and a band's inner boundary."""
    return [((xo + ix) * 0.5, y) for (y, xo, _), (ix, _) in zip(prof, inner)]


def smooth_x(pts, passes=2):
    """Light moving average on x - removes sampling jitter, keeps the shape."""
    p = [list(q) for q in pts]
    for _ in range(passes):
        q = [list(v) for v in p]
        for i in range(1, len(p) - 1):
            q[i][0] = (p[i - 1][0] + 2 * p[i][0] + p[i + 1][0]) / 4.0
        p = q
    return [tuple(v) for v in p]


def lerp_prefix(tail, y_from, x_from, ys):
    """Points from (x_from, y_from) blending into the head of `tail`."""
    x_to, y_to = tail[0]
    out = []
    for y in ys:
        t = (y - y_from) / (y_to - y_from) if y_to != y_from else 0.0
        t = max(0.0, min(1.0, t))
        t = t * t * (3 - 2 * t)
        out.append((x_from + (x_to - x_from) * t, y))
    return out


# ------------------------------------------------------------ front torso ---
TORSO_YS = [236, 252, 270, 290, 310, 330, 348]
# 13 % of the torso width, from DIMA.jpeg scanlines at chest / waist / belt.
TORSO_FRAC = [0.150, 0.145, 0.140, 0.135, 0.132, 0.130, 0.130]

FRONT_TORSO_L = profile(80, TORSO_YS, FCX, 'L')
FRONT_TORSO_R = profile(80, TORSO_YS, FCX, 'R')
FRONT_PIPE_L = smooth_x(band_edge(FRONT_TORSO_L, TORSO_FRAC, 'L'))
FRONT_PIPE_R = smooth_x(band_edge(FRONT_TORSO_R, TORSO_FRAC, 'R'))

BACK_TORSO_YS = [214, 236, 258, 280, 300, 320, 342]
BACK_TORSO_FRAC = [0.150, 0.145, 0.140, 0.136, 0.133, 0.130, 0.130]
BACK_TORSO_L = profile(153, BACK_TORSO_YS, BCX, 'L')
BACK_TORSO_R = profile(153, BACK_TORSO_YS, BCX, 'R')
BACK_PIPE_L = smooth_x(band_edge(BACK_TORSO_L, BACK_TORSO_FRAC, 'L'))
BACK_PIPE_R = smooth_x(band_edge(BACK_TORSO_R, BACK_TORSO_FRAC, 'R'))

# ------------------------------------------------------------------- legs ---
LEG_YS = [470, 510, 545, 570, 600, 640, 680, 710, 736]
HIP_YS = [352, 386, 420, 450]
# Violet band as a fraction of leg width: ~25 % on the thigh, flaring to ~38 %
# at the knee (the chevron), then running out to nothing on the lower calf.
FLEG_FRAC = [0.310, 0.360, 0.440, 0.470, 0.400, 0.280, 0.110, 0.035, 0.015]
# The back keeps a band all the way down (~20-30 %).
BLEG_FRAC = [0.230, 0.222, 0.216, 0.212, 0.214, 0.220, 0.228, 0.220, 0.200]

FRONT_LEG_L = profile(80, LEG_YS, FCX, 'L')
FRONT_LEG_R = profile(80, LEG_YS, FCX, 'R')
FRONT_LEGBAND_L = smooth_x(band_edge(FRONT_LEG_L, FLEG_FRAC, 'L'))
FRONT_LEGBAND_R = smooth_x(band_edge(FRONT_LEG_R, FLEG_FRAC, 'R'))
FRONT_LEGBAND_L = lerp_prefix(FRONT_LEGBAND_L, 348, FRONT_PIPE_L[-1][0], HIP_YS) + FRONT_LEGBAND_L
FRONT_LEGBAND_R = lerp_prefix(FRONT_LEGBAND_R, 348, FRONT_PIPE_R[-1][0], HIP_YS) + FRONT_LEGBAND_R
FRONT_HIP_L = profile(80, HIP_YS, FCX, 'L') + FRONT_LEG_L
FRONT_HIP_R = profile(80, HIP_YS, FCX, 'R') + FRONT_LEG_R
FRONT_LEGCHEV_L = smooth_x(mid_spine(FRONT_HIP_L, FRONT_LEGBAND_L, 'L'))[1:]
FRONT_LEGCHEV_R = smooth_x(mid_spine(FRONT_HIP_R, FRONT_LEGBAND_R, 'R'))[1:]

BACK_LEG_L = profile(151, LEG_YS)
BACK_LEG_R = profile(152, LEG_YS)
BACK_LEGBAND_L = smooth_x(band_edge(BACK_LEG_L, BLEG_FRAC, 'L'))
BACK_LEGBAND_R = smooth_x(band_edge([(y, xi, xo) for (y, xo, xi) in BACK_LEG_R], BLEG_FRAC, 'R'))
BACK_LEGBAND_L = lerp_prefix(BACK_LEGBAND_L, 344, BACK_PIPE_L[-1][0], HIP_YS) + BACK_LEGBAND_L
BACK_LEGBAND_R = lerp_prefix(BACK_LEGBAND_R, 344, BACK_PIPE_R[-1][0], HIP_YS) + BACK_LEGBAND_R

# ------------------------------------------------------------- side views ---
# Union silhouette of the left-hand figure (wearer's RIGHT side).
def _side_span(y):
    xs = []
    for idx in (57, 103, 117):
        c = S.crossings_at(_cl(idx), y)
        if c:
            xs += [min(c), max(c)]
    return (min(xs), max(xs)) if xs else None


SIDE_TORSO_YS = [176, 200, 230, 260, 290, 320, 348]
SIDE_LEG_YS = [356, 400, 450, 500, 550, 600, 650, 700, 736]
# Violet wraps the side seam: the middle ~44 % of the torso, ~50 % of the leg.
SIDE_TORSO_IN, SIDE_TORSO_OUT = 0.30, 0.72
SIDE_LEG_IN, SIDE_LEG_OUT = 0.24, 0.76


def side_band(ys, f0, f1):
    front, back = [], []
    for y in ys:
        sp = _side_span(y)
        if not sp:
            continue
        x0, x1 = sp
        w = x1 - x0
        back.append((x0 + f0 * w, y))
        front.append((x0 + f1 * w, y))
    return front, back


SIDE_TORSO_FRONT, SIDE_TORSO_BACK = side_band(SIDE_TORSO_YS, SIDE_TORSO_IN, SIDE_TORSO_OUT)
SIDE_LEG_FRONT, SIDE_LEG_BACK = side_band(SIDE_LEG_YS, SIDE_LEG_IN, SIDE_LEG_OUT)
SIDE_TORSO_FRONT = smooth_x(SIDE_TORSO_FRONT, 3)
SIDE_TORSO_BACK = smooth_x(SIDE_TORSO_BACK, 3)
SIDE_LEG_FRONT = smooth_x(SIDE_LEG_FRONT, 3)
SIDE_LEG_BACK = smooth_x(SIDE_LEG_BACK, 3)
SIDE_LEG_CHEV = [((a[0] + b[0]) * 0.5, a[1]) for a, b in zip(SIDE_LEG_FRONT, SIDE_LEG_BACK)]


# --------------------------------------------------------- raglan seams ----
def _seam(idx, sub_i, n=10):
    """Raglan seam polyline, ordered top (small y) -> bottom."""
    sp = S.path_of(DR[idx])[sub_i]
    pts = S.flatten([sp], 8)[0]
    if pts[0][1] > pts[-1][1]:
        pts = pts[::-1]
    step = max(1, len(pts) // n)
    out = pts[::step]
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


RAGLAN_FL = _seam(99, 2)      # front, viewer-left  (wearer's RIGHT)
RAGLAN_FR = _seam(99, 3)      # front, viewer-right (wearer's LEFT)
RAGLAN_BL = _seam(154, 1)     # back,  viewer-left  (wearer's LEFT)
RAGLAN_BR = _seam(154, 0)     # back,  viewer-right (wearer's RIGHT)


def edge_below(idx, y_from, y_to, centre, side, step=14):
    """Panel side edge from y_from to y_to (used below the armhole)."""
    out = []
    y = y_from
    while y <= y_to:
        xs = S.crossings_at(_cl(idx), y)
        if xs:
            sel = [x for x in xs if x < centre] if side == 'L' else [x for x in xs if x > centre]
            if sel:
                out.append((min(sel) if side == 'L' else max(sel), y))
        y += step
    return out


# Outer boundary of the violet band on the wearer's RIGHT side: raglan seam
# down to the armpit, then the panel's own side seam down to the belt.
FRONT_OUTER_R = RAGLAN_FL + edge_below(80, 258, 352, FCX, 'L')
BACK_OUTER_R = RAGLAN_BR + edge_below(153, 260, 344, BCX, 'R')


def offset_x(pts, d):
    return [(x + d, y) for x, y in pts]


def merge_by_y(head, tail, y_split):
    """head above y_split, tail below - used to join the raglan-follower to the
    contour-derived torso piping."""
    return [p for p in head if p[1] < y_split] + [p for p in tail if p[1] >= y_split]


def densify(pts, n=6):
    out = []
    for i in range(len(pts) - 1):
        for k in range(n):
            t = k / n
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
    out.append(pts[-1])
    return out


# Piping on the wearer's RIGHT: parallel to the raglan seam above the armpit,
# then the contour-derived torso piping down to the belt.
FRONT_BAND_W, BACK_BAND_W = 23.0, 17.0
FRONT_PIPE_WR = merge_by_y(offset_x(RAGLAN_FL, FRONT_BAND_W), list(FRONT_PIPE_L), 236)
BACK_PIPE_WR = merge_by_y(offset_x(RAGLAN_BR, -BACK_BAND_W), list(BACK_PIPE_R), 214)


# Violet field on the upper back (wearer's LEFT), torn edge then side piping.
# Pulled left against the reference: black must stay visible on the right of
# the back panel, with only the streaks reaching across it.
BACK_FIELD_EDGE = [(782.0, 130.0), (768.0, 156.0), (752.0, 180.0), (736.0, 206.0),
                   (722.0, 234.0), (710.0, 260.0), (701.0, 284.0), (694.0, 308.0),
                   (689.0, 330.0)] + [p for p in BACK_PIPE_L if p[1] >= 342]


# ------------------------------------------------- front leg chevron (v2) ---
# DIMA.jpeg shows the outer-leg band bending through a SHARP chevron at the
# knee, not running straight down.  Fractions of the leg width measured off the
# reference by scanline; the apex node is kept as a hard corner (no smoothing),
# because the reference corner is angular, not rounded.
CHEV_YS = [352, 400, 450, 495, 528, 548, 578, 606, 640, 680, 715, 736]
CHEV_FRAC = [0.285, 0.310, 0.350, 0.425, 0.475, 0.512,
             0.320, 0.205, 0.115, 0.065, 0.040, 0.028]
CHEV_APEX = 5                       # index of the sharp corner

FRONT_CHEV_PROF_L = profile(80, [y for y in CHEV_YS if y >= 460], FCX, 'L')
FRONT_CHEV_PROF_R = profile(80, [y for y in CHEV_YS if y >= 460], FCX, 'R')


def _hip_prof(side):
    """Above the crotch the two legs are one panel, so the band width is
    measured to the centre line rather than to a non-existent inseam."""
    out = []
    for (y, xo, xi) in profile(80, [y for y in CHEV_YS if y < 460], FCX, side):
        inner = min(xi, FCX) if side == 'L' else max(xi, FCX)
        out.append((y, xo, inner))
    return out


def _chev_edge(side):
    """Band inner edge with the knee corner, blended up to the torso piping."""
    prof = _hip_prof(side) + (FRONT_CHEV_PROF_L if side == 'L' else FRONT_CHEV_PROF_R)
    pts = []
    for (y, xo, xi), f in zip(prof, CHEV_FRAC):
        w = abs(xi - xo)
        pts.append((xo + f * w if side == 'L' else xo - f * w, y))
    return pts


FRONT_CHEV_L = _chev_edge('L')
FRONT_CHEV_R = _chev_edge('R')


def band_pinstripe(edge, prof, frac_out, side):
    """Line inside the band, `frac_out` of the band width out from its inner
    edge - follows the chevron exactly, corner included."""
    out = []
    for (x, y), (yy, xo, xi) in zip(edge, prof):
        d = (x - xo) if side == 'L' else (xo - x)
        out.append((x - d * frac_out, y) if side == 'L' else (x + d * frac_out, y))
    return out


_HIP_L = _hip_prof('L') + FRONT_CHEV_PROF_L
_HIP_R = _hip_prof('R') + FRONT_CHEV_PROF_R
FRONT_CHEV_PIN_L = band_pinstripe(FRONT_CHEV_L, _HIP_L, 0.40, 'L')
FRONT_CHEV_PIN_R = band_pinstripe(FRONT_CHEV_R, _HIP_R, 0.40, 'R')

# Band width at each node, so the pinstripe can be kept to the ~7 % of the band
# measured on the reference instead of a fixed weight.
FRONT_CHEV_W_L = [abs(x - xo) for (x, y), (yy, xo, xi) in zip(FRONT_CHEV_L, _HIP_L)]
FRONT_CHEV_W_R = [abs(x - xo) for (x, y), (yy, xo, xi) in zip(FRONT_CHEV_R, _HIP_R)]
