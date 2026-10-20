"""Saathi in Webots: plans its own way to a department through the OPD crowd, shows its face, records everything.

Args: --mode=saathi|baseline  --perception=gt|vision  --goal=Radiology  --out=DIR  --until=S  --every=S
gt: the planner gets the people's true positions; vision: it gets what YOLO + the depth camera see (perception.py).
Metrics always use the true positions. The crowd is kinematic: each walker plays its walk cycle in place (bvh_animation)
and this supervisor slides it along its path. Black box: every decision is saved with the camera frame and the reason.
"""
import json, math, os, subprocess, sys
import cv2
import numpy as np
from controller import Supervisor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cctv"))
from cctv import yaw_pitch_rotation  # noqa: E402
from brain import Grid, Metrics, Reflex  # noqa: E402

args = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
OUT, UNTIL, EVERY = os.path.abspath(args.get("out", "../../out/run")), float(args.get("until", 40)), float(args.get("every", 0.5))
MODE, PERCEPTION, GOAL = args.get("mode", "saathi"), args.get("perception", "gt"), args.get("goal", "Radiology")
FALL_AT = float(args.get("fall", 0))  # seconds; 0 = nobody falls
os.makedirs(os.path.join(OUT, "blackbox"), exist_ok=True)
scene = json.load(open(os.path.join(os.path.dirname(__file__), "scene.json")))
LOST = scene.get("lost") if args.get("lost") == "1" else None  # Saathi Parivaar: a parent reports a lost child at REPORT s
REPORT = float(args.get("report", 60))
ROBOT = int(args.get("robot", 1))            # which Saathi this is (Saathi Parivaar runs two)
WORLD = ROBOT == 1                            # only Saathi-1's controller moves the crowd and the scripted people
CHASE_ON = args.get("chase", "1") == "1"      # the chase camera follows this Saathi
LIVE = args.get("live") == "1"                # take spoken commands from the voice agent (tools/voice.py) instead of a script
if LIVE:
    REPORT = float("inf")                     # a lost child is reported by voice, not at a fixed time
CMDS = os.path.join(os.path.dirname(__file__), "..", "..", "out", "live", "commands.jsonl")
_cmd_pos = os.path.getsize(CMDS) if LIVE and os.path.exists(CMDS) else 0  # only commands given after start-up
paused = False

bot = Supervisor()
DT_MS = int(bot.getBasicTimeStep())
DT = DT_MS / 1000
cam, rf, lidar = bot.getDevice("camera"), bot.getDevice("depth"), bot.getDevice("lidar")
for d in (cam, rf, lidar):  # the lost-child scene runs YOLO every other step, so the cameras render at that rate too
    d.enable(DT_MS * (2 if LOST and d is not lidar else 1))
W, H = cam.getWidth(), cam.getHeight()
face = bot.getDevice("face")
wheels = [bot.getDevice(f"wheel_{n}") for n in ("fl", "fr", "rl", "rr")]
me = bot.getSelf()
my_r = me.getField("rotation")
R_W, LXY = 0.11, 0.23 + 0.255  # wheel radius; half wheelbase + half track (m)
for m in wheels:  # motors take speed commands
    m.setPosition(float("inf")); m.setVelocity(0.0)


def drive(vx, vy, wz):
    """Body velocity (forward, left m/s; turn rad/s) -> the four mecanum wheel speeds (inverse kinematics), order fl fr rl rr."""
    for m, s in zip(wheels, (vx - vy - LXY * wz, vx + vy + LXY * wz, vx + vy - LXY * wz, vx - vy + LXY * wz)):
        m.setVelocity(max(-24.0, min(24.0, s / R_W)))


def measured_pose():
    """Where physics has put the robot. (In sim this is ground truth; on the real rover, LiDAR localisation.)"""
    x, y, _ = me.getPosition()
    R = me.getOrientation()
    return x, y, math.atan2(R[3], R[0])
chase = bot.getFromDef("CHASE")
ch_t, ch_r = chase.getField("translation"), chase.getField("rotation")

WALK = 1.22  # m/s: walk.bvh's natural pace at 4 frames per 32 ms step, so feet don't slide (scaled people walk slower: scene.json)
walkers = []
for wk in scene["walkers"]:
    node = bot.getFromDef(wk["name"])
    a, b = (np.array(p, float) for p in wk["path"])
    walkers.append(dict(id=wk["name"], t=node.getField("translation"), r=node.getField("rotation"), a=a, b=b,
                        L=float(np.linalg.norm(b - a)), s=0.0, dir=1, turn=0.0, pos=a.copy(), vel=np.zeros(2), v=wk.get("speed", WALK)))
standers = {s["name"]: np.array(s["pos"], float) for s in scene["standers"]}


class Actor:
    """A scripted person with two bodies: walking (walk.bvh) while moving, standing (stand.bvh) while still."""

    def __init__(self, name, a):
        self.walk, self.stand = bot.getFromDef(name), bot.getFromDef(name + "_STAND")
        self.pos, self.vel, self.path, self.moving = np.array(a["start"], float), np.zeros(2), [], True
        self.script, self.v = [(t0, pts) for t0, pts in a.get("script", [])], a.get("speed", WALK)
        self.yaw = math.atan2(a["face"][1] - a["start"][1], a["face"][0] - a["start"][0])
        self._show(False)

    def _show(self, moving):
        if moving != self.moving:
            self.moving = moving
            on, off = (self.walk, self.stand) if moving else (self.stand, self.walk)
            on.getField("translation").setSFVec3f([float(self.pos[0]), float(self.pos[1]), 0.0])
            on.getField("rotation").setSFRotation([0, 0, 1, self.yaw])
            off.getField("translation").setSFVec3f([0.0, 0.0, -10.0])

    def go(self, path):
        self.path = [np.array(p, float) for p in path]

    def step(self, t):
        if self.script and t >= self.script[0][0]:
            self.go(self.script.pop(0)[1])
        if not self.path:
            self.vel = np.zeros(2)
            return self._show(False)
        d = self.path[0] - self.pos
        L = float(np.linalg.norm(d))
        u = d / max(L, 1e-9)
        self.pos = self.path.pop(0) if L <= self.v * DT else self.pos + u * self.v * DT
        self.vel, self.yaw = u * self.v, math.atan2(u[1], u[0])
        self._show(True)
        self.walk.getField("translation").setSFVec3f([float(self.pos[0]), float(self.pos[1]), 0.0])
        self.walk.getField("rotation").setSFRotation([0, 0, 1, self.yaw])

    def sync(self):
        """For a Saathi that does not move the people: read where the visible body is."""
        body = self.walk if self.walk.getField("translation").getSFVec3f()[2] > -5 else self.stand
        p = np.array(body.getField("translation").getSFVec3f()[:2])
        self.vel, self.pos = (p - self.pos) / DT, p


actors = {n: Actor(n, a) for n, a in scene.get("actors", {}).items()}
fallen_who, fall_seen, fall_state, fall_t, trip_goal, lying = None, None, None, 0.0, None, []
def AREA(x, y):
    n = min(scene["goals"], key=lambda n: math.hypot(scene["goals"][n][0] - x, scene["goals"][n][1] - y))
    d = math.hypot(scene["goals"][n][0] - x, scene["goals"][n][1] - y)
    return n if d < 3.5 else f"the middle of the hall, {d:.0f} m from {n}"
true_pairs = [(tuple(standers[a]), tuple(standers[b])) for a, b in scene["pairs"]]
# A goal is a department on the map, or "find:<thing>": then Saathi has to find it with its camera first.
FIND = GOAL[5:] if GOAL.startswith("find:") else None
goal = None if FIND else tuple(float(v) for v in GOAL[3:].split(",")) if GOAL.startswith("at:") else tuple(scene["goals"][GOAL])
SCAN_SPOTS = [(-7.6, 0.0), (-2.0, 1.0), (3.0, 1.0), (3.0, -2.0), (-3.0, -2.0)]  # where to look around if the thing is not in view
found, sightings, scan_left, spot = None, [], 2 * math.pi, 0
grid = Grid(scene["obstacles"])
brain = Reflex(grid, social=(MODE == "saathi"))
metrics = Metrics()
eyes = None
if PERCEPTION == "vision":
    from perception import Eyes, Namer, ObstacleMemory, depth_points, lidar_points
    eyes = Eyes(os.path.join(os.path.dirname(__file__), "..", "..", "models", "yolo11s.pt"), W, H, cam.getFov())
    memory = ObstacleMemory(grid)
    # YOLOE names things (unmapped obstacles, find:<thing>, falls). The lost-child scene skips it: ~1 GB less on an 8 GB Mac.
    namer = None if LOST else Namer(os.path.join(os.path.dirname(__file__), "..", "..", "models", "yoloe-11s-seg.pt"), W, cam.getFov())
unmapped = [(n, c, s) for n, c, s in scene.get("unmapped", [])]

if LOST:  # Saathi Parivaar: remember everyone seen, and find a lost child from the parent's words
    import clip, torch
    from PIL import Image
    from brain import GH, GW, astar, smooth
    from memory import CHILD_H, PeopleMemory
    _root = os.path.join(os.path.dirname(__file__), "..", "..")
    clip_model, clip_prep = clip.load(os.path.join(_root, "models", "weights", "clip", "ViT-B-32.pt"), device="cpu")
    with torch.no_grad():
        _q = clip_model.encode_text(clip.tokenize([LOST["query"]])).float()[0].numpy()
    qemb = _q / np.linalg.norm(_q)
    people_mem = PeopleMemory(grid, scene["places"].values())
    lost = dict(state=None, last_mem={}, live={}, belief=[])
    PITCH, CAM_H = 0.1, 1.005


def embed(crops):
    with torch.no_grad():
        E = clip_model.encode_image(torch.stack([clip_prep(Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))) for c in crops])).float().numpy()
    return E / np.linalg.norm(E, axis=1, keepdims=True)


def height(box, z):
    """Top of the head above the floor, from the box top and the depth (None if the head is cut off)."""
    if box[1] <= 2:
        return None
    zf = z - 0.12
    return CAM_H - zf * math.sin(PITCH) - ((box[1] - H / 2) * zf / eyes.f) * math.cos(PITCH)


def jagah(x, y):
    """Where (x, y) is, in words: near a named place, or in the hall so far from the nearest one."""
    n, (px, py) = min(scene["places"].items(), key=lambda kv: math.hypot(kv[1][0] - x, kv[1][1] - y))
    d = math.hypot(px - x, py - y)
    return f"{n} ke paas" if d < 3 else f"hall ke beech mein, {n} se {d:.0f} m"


def towards(x, y, vx, vy):
    """The named place someone walking with velocity (vx, vy) is heading for (most in line, nearer first), or None if
    no place is within about 50 degrees of their direction."""
    sp = math.hypot(vx, vy)
    cos = {n: ((p[0] - x) * vx + (p[1] - y) * vy) / sp / (math.hypot(p[0] - x, p[1] - y) + 1e-6) for n, p in scene["places"].items()}
    n = max(cos, key=lambda n: cos[n] - math.hypot(scene["places"][n][0] - x, scene["places"][n][1] - y) / 40)
    return n if cos[n] > 0.65 else None


def say(t, note, snap=True):
    global last_status, last_event
    events.write(json.dumps({"t": round(t, 2), "status": note}) + "\n"); events.flush()
    if snap:
        snapshot(t, note, boxes, people_true, measured_pose())
    last_status, last_event = note, t


radio_tx, radio_rx = bot.getDevice("radio_tx"), bot.getDevice("radio_rx")
radio_rx.enable(DT_MS)
others = {}  # the other Saathis in the hall: id -> (x, y), from their radio


def send(msg):
    radio_tx.send(json.dumps({**msg, "r": ROBOT}))


def chat(t, text):
    """A line in the Saathis' group chat (and in this one's event log), in Hinglish."""
    say(t, f"Saathi-{ROBOT}: {text}" if others else text)


def heard(t, m):
    """A radio message from another Saathi: its position, a sighting, a stretch of floor it looked at, or news."""
    if m["k"] == "pose":
        others[m["r"]] = (m["x"], m["y"])
    elif not LOST:
        return
    elif m["k"] == "sight":
        people_mem.add(m["t"], m["track"], m["x"], m["y"], m["vx"], m["vy"], m["h"], np.array(m["e"], float), robot=m["r"])
    elif m["k"] == "look":
        people_mem.look(m["t"], m["x"], m["y"], m["a"], m["d"])
    elif m["k"] == "found" and lost["state"] in ("with_parent", "search", "look"):
        lost.update(state="escort", found_xy=(m["x"], m["y"]), found_at=lost.get("found_at", t), found_by=m["r"], forget_keys={tuple(q) for q in m["keys"]})
        chat(t, "Papa ko le ke aa raha hoon")
        if WORLD:
            lost["follow"] = True  # the father walks behind me
    elif m["k"] == "done" and lost["state"] != "done":
        people_mem.forget(set(map(tuple, m["keys"])))
        lost.update(state="done", done_at=t)


def commands():
    """New lines in the voice agent's command file."""
    global _cmd_pos
    if not os.path.exists(CMDS):
        return []
    with open(CMDS) as f:
        f.seek(_cmd_pos)
        lines = f.readlines()
        _cmd_pos = f.tell()
    return [json.loads(q) for q in lines if q.strip()]


def obey(t, c):
    """A spoken command: go somewhere, stop, or a lost child (the parent's words become the memory's search)."""
    global goal, GOAL, paused, REPORT, qemb
    if c["cmd"] == "stop":
        paused = True
        say(t, "Haath ka ishara: mutthi. Ruk gaya" if c.get("via") == "gesture" else "Awaaz: \"Saathi, ruko\". Ruk gaya", snap=False)
    elif c["cmd"] == "go" and paused:
        paused = False
        say(t, "Khula haath: phir chal raha hoon", snap=False)
    elif c["cmd"] == "goto" and c["goal"] in scene["goals"]:
        paused, GOAL, goal = False, c["goal"], tuple(scene["goals"][c["goal"]])
        brain.path, brain.next_plan = None, 0.0
        say(t, f"Awaaz: {c['goal']} jaana hai. Chaliye, main le chalta hoon", snap=False)
    elif c["cmd"] == "lost" and LOST and lost["state"] is None:
        paused = False
        LOST.update(query=c["query"], said=c["said"], child=c.get("child", True))
        with torch.no_grad():
            q = clip_model.encode_text(clip.tokenize([c["query"]])).float()[0].numpy()
        qemb, REPORT = q / np.linalg.norm(q), t  # the parent reports now


def walk_parent_to(xy):
    """Saathi-1 moves the scripted father: straight to the child, around the furniture."""
    p = actors[LOST["parent"]]
    xy = np.array(xy, float)
    to = xy + (p.pos - xy) * 0.8 / max(1e-6, float(np.linalg.norm(p.pos - xy)))
    cost = np.ones((GH, GW), np.float32)
    p.go((smooth(grid, cost, astar(grid, cost, tuple(p.pos), tuple(to)) or []) or [])[1:] + [tuple(to)])


def lost_see(t, fr, boxes, pose):
    """Remember who is in view (crop embedding, place, height) about once a second each, mark the floor in view as
    looked at, and while searching score everyone in view who could be the child against the parent's words."""
    searching, keep = lost["state"] in ("search", "look"), []
    for tid, (x0, y0, x1, y1), z in boxes:
        tr = eyes.tracks.get(tid)
        if tr is None or y1 - y0 < 60:
            continue
        h = height((x0, y0, x1, y1), z)
        could_be = not LOST["child"] or (h is not None and h < CHILD_H)
        if t - lost["last_mem"].get(tid, -9.0) >= 0.8 or (searching and could_be):
            keep.append((tid, tr, h, could_be, fr[max(0, y0):y1, max(0, x0):x1]))
    if keep:
        for (tid, tr, h, could_be, crop), e in zip(keep, embed([c for *_, c in keep])):
            if t - lost["last_mem"].get(tid, -9.0) >= 0.8:
                people_mem.add(t, tid, tr["x"], tr["y"], tr["vx"], tr["vy"], h, e, robot=ROBOT, crop=cv2.resize(crop, (64, 128)))
                send(dict(k="sight", t=round(t, 2), track=tid, x=round(tr["x"], 3), y=round(tr["y"], 3), vx=round(tr["vx"], 3),
                          vy=round(tr["vy"], 3), h=None if h is None else round(h, 3), e=[round(float(v), 4) for v in e]))
                lost["last_mem"][tid] = t
            if searching and could_be:
                lost["live"].setdefault(tid, []).append(float(e @ qemb))
    x, y, th = pose
    r = np.asarray(lidar.getRangeImage(), float)
    a = (math.pi - np.arange(len(r)) * 2 * math.pi / len(r) + math.pi) % (2 * math.pi) - math.pi
    v = np.abs(a) < 0.5  # the camera's 60 degrees
    rays, ranges = th + a[v], np.where(np.isfinite(r[v]), r[v], 12.0)
    people_mem.look(t, x, y, rays, ranges)
    send(dict(k="look", t=round(t, 2), x=round(x, 2), y=round(y, 2), a=[round(float(q), 3) for q in rays], d=[round(float(q), 2) for q in ranges]))


def lost_report(t, pose):
    """The parent has told the help desk. The Saathi nearest the parent stays with them; the other searches the shared
    memory, says what the team remembers, and looks where the child can be now. With one Saathi, it searches."""
    child, parent = actors[LOST["who"]], actors[LOST["parent"]]
    if WORLD:
        say(t, f"Help desk: \"{LOST['said']}\"")
    px, py = parent.pos
    people_mem.look(t, float(px), float(py), np.linspace(-math.pi, math.pi, 72, endpoint=False), [3.3] * 72, 3.0)  # not near the parent
    lost.update(report_t=t, child_at_report=child.pos.copy(), peak=None, first_peak=None, next_where=t)
    mine = math.hypot(pose[0] - px, pose[1] - py)
    if others and all(mine < math.hypot(ox - px, oy - py) for ox, oy in others.values()):
        lost.update(state="with_parent", role="parent", s=None, best=dict(score=-1.0, chain=[]))
        chat(t, f"Main papa ke saath ruka hoon. Saathi-{min(others)}, tum dhoondho")
        return
    lost["role"] = "search"
    res = people_mem.search(qemb, child=LOST["child"])
    if res:
        best, s = res[0], res[0]["last"]
        sp = math.hypot(s["vx"], s["vy"])
        to = towards(s["x"], s["y"], s["vx"], s["vy"]) if sp > 0.2 else None
        way = f", {to} ki taraf ja raha tha" if to else ", chal raha tha" if sp > 0.2 else ", khada tha"
        who = "maine" if s["robot"] == ROBOT else f"Saathi-{s['robot']} ne"
        chat(t, f"Yaaddasht: {who} aisa bachcha {t - s['t']:.0f} s pehle {jagah(s['x'], s['y'])} dekha tha{way}. Main dhoondhta hoon")
        tiles = [cv2.resize(c["crop"], (128, 256)) for r in res for c in [max(r["chain"], key=lambda q: q["emb"] @ qemb)] if c["crop"] is not None]
        if tiles:
            cv2.imwrite(os.path.join(OUT, "memory_match.jpg"), np.hstack(tiles))
        lost.update(state="search", s=s, best=best, cands=[(r["last"], math.exp((r["score"] - best["score"]) / 0.004)) for r in res])
    else:
        lost.update(state="search", s=dict(t=t, x=float(px), y=float(py), vx=0.0, vy=0.0, robot=ROBOT), best=dict(score=-1.0, chain=[]), cands=None)
        chat(t, "Yaaddasht: aisa bachcha humne nahi dekha. Poore hall mein dhoondh raha hoon")


def facing(pose, xy):
    yaw = math.atan2(xy[1] - pose[1], xy[0] - pose[0])
    return (pose[0], pose[1], pose[2] + max(-0.6, min(0.6, (yaw - pose[2] + math.pi) % (2 * math.pi) - math.pi)) * DT)


def lost_step(t, pose):
    """The finder: search -> look around -> go to the child -> stay. The parent's Saathi: with_parent -> escort (the father
    walks behind it). Then done. Returns a pose to hold, or None to drive to `goal`."""
    global goal
    L, x, y = lost, pose[0], pose[1]
    child, parent = actors[LOST["who"]], actors[LOST["parent"]]
    if WORLD and L["state"] in ("stay", "escort") and float(np.linalg.norm(parent.pos - child.pos)) < 1.3:
        keys = {(r["robot"], r["track"]) for r in L["best"]["chain"]} | ({(ROBOT, L["tid"])} if "tid" in L else set()) | L.get("forget_keys", set())
        people_mem.forget(keys)
        send(dict(k="done", keys=[list(q) for q in keys]))
        chat(t, "Papa aur beta mil gaye. Is bachche ki saari yaadein mita di (privacy)")
        L.update(state="done", done_at=t)
    if L["state"] in ("search", "look"):
        for tid, sc in L["live"].items():
            if len(sc) >= 3 and np.median(sc[-5:]) >= L["best"]["score"] - 0.02 and tid in eyes.tracks:
                tr = eyes.tracks[tid]
                L.update(state="go", tid=tid, found_at=t, found_xy=(tr["x"], tr["y"]), child_at_found=child.pos.copy())
                chat(t, f"Mil gaya! {jagah(tr['x'], tr['y'])}, {math.hypot(tr['x'] - x, tr['y'] - y):.1f} m door. Uske paas ja raha hoon")
                break
    if L["state"] == "search":
        if goal is not None and L["peak"] is not None and math.hypot(goal[0] - x, goal[1] - y) < 0.4:
            L.update(state="look", look_left=2 * math.pi)
        elif t >= L["next_where"]:
            P = people_mem.where_now_all(L["cands"], t) if L.get("cands") else people_mem.where_now(L["s"], t)
            L["next_where"], L["belief"] = t + 1.5, P[::max(1, len(P) // 150)]
            if len(P):
                g, peak, _ = people_mem.viewpoint(P, (x, y))
                if L["peak"] is None or math.hypot(peak[0] - L["peak"][0], peak[1] - L["peak"][1]) > 1.0:
                    L["peak"], goal = peak, g
                    L["first_peak"] = L["first_peak"] or peak
                    brain.path, brain.next_plan = None, 0.0
        return None
    if L["state"] == "look":
        L["look_left"] -= 0.7 * DT
        if L["look_left"] <= 0:
            L.update(state="search", peak=None, next_where=t)
        return (x, y, pose[2] + 0.7 * DT)
    if L["state"] == "go":
        tr = eyes.tracks.get(L["tid"])
        if tr:
            L["found_xy"] = (tr["x"], tr["y"])
        fx, fy = L["found_xy"]
        d = math.hypot(fx - x, fy - y)
        if d > 1.6:
            goal = (fx + (x - fx) * 1.2 / d, fy + (y - fy) * 1.2 / d)
            return None
        L.update(state="stay", stay_at=t)
        if others:
            chat(t, f"Bachche ke saath ruka hoon. Saathi-{min(others)}, papa ko le aao")
            send(dict(k="found", x=round(fx, 2), y=round(fy, 2), keys=[list(q) for q in {(r["robot"], r["track"]) for r in L["best"]["chain"]} | {(ROBOT, L["tid"])}]))
        else:
            chat(t, "Bachche ke saath ruka hoon. Papa ko yahan bula raha hoon")
        if WORLD and not others:
            walk_parent_to((fx, fy))
    if L["state"] == "with_parent":
        d = math.hypot(parent.pos[0] - x, parent.pos[1] - y)
        if d > 1.8:
            goal = (parent.pos[0] + (x - parent.pos[0]) * 1.4 / d, parent.pos[1] + (y - parent.pos[1]) * 1.4 / d)
            return None
        return facing(pose, parent.pos)
    if L["state"] == "escort":
        fx, fy = L["found_xy"]
        d = math.hypot(fx - x, fy - y)
        if WORLD and L.get("follow"):  # the father walks along my trail, ~1.5 m behind; near the child he goes the last bit himself
            trail = L.setdefault("trail", [np.array([x, y])])
            if float(np.linalg.norm(trail[-1] - np.array([x, y]))) > 0.2:
                trail.append(np.array([x, y]))
            back, k = 0.0, len(trail) - 1
            while k > 0 and back < 1.5:
                back, k = back + float(np.linalg.norm(trail[k] - trail[k - 1])), k - 1
            if d < 2.4:
                L["follow"] = False
                walk_parent_to((fx, fy))
            elif float(np.linalg.norm(parent.pos - trail[k])) > 0.6 and not parent.path:
                parent.go(trail[max(0, k - 3):k + 1])
        if d > 2.0:
            goal = (fx + (x - fx) * 1.8 / d, fy + (y - fy) * 1.8 / d)
            return None
        return facing(pose, (fx, fy))
    return facing(pose, child.pos)


def lost_summary():
    L, d = lost, lambda a, b: round(float(math.hypot(a[0] - b[0], a[1] - b[1])), 2)
    if L["state"] is None:
        return dict(reported=False)
    out = dict(robot=ROBOT, role=L.get("role"), reported_at=round(L["report_t"], 2),
               found_after=round(L["found_at"] - L["report_t"], 1) if "found_at" in L else None,
               reunited_after=round(L["done_at"] - L["report_t"], 1) if "done_at" in L else None)
    s, cr = L.get("s"), L["child_at_report"]
    if s:
        out.update(remembered=L["best"]["score"] > 0, last_seen_ago=round(L["report_t"] - s["t"], 1), last_seen_by=s.get("robot"),
                   last_seen_error=d((s["x"], s["y"]), cr), first_guess_error=d(L["first_peak"], cr) if L["first_peak"] else None,
                   right_child=d(L["found_xy"], L["child_at_found"]) < 1.0 if "child_at_found" in L else None)
    return out
unmapped_hit = set()


def step_walker(w):
    if w["turn"] > 0:  # turning on the spot at a path end
        w["turn"] -= DT
        u = (w["b"] - w["a"]) * w["dir"] / w["L"]
        w["r"].setSFRotation([0, 0, 1, math.atan2(u[1], u[0]) + math.pi * max(0.0, w["turn"]) / 0.8])
        w["vel"] = np.zeros(2)
        return
    w["s"] += w["dir"] * w["v"] * DT
    if not 0 <= w["s"] <= w["L"]:
        w["s"] = min(max(w["s"], 0.0), w["L"]); w["dir"] *= -1; w["turn"] = 0.8
    u = (w["b"] - w["a"]) / w["L"]
    w["pos"], w["vel"] = w["a"] + u * w["s"], u * w["dir"] * w["v"]
    w["t"].setSFVec3f([float(w["pos"][0]), float(w["pos"][1]), 0.0])
    w["r"].setSFRotation([0, 0, 1, math.atan2(w["vel"][1], w["vel"][0])])


FW, FH = face.getWidth(), face.getHeight()
_face_state = None


def draw_face(gaze, blink, mood):
    """Saathi's eyes on the mast screen: they follow the nearest person, blink, and narrow while waiting."""
    global _face_state
    st = (round(gaze, 1), blink, mood)
    if st == _face_state:
        return
    _face_state = st
    face.setColor(0x0B3D38); face.fillRectangle(0, 0, FW, FH)
    face.setColor(0xFFFFFF)
    for cx in (int(FW * 0.32), int(FW * 0.68)):
        if blink:
            face.fillRectangle(cx - 30, int(FH * 0.44), 60, 7)
            continue
        ry = 22 if mood == "wait" else 34
        face.fillOval(cx, int(FH * 0.44), 30, ry)
        face.setColor(0x0B1F1C); face.fillOval(cx + int(gaze * 12), int(FH * 0.46), 12, min(14, ry - 6)); face.setColor(0xFFFFFF)
    cx, cy = FW / 2, FH * 0.66
    outer = [(cx + 40 * math.cos(a), cy + 16 * math.sin(a)) for a in np.linspace(0.25, math.pi - 0.25, 12)]
    inner = [(cx + 34 * math.cos(a), cy + 9 * math.sin(a)) for a in np.linspace(math.pi - 0.25, 0.25, 12)]
    face.fillPolygon([int(p[0]) for p in outer + inner], [int(p[1]) for p in outer + inner])


def frame_bgr():
    return np.frombuffer(cam.getImage(), np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def depth_m():
    return np.ctypeslib.as_array(rf.getRangeImage(data_type="buffer"), shape=(H * W,)).reshape(H, W)


def snapshot(t, status, boxes, people_true, pose):
    """Black box: the camera frame at the moment of a decision, with what Saathi saw drawn on it, and why."""
    img = frame_bgr()
    for tid, (x0, y0, x1, y1), z in boxes:
        col = (60, 60, 220) if z < 1.5 else (32, 160, 240) if z < 3 else (118, 133, 10)
        cv2.rectangle(img, (x0, y0), (x1, y1), col, 2)
        cv2.putText(img, f"{tid if isinstance(tid, str) else f'P{tid}'} {z:.1f} m", (x0 + 3, max(14, y0 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    near = sorted(((math.hypot(p["x"] - pose[0], p["y"] - pose[1]), p["id"]) for p in people_true))[:3]
    tag = f"{t:06.2f}"
    cv2.imwrite(os.path.join(OUT, "blackbox", f"{tag}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    blackbox.write(json.dumps({"t": round(t, 2), "decision": status, "speed": round(brain.v, 2), "pose": [round(v, 2) for v in pose],
                               "nearest": [[n, round(d, 2)] for d, n in near], "in_view": [f"P{tid}" for tid, _, _ in boxes],
                               "frame": f"blackbox/{tag}.jpg"}) + "\n")
    blackbox.flush()


_x0, _y0, _ = me.getField("translation").getSFVec3f()  # where the world put this Saathi
_far = goal and math.hypot(goal[0] - _x0, goal[1] - _y0) > 0.5
pose = (_x0, _y0, math.atan2(goal[1] - _y0, goal[0] - _x0) if _far else my_r.getSFRotation()[3])
last_status, last_event, chase_pos, nxt, k, boxes, arrived_at = "", -9.0, None, 0.0, 0, [], None
my_r.setSFRotation([0, 0, 1, pose[2]])  # face the first goal at the start
if args.get("calib"):  # drive test: 2 s forward, 2 s sideways (left), 2 s turning left; print where physics put the robot
    marks = []
    while bot.step(DT_MS) != -1:
        t = bot.getTime()
        drive(*((0.3, 0, 0) if t < 2 else (0, 0.3, 0) if t < 4 else (0, 0, 0.6) if t < 6 else (0, 0, 0)))
        if not marks or t - marks[-1][0] >= 0.5:
            marks.append([round(t, 2)] + [round(v, 3) for v in measured_pose()] + [round(me.getPosition()[2], 3)])
        if t > 6.2:
            json.dump(marks, open(os.path.join(OUT, "calib.json"), "w"))
            bot.simulationQuit(0)
loc_err = []
events = open(os.path.join(OUT, "events.jsonl"), "w")
states = open(os.path.join(OUT, "states.jsonl"), "w")
blackbox = open(os.path.join(OUT, "blackbox.jsonl"), "w")
fall_log = open(os.path.join(OUT, "fall_truth.jsonl"), "w")
alerts = open(os.path.join(OUT, "alerts.jsonl"), "w")

while bot.step(DT_MS) != -1:
    t = bot.getTime()
    k += 1
    pose = measured_pose()
    desired = pose
    if FALL_AT and WORLD and fallen_who is None and t >= FALL_AT:  # the walker most in front of Saathi falls
        def in_front(w):
            dx, dy = w["pos"][0] - pose[0], w["pos"][1] - pose[1]
            a = (math.atan2(dy, dx) - pose[2] + math.pi) % (2 * math.pi) - math.pi
            return abs(a) < 0.45 and 2.5 < math.hypot(dx, dy) < 8 and not grid.inside_box(w["pos"][0], w["pos"][1], 0.6)
        cand = sorted((w for w in walkers if in_front(w)), key=lambda w: math.hypot(w["pos"][0] - pose[0], w["pos"][1] - pose[1]))
        if cand:
            fallen_who = cand[0]
            fx, fy = fallen_who["pos"]
            body = bot.getFromDef(f"FALLEN_{fallen_who['id']}")
            body.getField("translation").setSFVec3f([float(fx), float(fy), 0.13])
            body.getField("rotation").setSFRotation([1, 0, 0, -1.5708])  # flat on the back
            fallen_who["t"].setSFVec3f([0.0, 0.0, -10.0])
            walkers.remove(fallen_who)
            standers["fallen"] = np.array([fx, fy])
            fall_log.write(json.dumps({"t": round(t, 2), "who": fallen_who["id"], "at": [round(float(fx), 2), round(float(fy), 2)]}) + "\n"); fall_log.flush()
    for w in walkers:
        if WORLD:
            step_walker(w)
        else:
            p = np.array(w["t"].getSFVec3f()[:2])
            w["vel"], w["pos"] = (p - w["pos"]) / DT, p
    for a in actors.values():
        a.step(t) if WORLD else a.sync()
    while radio_rx.getQueueLength() > 0:  # what the other Saathis said
        heard(t, json.loads(radio_rx.getString()))
        radio_rx.nextPacket()
    if k % 30 == 0:
        send(dict(k="pose", x=round(pose[0], 2), y=round(pose[1], 2)))
    if LIVE and k % 10 == 0:
        for c in commands():
            obey(t, c)
    people_true = [dict(id=w["id"], x=float(w["pos"][0]), y=float(w["pos"][1]), vx=float(w["vel"][0]), vy=float(w["vel"][1])) for w in walkers] + \
                  [dict(id=n, x=float(p[0]), y=float(p[1]), vx=0.0, vy=0.0) for n, p in standers.items()] + \
                  [dict(id=n, x=float(a.pos[0]), y=float(a.pos[1]), vx=float(a.vel[0]), vy=float(a.vel[1])) for n, a in actors.items()]
    if eyes and k % 2 == 0:  # YOLO at ~15 Hz
        dm = depth_m()
        fr = frame_bgr()
        boxes = eyes.see(fr, dm, pose, t)
        if LOST and k % 4 == 0:
            lost_see(t, fr, boxes, pose)
        if memory.update(depth_points(dm, [b for _, b, _ in boxes], pose, eyes.f), eyes.people(t)) and t - last_event > 1.0:
            seen = sorted(namer.look(frame_bgr(), dm, pose), key=lambda s: -s[1]) if namer else []
            near = [s for s in seen if min(math.hypot(s[2][0] - a, s[2][1] - b) for a, b in memory.points()) < 1.0]
            what = f"a {near[0][0]}" if near else "something"
            note = f"Found {what} that is not on my map: going around it"
            events.write(json.dumps({"t": round(t, 2), "status": note}) + "\n"); events.flush()
            snapshot(t, note, boxes, people_true, pose)
            last_status, last_event = note, t
        for p in eyes.people(t):  # how far is each estimate from the nearest real person?
            d = min(math.hypot(p["x"] - q["x"], p["y"] - q["y"]) for q in people_true)
            if d < 1.5:
                loc_err.append(d)
    if FIND and found is None and eyes and k % 10 == 0:  # look for the thing, about 3 times a second
        for name, s, (ox, oy), box in namer.look(frame_bgr(), depth_m(), pose):
            if name == FIND:
                sightings.append((ox, oy))
                if len(sightings) >= 3 and math.hypot(ox - sightings[-3][0], oy - sightings[-3][1]) < 0.8:
                    found = (ox, oy)
                    d = math.hypot(ox - pose[0], oy - pose[1])
                    goal = (ox + (pose[0] - ox) * 1.0 / d, oy + (pose[1] - oy) * 1.0 / d)  # stop 1 m in front of it
                    brain.path, brain.next_plan = None, 0.0
                    note = f"Found the {FIND} {d:.1f} m away: going there"
                    events.write(json.dumps({"t": round(t, 2), "status": note}) + "\n"); events.flush()
                    snapshot(t, note, [(f"{FIND} {s:.2f}", box, d)], people_true, pose)
                    last_status, last_event = note, t
                break
    if namer and fall_state is None and k % 4 == 2:  # fall classifier, ~8 Hz: open-vocab "person lying on the floor" + a wide box
        for name, s, (lx, ly), (x0, y0, x1, y1) in namer.look(frame_bgr(), depth_m(), pose):
            if name == "person lying on the floor" and (x1 - x0) > 1.2 * (y1 - y0):
                lying = [p for p in lying if t - p[2] < 1.5 and math.hypot(p[0] - lx, p[1] - ly) < 0.8] + [(lx, ly, t)]
                if len(lying) >= 3:
                    fall_seen = (sum(p[0] for p in lying) / len(lying), sum(p[1] for p in lying) / len(lying))
                break
    if eyes and fall_state is None and fall_seen:  # someone is lying on the floor: alert, go to them, stay, then carry on
        fx, fy = fall_seen
        fall_state, trip_goal = "going", goal
        d = math.hypot(fx - pose[0], fy - pose[1])
        goal = (fx + (pose[0] - fx) * 1.2 / d, fy + (pose[1] - fy) * 1.2 / d)
        brain.path, brain.next_plan = None, 0.0
        note = f"Someone has fallen near {AREA(fx, fy)} ({d:.1f} m): alerting the nurse station and going to them"
        alert = {"t": round(t, 2), "to": "Nurse Station", "message": f"Patient fallen near {AREA(fx, fy)}", "at": [round(fx, 2), round(fy, 2)]}
        alerts.write(json.dumps(alert) + "\n"); alerts.flush()
        # The thinking brain (a small VLM, ~3 s) adds what it sees to the alert, in its own process: the reflex loop never waits for it.
        apath, fpath = os.path.join(OUT, "alert_fall.json"), os.path.join(OUT, "alert_fall.jpg")
        cv2.imwrite(fpath, frame_bgr()); json.dump(alert, open(apath, "w"))
        root = os.path.join(os.path.dirname(__file__), "..", "..")
        subprocess.Popen([os.path.join(root, ".venv-brain", "bin", "python"), os.path.join(root, "tools", "vlm_see.py"), "--alert", apath, fpath],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        events.write(json.dumps({"t": round(t, 2), "status": note}) + "\n"); events.flush()
        snapshot(t, note, boxes, people_true, pose)
        last_status, last_event = note, t
    people = eyes.people(t) if eyes else people_true
    pairs = eyes.conversations(t) if eyes else true_pairs
    scan = lidar_points(lidar.getRangeImage(), pose, grid) if eyes else None
    if eyes:
        eyes.feel(scan, pose, t)
    if LOST and lost["state"] is None and t >= REPORT:
        lost_report(t, pose)
    hold = pose if paused else lost_step(t, pose) if LOST and lost["state"] else None  # stopped by voice, turning to look, or staying
    if hold is not None:
        desired, guard, arrived = hold, False, False
        brain.v, brain.status = 0.0, "Stopped: someone said \"Saathi, ruko\"" if paused else {"look": "Looking all around for the child", "stay": "Staying with the child until the father comes",
                                      "with_parent": "Staying with the father", "escort": "Waiting with the father near the child",
                                      "done": "Father and son are together"}.get(lost["state"], brain.status)
    elif goal is None:  # not found yet: turn on the spot and look; then try the next spot
        if scan_left > 0:
            desired, scan_left = (pose[0], pose[1], pose[2] + 0.6 * DT), scan_left - 0.6 * DT
            brain.status, guard, arrived = f"Looking around for the {FIND}", False, False
        else:
            spot, scan_left = (spot + 1) % len(SCAN_SPOTS), 2 * math.pi
            goal = SCAN_SPOTS[spot]
    if goal is not None and hold is None:
        desired, guard, arrived = brain.step(t, DT, pose, goal, people, pairs, scan, memory.points() if eyes else None)
        if fall_state == "going" and (arrived or math.hypot(pose[0] - fall_seen[0], pose[1] - fall_seen[1]) < 1.5):
            fall_state, fall_t = "staying", t
        if fall_state == "staying":
            arrived, brain.status = False, "Staying with the patient until the nurse comes"
            if t - fall_t > 6.0:  # the nurse has taken over (simulated): back to the trip
                fall_state, goal = "done", trip_goal
                brain.path, brain.next_plan = None, 0.0
        elif fall_state == "going":
            arrived, brain.status = False, "Going to the person who fell"
        if FIND and found is None and arrived:  # reached a look-around spot, still not found
            goal = None
            brain.path = None
    for n, (cx, cy), (sx, sy) in unmapped:  # did the robot drive into something that is not on its map?
        if abs(pose[0] - cx) < sx / 2 + 0.25 and abs(pose[1] - cy) < sy / 2 + 0.25:
            unmapped_hit.add(n)
    metrics.update(t, pose, brain.v, people_true, true_pairs, guard)
    if arrived and arrived_at is None:
        arrived_at = t
    x, y, th = pose
    dx, dy = desired[0] - x, desired[1] - y  # what the brain wants this step, as a body velocity, to the motors
    drive((dx * math.cos(th) + dy * math.sin(th)) / DT, (-dx * math.sin(th) + dy * math.cos(th)) / DT,
          ((desired[2] - th + math.pi) % (2 * math.pi) - math.pi) / DT)

    target = f"the {FIND}" if FIND else ("my post at the help desk" if GOAL.startswith("at:") else GOAL) if not (LOST and lost["state"]) else \
        "where the child may be" if lost["state"] in ("search", "go") else "the father" if lost["state"] == "with_parent" else "the child"
    status = brain.status.replace("Arrived", f"Arrived at {target}").replace("Going,", f"Going to {target},")
    kind = status.split()[0]
    if status != last_status and (kind in ("Safety", "Arrived") or (kind != last_status.split(" ")[0] and t - last_event > 0.6) or t - last_event > 1.5):
        # one entry per decision, not per frame
        events.write(json.dumps({"t": round(t, 2), "status": status}) + "\n"); events.flush()
        if kind != "Going":
            snapshot(t, status, boxes, people_true, pose)
        last_status, last_event = status, t
    near = min(people_true, key=lambda p: math.hypot(p["x"] - x, p["y"] - y))
    gaze = max(-1.0, min(1.0, (math.atan2(near["y"] - y, near["x"] - x) - th + math.pi) % (2 * math.pi) - math.pi))
    draw_face(gaze, (t % 4.2) < 0.15, "wait" if brain.v < 0.1 and not arrived else "happy")

    # Chase camera: behind and to the left of Saathi, eased so it doesn't jitter.
    if CHASE_ON:
        fwd, left = np.array([math.cos(th), math.sin(th)]), np.array([-math.sin(th), math.cos(th)])
        want = np.clip(np.array([x, y]) - 3.6 * fwd + 1.6 * left, [-8.6, -5.6], [8.6, 5.6])  # stay inside the hall, not behind the glass doors
        chase_pos = want if chase_pos is None else chase_pos + (want - chase_pos) * 0.06
        look = np.array([x, y]) + 0.8 * fwd
        ch_t.setSFVec3f([float(chase_pos[0]), float(chase_pos[1]), 2.2])
        ch_r.setSFRotation(yaw_pitch_rotation(math.atan2(look[1] - chase_pos[1], look[0] - chase_pos[0]),
                                              math.atan2(2.2 - 0.6, float(np.linalg.norm(look - chase_pos)))))

    if EVERY > 0 and t + 1e-6 >= nxt:
        tag = f"{t:06.2f}"
        cam.saveImage(os.path.join(OUT, f"cam_{tag}.png"), 100)
        np.save(os.path.join(OUT, f"depth_{tag}.npy"), depth_m().astype(np.float16))
        np.save(os.path.join(OUT, f"lidar_{tag}.npy"), np.array(lidar.getRangeImage(), np.float32))
        states.write(json.dumps({"t": round(t, 2), "robot": [round(x, 3), round(y, 3), round(th, 4)], "v": round(brain.v, 3), "status": status,
                                 "path": [[round(a, 2), round(b, 2)] for a, b in (brain.path or [])],
                                 "people": {p["id"]: [round(p["x"], 3), round(p["y"], 3)] for p in people_true},
                                 "seen": {p["id"]: [round(p["x"], 3), round(p["y"], 3)] for p in people} if eyes else {},
                                 **({"lost": lost["state"], "belief": [[round(float(a), 2), round(float(b), 2)] for a, b in lost["belief"]]} if LOST else {})}) + "\n")
        states.flush()
        nxt += EVERY
    if FIND and found is None:
        arrived_at = None
    if t >= UNTIL or (arrived_at is not None and t > arrived_at + 3 and not LOST) or (LOST and lost.get("done_at") and t > lost["done_at"] + 3):
        summary = dict(mode=MODE, perception=PERCEPTION, goal=GOAL, fall_detected=fall_seen is not None, found=[round(v, 2) for v in found] if FIND and found else None, arrived=arrived_at is not None, time=round(arrived_at or t, 2),
                       near_misses=metrics.near, conversation_cuts=metrics.cuts, unmapped_hits=sorted(unmapped_hit), min_dist=round(metrics.min_d, 3), safety_stops=metrics.stops,
                       localization_error_median=round(float(np.median(loc_err)), 3) if loc_err else None,
                       localization_error_p90=round(float(np.percentile(loc_err, 90)), 3) if loc_err else None,
                       **({"lost": lost_summary()} if LOST else {}))
        json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
        bot.simulationQuit(0)
