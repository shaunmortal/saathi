"""Turns a Webots run (out/run) into a control-room video and stills.

Per frame: YOLO11s + ByteTrack on Saathi's camera, distance to each person from the depth camera,
the LiDAR scan, a top-down map from the run's ground truth, and the planner's status as "thinking aloud".
Usage: python tools/make_media.py [run_dir]   ->   out/media/{dashboard.mp4, chase.mp4, cctv.mp4, front.mp4, stills/*.jpg}
"""
import glob, json, math, os, re, sys
import cv2
import numpy as np
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "run"))
MEDIA = os.path.join(ROOT, "out", "media", os.path.basename(RUN))
os.makedirs(os.path.join(MEDIA, "stills"), exist_ok=True)
scene = json.load(open(os.path.join(ROOT, "controllers", "saathi", "scene.json")))
states = [json.loads(l) for l in open(os.path.join(RUN, "states.jsonl"))]
events = [json.loads(l) for l in open(os.path.join(RUN, "events.jsonl"))]
TEAL, AMBER, RED, INK, PAPER = (118, 133, 10), (32, 160, 240), (60, 60, 220), (30, 30, 30), (246, 247, 245)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def tag(path):
    return re.search(r"_(\d+\.\d+)\.", path).group(1)


def frames(prefix):
    return {tag(p): p for p in glob.glob(os.path.join(RUN, f"{prefix}_*.*"))}


def text(img, s, org, scale=0.55, color=INK, thick=1, bg=None, pad=4):
    (w, h), base = cv2.getTextSize(s, FONT, scale, thick)
    if bg is not None:
        cv2.rectangle(img, (org[0] - pad, org[1] - h - pad), (org[0] + w + pad, org[1] + base + pad // 2), bg, -1)
    cv2.putText(img, s, org, FONT, scale, color, thick, cv2.LINE_AA)


def plain(s):
    """Planner status uses the sim's ground-truth names (W5, T2); the camera view knows people only by track ID."""
    return re.sub(r"\b[WTQ]\d\b", "a person", s)


PIDS = {}  # tracker ID -> P1, P2, ... in order of first sighting


def annotate(img, depth, res, t):
    out = img.copy()
    people = []
    if res.boxes is not None and len(res.boxes):
        ids = res.boxes.id.int().tolist() if res.boxes.id is not None else [None] * len(res.boxes)
        for (x0, y0, x1, y1), conf, tid in zip(res.boxes.xyxy.int().tolist(), res.boxes.conf.tolist(), ids):
            # The person is the nearest thing inside their own box; the upper 70% leaves out the floor at their feet.
            patch = depth[max(y0, 0):max(y0 + (y1 - y0) * 7 // 10, 1), max(x0, 0):max(x1, 1)].astype(np.float32)
            patch = patch[np.isfinite(patch)]
            d = float(np.percentile(patch, 25)) if patch.size else float("nan")
            if tid is not None:
                tid = PIDS.setdefault(tid, len(PIDS) + 1)
            col = RED if d < 1.5 else AMBER if d < 3 else TEAL
            cv2.rectangle(out, (x0, y0), (x1, y1), col, 2, cv2.LINE_AA)
            label = (f"P{tid}" if tid is not None else "person") + (f"  {d:.1f} m" if d == d else "")
            text(out, label, (x0 + 4, y0 - 6 if y0 > 24 else y0 + 18), 0.5, (255, 255, 255), 1, col)
            people.append(d)
    text(out, f"SAATHI CAM-1  YOLO11s + ByteTrack  t={t:5.1f}s", (10, img.shape[0] - 12), 0.5, (255, 255, 255), 1, (20, 20, 20))
    return out, people


def depth_view(depth, w, h):
    d = depth.astype(np.float32)
    bad = ~np.isfinite(d)
    v = np.clip((np.where(bad, 10, d) - 0.3) / 9.7, 0, 1)
    col = cv2.applyColorMap((255 - v * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    col[bad] = 0
    col = cv2.resize(col, (w, h), interpolation=cv2.INTER_AREA)
    text(col, "DEPTH CAMERA  near = red", (8, 18), 0.45, (255, 255, 255), 1, (20, 20, 20))
    return col


def lidar_view(ranges, w, h):
    img = np.full((h, w, 3), 24, np.uint8)
    cx, cy, s = w // 2, h // 2 + 20, min(w, h) / 2 / 8.0  # 8 m to the edge
    for r_m in (2, 4, 6, 8):
        cv2.circle(img, (cx, cy), int(r_m * s), (60, 60, 60), 1, cv2.LINE_AA)
    n = len(ranges)
    for i, r in enumerate(ranges):
        if not np.isfinite(r) or r <= 0:
            continue
        a = math.pi - i * 2 * math.pi / n  # rays sweep from behind-left, clockwise; forward is up
        x, y = int(cx - r * s * math.sin(a)), int(cy - r * s * math.cos(a))
        c = RED if r < 1.0 else AMBER if r < 2.0 else (220, 210, 120)
        cv2.circle(img, (x, y), 2, c, -1, cv2.LINE_AA)
    cv2.rectangle(img, (cx - 6, cy - 9), (cx + 6, cy + 9), TEAL, -1)
    text(img, "360 LIDAR  rings every 2 m", (8, 18), 0.45, (230, 230, 230), 1)
    return img


def map_view(st, trail, w, h):
    img = np.full((h, w, 3), PAPER, np.uint8)
    sx, sy = (w - 20) / 18, (h - 20) / 12
    P = lambda x, y: (int(10 + (x + 9) * sx), int(10 + (6 - y) * sy))
    cv2.rectangle(img, P(-9, 6), P(9, -6), (90, 90, 90), 2)
    for name, (x, y) in [("REG", (-6.3, 5.6)), ("PHARMACY", (-0.8, 5.6)), ("RADIOLOGY", (5.0, 5.6)), ("EMERGENCY", (-5, -5.6)), ("LAB", (2.5, -5.6)), ("WARDS", (8.2, 1.5)), ("ENTRY", (-8.3, 0))]:
        text(img, name, (P(x, y)[0] - 30, P(x, y)[1] + 4), 0.38, (110, 110, 110))
    route = scene["route"]
    for a, b in zip(route, route[1:]):
        cv2.line(img, P(*a), P(*b), (200, 220, 210), 6, cv2.LINE_AA)
    for a, b in zip(trail, trail[1:]):
        cv2.line(img, P(*a), P(*b), TEAL, 2, cv2.LINE_AA)
    for a, b in zip(st.get("path", []), st.get("path", [])[1:]):
        cv2.line(img, P(*a), P(*b), (182, 215, 160), 2, cv2.LINE_AA)
    for name, (x, y) in st["people"].items():
        cv2.circle(img, P(x, y), 6, (80, 80, 80) if name[0] != "T" else (170, 120, 60), -1, cv2.LINE_AA)
    for name, (x, y) in st.get("seen", {}).items():  # where Saathi thinks people are (camera + LiDAR)
        cv2.circle(img, P(x, y), 11, TEAL, 2, cv2.LINE_AA)
    if st.get("seen"):
        text(img, "dots: real people   rings: what Saathi sees", (16, 48), 0.45, (90, 90, 90))
    rx, ry, th = st["robot"]
    pts = np.array([[0.45, 0], [-0.3, 0.3], [-0.3, -0.3]])
    poly = np.array([P(rx + px * math.cos(th) - py * math.sin(th), ry + px * math.sin(th) + py * math.cos(th)) for px, py in pts])
    cv2.fillConvexPoly(img, poly, TEAL, cv2.LINE_AA)
    return img


def think_view(t, w, h, v):
    img = np.full((h, w, 3), (36, 44, 40), np.uint8)
    text(img, "THINKING ALOUD", (12, 26), 0.55, (180, 230, 220), 1)
    past = [e for e in events if e["t"] <= t][-6:]
    for i, e in enumerate(reversed(past)):
        c = (255, 255, 255) if i == 0 else (150, 160, 155)
        text(img, f"{e['t']:5.1f}s  {plain(e['status'])}", (12, 60 + i * 30), 0.52, c, 1)
    text(img, f"speed {v:.2f} m/s", (12, h - 14), 0.5, (180, 230, 220), 1)
    return img


cams, chases, cctvs, fronts = frames("cam"), frames("chase"), frames("cctv"), frames("front")
depths, lidars = frames("depth"), frames("lidar")
tags = sorted(set(cams) & set(chases) & set(depths) & set(lidars), key=float)
by_t = {f"{s['t']:06.2f}": s for s in states}
model = YOLO(os.path.join(ROOT, "models", "yolo11s.pt"))
fourcc = cv2.VideoWriter_fourcc(*"avc1")
vid = cv2.VideoWriter(os.path.join(MEDIA, "dashboard.mp4"), fourcc, 10, (1920, 1080))
trail, near_log = [], []
for k, tg in enumerate(tags):
    t = float(tg)
    st = by_t.get(tg) or min(states, key=lambda s: abs(s["t"] - t))
    trail.append(st["robot"][:2])
    img, depth = cv2.imread(cams[tg]), np.load(depths[tg])
    res = model.track(img, persist=True, classes=[0], conf=0.3, imgsz=640, tracker="bytetrack.yaml", verbose=False)[0]
    seen, dists = annotate(img, depth, res, t)
    near_log.append(min(dists) if dists else float("nan"))
    D = np.full((1080, 1920, 3), 15, np.uint8)
    D[0:720, 0:1280] = cv2.imread(chases[tg])
    text(D, "SAATHI  driving on camera + LiDAR" if st.get("seen") else "SAATHI  Webots OPD simulation", (16, 34), 0.8, (255, 255, 255), 2, (15, 107, 92), 8)
    D[720:1080, 0:640] = map_view(st, trail, 640, 360)
    D[720:1080, 640:1280] = lidar_view(np.load(lidars[tg]), 640, 360)
    D[0:480, 1280:1920] = seen
    D[480:720, 1280:1600] = depth_view(depth, 320, 240)
    D[480:720, 1600:1920] = cv2.resize(cv2.imread(fronts[tg]), (320, 240), interpolation=cv2.INTER_AREA) if tg in fronts else 0
    text(D, "FRONT CCTV", (1608, 498), 0.45, (255, 255, 255), 1, (20, 20, 20))
    D[720:1080, 1280:1920] = think_view(t, 640, 360, st["v"])
    vid.write(D)
    if k % 10 == 0:
        cv2.imwrite(os.path.join(MEDIA, "stills", f"dashboard_{tg}.jpg"), D, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(os.path.join(MEDIA, "stills", f"robotcam_{tg}.jpg"), seen, [cv2.IMWRITE_JPEG_QUALITY, 92])
vid.release()
for name, src in (("chase", chases), ("cctv", cctvs), ("front", fronts)):
    v = cv2.VideoWriter(os.path.join(MEDIA, f"{name}.mp4"), fourcc, 10, (1280, 720))
    for tg in sorted(src, key=float):
        v.write(cv2.imread(src[tg]))
    v.release()
ok = [d for d in near_log if d == d]
print(f"{len(tags)} frames; people boxed in {sum(1 for d in near_log if d == d)} frames; closest person seen {min(ok):.2f} m" if ok else "no detections")
print("wrote", MEDIA)
