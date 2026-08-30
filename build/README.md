# DIMA — SQD K-3 Art production layout

Rebuilds `DIMA_Suit_Final_Print.pdf` (production, DeviceCMYK, all vector) and
`DIMA_Suit_Final_Print_Check.pdf` (screen proof) from the two source files in
the repository root.

```
pip install pymupdf pillow numpy reportlab fonttools
python3 build/build.py     # -> DIMA_Suit_Final_v3.pdf        (8 pages)
python3 build/check.py     # -> DIMA_Suit_Final_v3_Check.pdf  (4 pages)
python3 build/verify.py    # pre-flight: colour space, fonts, rasters, bleed
python3 build/compare.py   # scanline fidelity check against DIMA.jpeg
```

Earlier releases (`DIMA_Suit_Final_Print.pdf`, `DIMA_Suit_Final_v2.pdf`) are
kept untouched; the scripts build v3.

## How it works

| module | role |
| --- | --- |
| `suitsrc.py` | reads the CorelDRAW sketch and converts its 232 vector objects to paths |
| `geom.py` | derives the livery's boundaries **from those contours** (band widths as a fraction of each panel's own width at each height, measured off `DIMA.jpeg`) |
| `shards.py` | the shard / blade / tapering-band primitives |
| `design.py` | the livery itself: violet fields with torn edges, dark slivers, black notches, the chest blade, the back burst |
| `textcurves.py` | text → explicit outlines, so the PDF references no font at all |
| `render.py` | DeviceCMYK painting, clipping, the ink palette |
| `build.py` | walks every source object in the sketch's own z-order and paints the livery clipped to each panel |

The livery is defined **once**, in the sketch's coordinate space, and then
clipped to every panel it crosses. That is what makes the graphic continue
across the front→side→back and body→sleeve joins without a seam: neighbouring
panels are cut out of one continuous definition rather than drawn separately.


## v2 corrections

Graphics reworked against the close-up references; construction, panel sizes,
colour build and PDF structure are unchanged.

| area | was | now |
| --- | --- | --- |
| chest | short triangular wedges | long thin slash streaks in two clusters, off the violet mass; white blade kept |
| back | wide radial spikes, field too far right | long near-parallel streaks above and below the plate, field pulled left so black stays on the right; plate widened |
| sleeves | small fan at the cuff | a band of long diagonal streaks crossing the lower forearm on both sleeves |
| front legs | straight vertical stripe | the reference's sharp knee chevron, with the pinstripe held at ~7 % of the band width |


## v3 corrections

Leg and side-panel graphics reworked against the 2D flat reference. Chest, back
and sleeves carried over from v2 unchanged; construction, panel sizes, colour
build and PDF structure untouched.

Element extents were measured off `DIMA.jpeg` at 3x by scanline, as a fraction
of each leg's own width from the side seam:

| design y | element extent | black gap |
| --- | --- | --- |
| 449 | 40 % | thin |
| 471 | 41 % | 18-23 % |
| 538 | 56 % (apex) | thin |
| 583 | 53 % | 31-44 % |
| 605 | 27 % | 11-14 % |
| 650 | 0 % | - |

| area | was | now |
| --- | --- | --- |
| front legs | one band split by a hairline | two separate elements; the gap is specified against the LEG (4.5-9 %), not the band, so it actually reads |
| front legs, side seam | element ran to the contour | a black gap is held at the seam along the whole length, opening below the knee where the element pulls away and tapers out |
| side panels | one solid violet wrap running the full length | predominantly black, carrying two separate elements: the front-side one runs out at the calf (as the front view does), the back-side one carries on to the ankle (as the back view does) |
| back legs | short calf blade | blade lengthened and raised to the measured position |

Sleeve colours are anatomical, per the author's decision: black is the wearer's
right arm, so it reads left on the front view and right on the back view.


## v5 — REF.pdf as the graphic master

`REF.pdf` supersedes every earlier graphic source. Inspecting it settled the
approach: it is not a picture to trace but a **finished Illustrator vector
master** — 472 painting operations, no raster, no font resource, and already
DeviceCMYK with this project's exact palette (rich black C40 M40 Y40 K100,
violet C72 M86 Y0 K16, violet shade C82 M95 Y5 K42, composite greys, no flat K).

So v5 does not redraw anything. It copies REF.pdf's page content stream and
changes one thing.

```
python3 build/v5.py         # -> DIMA_Suit_Final_v5.pdf          (9 pages)
python3 build/v5preview.py  # -> DIMA_Suit_Final_v5_PREVIEW.pdf  (4 pages)
python3 build/v5svg.py      # -> DIMA_Suit_Final_v5_SOURCE.svg
python3 build/v5verify.py   # pre-flight + overlay/difference against REF.pdf
```

| module | role |
| --- | --- |
| `refstream.py` | parses the page content stream into painting ops, each carrying the byte span that produced it, plus its CTM, colour and active clip |
| `v5master.py` | the one correction, and the art-only variant used by the detail pages |
| `v5.py` | assembles the nine production sheets |
| `v5verify.py` | colour space, fonts, rasters, trim, overlay/difference, leg symmetry, band width |
| `v5preview.py` | the screen proof that documents the change |
| `v5svg.py` | editable sRGB vector source |

### Why the stream is edited as bytes

An earlier attempt read REF.pdf with `get_drawings()` and re-emitted the paths
through ReportLab. That silently drops the clipping: REF.pdf fills large
rectangles *through* a `W n` clip path, so re-emitting the rectangle alone
floods the sheet with black and violet. Copying the byte range instead keeps
the clip, the even-odd flags, the z-order and the transparency group intact —
the artwork cannot drift from the master because it is the same objects.

### The one change

The image-RIGHT front leg (the wearer's LEFT) carries an elongated tapering
triangle: violet band `op146` with the black gap `op147` inside it, running to
the ankle. The image-LEFT leg's band was cut off square at about 62 % of the
leg. The brief requires the same element on both legs, mirrored rather than
redrawn, so the left leg's short band (`ops 158-164`) is replaced by copies of
`op146`+`op147` under a mirror matrix.

The axis is the trousers panel's own axis of symmetry, solved from its clip
path — 382 points, best fit **X = 444.927 pt**, mean residual 0.0005 pt.

Verified:

| check | result |
| --- | --- |
| page 1 against REF.pdf | 99.486 % identical pixel for pixel |
| pixels changed outside the corrected leg | 0 |
| left leg against the mirrored right leg | 93.6 % identical (the rest is pattern seams, asymmetric by construction) |
| violet share of leg width | 41 % at the knee tapering to 7.5 % at the ankle — a band, not a lampas |
| violet runs across the leg | 2 at every height — the black gap is intact |

Back legs, side panels, chest, back, sleeves, logos and the legal block are
byte-identical to REF.pdf: they were never touched, so the back legs are not
mirrored from the front and the sleeves keep their different colours.

### Sheets

1 — master sheet: FRONT + BACK + LEFT SIDE + RIGHT SIDE at one scale
(420,7 × 297,7 mm) · 2-3 — front and back, 600 × 800 mm · 4-5 — side views,
300 × 800 mm · 6-7 — each sleeve as a separate part, front and back halves at
one scale · 8-9 — front and back legs, 800 × 600 mm.

Detail pages place page 1 as a Form XObject, so their artwork is the same
object rather than a copy; the manufacturer's sheet furniture is suppressed on
them so nothing bleeds into a crop.
