"""Extract the parts of the MakerWorld "Moshu card-style slingshot" 3MF into STL files.

Usage:  python3 moshu/tools/extract_3mf.py <download.3mf> moshu/parts
The original geometry belongs to its designer, so the STLs stay local (gitignored).
Parts come out in print orientation (outer face on the bed, z=0), moved to the origin.
"""
import os, struct, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np

# 3MF object id -> name, identified by shape (see README)
NAMES = {'2': 'frame', '4': 'grip', '6': 'cover_plate', '8': 'spring',
         '10': 'nut_plate', '12': 'screw_plate', '14': 'knob', '16': 'slider'}
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PATH = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path'


def mat(s):  # 3MF uses row vectors: p' = [x y z 1] @ M
    v = list(map(float, s.split()))
    M = np.eye(4)
    M[:3, :3] = np.array(v[:9]).reshape(3, 3)
    M[3, :3] = v[9:]
    return M


def main(src, out):
    os.makedirs(out, exist_ok=True)
    z = zipfile.ZipFile(src)
    model = ET.fromstring(z.read('3D/3dmodel.model'))
    comps = {}
    for o in model.find('m:resources', NS):
        c = o.find('m:components/m:component', NS)
        comps[o.get('id')] = (c.get(PATH).lstrip('/'), mat(c.get('transform')))
    for item in model.find('m:build', NS):
        oid = item.get('objectid')
        path, Mc = comps[oid]
        mesh = ET.fromstring(z.read(path)).find('.//m:mesh', NS)
        V = np.array([[float(v.get(k)) for k in 'xyz'] for v in mesh.find('m:vertices', NS)])
        T = np.array([[int(t.get(k)) for k in ('v1', 'v2', 'v3')] for t in mesh.find('m:triangles', NS)])
        M = Mc @ mat(item.get('transform'))
        V = (np.c_[V, np.ones(len(V))] @ M)[:, :3]
        if np.linalg.det(M[:3, :3]) < 0:  # mirrored transform flips winding
            T = T[:, ::-1]
        V -= V.min(0)
        name = NAMES.get(oid, f'object_{oid}')
        with open(os.path.join(out, name + '.stl'), 'wb') as f:
            f.write(b'\0' * 80 + struct.pack('<I', len(T)))
            for a, b, c in V[T]:
                n = np.cross(b - a, c - a)
                n /= np.linalg.norm(n) or 1
                f.write(struct.pack('<12fH', *n, *a, *b, *c, 0))
        print(f'{name:12s} {np.round(V.max(0), 2)} mm, {len(T)} triangles')


if __name__ == '__main__':
    main(*sys.argv[1:3])
