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


def _band_sharp(spine, far_x, top_y, bot_y):
    """Like `_band` but with straight segments, so corners stay corners."""
    ring = list(spine) + [(far_x, bot_y), (far_x, top_y)]
    return [[('M', *ring[0])] + [('L', *p) for p in ring[1:]] + [('Z',)]]


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
FRONT_EDGE_WL = [(492.0, 146.0), (480.0, 164.0), (470.0, 182.0), (463.0, 198.0),
                 (460.0, 214.0), (466.0, 230.0), (480.0, 240.0), (496.0, 250.0),
                 (504.0, 264.0)] + [p for p in G.FRONT_PIPE_R if p[1] >= 288]

# The outer-leg band bends through a sharp chevron at the knee (DIMA.jpeg).
# Drawn with straight segments so the corner stays angular, not rounded.
FRONT_LEGBAND_L = list(G.FRONT_CHEV_L)
FRONT_LEGBAND_R = list(G.FRONT_CHEV_R)
FRONT_LEGPIN_L = list(G.FRONT_CHEV_PIN_L)
FRONT_LEGPIN_R = list(G.FRONT_CHEV_PIN_R)
FRONT_LEGW_L = list(G.FRONT_CHEV_W_L)
FRONT_LEGW_R = list(G.FRONT_CHEV_W_R)

# ---- chest burst -----------------------------------------------------------
CHEST_FIELD = FRONT_EDGE_WL[:7]          # the torn part of that boundary
# The chest marks in DIMA.jpeg are long, thin slash streaks that run well past
# the centre zip - not short triangular wedges.  Explicit placement, in two
# clusters: above the white blade and below it.
# (x, y, angle, length, half width, bow)
CHEST_STREAKS = [
    # Upper cluster.  Heads sit on the field edge, tips stop around the zip -
    # in DIMA.jpeg the marks reach the centre seam, they do not cross the chest.
    (498, 148, 162, 58, 4.6, 0.08), (492, 154, 158, 68, 5.2, 0.07),
    (488, 160, 166, 50, 4.0, 0.09), (484, 166, 160, 76, 5.4, 0.06),
    (480, 172, 155, 64, 4.6, 0.07), (477, 178, 164, 54, 4.0, 0.08),
    (474, 184, 159, 80, 5.2, 0.06), (471, 190, 153, 68, 4.4, 0.07),
    (469, 196, 162, 58, 4.0, 0.08), (467, 202, 157, 84, 5.0, 0.06),
    (466, 208, 151, 70, 4.2, 0.07), (465, 214, 160, 60, 3.8, 0.08),
    (466, 220, 155, 76, 4.4, 0.06), (468, 226, 150, 62, 3.6, 0.07),
    (472, 232, 158, 52, 3.2, 0.08),
    (494, 151, 169, 34, 2.4, 0.10), (486, 163, 152, 42, 2.6, 0.09),
    (478, 175, 168, 32, 2.2, 0.10), (472, 187, 149, 44, 2.6, 0.09),
    (467, 199, 167, 30, 2.0, 0.10), (466, 211, 148, 42, 2.4, 0.09),
    (469, 223, 166, 28, 1.9, 0.10),
    # Lower cluster: sparse, hugging the blade, as in the reference
    (500, 252, 157, 56, 3.6, 0.07), (497, 262, 163, 44, 3.0, 0.08),
    (496, 272, 152, 52, 3.0, 0.07), (500, 282, 159, 40, 2.6, 0.08),
    (505, 292, 154, 44, 2.4, 0.07),
    (498, 267, 168, 28, 1.8, 0.09), (503, 287, 149, 34, 1.8, 0.08),
]
CHEST_NOTCH = [     # a few thin black cut-ins, so the violet mass stays solid
    (0.16, 334, 40, 2.0, 0.30), (0.38, 340, 34, 1.8, 0.30), (0.60, 328, 30, 1.7, 0.30),
]
CHEST_DARK = [
    (494, 152, 160, 50, 2.2, 0.08), (486, 164, 156, 58, 2.4, 0.07),
    (479, 176, 163, 44, 1.9, 0.09), (473, 188, 157, 54, 2.1, 0.07),
    (469, 200, 152, 50, 2.0, 0.08), (466, 212, 161, 44, 1.8, 0.08),
    (467, 224, 154, 46, 1.9, 0.07),
    (498, 258, 158, 42, 2.0, 0.08), (497, 276, 153, 38, 1.8, 0.07),
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
    # legs - straight segments keep the knee corner sharp
    fill(c, _band_sharp(FRONT_LEGBAND_L, 250.0, 344.0, 764.0), PURPLE)
    fill(c, _band_sharp(FRONT_LEGBAND_R, 640.0, 344.0, 764.0), PURPLE)


def front_leg_chevron(c):
    """Black pinstripe inside the violet band, following the same chevron.

    Width is a fraction of the band, not a fixed weight: on DIMA.jpeg the line
    measures about 7 % of the band, so it must thin out as the band does.
    """
    for pin, bw, side in ((FRONT_LEGPIN_L, FRONT_LEGW_L, -1),
                          (FRONT_LEGPIN_R, FRONT_LEGW_R, 1)):
        w = [max(0.45, min(1.5, 0.037 * v)) for v in bw]
        fill(c, SH.taper_band(pin, w, w), RICH_BLACK)
        # a much fainter violet-shadow line just inside the band's inner edge
        rib = [(x - side * max(2.0, 0.13 * v), y) for (x, y), v in zip(pin, bw)]
        w2 = [max(0.3, v * 0.55) for v in w]
        fill(c, SH.taper_band(rib, w2, w2), PURPLE_DK)


def front_chest_graphic(c):
    fill(c, region_smooth(CHEST_FIELD, [(560.0, 300.0), (560.0, 140.0)]), PURPLE)
    fill(c, SH.streak_field(CHEST_STREAKS), PURPLE)
    fill(c, SH.streak_field(CHEST_DARK), PURPLE_DK)
    fill(c, [[('M', *CHEST_BLADE[0])] + [('L', *p) for p in CHEST_BLADE[1:]] + [('Z',)]], WHITE)
    fill(c, [[('M', *CHEST_TAIL[0])] + [('L', *p) for p in CHEST_TAIL[1:]] + [('Z',)]], WHITE)


def front_piping(c):
    stroke(c, smooth([p for p in FRONT_PIPE_WR if p[1] >= 172]), WHITE, 1.9, cap=1, join=1)
    stroke(c, smooth([p for p in FRONT_EDGE_WL if p[1] >= 258]), WHITE, 1.9, cap=1, join=1)
    for leg in (FRONT_LEGBAND_L, FRONT_LEGBAND_R):
        stroke(c, [[('M', *leg[0])] + [('L', *p) for p in leg[1:3]]], WHITE, 1.7, cap=1, join=1)


# ============================================================= BACK VIEW ===
BACK_OUTER_WR = list(G.BACK_OUTER_R)
BACK_PIPE_WR = list(G.BACK_PIPE_WR)
BACK_EDGE_WL = list(G.BACK_FIELD_EDGE)
BACK_LEGBAND_L = list(G.BACK_LEGBAND_L)
BACK_LEGBAND_R = list(G.BACK_LEGBAND_R)

BACK_FIELD = BACK_EDGE_WL[:9]
# On the back the marks are long, near-parallel streaks fanning down-right in
# two clusters (above and below the name plate), with black left showing on the
# right-hand side of the panel.  (x, y, angle, length, half width, bow)
BACK_STREAKS = [
    # Upper cluster, above the plate - shorter, so black stays on the right
    (776, 136, 28, 74, 4.6, 0.07), (768, 146, 34, 88, 5.2, 0.06),
    (761, 156, 23, 64, 3.8, 0.08), (754, 166, 30, 96, 5.4, 0.06),
    (747, 176, 37, 78, 4.4, 0.07), (740, 186, 26, 70, 3.8, 0.08),
    (766, 141, 41, 58, 3.2, 0.08), (751, 161, 19, 62, 3.2, 0.09),
    # a few wider teeth so the field edge reads as torn, not as a clean diagonal
    (772, 132, 33, 62, 8.0, 0.05), (757, 152, 26, 56, 7.0, 0.05),
    (744, 170, 31, 50, 6.0, 0.06),
    (743, 181, 45, 54, 2.8, 0.08), (737, 191, 32, 82, 4.0, 0.07),
    # Lower cluster, below the plate - the longest marks on the garment
    (728, 238, 29, 154, 6.6, 0.05), (722, 248, 35, 138, 5.8, 0.06),
    (717, 258, 24, 168, 7.0, 0.05), (712, 268, 31, 148, 6.0, 0.05),
    (708, 278, 38, 126, 5.2, 0.06), (704, 288, 26, 142, 5.6, 0.05),
    (700, 298, 33, 118, 4.6, 0.06), (697, 308, 28, 104, 4.0, 0.06),
    (695, 318, 35, 90, 3.4, 0.07), (693, 328, 30, 76, 2.9, 0.07),
    (725, 244, 43, 100, 4.0, 0.07), (714, 263, 19, 116, 4.2, 0.08),
    (706, 283, 44, 94, 3.6, 0.07), (698, 303, 21, 86, 3.0, 0.08),
]
BACK_NOTCH = [      # thin black cut-ins along the field edge
    (0.10, 205, 46, 2.4, 0.28), (0.19, 210, 58, 2.7, 0.26), (0.28, 202, 50, 2.3, 0.30),
    (0.37, 212, 60, 2.7, 0.27), (0.46, 206, 52, 2.4, 0.29), (0.55, 209, 62, 2.7, 0.28),
    (0.64, 203, 50, 2.3, 0.30), (0.73, 208, 54, 2.4, 0.28), (0.82, 212, 44, 2.0, 0.29),
    (0.91, 205, 36, 1.8, 0.30),
]
BACK_DARK = [
    (770, 142, 30, 64, 2.4, 0.07), (757, 160, 25, 70, 2.5, 0.07),
    (746, 174, 35, 58, 2.1, 0.08), (738, 186, 29, 66, 2.3, 0.07),
    (724, 244, 31, 118, 3.0, 0.06), (716, 262, 26, 130, 3.2, 0.05),
    (709, 278, 35, 106, 2.7, 0.06), (703, 294, 29, 110, 2.8, 0.06),
    (697, 312, 32, 82, 2.2, 0.07), (694, 326, 27, 68, 2.0, 0.07),
]

PLATE = (706.0, 196.0, 838.0, 230.0)
PLATE_TEXT = 'D. FEDOROV'


def back_purple(c):
    fill(c, _band(BACK_EDGE_WL, 580.0, 118.0, 352.0), PURPLE)
    fill(c, band_between(BACK_OUTER_WR, BACK_PIPE_WR), PURPLE)
    fill(c, _band(BACK_LEGBAND_L, 580.0, 340.0, 764.0), PURPLE)
    fill(c, _band(BACK_LEGBAND_R, 955.0, 340.0, 764.0), PURPLE)


def back_burst(c):
    fill(c, region_smooth(BACK_FIELD, [(640.0, 350.0), (640.0, 120.0)]), PURPLE)
    fill(c, SH.streak_field(BACK_STREAKS), PURPLE)
    fill(c, edge_blades(BACK_FIELD, BACK_NOTCH, inset=-34.0), RICH_BLACK)
    fill(c, SH.streak_field(BACK_DARK), PURPLE_DK)


def back_plate(c):
    x0, y0, x1, y1 = PLATE
    fill_pts(c, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], RICH_BLACK)
    cap = (y1 - y0) * 0.60
    w = TC.advance(PLATE_TEXT, cap, tracking=0.010)
    tx = (x0 + x1) / 2 - w / 2 + 1.0
    ty = (y0 + y1) / 2 + cap * 0.5
    fill(c, TC.outlines(PLATE_TEXT, cap, tx, ty, tracking=0.010, slant=5.0), WHITE, eo=True)


def back_piping(c):
    stroke(c, smooth([p for p in BACK_PIPE_WR if p[1] >= 172]), WHITE, 1.9, cap=1, join=1)
    stroke(c, smooth([p for p in BACK_EDGE_WL if p[1] >= 250]), WHITE, 1.9, cap=1, join=1)
    for leg in (BACK_LEGBAND_L, BACK_LEGBAND_R):
        stroke(c, [[('M', *leg[0])] + [('L', *p) for p in leg[1:3]]], WHITE, 1.7, cap=1, join=1)


def back_leg_spike(c):
    for sgn, bx in ((1, 702.0), (-1, 2 * BCX - 702.0)):
        ang = -66.0 if sgn > 0 else -114.0
        fill(c, SH.blade(bx, 704.0, ang, 58, 3.0, 0.30), PURPLE_DK)
        fill(c, SH.blade(bx - 3 * sgn, 708.0, ang + 7 * sgn, 38, 1.6, 0.30), PURPLE)


# =============================================================== SLEEVES ===
def forearm_streaks(c, x0, y0, flip, colour, n=21, dx=1.4, dy=3.7,
                    base_len=72.0, base_hw=1.9, ang=-46.0):
    """DIMA.jpeg carries a BAND of long, thin diagonal streaks across the lower
    forearm of both sleeves.  Each streak crosses most of the sleeve width and
    the whole stack steps down towards the cuff, so the band reads as a
    parallelogram, not as a fan bunched at one edge."""
    import shards as _SH
    jit = [(0.0, 0), (0.40, -4), (-0.32, 3), (0.18, -2), (-0.16, 5), (0.48, 2),
           (-0.44, -3), (0.22, 4), (-0.22, -2), (0.42, 3), (-0.36, -5),
           (0.12, 1), (-0.12, 4), (0.34, -3), (-0.28, 2), (0.06, -1),
           (0.26, 4), (-0.38, -2), (0.14, 3), (-0.18, -4), (0.36, 1)]
    specs = []
    for i in range(n):
        f, dang = jit[i % len(jit)]
        env = math.sin(math.pi * (i + 0.6) / (n + 0.2))
        L = base_len * (0.70 + 0.45 * env) + f * 22
        hw = base_hw * (0.55 + 0.6 * env)
        a = ang + dang
        bx, by = x0 + dx * i + f * 4.0, y0 + dy * i
        if flip:
            a = -180 - a
            bx = -bx
        specs.append((bx if not flip else -bx, by, a, L, hw, 0.10))
    if flip:
        specs = [(2 * x0 - x, y, a, L, hw, b) for (x, y, a, L, hw, b) in specs]
    fill(c, _SH.streak_field(specs), colour)


def cuff_burst(c, ox, oy, flip, colour):
    forearm_streaks(c, ox, oy, flip, colour)


def side_forearm(c, mirror, colour):
    """Forearm streak band for the side views.  In the sketch the visible
    forearm is part of the body profile panel, not the sleeve panel, so the
    band is painted with the body and clipped by it."""
    ox = (2 * MIRROR - 196.0) if mirror else 196.0
    forearm_streaks(c, ox, 330.0, mirror, colour, n=13, dx=1.6, dy=4.2,
                    base_len=58.0, base_hw=1.7)


def cuff_slivers(c, ox, oy, flip, colour):
    """Same band, dark tone and sparser - the violet sleeve of the reference."""
    forearm_streaks(c, ox, oy, flip, colour, n=13, dx=2.0, dy=5.6,
                    base_len=66.0, base_hw=1.7)


# ============================================================= SIDE VIEWS ===
SIDE_TORSO_FRONT = list(G.SIDE_TORSO_FRONT)
SIDE_TORSO_BACK = list(G.SIDE_TORSO_BACK)
SIDE_LEG_FRONT = list(G.SIDE_LEG_FRONT)
SIDE_LEG_BACK = list(G.SIDE_LEG_BACK)
SIDE_LEG_CHEV = list(G.SIDE_LEG_CHEV)
SIDE_YOKE_L = [(224.0, 150.0), (208.0, 162.0), (192.0, 180.0), (180.0, 204.0),
               (173.0, 230.0), (170.0, 256.0), (169.0, 280.0)]
