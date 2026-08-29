"""CMYK vector renderer: draws design-space paths onto a ReportLab canvas."""
from reportlab.lib.colors import CMYKColor

# ---------------------------------------------------------------- palette ---
# Derived from DIMA.jpeg (see colours.md).  All values DeviceCMYK.
RICH_BLACK = CMYKColor(0.40, 0.40, 0.40, 1.00)   # manufacturer spec 40/40/40/100
PURPLE     = CMYKColor(0.72, 0.86, 0.00, 0.16)   # main violet -> RGB 88/58/135
PURPLE_DK  = CMYKColor(0.82, 0.95, 0.05, 0.42)   # shadow shards -> RGB 55/24/95
WHITE      = CMYKColor(0.00, 0.00, 0.00, 0.00)


def composite_grey(k):
    """Neutral grey as a composite build.

    The manufacturer asks for composite rather than flat K on greys as well as
    on black, so every neutral uses the same 40 % chromatic under-colour as the
    specified rich black.  K is scaled down because the added C/M/Y darkens the
    result - the printed tone still matches the flat-K value it replaces.
    """
    kk = max(0.0, min(1.0, 0.75 * k))
    return CMYKColor(0.40 * kk, 0.40 * kk, 0.40 * kk, kk)


SEAM     = composite_grey(0.75)   # technical seam / stitch lines
TECH     = composite_grey(0.55)   # thin construction outlines
GREY_TXT = composite_grey(0.80)
HATCH    = composite_grey(0.32)   # sketch texture indication


def new_path(c):
    return c.beginPath()


def add(p, subs):
    """Append design-space subpaths to a ReportLab path object."""
    for s in subs:
        for seg in s:
            op = seg[0]
            if op == 'M':
                p.moveTo(seg[1], seg[2])
            elif op == 'L':
                p.lineTo(seg[1], seg[2])
            elif op == 'C':
                p.curveTo(*seg[1:7])
            elif op == 'Z':
                p.close()
    return p


def poly(c, pts, close=True):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def fill(c, subs, colour, eo=False):
    c.setFillColor(colour)
    c.drawPath(add(c.beginPath(), subs), stroke=0, fill=1, fillMode=1 if eo else 0)


def fill_pts(c, pts, colour):
    c.setFillColor(colour)
    c.drawPath(poly(c, pts), stroke=0, fill=1)


def stroke(c, subs, colour, w, dash=None, cap=0, join=0):
    c.setStrokeColor(colour)
    c.setLineWidth(w)
    c.setLineCap(cap)
    c.setLineJoin(join)
    c.setDash(dash if dash else [])
    c.drawPath(add(c.beginPath(), subs), stroke=1, fill=0)
    c.setDash([])


class Clip:
    """`with Clip(c, subpaths):` — restricts drawing to the panel outline."""

    def __init__(self, c, subs, eo=False):
        self.c, self.subs, self.eo = c, subs, eo

    def __enter__(self):
        self.c.saveState()
        p = add(self.c.beginPath(), self.subs)
        self.c.clipPath(p, stroke=0, fill=0, fillMode=1 if self.eo else 0)
        return self.c

    def __exit__(self, *a):
        self.c.restoreState()
        return False


# ------------------------------------------------------------------ text ---
def text(c, x, y, s, size, colour, bold=False, align='left', font=None, y_up=True):
    """Draw a string as vector outlines - the finished PDF references no font.

    `y_up` matches an un-flipped PDF canvas; set it False inside the sketch's
    y-down design space.
    """
    import textcurves as TC
    path = font or (TC.UI_BOLD if bold else TC.UI)
    cap = size * 0.72                      # optical cap height for a body size
    w = TC.advance(s, cap, path=path)
    if align == 'right':
        x -= w
    elif align == 'center':
        x -= w / 2.0
    fill(c, TC.outlines(s, cap, x, y, path=path, y_up=y_up), colour, eo=True)
    return w
