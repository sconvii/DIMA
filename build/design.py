"""The DIMA livery as vector geometry, in the coordinate space of the sketch.

Each motif is defined once and painted CLIPPED to every panel it crosses, so a
graphic that leaves the front panel re-enters the side or sleeve panel already
aligned: the front->side->back and body->sleeve joins match by construction.

Motif language read off DIMA.jpeg: a violet FIELD whose edge is torn into long
tapering blades, dark slivers laid inside the field, black notches cut back into
it.  Fabric folds and photographic shading in the reference are deliberately not
reproduced - only printed artwork is.
"""
import math
from render import RICH_BLACK, PURPLE, PURPLE_DK, WHITE, fill, fill_pts, stroke
import shards as SH
import textcurves as TC
import geom as G

FCX, BCX, MIRROR = G.FCX, G.BCX, G.MIRROR


# ------------------------------------------------------------- transforms ---
def mx(p, axis):
    return (2 * axis - p[0], p[1])


def mirror_pts(pts, axis):
    return [mx(p, axis) for p in pts]


def mirror_subs(subs, axis):
    out = []
    for s in subs:
        n = []
        for seg in s:
            if seg[0] == 'Z':
                n.append(seg)
            else:
                v = list(seg[1:])
                for i in range(0, len(v), 2):
                    v[i] = 2 * axis - v[i]
                n.append((seg[0], *v))
        out.append(n)
    return out


def smooth(pts, close=False):
    if len(pts) < 3:
        return [[('M', *pts[0])] + [('L', *p) for p in pts[1:]]]
    seq = [('M', *pts[0])]
    ext = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        seq.append(('C', c1[0], c1[1], c2[0], c2[1], p2[0], p2[1]))
    if close:
        seq.append(('Z',))
    return [seq]


def region_smooth(inner, far):
    sub = smooth(list(inner))[0]
    for p in far:
        sub.append(('L', *p))
    sub.append(('Z',))
    return [sub]


def _band(spine, far_x, top_y, bot_y):
    return region_smooth(spine, [(far_x, bot_y), (far_x, top_y)])


def along(pts, t):
    segs, total = [], 0.0
    for i in range(len(pts) - 1):
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        segs.append(d)
        total += d
    target = max(0.0, min(1.0, t)) * total
    acc = 0.0
    for i, d in enumerate(segs):
        if acc + d >= target or i == len(segs) - 1:
            u = (target - acc) / d if d else 0.0
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u,
                    pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u)
        acc += d
    return pts[-1]


def edge_blades(boundary, specs, inset=0.0):
    out = []
    for (t, ang, length, hw, skew) in specs:
        x, y = along(boundary, t)
        a = math.radians(ang)
        out += SH.blade(x - math.cos(a) * inset, y - math.sin(a) * inset,
                        ang, length, hw, skew)
    return out


def bigrect(c, x0, y0, x1, y1, col):
    fill(c, [[('M', x0, y0), ('L', x1, y0), ('L', x1, y1), ('L', x0, y1), ('Z',)]], col)


# ============================================================ FRONT VIEW ===
# WEARER'S RIGHT (front viewer-left): the violet is only a band along the
# raglan seam, widening into the torso side panel below the armpit.  Its outer
# edge is the seam itself, so the black sleeve stays black right up to it.
FRONT_OUTER_WR = list(G.FRONT_OUTER_R)
FRONT_PIPE_WR = list(G.FRONT_PIPE_WR)

# WEARER'S LEFT (front viewer-right): shoulder, sleeve and chest wedge are all
# violet - one region bounded by the torn chest edge, then the side piping.
FRONT_EDGE_WL = [(490.0, 148.0), (479.0, 166.0), (470.0, 184.0), (464.0, 200.0),
                 (462.0, 214.0), (472.0, 228.0), (489.0, 236.0), (501.0, 248.0),
                 (505.0, 262.0)] + [p for p in G.FRONT_PIPE_R if p[1] >= 288]

FRONT_LEGBAND_L = list(G.FRONT_LEGBAND_L)
FRONT_LEGBAND_R = list(G.FRONT_LEGBAND_R)
FRONT_LEGCHEV_L = list(G.FRONT_LEGCHEV_L)
FRONT_LEGCHEV_R = list(G.FRONT_LEGCHEV_R)

# ---- chest burst -----------------------------------------------------------
CHEST_FIELD = FRONT_EDGE_WL[:7]          # the torn part of that boundary
CHEST_SPIKES = [
    (0.05, 158, 52, 5.0, 0.30), (0.12, 152, 68, 5.6, 0.28), (0.19, 162, 40, 3.8, 0.34),
    (0.26, 149, 76, 5.2, 0.27), (0.33, 156, 56, 4.2, 0.30), (0.40, 146, 64, 4.4, 0.28),
    (0.47, 153, 44, 3.2, 0.32), (0.54, 143, 52, 3.4, 0.28), (0.61, 150, 38, 2.8, 0.30),
    (0.68, 140, 46, 3.0, 0.28), (0.75, 147, 34, 2.6, 0.30), (0.82, 137, 38, 2.4, 0.32),
    (0.09, 166, 32, 2.5, 0.36), (0.23, 167, 30, 2.2, 0.38), (0.37, 141, 42, 2.5, 0.30),
    (0.58, 158, 28, 2.0, 0.32), (0.89, 133, 30, 2.0, 0.32),
]
CHEST_NOTCH = [
    (0.11, 338, 30, 3.6, 0.30), (0.25, 330, 38, 4.0, 0.28), (0.39, 342, 26, 3.0, 0.32),
    (0.53, 320, 32, 3.2, 0.30), (0.67, 306, 28, 2.6, 0.30),
]
CHEST_SLIVER = [
    (0.07, 153, 44, 2.0, 0.30), (0.18, 148, 54, 2.1, 0.28), (0.29, 156, 38, 1.7, 0.30),
    (0.40, 145, 48, 1.8, 0.28), (0.51, 151, 36, 1.6, 0.30), (0.62, 142, 42, 1.6, 0.30),
    (0.73, 149, 32, 1.4, 0.30), (0.13, 161, 30, 1.4, 0.34), (0.35, 143, 36, 1.5, 0.30),
]
# White blade across the chest.  Explicit outline: a long chisel with a step
# in its lower edge, exactly as in DIMA.jpeg, plus a separate tail sliver.
CHEST_BLADE = [(420.0, 268.0),                       # lower-left point
               (450.0, 248.0), (478.0, 230.0), (506.0, 212.0), (527.0, 197.0),
               (536.0, 191.0),                       # upper-right chisel tip
               (524.0, 208.0), (509.0, 218.0), (496.0, 226.0),
               (488.0, 230.0), (482.0, 241.0),       # the step
               (462.0, 253.0), (438.0, 267.0)]
CHEST_TAIL = [(400.0, 284.0), (416.0, 274.0), (428.0, 267.0),
              (423.0, 275.0), (411.0, 282.0)]


def band_between(outer, inner):
    """Closed band between two boundary polylines."""
    sub = smooth(list(outer))[0]
    for p in reversed(G.densify(list(inner))):
        sub.append(('L', *p))
    sub.append(('Z',))
    return [sub]


def front_purple(c):
    """Violet fields of the front view."""
    # wearer's LEFT: shoulder + chest wedge + side panel, all outboard
    fill(c, _band(FRONT_EDGE_WL, 640.0, 118.0, 356.0), PURPLE)
    # wearer's RIGHT: narrow band along the raglan seam / side seam
    fill(c, band_between(FRONT_OUTER_WR, FRONT_PIPE_WR), PURPLE)
    # legs
    fill(c, _band(FRONT_LEGBAND_L, 250.0, 344.0, 764.0), PURPLE)
    fill(c, _band(FRONT_LEGBAND_R, 640.0, 344.0, 764.0), PURPLE)


def front_leg_chevron(c):
    for ch, side in ((FRONT_LEGCHEV_L, -1), (FRONT_LEGCHEV_R, 1)):
        n = len(ch)
        w = [min(3.2, 1.4 + 2.2 * math.sin(math.pi * i / (n - 1)) ** 0.6) for i in range(n)]
        fill(c, SH.taper_band(ch, w, w), RICH_BLACK)
        rib = [(x + side * 5.5, y) for x, y in ch]
        w2 = [v * 0.40 for v in w]
        fill(c, SH.taper_band(rib, w2, w2), PURPLE_DK)


def front_chest_graphic(c):
    fill(c, region_smooth(CHEST_FIELD, [(560.0, 300.0), (560.0, 140.0)]), PURPLE)
    fill(c, edge_blades(CHEST_FIELD, CHEST_SPIKES, inset=2.0), PURPLE)
    fill(c, edge_blades(CHEST_FIELD, CHEST_NOTCH, inset=-18.0), RICH_BLACK)
    fill(c, edge_blades(CHEST_FIELD, CHEST_SLIVER, inset=-12.0), PURPLE_DK)
    fill(c, [[('M', *CHEST_BLADE[0])] + [('L', *p) for p in CHEST_BLADE[1:]] + [('Z',)]], WHITE)
    fill(c, [[('M', *CHEST_TAIL[0])] + [('L', *p) for p in CHEST_TAIL[1:]] + [('Z',)]], WHITE)


def front_piping(c):
    stroke(c, smooth([p for p in FRONT_PIPE_WR if p[1] >= 172]), WHITE, 1.9, cap=1, join=1)
    stroke(c, smooth([p for p in FRONT_EDGE_WL if p[1] >= 258]), WHITE, 1.9, cap=1, join=1)
    for leg in (FRONT_LEGBAND_L, FRONT_LEGBAND_R):
        stroke(c, smooth(leg[:3]), WHITE, 1.7, cap=1, join=1)


# ============================================================= BACK VIEW ===
BACK_OUTER_WR = list(G.BACK_OUTER_R)
BACK_PIPE_WR = list(G.BACK_PIPE_WR)
BACK_EDGE_WL = list(G.BACK_FIELD_EDGE)
BACK_LEGBAND_L = list(G.BACK_LEGBAND_L)
BACK_LEGBAND_R = list(G.BACK_LEGBAND_R)

BACK_FIELD = BACK_EDGE_WL[:9]
BACK_SPIKES = [
    (0.05, 27, 92, 9.5, 0.28), (0.12, 32, 112, 10.5, 0.26), (0.19, 24, 76, 7.0, 0.32),
    (0.26, 29, 120, 9.5, 0.26), (0.33, 35, 98, 8.0, 0.28), (0.40, 26, 86, 6.8, 0.30),
    (0.47, 31, 100, 7.0, 0.27), (0.54, 36, 80, 5.8, 0.28), (0.61, 27, 70, 4.8, 0.29),
    (0.68, 33, 58, 4.0, 0.28), (0.75, 25, 50, 3.4, 0.31), (0.82, 30, 42, 2.8, 0.29),
    (0.89, 34, 34, 2.3, 0.29), (0.09, 38, 68, 5.4, 0.30), (0.44, 22, 58, 4.6, 0.34),
    (0.65, 38, 46, 3.4, 0.28), (0.95, 28, 28, 2.0, 0.30),
]
BACK_NOTCH = [
    (0.10, 205, 44, 3.4, 0.28), (0.18, 210, 56, 3.9, 0.26), (0.26, 202, 48, 3.4, 0.30),
    (0.34, 212, 58, 4.1, 0.27), (0.42, 206, 50, 3.6, 0.29), (0.50, 209, 60, 4.1, 0.28),
    (0.58, 203, 48, 3.4, 0.30), (0.66, 208, 52, 3.6, 0.28), (0.74, 212, 44, 3.1, 0.29),
    (0.82, 205, 38, 2.8, 0.30), (0.90, 209, 32, 2.4, 0.28),
]
BACK_SLIVER = [
    (0.07, 28, 88, 3.2, 0.28), (0.20, 33, 104, 3.4, 0.27), (0.33, 25, 80, 2.7, 0.30),
    (0.46, 31, 96, 2.9, 0.28), (0.59, 35, 82, 2.6, 0.28), (0.72, 26, 70, 2.2, 0.30),
    (0.25, 37, 68, 2.4, 0.28), (0.52, 23, 60, 2.1, 0.32), (0.85, 30, 50, 1.8, 0.30),
]

PLATE = (722.0, 198.0, 826.0, 229.0)
PLATE_TEXT = 'D. FEDOROV'


def back_purple(c):
    fill(c, _band(BACK_EDGE_WL, 580.0, 118.0, 352.0), PURPLE)
    fill(c, band_between(BACK_OUTER_WR, BACK_PIPE_WR), PURPLE)
    fill(c, _band(BACK_LEGBAND_L, 580.0, 340.0, 764.0), PURPLE)
    fill(c, _band(BACK_LEGBAND_R, 955.0, 340.0, 764.0), PURPLE)


def back_burst(c):
    fill(c, region_smooth(BACK_FIELD, [(640.0, 350.0), (640.0, 120.0)]), PURPLE)
    fill(c, edge_blades(BACK_FIELD, BACK_SPIKES, inset=3.0), PURPLE)
    fill(c, edge_blades(BACK_FIELD, BACK_NOTCH, inset=-34.0), RICH_BLACK)
    fill(c, edge_blades(BACK_FIELD, BACK_SLIVER, inset=-18.0), PURPLE_DK)


def back_plate(c):
    x0, y0, x1, y1 = PLATE
    ch = 5.0
    fill_pts(c, [(x0 + ch, y0), (x1, y0), (x1 - ch, y1), (x0, y1)], RICH_BLACK)
    cap = (y1 - y0) * 0.47
    w = TC.advance(PLATE_TEXT, cap, tracking=0.010)
    tx = (x0 + x1) / 2 - w / 2 + 1.0
    ty = (y0 + y1) / 2 + cap * 0.5
    fill(c, TC.outlines(PLATE_TEXT, cap, tx, ty, tracking=0.010, slant=5.0), WHITE, eo=True)


def back_piping(c):
    stroke(c, smooth([p for p in BACK_PIPE_WR if p[1] >= 172]), WHITE, 1.9, cap=1, join=1)
    stroke(c, smooth([p for p in BACK_EDGE_WL if p[1] >= 250]), WHITE, 1.9, cap=1, join=1)
    for leg in (BACK_LEGBAND_L, BACK_LEGBAND_R):
        stroke(c, smooth(leg[:3]), WHITE, 1.7, cap=1, join=1)


def back_leg_spike(c):
    for sgn, bx in ((1, 702.0), (-1, 2 * BCX - 702.0)):
        ang = -66.0 if sgn > 0 else -114.0
        fill(c, SH.blade(bx, 704.0, ang, 58, 3.0, 0.30), PURPLE_DK)
        fill(c, SH.blade(bx - 3 * sgn, 708.0, ang + 7 * sgn, 38, 1.6, 0.30), PURPLE)


# =============================================================== SLEEVES ===
def cuff_burst(c, ox, oy, flip, colour):
    """Blade cluster on the forearm above the cuff - each sleeve carries one in
    the opposite colour to the sleeve itself (DIMA.jpeg)."""
    specs = [(-44, 84, 6.0, 0, 0.28), (-36, 68, 4.6, 10, 0.30), (-52, 74, 4.8, 5, 0.28),
             (-30, 54, 3.4, 20, 0.32), (-60, 58, 3.4, 10, 0.28), (-46, 100, 5.2, 5, 0.27),
             (-40, 46, 2.6, 28, 0.30), (-56, 42, 2.4, 22, 0.30), (-48, 34, 2.1, 32, 0.30),
             (-26, 38, 2.2, 30, 0.32), (-64, 36, 2.0, 15, 0.30)]
    if flip:
        specs = [(-180 - a, L, hw, d, sk) for (a, L, hw, d, sk) in specs]
    fill(c, SH.fan(ox, oy, specs), colour)


def cuff_slivers(c, ox, oy, flip, colour):
    specs = [(-42, 44, 1.9, 4, 0.28), (-50, 36, 1.6, 10, 0.28), (-34, 32, 1.4, 14, 0.30)]
    if flip:
        specs = [(-180 - a, L, hw, d, sk) for (a, L, hw, d, sk) in specs]
    fill(c, SH.fan(ox, oy, specs), colour)


# ============================================================= SIDE VIEWS ===
SIDE_TORSO_FRONT = list(G.SIDE_TORSO_FRONT)
SIDE_TORSO_BACK = list(G.SIDE_TORSO_BACK)
SIDE_LEG_FRONT = list(G.SIDE_LEG_FRONT)
SIDE_LEG_BACK = list(G.SIDE_LEG_BACK)
SIDE_LEG_CHEV = list(G.SIDE_LEG_CHEV)
SIDE_YOKE_L = [(224.0, 150.0), (208.0, 162.0), (192.0, 180.0), (180.0, 204.0),
               (173.0, 230.0), (170.0, 256.0), (169.0, 280.0)]
