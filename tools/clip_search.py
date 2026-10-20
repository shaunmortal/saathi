"""Memory search test for Saathi Parivaar: can a spoken description find a person among everyone Saathi's camera saw?

Every 6th camera frame of out/ab_vision -> YOLO11s person crops -> CLIP ViT-B/32 embeddings; each description is matched
against all crops (no faces, no IDs). Writes out/media/parivaar/clip_search.jpg (top 8 per description), clip_child.jpg
(the child row only) and clip_search.json. Whether the top 8 are the right person is checked by eye on the image.
"""
import glob, json, os, re
import clip, cv2, numpy as np, torch
from PIL import Image
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "media", "parivaar")
os.makedirs(OUT, exist_ok=True)
QUERIES = ["a photo of a small child in a red shirt", "a photo of a woman in a green top", "a photo of a man in a blue shirt and jeans"]
LABELS = ["\"small child in a red shirt\"", "\"woman in a green top\"", "\"man in a blue shirt and jeans\""]

frames = sorted(glob.glob(os.path.join(ROOT, "out", "ab_vision", "cam_*.png")))[::6]
yolo = YOLO(os.path.join(ROOT, "models", "yolo11s.pt"))
model, prep = clip.load(os.path.join(ROOT, "models", "weights", "clip", "ViT-B-32.pt"), device="cpu")
crops, meta = [], []
for f in frames:
    img = cv2.imread(f)
    for x0, y0, x1, y1 in yolo.predict(img, classes=[0], conf=0.4, verbose=False)[0].boxes.xyxy.int().tolist():
        if y1 - y0 >= 60:  # people too far away to describe are skipped
            crops.append(img[y0:y1, x0:x1])
            meta.append(dict(t=float(re.search(r"_(\d+\.\d+)\.", f).group(1)), box=[x0, y0, x1, y1]))
with torch.no_grad():
    E = torch.cat([model.encode_image(torch.stack([prep(Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))) for c in crops[i:i + 64]]))
                   for i in range(0, len(crops), 64)])
    T = model.encode_text(clip.tokenize(QUERIES))
S = ((E / E.norm(dim=-1, keepdim=True)) @ (T / T.norm(dim=-1, keepdim=True)).T).numpy()

rows, result = [], dict(frames=len(frames), people=len(crops), queries=[])
for j, (q, lab) in enumerate(zip(QUERIES, LABELS)):
    top = np.argsort(-S[:, j])[:8]
    result["queries"].append(dict(query=q, top8=[dict(meta[i], score=round(float(S[i, j]), 3)) for i in top]))
    band = np.full((44, 8 * 110, 3), 255, np.uint8)
    cv2.putText(band, f"{lab}  ->  top 8 of {len(crops)} people seen", (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2, cv2.LINE_AA)
    rows.append(np.vstack([band, np.hstack([cv2.resize(crops[i], (110, 240)) for i in top])]))
cv2.imwrite(os.path.join(OUT, "clip_search.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
cv2.imwrite(os.path.join(OUT, "clip_child.jpg"), rows[0], [cv2.IMWRITE_JPEG_QUALITY, 92])
json.dump(result, open(os.path.join(OUT, "clip_search.json"), "w"), indent=1)
print(f"{len(frames)} frames, {len(crops)} people ->", OUT)
