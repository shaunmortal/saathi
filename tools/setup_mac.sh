#!/bin/zsh
# One-time setup on another Apple-silicon Mac: Python envs, Webots controller paths, model links.
# Needs Python 3.10 (brew install python@3.10, or the python.org 3.10 installer), Webots in ~/Applications and models/ copied over.
set -e
R=${0:A:h:h}; cd $R
PY=$(command -v python3.10 || ls /opt/homebrew/opt/python@3.10/bin/python3.10 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 2>/dev/null | head -1 || true)
[[ -x $PY ]] || { echo "Python 3.10 not found: brew install python@3.10 (or the python.org 3.10 installer)"; exit 1; }
[[ -e .venv ]] || $PY -m venv .venv
.venv/bin/pip install -q -r requirements.txt
[[ -e .venv-brain ]] || $PY -m venv .venv-brain
.venv-brain/bin/pip install -q -r requirements-brain.txt
for c in saathi cctv; do printf '[python]\nCOMMAND = %s\n' "$R/.venv/bin/python" > controllers/$c/runtime.ini; done
.venv/bin/python tools/make_world.py >/dev/null  # the world file holds absolute paths to the motion files
for d in . controllers/saathi; do [[ -e $d/mobileclip_blt.ts ]] || ln -s $R/models/mobileclip_blt.ts $d/mobileclip_blt.ts; done  # YOLOE's text encoder, looked up in the working dir
for f in models/yolo11s.pt models/yoloe-11s-seg.pt models/mobileclip_blt.ts models/qwen35_2b/model.safetensors models/weights/clip/ViT-B-32.pt; do
  [[ -e $f ]] || echo "MISSING $f: copy models/ from the team's Mac"
done
[[ -x ~/Applications/Webots.app/Contents/MacOS/webots ]] || echo "MISSING ~/Applications/Webots.app: copy it from the team's Mac"
echo "Done. Check: .venv/bin/python tools/bench.py 200   (expect Saathi 199/200 arrived, 73% fewer near-misses)"
