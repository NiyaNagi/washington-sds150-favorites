#!/usr/bin/env python3
"""
Validate the generated cover WITHOUT trusting the generator.

Everything here re-reads the gerber/Excellon files from disk with gerbonara
(a different implementation than the hand-rolled writer) and compares the
recovered geometry against RFH-2.brd.
"""
import warnings, json, math, sys, os
warnings.simplefilter('error', SyntaxWarning)   # any syntax complaint = failure

from gerbonara import LayerStack

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
spec = json.load(open(os.environ.get(
    'RFH2_COVER_SPEC', os.path.join(PROJ, 'build', 'cover_spec.json'))))
ls = LayerStack.open(os.environ.get(
    'RFH2_COVER_OUT', os.path.join(PROJ, 'build', 'cover_gerbers')))

fails, checks = [], []
def check(name, ok, detail=''):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(name)

# ---- 1. layer inventory ------------------------------------------------
want = {('top','copper'),('top','mask'),('top','silk'),
        ('bottom','copper'),('bottom','mask'),('bottom','silk'),
        ('mechanical','outline')}
got = set(ls.graphic_layers.keys())
check('all 7 gerber layers present & identified', want <= got, f'{sorted(got)}')
check('exactly one drill layer', len(list(ls.drill_layers)) == 1, f"{len(list(ls.drill_layers))}")

# ---- 2. drill file -----------------------------------------------------
drill_objs = [o for l in ls.drill_layers for o in l.objects]
holes = []
for o in drill_objs:
    ap = getattr(o, 'aperture', None)
    d = ap.diameter if ap is not None else None
    holes.append((round(o.x, 4), round(o.y, 4), round(d, 4)))
exp = sorted((round(x,4), round(y,4), round(d,4)) for x,y,d in spec['mount_holes'])
check('drill: 4 mounting holes recovered', sorted(holes) == exp,
      f'got {sorted(holes)}')
check('drill: every hole <= 6.3mm (JLCPCB plated max)',
      all(h[2] <= 6.3 for h in holes), f'max {max(h[2] for h in holes)}')

# ---- 3. outline layer: rectangle + 12 circles --------------------------
prof = ls[('mechanical','outline')]
arcs, lines = [], []
for o in prof.objects:
    t = type(o).__name__
    if t == 'Arc':   arcs.append(o)
    elif t == 'Line': lines.append(o)

check('outline: 4 straight segments (board rectangle)', len(lines) == 4, f'{len(lines)}')
check('outline: 12 arc objects (plunger cutouts)', len(arcs) == 12, f'{len(arcs)}')

# recover circle centres from the arcs and match to switch positions
recovered = []
for a in arcs:
    cx, cy = a.center
    r = math.dist((a.x1, a.y1), (cx, cy))
    recovered.append((round(cx,3), round(cy,3), round(2*r,3)))
recovered.sort()
expected = sorted((round(x,3), round(y,3), spec['plunger_dia'])
                  for x, y in spec['switches'].values())
check('plunger holes land exactly on the 12 switch centres',
      recovered == expected,
      f'\n    got {recovered}\n    exp {expected}')
check('plunger holes are all > 6.3mm, so correctly on outline not drill',
      all(r[2] > 6.3 for r in recovered), f'{recovered[0][2]}')

# board extents from the straight segments
xs = [v for l in lines for v in (l.x1, l.x2)]
ys = [v for l in lines for v in (l.y1, l.y2)]
check('board outline is 76 x 90 mm, matching the main PCB',
      (round(max(xs)-min(xs),3), round(max(ys)-min(ys),3)) == tuple(spec['board']),
      f'{max(xs)-min(xs)} x {max(ys)-min(ys)}')

# ---- 4. clearances -----------------------------------------------------
R = spec['plunger_dia']/2
edge_min = min(min(cx-R, spec['board'][0]-cx-R, cy-R, spec['board'][1]-cy-R)
               for cx, cy, _ in recovered)
check('plunger hole to board edge >= 1.0mm', edge_min >= 1.0, f'{edge_min:.3f} mm')

pair_min = min(math.dist((a[0],a[1]), (b[0],b[1])) - R*2
               for i,a in enumerate(recovered) for b in recovered[i+1:])
check('plunger hole to plunger hole >= 1.0mm', pair_min >= 1.0, f'{pair_min:.3f} mm')

mh_min = min(math.dist((cx,cy),(hx,hy)) - R - hd/2
             for cx,cy,_ in recovered for hx,hy,hd in spec['mount_holes'])
check('plunger hole to mounting hole >= 1.0mm', mh_min >= 1.0, f'{mh_min:.3f} mm')

# switch BODY is 12x12 -- bodies must not collide either (sanity on source board)
sw = list(spec['switches'].values())
body_min = min(max(abs(a[0]-b[0]), abs(a[1]-b[1])) - 12.0
               for i,a in enumerate(sw) for b in sw[i+1:])
check('switch bodies (12x12) do not overlap on the source board',
      body_min >= 0, f'{body_min:.3f} mm')

# ---- 5. silkscreen -----------------------------------------------------
silk = ls[('top','silk')]
sobjs = list(silk.objects)
regions = [o for o in sobjs if type(o).__name__ == 'Region']
strokes = [o for o in sobjs if type(o).__name__ in ('Line','Arc')]
check('silk: 4 filled arrow regions', len(regions) == spec['n_arrows'], f'{len(regions)}')
check('silk: stroke geometry present', len(strokes) > 100, f'{len(strokes)} segments')

widths = {round(o.aperture.diameter,3) for o in strokes if o.aperture}
check('silk line width >= 0.15mm (JLCPCB minimum)',
      all(w >= 0.15 for w in widths), f'{widths}')

# every silk object must sit inside the board
(sx0, sy0), (sx1, sy1) = silk.bounding_box()
check('silk entirely within board outline',
      sx0 >= 0 and sy0 >= 0 and sx1 <= spec['board'][0] and sy1 <= spec['board'][1],
      f'bbox ({sx0:.2f},{sy0:.2f})-({sx1:.2f},{sy1:.2f})')

# silk must not fall into a plunger hole (it would be routed away)
bad = []
for o in strokes:
    for px, py in [(o.x1,o.y1),(o.x2,o.y2)]:
        for cx, cy, _ in recovered:
            if math.dist((px,py),(cx,cy)) < R:
                bad.append((round(px,2),round(py,2)))
check('no silkscreen inside a plunger cutout', not bad, f'{bad[:5]}')

# ---- report ------------------------------------------------------------
print('=' * 68)
for name, ok, detail in checks:
    print(f'{"PASS" if ok else "FAIL"}  {name}')
    if detail and not ok:
        print(f'      {detail}')
    elif detail and ok and len(detail) < 40:
        print(f'      ({detail})')
print('=' * 68)
print(f'{len(checks)-len(fails)}/{len(checks)} passed')
sys.exit(1 if fails else 0)
