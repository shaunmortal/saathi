<div align="center">

# 🤖 Saathi
### *Raasta bhi, saath bhi.*
**A guide robot for Indian hospital OPDs. Talks in Hindi, reads the crowd, remembers people.**

[![Hack in Hills '26](https://img.shields.io/badge/Hack%20in%20Hills%20'26-Top%20500-ff7a00?style=for-the-badge)](https://unstop.com/hackathons/hack-in-hills-26-galgotias-university-gu-greater-noida-1752595)
[![PS-01](https://img.shields.io/badge/PS--01-Vision--Based%20Autonomous%20Robot-1f6feb?style=for-the-badge)](#ps-01-every-line-with-proof)
[![Webots](https://img.shields.io/badge/Webots-simulation-2ea44f?style=for-the-badge)](#run-it)
[![Runs on](https://img.shields.io/badge/Runs%20on-MacBook%20Air%20M1%20%7C%208%20GB-000?style=for-the-badge&logo=apple&logoColor=white)](#run-it)

<img src="docs/dashboard.gif" width="900" alt="Saathi driving through the OPD hall">

*Chase cam · Saathi's camera with YOLO boxes and distances · depth · map · 360° LiDAR · its thinking log. One real run.*

</div>

<br>

<table align="center">
<tr>
<td align="center"><h1>14–15k</h1>OPD patients <b>a day</b><br>at AIIMS Delhi</td>
<td align="center"><h1>69.6%</h1>of first-time visitors<br><b>needed a person</b> to find their way</td>
<td align="center"><h1>98%</h1>of older patients<br><b>come alone</b></td>
<td align="center"><h1>0</h1>wayfinding robots found<br>in any Indian OPD</td>
</tr>
</table>

<br>

## What Saathi does

<table>
<tr>
<td width="50%" align="center">
<img src="docs/crowd.gif" alt="Saathi weaving through the crowd">
<br><b>🚶 Walks you to Radiology at your pace</b><br><sub>Predicts where each person will be in 2 s. Slides sideways on mecanum wheels instead of stopping dead.</sub>
</td>
<td width="50%" align="center">
<img src="docs/sees.jpg" alt="What Saathi sees: people with IDs and distances">
<br><b>👀 Sees every person with ID and distance</b><br><sub>YOLO11 + depth camera + 360° LiDAR. Placed on the floor within 0.10 m.</sub>
</td>
</tr>
<tr>
<td colspan="2" align="center">
<img src="docs/side_by_side.jpg" alt="Normal robot cuts through a conversation; Saathi goes around">
<br><b>🙅 Never cuts through a conversation</b><br><sub>Same crowd, same goal. Left: a normal planner. Right: Saathi.</sub>
</td>
</tr>
<tr>
<td align="center">
<img src="docs/obstacles.jpg" alt="Unmapped box and wet-floor sign avoided">
<br><b>📦 Sees what the map does not have</b><br><sub>Wet-floor board and a cardboard box: map-only robot hit 2, Saathi 0.</sub>
</td>
<td align="center">
<img src="docs/dustbin.jpg" alt="Found the dustbin by sight">
<br><b>🔍 "Dustbin dhoondo"</b><br><sub>Finds anything by name with open-vocabulary vision, then drives there. 12 s.</sub>
</td>
</tr>
<tr>
<td align="center">
<img src="docs/fall.jpg" alt="Fall detected 0.3 s after it happened">
<br><b>🚨 Spots a fall in 0.3 s, alerts the nurse, stays</b><br><sub>A vision-language model gives a second opinion so resting patients don't page nurses all day.</sub>
</td>
<td align="center">
<img src="docs/slide_015.png" alt="Black box: Tum ruke kyun?">
<br><b>📼 "Tum ruke kyun?"</b><br><sub>Every decision is saved with its camera frame. The answer comes from the record, not imagination.</sub>
</td>
</tr>
</table>

<br>

## Saathi Parivaar: *ek yaad, kai aankhein*

**"Mera beta kho gaya, laal t-shirt."** Every Saathi in the hospital answers from one shared memory. One stays with papa, one goes where the boy is **now**.

<p align="center"><img src="docs/parivaar.gif" width="900" alt="Two Saathis search for a lost child from shared memory"></p>

<p align="center"><img src="docs/clip_search.jpg" width="900" alt="Memory search by description: 24 of 24 correct"></p>
<p align="center"><sub>Clothes and height only, never a face. Deleted after the reunion.</sub></p>

<br>

## Numbers, not promises

<table align="center">
<tr>
<td align="center"><h1>73%</h1><b>fewer near-misses</b><br>3.79 → 1.00 per trip</td>
<td align="center"><h1>0 / 200</h1><b>conversations cut</b><br>normal robot: 26%</td>
<td align="center"><h1>199 / 200</h1><b>trips arrived</b><br>normal robot: 185</td>
<td align="center"><h1>2×</h1><b>faster lost-child search</b><br>with memory, one robot</td>
</tr>
</table>

<p align="center">
<img src="docs/ab_chart.png" width="440" alt="200 crowds A/B">
<img src="docs/lost_chart.png" width="440" alt="Lost child, 200 seeds">
</p>
<p align="center"><sub>200 seeded crowds, deterministic, reproduced by <code>tools/bench.py</code> and <code>tools/bench_lost.py</code>.</sub></p>

<br>

## How it works

<p align="center"><img src="docs/slide_004.png" width="900" alt="Architecture"></p>

<p align="center"><sub>Reflex brain at 30 Hz · thinking brain (Whisper + Qwen3.5-2B on Apple MLX, offline) · a LiDAR safety guard no AI can override · black box.</sub></p>

## PS-01: every line, with proof

<p align="center"><img src="docs/slide_008.png" width="900" alt="PS-01 checklist with proof"></p>

## The body

<p align="center">
<img src="docs/team_rover.jpg" width="440" alt="Team rover design">
<img src="docs/rover_sim_closeup.jpg" width="440" alt="Same rover in Webots">
<br><sub>Our rover design, and the same rover in Webots: camera, depth, LiDAR, IMU, mecanum wheels. Same brain drives both.</sub>
</p>

<br>

## Run it

```sh
~/Applications/Webots.app/Contents/MacOS/webots worlds/opd.wbt        # the OPD hall, Saathi drives to Radiology
.venv/bin/python tools/bench.py 200                                    # 200-crowd A/B, matches the numbers above
.venv-brain/bin/python tools/voice.py                                  # talk to it in Hindi
```

Setup, every command, methods, sources and honest limits: **[docs/DETAILS.md](docs/DETAILS.md)** · Round 1 deck: [PDF](ppt/Saathi_HackInHills26.pdf)

<br>

## Team Glitch

| | | |
|---|---|---|
| 🧑‍💻 **Ayush Kumar** | Lead | robot & simulation, vision & AI, shared memory, Hindi voice |
| 📚 **Soumya Raghuwanshi** | Research | Indian hospital data and sources |
| 🎤 **Simran Kumari Keshri** | Testing & pitch | voice tests, demo video |

<div align="center"><sub>Hack in Hills '26 · PS-01 · Built on a MacBook Air M1, 8 GB</sub></div>
