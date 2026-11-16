"""Bite designs for the Moshu card slingshot.

The grip hangs on a 12.2 mm link (nut_plate/screw_plate) from frame pivot A=(28, 6).
Folded, it fills the free corner of the frame (card). Unfolding swings it around the link
pivot B near the bottom, so the frame/grip seam opens like a jaw: hinge at the bottom,
mouth at the top. Teeth are added to the frame edge; matching sockets are cut into the
grip, swept along the opening motion so nothing can jam.

All geometry is in part coordinates (print orientation, outer face on the bed) and in the
"card pose" (grip folded). Drawings are mirrored to show the outside.

    python3 -I moshu/tools/designs.py sheet out.png
"""
import random
import sys
from math import cos, pi, sin
from pathlib import Path

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

PARTS = Path(__file__).resolve().parent.parent / 'parts'
A, LINK, GB = np.array([28.0, 6.0]), 12.2, (28.0, 69.0)  # frame pivot, link length, grip pivot (grip coords)
MOUTH_X, MOUTH_Y = 34.0, (14.0, 54.0)                      # straight part of the seam that gets teeth
OPEN_PATH = np.linspace(180, 140, 21)                       # grip angle while unfolding (link at 0 deg)


def _slice(m, z):
    p, _ = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]).to_2D(to_2D=np.eye(4))
    return unary_union(p.polygons_full)


def load(part, skin=2.0):
    """Outer-face outline and the zone where >= `skin` mm of solid material is behind the face."""
    m = trimesh.load(PARTS / f'{part}.stl')
    outline = _slice(m, 0.7)
    solid = outline
    for z in np.arange(0.9, skin + 0.01, 0.2):
        solid = solid.intersection(_slice(m, z))
    return outline, solid.buffer(-1.0)


def grip_pose(g, phi=0.0, psi=180.0):
    B = A + LINK * np.array([cos(np.radians(phi)), sin(np.radians(phi))])
    return affinity.translate(affinity.rotate(g, psi, origin=GB), B[0] - GB[0], B[1] - GB[1])


def grip_unpose(g, phi=0.0, psi=180.0):
    B = A + LINK * np.array([cos(np.radians(phi)), sin(np.radians(phi))])
    return affinity.rotate(affinity.translate(g, GB[0] - B[0], GB[1] - B[1]), -psi, origin=GB)


# ---------- teeth (frame side, card coords) ----------
def teeth(style, rng):
    y0, y1 = MOUTH_Y
    x = MOUTH_X - 0.6  # root overlaps the frame edge
    out = []
    if style == 'square':
        for y in np.arange(y0, y1 - 3, 7.0):
            out.append(box(x, y, MOUTH_X + 3.5, y + 3.5))
        return out
    pitch, h, w = {'fang': (5.7, 4.2, 5.0), 'serrated': (3.4, 2.6, 3.2), 'saw': (6.6, 4.6, 6.4),
                   'mimic': (5.0, 4.0, 4.6), 'cilia': (4.0, 5.2, 1.5)}[style]
    for y in np.arange(y0, y1 - w + 0.01, pitch):
        hh, ww = h, w
        if style == 'mimic':
            hh, ww = rng.uniform(2.2, 4.6), rng.uniform(3.2, 4.8)
        if style == 'fang' and len(out) in (1, 5):
            hh = h * 1.25  # two canines
        tip = (MOUTH_X + hh, y + ww / 2)
        if style == 'cilia':  # thin spike with rounded tip
            out.append(unary_union([Polygon([(x, y), tip, (x, y + ww)]), Point(tip).buffer(0.45)]))
        elif style == 'serrated':
            out.append(Polygon([(x, y), (MOUTH_X + 0.3, y), tip, (MOUTH_X + 0.3, y + ww), (x, y + ww)]))
        else:
            out.append(Polygon([(x, y), tip, (x, y + ww)]))
    return out


def build_shapes(style, rng):
    frame, frame_safe = load('frame')
    grip, grip_safe = load('grip')
    T = unary_union(teeth(style, rng))
    sockets = unary_union([grip_unpose(T, 0, psi) for psi in OPEN_PATH]).buffer(0.3)  # grip coords
    grip_new = grip.difference(sockets)
    return {'frame': frame.union(T), 'frame_safe': frame_safe, 'teeth': T,
            'grip': grip_new, 'grip_safe': grip_safe.intersection(grip_new.buffer(-1.0)),
            'grip_teeth': grip_pose(grip_new).intersection(box(MOUTH_X, MOUTH_Y[0] - 2, MOUTH_X + 5, MOUTH_Y[1] + 2))}


# ---------- art helpers ----------
def lines(pts_list, w):
    return unary_union([LineString(p).buffer(w / 2) for p in pts_list])


def ring(c, r, w):
    return Point(c).buffer(r + w / 2).difference(Point(c).buffer(r - w / 2))


def wave(x0, x1, y, amp, n, w):
    t = np.linspace(x0, x1, 120)
    return LineString(np.c_[t, y + amp * np.sin((t - x0) / (x1 - x0) * n * 2 * pi)]).buffer(w / 2)


def voronoi(area, rng, n, w):
    from scipy.spatial import Voronoi
    minx, miny, maxx, maxy = area.bounds
    v = Voronoi(np.array([[rng.uniform(minx - 5, maxx + 5), rng.uniform(miny - 5, maxy + 5)] for _ in range(n)]))
    return lines([v.vertices[r] for r in v.ridge_vertices if -1 not in r], w)


def slit_eye(c, r, iris):
    pupil = affinity.scale(Point(0, 0).buffer(1), r * 0.16, r * 0.62)
    return affinity.translate(Point(0, 0).buffer(r).difference(pupil), *c)


def dots(area, rng, n, r):
    minx, miny, maxx, maxy = area.bounds
    return unary_union([Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy)).buffer(rng.uniform(*r)) for _ in range(n)])


KNOB = (63.3, 79.5)  # band post hole in the frame head - becomes the eye
BALLS = [(45.9, 53.7), (45.9, 43.7), (45.9, 33.7)]  # ammo holes in card pose


# ---------- designs: art in card coords; None colour = tactile groove ----------
def maw(s, rng):
    gums = box(38.6, 11, 42.6, 57)
    return {'frame': [('#ffcc00', ring(KNOB, 5.6, 2.6)), ('#7a0c14', voronoi(box(34, 75, 68, 106), rng, 14, 0.7)),
                      ('#efe6d2', s['teeth'])],
            'grip': [('#a4161a', gums), ('#efe6d2', s['grip_teeth']),
                     (None, unary_union([wave(36, 66, y, 1.2, 3, 0.8) for y in range(10, 70, 6)]))]}


def megalodon(s, rng):
    gills = lines([[(14 + k * 4.5, 9), (16.5 + k * 4.5, 18), (14 + k * 4.5, 27)] for k in range(4)], 1.0)
    return {'frame': [('#efefef', s['teeth']), (None, gills), ('#0a0a0a', Point(55, 93).buffer(3.2)),
                      ('#ffffff', Point(54, 94.2).buffer(0.9)), (None, lines([[(40, 100), (47, 97)], [(41, 103), (49, 99.5)]], 0.7))],
            'grip': [(None, lines([[(37, 64), (48, 70)], [(37, 60), (50, 67)]], 0.7))]}


def mimic(s, rng):
    planks = unary_union([box(-5, y, 75, y + 0.8) for y in range(4, 106, 8)])
    keyhole = unary_union([Point(51, 89).buffer(1.7), box(50.3, 83.5, 51.7, 89)])
    tongue = unary_union([LineString([(35, 20), (38, 30), (36.5, 40), (39.5, 48)]).buffer(2.4)])
    return {'frame': [(None, planks), ('#d4af37', box(44, 81, 58, 97).difference(keyhole)),
                      ('#d4af37', unary_union([box(22, 57, 26, 106), box(28, 0, 32, 30)])), ('#efe6d2', s['teeth'])],
            'grip': [(None, planks), ('#e75480', tongue), ('#efe6d2', s['grip_teeth']), ('#d4af37', box(34, 62, 68, 66))]}


def flytrap(s, rng):
    inside = unary_union([box(34, 8, 43, 60), box(24, 6, 34, 30)])
    veins = lines([[(34, y), (34 + 12 * cos(a), y + 12 * sin(a))] for y in range(12, 58, 7) for a in (-0.4, 0, 0.4)]
                  + [[(34, y), (34 - 10, y + d)] for y, d in ((10, -3), (18, 0), (26, 3))], 0.6)
    return {'frame': [('#c1121f', box(24, 6, 34, 30)), ('#d9ed92', s['teeth']),
                      ('#80b918', voronoi(box(34, 75, 68, 106), rng, 10, 0.6)), (None, veins)],
            'grip': [('#c1121f', box(34, 8, 43, 60)), ('#80b918', veins), ('#e0fbfc', dots(inside, rng, 10, (0.5, 0.9)))]}


def croc9(s, rng):
    scutes = unary_union([box(-5, y, 75, y + 0.7) for y in range(3, 106, 7)] + [box(x, -5, x + 0.7, 110) for x in range(5, 70, 8)])
    piston = lines([[(13, 12), (31, 12)], [(13, 22), (31, 22)], [(13, 12), (13, 22)], [(31, 17), (33, 17)]], 0.8)
    return {'frame': [(None, scutes.intersection(box(34, 75, 68, 106))), ('#ff2a2a', slit_eye(KNOB, 6.5, True)),
                      ('#c9d1d9', s['teeth']), (None, piston),
                      ('#ff7a00', box(36, 99, 66, 105).difference(unary_union([box(36 + k, 98, 38 + k, 106) for k in range(0, 30, 4)])))],
            'grip': [(None, scutes), ('#c9d1d9', s['grip_teeth'])]}


def beartrap(s, rng):
    chain = unary_union([ring((12 + (k % 2) * 0, 12 + k * 4.5), 2.2, 0.8) for k in range(4)])
    hazard = box(34, 60, 68, 66)
    rivets = unary_union([Point(p).buffer(1.1) for p in ((38, 79), (66, 79), (38, 102), (66, 102))])
    return {'frame': [('#b8c1c8', s['teeth']), (None, chain), ('#b8c1c8', rivets),
                      ('#8a3b12', dots(box(34, 75, 68, 106), rng, 12, (0.4, 1.0)))],
            'grip': [('#b8c1c8', s['grip_teeth']), ('#ffd000', hazard.difference(unary_union([box(34 + k, 58, 36 + k, 68) for k in range(0, 34, 4)]))),
                     (None, ring((40.2, 6), 4.5, 0.8))]}


DESIGNS = {  # name: (art fn, tooth style, (frame, grip, knob) base colours, one-liner)
    'MAW': (maw, 'fang', ('#1d1b1b', '#1d1b1b', '#9dff00'), 'Horror-Monster: Fangzähne, Zahnfleisch, Glow-Auge'),
    'MEGALODON': (megalodon, 'serrated', ('#65737e', '#f2f2f2', '#0a0a0a'), 'Hai: Sägezähne, weißer Bauch, fühlbare Kiemen'),
    'MIMIC': (mimic, 'mimic', ('#6b4226', '#6b4226', '#d4af37'), 'D&D-Truhe: Planken, Goldschloss, Zunge'),
    'FLYTRAP': (flytrap, 'cilia', ('#2f6b2a', '#2f6b2a', '#c1121f'), 'Venusfalle: Wimpern-Stacheln, roter Kelch'),
    'CROC-9': (croc9, 'square', ('#3d4349', '#3d4349', '#ff2a2a'), 'Mecha-Kroko: Zinnenzähne, Panzer, LED-Auge'),
    'BEAR TRAP': (beartrap, 'saw', ('#2b2b2b', '#2b2b2b', '#b8c1c8'), 'Tellereisen: Stahlzähne, Kette, Warnstreifen'),
}


def art(name, seed=3):
    fn, style, base, desc = DESIGNS[name]
    rng = random.Random(seed)
    s = build_shapes(style, rng)
    a = fn(s, rng)
    gsafe = grip_pose(s['grip_safe'])
    clip = {'frame': lambda g, c: g.intersection(s['frame_safe'].union(s['teeth']) if c else s['frame_safe']),
            'grip': lambda g, c: g.intersection(gsafe.union(s['grip_teeth']) if c else gsafe)}
    return s, base, desc, {p: [(c, clip[p](g, c)) for c, g in a[p]] for p in a}


def render(name, axs):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    s, base, desc, a = art(name)

    def draw(ax, geom, color, alpha=1.0, edge='none'):
        geom = affinity.scale(geom, -1, 1, origin=(34, 0))  # outside view
        for poly in getattr(geom, 'geoms', [geom]):
            if poly.is_empty or poly.geom_type != 'Polygon':
                continue
            rings = [poly.exterior] + list(poly.interiors)
            verts = np.concatenate([np.asarray(r.coords) for r in rings])
            codes = np.concatenate([[MPath.MOVETO] + [MPath.LINETO] * (len(r.coords) - 2) + [MPath.CLOSEPOLY] for r in rings])
            ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor=edge, lw=0.6, alpha=alpha))

    for ax, psi, label in ((axs[0], 180, f'{name}: zu (Karte)'), (axs[1], 135, 'offen (Biss)')):
        move = (lambda g: grip_pose(grip_unpose(g), 0, psi))
        draw(ax, s['frame'], base[0], edge='#777')
        draw(ax, grip_pose(s['grip'], 0, psi), base[1], edge='#777')
        draw(ax, Point(KNOB).buffer(3.2), base[2])
        for c, g in a['frame']:
            draw(ax, g, c or '#000000', 1 if c else 0.5)
        for c, g in a['grip']:
            draw(ax, move(g), c or '#000000', 1 if c else 0.5)
        ax.set_xlim(-48, 72) if psi != 180 else ax.set_xlim(-26, 94); ax.set_ylim(-40, 108); ax.set_aspect('equal'); ax.axis('off')
        ax.set_title(label, fontsize=13, fontweight='bold' if psi == 180 else 'normal', loc='left')
    axs[0].text(0, -0.02, desc, transform=axs[0].transAxes, fontsize=11, va='top')


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if sys.argv[1] == 'sheet':
        fig, axs = plt.subplots(3, 4, figsize=(16, 19), facecolor='#ececec')
        for i, name in enumerate(DESIGNS):
            render(name, axs[i // 2, (i % 2) * 2:(i % 2) * 2 + 2])
        fig.text(0.5, 0.01, 'Außenansicht  |  Zähne = echte Geometrie am Rahmen, Taschen im Griff aus der Schwenkbewegung berechnet  |  '
                 'Farbe = Inlay 0,6 mm  |  dunkle Linien = fühlbare Rillen', ha='center', fontsize=11)
        plt.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.04, wspace=0.02, hspace=0.12)
        plt.savefig(sys.argv[2], dpi=100)
