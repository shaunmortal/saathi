"""Saathi's eyes: YOLO11 on the camera plus the 360° LiDAR, each person placed on the floor map and tracked there.

The camera sees who is a person, 60° ahead; the LiDAR sees everyone around at torso height, as short arcs of points.
Both feed one floor tracker, so someone crossing from the side is tracked before they enter the camera's view.

Tracking happens on the floor, not in the image: a person moves only ~8 cm between frames, so nearest-neighbour matching
with an alpha-beta filter gives stable IDs and a usable velocity, which the planner needs to predict where people will be.
Someone out of view is remembered for 2 s and moved along their last velocity. Two people standing still 0.6-1.6 m apart
are treated as a conversation (a queue gets the same respect).
"""
import math
import numpy as np
from ultralytics import YOLO

TAU_POS, TAU_VEL, GATE, FORGET, VMAX = 0.08, 0.5, 0.9, 1.2, 2.0  # filter time constants (s), matching gate (m), memory (s), m/s cap


class Eyes:
    def __init__(self, weights, width, height, hfov, cam_forward=0.11):
        self.model = YOLO(weights)
        self.W, self.f, self.cam_forward = width, (width / 2) / math.tan(hfov / 2), cam_forward
        self.tracks, self.next_id = {}, 1  # id -> {x, y, vx, vy, t, hits}

    def feel(self, points, pose, t):
        """LiDAR: split the returns into arcs; an arc 0.1-0.9 m wide is a person (or something like one) at its centre."""
        x, y = pose[0], pose[1]
        dets, arc = [], []
        for q in list(points) + [None]:
            if q is not None and (not arc or math.hypot(q[0] - arc[-1][0], q[1] - arc[-1][1]) < 0.35):
                arc.append(q)
                continue
            if len(arc) >= 2 and math.hypot(arc[-1][0] - arc[0][0], arc[-1][1] - arc[0][1]) < 0.9:
                cx, cy = sum(a[0] for a in arc) / len(arc), sum(a[1] for a in arc) / len(arc)
                d = math.hypot(cx - x, cy - y) or 1.0
                dets.append([cx + 0.12 * (cx - x) / d, cy + 0.12 * (cy - y) / d, None, d])
            arc = [q] if q is not None else []
        merged = []  # at torso height one person shows as body + swinging arms: arcs closer than 0.6 m are one person
        for dt_ in dets:
            m = next((g for g in merged if math.hypot(g[0] - dt_[0], g[1] - dt_[1]) < 0.6), None)
            if m:
                m[0], m[1] = (m[0] + dt_[0]) / 2, (m[1] + dt_[1]) / 2
            else:
                merged.append(dt_)
        self._update([tuple(g) for g in merged], t)

    def see(self, bgr, depth, pose, t):
        """Detect, place on the floor, track. -> boxes [(id, (x0, y0, x1, y1), distance)] for drawing."""
        x, y, th = pose
        res = self.model.predict(bgr, classes=[0], conf=0.35, imgsz=640, verbose=False)[0]
        dets = []
        for x0, y0, x1, y1 in (res.boxes.xyxy.int().tolist() if res.boxes is not None else []):
            patch = depth[max(y0, 0):max(y0 + (y1 - y0) * 7 // 10, 1), max(x0, 0):max(x1, 1)]
            patch = patch[np.isfinite(patch)]
            if not patch.size:
                continue
            z = float(np.percentile(patch, 25)) + 0.12  # depth sees the front of the body; its centre is ~12 cm further
            fx, fy = self.cam_forward + z, -z * ((x0 + x1) / 2 - self.W / 2) / self.f
            dets.append((x + fx * math.cos(th) - fy * math.sin(th), y + fx * math.sin(th) + fy * math.cos(th), (x0, y0, x1, y1), z))
        return self._update(dets, t)

    def _update(self, dets, t):
        pred = {k: (v["x"] + v["vx"] * (t - v["t"]), v["y"] + v["vy"] * (t - v["t"])) for k, v in self.tracks.items()}
        pairs = sorted((math.hypot(px - dx, py - dy), k, j) for k, (px, py) in pred.items() for j, (dx, dy, _, _) in enumerate(dets))
        used_t, used_d, boxes = set(), set(), []
        for d, k, j in pairs:  # greedy nearest-neighbour matching on the floor
            if d > GATE or k in used_t or j in used_d:
                continue
            used_t.add(k); used_d.add(j)
            tr, (px, py), (dx, dy, box, z) = self.tracks[k], pred[k], dets[j]
            dt = max(1e-3, t - tr["t"])
            rx, ry = dx - px, dy - py
            a, b = 1 - math.exp(-dt / TAU_POS), 1 - math.exp(-dt / TAU_VEL)  # gains scale with the update rate (LiDAR 31 Hz, camera 15 Hz)
            vx, vy = tr["vx"] + b * rx / dt, tr["vy"] + b * ry / dt
            s = min(1.0, VMAX / (math.hypot(vx, vy) or 1.0))
            tr.update(x=px + a * rx, y=py + a * ry, vx=vx * s, vy=vy * s, t=t, hits=tr["hits"] + 1)
            if box:
                boxes.append((k, box, z))
        for j, (dx, dy, box, z) in enumerate(dets):
            if j not in used_d:
                self.tracks[self.next_id] = dict(x=dx, y=dy, vx=0.0, vy=0.0, t=t, hits=1)
                if box:
                    boxes.append((self.next_id, box, z))
                self.next_id += 1
        self.tracks = {k: v for k, v in self.tracks.items() if t - v["t"] < FORGET}
        return boxes

    def people(self, t):
        return [dict(id=f"P{k}", x=v["x"] + v["vx"] * (t - v["t"]), y=v["y"] + v["vy"] * (t - v["t"]), vx=v["vx"], vy=v["vy"])
                for k, v in self.tracks.items() if v["hits"] >= 3]

    def conversations(self, t):
        still = [p for p in self.people(t) if math.hypot(p["vx"], p["vy"]) < 0.25]
        return [((a["x"], a["y"]), (b["x"], b["y"])) for i, a in enumerate(still) for b in still[i + 1:]
                if 0.6 < math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 1.6]


def lidar_points(ranges, pose, grid, max_range=4.0):
    """LiDAR returns that are not walls or furniture, in world coordinates. Ray i points pi - i*2pi/n CCW from forward."""
    x, y, th = pose
    r = np.asarray(ranges, np.float32)
    a = math.pi - np.arange(len(r)) * 2 * math.pi / len(r)
    ok = np.isfinite(r) & (r > 0.15) & (r < max_range)
    px, py = x + r[ok] * np.cos(th + a[ok]), y + r[ok] * np.sin(th + a[ok])
    keep = [(float(u), float(v)) for u, v in zip(px, py) if not grid.inside_box(u, v, 0.15) and abs(u) < 8.8 and abs(v) < 5.8]
    return keep[::2]


def depth_points(depth, person_boxes, pose, f, pitch=0.1, cam_fwd=0.11, cam_h=1.005, step=6, max_d=4.0):
    """Depth pixels that are not people and not floor, as world (x, y) points: things standing 8-95 cm high."""
    H, W = depth.shape
    v, u = np.mgrid[0:H:step, 0:W:step]
    z = depth[::step, ::step].astype(np.float32)
    keep = np.isfinite(z) & (z > 0.2) & (z < max_d)
    for x0, y0, x1, y1 in person_boxes:  # people are the tracker's job
        mx, my = 0.1 * (x1 - x0), 0.05 * (y1 - y0)
        keep &= ~((u >= x0 - mx) & (u <= x1 + mx) & (v >= y0 - my) & (v <= y1 + my))
    xc, yc = (u - W / 2) * z / f, (v - H / 2) * z / f  # right, down in the camera frame
    fwd = cam_fwd + z * math.cos(pitch) - yc * math.sin(pitch)
    up = cam_h - z * math.sin(pitch) - yc * math.cos(pitch)
    keep &= (up > 0.08) & (up < 0.95)
    x, y, th = pose
    f_, l_ = fwd[keep], -xc[keep]
    return np.stack([x + f_ * math.cos(th) - l_ * math.sin(th), y + f_ * math.sin(th) + l_ * math.cos(th)], 1)


class ObstacleMemory:
    """Cells where the depth camera keeps seeing something the map does not know: after 3 sightings they are obstacles.
    A cell next to a tracked person is never added (and is dropped if a person turns up there): that was a person."""

    def __init__(self, grid, res=0.2):
        self.g, self.res, self.hits, self.known = grid, res, {}, set()

    def update(self, points, people):
        new = []
        for px, py in points:
            if abs(px) > 8.8 or abs(py) > 5.8 or self.g.inside_box(px, py, 0.15):
                continue  # walls and furniture the map already has
            if any(math.hypot(px - p["x"], py - p["y"]) < 0.6 for p in people):
                continue
            c = (round(px / self.res), round(py / self.res))
            self.hits[c] = self.hits.get(c, 0) + 1
            if self.hits[c] >= 3 and c not in self.known:
                self.known.add(c); new.append(c)
        self.known = {c for c in self.known if not any(math.hypot(c[0] * self.res - p["x"], c[1] * self.res - p["y"]) < 0.45 for p in people)}
        self.hits = {c: n for c, n in self.hits.items() if n < 50}
        return new

    def points(self):
        return [(c[0] * self.res, c[1] * self.res) for c in self.known]


class Namer:
    """Open-vocabulary detection (YOLOE): names things by text, so Saathi can say what blocked it and find what it is asked for.
    The vocabulary is embedded once at start-up; changing it means calling set_vocab again."""

    # People get posture words, not plain "person": with "person" in the list a lying body is just labelled "person".
    VOCAB = ["person lying on the floor", "person standing", "person walking", "yellow caution sign", "wet floor sign", "cardboard box",
             "dustbin", "chair", "sign board", "wheelchair", "bag", "television"]

    def __init__(self, weights, width, hfov, cam_forward=0.11):
        from ultralytics import YOLO
        self.model, self.W, self.f, self.cam_forward = YOLO(weights), width, (width / 2) / math.tan(hfov / 2), cam_forward
        self.set_vocab(self.VOCAB)

    def set_vocab(self, names):
        self.names = list(names)
        self.model.set_classes(self.names, self.model.get_text_pe(self.names))

    def look(self, bgr, depth, pose, conf=0.3):
        """-> [(name, confidence, (world x, world y), box)] for everything but people."""
        x, y, th = pose
        r = self.model.predict(bgr, conf=conf, imgsz=640, verbose=False)[0]
        out = []
        for (x0, y0, x1, y1), c, s in zip(r.boxes.xyxy.int().tolist(), r.boxes.cls.int().tolist(), r.boxes.conf.tolist()):
            if self.names[c] in ("person standing", "person walking"):
                continue
            if self.names[c] == "person lying on the floor":  # the body is what in the box lies 5-50 cm above the floor
                body = box_points(depth, (x0, y0, x1, y1), pose, self.f, 0.05, 0.5)
                if len(body) >= 5:
                    bx, by = np.median(body, 0)
                    out.append((self.names[c], s, (float(bx), float(by)), (x0, y0, x1, y1)))
                continue
            patch = depth[max(y0, 0):max(y1, 1), max(x0, 0):max(x1, 1)]
            patch = patch[np.isfinite(patch)]
            if not patch.size:
                continue
            z = float(np.percentile(patch, 30))
            fx, fy = self.cam_forward + z, -z * ((x0 + x1) / 2 - self.W / 2) / self.f
            out.append((self.names[c], s, (x + fx * math.cos(th) - fy * math.sin(th), y + fx * math.sin(th) + fy * math.cos(th)), (x0, y0, x1, y1)))
        return out


def box_points(depth, box, pose, f, lo, hi, pitch=0.1, cam_fwd=0.11, cam_h=1.005):
    """World (x, y) of the depth pixels inside an image box that stand lo..hi metres above the floor."""
    H, W = depth.shape
    x0, y0, x1, y1 = (max(0, int(v)) for v in box)
    v, u = np.mgrid[y0:min(y1, H), x0:min(x1, W)]
    z = depth[y0:min(y1, H), x0:min(x1, W)].astype(np.float32)
    xc, yc = (u - W / 2) * z / f, (v - H / 2) * z / f
    fwd, up = cam_fwd + z * math.cos(pitch) - yc * math.sin(pitch), cam_h - z * math.sin(pitch) - yc * math.cos(pitch)
    keep = np.isfinite(z) & (up > lo) & (up < hi)
    x, y, th = pose
    f_, l_ = fwd[keep], -xc[keep]
    return np.stack([x + f_ * math.cos(th) - l_ * math.sin(th), y + f_ * math.sin(th) + l_ * math.cos(th)], 1)
