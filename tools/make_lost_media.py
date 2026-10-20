"""Turns a Saathi Parivaar run (one or two Saathis finding a lost child) into a video and stills.

Per frame: the chase camera; a map with the Saathis, the father, the boy and the memory's guess of where he is now (particles);
the Saathis' Hinglish group chat from their event logs; the searching Saathi's camera; and, after the father's report, the
photos the shared memory matched to his words.
Usage: python tools/make_lost_media.py out/<run>   ->   out/media/<run>/{parivaar.mp4, stills/*.jpg}
"""
import glob, json, os, re, sys
import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.abspath(sys.argv[1])
MEDIA = os.path.join(ROOT, "out", "media", os.path.basename(RUN))
os.makedirs(os.path.join(MEDIA, "stills"), exist_ok=True)
DIRS = [RUN] + sorted(glob.glob(os.path.join(RUN, "r[0-9]")))  # Saathi-1 writes RUN, Saathi-2 writes RUN/r2
load = lambda d, n: [json.loads(q) for q in open(os.path.join(d, n))] if os.path.exists(os.path.join(d, n)) else []
STATES = [load(d, "states.jsonl") for d in DIRS]
CHAT = sorted(((e["t"], e["status"]) for d in DIRS for e in load(d, "events.jsonl")
               if re.search(r"Saathi-|Help desk|Yaaddasht|Mil gaya|ruka hoon|Papa|mita di|Awaaz|ishara", e["status"])), key=lambda c: c[0])
REPORT = next((t for t, s in CHAT if s.startswith("Help desk")), None)
MATCH = next((p for d in DIRS for p in [os.path.join(d, "memory_match.jpg")] if os.path.exists(p)), None)
SEARCHER = next((i for i, st in enumerate(STATES) if any(s.get("lost") in ("search", "look", "go") for s in st)), 0)
TEAL, DARK, AMBER, RED, BLUE, INK, PAPER = (118, 133, 10), (60, 90, 20), (32, 160, 240), (40, 40, 220), (200, 120, 40), (30, 30, 30), (246, 247, 245)
FONT = cv2.FONT_HERSHEY_SIMPLEX
PLACES = {"REGISTRATION": (-6.3, 5.4), "PHARMACY": (-0.8, 5.4), "RADIOLOGY": (5.0, 5.4), "EMERGENCY": (-5, -5.5), "LAB": (2.5, -5.5),
          "WARDS & LIFT": (7.9, 1.5), "WATER COOLER": (7.0, -4.5), "ENTRANCE": (-8.0, 0)}


def text(img, s, org, scale=0.55, color=INK, thick=1, bg=None, pad=4):
    (w, h), base = cv2.getTextSize(s, FONT, scale, thick)
    if bg is not None:
        cv2.rectangle(img, (org[0] - pad, org[1] - h - pad), (org[0] + w + pad, org[1] + base + pad // 2), bg, -1)
    cv2.putText(img, s, org, FONT, scale, color, thick, cv2.LINE_AA)


def wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return out + [line]


def at(st, t):
    return min(st, key=lambda s: abs(s["t"] - t)) if st else None


def map_view(t, w, h):
    img = np.full((h, w, 3), PAPER, np.uint8)
    sx, sy = (w - 20) / 18, (h - 60) / 12
    P = lambda x, y: (int(10 + (x + 9) * sx), int(50 + (6 - y) * sy))
    text(img, "MAP  orange glow: where the memory thinks the boy is now", (12, 30), 0.5, INK, 1)
    cv2.rectangle(img, P(-9, 6), P(9, -6), (90, 90, 90), 2)
    for name, (x, y) in PLACES.items():
        text(img, name, (P(x, y)[0] - 40, P(x, y)[1] + 4), 0.35, (120, 120, 120))
    st = [at(s, t) for s in STATES]
    if st[SEARCHER] and st[SEARCHER].get("belief") and st[SEARCHER].get("lost") in ("search", "look"):  # the guess, while searching
        heat = np.zeros((h, w), np.float32)
        for x, y in st[SEARCHER]["belief"]:
            px, py = P(x, y)
            if 0 <= px < w and 0 <= py < h:
                heat[py, px] += 1
        heat = cv2.GaussianBlur(heat, (0, 0), 14)
        a = np.clip(heat / max(1e-6, heat.max()), 0, 1)[..., None] * 0.75
        img[:] = (img * (1 - a) + np.array(AMBER, np.float32) * a).astype(np.uint8)
    for name, (x, y) in (st[0] or {}).get("people", {}).items():
        if name in ("L", "P"):
            continue
        cv2.circle(img, P(x, y), 5, (150, 150, 150), -1, cv2.LINE_AA)
    for name, label, col, dx, dy in (("P", "papa", BLUE, -52, -10), ("L", "beta", RED, 10, 16)):  # labels on opposite sides
        if st[0] and name in st[0]["people"]:
            x, y = st[0]["people"][name]
            cv2.circle(img, P(x, y), 8, col, -1, cv2.LINE_AA)
            text(img, label, (min(P(x, y)[0] + dx, w - 50), P(x, y)[1] + dy), 0.45, col, 1)
    for i, s in enumerate(st):
        if not s:
            continue
        rx, ry, th = s["robot"]
        pts = np.array([[0.5, 0], [-0.35, 0.33], [-0.35, -0.33]])
        poly = np.array([P(rx + px * np.cos(th) - py * np.sin(th), ry + px * np.sin(th) + py * np.cos(th)) for px, py in pts])
        cv2.fillConvexPoly(img, poly, TEAL if i == 0 else DARK, cv2.LINE_AA)
        lx = min(P(rx, ry)[0] + 12, w - 80)
        text(img, f"Saathi-{i + 1}" if len(STATES) > 1 else "Saathi", (lx, P(rx, ry)[1] - 14 - 14 * i), 0.45, TEAL if i == 0 else DARK, 1)
    return img


def chat_view(t, w, h):
    img = np.full((h, w, 3), (36, 44, 40), np.uint8)
    text(img, "SAATHI PARIVAAR  group chat" if len(STATES) > 1 else "SAATHI  thinking aloud", (14, 30), 0.6, (180, 230, 220), 1)
    lines = []
    for tt, s in [c for c in CHAT if c[0] <= t][-6:]:
        for i, ln in enumerate(wrap(s, 50)):
            lines.append((f"{tt:5.1f}s  {ln}" if i == 0 else f"        {ln}", tt))
    for i, (ln, tt) in enumerate(lines[-13:]):
        text(img, ln, (14, 66 + i * 36), 0.55, (255, 255, 255) if t - tt < 4 else (160, 170, 165), 1)
    return img


def frames(d, prefix):
    return {float(re.search(r"_(\d+\.\d+)\.", p).group(1)): p for p in glob.glob(os.path.join(d, f"{prefix}_*.*"))}


chases, cams = frames(RUN, "chase"), frames(DIRS[SEARCHER], "cam")
times = sorted(chases)
step = (times[1] - times[0]) if len(times) > 1 else 0.5
vid = cv2.VideoWriter(os.path.join(MEDIA, "parivaar.mp4"), cv2.VideoWriter_fourcc(*"avc1"), 10, (1920, 1080))
match = cv2.imread(MATCH) if MATCH else None
for k, t in enumerate(times):
    D = np.full((1080, 1920, 3), 15, np.uint8)
    D[0:720, 0:1280] = cv2.resize(cv2.imread(chases[t]), (1280, 720))
    text(D, f"SAATHI PARIVAAR  Webots OPD simulation   t = {t:5.1f} s", (16, 36), 0.8, (255, 255, 255), 2, (15, 107, 92), 8)
    D[0:540, 1280:1920] = map_view(t, 640, 540)
    D[540:1080, 1280:1920] = chat_view(t, 640, 540)
    if cams:
        ct = min(cams, key=lambda c: abs(c - t))
        D[720:1080, 0:480] = cv2.resize(cv2.imread(cams[ct]), (480, 360))
        text(D, f"Saathi-{SEARCHER + 1}'s camera" if len(STATES) > 1 else "Saathi's camera", (12, 748), 0.55, (255, 255, 255), 1, (20, 20, 20))
    panel = np.full((360, 800, 3), (28, 30, 30), np.uint8)
    if REPORT is not None and t >= REPORT and match is not None:
        strip = cv2.resize(match, (int(match.shape[1] * 250 / match.shape[0]), 250))[:, :760]
        panel[70:320, 20:20 + strip.shape[1]] = strip
        text(panel, "YAADDASHT: people the shared memory matched to the father's words (best first)", (20, 40), 0.55, (180, 230, 220), 1)
        text(panel, "clothes and height only: no face is stored", (20, 348), 0.5, (150, 160, 155), 1)
    else:
        text(panel, "Every Saathi remembers who it saw: where, when, which way.", (20, 160), 0.62, (180, 230, 220), 1)
        text(panel, "Clothes and height only, never a face.", (20, 200), 0.62, (180, 230, 220), 1)
    D[720:1080, 480:1280] = panel
    for _ in range(max(1, round(step * 10 / 2))):  # twice real time
        vid.write(D)
    if k % 10 == 0 or (REPORT and abs(t - REPORT) < step):
        cv2.imwrite(os.path.join(MEDIA, "stills", f"parivaar_{t:06.2f}.jpg"), D, [cv2.IMWRITE_JPEG_QUALITY, 90])
vid.release()
print(f"{len(times)} frames, {len(CHAT)} chat lines, searcher Saathi-{SEARCHER + 1} ->", MEDIA)
