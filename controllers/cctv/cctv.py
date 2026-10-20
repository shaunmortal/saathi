"""Fixed or flown camera (CCTV / chase): saves a frame every --every s of sim time into --out.

--look=x,y,z points the camera at a world point once at start-up; the chase camera is flown by Saathi's supervisor instead.
"""
import math, os, sys
from controller import Supervisor


def yaw_pitch_rotation(yaw, pitch):
    """Axis-angle for Rz(yaw)·Ry(pitch): heading yaw, looking down by pitch."""
    w1, z1, w2, y2 = math.cos(yaw / 2), math.sin(yaw / 2), math.cos(pitch / 2), math.sin(pitch / 2)
    v = (-z1 * y2, w1 * y2, w2 * z1)
    s = math.sqrt(sum(c * c for c in v)) or 1e-9
    return [v[0] / s, v[1] / s, v[2] / s, 2 * math.acos(max(-1.0, min(1.0, w1 * w2)))]


if __name__ == "__main__":
    args = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    out, every, until = os.path.abspath(args.get("out", "out")), float(args.get("every", 2)), float(args.get("until", 0))
    os.makedirs(out, exist_ok=True)
    bot = Supervisor()
    dt = int(bot.getBasicTimeStep())
    cam = bot.getDevice("cam")
    p = max(dt, round(every * 1000 / dt) * dt) if every > 0 else 0
    if p:  # render only when a frame is saved: four HD cameras rendered every step slow the whole simulation
        cam.enable(p)
    if "look" in args:
        tx, ty, tz = map(float, args["look"].split(","))
        x, y, z = bot.getSelf().getField("translation").getSFVec3f()
        bot.getSelf().getField("rotation").setSFRotation(yaw_pitch_rotation(math.atan2(ty - y, tx - x), math.atan2(z - tz, math.hypot(tx - x, ty - y))))
    name, nxt = bot.getName(), p / 1000 if p else float("inf")
    while bot.step(dt) != -1:
        t = bot.getTime()
        if t + 1e-6 >= nxt:
            cam.saveImage(os.path.join(out, f"{name}_{t:06.2f}.jpg"), 92)
            nxt += every
        if until and t >= until:
            bot.simulationQuit(0)
