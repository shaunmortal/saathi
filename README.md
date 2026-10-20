# Saathi: a crowd-aware hospital OPD robot that remembers people

**Hack in Hills '26, PS-01 Vision-Based Autonomous Robot (simulated).** Team Glitch. Built and tested in Webots on a MacBook Air M1 (8 GB).

![Saathi driving through the OPD hall: camera view with YOLO11 boxes, LiDAR, planner and status](docs/dashboard.gif)

An Indian district-hospital OPD hall: thousands of first-time patients a day, most of them alone, and 7 in 10 need a human to find their way.
Saathi is a service robot for that hall. It walks a patient to Radiology without cutting through crowds or conversations, reads the
OPD slip, talks in Hindi, notices a fall and stays with the patient until a nurse comes. Several Saathis share one memory of people
(clothes and height, never faces), so when a father says "mera beta kho gaya, laal t-shirt", the team estimates where the child is **now** and goes there.

## What works today (every number below is produced by the scripts in `tools/`)

| Capability | Proof |
|---|---|
| Crowd-aware navigation (A* + social costs: personal space, conversation groups, keep-left) | 200 seeded crowds: 199/200 arrived vs 185/200 for a plain planner, near-misses 1.0 vs 3.8 per trip, 0% trips cutting a conversation (`out/bench/summary.json`) |
| Perception on the robot's own camera + depth + LiDAR | YOLO11 + ByteTrack on rendered frames; unmapped cardboard box found at 15 s and avoided (`docs/obstacles.jpg`) |
| Open-vocabulary goals | "find: dustbin" found 7.5 m away with YOLOE, arrived in 12 s |
| Fall detection with second opinion | YOLOE "person lying on the floor" + Qwen3.5-2B VLM describes the scene in 4.9 s, alert to nurse station, robot stays (`docs/fall.jpg`) |
| Shared people memory, lost-child search | 24/24 correct by eye over 96 people seen in 54 frames (`docs/clip_search.jpg`); 200-seed benchmark: memory roughly halves search time for one robot (`out/bench_lost/summary.json`) |
| Hindi voice, offline | Whisper large-v3-turbo (MLX) + phrasebook + macOS Lekha voice; self-test 5/5 understood, about 3 s each |
| Safety | 0.6 m hard stop in the controller that no planner, LLM or voice command can override; black-box decision log for every run |

![200-crowd A/B: Saathi vs baseline](docs/ab_chart.png)

Status: Round 2 prototype. Everything is simulation; see "What is real and what is simplified" below.

---

## The simulation

A district-hospital OPD hall (Hindi + English signage, token display, pharmacy queue, waiting chairs) with animated people,
and Saathi on the team's rover: camera + depth camera on a mast, 360° LiDAR, IMU, mecanum-style wheels and a face screen.

## Run

```sh
# Webots: stable R2025a does not start on macOS 27; use the nightly copied to ~/Applications (any master build after 3 Oct 2026).
~/Applications/Webots.app/Contents/MacOS/webots worlds/opd.wbt                                   # GUI
~/Applications/Webots.app/Contents/MacOS/webots --batch --minimize --mode=fast worlds/opd.wbt     # record a run into out/run
.venv/bin/python tools/make_media.py     # YOLO11s + ByteTrack on Saathi's camera -> out/media/dashboard.mp4 and stills
```

Regenerate after editing: `tools/make_world.py` (world layout, crowd paths, route), `tools/make_signs.sh` (sign textures),
`tools/make_floor.py` (floor tiles).

Everything behind the PPT, in order (all deterministic):

```sh
tools/final_runs.sh                            # 7 Webots runs: A/B, camera+LiDAR, unmapped obstacles, find:dustbin, fall
.venv/bin/python tools/bench.py 200         # headless A/B on 200 seeded crowds (planner, true positions)
.venv/bin/python tools/make_ab_media.py; .venv/bin/python tools/make_feature_media.py
.venv/bin/python tools/make_media.py out/ab_vision; .venv/bin/python tools/make_media.py out/ab_saathi
.venv/bin/python tools/clip_search.py         # memory search test for Saathi Parivaar -> out/media/parivaar
.venv/bin/python tools/make_ppt.py && tools/render_ppt.sh ppt/Saathi_HackInHills26.pptx --pdf
```

One run: `tools/run_webots.sh NAME --mode=saathi|baseline --perception=gt|vision --goal=Radiology|find:dustbin --unmapped=1 --fall=4`.
The VLM (Qwen3.5-2B, `models/qwen35_2b`) runs in `.venv-brain` (mlx-vlm 0.7.6): `.venv-brain/bin/python tools/vlm_see.py OUT.json IMAGE...`

## Saathi Parivaar: a shared memory of people (finding a lost child)

`controllers/saathi/memory.py` remembers who each robot saw: where, when, how tall, which way they walked, and a CLIP
embedding of the crop (clothes, never a face). It also remembers which floor cells were in view and empty. When a parent
describes a child, it finds the best match (text score + height + moves that are physically possible), estimates where the
child is NOW with particles (keep walking, go to a place, stay, wander; places already looked at are ruled out), and sends the
robot to look there. Once the child is found, every record of them is deleted.

```sh
TIMEOUT=1500 tools/run_webots.sh lost --perception=vision --lost=1 --report=60 --until=150 --every=0.5   # Webots scene
.venv/bin/python tools/bench_lost.py 200                                                                   # 200 seeds x 4 strategies x 1-3 robots
```

The Webots scene: a father at the registration counter; his son wanders off to the water cooler while Saathi drives to
Radiology; at `--report` seconds the father asks the help desk. The bench (`out/bench_lost/`) uses a bigger floor (the hall plus a
corridor, lab, radiology block, toilets and a stair/lift lobby), a lost-child behaviour generator the predictor never sees,
look-alike children in half the seeds, and CLIP text scores and heights measured on Webots renders.
Measured on our renders: CLIP image-to-image similarity cannot tell people apart (same person 0.91 vs others 0.88, median), so a
person is followed by text score, height (depth camera: boy 1.33 m, girl 1.46 m) and physically possible moves instead.

## Talking to Saathi (Hindi voice)

`tools/voice.py` (run it in `.venv-brain`) listens on the Mac's microphone, transcribes Hindi / Hinglish / English with Whisper
large-v3-turbo (4-bit, MLX, offline, `models/whisper_turbo_q4`), understands hospital requests with a phrasebook (departments,
"kho gaya" + colour + clothes, "Saathi, ruko"), answers in the Mac's Hindi voice (Lekha) and writes commands to
`out/live/commands.jsonl`. A controller started with `--live=1` obeys them.

```sh
.venv-brain/bin/python tools/voice.py --selftest      # Lekha speaks 5 requests, Whisper hears them: 5/5 understood, ~3 s each
tools/live.sh                                          # Webots in real time, Saathi waits at the entrance (add --robots=2)
.venv-brain/bin/python tools/voice.py                  # second terminal: Enter, speak 5 s ("Mera beta kho gaya, laal t-shirt")
```

Say "Saathi, ruko" to stop it: a single short word on its own is often misheard.
Gesture stop: `.venv/bin/python tools/gesture.py` watches the webcam (MediaPipe hand landmarks, `models/hand_landmarker.task`);
a fist held 0.5 s sends "stop", an open palm held 1 s sends "go". The robot's 0.6 m safety stop never depends on either.

## Setup on another Mac (Apple silicon)

```sh
git clone <repo> saathi_sim && cd saathi_sim
# from the team's Mac: copy models/ (about 2.6 GB) into saathi_sim/, and Webots.app into ~/Applications
brew install python@3.10                # or the python.org 3.10 installer
tools/setup_mac.sh                      # Python envs, Webots controller paths, checks
.venv/bin/python tools/bench.py 200     # should match the PPT: Saathi 199/200 arrived, 73% fewer near-misses
```

The VLM weights are `mlx-community/Qwen3.5-2B-4bit` on Hugging Face.

## What is real and what is simplified

- Real: the 3D render; camera, depth and LiDAR data; YOLO11 / YOLOE on the rendered frames; the planner; physics wheels driven by speed commands.
- Simplified: people walk fixed paths and do not react to the robot; the robot's own position comes from the simulator (LiDAR localisation on the real rover);
  `--perception=gt` gives the planner the people's true positions (the 200-crowd A/B does this); the nurse is simulated (6 s).

## Gotchas

- Library PROTOs and their meshes/textures are vendored in `protos/projects/` because Webots' own downloads from GitHub fail with HTTP/2 errors. No network needed.
- `controllers/bvh_animation` is the stock Webots BVH player copied next to its `libbvh_util.dylib`; a symlink to the app's copy cannot find the library.
- The BVH player measures every frame against frame 0 (the T-pose), so `motions/stand.bvh` keeps frame 0 and repeats one mid-walk pose after it.
- The Sandra model is not used: her left arm stays in the T-pose with this player.
