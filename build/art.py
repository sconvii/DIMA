"""Traced reference artwork placed on the technical panels.

Every path is traced from REFERENCE_MASTER_2D; none is authored here.  Each
zone crosses over under ONE similarity - uniform scale from the zone's width,
position from a silhouette fit - so inside a zone every element keeps its
width, angle, length and the black gaps around it.
"""
import numpy as np
import trace as T
import zones as Z
import place as P

M = T.masks()

_FC = Z.crotch_y('front')
_BC = Z.crotch_y('back')

# ------------------------------------------------------------- zone boxes ---
FRONT_TORSO_BOX = (Z.VIEW['front'][0], Z.VIEW['front'][1], Z.VIEW['front'][2], _FC + 2)
BACK_TORSO_BOX = (Z.VIEW['back'][0], Z.VIEW['back'][1], Z.VIEW['back'][2], _BC + 2)
FL_BOX = Z.leg_box('front', 'L')
FR_BOX = Z.leg_box('front', 'R')
BL_BOX = Z.leg_box('back', 'L')
BR_BOX = Z.leg_box('back', 'R')
SLB_BOX = Z.VIEW['sleeve_black']
SLP_BOX = Z.VIEW['sleeve_purple']
SIDE_A_BOX = Z.VIEW['side_a']
SIDE_B_BOX = Z.VIEW['side_b']

# --------------------------------------------------------- zone transforms --
_, _fi = Z.view_transform('front')
_, _bi = Z.view_transform('back')
_, _fl = Z.leg_transform('front', 'L')
_, _bl = Z.leg_transform('back', 'L')
S_FRONT = _fi['pat_w'] / _fi['ref_w']
S_BACK = _bi['pat_w'] / _bi['ref_w']
S_FLEG = _fl['pat_w'] / _fl['ref_w']
S_BLEG = _bl['pat_w'] / _bl['ref_w']
_slb = Z.pat_sleeve([76, 77])
_slp = Z.pat_sleeve([78, 79])
_slb_b = Z.pat_sleeve([159, 160])
_slp_b = Z.pat_sleeve([157, 158])
S_SLB = _slb['width'] / Z.sleeve_metrics('sleeve_black')['width']
S_SLP = _slp['width'] / Z.sleeve_metrics('sleeve_purple')['width']

FIT = {}
FIT['front_torso'], _ = P.build(FRONT_TORSO_BOX, [76, 77, 78, 79, 80],
                                (250, 80, 650, 460), S_FRONT)
FIT['front_leg_L'], _ = P.build(FL_BOX, [80], (250, 452, 445.2, 782), S_FLEG)
FIT['front_leg_R'], _ = P.build(FR_BOX, [80], (445.2, 452, 650, 782), S_FLEG)
FIT['back_torso'], _ = P.build(BACK_TORSO_BOX, [153, 155, 156, 157, 158, 159, 160],
                               (580, 80, 960, 352), S_BACK)
FIT['back_leg_L'], _ = P.build(BL_BOX, [151], None, S_BLEG)
FIT['back_leg_R'], _ = P.build(BR_BOX, [152], None, S_BLEG)
FIT['sleeve_black_front'], _ = P.build(SLB_BOX, [76, 77], None, S_SLB)
FIT['sleeve_purple_front'], _ = P.build(SLP_BOX, [78, 79], None, S_SLP)
# Back faces: same arm, mirrored, because a flat shows the far side reversed.
# Nothing is swapped between arms - black stays the wearer's right.
_axb = (_slb_b['span'][0] + _slb_b['span'][1]) / 2.0
_axp = (_slp_b['span'][0] + _slp_b['span'][1]) / 2.0
FIT['sleeve_black_back'], _ = P.build(SLB_BOX, [159, 160], None, S_SLB)
FIT['sleeve_purple_back'], _ = P.build(SLP_BOX, [157, 158], None, S_SLP)
# Side panels ride at LEG scale so they stay continuous with front and back and
# leave the side view predominantly black, as the reference panel is.
FIT['side_L'], _ = P.build(SIDE_A_BOX, [57, 103], (137, 352, 250, 740), S_FLEG)
FIT['side_R'], _ = P.build(SIDE_B_BOX, [56, 102], (960, 352, 1075, 740), S_FLEG)


# ------------------------------------------------------------------ paths ---
# White trims are thin: the piping lines and the period of "D. FEDOROV" fall
# below the speckle filter used for the big violet shapes, so they get their
# own, finer settings.
FINE = dict(eps=0.0016, blur=0, min_area=4)


def _zone(mask_name, box, key, fine=False):
    tf = FIT[key]
    flat = []
    opts = FINE if fine else {}
    for poly in T.contours(M[mask_name], box, **opts):
        for ring in [poly['outer']] + poly['holes']:
            p = tf(ring)
            sub = [('M', float(p[0][0]), float(p[0][1]))]
            sub += [('L', float(x), float(y)) for x, y in p[1:]]
            sub.append(('Z',))
            flat.append(sub)
    return flat


def front_torso_purple():
    return _zone('purple', FRONT_TORSO_BOX, 'front_torso')


def front_torso_white():
    return _zone('white', FRONT_TORSO_BOX, 'front_torso', fine=True)


def back_torso_purple():
    return _zone('purple', BACK_TORSO_BOX, 'back_torso')


def back_torso_white():
    return _zone('white', BACK_TORSO_BOX, 'back_torso', fine=True)


def front_legs_purple():
    return _zone('purple', FL_BOX, 'front_leg_L') + _zone('purple', FR_BOX, 'front_leg_R')


def back_legs_purple():
    return _zone('purple', BL_BOX, 'back_leg_L') + _zone('purple', BR_BOX, 'back_leg_R')


def side_purple(side):
    box = SIDE_A_BOX if side == 'L' else SIDE_B_BOX
    return _zone('purple', box, 'side_L' if side == 'L' else 'side_R')


def sleeve_marks(kind, face):
    """Marks on a sleeve: violet on the black sleeve, dark on the violet one."""
    box = SLB_BOX if kind == 'black' else SLP_BOX
    name = 'purple' if kind == 'black' else 'black'
    return _zone(name, box, 'sleeve_%s_%s' % (kind, face))
