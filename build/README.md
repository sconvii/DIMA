# DIMA — SQD K-3 Art production layout

Rebuilds `DIMA_Suit_Final_Print.pdf` (production, DeviceCMYK, all vector) and
`DIMA_Suit_Final_Print_Check.pdf` (screen proof) from the two source files in
the repository root.

```
pip install pymupdf pillow numpy reportlab fonttools
python3 build/build.py     # -> DIMA_Suit_Final_v2.pdf        (8 pages)
python3 build/check.py     # -> DIMA_Suit_Final_v2_Check.pdf  (4 pages)
python3 build/verify.py    # pre-flight: colour space, fonts, rasters, bleed
python3 build/compare.py   # scanline fidelity check against DIMA.jpeg
```

`DIMA_Suit_Final_Print.pdf` is the first release and is kept untouched;
the scripts now build the corrected v2.

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
