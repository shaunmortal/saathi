"""Saathi Parivaar benchmark: find a lost child on a bigger hospital floor with 1-3 robots, with and without memory.

Headless and seeded, no rendering. The floor is the Webots OPD hall plus a corridor east of its Wards & Lift door, with a lab,
a radiology block, toilets and a stair/lift lobby. Robots do their own jobs, see through a 60 deg, 8 m camera (walls block it)
and put every child they see into one shared memory (controllers/saathi/memory.py). A child separates from a parent and
wanders with a behaviour from its own generator (the predictor never sees it); 1-3 minutes later the parent reports.
Half the seeds add two look-alike children. Sightings carry CLIP text scores and heights like those we measured on Webots renders.
After the report every robot visits viewpoints that cover the whole floor, looking all around at each (so every strategy
finds the child eventually); strategies differ only in which unvisited viewpoint a free robot takes next:
  sweep       no memory: the nearest one
  last_seen   robot 1 first goes where the memory last saw the child (recall, as in ReMEmbR), then the nearest one
  where_now   ours: the one with the most particles for where the child can be now, for the distance (places the team
              already looked at are ruled out)
  no_ruleout  where_now without ruling out places already looked at
  recall_where_now  robot 1 first goes where the memory last saw the child, then everyone follows where_now
  team_split  robot 1 follows where_now; the others take the nearest viewpoints, so the floor is still covered
Usage: [GAP=60,180] [BENCH_OUT=bench_lost] python tools/bench_lost.py [N seeds=200]  ->  out/<BENCH_OUT>/{runs.jsonl, summary.json, chart.png}
"""
import json, math, os, sys
from multiprocessing import Pool
import numpy as np
from scipy.ndimage import binary_dilation, uniform_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "controllers", "saathi"))
from brain import astar  # noqa: E402
from memory import PeopleMemory  # noqa: E402

SCENE = json.load(open(os.path.join(ROOT, "controllers", "saathi", "scene.json")))
OUT = os.path.join(ROOT, "out", os.environ.get("BENCH_OUT", "bench_lost"))
RES, X0, Y0, X1, Y1 = 0.2, -9.4, -6.4, 33.4, 10.4
ROOMS = [(-9, -6, 9, 6), (9.2, 0.6, 33, 2.6), (14, 2.8, 20, 9), (24, 2.8, 30, 9), (18, -4, 22, 0.4), (30, -4, 33, 0.4)]
DOORS = [(8.9, 0.8, 9.3, 2.2), (16.2, 2.5, 17.8, 2.9), (26.2, 2.5, 27.8, 2.9), (19.2, 0.3, 20.8, 0.7), (31.0, 0.3, 32.6, 0.7)]
PLACES = {**{k: tuple(v) for k, v in SCENE["places"].items()}, "corridor": (21.0, 1.6), "lab": (17.0, 6.0), "radiology block": (27.0, 6.0),
          "toilets": (20.0, -2.0), "stairs and lift": (31.5, -2.0), "corridor end": (32.4, 1.6)}
DT, LIMIT, V_BOT, TURN, CAM_R, HALF_FOV = 0.5, 180.0, 0.65, 0.9, 8.0, 0.52
GAP = tuple(float(v) for v in os.environ.get("GAP", "60,180").split(","))  # s from the child wandering off to the parent's report
CHILD, LOOKALIKE = (0.270, 0.012), (0.262, 0.012)   # CLIP text score for "small child in a red shirt" (mean, sd)
STRATEGIES = tuple(os.environ.get("STRATS", "sweep,last_seen,where_now,no_ruleout,recall_where_now,team_split").split(","))
SEED0 = int(os.environ.get("SEED0", 0))  # held-out seeds for designs chosen after seeing seeds 0-199
Q = np.eye(8)[0]  # the description's embedding; a sighting's embedding is built so that emb @ Q is its text score


class Floor:
    """The bigger floor at RES m with brain.Grid's interface (blocked, X, Y, cell, x0, y0, res); wall blocks sight too."""

    def __init__(self, furniture):
        xs, ys = X0 + (np.arange(round((X1 - X0) / RES)) + 0.5) * RES, Y0 + (np.arange(round((Y1 - Y0) / RES)) + 0.5) * RES
        self.X, self.Y = np.meshgrid(xs, ys)
        free = np.zeros(self.X.shape, bool)
        for a, b, c, d in ROOMS + DOORS:
            free |= (self.X > a) & (self.X < c) & (self.Y > b) & (self.Y < d)
        stuff = np.zeros_like(free)
        for cx, cy, sx, sy in furniture:
            stuff |= (np.abs(self.X - cx) < sx / 2) & (np.abs(self.Y - cy) < sy / 2)
        self.wall, self.blocked = ~free, binary_dilation(~free | stuff, iterations=2)
        self.res, self.x0, self.y0 = RES, X0, Y0
        self.ones = np.ones(self.X.shape, np.float32)

    def cell(self, x, y):
        return min(self.X.shape[0] - 1, max(0, int((y - Y0) / RES))), min(self.X.shape[1] - 1, max(0, int((x - X0) / RES)))

    def cells(self, PX, PY):
        return np.clip(((PY - Y0) / RES).astype(int), 0, self.X.shape[0] - 1), np.clip(((PX - X0) / RES).astype(int), 0, self.X.shape[1] - 1)

    def path(self, a, b):
        p = astar(self, self.ones, tuple(a), tuple(b))
        return [np.array(q) for q in (p or [])[1::3]] + [np.array(b, float)]

    def random_free(self, rng, box):
        while True:
            x, y = rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3])
            if not self.blocked[self.cell(x, y)]:
                return np.array([x, y])

    def sees(self, ax, ay, th, bx, by):
        d = math.hypot(bx - ax, by - ay)
        if d > CAM_R or abs((math.atan2(by - ay, bx - ax) - th + math.pi) % (2 * math.pi) - math.pi) > HALF_FOV:
            return False
        n = max(2, int(d / 0.1))
        return not self.wall[self.cells(np.linspace(ax, bx, n), np.linspace(ay, by, n))].any()


class Mover:
    """A child (or a robot body) walking a list of waypoints, pausing at some."""

    def __init__(self, pos, v):
        self.pos, self.v, self.legs, self.path, self.pause, self.vel = np.array(pos, float), v, [], [], 0.0, np.zeros(2)

    def step(self, fl):
        if self.pause > 0:
            self.pause -= DT
        elif not self.path and self.legs:
            target, self.pause_next = self.legs.pop(0)
            self.path = fl.path(self.pos, target)
        if self.pause > 0 or not self.path:
            self.vel = np.zeros(2)
            return
        d = self.path[0] - self.pos
        L = float(np.linalg.norm(d))
        self.vel = d / max(L, 1e-9) * self.v
        if L <= self.v * DT:
            self.pos = self.path.pop(0)
            if not self.path:
                self.pause = self.pause_next
        else:
            self.pos = self.pos + self.vel * DT


def lost_plan(rng, fl, start):
    """How the lost child moves: its own generator, unrelated to the predictor's guesses."""
    mode = rng.choice(["toilets", "lift", "room", "hall place", "wander"], p=[0.2, 0.15, 0.2, 0.2, 0.25])
    if mode == "toilets":
        legs = [(fl.random_free(rng, (18.5, -3.5, 21.5, -0.2)), 1e9)]
    elif mode == "lift":
        legs = [(fl.random_free(rng, (30.5, -3.5, 32.5, -0.2)), 1e9)]
    elif mode == "room":
        box = [(14.5, 3.3, 19.5, 8.5), (24.5, 3.3, 29.5, 8.5)][int(rng.integers(2))]
        legs = [(fl.random_free(rng, box), 1e9)]
    elif mode == "hall place":
        far = [p for p in SCENE["places"].values() if math.hypot(p[0] - start[0], p[1] - start[1]) > 6]
        p = np.array(far[int(rng.integers(len(far)))]) + rng.normal(0, 0.6, 2)
        legs = [(p if not fl.blocked[fl.cell(*p)] else fl.random_free(rng, (p[0] - 1.5, p[1] - 1.5, p[0] + 1.5, p[1] + 1.5)), 1e9)]
    else:
        legs, pos = [], np.array(start)
        for _ in range(int(rng.integers(4, 7))):
            pos = fl.random_free(rng, (max(-8.5, pos[0] - 7), max(-5.5, pos[1] - 5), min(32.5, pos[0] + 7), min(8.5, pos[1] + 5)))
            legs.append((pos, float(rng.uniform(5, 15))))
        legs[-1] = (legs[-1][0], 1e9)
    return str(mode), legs


def viewpoints(fl):
    pts = [np.array(p, float) for p in PLACES.values()]
    for x in np.arange(-6, 33, 5.0):
        for y in np.arange(-4, 9, 4.0):
            if not fl.blocked[fl.cell(x, y)]:
                pts.append(np.array([x, y]))
    return [p for p in pts if not fl.blocked[fl.cell(*p)]]


def run(args):
    seed, strategy, nbots = args
    fl = Floor(SCENE["obstacles"])
    rng = np.random.default_rng(seed)                       # the scene: the same for every strategy and robot count
    parent = fl.random_free(rng, (-7.5, -4.5, 7.5, 4.5))
    t_sep, gap = float(rng.uniform(15, 45)), float(rng.uniform(*GAP))
    t_rep = t_sep + gap
    kids = [Mover(parent + rng.normal(0, 0.4, 2), float(np.clip(rng.normal(0.9, 0.15), 0.5, 1.3)))]
    mode, kids[0].legs = lost_plan(rng, fl, parent)
    if rng.random() < 0.5:  # two look-alike children walking about with their own families
        for _ in range(2):
            m = Mover(fl.random_free(rng, (-8, -5, 30, 8)), 0.8)
            m.legs = [(fl.random_free(rng, (-8, -5, 30, 8)), float(rng.uniform(10, 40))) for _ in range(8)]
            kids.append(m)
    heights = [rng.normal(1.33, 0.03) for _ in kids]
    bots = []
    for b in range(nbots):                                  # robot b does the same jobs whatever the robot count
        brng = np.random.default_rng(seed * 10 + b + 1)
        bots.append(dict(m=Mover(fl.random_free(brng, (-8, -5, 8, 5)), V_BOT), th=float(brng.uniform(-math.pi, math.pi)),
                         rng=brng, look=0.0, travel=0.0, looked=True))
    mem = PeopleMemory(fl, PLACES.values())
    drng = np.random.default_rng(seed + 777)                 # detections and scores
    tracks, last_seen_by, live, rejected = {}, {}, {}, set()
    vps, visited, claimed = viewpoints(fl), set(), {}
    state = dict(found=None, wrong=0, s=None, score=0.25, first_guess=None, last_seen_err=None, exclude=set())
    t = 0.0
    while t < t_rep + LIMIT and state["found"] is None:
        if t < t_sep:
            kids[0].pos = parent + np.array([0.6, 0.0])      # with the parent until they separate
        else:
            kids[0].step(fl)
        for k in kids[1:]:
            k.step(fl)
        if abs(t - t_rep) < DT / 2:                          # the parent reports: search the shared memory
            res = mem.search(Q, child=True)
            px, py = parent
            near = np.hypot(fl.X - px, fl.Y - py) < 3.0       # the parent has looked around: not within 3 m
            mem.seen[near] = t
            if res:  # everyone who matches nearly as well is a candidate, weighted by how close their score is
                state["s"], state["score"] = res[0]["last"], res[0]["score"]
                state["cands"] = [(r["last"], math.exp((r["score"] - res[0]["score"]) / 0.004)) for r in res]
                state["last_seen_err"] = float(math.hypot(state["s"]["x"] - kids[0].pos[0], state["s"]["y"] - kids[0].pos[1]))
            else:
                state["s"] = dict(t=t, x=float(px), y=float(py), vx=0.0, vy=0.0)
            for b in bots:  # drop their jobs and start searching
                b["m"].legs, b["m"].path, b["m"].pause, b["look"], b["looked"] = [], [], 0.0, 0.0, True
        searching = t >= t_rep
        for i, b in enumerate(bots):
            m = b["m"]
            if b["look"] > 0:                                # turning on the spot to look around
                b["look"] -= TURN * DT
                b["th"] += TURN * DT
            else:
                before = m.pos.copy()
                m.step(fl)
                b["travel"] += float(np.linalg.norm(m.pos - before))
                if np.linalg.norm(m.vel) > 0:
                    b["th"] = math.atan2(m.vel[1], m.vel[0])
                if _idle(b) and not b["looked"]:            # just arrived: look all around first
                    b["look"], b["looked"] = 2 * math.pi, True
                elif _idle(b):
                    if searching:
                        _next_viewpoint(fl, mem, b, i, bots, state, strategy, t, vps, visited, claimed, kids[0].pos)
                    else:                                    # their own job: go to a random place, look around there
                        m.legs = [(fl.random_free(b["rng"], (-8.5, -5.5, 32.5, 8.5)) if b["rng"].random() < 0.4 else
                                   np.array(list(PLACES.values())[int(b["rng"].integers(len(PLACES)))], float), 0.0)]
                    b["looked"] = False
            x, y, th = float(m.pos[0]), float(m.pos[1]), b["th"]
            A = th + np.linspace(-HALF_FOV, HALF_FOV, 13)   # the floor in view, up to 6 m or the first wall, is looked at
            D = np.arange(0.5, 6.0, RES)
            jj, ii = fl.cells(x + D[None] * np.cos(A)[:, None], y + D[None] * np.sin(A)[:, None])
            ok = np.cumsum(fl.wall[jj, ii], 1) == 0
            mem.seen[jj[ok], ii[ok]] = t
            for e, k in enumerate(kids):
                if e in rejected or not fl.sees(x, y, th, k.pos[0], k.pos[1]):
                    continue
                if drng.random() > (0.9 if math.hypot(k.pos[0] - x, k.pos[1] - y) < 6 else 0.6):
                    continue
                key = (i, e)
                if t - last_seen_by.get(key, -9) > 1.2:          # out of view for a while: the tracker gives a new ID
                    tracks[key] = len(tracks) + 1
                last_seen_by[key] = t
                score = float(drng.normal(*(CHILD if e == 0 else LOOKALIKE)))
                emb = score * Q + math.sqrt(max(0.0, 1 - score * score)) * np.eye(8)[1 + (tracks[key] % 7)]
                v = k.vel + drng.normal(0, 0.15, 2)
                mem.add(t, tracks[key], float(k.pos[0] + drng.normal(0, 0.1)), float(k.pos[1] + drng.normal(0, 0.1)),
                        float(v[0]), float(v[1]), float(heights[e] + drng.normal(0, 0.02)), emb, robot=i)
                if searching:
                    live.setdefault(key, []).append(score)
                    if len(live[key]) >= 3 and np.median(live[key][-5:]) >= state["score"] - 0.02:
                        if e == 0:
                            state["found"] = t - t_rep
                        else:                                       # the parent looks at the photo: not him
                            state["wrong"] += 1
                            rejected.add(e)
                            state["exclude"].add((i, tracks[key]))
                            res = mem.search(Q, child=True, exclude=state["exclude"])
                            if res:
                                state["cands"] = [(r["last"], math.exp((r["score"] - res[0]["score"]) / 0.004)) for r in res]
                                state["s"] = res[0]["last"]
        t += DT
    return dict(seed=seed, strategy=strategy, robots=nbots, mode=mode, gap=round(gap), lookalikes=len(kids) - 1,
                found=state["found"] is not None, time=round(state["found"] if state["found"] is not None else LIMIT, 1),
                wrong=state["wrong"], travel=round(sum(b["travel"] for b in bots), 1),
                last_seen_err=None if state["last_seen_err"] is None else round(state["last_seen_err"], 2),
                seen_after_sep=bool(state["s"] is not None and state["s"]["t"] > t_sep + 1), last_seen_ago=round(t_rep - state["s"]["t"], 1) if state["s"] else None,
                first_guess_err=state["first_guess"])


def _idle(b):
    return b["look"] <= 0 and not b["m"].path and not b["m"].legs and b["m"].pause <= 0


def _next_viewpoint(fl, mem, b, i, bots, state, strategy, t, vps, visited, claimed, child_pos):
    """A free robot takes an unvisited viewpoint no other robot has claimed; which one depends on the strategy."""
    m = b["m"]
    if i in claimed:
        visited.add(claimed.pop(i))
    if strategy in ("last_seen", "recall_where_now") and i == 0 and not state.get("went_last"):
        state["went_last"] = True
        m.legs = [(np.array([state["s"]["x"], state["s"]["y"]]), 0.0)]
        return
    free = [k for k in range(len(vps)) if k not in visited and k not in claimed.values()]
    if not free:  # everything visited: start a new round
        visited.clear()
        free = [k for k in range(len(vps)) if k not in claimed.values()]
    d = np.array([np.linalg.norm(vps[k] - m.pos) for k in free])
    if strategy in ("where_now", "no_ruleout", "recall_where_now") or (strategy == "team_split" and i == 0):
        P = mem.where_now_all(state.get("cands") or [(state["s"], 1.0)], t, n=500, use_seen=(strategy != "no_ruleout"))
        V = np.array([vps[k] for k in free])
        mass = (((P[:, None, :] - V[None]) ** 2).sum(-1) < 25).sum(0) / max(1, len(P)) if len(P) else np.zeros(len(free))
        k = int(np.argmax((mass + 0.02) / (d + 5.0)))  # likely and near first; empty viewpoints still get their turn
        if state["first_guess"] is None:
            state["first_guess"] = round(float(np.linalg.norm(vps[free[k]] - child_pos)), 2)
    else:
        k = int(np.argmin(d))
    claimed[i] = free[k]
    m.legs = [(vps[free[k]], 0.0)]


def summarize(rows):
    out = {}
    for s in STRATEGIES:
        for n in (1, 2, 3):  # (team_split with 1 robot is where_now)
            r = [x for x in rows if x["strategy"] == s and x["robots"] == n]
            if not r:
                continue
            w = [x for x in r if x["seen_after_sep"]]  # a robot saw the child after they left the parent
            out[f"{s}/{n}"] = dict(runs=len(r), found_in_3_min=round(float(np.mean([x["found"] for x in r])), 3),
                                    median_time=float(np.median([x["time"] for x in r])),
                                    seen_walking_off=len(w), found_if_seen_walking_off=round(float(np.mean([x["found"] for x in w])), 3) if w else None,
                                    median_time_if_seen_walking_off=float(np.median([x["time"] for x in w])) if w else None,
                                    wrong_approaches=round(float(np.mean([x["wrong"] for x in r])), 2),
                                    travel_m=round(float(np.mean([x["travel"] for x in r])), 1))
    errs = [(x["last_seen_err"], x["first_guess_err"]) for x in rows if x["strategy"] == "where_now" and x["robots"] == 1
            and x["last_seen_err"] is not None and x["first_guess_err"] is not None]
    if errs:
        out["guess_error_m"] = dict(last_seen=round(float(np.median([a for a, _ in errs])), 2), where_now=round(float(np.median([b for _, b in errs])), 2))
    return out


def chart(s, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = {"sweep": "No memory (sweep)", "last_seen": "Memory: where it was last seen", "where_now": "Memory: where it is now",
             "recall_where_now": "Memory: last seen, then where now"}
    cols = {"sweep": "#b9c0bd", "last_seen": "#8c9692", "where_now": "#2f8f80", "recall_where_now": "#0f5c52"}
    fig, axs = plt.subplots(1, 2, figsize=(16, 5.6), dpi=120)
    for ax, key, title, fmt in ((axs[0], "found_in_3_min", "Lost child found within 3 minutes of the report", "{:.0%}"),
                                (axs[1], "median_time", "Median time to find (s; 180 = not found)", "{:.0f}")):
        for k, st in enumerate(("sweep", "last_seen", "where_now", "recall_where_now")):
            vals = [s.get(f"{st}/{n}", {}).get(key, 0) for n in (1, 2, 3)]
            bars = ax.bar(np.arange(3) + (k - 1.5) * 0.2, vals, 0.19, color=cols[st], label=names[st])
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), fmt.format(v), ha="center", va="bottom", fontsize=9)
        ax.set_xticks(range(3), ["1 robot", "2 robots", "3 robots"], fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.spines[["top", "right", "left"]].set_visible(False); ax.set_yticks([])
    axs[0].legend(fontsize=10, frameon=False, loc="upper left")
    fig.suptitle(f"{s['where_now/1']['runs']} seeded lost-child cases on a hospital floor, report {GAP[0]:.0f}-{GAP[1]:.0f} s after the child wandered off",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    os.makedirs(OUT, exist_ok=True)
    jobs = [(seed, st, nb) for seed in range(SEED0, SEED0 + n) for st in STRATEGIES for nb in (1, 2, 3)]
    with Pool(int(os.environ.get("PROCS", 6))) as pool:
        rows = pool.map(run, jobs, chunksize=4)
    with open(os.path.join(OUT, "runs.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    s = summarize(rows)
    json.dump(s, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    chart(s, os.path.join(OUT, "chart.png"))
    print(json.dumps(s, indent=1))
