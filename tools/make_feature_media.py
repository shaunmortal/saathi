"""PPT visuals for the PS-01 features, from the final runs -> out/media/features/.

obstacles.jpg  map-only vs depth vision at the cardboard box nobody put on the map (chase cameras), plus YOLOE's label
found_box.jpg  Saathi's camera when it found the box, with YOLOE's box drawn
dustbin.jpg    Saathi's camera when it found the dustbin ("find:dustbin"), and arrive.jpg when it got there
fall.jpg       Saathi's camera when it classified the fall (YOLOE "person lying on the floor"), stay.jpg staying with them
"""
import glob, json, os, re, shutil
import cv2
import numpy as np
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "media", "features")
os.makedirs(OUT, exist_ok=True)
run = lambda name, *p: os.path.join(ROOT, "out", name, *p)
states = lambda name: [json.loads(l) for l in open(run(name, "states.jsonl"))]
scene = json.load(open(os.path.join(ROOT, "controllers", "saathi", "scene.json")))
yoloe = YOLO(os.path.join(ROOT, "models", "yoloe-11s-seg.pt"))


def frame(name, kind, t):
    fs = glob.glob(run(name, f"{kind}_*.*"))
    return min(fs, key=lambda f: abs(float(re.search(r"_(\d+\.\d+)\.", f).group(1)) - t))


def label(img, text, colour):
    cv2.rectangle(img, (0, 0), (img.shape[1], 52), colour, -1)
    cv2.putText(img, text, (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def draw_named(path, names, out, keep):
    """Run YOLOE with these prompts and draw the boxes whose name is in keep."""
    yoloe.set_classes(names, yoloe.get_text_pe(names))
    img = cv2.imread(path)
    r = yoloe.predict(img, conf=0.3, verbose=False)[0]
    for (x0, y0, x1, y1), c, s in zip(r.boxes.xyxy.int().tolist(), r.boxes.cls.int().tolist(), r.boxes.conf.tolist()):
        if names[c] in keep:
            cv2.rectangle(img, (x0, y0), (x1, y1), (32, 160, 240), 3)
            cv2.putText(img, f"{names[c]} {s:.2f}", (x0 + 4, max(18, y0 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (32, 160, 240), 2, cv2.LINE_AA)
    cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 92])


# Unknown obstacle: both runs at the moment they are closest to the cardboard box.
box = next((c for n, c, s in scene.get("unmapped", []) if n == "cardboard box"), None) or [2.0, 3.1]
tiles = []
for name, text, col in (("ob_maponly", "MAP ONLY: drives into the box", (110, 110, 110)), ("ob_vision", "WITH DEPTH VISION: sees it, goes around", (82, 92, 15))):
    st = min(states(name), key=lambda s: np.hypot(s["robot"][0] - box[0], s["robot"][1] - box[1]))
    img = label(cv2.imread(frame(name, "chase", st["t"])), text, col)
    cv2.imwrite(os.path.join(OUT, f"obstacle_{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    tiles.append(img)
cv2.imwrite(os.path.join(OUT, "obstacles.jpg"), np.hstack([tiles[0], np.full((tiles[0].shape[0], 16, 3), 255, np.uint8), tiles[1]]), [cv2.IMWRITE_JPEG_QUALITY, 90])
ev = [json.loads(l) for l in open(run("ob_vision", "events.jsonl"))]
found_box = next(e for e in ev if "cardboard box" in e["status"])
draw_named(frame("ob_vision", "cam", found_box["t"] + 0.3), ["cardboard box", "yellow caution sign", "person standing", "person walking"],
           os.path.join(OUT, "found_box.jpg"), {"cardboard box", "yellow caution sign"})

# Find the dustbin.
ev = [json.loads(l) for l in open(run("find_dustbin", "events.jsonl"))]
found = next(e for e in ev if e["status"].startswith("Found the dustbin"))
arrive = next(e for e in ev if e["status"].startswith("Arrived"))
draw_named(frame("find_dustbin", "cam", found["t"]), ["dustbin", "person standing", "person walking"], os.path.join(OUT, "dustbin.jpg"), {"dustbin"})
shutil.copy(frame("find_dustbin", "chase", arrive["t"]), os.path.join(OUT, "arrive.jpg"))

# Fall: the frame Saathi classified, and Saathi staying beside the person.
alert = json.load(open(run("fall_vision", "alert_fall.json")))
draw_named(run("fall_vision", "alert_fall.jpg"), ["person lying on the floor", "person standing", "person walking"], os.path.join(OUT, "fall.jpg"), {"person lying on the floor"})
ev = [json.loads(l) for l in open(run("fall_vision", "events.jsonl"))]
stay = next(e for e in ev if e["status"].startswith("Staying"))
shutil.copy(frame("fall_vision", "chase", stay["t"] + 1.5), os.path.join(OUT, "stay.jpg"))
json.dump(dict(found_box=found_box, dustbin=found, dustbin_arrived=arrive, fall_alert=alert, fall_stay=stay), open(os.path.join(OUT, "facts.json"), "w"), indent=1)
print("wrote", OUT)
