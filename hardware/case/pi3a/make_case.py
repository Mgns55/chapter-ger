"""Chapter case back (v5) adapted for a Raspberry Pi 3 Model A+.

- removes the four Pi Zero bosses on the back wall (upper left)
- adds four standoffs on top of the speaker-chamber lid for the Pi 3 A+
  (hole pattern 58 x 49 mm, same M2.5 heat-set inserts as the rest of the case)

Everything else (speaker chamber, amp block, USB-C mount, encoder mounts,
snap rim for the unchanged front cover) stays exactly as in the original file.
Usage: python3 make_case.py <original back STL> <output STL>
"""
import sys

import manifold3d as mf
import numpy as np
import trimesh

# Measured from chapter-case-back-v5.stl (case origin moved to 0,0,0)
ZERO_BOSSES = [(13.15, 65.89), (71.08, 65.90), (13.15, 88.90), (71.08, 88.90)]  # (x, z)
BOSS_CUT_RADIUS = 4.2          # bosses are 7 mm wide
BOSS_Y_FROM, BACK_WALL_Y = 60.0, 72.0
LID_TOP_Z = 58.0               # top of the speaker-chamber lid

# Pi 3 A+: board 65 x 56 mm, holes 3.5 mm from each edge -> 58 x 49 mm pattern
BOARD_X0, BOARD_Y0 = 8.0, 15.0   # board corner on the lid (clear of the rib at x 78..81)
BOARD_W, BOARD_D = 65.0, 56.0
HOLE_INSET = 3.5
STANDOFF_HEIGHT = 6.0          # board underside at z = 64
STANDOFF_RADIUS = 3.5          # 7 mm, like the original bosses
INSERT_HOLE_RADIUS = 1.55      # 3.1 mm, like the original bosses
INSERT_HOLE_DEPTH = 5.0


def to_manifold(mesh: trimesh.Trimesh) -> mf.Manifold:
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                               tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def to_trimesh(manifold: mf.Manifold) -> trimesh.Trimesh:
    mesh = manifold.to_mesh()
    return trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts, process=True)


def cylinder_z(x, y, z0, z1, r):
    return mf.Manifold.cylinder(z1 - z0, r, r, 64).translate([x, y, z0])


def cylinder_y(x, z, y0, y1, r):
    # cylinder along +z, rotated so its axis runs along +y
    return mf.Manifold.cylinder(y1 - y0, r, r, 64).rotate([-90, 0, 0]).translate([x, y0, z])


def pi_holes():
    xs = (BOARD_X0 + HOLE_INSET, BOARD_X0 + BOARD_W - HOLE_INSET)
    ys = (BOARD_Y0 + HOLE_INSET, BOARD_Y0 + BOARD_D - HOLE_INSET)
    return [(x, y) for x in xs for y in ys]


def main(src: str, dst: str) -> None:
    original = trimesh.load(src)
    offset = -original.bounds[0]
    original.apply_translation(offset)
    parts = sorted(original.split(only_watertight=False), key=lambda p: -len(p.faces))
    shell, extras = parts[0], parts[1:]
    assert shell.is_watertight, "main case body must be closed"

    body = to_manifold(shell)
    for x, z in ZERO_BOSSES:
        body = body - cylinder_y(x, z, BOSS_Y_FROM, BACK_WALL_Y + 0.2, BOSS_CUT_RADIUS)
    for x, y in pi_holes():
        standoff = cylinder_z(x, y, LID_TOP_Z - 0.5, LID_TOP_Z + STANDOFF_HEIGHT, STANDOFF_RADIUS)
        hole = cylinder_z(x, y, LID_TOP_Z + STANDOFF_HEIGHT - INSERT_HOLE_DEPTH,
                          LID_TOP_Z + STANDOFF_HEIGHT + 0.5, INSERT_HOLE_RADIUS)
        body = (body + standoff) - hole

    result = trimesh.util.concatenate([to_trimesh(body), *extras])
    result.apply_translation(-offset)          # back to the original file's position
    result.export(dst)
    print("written", dst, "watertight body:", to_trimesh(body).is_watertight)
    print("Pi 3 A+ standoffs at (x, y):", [(round(x, 1), round(y, 1)) for x, y in pi_holes()])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
