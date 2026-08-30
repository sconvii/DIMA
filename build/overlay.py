"""Zone-by-zone overlay: traced reference vs the built PDF, in design space."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, pymupdf, io
from PIL import Image
import trace as T, art as A, fit as F

PDF = 'DIMA_Suit_Final_v4.pdf'
DPI = 3.0                       # px per design point

M = T.masks()


def built_masks(pdf=PDF, dpi=DPI):
    d = pymupdf.open(pdf)
    pix = d[0].get_pixmap(dpi=int(dpi * 72), colorspace=pymupdf.csRGB, alpha=True)
    raw = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 4)
    rgb = raw[..., :3].astype(np.int16)
    al = raw[..., 3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = 0.299 * r + 0.587 * g + 0.114 * b
    gar = al > 128
    pur = (b - r > 28) & (b > 55) & gar
    wht = (L > 168) & gar & (abs(r - g) < 30) & (abs(g - b) < 30) & ~pur
    d.close()
    return {'garment': gar, 'purple': pur, 'white': wht}


def ref_zone_in_design(mask_name, box, key, shape, dpi=DPI):
    """Rasterise the traced+placed reference zone into design space."""
    canvas = np.zeros(shape, np.uint8)
    tf = A.FIT[key]
    for poly in T.contours(M[mask_name], box):
        rings = [poly['outer']] + poly['holes']
        for j, ring in enumerate(rings):
            p = tf(ring) * dpi
            cv2.fillPoly(canvas, [p.astype(np.int32)], 0 if j else 1)
    return canvas.astype(bool)


# Window = the real panel mask, so a zone is never scored against its
# neighbour's artwork.  (name, ref mask, ref box, transform key, panels, y band)
ZONES = [
    ('CHEST',     'purple', A.FRONT_TORSO_BOX, 'front_torso', [80], (92, 460)),
    ('CHEST wht', 'white',  A.FRONT_TORSO_BOX, 'front_torso', [80], (92, 460)),
    ('BACK',      'purple', A.BACK_TORSO_BOX,  'back_torso',  [153, 155, 156], (92, 352)),
    ('BACK wht',  'white',  A.BACK_TORSO_BOX,  'back_torso',  [153, 155, 156], (92, 352)),
    ('LEG F-L',   'purple', A.FL_BOX, 'front_leg_L', [80], (452, 745, 250, 445.2)),
    ('LEG F-R',   'purple', A.FR_BOX, 'front_leg_R', [80], (452, 745, 445.2, 650)),
    ('LEG B-L',   'purple', A.BL_BOX, 'back_leg_L',  [151], (348, 745)),
    ('LEG B-R',   'purple', A.BR_BOX, 'back_leg_R',  [152], (348, 745)),
    ('SIDE L',    'purple', A.SIDE_A_BOX, 'side_L',  [57, 103], (340, 745)),
    ('SIDE R',    'purple', A.SIDE_B_BOX, 'side_R',  [56, 102], (340, 745)),
    ('SLV blk F', 'purple', A.SLB_BOX, 'sleeve_black_front',  [76, 77], (150, 450)),
    ('SLV pur F', 'black',  A.SLP_BOX, 'sleeve_purple_front', [78, 79], (150, 450)),
    ('SLV pur B', 'black',  A.SLP_BOX, 'sleeve_purple_back',  [157, 158], (150, 450)),
    ('SLV blk B', 'purple', A.SLB_BOX, 'sleeve_black_back',   [159, 160], (150, 450)),
]

_PANEL_CACHE = {}


def panel_window(idxs, band, shape):
    """Panel mask limited to a y band, and to an x band when two zones share a
    panel - the two front legs are both part of #80 and must be scored apart."""
    key = (tuple(idxs), band)
    if key not in _PANEL_CACHE:
        m = F.panel_mask(idxs, None, DPI).astype(bool)
        if m.shape != shape:
            m = cv2.resize(m.astype(np.uint8), (shape[1], shape[0]),
                           interpolation=cv2.INTER_NEAREST).astype(bool)
        w = np.zeros(shape, bool)
        y0, y1 = int(band[0] * DPI), int(band[1] * DPI)
        if len(band) == 4:
            w[y0:y1, int(band[2] * DPI):int(band[3] * DPI)] = True
        else:
            w[y0:y1] = True
        _PANEL_CACHE[key] = m & w
    return _PANEL_CACHE[key]


def run(pdf=PDF):
    B = built_masks(pdf)
    shape = B['purple'].shape
    print('%-11s %8s %8s %7s %9s' % ('zone', 'ref px', 'built px', 'IoU', 'area err'))
    print('-' * 50)
    rows = []
    for name, mname, box, key, panels, band in ZONES:
        R = ref_zone_in_design(mname, box, key, shape)
        Bm = B['white'] if mname == 'white' else B['purple']
        if mname == 'black':
            Bm = B['garment'] & ~B['purple'] & ~B['white']
        win = panel_window(panels, band, shape)
        r, b = R & win, Bm & win
        inter = np.count_nonzero(r & b); union = np.count_nonzero(r | b)
        iou = inter / max(union, 1)
        ae = (np.count_nonzero(b) - np.count_nonzero(r)) / max(np.count_nonzero(r), 1)
        rows.append((name, np.count_nonzero(r), np.count_nonzero(b), iou, ae))
        print('%-11s %8d %8d %7.3f %+8.1f%%' % (name, rows[-1][1], rows[-1][2], iou, ae * 100))
    return rows


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else PDF)


def visual(pdf=PDF, out='analysis/v4_overlay.png'):
    """Per-zone panel: reference (magenta) vs built (green); white = agreement."""
    B = built_masks(pdf)
    shape = B['purple'].shape
    tiles = []
    for name, mname, box, key, panels, band in ZONES:
        if mname != 'purple':
            continue
        R = ref_zone_in_design(mname, box, key, shape)
        win = panel_window(panels, band, shape)
        r, b = R & win, B['purple'] & win
        ys, xs = np.nonzero(r | b)
        if len(xs) == 0:
            continue
        pad = 12
        x0, x1 = max(0, xs.min() - pad), min(shape[1], xs.max() + pad)
        y0, y1 = max(0, ys.min() - pad), min(shape[0], ys.max() + pad)
        img = np.full((y1 - y0, x1 - x0, 3), 250, np.uint8)
        rr, bb = r[y0:y1, x0:x1], b[y0:y1, x0:x1]
        img[rr & ~bb] = (220, 40, 200)      # reference only
        img[bb & ~rr] = (40, 190, 90)       # built only
        img[rr & bb] = (35, 35, 35)         # agreement
        h = 470
        im = Image.fromarray(img).resize((max(1, int(img.shape[1] * h / img.shape[0])), h),
                                         Image.NEAREST)
        tiles.append((name, im))
    W = sum(t.width for _, t in tiles) + 16 * len(tiles)
    sheet = Image.new('RGB', (W, 470 + 26), (255, 255, 255))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    x = 0
    for name, t in tiles:
        sheet.paste(t, (x, 26))
        dr.text((x + 3, 8), name, fill=(0, 0, 0))
        x += t.width + 16
    sheet.save(out)
    print('wrote', out, sheet.size)
