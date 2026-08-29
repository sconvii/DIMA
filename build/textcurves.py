"""Convert a string to explicit vector outlines (design space, y-DOWN).

The result carries no font reference at all, so the finished PDF cannot suffer
from a missing or unembedded font.
"""
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

FONT = '/mnt/skills/examples/canvas-design/canvas-fonts/BigShoulders-Bold.ttf'
# Cyrillic-capable faces for the technical annotations
UI = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
UI_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def _cap(f, upm):
    """Cap height, measured from the 'H' outline when OS/2 does not carry it."""
    v = getattr(f['OS/2'], 'sCapHeight', None)
    if v:
        return v
    try:
        return f['glyf']['H'].yMax
    except Exception:
        return upm * 0.7


class _Pen(BasePen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.subs, self.cur = [], None

    def _moveTo(self, p):
        if self.cur:
            self.subs.append(self.cur)
        self.cur = [('M', p[0], p[1])]

    def _lineTo(self, p):
        self.cur.append(('L', p[0], p[1]))

    def _curveToOne(self, c1, c2, p):
        self.cur.append(('C', c1[0], c1[1], c2[0], c2[1], p[0], p[1]))

    def _closePath(self):
        if self.cur:
            self.cur.append(('Z',))
            self.subs.append(self.cur)
            self.cur = None

    def done(self):
        if self.cur:
            self.cur.append(('Z',))
            self.subs.append(self.cur)
            self.cur = None
        return self.subs


def outlines(text, size, x, y, tracking=0.0, slant=0.0, path=FONT, y_up=False):
    """Outlines of `text` with cap-height `size`, baseline-left at (x, y).

    `slant` is the oblique in degrees (positive leans right); `tracking` adds
    letter spacing as a fraction of `size`.  Returns subpaths with y increasing
    DOWNWARD (the sketch's design space); pass `y_up=True` when drawing onto an
    un-flipped PDF canvas, where y increases upward.
    """
    f = TTFont(path)
    upm = f['head'].unitsPerEm
    cap = _cap(f, upm)
    s = size / cap
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    hmtx = f['hmtx']
    import math
    sk = math.tan(math.radians(slant))
    out, pen_x = [], 0.0
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            pen_x += upm * 0.3
            continue
        pen = _Pen(gs)
        gs[gname].draw(pen)
        for sub in pen.done():
            nsub = []
            for seg in sub:
                op, v = seg[0], list(seg[1:])
                pts = []
                for i in range(0, len(v), 2):
                    gx, gy = v[i], v[i + 1]
                    # font units -> design units, y flipped, oblique applied
                    dx = (pen_x + gx) * s + (gy * s) * sk
                    dy = (gy * s) if y_up else (-gy * s)
                    pts += [x + dx, y + dy]
                nsub.append((op, *pts) if op != 'Z' else ('Z',))
            out.append(nsub)
        pen_x += hmtx[gname][0] + tracking * cap
    f.close()
    return out


def advance(text, size, tracking=0.0, path=FONT):
    f = TTFont(path)
    upm = f['head'].unitsPerEm
    cap = _cap(f, upm)
    s, cmap, hmtx = size / cap, f.getBestCmap(), f['hmtx']
    w = 0.0
    for ch in text:
        g = cmap.get(ord(ch))
        w += (hmtx[g][0] + tracking * cap) if g else upm * 0.3
    f.close()
    return w * s
