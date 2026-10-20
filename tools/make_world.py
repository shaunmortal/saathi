"""Writes worlds/opd.wbt: an Indian district-hospital OPD hall with signage, seating, a crowd of skinned humans and Saathi.

Hall interior: x in [-9, 9], y in [-6, 6], ceiling at 3.2 m. Doors and signs face into the hall.
Crowd and robot positions are shared with controllers/saathi/saathi.py through controllers/saathi/scene.json.
"""
import json, math, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Run settings: python tools/make_world.py --mode=baseline --perception=vision --goal=Lab --unmapped=1 --out=../../out/x --every=0.1 --until=60
RUN = dict(mode="saathi", perception="gt", goal="Radiology", out="../../out/run", every="0.1", until="60", unmapped="0", fall="0", lost="0", report="60", robots="1", quit="1", floors="1", tour="")
RUN.update(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
MOTIONS = ROOT / "motions"

# Walkers loop between their waypoints at the animation's natural speed; standers hold a pose.
# The stock Robert skin stands 2.27 m tall on our depth camera: scaled to ~1.75 m. His stride shrinks with him, so he walks
# at 0.77 x the animation's 1.22 m/s (feet do not slide). The boy (Anthony, 1.33 m) and the girl (Sophia, 1.46 m) are as they are.
SCALE = {"Robert": 0.77}
SPEED = lambda model: round(1.22 * SCALE.get(model, 1.0), 3)
# Sandra is left out: her left arm stays in the T-pose with the stock BVH player.
WALKERS = [  # name, model, skin tone, path
    ("W1", "Robert", "_brown", [(0.3, 3.8), (7.5, 3.8)]),
    ("W2", "Sophia", "_brown", [(7.5, -5.0), (-7.0, -5.0)]),
    ("W3", "Anthony", "_brown", [(-3.0, -5.2), (-3.0, 4.2)]),
    ("W4", "Robert", "", [(3.6, -2.0), (3.6, 4.4)]),
    ("W5", "Robert", "_brown", [(6.8, -1.1), (-6.8, -1.1)]),
]
STANDERS = [  # name, model, skin tone, (x, y), look-at
    ("T1", "Sophia", "", (-1.0, 3.25), (-1.0, 1.9)),   # a pair talking 1.35 m apart, right across the direct line to Radiology
    ("T2", "Robert", "_brown", (-1.0, 1.9), (-1.0, 3.25)),
    ("Q1", "Sophia", "_brown", (-0.8, 5.15), (-0.8, 7.0)),
    ("Q2", "Anthony", "", (-0.8, 4.4), (-0.8, 7.0)),
]
ROUTE = [(-7.6, 0.0), (-3.6, -0.5), (1.4, -0.4), (3.2, 2.4), (5.0, 4.7)]  # keeps 1.2 m+ from the talking pair
# Furniture footprints (centre x, centre y, size x, size y) for the planner, and where each department is reached from inside the hall.
OBSTACLES = [(-6.3, 4.9, 3.5, 0.8), (-0.8, 5.8, 2.2, 0.35), (1.5, -3.0, 2.6, 0.5), (1.5, -4.0, 2.6, 0.5), (6.2, -3.0, 2.6, 0.5),
             (6.2, -4.0, 2.6, 0.5), (7.6, -5.6, 0.4, 0.4), (-2.25, 5.65, 0.9, 0.4), (-6.4, -5.4, 0.6, 0.6)]
# Things in the hall that are NOT on Saathi's map: it has to see them (depth camera) to avoid them. (x, y, size x, size y)
UNMAPPED = [("wet floor sign", (-4.6, 0.3), (0.45, 0.5)), ("cardboard box", (2.0, 3.1), (0.7, 0.55))] if RUN["unmapped"] == "1" else []
GOALS = {"Radiology": (5.0, 4.9), "Emergency": (-5.0, -4.9), "Lab": (2.5, -4.9), "Wards & Lift": (8.0, 1.5), "Registration": (-6.3, 3.9)}
# --floors=2: a lift shaft in the right wall takes Saathi to the first floor (Blood Bank, ICU, OT, Wards). The cabin is 1.4 x 1.6 m at (8.3, 1.5).
FLOOR2 = RUN["floors"] == "2"
Z2 = 3.28                                   # first-floor floor level (the hall's ceiling slab is 3.20-3.28)
LIFT = dict(cabin=(8.3, 1.5), lobby=(6.6, 1.5), z2=Z2, door_x=7.52, door_y=(1.125, 1.875), door_open=0.75)
SHAFT = [(8.25, 0.55, 1.7, 0.12), (8.25, 2.45, 1.7, 0.12), (7.4, 0.2, 0.1, 1.1), (7.4, 2.8, 0.1, 1.1)]  # shaft side walls and the front wall beside the doors
GOALS2 = {"Blood Bank": (-3.0, 4.9), "ICU": (-4.0, -4.9), "OT": (3.0, -4.9), "Wards": (4.5, 4.9), "Nurse Station": (0.0, 3.9)}
OBSTACLES2 = [(0.0, 4.9, 3.4, 0.8), (-4.0, -2.0, 2.6, 0.5), (-4.0, -3.0, 2.6, 0.5), (6.8, -4.6, 1.0, 2.2), (-7.8, 4.0, 1.2, 1.6)] + SHAFT  # nurse counter, chairs, a stretcher, stairs
WALKERS2 = [("W6", "Robert", "", [(-6.0, -1.0), (6.0, -1.0)]), ("W7", "Sophia", "_brown", [(-2.0, 3.0), (-2.0, -4.5)])]
STANDERS2 = [("N1", "Sophia", "", (0.0, 5.15), (0.0, 7.0)), ("V1", "Anthony", "_brown", (-6.6, 1.0), (-8.0, 1.0))]  # nurse at the counter, a visitor reading the board
GOALS1 = {"Pharmacy": (-2.2, 4.3), "Wards & Lift": LIFT["lobby"]}  # ground-floor goals that exist only with the lift (scene["goals"] stays as the benchmarks know it)
# Where people walk to (doors, counters, the water cooler, the entrance): the memory's guesses for where a lost child went.
PLACES = {**GOALS, "water cooler": (7.1, -5.0), "pharmacy": (-0.8, 4.0), "entrance": (-8.3, 0.0)}
# Saathi Parivaar scenario (--lost=1): a father at the registration counter; his son wanders off to the water cooler while
# Saathi drives to Radiology, and at --report seconds the father asks the help desk. The boy is the only child in the hall.
ACTORS = []  # name, model, skin tone, start, look-at, [(start time, path)]: each has a walking and a standing body
LOST = None
if RUN["lost"] == "1":
    WALKERS[1] = ("W2", "Sophia", "_brown", [(6.0, -5.0), (-7.0, -5.0)])  # leaves the water cooler free
    WALKERS[2] = ("W3", "Sophia", "", WALKERS[2][3])
    STANDERS[3] = ("Q2", "Robert", "", STANDERS[3][3], STANDERS[3][4])
    ACTORS = [("L", "Anthony", "_brown", (-5.3, 3.7), (-5.3, 5.0), [(6.0, [(-3.0, 0.8), (0.5, -1.9), (4.0, -2.2), (8.2, -2.3), (8.2, -4.6), (7.4, -4.95)])]),
              ("P", "Robert", "_brown", (-6.1, 3.9), (-6.1, 5.0), [])]
    LOST = dict(query="a photo of a small child in a red shirt", said="Mera beta kho gaya. Laal t-shirt, chhota sa hai.", child=True, who="L", parent="P")

# Rotations that turn a Plane (normal +z, texture up +y) to face into the hall from each wall.
FACE = {"back": "1 0 0 1.5708", "front": "0 0.7071 0.7071 3.1416", "right": "0.5774 -0.5774 -0.5774 2.0944", "left": "0.5774 0.5774 0.5774 2.0944"}

out = []
w = out.append


def pbr(color, rough=0.7, metal=0, extra=""):
    return f"PBRAppearance {{ baseColor {color} roughness {rough} metalness {metal} {extra} }}"


def box(pos, size, app, rot="0 0 1 0"):
    w(f"Pose {{ translation {pos} rotation {rot} children [ Shape {{ appearance {app} geometry Box {{ size {size} }} }} ] }}")


def cyl(pos, r, h, app):
    w(f"Pose {{ translation {pos} children [ Shape {{ appearance {app} geometry Cylinder {{ radius {r} height {h} }} }} ] }}")


def picture(pos, wall, wd, ht, tex, glow=0.35):
    url = f'"../textures/{tex}"'
    app = (f"PBRAppearance {{ baseColorMap ImageTexture {{ url [ {url} ] }} roughness 0.6 metalness 0 "
           f"emissiveColorMap ImageTexture {{ url [ {url} ] }} emissiveIntensity {glow} }}")
    w(f"Pose {{ translation {pos} rotation {FACE[wall]} children [ Shape {{ appearance {app} geometry Plane {{ size {wd} {ht} }} }} ] }}")


def door(x, y, wall, width=1.6, z=0):
    # A light steel-blue hospital door with a vision panel and kick plate, set in a dark frame.
    t = 0.06
    if wall in ("back", "front"):
        s = 1 if wall == "back" else -1
        box(f"{x} {y - s * 0.01} {z + 1.12}", f"{width + 0.16} {t} 2.32", pbr("0.25 0.27 0.3"))
        box(f"{x} {y - s * 0.04} {z + 1.1}", f"{width} {t} 2.2", pbr("0.56 0.67 0.75", 0.5))
        box(f"{x - width / 4} {y - s * 0.075} {z + 1.45}", f"0.22 0.01 0.5", pbr("0.15 0.2 0.25", 0.1))
        box(f"{x + width / 4} {y - s * 0.075} {z + 1.45}", f"0.22 0.01 0.5", pbr("0.15 0.2 0.25", 0.1))
        box(f"{x} {y - s * 0.075} {z + 0.15}", f"{width} 0.01 0.25", pbr("0.7 0.72 0.75", 0.3, 0.3))
        box(f"{x} {y - s * 0.075} {z + 1.1}", f"0.02 0.01 2.2", pbr("0.3 0.35 0.4"))
    else:
        s = 1 if wall == "right" else -1
        box(f"{x - s * 0.01} {y} {z + 1.12}", f"{t} {width + 0.16} 2.32", pbr("0.25 0.27 0.3"))
        box(f"{x - s * 0.04} {y} {z + 1.1}", f"{t} {width} 2.2", pbr("0.72 0.74 0.76", 0.25, 0.5))
        box(f"{x - s * 0.075} {y} {z + 1.1}", f"0.01 0.02 2.2", pbr("0.3 0.32 0.35"))


def chair_row(cx, cy, n=5, z=0):
    # Steel gang chairs facing +y, the kind in every government OPD.
    seat, back, steel = pbr("0.12 0.33 0.62", 0.45), pbr("0.12 0.33 0.62", 0.45), pbr("0.7 0.72 0.75", 0.35, 0.4)
    L = n * 0.52
    box(f"{cx} {cy} {z + 0.40}", f"{L} 0.06 0.05", steel)
    for e in (-1, 1):
        box(f"{cx + e * (L / 2 - 0.05)} {cy} {z + 0.2}", "0.05 0.42 0.04", steel)
        box(f"{cx + e * (L / 2 - 0.05)} {cy} {z + 0.21}", "0.04 0.04 0.42", steel)
    for i in range(n):
        x = cx - L / 2 + 0.26 + i * 0.52
        box(f"{x} {cy + 0.02} {z + 0.46}", "0.46 0.42 0.035", seat)
        box(f"{x} {cy - 0.2} {z + 0.72}", "0.46 0.03 0.4", back, "1 0 0 -0.12")


def human(name, model, tone, x, y, yaw, motion, z=0):
    args = ["-d", f"skin_{name}", "-f", str(MOTIONS / motion), "-l", "-s", "100000"]
    a = " ".join(f'"{v}"' for v in args)
    w(f"DEF {name} Robot {{ translation {x} {y} {z} rotation 0 0 1 {yaw:.4f} children [ CharacterSkin {{ name \"skin_{name}\" model \"{model}\" skinTone \"{tone}\" scale {SCALE.get(model, 1)} {SCALE.get(model, 1)} {SCALE.get(model, 1)} }} ] "
      f"name \"{name}\" controller \"bvh_animation\" controllerArgs [ {a} ] }}")


w("#VRML_SIM R2025a utf8\n")
w('EXTERNPROTO "../protos/projects/humans/skin_animated_humans/protos/CharacterSkin.proto"')
w('EXTERNPROTO "../protos/projects/objects/hospital/protos/DripStand.proto"')
w('EXTERNPROTO "../protos/projects/objects/factory/containers/protos/CardboardBox.proto"')
w('EXTERNPROTO "../protos/SaathiRover.proto"\n')
w('WorldInfo { info [ "Saathi: crowd-aware OPD guide robot (Hack in Hills 26, PS-01)" ] title "Saathi OPD" basicTimeStep 32 contactProperties [ ContactProperties { bumpSound \"\" rollSound \"\" slideSound \"\" } '
  'ContactProperties { material1 \"InteriorWheelMat\" coulombFriction [ 0, 2, 0 ] frictionRotation -0.785398 0 bounce 0 forceDependentSlip [ 10, 0 ] bumpSound \"\" rollSound \"\" slideSound \"\" } '
  'ContactProperties { material1 \"ExteriorWheelMat\" coulombFriction [ 0, 2, 0 ] frictionRotation 0.785398 0 bounce 0 forceDependentSlip [ 10, 0 ] bumpSound \"\" rollSound \"\" slideSound \"\" } ] }')
w("Viewpoint { orientation -0.2 0.2 0.96 1.6 position -1 -14 9 }")
w("Background { skyColor [ 0.8 0.82 0.84 ] }")
w("DirectionalLight { direction 0.15 0.25 -1 intensity 1.1 castShadows FALSE }")
for (lx, ly) in [(-5, -3), (-5, 3), (2, -3), (2, 3), (7, 0)]:
    w(f"PointLight {{ location {lx} {ly} 2.9 intensity 0.55 castShadows FALSE }}")

# Floor, ceiling with light panels, two-tone walls with a teal dado rail.
w('Solid { children [ Shape { appearance PBRAppearance { baseColorMap ImageTexture { url [ "../textures/floor_tiles.jpg" ] } '
  'roughness 0.35 metalness 0 textureTransform TextureTransform { scale 7.5 5 } } geometry Plane { size 18 12 } } ] name "floor" boundingObject Plane { size 18 12 } }')
if FLOOR2:  # the slab stops at the shaft so the cabin can pass
    box("-0.9 0 3.24", "16.6 12.4 0.08", pbr("0.95 0.95 0.94", 0.9))
    box("8.25 -2.85 3.24", "1.9 6.7 0.08", pbr("0.95 0.95 0.94", 0.9))
    box("8.25 4.35 3.24", "1.9 3.7 0.08", pbr("0.95 0.95 0.94", 0.9))
else:
    box("0 0 3.24", "18.4 12.4 0.08", pbr("0.95 0.95 0.94", 0.9))
for px in (-6, -2, 2, 6):
    for py in (-3.5, 0, 3.5):
        box(f"{px} {py} 3.195", "1.2 0.6 0.015", pbr("1 1 1", 0.5, 0, "emissiveColor 1 1 0.96 emissiveIntensity 2.5"))
lower, upper, rail = pbr("0.62 0.78 0.74", 0.8), pbr("0.95 0.94 0.9", 0.9), pbr("0.06 0.45 0.42", 0.5)
for (cx, cy, sx, sy) in [(0, 6.1, 18.4, 0.2), (0, -6.1, 18.4, 0.2), (9.1, 0, 0.2, 12.4), (-9.1, 0, 0.2, 12.4)]:
    box(f"{cx} {cy} 0.6", f"{sx} {sy} 1.2", lower)
    box(f"{cx} {cy} 2.2", f"{sx} {sy} 2.0", upper)
    ix = cx - math.copysign(0.11, cx) if sx < 1 else cx
    iy = cy - math.copysign(0.11, cy) if sy < 1 else cy
    box(f"{ix} {iy} 1.2", f"{sx if sx > 1 else 0.03} {sy if sy > 1 else 0.03} 0.06", rail)

# Back wall (y = 6): registration counter + token display, pharmacy window, radiology.
box("-6.3 4.9 0.525", "3.4 0.7 1.05", pbr("0.55 0.38 0.22", 0.6))
box("-6.3 4.9 1.07", "3.5 0.8 0.04", pbr("0.96 0.96 0.95", 0.3))
box("-6.3 4.6 1.37", "3.4 0.02 0.55", pbr("0.75 0.88 0.92", 0.05, 0, "transparency 0.6"))
for mx in (-7.3, -6.3, -5.3):
    box(f"{mx} 5.1 1.27", "0.45 0.04 0.3", pbr("0.05 0.05 0.06", 0.3))
picture("-6.3 5.97 2.55", "back", 2.4, 0.6, "sign_registration.png")
box("-3.6 5.975 2.3", "1.08 0.03 0.58", pbr("0.08 0.08 0.09", 0.4))
picture("-3.6 5.955 2.3", "back", 1.0, 0.5, "token.png", 1.2)
box("-0.8 5.96 1.6", "2.0 0.04 1.0", pbr("0.55 0.68 0.72", 0.05, 0, "transparency 0.35"))
box("-0.8 5.8 1.05", "2.2 0.35 0.06", pbr("0.96 0.96 0.95", 0.3))
picture("-0.8 5.97 2.55", "back", 2.4, 0.6, "sign_pharmacy.png")
picture("2.0 5.97 1.7", "back", 0.6, 0.8, "poster_left.png", 0.2)
door(5.0, 6.0, "back")
picture("5.0 5.97 2.6", "back", 2.4, 0.6, "sign_radiology.png")
# Front wall (y = -6): emergency and lab, a hygiene poster.
door(-5.0, -6.0, "front")
picture("-5.0 -5.97 2.6", "front", 2.4, 0.6, "sign_emergency.png")
door(2.5, -6.0, "front")
picture("2.5 -5.97 2.6", "front", 2.4, 0.6, "sign_lab.png")
picture("-1.5 -5.97 1.7", "front", 0.6, 0.8, "poster_hands.png", 0.2)
# Right wall (x = 9): wards and lift. Left wall (x = -9): glass entrance under the hospital board.
if not FLOOR2:
    door(9.0, 1.5, "right", 1.5)
    picture("8.97 1.5 2.6", "right", 2.4, 0.6, "sign_wards.png")


def lift_shaft(z):
    """Shaft walls, the front wall with the door opening, a steel door frame and the call button, at floor level z."""
    steel, dark = pbr("0.72 0.74 0.76", 0.25, 0.5), pbr("0.25 0.27 0.3")
    for (cx, cy, sx, sy) in SHAFT:
        box(f"{cx} {cy} {z + 1.6}", f"{sx} {sy} 3.2", upper)
    box(f"7.4 1.5 {z + 2.75}", "0.1 1.7 0.9", upper)                      # over the door
    for y in (0.67, 2.33):                                                  # frame: two posts and a lintel, the opening stays open
        box(f"7.38 {y} {z + 1.12}", "0.04 0.06 2.32", dark)
    box(f"7.38 1.5 {z + 2.3}", "0.04 1.72 0.12", dark)
    box(f"7.36 1.5 {z + 2.42}", "0.02 0.5 0.12", pbr("0.1 0.1 0.1", 0.3, 0, "emissiveColor 1 0.55 0.1 emissiveIntensity 1.5"))  # floor indicator lamp
    box(f"7.36 2.55 {z + 1.0}", "0.02 0.1 0.16", steel)                     # call button plate
    picture(f"7.35 1.5 {z + 2.6}", "right", 1.7, 0.45, "sign_lift.png")


def lift_doors(tag, z):
    """Two sliding door panels that Saathi's supervisor moves: closed at y 1.125 / 1.875, open 0.75 m apart behind the front wall."""
    for n, y in zip("AB", LIFT["door_y"]):
        w(f'DEF {tag}_{n} Solid {{ translation {LIFT["door_x"]} {y} {z + 1.1} children [ Shape {{ appearance {pbr("0.72 0.74 0.76", 0.25, 0.5)} geometry Box {{ size 0.04 0.75 2.2 }} }} '
          f'Pose {{ translation -0.025 0 0 children [ Shape {{ appearance {pbr("0.3 0.32 0.35")} geometry Box {{ size 0.01 0.02 2.2 }} }} ] }} ] name "{tag}_{n}" }}')


if FLOOR2:
    lift_shaft(0)
    lift_doors("LDOOR1", 0)
    # The cabin: floor, three walls, a mirror strip and a ceiling light. Saathi's supervisor slides it between the floors.
    w(f'DEF LIFT Solid {{ translation {LIFT["cabin"][0]} {LIFT["cabin"][1]} 0 children [ '
      f'Pose {{ translation 0 0 -0.03 children [ Shape {{ appearance {pbr("0.35 0.36 0.38", 0.4)} geometry Box {{ size 1.4 1.6 0.06 }} }} ] }} '
      f'Pose {{ translation 0.68 0 1.2 children [ Shape {{ appearance {pbr("0.8 0.81 0.83", 0.2, 0.6)} geometry Box {{ size 0.04 1.6 2.4 }} }} ] }} '
      f'Pose {{ translation 0.66 0 1.3 children [ Shape {{ appearance {pbr("0.9 0.92 0.95", 0.05, 0.9)} geometry Box {{ size 0.01 1.4 0.6 }} }} ] }} '
      f'Pose {{ translation 0 0.78 1.2 children [ Shape {{ appearance {pbr("0.8 0.81 0.83", 0.2, 0.6)} geometry Box {{ size 1.4 0.04 2.4 }} }} ] }} '
      f'Pose {{ translation 0 -0.78 1.2 children [ Shape {{ appearance {pbr("0.8 0.81 0.83", 0.2, 0.6)} geometry Box {{ size 1.4 0.04 2.4 }} }} ] }} '
      f'Pose {{ translation 0 0 2.42 children [ Shape {{ appearance {pbr("0.85 0.85 0.85", 0.5)} geometry Box {{ size 1.4 1.6 0.04 }} }} ] }} '
      f'Pose {{ translation 0 0 2.395 children [ Shape {{ appearance {pbr("1 1 1", 0.5, 0, "emissiveColor 1 1 0.96 emissiveIntensity 2.5")} geometry Box {{ size 0.8 0.4 0.01 }} }} ] }} '
      f'PointLight {{ location 0 0 2.2 intensity 0.4 castShadows FALSE }} ] name "lift" }}')
box("-8.97 0 1.25", "0.06 2.7 2.5", pbr("0.25 0.27 0.3"))
box("-8.93 0 1.22", "0.04 2.5 2.4", pbr("0.7 0.84 0.9", 0.05, 0, "transparency 0.45"))
picture("-8.97 0 2.85", "left", 3.2, 0.8, "sign_entrance.png", 0.5)

# Waiting area, a drip stand by emergency, a water cooler and Swachh Bharat bins.
for (cx, cy) in [(1.5, -3.0), (1.5, -4.0), (6.2, -3.0), (6.2, -4.0)]:
    chair_row(cx, cy)
w('DripStand { translation -6.4 -5.4 0 name "drip stand" }')
box("7.6 -5.6 0.55", "0.4 0.4 1.1", pbr("0.92 0.92 0.92", 0.4))
cyl("7.6 -5.6 1.3", 0.13, 0.4, pbr("0.45 0.65 0.95", 0.1, 0, "transparency 0.4"))
cyl("-2.5 5.65 0.3", 0.2, 0.6, pbr("0.15 0.55 0.25", 0.6))
cyl("-2.0 5.65 0.3", 0.2, 0.6, pbr("0.15 0.35 0.75", 0.6))

if FLOOR2:  # ---------- first floor: Blood Bank, ICU, OT, Wards, a nurse station, stairs ----------
    Z = Z2
    for (lx, ly) in [(-5, -3), (-5, 3), (2, -3), (2, 3), (7, -3)]:
        w(f"PointLight {{ location {lx} {ly} {Z + 2.9} intensity 0.55 castShadows FALSE }}")
    # A Box, not a Plane: a Plane collider is an infinite half-space and would throw everything on the ground floor out of it.
    w(f'Solid {{ translation 0 0 {Z - 0.01} children [ Pose {{ translation 0 0 0.011 children [ Shape {{ appearance PBRAppearance {{ baseColorMap ImageTexture {{ url [ "../textures/floor_tiles.jpg" ] }} '
      f'roughness 0.35 metalness 0 textureTransform TextureTransform {{ scale 7.5 5 }} }} geometry Plane {{ size 18 12 }} }} ] }} ] name "floor2" boundingObject Box {{ size 18 12 0.02 }} }}')
    box(f"0 0 {Z + 3.24}", "18.4 12.4 0.08", pbr("0.95 0.95 0.94", 0.9))
    for px in (-6, -2, 2, 6):
        for py in (-3.5, 0, 3.5):
            box(f"{px} {py} {Z + 3.195}", "1.2 0.6 0.015", pbr("1 1 1", 0.5, 0, "emissiveColor 1 1 0.96 emissiveIntensity 2.5"))
    for (cx, cy, sx, sy) in [(0, 6.1, 18.4, 0.2), (0, -6.1, 18.4, 0.2), (9.1, 0, 0.2, 12.4), (-9.1, 0, 0.2, 12.4)]:
        box(f"{cx} {cy} {Z + 0.6}", f"{sx} {sy} 1.2", lower)
        box(f"{cx} {cy} {Z + 2.2}", f"{sx} {sy} 2.0", upper)
        ix = cx - math.copysign(0.11, cx) if sx < 1 else cx
        iy = cy - math.copysign(0.11, cy) if sy < 1 else cy
        box(f"{ix} {iy} {Z + 1.2}", f"{sx if sx > 1 else 0.03} {sy if sy > 1 else 0.03} 0.06", rail)
    lift_shaft(Z)
    lift_doors("LDOOR2", Z)
    picture(f"7.35 -0.9 {Z + 1.7}", "right", 1.2, 0.5, "sign_floor1.png", 0.5)
    # Back wall: nurse station counter, Blood Bank, Wards 1-6 (a bed visible through the open door).
    box(f"0 4.9 {Z + 0.525}", "3.4 0.7 1.05", pbr("0.55 0.38 0.22", 0.6))
    box(f"0 4.9 {Z + 1.07}", "3.5 0.8 0.04", pbr("0.96 0.96 0.95", 0.3))
    picture(f"0 5.97 {Z + 2.55}", "back", 2.4, 0.6, "sign_nurse.png")
    door(-3.0, 6.0, "back", z=Z); picture(f"-3.0 5.97 {Z + 2.6}", "back", 2.4, 0.6, "sign_bloodbank.png")
    picture(f"-5.5 5.97 {Z + 1.7}", "back", 0.6, 0.8, "poster_donate.png", 0.2)
    door(4.5, 6.0, "back", z=Z); picture(f"4.5 5.97 {Z + 2.6}", "back", 2.4, 0.6, "sign_wards2.png")
    # Front wall: ICU and OT. A stretcher parked by the right wall; stairs down on the left wall.
    door(-4.0, -6.0, "front", z=Z); picture(f"-4.0 -5.97 {Z + 2.6}", "front", 2.4, 0.6, "sign_icu.png")
    door(3.0, -6.0, "front", z=Z); picture(f"3.0 -5.97 {Z + 2.6}", "front", 2.4, 0.6, "sign_ot.png")
    picture(f"0 -5.97 {Z + 1.7}", "front", 0.6, 0.8, "poster_hands.png", 0.2)
    for (cx, cy) in [(-4.0, -2.0), (-4.0, -3.0)]:
        chair_row(cx, cy, z=Z)
    box(f"6.8 -4.6 {Z + 0.8}", "0.7 2.0 0.12", pbr("0.9 0.9 0.92", 0.6))       # stretcher mattress
    box(f"6.8 -4.6 {Z + 0.72}", "0.75 2.05 0.05", pbr("0.6 0.62 0.65", 0.3, 0.6))
    for sx_, sy_ in ((-0.3, -0.9), (0.3, -0.9), (-0.3, 0.9), (0.3, 0.9)):
        cyl(f"{6.8 + sx_} {-4.6 + sy_} {Z + 0.35}", 0.02, 0.7, pbr("0.6 0.62 0.65", 0.3, 0.6))
    for i in range(6):  # a flight of stairs going down, boxed by a railing
        box(f"{-7.8} {4.6 - i * 0.26} {Z - 0.08 - i * 0.16}", "1.1 0.26 0.16", pbr("0.6 0.6 0.58", 0.8))
    box(f"-7.2 4.0 {Z + 0.5}", "0.04 1.6 1.0", pbr("0.3 0.32 0.35", 0.4, 0.5))
    picture(f"-8.97 4.0 {Z + 2.2}", "left", 1.6, 0.5, "sign_stairs.png", 0.4)
    for (name, model, tone, pts) in WALKERS2:
        (x0, y0), (x1, y1) = pts[0], pts[1]
        human(name, model, tone, x0, y0, math.atan2(y1 - y0, x1 - x0), "walk.bvh", Z)
    for (name, model, tone, (x, y), (lx, ly)) in STANDERS2:
        human(name, model, tone, x, y, math.atan2(ly - y, lx - x), "stand.bvh", Z)
    w(f'DEF CCTV2 Robot {{ translation -8.6 -5.6 {Z + 3.0} children [ Camera {{ name "cam" width 1280 height 720 fieldOfView 1.25 antiAliasing TRUE }} ] '
      f'name "cctv2" controller "cctv" controllerArgs [ "--out={RUN["out"]}" "--every={RUN["every"]}" "--look=1,1.5,{Z}" ] supervisor TRUE }}')

# Not on Saathi's map: a yellow A-frame "wet floor" sign (Hindi + English) and a cardboard box someone left in the hall.
(wx, wy) = UNMAPPED[0][1] if UNMAPPED else (0, -50)  # off: parked out of sight below the floor
yellow = pbr("0.96 0.77 0.0", 0.5)
for s in (1, -1) if UNMAPPED else ():  # two leaning panels, text facing each way
    box(f"{wx + s * 0.11} {wy} 0.3", "0.02 0.4 0.62", yellow, f"0 1 0 {s * 0.33}")
    w(f'Pose {{ translation {wx + s * 0.125} {wy} 0.3 rotation 0 1 0 {s * 0.33} children [ Pose {{ rotation {FACE["left"] if s < 0 else FACE["right"]} children [ '
      f'Shape {{ appearance PBRAppearance {{ baseColorMap ImageTexture {{ url [ "../textures/caution_wet.png" ] }} roughness 0.6 metalness 0 }} geometry Plane {{ size 0.38 0.58 }} }} ] }} ] }}')
if UNMAPPED:
    (bx, by), (bsx, bsy) = UNMAPPED[1][1], UNMAPPED[1][2]
    w(f'CardboardBox {{ translation {bx} {by} 0.3 size {bsx} {bsy} 0.6 name "unmapped box" }}')

# People.
for (name, model, tone, pts) in WALKERS:
    (x0, y0), (x1, y1) = pts[0], pts[1]
    human(name, model, tone, x0, y0, math.atan2(y1 - y0, x1 - x0), "walk.bvh")
for (name, model, tone, (x, y), (lx, ly)) in STANDERS:
    human(name, model, tone, x, y, math.atan2(ly - y, lx - x), "stand.bvh")
for (name, model, tone, (x, y), (lx, ly), _) in ACTORS:  # the walking body waits below the floor until the script moves it
    human(name, model, tone, x, y, math.atan2(ly - y, lx - x), "walk.bvh", -10)
    human(f"{name}_STAND", model, tone, x, y, math.atan2(ly - y, lx - x), "stand.bvh")

# The person who falls (--fall=7: at 7 s the walker in front of Saathi is swapped for this body lying on the floor). No controller: it lies still.
for (name, model, tone, _) in WALKERS:  # one lying body per walker, same look, parked out of sight until needed
    w(f'DEF FALLEN_{name} Robot {{ translation 0 0 -10 children [ CharacterSkin {{ name "skin_fallen_{name}" model "{model}" skinTone "{tone}" scale {SCALE.get(model, 1)} {SCALE.get(model, 1)} {SCALE.get(model, 1)} }} ] name "fallen {name}" }}')

# Saathi at the entrance, a CCTV camera high in a corner, and a chase camera Saathi's supervisor flies behind it.
O, E = RUN["out"], RUN["every"]
x0, y0 = ROUTE[0]
arg = lambda run: " ".join(f'"--{k}={v}"' for k, v in run.items() if k not in ("unmapped", "robots", "floors"))  # fall, lost, report too
if RUN["robots"] == "2":  # Saathi Parivaar: Saathi-1 is posted at the help desk facing the registration queue; Saathi-2 does its trip
    w(f'DEF SAATHI SaathiRover {{ translation -4.4 2.0 0 rotation 0 0 1 1.5708 controllerArgs [ {arg({**RUN, "goal": "at:-4.4,2.0", "robot": "1", "chase": "0"})} ] }}')
    w(f'DEF SAATHI2 SaathiRover {{ translation {x0} {y0} 0 name "saathi2" controllerArgs [ {arg({**RUN, "out": RUN["out"] + "/r2", "robot": "2", "chase": "1"})} ] }}')
else:
    w(f'DEF SAATHI SaathiRover {{ translation {x0} {y0} 0 controllerArgs [ {arg(RUN)} ] }}')
w('DEF CCTV Robot { translation -8.6 -5.6 3.0 children [ Camera { name "cam" width 1280 height 720 fieldOfView 1.25 antiAliasing TRUE } ] '
  f'name "cctv" controller "cctv" controllerArgs [ "--out={O}" "--every={E}" "--look=1,1.5,0" ] supervisor TRUE }}')
w('DEF FRONT Robot { translation 7.4 5.5 2.3 children [ Camera { name "cam" width 1280 height 720 fieldOfView 0.9 antiAliasing TRUE } ] '
  f'name "front" controller "cctv" controllerArgs [ "--out={O}" "--every={E}" "--look=2.2,1.2,0.7" ] supervisor TRUE }}')
w('DEF PAIRCAM Robot { translation -3.6 -0.2 2.1 children [ Camera { name "cam" width 1280 height 720 fieldOfView 0.85 antiAliasing TRUE } ] '
  f'name "paircam" controller "cctv" controllerArgs [ "--out={O}" "--every={E}" "--look=-0.6,2.6,0.6" ] supervisor TRUE }}')
w('DEF CHASE Robot { translation -10 0 2 children [ Camera { name "cam" width 1280 height 720 fieldOfView 0.95 antiAliasing TRUE } ] '
  f'name "chase" controller "cctv" controllerArgs [ "--out={O}" "--every={E}" ] supervisor TRUE }}')

(ROOT / "worlds" / "opd.wbt").write_text("\n".join(out) + "\n")
scene = {"walkers": [{"name": n, "path": p, "speed": SPEED(m), "floor": 1} for (n, m, _, p) in WALKERS] +
                    ([{"name": n, "path": p, "speed": SPEED(m), "floor": 2} for (n, m, _, p) in WALKERS2] if FLOOR2 else []),
         "standers": [{"name": n, "pos": p, "floor": 1} for (n, _, _, p, _) in STANDERS] + ([{"name": n, "pos": p, "floor": 2} for (n, _, _, p, _) in STANDERS2] if FLOOR2 else []),
         "route": ROUTE,
         "obstacles": OBSTACLES + (SHAFT if FLOOR2 else []),
         "floor2": dict(obstacles=OBSTACLES2, goals=GOALS2, goals1=GOALS1, lift=LIFT) if FLOOR2 else None, "unmapped": [[n, list(c), list(s)] for n, c, s in UNMAPPED], "goals": GOALS, "pairs": [["T1", "T2"]], "start": ROUTE[0], "places": PLACES, "lost": LOST,
         "actors": {n: dict(start=p, face=f, script=sc, speed=SPEED(m)) for n, m, _, p, f, sc in ACTORS}}
(ROOT / "controllers" / "saathi").mkdir(parents=True, exist_ok=True)
(ROOT / "controllers" / "saathi" / "scene.json").write_text(json.dumps(scene, indent=1))
print("wrote", ROOT / "worlds" / "opd.wbt")
