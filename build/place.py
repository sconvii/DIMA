"""Per-zone placement: uniform scale from the zone width, position from the
silhouette fit.  One transform per zone; nothing inside a zone is stretched."""
import numpy as np
import fit as F
import zones as Z
import trace as T


class Place:
    def __init__(self, scale, ref_anchor, pat_anchor, flip_about=None):
        self.s = float(scale)
        self.ra = np.asarray(ref_anchor, float)
        self.pa = np.asarray(pat_anchor, float)
        self.flip = flip_about

    def __call__(self, pts):
        p = (np.asarray(pts, float) - self.ra) * self.s + self.pa
        if self.flip is not None:
            p = np.column_stack([2 * self.flip - p[:, 0], p[:, 1]])
        return p

    def __repr__(self):
        return 'Place(s=%.4f pat=%s)' % (self.s, tuple(np.round(self.pa, 1)))


def build(ref_box, pat_idxs, pat_clip, scale, flip_about=None):
    r = F.fit(ref_box, pat_idxs, pat_clip, scale=scale)
    return Place(r['scale'], r['ref_anchor'], r['pat_anchor'], flip_about), r['iou']
