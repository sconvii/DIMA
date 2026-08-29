"""Generators for the shard / lightning-blade motif used all over the suit."""
import math


def blade(x, y, ang, length, half_w, skew=0.35, bow=0.10):
    """One tapering sliver: base centred on (x, y), sharp tip `length` away.

    `ang` is degrees, measured clockwise from +x in the y-DOWN design space.
    `skew` biases the base towards one flank so the blade reads as torn rather
    than as a symmetric triangle; `bow` curves the long flanks slightly.
    """
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux                                   # unit normal
    tipx, tipy = x + ux * length, y + uy * length
    b1 = (x + px * half_w * (1 + skew), y + py * half_w * (1 + skew))
    b2 = (x - px * half_w * (1 - skew), y - py * half_w * (1 - skew))
    # control points bow the flanks outwards a touch
    m1 = (x + ux * length * 0.45 + px * half_w * (1 + bow) * 0.75,
          y + uy * length * 0.45 + py * half_w * (1 + bow) * 0.75)
    m2 = (x + ux * length * 0.45 - px * half_w * (1 - bow) * 0.55,
          y + uy * length * 0.45 - py * half_w * (1 - bow) * 0.55)
    return [[('M', b1[0], b1[1]),
             ('C', m1[0], m1[1], m1[0], m1[1], tipx, tipy),
             ('C', m2[0], m2[1], m2[0], m2[1], b2[0], b2[1]),
             ('Z',)]]


def fan(ox, oy, specs):
    """A burst of blades.  `specs` = [(ang, length, half_w, dist, skew), ...]
    where `dist` slides the blade base along its own direction from the origin."""
    out = []
    for sp in specs:
        ang, length, hw, dist = sp[0], sp[1], sp[2], sp[3]
        skew = sp[4] if len(sp) > 4 else 0.35
        a = math.radians(ang)
        bx, by = ox + math.cos(a) * dist, oy + math.sin(a) * dist
        out += blade(bx, by, ang, length, hw, skew)
    return out


def slash(pts_w):
    """Long lightning slash from a centreline with per-node half widths.

    `pts_w` = [(x, y, half_width), ...] along the spine; returns one closed
    subpath tapering to points at both ends.
    """
    left, right = [], []
    n = len(pts_w)
    for i, (x, y, hw) in enumerate(pts_w):
        if i == 0:
            dx, dy = pts_w[1][0] - x, pts_w[1][1] - y
        elif i == n - 1:
            dx, dy = x - pts_w[-2][0], y - pts_w[-2][1]
        else:
            dx, dy = pts_w[i + 1][0] - pts_w[i - 1][0], pts_w[i + 1][1] - pts_w[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        left.append((x + px * hw, y + py * hw))
        right.append((x - px * hw, y - py * hw))
    ring = left + right[::-1]
    sub = [('M', *ring[0])] + [('L', *p) for p in ring[1:]] + [('Z',)]
    return [sub]


def taper_band(spine, widths_out, widths_in=None):
    """Band following `spine` [(x,y)...] with outboard/inboard half widths."""
    if widths_in is None:
        widths_in = widths_out
    a, b = [], []
    n = len(spine)
    for i, (x, y) in enumerate(spine):
        if i == 0:
            dx, dy = spine[1][0] - x, spine[1][1] - y
        elif i == n - 1:
            dx, dy = x - spine[-2][0], y - spine[-2][1]
        else:
            dx, dy = spine[i + 1][0] - spine[i - 1][0], spine[i + 1][1] - spine[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        a.append((x + px * widths_out[i], y + py * widths_out[i]))
        b.append((x - px * widths_in[i], y - py * widths_in[i]))
    ring = a + b[::-1]
    return [[('M', *ring[0])] + [('L', *p) for p in ring[1:]] + [('Z',)]]


def streak(x, y, ang, length, half_w, head=0.30, tail=0.10, bow=0.0):
    """A long, thin slash mark - the motif actually used on DIMA.jpeg.

    Much more elongated than `blade`: the widest point sits at `head` along the
    length and both ends run out to points, so the mark reads as a torn streak
    rather than a triangular wedge.  `bow` bends it slightly across its length.
    """
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux

    def at(t, w):
        b = bow * math.sin(math.pi * t) * half_w
        return (x + ux * length * t + px * (w + b),
                y + uy * length * t + py * (w + b))

    p0 = at(0.0, 0.0)
    pa = at(head, half_w)
    pb = at(1.0 - tail, half_w * 0.30)
    p1 = at(1.0, 0.0)
    pc = at(1.0 - tail, -half_w * 0.22)
    pd = at(head, -half_w * 0.55)
    return [[('M', p0[0], p0[1]),
             ('C', *at(head * 0.45, half_w * 0.72), *at(head * 0.80, half_w), *pa),
             ('C', *at(head + (1 - tail - head) * 0.5, half_w * 0.66), *pb, *p1),
             ('C', *pc, *at(head + (1 - head) * 0.4, -half_w * 0.42), *pd),
             ('C', *at(head * 0.60, -half_w * 0.40), *at(head * 0.25, -half_w * 0.16), *p0),
             ('Z',)]]


def streak_field(specs):
    """Streaks from explicit (x, y, angle, length, half width[, bow]) tuples."""
    out = []
    for sp in specs:
        x, y, ang, L, hw = sp[:5]
        bow = sp[5] if len(sp) > 5 else 0.0
        out += streak(x, y, ang, L, hw, bow=bow)
    return out


def streak_band(ox, oy, dx, dy, n, ang, specs):
    """`n` streaks stepped along (dx, dy); `specs` cycles through
    (offset across the step, angle jitter, length, half width)."""
    out = []
    for i in range(n):
        off, dang, length, hw = specs[i % len(specs)]
        a = math.radians(ang + dang)
        bx = ox + dx * i - math.sin(a) * off
        by = oy + dy * i + math.cos(a) * off
        out += streak(bx, by, ang + dang, length, hw)
    return out
