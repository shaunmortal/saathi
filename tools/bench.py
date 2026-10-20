"""A/B test: a normal robot vs Saathi, same seeded crowds, same trips. Headless and fast: no rendering.

Each seed builds an OPD crowd (8-12 walkers on straight paths, a talking pair standing across the direct route, one more
pair elsewhere, a pharmacy queue) and a trip from the entrance to a random department. People are kinematic, as in Webots:
they walk their paths and do not react to the robot. Both robots use controllers/saathi/brain.py; perception is ground truth here.
Usage: python tools/bench.py [N seeds=200]  ->  out/bench/{runs.jsonl, summary.json, ab_chart.png}
"""
import json, math, os, sys
from multiprocessing import Pool
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "controllers", "saathi"))
from brain import Grid, Metrics, Reflex  # noqa: E402

SCENE = json.load(open(os.path.join(ROOT, "controllers", "saathi", "scene.json")))
DT, LIMIT, WALK = 0.032, 90.0, 1.22
OUT = os.path.join(ROOT, "out", "bench")


def crowd(seed, grid, start, goal):
    rng = np.random.default_rng(seed)
    def free_pt(pad=0.45):
        while True:
            x, y = rng.uniform(-8.4, 8.4), rng.uniform(-5.4, 5.4)
            if not grid.inside_box(x, y, pad) and math.hypot(x - start[0], y - start[1]) > 1.5:
                return np.array([x, y])
    def clear(a, b):
        n = int(np.linalg.norm(b - a) / 0.2) + 1
        return all(not grid.inside_box(*(a + (b - a) * k / n), 0.3) for k in range(n + 1))
    walkers = []
    while len(walkers) < int(rng.integers(8, 13)):
        a, b = free_pt(), free_pt()
        if np.linalg.norm(b - a) > 6 and clear(a, b):
            L = float(np.linalg.norm(b - a))
            walkers.append(dict(id=f"W{len(walkers) + 1}", a=a, b=b, L=L, s=float(rng.uniform(0, L)), dir=int(rng.choice([-1, 1])), turn=0.0))
    pairs = []
    sv, gv = np.array(start), np.array(goal)
    for f in rng.uniform(0.35, 0.65, 20):  # a pair talking right across the direct route
        mid, u = sv + (gv - sv) * f, (gv - sv) / np.linalg.norm(gv - sv)
        n = np.array([-u[1], u[0]]) * rng.uniform(0.5, 0.6)
        a, b = mid - n, mid + n
        if not grid.inside_box(*a, 0.4) and not grid.inside_box(*b, 0.4) and np.linalg.norm(gv - mid) > 2:
            pairs.append((a, b)); break
    while len(pairs) < 2:
        mid, ang = free_pt(0.9), rng.uniform(0, math.pi)
        n = np.array([math.cos(ang), math.sin(ang)]) * 0.55
        if np.linalg.norm(mid - gv) > 2:
            pairs.append((mid - n, mid + n))
    standers = [np.array(p, float) for p in ([(-0.8, 5.15), (-0.8, 4.4)])] + [p for pr in pairs for p in pr]
    return walkers, pairs, standers


def step_walkers(walkers, dt):
    for w in walkers:
        if w["turn"] > 0:
            w["turn"] -= dt; w["vel"] = np.zeros(2); continue
        w["s"] += w["dir"] * WALK * dt
        if not 0 <= w["s"] <= w["L"]:
            w["s"] = min(max(w["s"], 0.0), w["L"]); w["dir"] *= -1; w["turn"] = 0.8
        u = (w["b"] - w["a"]) / w["L"]
        w["pos"], w["vel"] = w["a"] + u * w["s"], u * w["dir"] * WALK


def run(args):
    seed, social = args
    grid = Grid(SCENE["obstacles"])
    rng = np.random.default_rng(10_000 + seed)
    assert not SCENE.get("floor2"), "scene.json is the two-floor demo world: run tools/make_world.py (defaults) first"
    name = list(SCENE["goals"])[int(rng.integers(len(SCENE["goals"])))]
    start, goal = tuple(SCENE["start"]), tuple(SCENE["goals"][name])
    walkers, pairs, standers = crowd(seed, grid, start, goal)
    bot, m = Reflex(grid, social), Metrics()
    pose, t, arrived = (start[0], start[1], math.atan2(goal[1] - start[1], goal[0] - start[0])), 0.0, False
    pair_pts = [(tuple(a), tuple(b)) for a, b in pairs]
    while t < LIMIT and not arrived:
        step_walkers(walkers, DT)
        people = [dict(id=w["id"], x=w["pos"][0], y=w["pos"][1], vx=w["vel"][0], vy=w["vel"][1]) for w in walkers] + \
                 [dict(id=f"S{k}", x=p[0], y=p[1], vx=0.0, vy=0.0) for k, p in enumerate(standers)]
        pose, guard, arrived = bot.step(t, DT, pose, goal, people, pair_pts)
        m.update(t, pose, bot.v, people, pair_pts, guard)
        t += DT
    return dict(seed=seed, mode="saathi" if social else "baseline", goal=name, arrived=arrived, time=round(t, 2),
                near_misses=m.near, conversation_cuts=m.cuts, min_dist=round(m.min_d, 3), safety_stops=m.stops, path=round(m.path_len, 2))


def summarize(rows):
    out = {}
    for mode in ("baseline", "saathi"):
        r = [x for x in rows if x["mode"] == mode]
        ok = [x for x in r if x["arrived"]]
        out[mode] = dict(trips=len(r), arrived=len(ok), near_misses_per_trip=float(np.mean([x["near_misses"] for x in r])),
                         trips_cutting_a_conversation=float(np.mean([x["conversation_cuts"] > 0 for x in r])),
                         median_closest_pass=float(np.median([x["min_dist"] for x in r])),
                         safety_stops_per_trip=float(np.mean([x["safety_stops"] for x in r])),
                         median_trip_time=float(np.median([x["time"] for x in ok])) if ok else None)
    return out


def chart(s, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    b, a = s["baseline"], s["saathi"]
    panels = [("Near-misses per trip\n(someone under 0.8 m)", b["near_misses_per_trip"], a["near_misses_per_trip"], "{:.2f}"),
              ("Trips that cut through\na conversation", 100 * b["trips_cutting_a_conversation"], 100 * a["trips_cutting_a_conversation"], "{:.0f}%"),
              ("Safety stops per trip\n(someone under 0.6 m)", b["safety_stops_per_trip"], a["safety_stops_per_trip"], "{:.2f}"),
              ("Reached the goal\n(within 90 s)", b["arrived"], a["arrived"], "{:.0f}/" + str(b["trips"])),
              ("Median trip time (s)", b["median_trip_time"], a["median_trip_time"], "{:.0f} s")]
    fig, axs = plt.subplots(1, 5, figsize=(19, 5.4), dpi=120)
    for ax, (title, vb, va, fmt) in zip(axs, panels):
        bars = ax.bar(["Normal robot", "Saathi"], [vb, va], color=["#9aa3a0", "#0f5c52"], width=0.6)
        for bar, v in zip(bars, (vb, va)):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), fmt.format(v), ha="center", va="bottom", fontsize=15, fontweight="bold")
        ax.set_title(title, fontsize=13)
        ax.spines[["top", "right", "left"]].set_visible(False); ax.set_yticks([])
        ax.tick_params(axis="x", labelsize=12); ax.set_ylim(0, max(vb, va) * 1.25 + 1e-6)
    fig.suptitle(f"Same {b['trips']} seeded OPD crowds, same trips: a normal robot vs Saathi", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    os.makedirs(OUT, exist_ok=True)
    with Pool(6) as pool:
        rows = pool.map(run, [(s, social) for s in range(n) for social in (False, True)])
    with open(os.path.join(OUT, "runs.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    s = summarize(rows)
    json.dump(s, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    chart(s, os.path.join(OUT, "ab_chart.png"))
    print(json.dumps(s, indent=1))
