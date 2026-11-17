"""Build print files for a bite design and check that it stays printable and still works.

    python3 -I moshu/tools/build.py MAW            # one design
    python3 -I moshu/tools/build.py all            # every design

Writes moshu/out/<design>/ (gitignored, it contains the designer's geometry):
  frame_base.stl, frame_<n>_<colour>.stl, grip_base.stl, grip_<n>_<colour>.stl,
  checks.txt and preview.png. Load all STLs of one part at once in Bambu Studio and
  answer "yes" to "load as a single object with multiple parts", then pick a filament per part.
"""
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
import manifold3d as mf
import trimesh
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent))
import designs as D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INLAY = 0.6   # colour depth on the outer face = 3 layers at 0.2 mm
GROOVE = 0.7  # tactile groove depth (deeper than inlays: no coplanar faces)
DEPLOYED = (-100, 90)  # link angle, grip angle of the unfolded slingshot


def man(path):
    m = trimesh.load(path)
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def extrude(geom, z0, z1):
    rings = [np.asarray(r.coords)[:-1] for p in getattr(geom, 'geoms', [geom]) if p.geom_type == 'Polygon'
             for r in [p.exterior, *p.interiors]]
    return mf.CrossSection(rings, mf.FillRule.EvenOdd).extrude(z1 - z0).translate([0, 0, z0])


def pose(G, phi, psi):
    B = D.A + D.LINK * np.array([np.cos(np.radians(phi)), np.sin(np.radians(phi))])
    return G.translate([-D.GB[0], -D.GB[1], 0]).rotate([0, 0, psi]).translate([B[0], B[1], 0])


def save(m, path):
    """Export as a slicer will read it: float32 vertices merged, zero-area triangles from
    collapsed (zero-length) boolean edges removed."""
    g = m.to_mesh()
    t = trimesh.Trimesh(np.asarray(g.vert_properties, np.float32)[:, :3].astype(float), np.asarray(g.tri_verts), process=True)
    f = t.faces  # drop only triangles that collapsed (repeated vertex); collinear ones keep the surface closed
    t.update_faces((f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2]))
    t.remove_unreferenced_vertices()
    t.export(path)
    return trimesh.load(path)  # check the file itself


def colour_split(P, layers, face):
    """Split the outer face into colour inlays, then cut tactile grooves. Returns [(colour|'base', manifold)].
    Cutters reaching the part outline overshoot it by 0.5 mm so no cut face lies exactly on the part surface."""
    grooves = [extrude(g, -1, GROOVE) for c, g in layers if c is None]
    G = sum(grooves[1:], grooves[0]) if grooves else None
    def prep(g):  # overshoot the outline (reaching 0.02 mm inside it, never exactly on it) + seal hairlines
        return g.union(g.buffer(0.5).difference(face.buffer(-0.02))).buffer(0.03).buffer(-0.03)
    out, raw = [], []
    for c, g in layers:
        if c is None:
            continue
        piece = P ^ extrude(prep(g), -1, INLAY)
        out.append((c, piece - G if G else piece))
        raw.append(g)
    base = P - extrude(prep(D.unary_union(raw)), -1, INLAY) if raw else P  # one cutter: touching colours can't pinch
    return [('base', base - G if G else base)] + out


def motion_check(F, G, F0, G0):
    """Flood-fill the (link, grip) angle grid from the folded card; the unfolded pose must stay reachable."""
    phis, psis = range(-110, 15, 5), range(0, 360, 5)
    vol = {}
    for phi in phis:
        for psi in psis:
            vol[phi, psi] = ((F ^ pose(G, phi, psi)).volume(), (F0 ^ pose(G0, phi, psi)).volume())
    ok = {k for k, (new, orig) in vol.items() if orig < 10 and new <= orig + 0.5}
    start, seen, todo = (0, 180), {(0, 180)}, deque([(0, 180)])
    while todo:
        phi, psi = todo.popleft()
        for n in ((phi + 5, psi), (phi - 5, psi), (phi, (psi + 5) % 360), (phi, (psi - 5) % 360)):
            if n in ok and n not in seen:
                seen.add(n)
                todo.append(n)
    orig_free = {k for k, (_, orig) in vol.items() if orig < 0.5}
    return start in ok and DEPLOYED in seen, len(seen), len(orig_free - seen)


def build(name):
    s, base, desc, art = D.art(name)
    out = ROOT / 'out' / name.lower().replace(' ', '_')
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob('*.stl'):
        f.unlink()
    F0, G0 = man(D.PARTS / 'frame.stl'), man(D.PARTS / 'grip.stl')
    F = F0 + extrude(s['teeth'], 0, 10)
    G = G0 - extrude(s['grip_cut'], -1, 11)

    grip_layers = [(c, D.grip_unpose(g)) for c, g in art['grip']]
    files, palette = {}, {}
    grip_face = D.load('grip')[0].difference(s['grip_cut'])
    for part, P, layers, b, face in (('frame', F, art['frame'], base[0], s['frame']), ('grip', G, grip_layers, base[1], grip_face)):
        for i, (c, m) in enumerate(colour_split(P, layers, face)):
            colour = b if c == 'base' else c
            fn = out / (f'{part}_base.stl' if c == 'base' else f'{part}_{i}_{colour[1:]}.stl')
            files[fn.name] = save(m, fn)
            palette[fn.name] = colour

    # ---------- checks ----------
    checks = []
    def check(label, ok, detail=''):
        checks.append(('OK  ' if ok else 'FAIL') + f'  {label}' + (f'  ({detail})' if detail else ''))

    card_new = [F.slice(z) + pose(G, 0, 180).slice(z) for z in (0.7, 5.0, 9.3)]
    card_old = [F0.slice(z) + pose(G0, 0, 180).slice(z) for z in (0.7, 5.0, 9.3)]
    close = lambda c: c.offset(0.5, mf.JoinType.Round).offset(-0.5, mf.JoinType.Round)  # ignore the seam between the parts
    extra = max((close(n) - close(o).offset(0.02, mf.JoinType.Miter)).area() for n, o in zip(card_new, card_old))
    same_box = all(np.allclose(n.bounds(), o.bounds(), atol=0.05) for n, o in zip(card_new, card_old))
    check('Karte: Außenkontur unverändert, nichts steht über', same_box and extra < 0.05, f'{extra:.3f} mm² zusätzlich')
    check('Karte: Dicke unverändert', np.isclose(F.bounding_box()[5], F0.bounding_box()[5]) and np.isclose(G.bounding_box()[5], G0.bounding_box()[5]))
    frame_face0 = D.load('frame')[0]
    window = box(0, 0, D.MOUTH_X, 106).difference(frame_face0)  # holes/openings left of the seam
    check('Zähne ragen nicht ins Abzugsfenster', s['teeth'].intersection(window.buffer(0.2)).area < 1e-6)
    thin = max([g.difference(g.buffer(-0.39).buffer(0.39)).area / max(g.area, 1e-9) for p in art for _, g in art[p]] + [0])
    check(f'Druckbar: keine Details unter {D.MIN_W} mm', thin < 0.02, f'{thin:.1%} Fläche grenzwertig')
    grooves = [g for p in art for c, g in art[p] if c is None]
    check('Druckbar: Rillen überbrückbar (< 2,5 mm breit)', all(g.buffer(-1.25).is_empty for g in grooves))
    grip2d = D.load('grip')[0].difference(s['grip_cut'])
    sliver = grip2d.difference(grip2d.buffer(-0.4).buffer(0.4)).intersection(s['grip_cut'].buffer(1.0))
    sliver = sliver.buffer(-0.02).buffer(0.02).area  # ignore sub-micron numeric residue
    check(f'Druckbar: keine Wände unter {D.MIN_W} mm im Griff', sliver < 0.05, f'{sliver:.3f} mm²')
    check('Alle Teile wasserdicht (slicerfest)', all(t.is_watertight for t in files.values()))
    reach, n_reach, lost = motion_check(F, G, F0, G0)
    check('Mechanik: Griff klappt von Karte bis Pistolenstellung frei', reach, f'{n_reach} Stellungen erreichbar, {lost} Original-Stellungen blockiert')

    report = [f'{name} – {desc}', ''] + checks + ['', 'Dateien und Farben:'] + [f'  {k:28s} {v}' for k, v in palette.items()]
    report += [f'  knob (Original-Teil)         {base[2]}', '', 'Unverändert aus dem Original drucken: slider, spring, cover_plate, nut_plate, screw_plate, knob']
    (out / 'checks.txt').write_text('\n'.join(report) + '\n')
    preview(out, palette)
    print('\n'.join(report[:len(checks) + 2]))
    return all(c.startswith('OK') for c in checks)


def preview(out, palette):
    """Outside view (from below) of: folded card, biting, unfolded."""
    states = [((0, 180), 0), ((0, 135), -120), (DEPLOYED, -250)]  # view is mirrored: negative x shows to the right
    lines = []
    for (phi, psi), dx in states:
        B = D.A + D.LINK * np.array([np.cos(np.radians(phi)), np.sin(np.radians(phi))])
        lines.append(f'translate([{dx},0,0]) {{')
        for fn, c in palette.items():
            imp = f'color("{c}") import("{out / fn}");'
            if fn.startswith('grip'):
                imp = f'translate([{B[0]},{B[1]},0]) rotate([0,0,{psi}]) translate([{-D.GB[0]},{-D.GB[1]},0]) ' + imp
            lines.append('  ' + imp)
        lines.append('}')
    scad = out / 'preview.scad'
    scad.write_text('\n'.join(lines) + '\n')
    subprocess.run(['xvfb-run', '-a', 'openscad', '-o', str(out / 'preview.png'), '--imgsize=2400,1100', '--viewall',
                    '--autocenter', '--projection=o', '--camera=0,0,0,180,0,180,0', '--colorscheme=Tomorrow', str(scad)],
                   check=True, capture_output=True)
    subprocess.run(['convert', str(out / 'preview.png'), '-trim', '-bordercolor', '#f8f8f8', '-border', '30', str(out / 'preview.png')], check=True)
    scad.unlink()


if __name__ == '__main__':
    names = list(D.DESIGNS) if sys.argv[1] == 'all' else [sys.argv[1]]
    results = {n: build(n) for n in names}
    print('\n' + '  '.join(f'{n}: {"OK" if ok else "FAIL"}' for n, ok in results.items()))
    sys.exit(0 if all(results.values()) else 1)
