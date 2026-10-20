"""Saathi Parivaar's memory of people: who was seen, where, when, how tall and walking which way (clothes and height,
never a face); which floor cells were in view and empty; and where a remembered person can be now.

A description ("small child in a red shirt") is matched with CLIP text embeddings. On our renders CLIP's image-to-image
similarity cannot tell people apart (median 0.91 for the same person, 0.88 for others), so a person is followed through
time by their text score, their height and whether each move was physically possible, not by a face or a photo match.
Works on any grid with blocked, X, Y, cell(x, y), x0, y0 and res (brain.Grid for the hall, a bigger floor in the benchmark).
Shared by the Webots controller and the headless benchmark. Run this file to self-check.
"""
import math
import numpy as np
from scipy.ndimage import uniform_filter

CHILD_H = 1.41   # m: shorter is a child (the boy model measures 1.33 m on the depth camera, the girl 1.46 m)
V_MAX = 1.8      # m/s: faster than anyone could have walked between two sightings
LINK_GAP = 20.0  # s: a new track can only be the same person if they were seen again within this (longer: anyone could be anyone)
DT = 0.5         # s per prediction step


class PeopleMemory:
    def __init__(self, grid, places):
        self.g, self.places = grid, np.array(list(places), float)  # where people walk to: doors, water cooler, counters
        self.rows, self.seen = [], np.full(grid.blocked.shape, -np.inf)  # sightings; last time each floor cell was in view

    def add(self, t, track, x, y, vx, vy, h, emb, robot=1, crop=None):
        self.rows.append(dict(t=t, track=track, robot=robot, x=x, y=y, vx=vx, vy=vy, h=h, emb=emb / np.linalg.norm(emb), crop=crop))

    def look(self, t, x, y, angles, ranges, max_r=6.0):
        """The floor along each ray in view, up to where the LiDAR hit something, was looked at at time t."""
        for a, r in zip(angles, ranges):
            for d in np.arange(0.5, min(r - 0.3, max_r), self.g.res):
                self.seen[self.g.cell(x + d * math.cos(a), y + d * math.sin(a))] = t

    def forget(self, keys):
        """Delete everything remembered about these people (robot, track): done once a lost person is found."""
        self.rows = [r for r in self.rows if (r["robot"], r["track"]) not in keys]

    def search(self, q, child=False, k=3, exclude=()):
        """q: unit CLIP text embedding -> up to k people, best first: dict(score, key, last, chain).
        A person's score is the median over their sightings; a child query skips anyone measured taller than CHILD_H;
        exclude: (robot, track) keys the parent has already said are not the one."""
        by = {}
        for r in self.rows:
            by.setdefault((r["robot"], r["track"]), []).append(r)
        cands = []
        for key, rs in by.items():
            if key in exclude:
                continue
            hs = [r["h"] for r in rs if r["h"] is not None]
            if child and (not hs or np.median(hs) >= CHILD_H):
                continue
            cands.append((float(np.median([r["emb"] @ q for r in rs])), key, sorted(rs, key=lambda r: r["t"])))
        cands.sort(key=lambda c: -c[0])
        out = []
        for score, key, rs in cands[:k]:
            chain = list(rs)  # follow them forward through later tracks that match as well and they could have walked to
            for s2, key2, rs2 in sorted(cands, key=lambda c: c[2][0]["t"]):
                a, b = chain[-1], rs2[0]
                if key2 != key and s2 >= score - 0.02 and 0 < b["t"] - a["t"] <= LINK_GAP and math.hypot(b["x"] - a["x"], b["y"] - a["y"]) <= V_MAX * (b["t"] - a["t"]) + 1.0:
                    chain += rs2
            out.append(dict(score=score, key=key, last=chain[-1], chain=chain))
        return out

    def _cells(self, P):
        g = self.g
        return np.clip(((P[:, 1] - g.y0) / g.res).astype(int), 0, g.blocked.shape[0] - 1), np.clip(((P[:, 0] - g.x0) / g.res).astype(int), 0, g.blocked.shape[1] - 1)

    def where_now(self, s, t, n=1500, seed=0, use_seen=True):
        """Where someone last seen in sighting s can be at time t: an (n, 2) array of particles.
        Each particle keeps walking the way they went, walks to a place (ahead of them if they were walking), stays, or
        wanders, at 0.5-1.2 m/s, and stops at walls. A particle standing in a cell that was in view after it got there (and
        nobody was seen) keeps a tenth of its weight: the camera misses a child about 1 time in 10, and they may walk in
        later. The cloud is resampled by weight. Particles move on from the last call for the same sighting (cheap to repeat)."""
        key = (s["t"], s["x"], s["y"], n, seed)
        self._wn = getattr(self, "_wn", {})
        c = self._wn.get(key)
        if c is None or t < c["t"]:
            if len(self._wn) > 16:
                self._wn.clear()
            c = self._wn[key] = self._start(s, n, seed, key)
        while c["t"] + DT <= t + 1e-9:
            self._step(c)
        P, moving, since = c["P"], c["moving"], c["since"]
        if not use_seen:  # ablation: ignore where the robots have already looked
            return P.copy()
        missed = self.seen[self._cells(P)] >= np.where(moving, t - 3.0, since)  # walkers: in view in the last 3 s
        w = np.where(missed, 0.1, 1.0)
        return P[np.random.default_rng(seed + int(t * 2)).choice(len(P), len(P), p=w / w.sum())]

    def where_now_all(self, cands, t, n=1500, seed=0, use_seen=True, anywhere=None):
        """Particles for several people who could be the one asked about, as (sighting, weight), plus a share spread over the
        whole floor (a tenth of the weight where we looked in the last 60 s), so a look-alike in the memory or a wrong first
        guess cannot stall the search. That share is 15% if the best match was last seen walking (their direction says a lot),
        else 40%."""
        if anywhere is None:
            anywhere = 0.15 if cands and math.hypot(cands[0][0]["vx"], cands[0][0]["vy"]) > 0.2 else 0.4
        w = np.array([c[1] for c in cands], float)
        w = w / w.sum() * (1 - anywhere) if len(w) else w
        parts = [self.where_now(s, t, max(1, int(n * wk)), seed + k, use_seen) for k, ((s, _), wk) in enumerate(zip(cands, w))]
        free = np.argwhere(~self.g.blocked)
        fw = np.where(self.seen[free[:, 0], free[:, 1]] >= t - 60, 0.1, 1.0) if use_seen else np.ones(len(free))
        pick = free[np.random.default_rng(seed + int(t)).choice(len(free), max(1, int(n * anywhere)), p=fw / fw.sum())]
        parts.append(np.stack([self.g.X[pick[:, 0], pick[:, 1]], self.g.Y[pick[:, 0], pick[:, 1]]], 1))
        return np.concatenate(parts)

    def _start(self, s, n, seed, key):
        rng = np.random.default_rng(seed)
        P = np.tile([s["x"], s["y"]], (n, 1)).astype(float)
        walking = math.hypot(s["vx"], s["vy"]) > 0.2
        h0 = math.atan2(s["vy"], s["vx"]) if walking else 0.0
        mode = rng.choice(4, n, p=[0.3, 0.4, 0.15, 0.15] if walking else [0.0, 0.5, 0.3, 0.2])  # keep going, to a place, stay, wander
        d = self.places[None] - P[:, None]
        dist = np.hypot(d[..., 0], d[..., 1]) + 1e-6
        ahead = (d[..., 0] * math.cos(h0) + d[..., 1] * math.sin(h0)) / dist if walking else np.zeros_like(dist)
        w = np.exp(2.0 * ahead) / (1 + dist / 15)  # places in the walking direction; nearer a little more likely
        target = self.places[(np.cumsum(w / w.sum(1, keepdims=True), 1) > rng.random((n, 1))).argmax(1)]
        head = h0 + rng.normal(0, 0.25, n) if walking else rng.uniform(-math.pi, math.pi, n)
        return dict(key=key, rng=rng, t=float(s["t"]), P=P, mode=mode, v=rng.uniform(0.5, 1.2, n), head=head, target=target,
                    moving=mode != 2, since=np.full(n, float(s["t"])))  # since: when the particle got to where it now stands

    def _step(self, c):
        P, mode, moving, rng = c["P"], c["mode"], c["moving"], c["rng"]
        to = c["target"] - P
        togo = np.hypot(to[:, 0], to[:, 1])
        head = np.where(mode == 1, np.arctan2(to[:, 1], to[:, 0]), c["head"] + np.where(mode == 3, rng.normal(0, 0.6, len(P)), 0.0))
        step = np.where(mode == 1, np.minimum(c["v"] * DT, togo), c["v"] * DT) * moving
        nxt = P + np.stack([np.cos(head), np.sin(head)], 1) * step[:, None]
        ok = ~self.g.blocked[self._cells(nxt)]
        c["P"] = np.where((moving & ok)[:, None], nxt, P)
        c["head"] = np.where(moving & ~ok & (mode == 3), head + math.pi, head)       # wanderers turn back from walls
        stop = moving & ((~ok & (mode != 3)) | ((mode == 1) & (togo <= c["v"] * DT)))  # the others stop there
        c["t"] += DT
        c["since"] = np.where(stop, c["t"], c["since"])
        c["moving"] = moving & ~stop

    def viewpoint(self, P, xy, standoff=1.8):
        """-> (goal, peak, share): the densest ~1 m patch of particles, and a spot standoff metres short of it on the robot's side."""
        H = np.zeros(self.g.blocked.shape)
        np.add.at(H, self._cells(P), 1)
        D = uniform_filter(H, 5)
        j, i = np.unravel_index(int(D.argmax()), D.shape)
        px, py = float(self.g.X[j, i]), float(self.g.Y[j, i])
        dx, dy = xy[0] - px, xy[1] - py
        k = min(standoff, math.hypot(dx, dy)) / (math.hypot(dx, dy) or 1.0)
        return (px + dx * k, py + dy * k), (px, py), float(D[j, i] * 25 / max(1, len(P)))


if __name__ == "__main__":
    from brain import Grid
    g = Grid([])
    m = PeopleMemory(g, [(8.0, 0.0), (-8.0, 0.0)])
    s = dict(t=0.0, x=0.0, y=0.0, vx=1.0, vy=0.0)
    P = m.where_now(s, 8.0)
    assert len(P) == 1500 and P[:, 0].mean() > 3.0, P.mean(0)          # walking east: the cloud moves east
    goal, peak, share = m.viewpoint(P, (-5.0, 0.0))
    assert peak[0] > 5.0 and goal[0] < peak[0], (goal, peak)            # the place ahead (8, 0) holds the most particles
    m.look(8.0, 3.0, 0.0, [0.0], [9.0])                                 # now we look east from (3, 0) and see no one
    P2 = m.where_now(s, 8.0)
    gone = lambda Q: float(np.mean((np.abs(Q[:, 1]) < 0.2) & (Q[:, 0] > 3.4) & (Q[:, 0] < 8.6)))
    assert gone(P2) < 0.5 * gone(P), (gone(P), gone(P2))  # far fewer particles left where we just looked
    e = np.eye(4)
    m.add(1.0, 7, 1.0, 1.0, 0.0, 0.0, 2.2, e[0] + 0.1 * e[1])          # a tall man who matches the words best
    m.add(1.0, 8, 2.0, 2.0, 0.0, 0.0, 1.3, e[0] + 0.5 * e[1])          # a child, matching less well
    m.add(3.0, 9, 3.0, 2.5, 0.0, 0.0, 1.3, e[0] + 0.5 * e[1])          # the same child later, under a new track ID
    m.add(3.5, 10, -8.0, 5.0, 0.0, 0.0, 1.3, e[0] + 0.5 * e[1])        # a look-alike too far away to be him
    best = m.search(e[0], child=True)[0]
    assert best["key"] == (1, 8) and best["last"]["track"] == 9, best
    m.forget({(1, 8), (1, 9)})
    assert all(r["track"] not in (8, 9) for r in m.rows)
    print(f"memory ok: {gone(P):.0%} -> {gone(P2):.0%} of particles in the strip just looked at; child found through a new track ID; forgotten")
