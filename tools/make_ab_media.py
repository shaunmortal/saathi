"""PPT visuals from the Webots A/B runs (out/ab_baseline, out/ab_saathi, out/ab_vision) -> out/media/ab/.

trajectories.png: both robots' paths on the hall map, the talking pair, the walkers' tracks.
side_by_side.jpg: the CCTV frame when each robot is closest to the talking pair.
blackbox.jpg + blackbox.json: one decision from the vision run's black box, frame and reason.
"""
import json, math, os, shutil
import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "media", "ab")
os.makedirs(OUT, exist_ok=True)
scene = json.load(open(os.path.join(ROOT, "controllers", "saathi", "scene.json")))
runs = {k: [json.loads(l) for l in open(os.path.join(ROOT, "out", f"ab_{k}", "states.jsonl"))] for k in ("baseline", "saathi", "vision")}
summ = {k: json.load(open(os.path.join(ROOT, "out", f"ab_{k}", "summary.json"))) for k in runs}
pair = [np.array(next(s["pos"] for s in scene["standers"] if s["name"] == n)) for n in scene["pairs"][0]]
mid = (pair[0] + pair[1]) / 2


def trajectories():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(16, 9), dpi=110)
    ax.add_patch(Rectangle((-9, -6), 18, 12, fill=False, lw=2.5, ec="#5a625f"))
    for cx, cy, sx, sy in scene["obstacles"]:
        ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy, fc="#d9dfdb", ec="#b5bdb8"))
    for name, (gx, gy) in scene["goals"].items():
        ax.text(gx, gy + (0.55 if gy > 0 else -0.75), name, ha="center", fontsize=13, color="#6b736f")
    for w in runs["saathi"][0]["people"]:
        tr = np.array([s["people"][w] for s in runs["saathi"]])
        ax.plot(tr[:, 0], tr[:, 1], color="#c9cfcb", lw=1.2, zorder=1)
    ax.plot(*zip(*pair), color="#2b6cb0", lw=2, ls=":", zorder=3)
    for p in pair:
        ax.add_patch(plt.Circle(p, 0.25, color="#2b6cb0", zorder=4))
    ax.text(mid[0] + 0.45, mid[1] + 0.05, "two people\ntalking", fontsize=13, color="#2b6cb0", va="center")
    for k, col, lab in (("baseline", "#8f9894", "Normal robot"), ("saathi", "#0f5c52", "Saathi")):
        tr = np.array([s["robot"][:2] for s in runs[k]])
        s = summ[k]
        ax.plot(tr[:, 0], tr[:, 1], color=col, lw=4, zorder=5, solid_capstyle="round",
                label=f"{lab}: {s['near_misses']} near-misses, {'cut through the conversation' if s['conversation_cuts'] else 'went around the conversation'}, closest {s['min_dist']:.2f} m")
    ax.plot(*scene["start"], marker="o", ms=12, color="#b8550d", zorder=6)
    ax.text(scene["start"][0] + 0.3, scene["start"][1] - 0.6, "Entrance", fontsize=13, color="#b8550d")
    ax.set_xlim(-9.3, 9.3); ax.set_ylim(-6.3, 6.3); ax.set_aspect("equal"); ax.axis("off")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.09), ncol=1, fontsize=14, frameon=False)
    ax.set_title("Same crowd, same trip to Radiology (Webots)", fontsize=17, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "trajectories.png"))


def side_by_side():
    tiles = []
    for k, lab in (("baseline", "NORMAL ROBOT: cuts through the conversation"), ("saathi", "SAATHI: goes around it")):
        st = min(runs[k], key=lambda s: np.hypot(s["robot"][0] - mid[0], s["robot"][1] - mid[1]))
        img = cv2.imread(os.path.join(ROOT, "out", f"ab_{k}", f"paircam_{st['t']:06.2f}.jpg"))
        cv2.imwrite(os.path.join(OUT, f"side_{k}_raw.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.rectangle(img, (0, 0), (img.shape[1], 52), (82, 92, 15) if k == "saathi" else (110, 110, 110), -1)
        cv2.putText(img, lab, (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(img)
        cv2.imwrite(os.path.join(OUT, f"side_{k}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(os.path.join(OUT, "side_by_side.jpg"), np.hstack([tiles[0], np.full((tiles[0].shape[0], 16, 3), 255, np.uint8), tiles[1]]), [cv2.IMWRITE_JPEG_QUALITY, 90])


def blackbox():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "out", "ab_vision", "blackbox.jsonl"))]
    subject = lambda r: next((w for w in r["decision"].split() if w.startswith("P") and w[1:].isdigit()), None)
    pick = next((r for r in rows if r["decision"].startswith(("Waiting", "Sliding", "Slowing")) and subject(r) in r.get("in_view", [])), rows[0])
    shutil.copy(os.path.join(ROOT, "out", "ab_vision", pick["frame"]), os.path.join(OUT, "blackbox.jpg"))
    json.dump(pick, open(os.path.join(OUT, "blackbox.json"), "w"), indent=1)
    return pick


trajectories()
side_by_side()
print(json.dumps(blackbox()))
print(json.dumps(summ, indent=1))
