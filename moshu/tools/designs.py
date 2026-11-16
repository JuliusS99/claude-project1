"""Colour/texture designs for the Moshu card slingshot.

Every design is 2D art drawn on the OUTER face of a part (the face that lies on the
print bed). Coordinates are in "outside view": x is mirrored so text reads correctly
when you look at the finished part.

    python3 -I moshu/tools/designs.py sheet out.png    # concept sheet of all designs
"""
import random
import sys
from math import cos, pi, sin
from pathlib import Path

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.ops import unary_union

PARTS = Path(__file__).resolve().parent.parent / 'parts'
FACE_Z = {'frame': 0.7, 'grip': 0.7}  # just above the 0.5 mm edge fillet


def face(part):
    """Outer-face outline of a part, mirrored into outside view."""
    m = trimesh.load(PARTS / f'{part}.stl')
    p, _ = m.section(plane_origin=[0, 0, FACE_Z[part]], plane_normal=[0, 0, 1]).to_2D(to_2D=np.eye(4))
    g = unary_union(p.polygons_full)
    return affinity.scale(g, -1, 1, origin=(m.extents[0] / 2, 0))


# ---------- pattern helpers (all return shapely geometry) ----------
def lines(pts_list, w):
    return unary_union([LineString(p).buffer(w / 2, cap_style='round') for p in pts_list])


def ring(c, r, w):
    return Point(c).buffer(r + w / 2).difference(Point(c).buffer(r - w / 2))


def circuit(area, rng, w=0.7, step=3.0, n=26):
    """Random PCB traces with round pads."""
    minx, miny, maxx, maxy = area.bounds
    paths, pads = [], []
    for _ in range(n):
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if not area.contains(Point(x, y)):
            continue
        pts, d = [(x, y)], rng.choice([(0, 1), (1, 0), (0, -1), (-1, 0)])
        for _ in range(rng.randint(3, 9)):
            if rng.random() < 0.35:  # 45 degree bend
                d = rng.choice([(d[0] + d[1], d[1] - d[0]), (d[0] - d[1], d[1] + d[0])])
                d = (np.sign(d[0]), np.sign(d[1]))
            x, y = x + d[0] * step, y + d[1] * step
            pts.append((x, y))
        paths.append(pts)
        pads += [Point(pts[0]).buffer(1.1), Point(pts[-1]).buffer(1.1)]
    return unary_union([lines(paths, w)] + pads)


def hexgrid(area, r=2.6, w=0.7):
    minx, miny, maxx, maxy = area.bounds
    cells, dx, dy = [], r * 1.5, r * 3 ** 0.5
    for i in range(int((maxx - minx) / dx) + 3):
        for j in range(int((maxy - miny) / dy) + 3):
            cx, cy = minx + i * dx, miny + j * dy + (dy / 2 if i % 2 else 0)
            hexa = [(cx + r * cos(k * pi / 3), cy + r * sin(k * pi / 3)) for k in range(7)]
            cells.append(LineString(hexa).buffer(w / 2))
    return unary_union(cells)


def voronoi(area, rng, n=40, w=0.8):
    from scipy.spatial import Voronoi
    minx, miny, maxx, maxy = area.bounds
    pts = np.array([[rng.uniform(minx - 5, maxx + 5), rng.uniform(miny - 5, maxy + 5)] for _ in range(n)])
    v = Voronoi(pts)
    segs = [v.vertices[r] for r in v.ridge_vertices if -1 not in r]
    return lines(segs, w)


def scales(area, r=3.2, w=0.6):
    minx, miny, maxx, maxy = area.bounds
    arcs = []
    for j, y in enumerate(np.arange(maxy + r, miny - r, -r * 0.9)):
        for x in np.arange(minx - r, maxx + r, r * 1.6):
            cx = x + (r * 0.8 if j % 2 else 0)
            a = np.linspace(pi, 2 * pi, 18)  # lower half circle: scales point down
            arcs.append(np.c_[cx + r * np.cos(a), y + r * np.sin(a)])
    return lines(arcs, w)


def stripes(area, pitch=4.0, angle=45):
    minx, miny, maxx, maxy = area.bounds
    L = (maxx - minx) + (maxy - miny)
    bands = [box(minx + k, miny - L, minx + k + pitch / 2, maxy + L) for k in np.arange(-L, L, pitch)]
    return affinity.rotate(unary_union(bands), angle, origin=area.centroid)


def runes(origin, n, rng, size=3.2, gap=1.4, w=0.45, vertical=True):
    """Simple angular glyphs made from strokes between a 2x3 node grid."""
    nodes = [(x, y) for y in (0, 0.5, 1) for x in (0, 0.6)]
    out = []
    for k in range(n):
        strokes = [rng.sample(nodes, 2) for _ in range(rng.randint(2, 4))]
        ox, oy = origin
        if vertical:
            oy -= k * (size + gap)
        else:
            ox += k * (size * 0.6 + gap)
        out += [[(ox + a[0] * size, oy - a[1] * size), (ox + b[0] * size, oy - b[1] * size)] for a, b in strokes]
    return lines(out, w)


def vine(p0, p1, rng, amp=3.0, waves=4, leaf=2.2, w=0.7):
    t = np.linspace(0, 1, 200)
    d = np.subtract(p1, p0)
    nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    pts = np.array(p0) + np.outer(t, d) + np.outer(amp * np.sin(t * waves * 2 * pi), nrm)
    leaves = []
    for k, i in enumerate(range(12, 200, 18)):
        tang = pts[min(i + 1, 199)] - pts[i - 1]
        ang = np.degrees(np.arctan2(tang[1], tang[0])) + (50 if k % 2 else -50)
        e = affinity.scale(Point(0, 0).buffer(1), leaf, leaf * 0.4)
        e = affinity.translate(affinity.rotate(e, ang, origin=(0, 0)), *pts[i])
        leaves.append(affinity.translate(e, *(0.9 * leaf * np.array([cos(np.radians(ang)), sin(np.radians(ang))]))))
    return unary_union([LineString(pts).buffer(w / 2)] + leaves)


def stars(area, rng, n=45):
    minx, miny, maxx, maxy = area.bounds
    out = []
    for _ in range(n):
        c = (rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        s = rng.choice([0.45, 0.45, 0.6, 0.8, 1.6])
        if s > 1:  # four point star
            pts = [(c[0] + (s if k % 2 == 0 else s * 0.3) * cos(k * pi / 4), c[1] + (s if k % 2 == 0 else s * 0.3) * sin(k * pi / 4)) for k in range(8)]
            out.append(Polygon(pts))
        else:
            out.append(Point(c).buffer(s))
    return unary_union(out)


def sigil(c, r, w=0.6, k=7):
    """Magic circle: two rings, a k-pointed star polygon and tick marks."""
    pts = [(c[0] + r * 0.82 * sin(2 * pi * i / k), c[1] + r * 0.82 * cos(2 * pi * i / k)) for i in range(k)]
    star = [pts[(i * 3) % k] for i in range(k + 1)]
    ticks = [[(c[0] + r * 0.9 * sin(a), c[1] + r * 0.9 * cos(a)), (c[0] + r * 1.0 * sin(a), c[1] + r * 1.0 * cos(a))]
             for a in np.linspace(0, 2 * pi, 36, endpoint=False)]
    return unary_union([ring(c, r, w), ring(c, r * 0.82, w * 0.8), lines([star], w * 0.8), lines(ticks, w * 0.5)])


def text(s, xy, size, angle=0):
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    tp = TextPath((0, 0), s, size=size, prop=FontProperties(family='DejaVu Sans', weight='bold'))
    g = Polygon()
    for poly in tp.to_polygons():
        if len(poly) > 2:
            g = g.symmetric_difference(Polygon(poly))
    return affinity.translate(affinity.rotate(g, angle, origin=(0, 0)), *xy)


def eye(c, r):
    """Dragon eye: almond with slit pupil (pupil is left as base colour)."""
    almond = Point(0, r * 0.75).buffer(r).intersection(Point(0, -r * 0.75).buffer(r))
    almond = affinity.rotate(almond, 90, origin=(0, 0))
    pupil = affinity.scale(Point(0, 0).buffer(1), r * 0.12, r * 0.55)
    return affinity.translate(almond.difference(pupil), *c)


# ---------- designs ----------
# Each design returns {'frame': [(colour, geom), ...], 'grip': [...]} in outside view.
# A colour of None means a tactile groove (recessed, base colour).
def neon_circuit(f, g, rng):
    label = text('N30N', (36, 18), 5.5)
    return {'frame': [('#39ff14', circuit(f, rng, n=70).difference(label.buffer(1.5))), ('#00e5ff', label)],
            'grip': [(None, hexgrid(g)), ('#39ff14', circuit(g, rng, n=10))]}


def titan_mech(f, g, rng):
    panels = lines([[(33, 62), (68, 62)], [(26, 75), (26, 106)], [(48, 0), (48, 30)], [(0, 88), (26, 88)]], 0.8)
    plate = box(0, 97, 24, 106)
    return {'frame': [(None, panels), ('#ff7a00', plate.difference(stripes(plate, 5))),
                      ('#ff7a00', text('TX-07', (35, 21), 4.5))],
            'grip': [(None, stripes(g, 3.0, 30).intersection(box(0, 0, 34, 50))), ('#ff7a00', box(0, 62, 34, 66))]}


def xeno_biotech(f, g, rng):
    core = unary_union([Point(15, 90).buffer(3), ring((15, 90), 5.5, 0.9), ring((15, 90), 8, 0.6)])
    return {'frame': [('#9dff00', voronoi(f, rng, 55, 0.9).difference(Point(15, 90).buffer(9))), ('#ff2bd6', core)],
            'grip': [(None, voronoi(g, rng, 25, 0.8))]}


def elven_warden(f, g, rng):
    return {'frame': [('#d4af37', vine((7, 101), (30, 68), rng, amp=2.5, waves=2.5)),
                      ('#d4af37', vine((36, 16), (56, 16), rng, amp=2.0, waves=2, leaf=1.8)),
                      ('#d4af37', runes((63.1, 101), 20, rng, size=3.0))],
            'grip': [(None, scales(g, 3.0)), ('#d4af37', runes((26, 72), 12, rng))]}


def dragonscale(f, g, rng):
    claws = lines([[(36 + k * 4, 26), (42 + k * 4, 12)] for k in range(3)], 1.2)
    return {'frame': [('#a4161a', scales(f, 3.6, 1.1).intersection(box(33, 0, 68, 58)).difference(claws.buffer(0.8))),
                      ('#d4af37', eye((17, 91), 8)), ('#d4af37', ring((17, 91), 9, 0.8)), ('#d4af37', claws)],
            'grip': [(None, scales(g, 3.2)), ('#a4161a', box(0, 66, 34, 75))]}


def astral_sigil(f, g, rng):
    return {'frame': [('#e8f6ff', stars(f, rng, 60).difference(Point(17, 91).buffer(12.5))), ('#ffd166', sigil((17, 91), 11.5))],
            'grip': [('#e8f6ff', stars(g, rng, 18).difference(Point(8.5, 56).buffer(6.5))), ('#ffd166', sigil((8.5, 56), 5.8, k=5))]}


DESIGNS = {  # name: (function, base colour, short description)
    'NEON CIRCUIT': (neon_circuit, '#141414', 'Cyberpunk: Leiterbahnen in Neon'),
    'TITAN MECH': (titan_mech, '#5b6168', 'Military Sci-Fi: Panzerplatten + Warnstreifen'),
    'XENO BIOTECH': (xeno_biotech, '#2d1b3d', 'Alien: lebende Zellstruktur'),
    'ELVEN WARDEN': (elven_warden, '#2f5d3a', 'High Fantasy: Ranken + Runen'),
    'DRAGONSCALE': (dragonscale, '#151515', 'Dark Fantasy: Drachenschuppen + Auge'),
    'ASTRAL SIGIL': (astral_sigil, '#0b1a3a', 'Sci-Fi x Magie: Sternkarte + Siegel'),
}


def render(name, ax, seed=7):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    fn, base, desc = DESIGNS[name]
    f, g = face('frame'), face('grip')
    safe = {'frame': f.buffer(-1.2), 'grip': g.buffer(-1.2)}  # keep art off edges and holes
    art = fn(safe['frame'], safe['grip'], random.Random(seed))

    def draw(geom, color, dx, **kw):
        for poly in getattr(geom, 'geoms', [geom]):
            if poly.is_empty or poly.geom_type != 'Polygon':
                continue
            rings = [poly.exterior] + list(poly.interiors)
            verts = np.concatenate([np.asarray(r.coords) + [dx, 0] for r in rings])
            codes = np.concatenate([[MPath.MOVETO] + [MPath.LINETO] * (len(r.coords) - 2) + [MPath.CLOSEPOLY] for r in rings])
            ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor='none', **kw))

    for part, geom, dx in (('frame', f, 0), ('grip', g, 76)):
        draw(geom, base, dx)
        for color, a in art[part]:
            a = a.intersection(safe[part])
            draw(a, color or '#000000', dx, alpha=1 if color else 0.55)
    ax.set_xlim(-3, 113); ax.set_ylim(-3, 109); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(f'{name}\n{desc}', fontsize=11, fontweight='bold')


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if sys.argv[1] == 'sheet':
        fig, axs = plt.subplots(2, 3, figsize=(16, 11), facecolor='#eeeeee')
        for ax, name in zip(axs.flat, DESIGNS):
            render(name, ax)
        fig.text(0.5, 0.01, 'links Rahmen, rechts Griff (Außenseite)  |  Farbe = Inlay 0,6 mm  |  dunkle Linien = fühlbare Rillen',
                 ha='center', fontsize=11)
        plt.tight_layout(rect=(0, 0.03, 1, 1))
        plt.savefig(sys.argv[2], dpi=110)
