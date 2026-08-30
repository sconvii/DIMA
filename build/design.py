"""Geometry helpers and the trims that are NOT part of the traced artwork.

Every graphic path for the chest, back, sleeves, front legs, back legs and side
panels has been DELETED from this module - those now come from `art.py`, traced
directly off REFERENCE_MASTER_2D.  Nothing here draws design artwork.
"""
import math
from render import RICH_BLACK, PURPLE, PURPLE_DK, WHITE, fill, fill_pts, stroke
import geom as G

FCX, BCX, MIRROR = G.FCX, G.BCX, G.MIRROR


def mx(p, axis):
    return (2 * axis - p[0], p[1])


def mirror_pts(pts, axis):
    return [mx(p, axis) for p in pts]


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


def bigrect(c, x0, y0, x1, y1, col):
    fill(c, [[('M', x0, y0), ('L', x1, y0), ('L', x1, y1), ('L', x0, y1), ('Z',)]], col)
