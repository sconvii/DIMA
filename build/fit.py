"""Fit each zone's similarity by aligning SILHOUETTES, not guessed landmarks.

For every zone the reference garment mask and the technical panel mask are
rasterised into the same space, and one uniform scale plus a translation is
searched for maximum overlap.  Scale stays isotropic, so the artwork inside a
zone is never stretched - the whole group is placed as one.
"""
import numpy as np
import cv2
import pymupdf
import trace as T
import suitsrc as S

DPI = 1.5          # px per design point - enough for a silhouette fit
M = T.masks()
GAR = M['garment']
_doc, _page, DR, _rect = S.load()


def panel_mask(idxs, clip=None, dpi=DPI):
    """Rasterise pattern panels into a design-space mask."""
    doc = pymupdf.open()
    pw, ph = _rect.width, _rect.height
    pg = doc.new_page(width=pw, height=ph)
    sh = pg.new_shape()
    for i in idxs:
        subs = S.close_all(S.path_of(DR[i]))
        for poly in S.flatten(subs, 10):
            sh.draw_polyline([pymupdf.Point(*p) for p in poly])
        sh.finish(color=None, fill=(0, 0, 0), closePath=True)
    sh.commit()
    pix = pg.get_pixmap(dpi=int(dpi * 72), colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    m = (a < 128).astype(np.uint8)
    if clip:
        x0, y0, x1, y1 = clip
        keep = np.zeros_like(m)
        keep[int(y0 * dpi):int(y1 * dpi), int(x0 * dpi):int(x1 * dpi)] = 1
        m = m * keep
    doc.close()
    return m


def ref_mask(box):
    x0, y0, x1, y1 = box
    m = np.zeros_like(GAR, np.uint8)
    m[y0:y1, x0:x1] = GAR[y0:y1, x0:x1]
    return m


def _bbox(m):
    ys, xs = np.nonzero(m)
    return xs.min(), ys.min(), xs.max(), ys.max()


def fit(ref_box, pat_idxs, pat_clip=None, dpi=DPI, refine=True, scale=None):
    """Similarity aligning the reference silhouette to the panel silhouette.

    Closed form from image moments: an isotropic scale from the area ratio and
    a translation from the centroids.  That is the least-squares similarity for
    two filled shapes, and it cannot stretch either axis.  A short local search
    then trims the residual.
    """
    R = ref_mask(ref_box)
    P = panel_mask(pat_idxs, pat_clip, dpi)
    ra = np.count_nonzero(R)
    pa = np.count_nonzero(P) / (dpi * dpi)
    if ra == 0 or pa == 0:
        raise ValueError('empty mask')
    # Scale is taken from the zone WIDTH when one is supplied: every element of
    # this artwork is width-referenced (band widths, and the black gaps between
    # them), and those must transfer unchanged.  Area is only the fallback.
    s = float(scale) if scale else float(np.sqrt(pa / ra))
    ys, xs = np.nonzero(R)
    rc = np.array([xs.mean(), ys.mean()])
    ys, xs = np.nonzero(P)
    pc = np.array([xs.mean() / dpi, ys.mean() / dpi])

    if refine:
        rx0, ry0, rx1, ry1 = _bbox(R)
        Rsm = R[ry0:ry1 + 1, rx0:rx1 + 1]
        off = np.array([(rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0]) - rc
        best = (s, pc, -1.0)
        span_s, span_t = (0.0 if scale else 0.18), 26.0
        for _ in range(3):
            s_grid = ([s] if scale else
                      np.linspace(best[0] * (1 - span_s), best[0] * (1 + span_s), 9))
            for sc in s_grid:
                w = max(2, int(round((rx1 - rx0) * sc * dpi)))
                h = max(2, int(round((ry1 - ry0) * sc * dpi)))
                warped = cv2.resize(Rsm, (w, h), interpolation=cv2.INTER_NEAREST)
                for dx in np.linspace(-span_t, span_t, 9):
                    for dy in np.linspace(-span_t, span_t, 9):
                        cx, cy = best[1][0] + dx, best[1][1] + dy
                        ox = int(round((cx + off[0] * sc) * dpi - w / 2))
                        oy = int(round((cy + off[1] * sc) * dpi - h / 2))
                        if ox < 0 or oy < 0 or ox + w > P.shape[1] or oy + h > P.shape[0]:
                            continue
                        sub = P[oy:oy + h, ox:ox + w]
                        inter = np.count_nonzero(sub & warped)
                        union = np.count_nonzero(sub | warped) + int(P.sum()) - int(sub.sum())
                        iou = inter / max(union, 1)
                        if iou > best[2]:
                            best = (sc, np.array([cx, cy]), iou)
            span_s *= 0.4
            span_t *= 0.4
        s, pc, iou = best[0], best[1], best[2]
    else:
        iou = -1.0
    return {'scale': float(s), 'ref_anchor': (float(rc[0]), float(rc[1])),
            'pat_anchor': (float(pc[0]), float(pc[1])), 'iou': float(iou)}


def _unused(ref_box, pat_idxs, pat_clip=None, dpi=DPI, iters=3):
    R = ref_mask(ref_box)
    P = panel_mask(pat_idxs, pat_clip, dpi)
    rx0, ry0, rx1, ry1 = _bbox(R)
    px0, py0, px1, py1 = _bbox(P)
    rw, rh = rx1 - rx0, ry1 - ry0
    pw, ph = px1 - px0, py1 - py0
    # seed: match the bounding boxes on the smaller of the two ratios
    s0 = min(pw / max(rw, 1), ph / max(rh, 1)) / dpi
    rc = np.array([(rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0])
    pc = np.array([(px0 + px1) / 2.0, (py0 + py1) / 2.0]) / dpi

    Rsm = R[ry0:ry1 + 1, rx0:rx1 + 1]
    best = (s0, pc, -1.0)
    span_s, span_t = 0.35, 60.0
    for it in range(iters):
        s_grid = np.linspace(best[0] * (1 - span_s), best[0] * (1 + span_s), 13)
        t_grid = np.linspace(-span_t, span_t, 13)
        for s in s_grid:
            w = max(2, int(round((rx1 - rx0) * s * dpi)))
            h = max(2, int(round((ry1 - ry0) * s * dpi)))
            warped = cv2.resize(Rsm, (w, h), interpolation=cv2.INTER_NEAREST)
            for dx in t_grid:
                for dy in t_grid:
                    ox = int(round((best[1][0] + dx) * dpi - w / 2))
                    oy = int(round((best[1][1] + dy) * dpi - h / 2))
                    if ox < 0 or oy < 0 or ox + w > P.shape[1] or oy + h > P.shape[0]:
                        continue
                    sub = P[oy:oy + h, ox:ox + w]
                    inter = np.count_nonzero(sub & warped)
                    union = np.count_nonzero(sub | warped) + (P.sum() - sub.sum())
                    iou = inter / max(union, 1)
                    if iou > best[2]:
                        best = (s, np.array([best[1][0] + dx, best[1][1] + dy]), iou)
        span_s *= 0.35
        span_t *= 0.35
    s, pcen, iou = best
    return {'scale': float(s), 'ref_anchor': tuple(rc),
            'pat_anchor': (float(pcen[0]), float(pcen[1])), 'iou': float(iou)}
