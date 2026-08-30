"""Parser for REF.pdf's page content stream.

REF.pdf is a finished Illustrator CMYK vector master: the stream uses only
path construction (m l c y h re), painting (f f* S n), clipping (W), colour
(k K) and state (q Q cm gs w j J d) operators.  There is no text, no image
and no RGB anywhere, so the stream can be manipulated as *bytes* and stays
print-correct.

parse() returns one Op per painting operator, carrying the exact byte span
that produced it.  Re-emitting that span verbatim reproduces the element
bit-exactly; wrapping it in a `cm` reproduces it transformed.  Nothing here
redraws geometry by hand.
"""
import re

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)'
TOKEN = re.compile(rb'/[^\s/\[\]<>(){}]+|<<|>>|\[|\]|[-+]?(?:\d+\.?\d*|\.\d+)|[A-Za-z\'"*]+')

PAINT = {'f', 'F', 'f*', 'S', 's', 'B', 'B*', 'b', 'b*', 'n'}


def mat_mul(a, b):
    """a then b  (PDF row-vector convention)."""
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (a0 * b0 + a1 * b2, a0 * b1 + a1 * b3,
            a2 * b0 + a3 * b2, a2 * b1 + a3 * b3,
            a4 * b0 + a5 * b2 + b4, a4 * b1 + a5 * b3 + b5)


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


class Op:
    __slots__ = ('i', 'start', 'end', 'op', 'ctm', 'fill', 'stroke', 'width',
                 'pts', 'bbox', 'clip', 'qdepth', 'nsub', 'qpos')

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def __repr__(self):
        b = self.bbox
        return (f'<Op#{self.i} {self.op} f={self.fill} s={self.stroke} '
                f'bbox=({b[0]:.1f},{b[1]:.1f},{b[2]:.1f},{b[3]:.1f})>')


def parse(stream: bytes):
    """Tokenise the stream and return (ops, tokens).

    Coordinates in Op.bbox / Op.pts are *device* space (page space, y-up,
    origin bottom-left) with the CTM in force applied.
    """
    toks = [(m.group(0).decode('latin-1'), m.start(), m.end())
            for m in TOKEN.finditer(stream)]

    ops = []
    stack = []                       # saved (ctm, fill, stroke, width, clip)
    qpos = []                        # byte offset of each open 'q'
    ctm = (1, 0, 0, 1, 0, 0)
    fill = stroke = None
    width = 1.0
    clip = None                      # bbox of the active clip, device space
    pend_clip = False

    operands = []
    cur = []                         # device-space points of the current path
    subs = 0                         # number of subpaths in the current path
    cx = cy = 0.0                    # current point, user space
    sx = sy = 0.0                    # subpath start, user space
    path_start = None                # byte offset where the current path began

    def dev(x, y):
        return apply(ctm, x, y)

    def num(k):
        return float(operands[k][0])

    def opnd0(default):
        return operands[0][1] if operands else default

    for tok, a, b in toks:
        if re.fullmatch(NUM, tok):
            operands.append((tok, a, b))
            continue
        if tok.startswith('/') or tok in ('[', ']', '<<', '>>'):
            operands.append((tok, a, b))
            continue

        # ---- path construction -------------------------------------
        if tok == 'm':
            if path_start is None:
                path_start = opnd0(a)
            cx, cy = num(-2), num(-1)
            sx, sy = cx, cy
            cur.append(dev(cx, cy))
            subs += 1
        elif tok == 'l':
            cx, cy = num(-2), num(-1)
            cur.append(dev(cx, cy))
        elif tok == 'c':
            for i in (-6, -4, -2):
                cur.append(dev(num(i), num(i + 1)))
            cx, cy = num(-2), num(-1)
        elif tok == 'v':
            for i in (-4, -2):
                cur.append(dev(num(i), num(i + 1)))
            cx, cy = num(-2), num(-1)
        elif tok == 'y':
            for i in (-4, -2):
                cur.append(dev(num(i), num(i + 1)))
            cx, cy = num(-2), num(-1)
        elif tok == 'h':
            cx, cy = sx, sy
        elif tok == 're':
            if path_start is None:
                path_start = opnd0(a)
            x, y, w, hh = num(-4), num(-3), num(-2), num(-1)
            for px, py in ((x, y), (x + w, y), (x + w, y + hh), (x, y + hh)):
                cur.append(dev(px, py))
            cx, cy = x, y
            sx, sy = x, y
            subs += 1

        # ---- clipping ----------------------------------------------
        elif tok in ('W', 'W*'):
            pend_clip = True

        # ---- painting ----------------------------------------------
        elif tok in PAINT:
            if cur:
                xs = [p[0] for p in cur]
                ys = [p[1] for p in cur]
                bbox = (min(xs), min(ys), max(xs), max(ys))
            else:
                bbox = (0, 0, 0, 0)
            if pend_clip:
                if clip is None:
                    clip = bbox
                else:
                    clip = (max(clip[0], bbox[0]), max(clip[1], bbox[1]),
                            min(clip[2], bbox[2]), min(clip[3], bbox[3]))
                pend_clip = False
            if tok != 'n':
                ops.append(Op(i=len(ops), start=path_start, end=b, op=tok,
                              ctm=ctm, fill=fill, stroke=stroke, width=width,
                              pts=cur, bbox=bbox, clip=clip, qdepth=len(stack),
                              nsub=subs, qpos=qpos[-1] if qpos else None))
            cur = []
            subs = 0
            path_start = None

        # ---- colour -------------------------------------------------
        elif tok == 'k':
            fill = tuple(round(num(i), 4) for i in (-4, -3, -2, -1))
        elif tok == 'K':
            stroke = tuple(round(num(i), 4) for i in (-4, -3, -2, -1))
        elif tok == 'g':
            fill = (0.0, 0.0, 0.0, round(1 - num(-1), 4))
        elif tok == 'G':
            stroke = (0.0, 0.0, 0.0, round(1 - num(-1), 4))

        # ---- state --------------------------------------------------
        elif tok == 'q':
            stack.append((ctm, fill, stroke, width, clip))
            qpos.append(a)
        elif tok == 'Q':
            if stack:
                ctm, fill, stroke, width, clip = stack.pop()
            if qpos:
                qpos.pop()
        elif tok == 'cm':
            ctm = mat_mul(tuple(num(i) for i in range(-6, 0)), ctm)
        elif tok == 'w':
            width = num(-1)

        operands = []

    return ops, toks


def load(path='REF.pdf'):
    import pymupdf
    doc = pymupdf.open(path)
    page = doc[0]
    stream = page.read_contents()
    ops, toks = parse(stream)
    return doc, page, stream, ops
