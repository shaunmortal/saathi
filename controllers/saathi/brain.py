"""Saathi's reflex brain, shared by the Webots controller and the headless A/B benchmark (tools/bench.py).

Saathi plans with grid A* on a crowd costmap: people cost where they are and where they will be over the next 2 s,
a talking pair gets a wall of cost between them, and keep-left adds cost to the right-hand half of the hall for the trip.
It slows for people in its lane, slides sideways (mecanum) for someone walking straight at it, and a safety guard stops it
under 0.6 m. The baseline is a normal obstacle-avoiding robot: the same planner treating people as obstacles where they are
now, at a fixed speed, with the same safety guard: no prediction, no conversations, no keep-left, no slowing, no side-step.
Run this file to self-check the planner.
"""
import copy, heapq, math
import numpy as np

RES, X0, Y0, X1, Y1 = 0.2, -9.0, -6.0, 9.0, 6.0
GW, GH = round((X1 - X0) / RES), round((Y1 - Y0) / RES)
NEAR_MISS, GUARD, LANE = 0.8, 0.6, 0.8   # m: near-miss distance, safety-guard stop distance, half-width of the lane ahead
VMAX, ACC, LOOK = 0.65, 0.8, 0.8        # m/s, m/s², pure-pursuit lookahead (m)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Grid:
    """Free space of the hall at RES metres; walls and furniture boxes are inflated by the robot's radius."""

    def __init__(self, obstacles, inflate=0.35):
        xs, ys = X0 + (np.arange(GW) + 0.5) * RES, Y0 + (np.arange(GH) + 0.5) * RES
        self.X, self.Y = np.meshgrid(xs, ys)
        b = (self.X < X0 + inflate) | (self.X > X1 - inflate) | (self.Y < Y0 + inflate) | (self.Y > Y1 - inflate)
        for cx, cy, sx, sy in obstacles:
            b |= (np.abs(self.X - cx) < sx / 2 + inflate) & (np.abs(self.Y - cy) < sy / 2 + inflate)
        self.blocked = b
        self.boxes = obstacles
        self.res, self.x0, self.y0 = RES, X0, Y0

    @staticmethod
    def cell(x, y):
        return min(GH - 1, max(0, int((y - Y0) / RES))), min(GW - 1, max(0, int((x - X0) / RES)))

    def free(self, x, y):
        return not self.blocked[self.cell(x, y)]

    def inside_box(self, x, y, pad=0.0):
        return any(abs(x - cx) < sx / 2 + pad and abs(y - cy) < sy / 2 + pad for cx, cy, sx, sy in self.boxes)


def cost_map(grid, people, pairs, start, goal, social=True):
    """1 everywhere, plus personal space now and over the next 2 s, conversation walls and the keep-left lane.
    social=False: people only where they are now (the baseline robot's obstacle layer)."""
    c = np.ones((GH, GW), np.float32)
    if not social:
        for p in people:
            d = np.hypot(grid.X - p["x"], grid.Y - p["y"])
            c += np.where(d < 0.6, 6 * (1 - d / 0.6), 0).astype(np.float32)
        return c
    for p in people:
        r, amp = (1.4, 10.0) if p.get("kind") == "wheelchair" else (0.95, 8.0)
        for k in range(5):
            d = np.hypot(grid.X - (p["x"] + p["vx"] * k * 0.5), grid.Y - (p["y"] + p["vy"] * k * 0.5))
            c += np.where(d < r, amp * (1 - 0.15 * k) * (1 - d / r), 0).astype(np.float32)
    for (ax, ay), (bx, by) in pairs:
        ex, ey = bx - ax, by - ay
        t = np.clip(((grid.X - ax) * ex + (grid.Y - ay) * ey) / (ex * ex + ey * ey + 1e-9), 0, 1)
        c = np.where(np.hypot(grid.X - ax - ex * t, grid.Y - ay - ey * t) < 0.55, np.maximum(c, 60.0), c)
    if abs(goal[0] - start[0]) > 4:  # a long east-west trip: the right-hand half of the hall costs a little more
        east = goal[0] > start[0]
        lo, hi = min(start[0], goal[0]), max(start[0], goal[0])
        right = (grid.Y < 0) if east else (grid.Y > 0)
        c += np.where(right & (grid.X >= lo) & (grid.X <= hi) & (np.abs(grid.Y) < 4.5), 0.9, 0).astype(np.float32)
    return c


_STEPS = [(0, 1, 1.0), (0, -1, 1.0), (1, 0, 1.0), (-1, 0, 1.0), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]


def _nearest_free(blocked, j, i):
    if not blocked[j, i]:
        return j, i
    js, is_ = np.nonzero(~blocked)
    k = int(np.argmin((js - j) ** 2 + (is_ - i) ** 2))
    return int(js[k]), int(is_[k])


def astar(grid, cost, start, goal):
    """8-connected A* with an octile heuristic; edge cost = step length x mean cell cost. Returns world points or None."""
    blocked = grid.blocked
    gh, gw = blocked.shape  # any grid: the hall here, a bigger floor in tools/bench_lost.py
    s, g = _nearest_free(blocked, *grid.cell(*start)), _nearest_free(blocked, *grid.cell(*goal))
    best, came, closed = {s: 0.0}, {}, set()
    h = lambda n: (lambda dx, dy: dx + dy + (math.sqrt(2) - 2) * min(dx, dy))(abs(n[1] - g[1]), abs(n[0] - g[0]))
    heap = [(h(s), s)]
    while heap:
        _, n = heapq.heappop(heap)
        if n in closed:
            continue
        if n == g:
            break
        closed.add(n)
        j, i = n
        for dj, di, L in _STEPS:
            m = (j + dj, i + di)
            if not (0 <= m[0] < gh and 0 <= m[1] < gw) or blocked[m] or m in closed:
                continue
            if dj and di and (blocked[j + dj, i] or blocked[j, i + di]):
                continue  # no corner cutting
            ng = best[n] + L * 0.5 * (cost[n] + cost[m])
            if ng < best.get(m, math.inf):
                best[m], came[m] = ng, n
                heapq.heappush(heap, (ng + h(m), m))
    if g != s and g not in came:
        return None
    cells = [g]
    while cells[-1] != s:
        cells.append(came[cells[-1]])
    return [(grid.x0 + (i + 0.5) * grid.res, grid.y0 + (j + 0.5) * grid.res) for j, i in reversed(cells)]


def _clear(grid, cost, a, b):
    n = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.1))
    for k in range(1, n):
        c = grid.cell(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
        if grid.blocked[c] or cost[c] > 2.5:
            return False
    return True


def smooth(grid, cost, pts):
    """Keep only the corners: jump to the farthest point reachable in a straight, cheap line."""
    if not pts or len(pts) < 3:
        return pts
    out, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not _clear(grid, cost, pts[i], pts[j]):
            j -= 1
        out.append(pts[j])
        i = j
    return out


class Reflex:
    """Plans and drives one step at a time. social=False is the baseline robot."""

    def __init__(self, grid, social=True):
        self.g, self.social = grid, social
        self.path, self.next_plan, self.v, self.off, self.hold = None, 0.0, 0.0, 0.0, (0.0, 0.0, None)
        self.status, self.wait_until, self.wait_why = "", 0.0, ""

    def plan(self, x, y, goal, people, pairs, scan=(), hard=()):
        g = self.g
        if hard:  # obstacles the camera found that the map does not have: blocked, inflated by the robot's radius
            g = copy.copy(self.g)
            g.blocked = self.g.blocked.copy()
            for px, py in hard:
                g.blocked |= np.hypot(self.g.X - px, self.g.Y - py) < 0.45
        self.g_plan = g  # the map plus what the camera found, for the side-step and collision checks below
        cost = cost_map(self.g, people, pairs, (x, y), goal, self.social)
        for px, py in scan:  # LiDAR returns that are not furniture: someone the camera cannot see, beside or behind
            d = np.hypot(self.g.X - px, self.g.Y - py)
            cost += np.where(d < 0.5, 4 * (1 - d / 0.5), 0).astype(np.float32)
        p = astar(g, cost, (x, y), goal)
        self.path = smooth(g, cost, p) if p else None
        self.cost = cost

    def _lookahead(self, x, y):
        pts = self.path
        best, bi, bt = math.inf, 0, 0.0
        for k in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            ex, ey = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * ex + (y - ay) * ey) / (ex * ex + ey * ey + 1e-9)))
            d = math.hypot(ax + ex * t - x, ay + ey * t - y)
            if d < best:
                best, bi, bt = d, k, t
        rem, k, t = LOOK, bi, bt
        while k < len(pts) - 1:
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            L = math.hypot(bx - ax, by - ay) * (1 - t)
            if L >= rem:
                f = t + rem / max(1e-9, math.hypot(bx - ax, by - ay))
                return ax + (bx - ax) * f, ay + (by - ay) * f
            rem -= L; k += 1; t = 0.0
        return pts[-1]

    def step(self, t, dt, pose, goal, people, pairs, scan=None, hard=None):
        """pose (x, y, th) -> new pose, whether the safety guard fired, whether it arrived.
        scan: LiDAR points (world x, y). When given, the safety guard uses them as well: it does not depend on the camera."""
        x, y, th = pose
        fwd, left = (math.cos(th), math.sin(th)), (-math.sin(th), math.cos(th))
        vlim, why, want_off, dodge = VMAX, "", 0.0, None
        if self.social:
            for p in people:
                rx, ry = p["x"] - x, p["y"] - y
                ahead, side = rx * fwd[0] + ry * fwd[1], rx * left[0] + ry * left[1]
                closing = -(p["vx"] * fwd[0] + p["vy"] * fwd[1])
                if 0 < ahead < 3.5 and abs(side) < 1.0 and closing > 0.3:
                    want_off, dodge = (0.7 if side <= 0.3 else -0.6), p["id"]
                if ahead > 1.4 and p["vx"] * fwd[0] + p["vy"] * fwd[1] > self.v + 0.1:
                    continue  # well ahead of me and walking away faster than I drive: no need to slow down
                if math.hypot(p["vx"], p["vy"]) < 0.2:  # standing still: the planner goes around them, I only ease off
                    if 0 < ahead < 1.5 and abs(side) < LANE:
                        vlim, why = min(vlim, VMAX * 0.5), why or f"Easing past {p['id']}"
                    continue
                for k, (qx, qy) in enumerate(((p["x"], p["y"]), (p["x"] + p["vx"], p["y"] + p["vy"]))):
                    a = (qx - x) * fwd[0] + (qy - y) * fwd[1]
                    s = (qx - x) * left[0] + (qy - y) * left[1]
                    if a > 0 and abs(s) < LANE:
                        lim = 0.0 if a < 0.9 else VMAX * min(1.0, (a - 0.9) / 1.1)
                        if lim < vlim:
                            vlim, why = lim, (f"Waiting for {p['id']}" if lim == 0 else f"Slowing for {p['id']}" + (" (will cross my path in 1 s)" if k else ""))
            if vlim == 0.0:  # once I decide to wait, I wait at least 0.4 s: no stop-go flicker
                self.wait_until, self.wait_why = t + 0.4, why
            elif t < self.wait_until:
                vlim, why = 0.0, self.wait_why
            if dodge:
                gp = getattr(self, "g_plan", self.g)
                for side in (want_off, -0.6 if want_off > 0 else 0.7, 0.0):  # only slide where there is room
                    sx, sy = x + (side - self.off) * left[0], y + (side - self.off) * left[1]
                    if side == 0.0 or (not gp.blocked[gp.cell(sx, sy)] and all(math.hypot(sx - q["x"], sy - q["y"]) > 0.6 for q in people)):
                        want_off = side
                        break
                self.hold = (t + 1.0, want_off, dodge)
            elif self.hold[0] > t:
                _, want_off, dodge = self.hold
        vy = max(-0.45, min(0.45, 1.5 * (want_off - self.off)))
        self.off += vy * dt
        rx, ry = x - self.off * left[0], y - self.off * left[1]
        if t >= self.next_plan or self.path is None:
            self.plan(rx, ry, goal, people, pairs, scan or (), hard or ())
            self.next_plan = t + 0.5
        arrived = math.hypot(goal[0] - rx, goal[1] - ry) < 0.35
        if self.path is None or arrived:
            self.v, vcmd, err = 0.0, 0.0, 0.0
        else:
            lx, ly = self._lookahead(rx, ry)
            err = wrap(math.atan2(ly - ry, lx - rx) - th)
            vcmd = min(vlim, VMAX * max(0.25, math.cos(err)))
        pts = [(p["x"], p["y"]) for p in people] + list(scan or ()) + list(hard or ())
        guard = any(0 < (px - x) * fwd[0] + (py - y) * fwd[1] < GUARD and abs((px - x) * left[0] + (py - y) * left[1]) < 0.45 for px, py in pts)
        if guard:
            vcmd = 0.0
        self.v += max(-ACC * dt * 2, min(ACC * dt, vcmd - self.v))
        if guard:
            self.v = 0.0
        th = wrap(th + max(-1.2, min(1.2, 2.2 * err)) * dt)
        nx = x + (self.v * math.cos(th) - vy * math.sin(th)) * dt
        ny = y + (self.v * math.sin(th) + vy * math.cos(th)) * dt
        if self.g.inside_box(nx, ny, 0.25) or not (X0 + 0.3 < nx < X1 - 0.3 and Y0 + 0.3 < ny < Y1 - 0.3) or \
                any(math.hypot(nx - px, ny - py) < 0.35 for px, py in (hard or ())):
            nx, ny, self.v, self.next_plan = x, y, 0.0, t  # never drive into furniture; replan next step
        self.status = ("Arrived" if arrived else "Safety stop: someone under 0.6 m" if guard else why or
                       (f"Sliding {'left' if want_off > 0 else 'right'} to let {dodge} pass" if dodge else "Going, keeping left"))
        return (nx, ny, th), guard, arrived


class Metrics:
    """Near-misses (someone under 0.8 m while the robot moves), conversations cut, closest pass, safety stops, trip time."""

    def __init__(self):
        self.near, self.cuts, self.min_d, self.stops, self.path_len = 0, 0, math.inf, 0, 0.0
        self._cool, self._cut, self._guard_on, self._last = {}, set(), False, None

    def update(self, t, pose, v, people, pairs, guard):
        x, y = pose[0], pose[1]
        if self._last:
            self.path_len += math.hypot(x - self._last[0], y - self._last[1])
        self._last = (x, y)
        for p in people:
            d = math.hypot(p["x"] - x, p["y"] - y)
            self.min_d = min(self.min_d, d)
            if d < NEAR_MISS and abs(v) > 0.1 and t >= self._cool.get(p["id"], 0):
                self.near += 1
                self._cool[p["id"]] = t + 3.0
        for k, ((ax, ay), (bx, by)) in enumerate(pairs):
            ex, ey = bx - ax, by - ay
            u = ((x - ax) * ex + (y - ay) * ey) / (ex * ex + ey * ey + 1e-9)
            if 0.15 < u < 0.85 and math.hypot(ax + ex * u - x, ay + ey * u - y) < 0.3 and k not in self._cut:
                self._cut.add(k)
                self.cuts += 1
        if guard and not self._guard_on:
            self.stops += 1
        self._guard_on = guard


if __name__ == "__main__":
    import time
    g = Grid([(1.5, -3.0, 2.6, 0.55), (-6.3, 4.9, 3.5, 0.8)])
    t0 = time.perf_counter()
    straight = astar(g, np.ones((GH, GW), np.float32), (-7.6, 0.0), (5.0, 4.7))
    pair = [((-1.0, 1.0), (-1.0, 2.2))]
    social = smooth(g, cost_map(g, [], pair, (-7.6, 0.0), (5.0, 4.7)), astar(g, cost_map(g, [], pair, (-7.6, 0.0), (5.0, 4.7)), (-7.6, 0.0), (5.0, 4.7)))
    ms = (time.perf_counter() - t0) * 1000 / 2
    assert straight and abs(straight[-1][0] - 5.0) < 0.2 and abs(straight[-1][1] - 4.7) < 0.2, straight[-1]
    m = Metrics()
    for k in range(len(social) - 1):
        for f in np.linspace(0, 1, 30):
            m.update(0, (social[k][0] + (social[k + 1][0] - social[k][0]) * f, social[k][1] + (social[k + 1][1] - social[k][1]) * f), 0.5, [], pair, False)
    assert m.cuts == 0, "the social path must not cut between the talking pair"
    print(f"planner ok: {len(straight)} cells straight, {len(social)} corners social, {ms:.0f} ms per plan")
