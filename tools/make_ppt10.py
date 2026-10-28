"""Round 2 deck, 10 slides on the official template -> ppt/Saathi_Round2.pptx. Visual first: real frames from our Webots runs, charts from
our benchmarks, diagrams drawn here. Every number is read from out/ (tools/bench.py, tools/run_webots.sh). Render: tools/render_ppt.sh ppt/Saathi_Round2.pptx --pdf"""
import glob, re
from pptkit import *

TOUR = json.load(open(P("out", "tour_vision", "summary.json")))
TOUR_EV = [json.loads(l) for l in open(P("out", "tour_vision", "events.jsonl"))]
LOSTB = json.load(open(P("out", "bench_lost", "summary.json")))
CS = json.load(open(P("out", "media", "parivaar", "clip_search.json")))
GITHUB = "github.com/shaunmortal/saathi"


def tour_frame(cam, t):
    fs = glob.glob(P("out", "tour_vision", f"{cam}_*.jpg"))
    return min(fs, key=lambda f: abs(float(re.search(r"_(\d+\.\d+)\.jpg", f).group(1)) - t))


def ev(word):
    return next(e["t"] for e in TOUR_EV if word in e["status"])


def pill(slide, x, y, w, label, fill=MINT, color=TEAL, size=13):
    card(slide, x, y, w, 0.42, fill=fill, line=None, radius=0.5)
    text(slide, x, y + 0.02, w, 0.38, [(label, size, True, color)], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)


def caption(slide, x, y, w, s, size=CAP):
    text(slide, x, y, w, 0.5, [(s, size, False, MUTED)])


def frame(slide, path, x, y, w, h, title, sub=None, tcolor=TEAL):
    picture(slide, path, x, y, w, h)
    text(slide, x, y + h + 0.05, w, 0.75, [(title, 15, True, tcolor)] + ([para(sub, 13, MUTED, space=1)] if sub else []))


prs = Presentation(P("ppt", "template.pptx"))
for _ in range(2):
    duplicate(prs, list(prs.slides)[6])
lst = prs.slides._sldIdLst
thanks_id = lst[7]
lst.remove(thanks_id)
lst.append(thanks_id)
cover, problem, solution, arch, proto, results, parivaar, proof, progress, thanks = list(prs.slides)
b0, s0, v = BENCH["baseline"], BENCH["saathi"], AB["vision"]

# 1. COVER + TEAM
TEAM = [("Ayush Kumar", "Lead: robot & simulation, vision & AI, shared memory, Hindi voice"),
        ("Soumya Raghuwanshi", "Research: Indian hospital data and sources"),
        ("Simran Kumari Keshri", "Testing and pitch: voice tests, demo video")]
team = next(t for t in cover.shapes if t.shape_type == 6)
for sh in team.shapes:
    if sh.has_text_frame and "TEAM NAME" in sh.text_frame.text:
        ps = sh.text_frame.paragraphs
        for p, val in zip(ps, ["TEAM NAME: Team Glitch", "MEMBERS & ROLES:"]):
            p.runs[0].text = " • " + val
            p.runs[0].font.size = Pt(24)
            for r in p.runs[1:]:
                r.text = ""
        ps[2]._p.getparent().remove(ps[2]._p)
text(cover, 3.43, 7.5, 6.9, 3.3, [p for i, (name, role) in enumerate(TEAM)
     for p in (para(name, 20, INK, True, space=0 if i == 0 else 12), para(role, 15, MUTED, space=1))])
text(cover, 10.6, 4.6, 8.8, 1.0, [("SAATHI", 54, True, TEAL)])
text(cover, 10.6, 5.6, 8.8, 1.2, [("A robot guide that reads Indian hospital crowds", 22, True, INK),
                                   para("PS-01 · Vision-Based Autonomous Robot · Round 2: working prototype in a two-floor Webots hospital", 15, MUTED, space=6)])
pill(cover, 10.6, 6.95, 3.3, GITHUB, fill=TEAL, color=WHITE, size=12)
picture(cover, P("docs", "floor2_frame.jpg"), 10.6, 7.5, 7.1, 3.6)

# 2. PROBLEM STATEMENT (slide 2, as asked)
set_title(problem, "PROBLEM STATEMENT: PATIENTS GET LOST IN INDIAN OPDs")
clear_body(problem)
for i, (num, cap) in enumerate([("14–15k", "OPD patients a day at one hospital (AIIMS Delhi)"),
                                ("69.6%", "of first-time OPD visitors needed a person to find their way (GMC Bhopal)"),
                                ("98%", "of older patients at AIIMS geriatric OPD come alone (2026 preprint)"),
                                ("3 h+", "total wait for 58% of 400 patients (RIMS Ranchi, 2026)")]):
    x = 0.6 + i * 3.1
    card(problem, x, 2.35, 2.9, 2.1)
    text(problem, x + 0.18, 2.45, 2.6, 1.95, [(num, 40, True, SAFFRON), para(cap, 13, space=2)])
# A first-time patient's hour today, and with Saathi: two rows of the same journey.
text(problem, 0.6, 4.7, 12.0, 0.4, [("ONE PATIENT, ONE X-RAY: TODAY vs WITH SAATHI", H, True, TEAL)])
today = [("Enters alone", "signs in English"), ("Asks the guard", "“seedha jao”"), ("Wrong corridor", "walks back"), ("Asks a nurse", "she leaves her patient"), ("Reaches Radiology", "after a long detour")]
with_s = [("“Mujhe X-ray karwana hai”", "in Hindi, at the entrance"), ("Saathi walks with them", "at their pace, through the crowd"), ("Reaches Radiology", "and says so")]
for row, (lab, steps, col, fill) in enumerate((("TODAY", today, MUTED, CARD), ("WITH SAATHI", with_s, TEAL, MINT))):
    y = 5.2 + row * 1.55
    text(problem, 0.6, y + 0.3, 1.6, 0.6, [(lab, 13, True, col)])
    n, w0 = len(steps), 10.0 / len(steps)
    for i, (a, b) in enumerate(steps):
        x = 2.3 + i * w0
        card(problem, x, y, w0 - 0.25, 1.25, fill=fill, line=None)
        text(problem, x + 0.12, y + 0.1, w0 - 0.5, 1.1, [(a, 13, True, INK), para(b, 12, MUTED, space=1)])
        if i < n - 1:
            arrow(problem, x + w0 - 0.25, y + 0.62, x + w0, y + 0.62, color=col, width=1.5)
text(problem, 0.6, 8.4, 12.0, 0.4, [("WHAT IT COSTS, AND WHY A ROBOT", H, True, TEAL)])
for i, (a, b) in enumerate([("Hours lost, appointments missed", "patients, mostly first-time, elderly, low-literacy"),
                            ("Help desks and nurses pulled away", "every “X-ray kahan hai?” is a nurse off her patient"),
                            ("A fall in a packed hall is noticed late", "nobody is watching the floor"),
                            ("Today's robot planners fail in crowds", "they freeze, or cut straight through people")]):
    x = 0.6 + i * 3.1
    card(problem, x, 8.85, 2.9, 1.55, fill=CARD)
    text(problem, x + 0.15, 8.92, 2.65, 1.45, [(a, 13, True, INK), para(b, 12, MUTED, space=2)])
picture(problem, IMG["hall"], 13.0, 2.35, 6.4, 3.6)
caption(problem, 13.0, 5.98, 6.4, "Our OPD hall in Webots: Hindi + English signs, token display, pharmacy queue, animated people")
card(problem, 13.0, 6.75, 6.4, 1.75, fill=MINT, line=None)
text(problem, 13.2, 6.85, 6.0, 1.6, [("THE GAP", 15, True, TEAL), para("No wayfinding robot found in any Indian OPD (our 2024–26 search). Guide robots exist at airports abroad; Indian OPD crowds are denser.", 13)])
text(problem, 13.0, 8.65, 6.4, 0.4, [("PS-01 · VISION-BASED AUTONOMOUS ROBOT", 14, True, TEAL)])
for i, s in enumerate(["AI vision: people + objects", "Drives itself to a goal", "Real-time decisions", "Simulated hospital (allowed)"]):
    pill(problem, 13.0 + (i % 2) * 3.25, 9.1 + (i // 2) * 0.55, 3.15, s, size=12)
footer(problem, "Sources: AIIMS OPD load, UNI and Free Press Journal, Sep 2026 · GMC Bhopal, IJCMPH 2026 (n=336) · AIIMS geriatric OPD, Research Square preprint, Aug 2026 (n=400) · RIMS Ranchi, Cureus, Sep 2026 (n=400)")

# 3. SOLUTION: what Saathi does, in six real frames
set_title(solution, "SOLUTION: SAATHI, A GUIDE ROBOT THAT READS THE CROWD")
clear_body(solution)
text(solution, 0.6, 2.3, 18.8, 0.5, [dict(runs=[("Say “Mujhe X-ray karwana hai”. ", True, INK), ("Saathi walks you there at your pace, talks in Hindi, explains every move, and takes the lift when your department is upstairs. All frames below are from our Webots runs.", False, INK)], size=16)])
frames = [(IMG["blackbox"], "Sees every person with an ID and distance", "YOLO11 + depth camera + 360° LiDAR"),
          (P("docs", "side_by_side.jpg"), "Never cuts through a conversation", "left: a normal planner · right: Saathi"),
          (P("docs", "obstacles.jpg"), "Sees what the map does not have", "wet-floor board, cardboard box: 0 hits"),
          (P("docs", "lift_frame.jpg"), "Takes the lift to the first floor", "doors close, cabin travels, doors open"),
          (P("docs", "fall.jpg"), "Spots a fall, alerts the nurse, stays", "VLM second opinion: resting or fallen?"),
          (P("docs", "arrive.jpg"), "Arrives, and says so in Hindi", "offline Whisper + phrasebook + Lekha voice")]
for i, (img, t, s) in enumerate(frames):
    x, y = 0.6 + (i % 3) * 6.32, 2.95 + (i // 3) * 3.5
    frame(solution, img, x, y, 6.1, 2.7, t, s)
card(solution, 0.6, 9.75, 18.8, 0.72, fill=TEAL, line=None)
for i, s in enumerate(["🗣 Hindi, fully offline", "📼 Black box answers “tum ruke kyun?”", "🧠 Robots share one memory of people", "📊 Tested on 200 seeded crowds"]):
    text(solution, 0.8 + i * 4.7, 9.83, 4.6, 0.56, [(s, 14, True, WHITE)], anchor=MSO_ANCHOR.MIDDLE)

# 4. HOW IT WORKS: architecture + one trip through it
set_title(arch, "HOW IT WORKS: TWO BRAINS AND A GUARD NEITHER CAN OVERRIDE")
clear_body(arch)
row1, row2, h = 2.35, 4.45, 1.5
node(arch, 0.6, row1, 3.3, h, "SENSORS", "Stereo RGB · depth camera · 360° LiDAR · IMU")
node(arch, 4.5, row1, 5.6, h, "REFLEX BRAIN · 30 Hz", "YOLO11 + depth + LiDAR → people with speed · A* on a crowd costmap, 2 s ahead", fill=MINT)
node(arch, 10.7, row1, 3.6, h, "SAFETY GUARD", "On LiDAR, below the AI: stop under 0.6 m. Fist = stop.", fill=RGBColor(0xFB, 0xEC, 0xE2), title_color=SAFFRON)
node(arch, 14.9, row1, 4.5, h, "MOTORS", "Body velocity → 4 mecanum wheel speeds (physics)")
node(arch, 0.6, row2, 3.3, h, "YOU", "Hindi voice · typing · hand gesture")
node(arch, 4.5, row2, 5.6, h, "THINKING BRAIN", "Whisper (Hindi) + phrasebook · Qwen3.5-2B VLM describes scenes · Lekha voice", fill=MINT)
node(arch, 10.7, row2, 3.6, h, "RADIO · SHARED MEMORY", "Robots talk to each other: who they saw, where they are, who searches where. Never a face.")
node(arch, 14.9, row2, 4.5, h, "BLACK BOX", "Every decision + camera frame + reason. Replayable.")
for x1, x2 in ((3.9, 4.5), (10.1, 10.7), (14.3, 14.9)):
    arrow(arch, x1, row1 + h / 2, x2, row1 + h / 2)
arrow(arch, 3.9, row2 + h / 2, 4.5, row2 + h / 2)
arrow(arch, 10.1, row2 + h / 2, 10.7, row2 + h / 2)
arrow(arch, 6.6, row2, 6.6, row1 + h)
arrow(arch, 8.0, row1 + h, 8.0, row2)
arrow(arch, 12.5, row1 + h, 12.5, row2)
arrow(arch, 14.3, row2 + h / 2, 14.9, row2 + h / 2)
text(arch, 6.68, row1 + h + 0.08, 1.3, 0.4, [("goals", 12, False, MUTED)])
text(arch, 8.08, row1 + h + 0.08, 1.3, 0.4, [("events", 12, False, MUTED)])
text(arch, 0.6, 6.3, 18.8, 0.4, [("ONE REQUEST, END TO END: “BLOOD BANK KAHAN HAI?”", H, True, TEAL)])
steps = [("Hear", "Whisper → “Blood Bank”, first floor"), ("Plan", "A* to the lift lobby on the crowd costmap"), ("Drive", "slow, wait, side-step; guard watches 0.6 m"),
         ("Lift", "call it, ride up, switch floor map"), ("Walk", "to Blood Bank, around people and groups"), ("Say", "“Aa gaye”; every step in the black box")]
for i, (a, b) in enumerate(steps):
    x = 0.6 + i * 3.15
    card(arch, x, 6.8, 2.95, 1.35, fill=CARD)
    text(arch, x + 0.12, 6.88, 2.75, 1.25, [(f"{i + 1}  {a}", 15, True, TEAL), para(b, 12.5, space=1)])
    if i < 5:
        arrow(arch, x + 2.95, 7.47, x + 3.15, 7.47, width=1.5)
text(arch, 0.6, 8.4, 18.8, 0.4, [("STACK (ALL ON AN 8 GB M1 LAPTOP, NO CLOUD)", H, True, TEAL)])
for i, s in enumerate(["Webots physics", "Python 3.10", "YOLO11", "YOLOE open-vocab", "ByteTrack", "CLIP", "Whisper v3-turbo (MLX)", "Qwen3.5-2B VLM (MLX)", "A* + social costs", "MediaPipe Hands", "macOS Lekha TTS"]):
    pill(arch, 0.6 + (i % 6) * 3.15, 8.85 + (i // 6) * 0.55, 2.95, s, size=12)
for i, (num, cap) in enumerate([(f"{v['localization_error_median']:.2f} m", "median error placing people"), ("9.5 ms", "YOLO11n per frame"), ("~5 ms", "a plan, replanned twice a second"),
                                (f"{FEAT['fall_alert']['t'] - FALL_T['t']:.1f} s", "fall classified after it happened")]):
    text(arch, 0.6 + i * 4.7, 10.0, 4.5, 0.6, [dict(runs=[(num + "  ", True, SAFFRON), (cap, False, MUTED)], size=13)])

# 5. PROTOTYPE: the whole hospital in one run, on its own camera
t_wet, t_ph, t_fall, t_lift, t_f2, t_bb, t_lab = ev("not on my map"), ev("Arrived at Pharmacy"), ev("Staying with the patient"), ev("Lift mein hoon"), ev("Pehli manzil"), ev("Arrived at Blood Bank"), ev("Arrived at Lab")
set_title(proto, f"PROTOTYPE: ONE RUN, TWO FLOORS, A LIFT, A FALL · {TOUR['time']:.0f} s ON ITS OWN CAMERA")
clear_body(proto)
strip = [(tour_frame("cctv", t_wet), f"{t_wet:.0f} s", "Wet-floor board not on the map: goes around"), (tour_frame("cctv", t_ph), f"{t_ph:.0f} s", "Arrives at Pharmacy, beside the queue"),
         (tour_frame("cctv", t_fall), f"{t_fall:.0f} s", "A man falls: alert sent, Saathi stays"), (tour_frame("chase", t_lift - 2), f"{t_lift:.0f} s", "Into the lift; doors close, cabin rises"),
         (tour_frame("cctv2", t_f2 + 8), f"{t_f2:.0f} s", "First floor: Nurse Station, Wards, Blood Bank"), (tour_frame("cctv", t_lab), f"{t_lab:.0f} s", "Back down by lift: arrives at Lab")]
for i, (img, when, what) in enumerate(strip):
    x = 0.6 + i * 3.15
    picture(proto, img, x, 2.35, 2.95, 1.66)
    pill(proto, x, 2.4, 0.9, when, fill=TEAL, color=WHITE, size=12)
    text(proto, x, 4.05, 2.95, 0.8, [(what, 12.5, False, INK)])
    if i < 5:
        arrow(proto, x + 2.95, 3.18, x + 3.15, 3.18, color=TEAL, width=1.5)
picture(proto, IMG["dash"], 0.6, 5.0, 7.7, 4.33, fit="contain")
caption(proto, 0.6, 9.4, 7.7, "What Saathi works from: its camera with YOLO boxes and distances, depth, floor map, 360° LiDAR, its thinking log", 12)
frame(proto, P("docs", "lift_frame.jpg"), 8.55, 5.0, 4.5, 2.1, "NEW · the lift", "doors, cabin, call button; the map switches floors")
frame(proto, P("docs", "floor2_frame.jpg"), 8.55, 7.9, 4.5, 2.1, "NEW · the first floor", "Blood Bank, ICU, OT, Wards, nurse station")
card(proto, 13.3, 5.0, 6.1, 5.45, fill=MINT, line=None)
text(proto, 13.5, 5.1, 5.7, 0.4, [("THIS RUN, MEASURED", 15, True, TEAL)])
for i, (num, cap) in enumerate([(f"{TOUR['near_misses']}", "near-misses"), (f"{TOUR['conversation_cuts']}", "conversations cut"), (f"{len(TOUR['unmapped_hits'])}", "unmapped obstacles hit"),
                                ("4", "departments on 2 floors"), ("1", "fall handled on the way"), (f"{TOUR['time']:.0f} s", "entrance → Lab, all by itself")]):
    text(proto, 13.5 + (i % 2) * 2.9, 5.55 + (i // 2) * 1.1, 2.8, 1.0, [(num, 30, True, TEAL), para(cap, 12.5, space=0)])
text(proto, 13.5, 8.72, 5.7, 0.4, [("NEW IN ROUND 2", 13, True, SAFFRON)])
for i, s_ in enumerate(["Lift + first floor", "9 departments by voice", "Tour of departments", "Fall: VLM second opinion", "2 robots talk + share memory", "Open source on GitHub"]):
    pill(proto, 13.5 + (i % 2) * 2.9, 9.1 + (i // 2) * 0.44, 2.8, s_, fill=WHITE, size=11.5)

# 6. RESULTS: 200 seeded crowds
set_title(results, f"RESULTS: {b0['trips']} SEEDED CROWDS, SAATHI vs A NORMAL ROBOT")
clear_body(results)
picture(results, IMG["chart"], 0.6, 2.3, 11.6, 5.2, fit="contain", border=False)
for i, (num, cap) in enumerate([(f"{NEAR_DROP}% fewer", f"near-misses: {b0['near_misses_per_trip']:.2f} → {s0['near_misses_per_trip']:.2f} per trip"),
                                ("0 of " + str(s0["trips"]), f"trips cut through a conversation (normal robot: {round(100 * b0['trips_cutting_a_conversation'])}%)"),
                                (f"{s0['arrived']}/{s0['trips']}", f"trips reached the goal (normal robot: {b0['arrived']}/{b0['trips']})"),
                                (f"+{s0['median_trip_time'] - b0['median_trip_time']:.0f} s", f"the price: median trip {b0['median_trip_time']:.0f} s → {s0['median_trip_time']:.0f} s")]):
    x = 0.6 + i * 2.95
    card(results, x, 7.7, 2.8, 1.85, fill=MINT if i < 3 else CARD, line=None if i < 3 else LINE)
    text(results, x + 0.15, 7.78, 2.55, 1.75, [(num, 26, True, TEAL if i < 3 else SAFFRON), para(cap, 12, space=2)])
caption(results, 0.6, 9.65, 11.6, "Each seed: an OPD crowd (8–12 walkers, two talking pairs, a pharmacy queue) and a trip from the entrance to a random department. Normal robot = same A* planner, people as static obstacles, fixed speed, same 0.6 m stop. Deterministic: tools/bench.py 200.", 12)
for y, img, lab, col in ((2.3, "side_base", "NORMAL ROBOT: cuts through the conversation", MUTED), (6.0, "side_saathi", "SAATHI: goes around it", TEAL)):
    card(results, 12.6, y, 6.8, 0.45, fill=col, line=None, radius=0.15)
    text(results, 12.75, y + 0.03, 6.5, 0.4, [(lab, 14, True, WHITE)], anchor=MSO_ANCHOR.MIDDLE)
    picture(results, IMG[img], 12.6, y + 0.55, 6.8, 2.95)
rows_ab = [("Same crowd, in Webots", "Normal", "Saathi", "Saathi, camera only")] + [
    (lab, *[f(AB[k]) for k in ("baseline", "saathi", "vision")]) for lab, f in (
        ("Near-misses", lambda s: str(s["near_misses"])), ("Cut a conversation", lambda s: "yes" if s["conversation_cuts"] else "no"), ("Time to Radiology", lambda s: f"{s['time']:.0f} s"))]
tb = results.shapes.add_table(len(rows_ab), 4, Inches(12.6), Inches(9.6), Inches(6.8), Inches(0.3 * len(rows_ab))).table
for c, wd in enumerate((2.6, 1.2, 1.2, 1.8)):
    tb.columns[c].width = Inches(wd)
for r, row in enumerate(rows_ab):
    for c, val in enumerate(row):
        cell = tb.cell(r, c)
        cell.text = val
        cell.margin_left = cell.margin_right = Inches(0.08)
        cell.margin_top = cell.margin_bottom = Inches(0.02)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if r == 0 else (CARD if r % 2 else WHITE)
        f = cell.text_frame.paragraphs[0].runs[0].font
        f.name, f.size, f.bold, f.color.rgb = FONT, Pt(11), r == 0 or c == 0, WHITE if r == 0 else INK

# 7. SAATHI PARIVAAR: one shared memory, a lost child found where he is now
set_title(parivaar, "SAATHI PARIVAAR: ROBOTS SHARE ONE MEMORY OF PEOPLE (BUILT, MEASURED)")
clear_body(parivaar)
picture(parivaar, P("docs", "parivaar_frame.jpg"), 0.6, 2.3, 9.8, 5.5)
caption(parivaar, 0.6, 7.85, 9.8, "Two Saathis, one run: papa reports “laal t-shirt” at the help desk. The robots talk over radio (group chat, right): Saathi-1 stays with him, Saathi-2 goes where the memory says the boy is now (orange glow).", 12)
for i, (head, body) in enumerate([("REMEMBER", "who each robot saw: where, when, height, clothes. No face."), ("ASK", "papa's words search every robot's memory"),
                                  ("WHERE NOW?", "from his last motion; places already checked are ruled out"), ("SEARCH AS A TEAM", "robots talk over radio, split the places; one stays with papa")]):
    x = 0.6 + i * 2.45
    card(parivaar, x, 8.5, 2.3, 1.9)
    text(parivaar, x + 0.12, 8.58, 2.1, 1.8, [(f"{i + 1}  {head}", 13, True, TEAL), para(body, 12, space=3)])
picture(parivaar, P("out", "media", "parivaar", "clip_child.jpg"), 10.7, 2.3, 8.7, 2.5, fit="contain")
caption(parivaar, 10.7, 4.82, 8.7, f"Search by description on Saathi's own camera: “small child in a red shirt”, top 8 of {CS['people']} people seen are all him. 24 of 24 right.", 12)
picture(parivaar, P("out", "bench_lost", "chart.png"), 10.7, 5.5, 8.7, 3.0, fit="contain", border=False)
w1, s1, w3 = LOSTB["where_now/1"], LOSTB["sweep/1"], LOSTB["where_now/3"]
for i, (num, cap) in enumerate([(f"{s1['median_time'] / w1['median_time']:.1f}×", f"faster with memory, one robot ({s1['median_time']:.0f} s → {w1['median_time']:.0f} s median)"),
                                (f"{round(100 * w3['found_in_3_min'])}%", "found within 3 min with three robots")]):
    text(parivaar, 10.7 + i * 4.4, 8.55, 4.2, 1.0, [(num, 28, True, TEAL), para(cap, 12, space=0)])
text(parivaar, 10.7, 9.6, 8.7, 0.9, [para("200 lost-child seeds, 3 strategies, 1–3 robots (tools/bench_lost.py). Honest: with a team, team size matters more than strategy.", 12, MUTED, space=0),
                                     para("Privacy: clothes, not faces · record deleted after the reunion · wiped daily", 12, INK, True, 3)])

# 8. PS-01, EVERY LINE WITH PROOF + what is real
set_title(proof, "PS-01 CHECKLIST WITH PROOF · WHAT IS REAL AND WHAT IS SIMPLIFIED")
clear_body(proof)
crows = [("PS-01 asks for", "What Saathi does", "Proof from our runs"),
         ("Understand surroundings with AI vision", "YOLO11 + depth + 360° LiDAR; people on a floor map", f"People placed within {v['localization_error_median']:.2f} m (median)"),
         ("Identify relevant people and objects", "Tracks people; YOLOE names objects by text", "“cardboard box”, “yellow caution sign” named on sight"),
         ("Navigate autonomously to an objective", "A* on a crowd costmap; goals by name, by sight, on either floor", f"Dustbin found by camera in {FIND['time']:.0f} s · Blood Bank via lift"),
         ("Detect and avoid obstacles", "Depth camera finds what the map lacks", f"Map-only robot hit {len(OB['maponly']['unmapped_hits'])}; Saathi {len(OB['vision']['unmapped_hits'])}"),
         ("Real-time decision making", "30 Hz reflex loop, replans twice a second", f"{s0['trips']} crowds: {NEAR_DROP}% fewer near-misses"),
         ("Object detection, image classification", "YOLOE posture: “person lying on the floor”", f"Fall classified {FEAT['fall_alert']['t'] - FALL_T['t']:.1f} s after it happened"),
         ("Scene understanding", "Conversations and queues from tracks; signs read", f"0 of {s0['trips']} conversations cut"),
         ("Vision-language models", "Qwen3.5-2B (Apple MLX) describes the scene", "Its description goes with the nurse alert"),
         ("Motor control", "Physics mecanum base, speed per wheel", f"Motion within {100 * CAL_ERR:.0f}% of the command"),
         ("Real or simulated environment", "Two-floor Webots hospital, Hindi + English signs", "Deterministic: same seed, same numbers")]
ct = proof.shapes.add_table(len(crows), 3, Inches(0.6), Inches(2.3), Inches(12.6), Inches(0.6 * len(crows))).table
for c, wd in enumerate((4.0, 4.5, 4.1)):
    ct.columns[c].width = Inches(wd)
for r, row in enumerate(crows):
    for c, val in enumerate(row):
        cell = ct.cell(r, c)
        cell.text = ("✓  " if r and c == 0 else "") + val
        cell.margin_left = cell.margin_right = Inches(0.1)
        cell.margin_top = cell.margin_bottom = Inches(0.04)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if r == 0 else (CARD if r % 2 else WHITE)
        f = cell.text_frame.paragraphs[0].runs[0].font
        f.name, f.size, f.bold = FONT, Pt(12.5), r == 0 or c == 0
        f.color.rgb = WHITE if r == 0 else (TEAL if c == 0 else INK)
card(proof, 13.5, 2.3, 5.9, 3.6, fill=MINT, line=None)
text(proof, 13.7, 2.4, 5.5, 3.4, [("REAL", 15, True, TEAL)] + bullets(["The 3D render; camera, depth and LiDAR data", "YOLO11 / YOLOE / CLIP on the rendered frames", "The planner, the memory, the voice agent",
                                                                        "Physics wheels driven by speed commands; the lift cabin"], 12.5, gap=3))
card(proof, 13.5, 6.05, 5.9, 2.4, fill=CARD)
text(proof, 13.7, 6.15, 5.5, 2.2, [("SIMPLIFIED (WE SAY SO)", 15, True, SAFFRON)] + bullets(["People walk fixed paths and do not react to the robot", "Robot position from the simulator (LiDAR SLAM on the real rover)",
                                                                                            "The nurse is simulated (takes over after 6 s)"], 12.5, gap=3))
picture(proof, IMG["closeup"], 13.5, 8.6, 2.6, 1.85)
text(proof, 16.3, 8.6, 3.1, 1.9, [("SAME CODE, REAL ROVER", 13, True, TEAL), para("The brain talks to sensors through one small interface: Webots today, Jetson Orin Nano on our rover next.", 12, space=2)])

# 9. PROGRESS & ROADMAP
set_title(progress, "PROGRESS: WHAT WAS BUILT WHEN, AND WHAT COMES NEXT")
clear_body(progress)
steps = [("12 OCT", "Webots OPD hall, physics rover, crowd-aware planner, camera + LiDAR + depth, fall alert, VLM, black box, 200-crowd A/B"),
         ("14 OCT", "Shared memory of people, lost-child search, 200-seed benchmark, offline Hindi voice"),
         ("20 OCT", "Whole hospital: lift, first floor (Blood Bank, ICU, OT, Wards), tour of departments, GitHub public"),
         ("24–27 OCT", "Demo video, LinkedIn pitch, Instagram reel, Round 2 submission"),
         ("20–21 NOV", "Manali finale: 3 robots live and fully offline on a laptop, held-out 200-seed test"),
         ("2027", "Real rover (Jetson Orin Nano, face screen, mic, e-stop); OPD pilot with consent and face blurring")]
arrow(progress, 0.9, 2.85, 19.1, 2.85, color=LINE, width=3)
for i, (when, what) in enumerate(steps):
    x = 0.6 + i * 3.15
    dot = progress.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.15), Inches(2.65), Inches(0.4), Inches(0.4))
    dot.fill.solid(); dot.fill.fore_color.rgb = SAFFRON if i < 3 else TEAL; dot.line.fill.background()
    text(progress, x, 3.2, 2.95, 2.6, [(when + ("  ✓" if i < 3 else ""), 15, True, SAFFRON if i < 3 else TEAL), para(what, 12.5, space=4)])
picture(progress, IMG["rover"], 0.6, 5.0, 5.4, 5.0, fit="contain")
caption(progress, 0.6, 10.05, 5.4, "Our rover design: the body Saathi's brain will drive", 12)
picture(progress, P("docs", "floor2_frame.jpg"), 6.3, 5.0, 6.7, 3.77)
caption(progress, 6.3, 8.85, 6.7, "The first floor, built this week: Blood Bank, Nurse Station, Wards, ICU, OT, stairs, lift", 12)
picture(progress, P("docs", "lift_frame.jpg"), 6.3, 9.3, 2.0, 1.12)
picture(progress, P("docs", "parivaar_frame.jpg"), 8.45, 9.3, 2.0, 1.12)
picture(progress, P("docs", "fall.jpg"), 10.6, 9.3, 2.0, 1.12)
card(progress, 13.2, 5.0, 6.2, 5.45, fill=MINT, line=None)
text(progress, 13.4, 5.1, 5.8, 5.25, [("OPEN SOURCE, REPRODUCIBLE", 15, True, TEAL), para(GITHUB, 16, INK, True, 4),
     para("README: GIFs of every run, every number with the script that makes it", 12.5, space=4)] + bullets([
     "tools/demo.sh: the whole-hospital run, live", "tools/bench.py 200: the A/B numbers", "tools/bench_lost.py 200: the lost-child numbers", "tools/voice.py: talk to it in Hindi"], 12.5, gap=3) +
     [para("Where it goes: 816 medical colleges, 714 district hospitals; Robot-as-a-Service about ₹15,000 a month per robot", 12, MUTED, space=8)])

# 10. THANK YOU
text(thanks, 15.1, 4.95, 4.3, 2.8, [("SAATHI", 34, True, TEAL), para("Raasta bhi, saath bhi.", 20, INK, True, 2),
     para("The way, and the company.", 15, MUTED, space=2), para(GITHUB, 13, TEAL, True, 10), para("Team Glitch · " + TEAM[0][0], 13, MUTED, space=2)])

out = P("ppt", "Saathi_Round2.pptx")
prs.save(out)
print("wrote", out, "slides:", len(prs.slides))
