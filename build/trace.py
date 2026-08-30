"""Vectorise REFERENCE_MASTER_2D by tracing it - no artwork is invented here.

Colour separation -> contour extraction -> polygon simplification.  Holes are
kept as separate subpaths so the black gaps in the reference stay real
negative space instead of being painted over.
"""
import numpy as np
import cv2
from PIL import Image

REF = 'ref2d.png'
EPS = 0.0030          # simplification, as a fraction of each contour's perimeter
BLUR = 5              # median filter that kills JPEG speckle before tracing
MIN_AREA = 18         # px^2 - below this is JPEG speckle, not artwork


def masks(path=REF):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    h, w, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    L = 0.299 * r + 0.587 * g + 0.114 * b
    light = ((L > 195) & (abs(r - g) < 16) & (abs(g - b) < 16)).astype(np.uint8)
    # Flood the page in from the corners: white INSIDE the garment is design,
    # not background, and must not be swallowed by a plain luminance threshold.
    ff = light.copy()
    mk = np.zeros((h + 2, w + 2), np.uint8)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        cv2.floodFill(ff, mk, seed, 2)
    garment = ~(ff == 2)
    purple = (b - r > 28) & (b > 55) & garment
    white = (L > 168) & garment & (abs(r - g) < 30) & (abs(g - b) < 30) & ~purple
    black = garment & ~purple & ~white
    return {'garment': garment, 'purple': purple, 'white': white, 'black': black}


def contours(mask, box=None, eps=None, blur=None, min_area=None):
    """Traced polygons: [{'outer': Nx2, 'holes': [Nx2, ...]}, ...] in image px."""
    m = mask.astype(np.uint8)
    if box:
        x0, y0, x1, y1 = box
        sub = np.zeros_like(m)
        sub[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        m = sub
    bl = BLUR if blur is None else blur
    if bl:
        m = cv2.medianBlur(m * 255, bl) // 255
    if (blur is None) or blur:
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return []
    hier = hier[0]
    out = []
    for i, c in enumerate(cs):
        if hier[i][3] != -1:            # a hole; attached to its parent below
            continue
        ma = MIN_AREA if min_area is None else min_area
        if cv2.contourArea(c) < ma:
            continue
        ep = EPS if eps is None else eps
        poly = cv2.approxPolyDP(c, ep * cv2.arcLength(c, True), True)
        holes = []
        j = hier[i][2]
        while j != -1:
            hc = cs[j]
            if cv2.contourArea(hc) >= ma:
                holes.append(cv2.approxPolyDP(hc, ep * cv2.arcLength(hc, True), True)
                             .reshape(-1, 2).astype(float))
            j = hier[j][0]
        out.append({'outer': poly.reshape(-1, 2).astype(float), 'holes': holes})
    out.sort(key=lambda p: cv2.contourArea(p['outer'].astype(np.float32)), reverse=True)
    return out


def panel_span(garment, box, y):
    """x extent of the garment on row y inside box - used for control points."""
    x0, y0, x1, y1 = box
    row = garment[y, x0:x1]
    idx = np.nonzero(row)[0]
    if len(idx) == 0:
        return None
    return x0 + idx[0], x0 + idx[-1]


def panel_rows(garment, box):
    x0, y0, x1, y1 = box
    sub = garment[y0:y1, x0:x1]
    rows = np.nonzero(sub.sum(1) > 2)[0]
    return (y0 + rows[0], y0 + rows[-1]) if len(rows) else None
