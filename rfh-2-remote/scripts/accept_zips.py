#!/usr/bin/env python3
"""Unpack each upload zip into a clean dir and check it the way a fab would."""
import warnings, zipfile, tempfile, os, math, sys
warnings.simplefilter('ignore')
from gerbonara import LayerStack

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
UPLOAD = os.path.join(PROJ, 'jlcpcb-upload')

ZIPS = {'cover':     os.path.join(UPLOAD, 'JLCPCB-1-RFH-2-cover.zip'),
        'mainboard': os.path.join(UPLOAD, 'JLCPCB-2-RFH-2-mainboard.zip'),
        'bottom':    os.path.join(UPLOAD, 'JLCPCB-3-RFH-2-bottom.zip')}

REQUIRED = [('top','copper'), ('bottom','copper'), ('top','mask'),
            ('bottom','mask'), ('top','silk'), ('mechanical','outline')]

fails = []
def ck(tag, name, ok, detail=''):
    print(f'  {"PASS" if ok else "FAIL"}  {name}' + (f'   ({detail})' if detail else ''))
    if not ok: fails.append(f'{tag}: {name}')

for tag, zp in ZIPS.items():
    print(f'\n=== {tag}  ({os.path.getsize(zp)/1024:.0f} kB) ===')
    d = tempfile.mkdtemp()
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        z.extractall(d)

    ck(tag, 'no directories inside zip (flat)', not any(n.endswith('/') for n in names))
    ck(tag, 'no stray non-CAM files', not any(
        n.lower().endswith(('.txt','.md','.pdf','.png','.gbrjob')) for n in names),
        f'{len(names)} files')

    ls = LayerStack.open(d)
    ids = set(ls.graphic_layers.keys())
    for layer in REQUIRED:
        ck(tag, f'layer present: {layer[0]} {layer[1]}', layer in ids)

    ndrill = sum(1 for l in ls.drill_layers for _ in l.objects)
    ck(tag, 'drill file found and non-empty', ndrill > 0, f'{ndrill} holes')

    dias = [o.aperture.diameter for l in ls.drill_layers for o in l.objects
            if getattr(o, 'aperture', None)]
    if dias:
        ck(tag, 'all drills within JLCPCB 0.3-6.3mm',
           min(dias) >= 0.3 and max(dias) <= 6.3,
           f'{min(dias):.2f}-{max(dias):.2f} mm')

    # outline layer must be a closed-ish profile with sane extents
    prof = ls[('mechanical','outline')]
    (x0,y0),(x1,y1) = prof.bounding_box()
    w, h = x1-x0, y1-y0
    ck(tag, 'outline extents ~76 x 90 mm', abs(w-76) < 0.5 and abs(h-90) < 0.5,
       f'{w:.2f} x {h:.2f}')
    ck(tag, 'board >= JLCPCB 5x5mm minimum', w >= 5 and h >= 5)

    # everything must live inside the outline
    for lid in ids:
        if lid == ('mechanical','outline'):
            continue
        try:
            (a,b),(c_,e) = ls[lid].bounding_box()
        except Exception:
            continue
        inside = a >= x0-0.6 and b >= y0-0.6 and c_ <= x1+0.6 and e <= y1+0.6
        ck(tag, f'{lid[0]} {lid[1]} within outline', inside)

print('\n' + '='*60)
if fails:
    print('FAILURES:')
    for f in fails: print('  -', f)
    sys.exit(1)
print('both archives pass acceptance checks')
