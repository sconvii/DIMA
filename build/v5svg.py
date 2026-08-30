"""Editable vector source for v5.

The production PDF is DeviceCMYK; SVG has no CMYK colour space, so the export
carries the same geometry with each ink converted to its sRGB equivalent.  It
is the file to open for editing - the PDF stays the one to print.
"""
import re
import pymupdf

SRC = 'build/v5_master.pdf'
OUT = 'DIMA_Suit_Final_v5_SOURCE.svg'

# The inks, so the SVG names them the way the production file does.
INKS = [('#5A3B87', 'violet  C72 M86 Y0 K16'),
        ('#37175F', 'violet shade  C82 M95 Y5 K42'),
        ('#000000', 'rich black  C40 M40 Y40 K100'),
        ('#FFFFFF', 'white  C0 M0 Y0 K0')]


def build(src=SRC, out=OUT):
    doc = pymupdf.open(src)
    svg = doc[0].get_svg_image(text_as_path=True)
    note = ('<!-- DIMA - SQD K-3 Art - D. FEDOROV\n'
            '     Vector source for DIMA_Suit_Final_v5.pdf.\n'
            '     Geometry is REF.pdf verbatim; the only change is the\n'
            '     elongated triangle mirrored onto the image-LEFT front leg.\n'
            '     Print from the PDF - it is DeviceCMYK; this SVG is sRGB.\n'
            + '\n'.join(f'       {h}  =  {n}' for h, n in INKS)
            + ' -->\n')
    svg = re.sub(r'(<svg\b[^>]*>)', r'\1\n' + note, svg, count=1)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(svg)
    doc.close()
    return out, len(svg)


if __name__ == '__main__':
    p, n = build()
    print(f'{p}: {n/1024:.0f} KB')
