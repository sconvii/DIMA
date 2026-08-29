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
