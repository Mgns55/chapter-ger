"""Chapter Pro, variant A ("Radio") - parametric printable case.

Hardware: Raspberry Pi 3 A+ on a PiSugar 3 Plus (5000 mAh, 65 x 56 mm), 3.12" SSD1322
OLED (UN312-5664-7: PCB 100.5 x 33.5 mm, holes 95 x 28.5 mm), Dayton Audio ND90-4 (rear-mounted behind a grille),
MAX98357A, 2 x KY-040 on the top.

Final coordinates: X = width (left -> right, seen from the front), Y = depth
(front face y = 0), Z = height (bottom z = 0). The STL files are written in
print orientation (no supports needed).

Parts
  chapter-pro-gehaeuse.stl         body, printed front face down
  chapter-pro-rueckwand.stl        back panel with Pi/PiSugar holder, outer face down
  chapter-pro-lautsprecherring.stl clamp ring for the ND90-4

Usage: python3 make_chapter_pro.py [output dir]
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient

# ---------------------------------------------------------------- dimensions
W, H = 224.0, 135.0           # outer width / height
BODY_D = 101.0                # body depth (front panel + open back)
PANEL_T = 4.0                 # back panel thickness  -> total depth 105 mm
FRONT_T = 4.0                 # front wall
WALL = 3.0                    # side, top, bottom, divider
OUTER_R = 8.0                 # rounded edges (along the depth axis)
INNER_R = 3.0

LEFT_CAV = (WALL, WALL, 110.0, H - WALL)            # speaker chamber (x0, z0, x1, z1)
RIGHT_CAV = (113.0, WALL, W - WALL, H - WALL)       # electronics

# back-panel screw columns (M3 heat-set inserts, M3x10 screws)
COLUMNS = [(8.0, 8.0), (8.0, H - 8.0), (111.5, 8.0), (111.5, H - 8.0), (W - 8.0, 8.0), (W - 8.0, H - 8.0)]
COLUMN_R = 5.5
M3_INSERT_R, M3_INSERT_DEPTH = 2.0, 7.0      # 4.0 mm hole for M3 x 5.7 inserts
M25_INSERT_R = 1.55                           # 3.1 mm hole, as in the original Chapter case

# speaker: Dayton ND90-4, frame 104 mm, cut-out 85 mm, rear-mounted
SPK = (56.5, 67.5)                            # centre (x, z)
GRILLE_R, GRILLE_HOLE_R, GRILLE_PITCH = 41.5, 1.8, 5.2
SPK_BOSS_OFFSET = 41.0                        # bosses on the diagonals, r = 58 mm
SPK_BOSS_R, SPK_BOSS_H = 4.5, 4.0
SPK_LIP = (52.5, 54.0, 2.0)                   # centring lip r_in, r_out, height (frame 104 mm)

# OLED 3.12" SSD1322 (drawing UN312-5664-7, seen from the front, pins on the right):
# PCB 100.5 x 33.5, holes 4 x 3.2 mm on 95 x 28.5, glass 89.5 x 29.8 (1.4 mm below the
# PCB top, 5.0 mm from the left edge), active area 76.78 x 19.18 (5.1 mm below the
# PCB top, 12.36 mm from the right edge).
OLED = (167.0, 92.0)                          # centre of the active area (x, z)
OLED_WIN = (80.0, 23.0)                       # window at the front face (visible area 78.8 x 21.2)
OLED_CHAMFER = 3.0                            # window grows by 3 mm per side towards the inside
OLED_PCB = (100.5, 33.5)
OLED_PCB_CENTRE = (OLED[0] + (100.5 / 2 - 12.36 - 76.78 / 2) * -1.0,   # active area 0.5 mm left of PCB centre
                   OLED[1] - (33.5 / 2 - 5.1 - 19.18 / 2))             # and 2.06 mm above it
OLED_HOLES = [(OLED_PCB_CENTRE[0] + dx, OLED_PCB_CENTRE[1] + dz) for dx in (-47.5, 47.5) for dz in (-14.25, 14.25)]
OLED_GLASS = (OLED_PCB_CENTRE[0] - 100.5 / 2 + 5.0, OLED_PCB_CENTRE[1] + 33.5 / 2 - 1.4 - 29.8,
              OLED_PCB_CENTRE[0] - 100.5 / 2 + 5.0 + 89.5, OLED_PCB_CENTRE[1] + 33.5 / 2 - 1.4)
OLED_BOSS_R, OLED_BOSS_H = 3.0, 2.6           # PCB sits 2.6 mm behind the front wall (glass + tape)
OLED_PILOT_R = 1.05                           # 2.1 mm pilot for 2.5 x 6 mm self-tapping screws

# encoders on the top
KNOBS = [("Menü", 144.5), ("Lautstärke", 189.5)]
KNOB_Y = 50.0
# KY-040 mounting copied from the original Chapter case (chapter-case-back-v5.stl, same 3 mm top):
# 21 mm knob recess, 13.4 mm through hole, two posts with M2.5 inserts 17.5 mm long, one rib.
KNOB_RECESS_R, KNOB_RECESS_DEPTH = 10.5, 1.75
KNOB_HOLE_R = 6.72
KY040_POSTS = ((8.3, -5.8), (8.8, 11.1))      # (dx, dy) from the encoder axis
KY040_POST_R, KY040_POST_LEN = 3.5, 17.5
KY040_RIB = (8.1, 13.1, -9.55, 12.45)          # dx0, dx1, dy0, dy1
# Print support: the case prints front-down, so rib and posts would hang ~40 mm above the
# front wall. A solid web from the front wall up to the rib carries them (no slicer supports)
# and stiffens the mount. It stops 4 mm short of the post ends so the encoder board and its
# angled pin header stay clear.
KY040_WEB_DX = (7.8, 13.1)                      # covers the rib and the lower tip of the first post
KY040_WEB_CLEAR = 4.0
VOLUME_ICON_Y = 28.0                           # centre of the engraved volume icon (in front of the knob)
ENGRAVE = 1.0
FONT = FontProperties(family="DejaVu Serif")

# Pi 3 A+ + PiSugar 3 Plus stack (both 65 x 56 mm) lies battery-down on the back panel:
# four corner guides + two loops for a hook-and-loop strap, ports stay free on all edges
PI_CENTRE = (167.0, 42.0)                     # (x, z)
PI_SIZE = (65.0, 56.0)
PI_GUIDE_H, PI_GUIDE_LEG, PI_GUIDE_T = 12.0, 9.0, 2.0

# back panel openings
USB = (135.0, 105.0)                          # USB-C panel-mount socket (x, z)

# 3.5 mm headphone socket (YACSEJAO D-type panel cable: flange 31 x 26 mm, round front 20 mm,
# body ~20 mm, 42 mm deep) on the right side, half-way up. It is mounted from the INSIDE:
# only the round black front shows through a round hole, no screws visible. The flange sits
# in a 1 mm pocket (wall 2 mm there) and a printed clamp, screwed to two pads, holds it.
JACK = (55.0, 88.0)                           # (y, z) on the right side wall
JACK_FRONT_R = 10.3                           # 20.6 mm round hole for the 20 mm front
JACK_FLANGE = (31.6, 26.6)                    # pocket for the flange (y, z), 0.3 mm play per side
JACK_POCKET_DEPTH = 1.0
JACK_PAD_OFFSET = 21.0                        # clamp pads left/right of the flange (y offset)
JACK_PAD_R, JACK_PAD_H = 4.5, 7.0             # pads stick 7 mm into the case, M3 insert inside
JACK_CLAMP_RIM_H = 7.0                        # clamp rim reaches from the pad tops to the flange

# MAX98357A breakout: two M2.5 domes like the original Chapter case (holes 13.2 mm apart),
# on the electronics side of the divider, near the front and the speaker cable hole
# Close to the front: the case prints front-down, so low domes need (almost) no support.
AMP_DOMES = ((14.0, 32.0), (27.2, 32.0))      # (y, z)
AMP_DOME_R, AMP_DOME_LEN = 3.5, 8.0

# No power button: the PiSugar's own button is used.

NAME_TEXT = "Franz Pro"                       # engraved on the bottom
NAME_CAP = 5.0
SEG = 64


# ---------------------------------------------------------------- helpers
def cs_from_shapely(poly) -> mf.CrossSection:
    poly = orient(poly, 1.0)
    rings = [np.asarray(poly.exterior.coords[:-1])]
    rings += [np.asarray(r.coords[:-1]) for r in poly.interiors]
    return mf.CrossSection([r.tolist() for r in rings])


def rrect(x0, z0, x1, z1, r):
    return box(x0, z0, x1, z1).buffer(-r).buffer(r, resolution=16)


def prism_y(poly, y0, y1) -> mf.Manifold:
    """Extrude a 2-D shape in the (x, z) plane along +y from y0 to y1."""
    return cs_from_shapely(poly).extrude(y1 - y0).rotate([90, 0, 0]).translate([0, y1, 0])


def cyl_y(x, z, y0, y1, r, seg=SEG):
    return mf.Manifold.cylinder(y1 - y0, r, r, seg).rotate([-90, 0, 0]).translate([x, y0, z])


def cyl_z(x, y, z0, z1, r, seg=SEG):
    return mf.Manifold.cylinder(z1 - z0, r, r, seg).translate([x, y, z0])


def cyl_x(y, z, x0, x1, r, seg=SEG):
    return mf.Manifold.cylinder(x1 - x0, r, r, seg).rotate([0, 90, 0]).translate([x0, y, z])


def union(parts):
    parts = [p for p in parts if not p.is_empty()]
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add) if parts else mf.Manifold()


def text_shape(text, size):
    path = TextPath((0, 0), text, size=size, prop=FONT)
    shape = None
    for ring in path.to_polygons():
        if len(ring) < 3:
            continue
        poly = Polygon(ring).buffer(0)
        shape = poly if shape is None else shape.symmetric_difference(poly)
    return shape


def cap_size(cap_height):
    return cap_height / (TextPath((0, 0), "M", size=10, prop=FONT).get_extents().height / 10)


def text_solid(text, size, depth):
    """Text as a solid, letters in the xy plane, centred on x = 0, baseline y = 0, z 0..depth."""
    shape = text_shape(text, size)
    minx, _, maxx, _ = shape.bounds
    parts = []
    for geom in getattr(shape, "geoms", [shape]):
        parts.append(cs_from_shapely(geom).extrude(depth))
    return union(parts).translate([-(minx + maxx) / 2, 0, 0])


def volume_icon_solid(depth):
    """Speaker symbol followed by four bars of growing height, centred on (0, 0), z 0..depth.
    Bars stand on the front edge (-y) and grow towards the back, read from the front."""
    shapes = [
        box(-12.0, -1.6, -9.6, 1.6),                                     # speaker body
        Polygon([(-9.6, -1.6), (-6.0, -4.2), (-6.0, 4.2), (-9.6, 1.6)]),  # speaker cone
    ]
    bar_w, gap, base = 2.0, 1.7, -4.2
    for i, height in enumerate((2.4, 4.4, 6.4, 8.4)):
        x0 = -3.0 + i * (bar_w + gap)
        shapes.append(box(x0, base, x0 + bar_w, base + height))
    parts = [cs_from_shapely(shape).extrude(depth) for shape in shapes]
    icon = union(parts)
    return icon.translate([-(-12.0 + (-3.0 + 3 * (bar_w + gap) + bar_w)) / 2, 0, 0])


def to_trimesh(m: mf.Manifold) -> trimesh.Trimesh:
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts, process=True)


# ---------------------------------------------------------------- body
def build_body() -> mf.Manifold:
    body = prism_y(rrect(0, 0, W, H, OUTER_R), 0, BODY_D)
    for cav in (LEFT_CAV, RIGHT_CAV):
        body -= prism_y(rrect(*cav, INNER_R), FRONT_T, BODY_D + 1)

    # screw columns for the back panel
    body += union([cyl_y(x, z, FRONT_T - 0.1, BODY_D, COLUMN_R) for x, z in COLUMNS])
    body -= union([cyl_y(x, z, BODY_D - M3_INSERT_DEPTH, BODY_D + 1, M3_INSERT_R) for x, z in COLUMNS])

    # speaker grille (hex pattern), decorative groove, mounting bosses, centring lip
    sx, sz = SPK
    holes = []
    rows = int(GRILLE_R / (GRILLE_PITCH * 0.866)) + 1
    for row in range(-rows, rows + 1):
        dz = row * GRILLE_PITCH * 0.866
        shift = GRILLE_PITCH / 2 if row % 2 else 0.0
        for col in range(-10, 11):
            dx = col * GRILLE_PITCH + shift
            if (dx * dx + dz * dz) ** 0.5 + GRILLE_HOLE_R <= GRILLE_R:
                holes.append(cyl_y(sx + dx, sz + dz, -1, FRONT_T + 1, GRILLE_HOLE_R, 20))
    body -= union(holes)
    groove = cyl_y(sx, sz, -1, 0.8, 50.5, 128) - cyl_y(sx, sz, -2, 2, 49.5, 128)
    body -= groove
    lip = cyl_y(sx, sz, FRONT_T - 0.1, FRONT_T + SPK_LIP[2], SPK_LIP[1], 128) - \
        cyl_y(sx, sz, FRONT_T - 1, FRONT_T + SPK_LIP[2] + 1, SPK_LIP[0], 128)
    body += lip
    spk_bosses = [(sx + a * SPK_BOSS_OFFSET, sz + b * SPK_BOSS_OFFSET) for a in (-1, 1) for b in (-1, 1)]
    body += union([cyl_y(x, z, FRONT_T - 0.1, FRONT_T + SPK_BOSS_H, SPK_BOSS_R) for x, z in spk_bosses])
    body -= union([cyl_y(x, z, FRONT_T + SPK_BOSS_H - 5.5, FRONT_T + SPK_BOSS_H + 1, M3_INSERT_R)
                   for x, z in spk_bosses])

    # OLED window with inner chamfer, clamp bosses
    ox, oz = OLED
    ww, wh = OLED_WIN
    c = OLED_CHAMFER
    front = mf.Manifold.cube([ww, 0.01, wh]).translate([ox - ww / 2, -0.5, oz - wh / 2])
    back = mf.Manifold.cube([ww + 2 * c, 0.01, wh + 2 * c]).translate([ox - ww / 2 - c, FRONT_T + 0.1, oz - wh / 2 - c])
    window = mf.Manifold.batch_hull([front, back])
    window += mf.Manifold.cube([ww, 1.2, wh]).translate([ox - ww / 2, -0.6, oz - wh / 2])
    body -= window
    # standoffs at the module's four holes, trimmed where they would touch the glass
    gx0, gz0, gx1, gz1 = OLED_GLASS
    glass_keepout = prism_y(box(gx0 - 0.4, gz0 - 0.4, gx1 + 0.4, gz1 + 0.4), FRONT_T - 0.5, FRONT_T + 10)
    bosses = union([cyl_y(x, z, FRONT_T - 0.1, FRONT_T + OLED_BOSS_H, OLED_BOSS_R) for x, z in OLED_HOLES])
    body += bosses - glass_keepout
    body -= union([cyl_y(x, z, FRONT_T + OLED_BOSS_H - 5.0, FRONT_T + OLED_BOSS_H + 1, OLED_PILOT_R, 24)
                   for x, z in OLED_HOLES])

    # name engraved on the bottom (0.6 mm), readable when the radio is tipped backwards
    name = text_solid(NAME_TEXT, cap_size(NAME_CAP), 1.6).mirror([0, 1, 0])   # letter "up" = towards the front
    body -= name.translate([W / 2, BODY_D / 2 + cap_size(NAME_CAP) * 0.36, -1.0])

    # headphone socket, mounted from the inside of the right side wall
    jy, jz = JACK
    inner = W - WALL
    fy, fz = JACK_FLANGE
    pocket = (mf.Manifold.cube([JACK_POCKET_DEPTH + 1, fy, fz]).translate([inner - 1, jy - fy / 2, jz - fz / 2]))
    body -= pocket
    body -= cyl_x(jy, jz, inner - 2, W + 1, JACK_FRONT_R, 128)
    # clamp pads; teardrop-shaped towards -y because the wall prints upright with +y up
    pads = []
    for dy in (-JACK_PAD_OFFSET, JACK_PAD_OFFSET):
        pad = cyl_x(jy + dy, jz, inner - JACK_PAD_H, inner + 0.1, JACK_PAD_R, 48)
        tip = mf.Manifold.cube([JACK_PAD_H + 0.1, 0.01, 1.0]).translate(
            [inner - JACK_PAD_H, jy + dy - JACK_PAD_R * 2 ** 0.5, jz - 0.5])
        pads.append(mf.Manifold.batch_hull([pad, tip]))
    body += union(pads)
    body -= union([cyl_x(jy + dy, jz, inner - JACK_PAD_H - 1, inner - 1.0, M3_INSERT_R, 32)
                   for dy in (-JACK_PAD_OFFSET, JACK_PAD_OFFSET)])

    # knobs on the top: holes, thinned wall under the nut, engraved labels
    top_inner = H - WALL
    for text, kx in KNOBS:
        body -= cyl_z(kx, KNOB_Y, H - KNOB_RECESS_DEPTH, H + 1, KNOB_RECESS_R, 96)
        body -= cyl_z(kx, KNOB_Y, top_inner - 1, H + 1, KNOB_HOLE_R, 96)
        # KY-040 mount. The top wall prints upright with +y up, so the rib runs the full post
        # length and the posts are teardrops pointing -y: no supports needed.
        dx0, dx1, dy0, dy1 = KY040_RIB
        bottom = top_inner - KY040_POST_LEN
        rib = mf.Manifold.cube([dx1 - dx0, dy1 - dy0, KY040_POST_LEN - 1.0]).translate(
            [kx + dx0, KNOB_Y + dy0, bottom + 1.0])
        parts = [rib.translate([0, 0, 0.1])]
        for dx, dy in KY040_POSTS:
            post = cyl_z(kx + dx, KNOB_Y + dy, bottom, top_inner + 0.1, KY040_POST_R, 48)
            tip = mf.Manifold.cube([1.0, 0.01, KY040_POST_LEN + 0.1]).translate(
                [kx + dx - 0.5, KNOB_Y + dy - KY040_POST_R * 2 ** 0.5, bottom])
            parts.append(mf.Manifold.batch_hull([post, tip]))
        wx0, wx1 = KY040_WEB_DX
        web = mf.Manifold.cube([wx1 - wx0, KNOB_Y + dy0 - FRONT_T + 0.2, KY040_POST_LEN - KY040_WEB_CLEAR + 0.1]).translate(
            [kx + wx0, FRONT_T - 0.1, bottom + KY040_WEB_CLEAR])
        parts.append(web)
        body += union(parts)
        body -= union([cyl_z(kx + dx, KNOB_Y + dy, bottom - 1, bottom + 5.0, M25_INSERT_R, 32)
                       for dx, dy in KY040_POSTS])
    # no words on the top: only a small volume icon in front of the volume knob
    body -= volume_icon_solid(ENGRAVE + 1).translate([KNOBS[1][1], VOLUME_ICON_Y, H - ENGRAVE])

    # rubber-feet recesses (10 mm, 1 mm deep)
    for x in (20.0, W - 20.0):
        for y in (15.0, BODY_D - 12.0):
            body -= cyl_z(x, y, -1, 1.0, 5.5)


    # amplifier domes on the divider (teardrops pointing -y: the divider prints upright, +y up)
    divider_face = RIGHT_CAV[0]
    domes = []
    for dy, dz in AMP_DOMES:
        dome = cyl_x(dy, dz, divider_face - 0.1, divider_face + AMP_DOME_LEN, AMP_DOME_R, 48)
        tip = mf.Manifold.cube([AMP_DOME_LEN + 0.1, 0.01, 1.0]).translate(
            [divider_face - 0.1, dy - AMP_DOME_R * 2 ** 0.5, dz - 0.5])
        domes.append(mf.Manifold.batch_hull([dome, tip]))
    body += union(domes)
    body -= union([cyl_x(dy, dz, divider_face + AMP_DOME_LEN - 5.0, divider_face + AMP_DOME_LEN + 1, M25_INSERT_R, 32)
                   for dy, dz in AMP_DOMES])

    # cable pass-through speaker chamber -> electronics (seal with hot glue)
    body -= cyl_x(45.0, 20.0, 105.0, 118.0, 3.0)
    return body


# ---------------------------------------------------------------- back panel
def build_back_panel() -> mf.Manifold:
    y_in, y_out = BODY_D, BODY_D + PANEL_T
    panel = prism_y(rrect(0, 0, W, H, OUTER_R), y_in, y_out)

    # locating / sealing lips that drop into both openings
    lips = []
    for cav in (LEFT_CAV, RIGHT_CAV):
        outer = rrect(*cav, INNER_R).buffer(-0.4, join_style=2)
        inner = outer.buffer(-1.6, join_style=2)
        lips.append(prism_y(outer.difference(inner), y_in - 3.0, y_in + 0.1))
    lips = union(lips) - union([cyl_y(x, z, y_in - 4, y_in + 1, COLUMN_R + 0.6) for x, z in COLUMNS])
    panel += lips

    # screw holes with counterbore on the outside
    panel -= union([cyl_y(x, z, y_in - 4, y_out + 1, 1.7) for x, z in COLUMNS])
    panel -= union([cyl_y(x, z, y_out - 2.0, y_out + 1, 3.3) for x, z in COLUMNS])

    # Pi 3 A+ / PiSugar holder: L-shaped corner guides (0.5 mm play) and two strap loops
    px, pz = PI_CENTRE
    hw, hh = PI_SIZE[0] / 2 + 0.5, PI_SIZE[1] / 2 + 0.5
    guides = []
    for sx_ in (-1, 1):
        for sz_ in (-1, 1):
            cx, cz = px + sx_ * hw, pz + sz_ * hh          # inner corner of the guide
            leg = PI_GUIDE_LEG
            t = PI_GUIDE_T
            a = box(min(cx, cx + sx_ * t), min(cz - sz_ * leg, cz + sz_ * t),
                    max(cx, cx + sx_ * t), max(cz - sz_ * leg, cz + sz_ * t))
            b = box(min(cx - sx_ * leg, cx + sx_ * t), min(cz, cz + sz_ * t),
                    max(cx - sx_ * leg, cx + sx_ * t), max(cz, cz + sz_ * t))
            guides.append(prism_y(a.union(b), y_in - PI_GUIDE_H, y_in + 0.1))
    panel += union(guides)
    loops = []
    for sx_ in (-1, 1):                                    # strap runs vertically over the stack
        x = px + sx_ * 16.0
        for z in (pz - hh - 6.0, pz + hh + 6.0):
            loop = prism_y(rrect(x - 8.0, z - 2.5, x + 8.0, z + 2.5, 1.0), y_in - 5.5, y_in + 0.1)
            loop -= prism_y(box(x - 6.5, z - 3.0, x + 6.5, z + 3.0), y_in - 3.0, y_in + 1.0)
            loops.append(loop)
    panel += union(loops)

    # USB-C panel-mount socket (flange 25 x 8 mm, threaded holes 17 mm apart, Ø 3 mm):
    # flange sits in a 2 mm recess on the outside, socket body through a 10.5 x 5.5 cut-out,
    # screws from the inside
    ux, uz = USB
    panel -= prism_y(rrect(ux - 12.9, uz - 4.4, ux + 12.9, uz + 4.4, 2.5), y_out - 2.0, y_out + 1)
    panel -= prism_y(rrect(ux - 5.25, uz - 2.75, ux + 5.25, uz + 2.75, 1.2), y_in - 1, y_out + 1)
    panel -= union([cyl_y(ux + dx, uz, y_in - 1, y_out + 1, 1.7, 32) for dx in (-8.5, 8.5)])

    # ventilation slots above the Pi
    for i in range(6):
        x = 165.0 + i * 8.0
        panel -= prism_y(rrect(x - 1.5, 80.0, x + 1.5, 102.0, 1.49), y_in - 1, y_out + 1)
    return panel


# ---------------------------------------------------------------- loose parts
def build_speaker_ring() -> mf.Manifold:
    """Clamp ring, printed ear plate down, pressing rim up. Local origin = speaker centre."""
    plate = [mf.Manifold.cylinder(3.0, 53.0, 53.0, 128)]
    for a in (-1, 1):
        for b in (-1, 1):
            ear = mf.Manifold.cylinder(3.0, 5.5, 5.5, 48).translate([a * SPK_BOSS_OFFSET, b * SPK_BOSS_OFFSET, 0])
            plate.append(ear)
    plate = mf.Manifold.batch_hull(plate)
    rim = mf.Manifold.cylinder(7.0, 53.0, 53.0, 128)
    ring = (plate + rim) - mf.Manifold.cylinder(20, 45.0, 45.0, 128).translate([0, 0, -5])
    for a in (-1, 1):
        for b in (-1, 1):
            ring -= mf.Manifold.cylinder(20, 1.7, 1.7, 32).translate([a * SPK_BOSS_OFFSET, b * SPK_BOSS_OFFSET, -5])
    return ring


def build_jack_clamp() -> mf.Manifold:
    """Clamp for the headphone socket: plate on the pads, rim pressing the flange to the wall.
    Printed plate down, rim up. Slide it over the cable before fitting the socket."""
    off = JACK_PAD_OFFSET
    plate = mf.Manifold.batch_hull([
        mf.Manifold.cylinder(3.0, 14.0, 14.0, 96),
        mf.Manifold.cylinder(3.0, 5.5, 5.5, 48).translate([off, 0, 0]),
        mf.Manifold.cylinder(3.0, 5.5, 5.5, 48).translate([-off, 0, 0]),
    ])
    rim = mf.Manifold.cylinder(3.0 + JACK_CLAMP_RIM_H, 12.5, 12.5, 96)
    clamp = (plate + rim) - mf.Manifold.cylinder(20, 10.75, 10.75, 96).translate([0, 0, -5])
    for x in (-off, off):
        clamp -= mf.Manifold.cylinder(20, 1.7, 1.7, 32).translate([x, 0, -5])
    return clamp


def build_display_clamps() -> mf.Manifold:
    """Four 14 x 8 x 2.5 mm clamps with a slotted M2.5 hole, laid out for printing."""
    clamps = []
    for i in range(4):
        tab = cs_from_shapely(rrect(0, 0, 14.0, 8.0, 1.5)).extrude(2.5)
        slot = cs_from_shapely(rrect(2.2, 2.7, 7.2, 5.3, 1.29)).extrude(4).translate([0, 0, -1])
        clamps.append((tab - slot).translate([i * 18.0, 0, 0]))
    return union(clamps)


# ---------------------------------------------------------------- export
def to_print_body(m):          # front face on the bed: new z = y
    return m.rotate([90, 0, 0]).translate([0, H, 0])


def to_print_panel(m):         # outer face on the bed: new z = (BODY_D + PANEL_T) - y
    return m.rotate([-90, 0, 0]).translate([0, 0, BODY_D + PANEL_T])


def main(out_dir="."):
    os.makedirs(out_dir, exist_ok=True)
    parts = {
        "chapter-pro-gehaeuse.stl": to_print_body(build_body()),
        "chapter-pro-rueckwand.stl": to_print_panel(build_back_panel()),
        "chapter-pro-lautsprecherring.stl": build_speaker_ring(),
        "chapter-pro-kopfhoererhalter.stl": build_jack_clamp(),
    }
    for name, m in parts.items():
        mesh = to_trimesh(m)
        mesh.apply_translation([-mesh.bounds[0][0], -mesh.bounds[0][1], -mesh.bounds[0][2]])
        mesh.export(os.path.join(out_dir, name))
        size = mesh.bounds[1] - mesh.bounds[0]
        print(f"{name:36s} {size[0]:6.1f} x {size[1]:6.1f} x {size[2]:6.1f} mm  "
              f"{mesh.volume / 1000:6.1f} cm3  watertight={mesh.is_watertight}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
