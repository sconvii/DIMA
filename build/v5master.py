"""Build the corrected single-sheet master from REF.pdf.

REF.pdf is a finished Illustrator DeviceCMYK vector master (no RGB, no fonts,
no rasters).  The only change the brief asks for is on the FRONT view:

  * the image-RIGHT front leg (= wearer's LEFT leg) carries an elongated
    tapering triangle - purple band `op146` with the black gap `op147`
    inside it - that runs all the way down to the ankle;
  * the image-LEFT front leg's band is cut off square at ~62 % of the leg.

The brief requires the *same* element on the second front leg, produced by
geometric mirroring of the existing element - never redrawn.  So the
left leg's band group is replaced by byte-identical copies of op146+op147
wrapped in a mirror matrix about the trousers panel's own axis of symmetry.

Nothing else in the stream is touched, so every other element stays
bit-exact with REF.pdf.
"""
import pymupdf

SRC = 'REF.pdf'
OUT = 'build/v5_master.pdf'

# Axis of symmetry of the front trousers panel, solved from the clip path
# itself (382 points, mean residual 0.0005 pt).
AXIS = 444.92700

# Byte spans in REF.pdf's page content stream (see build/refstream.py).
ELONGATED = (783432, 784037)   # q..Q of op146 (purple) + op147 (black gap)
LEFT_BAND = (785442, 786411)   # q..Q of ops 158-164, the left leg's short band

PURPLE_K = b'0.72 0.86 0 0.16 k\n'


def mirrored_block(stream: bytes) -> bytes:
    """The right leg's elongated triangle, mirrored about AXIS."""
    src = stream[ELONGATED[0]:ELONGATED[1]]
    return (b'q\n' + PURPLE_K
            + f'-1 0 0 1 {2 * AXIS:.5f} 0 cm\n'.encode('ascii')
            + src
            + b'Q\n')


def build(src=SRC, out=OUT):
    doc = pymupdf.open(src)
    page = doc[0]
    stream = page.read_contents()

    new = (stream[:LEFT_BAND[0]]
           + mirrored_block(stream)
           + stream[LEFT_BAND[1]:])

    # replace the page's content with the edited stream
    xref = doc.get_new_xref()
    doc.update_object(xref, '<<>>')
    doc.update_stream(xref, new)
    doc.xref_set_key(page.xref, 'Contents', f'{xref} 0 R')

    doc.save(out, garbage=4, deflate=True, clean=False)
    doc.close()
    return out, len(stream), len(new)


if __name__ == '__main__':
    p, a, b = build()
    print(f'{p}: stream {a} -> {b} bytes ({b - a:+d})')


# ------------------------------------------------------------- art-only ------
# The master sheet also carries the manufacturer's furniture: the SQDRA and
# SQD K-3 Art logos, the legal paragraph, the contact line, the "Согласовано"
# rule and the elastic-panel note.  That belongs on page 1 but must not bleed
# into a cropped detail page, so a second master is written with those objects
# neutralised - their painting operator is replaced by `n`, which consumes the
# path and draws nothing.  Geometry is untouched; nothing is re-drawn.

ART = 'build/v5_art.pdf'

# The four garment views, measured off the sheet (device space, y-up).
BANDS = [(128, 100, 251, 747),        # side view, wearer's RIGHT
         (304, 100, 586, 747),        # front
         (626, 100, 908, 747),        # back
         (960, 100, 1083, 747)]       # side view, wearer's LEFT


def _visible(o):
    b = o.bbox
    if o.clip:
        c = o.clip
        b = (max(b[0], c[0]), max(b[1], c[1]), min(b[2], c[2]), min(b[3], c[3]))
    return b


def furniture_ops(ops, join=20):
    """Painting ops that belong to the sheet furniture rather than a garment.

    An op is furniture when its visible box falls outside all four garment
    views.  That test alone misses a few glyphs of the elastic-panel note
    whose boxes reach into the side view's column, so each run of furniture
    ops is then closed up: an object bracketed on both sides by furniture,
    within `join` objects, is part of the same block.
    """
    flagged = []
    for o in ops:
        b = _visible(o)
        if b[2] <= b[0] or b[3] <= b[1]:
            continue
        if not any(b[0] >= X0 - 0.6 and b[2] <= X1 + 0.6
                   and b[1] >= Y0 - 0.6 and b[3] <= Y1 + 0.6
                   for X0, Y0, X1, Y1 in BANDS):
            flagged.append(o.i)

    keep = set()
    for i in flagged:
        keep.add(i)
    run = []
    for i in flagged:
        if run and i - run[-1] > join:
            keep.update(range(run[0], run[-1] + 1))
            run = []
        run.append(i)
    if run:
        keep.update(range(run[0], run[-1] + 1))
    return [o for o in ops if o.i in keep]


def build_art(src=OUT, out=ART):
    import refstream
    doc = pymupdf.open(src)
    page = doc[0]
    stream = page.read_contents()
    ops, _ = refstream.parse(stream)

    buf = bytearray(stream)
    hidden = furniture_ops(ops)
    for o in hidden:
        n = len(o.op)
        buf[o.end - n:o.end] = b'n' + b' ' * (n - 1)

    xref = doc.get_new_xref()
    doc.update_object(xref, '<<>>')
    doc.update_stream(xref, bytes(buf))
    doc.xref_set_key(page.xref, 'Contents', f'{xref} 0 R')
    doc.save(out, garbage=4, deflate=True, clean=False)
    doc.close()
    return out, len(hidden)
