"""Round 1 deck (17 slides): fills the official template -> ppt/Saathi_HackInHills26.pptx. Render: tools/render_ppt.sh <pptx> [--pdf]"""
from pptkit import *

prs = Presentation(P("ppt", "template.pptx"))
for _ in range(9):  # nine more EXTRA slides in the template's EXTRA style
    duplicate(prs, list(prs.slides)[6])
lst = prs.slides._sldIdLst
thanks_id = lst[7]
lst.remove(thanks_id)
lst.append(thanks_id)  # Thank you stays last
cover, problem, solution, arch, market, future, parivaar, checklist, extra1, results, scene_ab, pixels, obst, fall_s, bbox, extra2, thanks = list(prs.slides)

# 1. TEAM (cover): the template's TEAM block, plus what the project is.
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
        ps[2]._p.getparent().remove(ps[2]._p)  # the template's ROLES line: roles sit under each name below
text(cover, 3.43, 7.5, 6.9, 3.3, [p for i, (name, role) in enumerate(TEAM)
     for p in (para(name, 20, INK, True, space=0 if i == 0 else 12), para(role, 15, MUTED, space=1))])
text(cover, 10.6, 4.75, 8.8, 1.0, [("SAATHI", 54, True, TEAL)])
text(cover, 10.6, 5.75, 8.8, 1.0, [("A robot guide that reads Indian hospital crowds", 22, True, INK),
                                    para("PS-01 · Vision-Based Autonomous Robot · shown in a Webots hospital simulation", 15, MUTED, space=6)])
picture(cover, IMG["face"], 10.6, 7.0, 7.1, 4.0)

# 2. PROBLEM STATEMENT & THEME
set_title(problem, "PROBLEM STATEMENT & THEME")
clear_body(problem)
text(problem, 0.6, 2.4, 12.0, 1.2, [("PROBLEM", H, True, TEAL), para("Big Indian OPDs are packed, confusing and signed in English. "
     "First-time, elderly and low-literacy patients get lost, and staff leave their work to show them the way.")])
for i, (num, cap) in enumerate([("14–15k", "OPD patients a day at AIIMS Delhi"),
                                ("69.6%", "of first-time OPD visitors needed a person to find their way (GMC Bhopal)"),
                                ("3 h+", "total OPD wait for 58% of 400 patients (RIMS Ranchi, 2026)")]):
    x = 0.6 + i * 4.07
    card(problem, x, 3.7, 3.87, 2.05)
    text(problem, x + 0.2, 3.8, 3.5, 1.9, [(num, 44, True, SAFFRON), para(cap, SMALL, space=2)])
text(problem, 0.6, 5.95, 12.0, 1.6, [("IMPACT", H, True, TEAL), para("Hours lost and appointments missed. Help desks and nurses pulled away from care. "
     "A fall in a packed hall is noticed late. And today's robot planners either freeze in dense crowds or cut straight through people.")])
text(problem, 0.6, 7.75, 12.0, 2.7, [("THEME ALIGNMENT · PS-01 VISION-BASED AUTONOMOUS ROBOT", H, True, TEAL)] + bullets([
    "AI vision finds and tracks people and objects (YOLO11 + depth camera)",
    "Drives itself to a goal (any department) while avoiding obstacles and people",
    "Decides in real time: slow down, give way, side-step, stop",
    "Shown in a realistic simulated hospital (Webots), which PS-01 allows"], 18))
picture(problem, IMG["hall"], 13.0, 2.45, 6.4, 4.4)
text(problem, 13.0, 6.92, 6.4, 0.8, [("Our simulated OPD hall in Webots: Hindi + English signs, token display, pharmacy queue", CAP, False, MUTED)])
card(problem, 13.0, 7.85, 6.4, 2.55, fill=MINT, line=None)
text(problem, 13.25, 7.98, 5.9, 2.35, [("THE GAP", H, True, TEAL), para("Our 2024–26 search found no wayfinding robot working in an Indian OPD. "
     "Guide robots already work in airports abroad (SPENCER at Amsterdam Schiphol); Indian OPD crowds are denser.", 17)])
footer(problem, "Sources: AIIMS OPD load: UNI and Free Press Journal, Sep 2026 · GMC Bhopal: IJCMPH 2026 (336 first-time visitors) · RIMS Ranchi: Cureus, 20 Sep 2026")

# 3. SOLUTION
set_title(solution, "SOLUTION")
clear_body(solution)
text(solution, 0.6, 2.35, 12.1, 1.3, [dict(runs=[("Saathi is an autonomous guide robot for hospital OPDs. ", True, INK),
     ("Say “Mujhe X-ray karwana hai” and it walks you to Radiology at your pace, reading the crowd with its camera, and it can explain every move.", False, INK)], size=20)])
text(solution, 0.6, 3.65, 12.0, 0.4, [("KEY FEATURES", H, True, TEAL)])
feats = [("Talks like a person", "Hindi, Hinglish or English. Asks when unsure: “Kaunsa red shirt?”"),
         ("Reads the crowd", "Predicts where each person will be in 2 s. Never cuts through a conversation; wheelchairs go first."),
         ("Side-steps, keeps left", "Mecanum wheels slide it aside instead of stopping dead in a busy corridor."),
         ("Finds things", "“Dustbin dhoondo”: open-vocabulary detection finds it by name, and Saathi drives there."),
         ("Watches out", "Spots a fall, alerts the nurse station and stays with the patient."),
         ("Safe by design", "Hard stop under 0.6 m, and a fist gesture stops it. The AI cannot override either.")]
for i, (t, b) in enumerate(feats):
    x, y = 0.6 + (i % 3) * 4.07, 4.1 + (i // 3) * 2.02
    card(solution, x, y, 3.87, 1.87)
    text(solution, x + 0.18, y + 0.12, 3.5, 1.65, [(t, 17, True, TEAL), para(b, 15.5)])
card(solution, 0.6, 8.3, 12.07, 2.15, fill=TEAL, line=None)
text(solution, 0.85, 8.42, 11.6, 1.95, [("UNIQUE VALUE: EXPLAINABLE, TESTED, BUILT FOR INDIAN CROWDS", 17, True, MINT),
     para("A black box records every decision with its camera frame and reason, so “Tum ruke kyun?” gets an answer with proof. "
          f"In {b0['trips']} seeded crowds Saathi had {NEAR_DROP}% fewer near-misses than a normal robot and never cut through a conversation.", 17, WHITE),
     para("Next: Saathi Parivaar. Robots that share one memory of people find a lost child where he is now, not where he was seen.", 17, MINT, True, 6)])
picture(solution, IMG["cam"], 13.0, 2.45, 6.4, 3.6)
text(solution, 13.0, 6.1, 6.4, 0.5, [("What Saathi sees: YOLO11s boxes, track IDs and distance from its depth camera", CAP, False, MUTED)])
picture(solution, IMG["crowd"], 13.0, 6.75, 6.4, 3.4)
text(solution, 13.0, 10.2, 6.4, 0.4, [("Moving through the OPD crowd (Webots simulation)", CAP, False, MUTED)])

# 4. ARCHITECTURE: two brains and a guard, then stack / flow / APIs.
set_title(arch, "ARCHITECTURE")
clear_body(arch)
row1, row2, h = 2.4, 4.75, 1.65
node(arch, 0.6, row1, 3.3, h, "SENSORS", "Stereo RGB camera · depth camera · 360° LiDAR · IMU · ultrasonic")
node(arch, 4.5, row1, 5.6, h, "REFLEX BRAIN · 30 Hz", "YOLO11 + depth + LiDAR → people with speed; depth finds what the map lacks · A* on a crowd costmap", fill=MINT)
node(arch, 10.7, row1, 3.6, h, "SAFETY GUARD", "Runs on LiDAR, not the AI: stops under 0.6 m. A fist gesture stops it.", fill=RGBColor(0xFB, 0xEC, 0xE2), title_color=SAFFRON)
node(arch, 14.9, row1, 4.5, h, "MOTOR CONTROL", "Body velocity → four mecanum wheel speeds (inverse kinematics)")
node(arch, 0.6, row2, 3.3, h, "YOU", "Voice (Hindi speech-to-text) · typing · hand gesture")
node(arch, 4.5, row2, 5.6, h, "THINKING BRAIN · LLM + VLM", "LLM talks Hinglish and plans; a small VLM (Qwen3.5-2B) describes scenes and reads signs", fill=MINT)
node(arch, 10.7, row2, 3.6, h, "BLACK BOX", "Every decision: camera frame + reason. Answers “why?”")
node(arch, 14.9, row2, 4.5, h, "RUNS ON", "Today: an 8 GB M1 MacBook Air. Robot: Jetson Orin Nano (planned)")
for x1, x2 in ((3.9, 4.5), (10.1, 10.7), (14.3, 14.9)):
    arrow(arch, x1, row1 + h / 2, x2, row1 + h / 2)
arrow(arch, 3.9, row2 + h / 2, 4.5, row2 + h / 2)
arrow(arch, 10.7, row2 + h / 2, 10.1, row2 + h / 2)
arrow(arch, 6.6, row2, 6.6, row1 + h)
arrow(arch, 8.0, row1 + h, 8.0, row2)
text(arch, 6.68, row1 + h + 0.12, 1.3, 0.4, [("goals", 13, False, MUTED)])
text(arch, 8.08, row1 + h + 0.12, 1.3, 0.4, [("events", 13, False, MUTED)])
arrow(arch, 10.1, row1 + h - 0.15, 11.4, row2)
cols = [("TECH STACK", ["Webots R2025a (physics, mecanum wheels) · Python 3.10", "YOLO11 + YOLOE open-vocabulary · camera + LiDAR tracker",
                        "Qwen3.5-2B vision-language model on Apple MLX", "LLM agent: Claude API, small local model offline",
                        "whisper.cpp (Hindi speech) · Hindi text-to-speech", "MediaPipe Hands for the gesture stop"]),
        ("DATA FLOW", ["Camera + depth → people with ID and distance", "Crowd map with each person's next 2 seconds",
                       "Planner picks path and speed (groups, wheelchairs, keep-left)", "Safety guard checks, then the wheels move",
                       "Every decision → black box → the agent can explain it"]),
        ("APIS + MEASURED", ["API: Claude for conversation only; offline phrasebook without network",
                             f"People placed within {AB['vision']['localization_error_median']:.2f} m (median) by camera + LiDAR",
                             "Planner: about 5 ms a plan, replans twice a second", "YOLO11n 9.5 ms a frame on our 8 GB M1 laptop",
                             f"Fall classified {FEAT['fall_alert']['t'] - FALL_T['t']:.1f} s after it happened · VLM about 3 s an answer"])]
for i, (t, items) in enumerate(cols):
    text(arch, 0.6 + i * 6.32, 6.75, 6.1, 3.9, [(t, H, True, TEAL)] + bullets(items, SMALL, gap=4))

# 5. MARKET RESEARCH / ANALYSIS
set_title(market, "MARKET RESEARCH/ANALYSIS")
clear_body(market)
card(market, 0.6, 2.4, 9.3, 3.8)
text(market, 0.85, 2.52, 8.8, 3.6, [("TARGET USERS", H, True, TEAL)] + bullets([
    "Patients: elderly, first-time, low-literacy and non-English-speaking visitors",
    "Hospitals: government medical colleges, district hospitals, AIIMS-type institutes, large private chains",
    "Staff: help desks and nurses answer fewer “X-ray kahan hai?” questions"], 17, gap=8))
card(market, 10.1, 2.4, 9.3, 3.8)
text(market, 10.35, 2.52, 8.8, 0.4, [("MARKET SIZE", H, True, TEAL)])
for i, (num, cap) in enumerate([("816", "medical colleges (2025–26)"), ("714", "district hospitals"), ("1,340", "sub-divisional hospitals")]):
    text(market, 10.35 + i * 2.95, 2.95, 2.85, 1.35, [(num, 40, True, SAFFRON), para(cap, 15, space=0)])
text(market, 10.35, 4.4, 8.8, 1.75, [dict(runs=[("India medical-robot market: ", True, INK), ("USD 191 M (2024) → 450 M (2029), MarketsandMarkets; "
     "USD 1.32 B (2024) → 8.12 B (2033) under IMARC's broader definition. Guide robots are a new slice of it.", False, INK)], size=SMALL)])
card(market, 0.6, 6.4, 9.3, 4.0)
text(market, 0.85, 6.52, 8.8, 3.8, [("POTENTIAL REVENUE MODEL", H, True, TEAL)] + bullets([
    "Robot-as-a-Service: about ₹15,000 a month per robot, with maintenance and updates",
    "Sale + annual maintenance contract for large hospitals",
    "Licence the Saathi brain to robot makers",
    "Crowd-flow analytics for hospital admins (busy hours, where patients get lost)",
    "Pilots funded through CSR and the National Health Mission"], 17, gap=6))
card(market, 10.1, 6.4, 9.3, 4.0)
text(market, 10.35, 6.52, 8.8, 3.8, [("EXPECTED GROWTH", H, True, TEAL)] + bullets([
    "Pilot in one OPD → state rollout (NHM / CSR) → private chains",
    "Beyond hospitals: railway stations, airports, pilgrimage sites",
    "The medical-robot market is forecast to grow 18.7–20.6% a year (reports above)",
    "Every robot's black box adds data that makes the next one smarter"], 17, gap=6))
footer(market, "Sources: Health Dynamics of India 2022-23 (MoHFW, data as of 31 Mar 2023) · NMC approvals 2025-26 (The Tribune) · MarketsandMarkets and IMARC, India medical robots market")

# 6. FUTURE SCOPE: a timeline.
set_title(future, "FUTURE SCOPE")
clear_body(future)
steps = [("BUILT · OCT 2026", "Physics rover in a Webots OPD; crowd-aware planner; camera + LiDAR + depth; fall alert; VLM; A/B on 200 crowds"),
         ("BY 24 OCT 2026", "Saathi Parivaar with 2 robots, Hindi voice agent, walks at the patient's pace, gesture stop, demo video"),
         ("20–21 NOV 2026", "Manali finale: Saathi Parivaar with 3 robots and its 200-seed test, live and fully offline on a laptop"),
         ("2027", "Build the real rover: Jetson Orin Nano, team design, face screen, mic, speaker, e-stop. Pilot in one OPD with consent and face blurring"),
         ("NEXT", "More Indian languages (Bhashini, IndicWhisper), token/queue integration, robot fleets, stations and airports")]
arrow(future, 0.9, 3.05, 19.1, 3.05, color=LINE, width=3)
for i, (when, what) in enumerate(steps):
    x = 0.6 + i * 3.8
    dot = future.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.15), Inches(2.85), Inches(0.4), Inches(0.4))
    dot.fill.solid(); dot.fill.fore_color.rgb = TEAL if i else SAFFRON; dot.line.fill.background()
    text(future, x, 3.5, 3.6, 3.3, [(when, 17, True, SAFFRON if i == 0 else TEAL), para(what, 17, space=5)])
card(future, 0.6, 7.05, 18.8, 3.4, fill=CARD)
text(future, 0.9, 7.2, 8.8, 3.1, [("ALSO ON THE ROADMAP", H, True, TEAL)] + bullets([
    "Staff mobile app: send Saathi, see where it is, read its black box",
    "Fine-tune YOLO on Indian hospital scenes: wheelchairs, stretchers, crowds at counters",
    "Crowd heatmaps that tell admins where patients get lost"], 17, gap=6))
text(future, 10.2, 7.2, 8.9, 3.1, [("WHY IT SCALES", H, True, TEAL)] + bullets([
    "The brain is software: the same code runs in Webots and on the real robot",
    "Hindi first, then any Indian language with the same agent",
    "Hospitals, stations, airports and melas share one problem: crowds and lost people"], 17, gap=6))

# EXTRA (first): Saathi Parivaar, the team memory being built for the finale. Only the memory search is measured so far.
set_title(parivaar, "EXTRA · SAATHI PARIVAAR: EK YAAD, KAI AANKHEIN")
clear_body(parivaar)
CS = json.load(open(P("out", "media", "parivaar", "clip_search.json")))
text(parivaar, 0.6, 2.3, 11.6, 0.9, [dict(runs=[("A mother says “Mera beta kho gaya, laal t-shirt, 6 saal”. ", True, INK),
     ("Every Saathi in the hospital answers from one shared memory of people. Building now for the finale.", False, INK)], size=18)])
for i, (head, body) in enumerate([
        ("REMEMBER", "Each robot logs who it saw, where, when and which way they walked. Clothes only: no face is stored."),
        ("ASK", "Her words search every robot's memory: “Saathi-2 saw him 3 min ago at the pharmacy, walking to the corridor.” She taps his photo."),
        ("WHERE NOW?", "From his last motion Saathi works out where he can be now, and rules out places the robots checked and found empty."),
        ("SEARCH AS A TEAM", "Robots split the likely places; one stays with the mother. Once they meet, his record is deleted.")]):
    x = 0.6 + i * 2.95
    card(parivaar, x, 3.3, 2.75, 2.5)
    text(parivaar, x + 0.15, 3.4, 2.45, 2.35, [(f"{i + 1}  {head}", 16, True, TEAL), para(body, 14, space=4)])
picture(parivaar, P("out", "media", "parivaar", "clip_child.jpg"), 0.6, 6.05, 6.9, 2.23, fit="contain")
text(parivaar, 7.7, 6.0, 4.5, 2.6, [("TESTED ON SAATHI'S OWN CAMERA", 15, True, TEAL),
     para(f"“Small child in a red shirt”: the top 8 of {CS['people']} people seen are all him. "
          "A woman in green and a man in blue: 24 of 24 right. No look-alikes in this hall yet; the finale test adds them.", 14, space=3)])
card(parivaar, 12.6, 2.3, 6.8, 6.35)
text(parivaar, 12.85, 2.4, 6.35, 6.2, [("WHAT EXISTS → WHAT SAATHI ADDS", 16, True, TEAL)] +
     [p for old, new in [("NVIDIA ReMEmbR (2024): a robot recalls where it saw things", "Where a person is now, from a fresh sighting"),
                         ("HUMEMBR (IROS 2026): finds known people by face and routine", "Strangers, by clothes only; no face stored"),
                         ("Kumbh 2025 khoya-paya: face recognition on fixed cameras", "Robots also remember where they looked and saw no one"),
                         ("Lost-child robots (Japan, 2017): share spoken descriptions", "A team that splits the search; one robot always stays")]
      for p in (para(old, 13, MUTED, space=8), para("→ " + new, 15, INK, True, space=1))] +
     [para("WHY INDIA", 16, TEAL, True, space=14)] + bullets([
         "98% of 400 older patients at AIIMS Delhi's geriatric OPD usually come alone (preprint, 2026). The robots become the family they didn't bring.",
         "People rest on OPD floors. Memory tells a fall from rest, so nurses are not paged all day."], 14, gap=4))
card(parivaar, 0.6, 8.85, 18.8, 1.62, fill=MINT, line=None)
text(parivaar, 0.85, 8.92, 4.0, 0.4, [("ONE MEMORY, FIVE JOBS", 15, True, TEAL)])
for i, (name, what) in enumerate([("Khoya-Paya", "finds a lost child"), ("Bichhadne se pehle", "spots a child drifting from family"),
                                  ("Vaada", "fetches you before your token"), ("Doosri raay", "fell, or resting on the floor?"),
                                  ("Ek ruke, ek bulaye", "one stays, one fetches help")]):
    text(parivaar, 0.85 + i * 3.7, 9.3, 3.6, 0.7, [(name, 15, True, INK), para(what, 13, MUTED, space=0)])
text(parivaar, 0.85, 10.05, 18.3, 0.38, [("Privacy: clothes, not faces · deleted after a reunion · wiped daily · every search logged     "
     "Plan: 2 robots by 24 Oct · 3 robots and a 200-seed test (1 vs 3 robots, memory on/off) at the finale", 13, False, INK)])
footer(parivaar, "Prior work, to our knowledge (our search, Oct 2026): ReMEmbR arXiv 2409.13682 · HUMEMBR arXiv 2606.30404 · Kumbh 2025 Digital Khoya-Paya Kendra · "
       "Wada et al., IEICE CNR2017-12 · AIIMS geriatric OPD: Research Square preprint, Aug 2026")

# 7. EXTRA: the working simulation.
set_title(extra1, "EXTRA · WORKING PROTOTYPE (SIMULATION)")
clear_body(extra1)
picture(extra1, IMG["dash"], 0.6, 2.4, 12.4, 6.98, fit="contain")
text(extra1, 0.6, 9.45, 12.4, 0.9, [("One frame of our Webots run: chase camera, Saathi's camera with YOLO boxes and distances, depth camera, front CCTV, map, 360° LiDAR, and its thinking log.", CAP, False, MUTED)])
text(extra1, 13.4, 2.4, 6.0, 8.2, [("BUILT AND RUNNING", H, True, TEAL)] + bullets([
    "OPD hall with Hindi + English signs, token display, pharmacy queue, animated people",
    "Plans its own way to any department (A* on a crowd costmap)",
    "Sees people with camera + depth + 360° LiDAR, tracks them on the floor",
    "Slows, waits, slides sideways to let people pass, and thinks aloud",
    "Sees obstacles that are not on its map, finds things it is asked for, spots falls",
    "Black box: every decision saved with its camera frame",
    "Physics mecanum base driven by wheel speed commands"], SMALL, gap=5) +
    [para("BUILDING NEXT (BY 24 OCT)", H, TEAL, True, space=16)] + bullets([
    "Saathi Parivaar: 2 robots share one memory (Khoya-Paya demo)",
    "Hindi voice agent: speech in, Hindi voice out",
    "Walks at the patient's pace; eyes that look at the person",
    "Gesture stop from a webcam"], SMALL, gap=5) +
    [para("Demo video and GitHub repo: in the prototype round (18–24 Oct)", 15, MUTED, space=16)])

# 8. EXTRA: the A/B test over 200 seeded crowds.
set_title(results, f"EXTRA · RESULTS: {b0['trips']} CROWDS, TWO ROBOTS")
clear_body(results)
picture(results, IMG["chart"], 0.6, 2.3, 18.8, 5.35, fit="contain", border=False)
for i, (num, cap) in enumerate([(f"{NEAR_DROP}% fewer", f"near-misses: {b0['near_misses_per_trip']:.2f} → {s0['near_misses_per_trip']:.2f} per trip"),
                                ("0 of " + str(s0["trips"]), f"trips cut through a conversation (normal robot: {round(100 * b0['trips_cutting_a_conversation'])}%)"),
                                (f"{s0['arrived']}/{s0['trips']}", f"trips reached the goal (normal robot: {b0['arrived']}/{b0['trips']})"),
                                (f"+{s0['median_trip_time'] - b0['median_trip_time']:.0f} s", f"the price: median trip {b0['median_trip_time']:.0f} s → {s0['median_trip_time']:.0f} s")]):
    x = 0.6 + i * 4.75
    card(results, x, 7.8, 4.55, 1.95, fill=MINT if i < 3 else CARD, line=None if i < 3 else LINE)
    text(results, x + 0.2, 7.9, 4.2, 1.8, [(num, 32, True, TEAL if i < 3 else SAFFRON), para(cap, 15, space=2)])
footer(results, "Method: each seed builds an OPD crowd (8–12 walkers, two talking pairs, a pharmacy queue) and a trip from the entrance to a random department. "
       "Both robots get people's true positions. Normal robot = the same A* planner treating people as obstacles where they are now, fixed speed, same 0.6 m stop."
       + (" The trip Saathi missed: a very crowded crossing where it kept waiting rather than push through." if s0["arrived"] < s0["trips"] else ""))

# EXTRA (first): every line of PS-01, with what Saathi does and the proof from our runs.
set_title(checklist, "EXTRA · PS-01 CHECKLIST: EVERY LINE, WITH PROOF")
clear_body(checklist)
v = AB["vision"]
crows = [("PS-01 asks for", "What Saathi does", "Proof from our runs"),
         ("Understand surroundings with AI vision", "YOLO11 + depth camera + 360° LiDAR; people on a floor map", f"People placed within {v['localization_error_median']:.2f} m (median)"),
         ("Identify relevant people and objects", "Tracks people; YOLOE names objects by text", "“cardboard box” and “yellow caution sign” named on sight"),
         ("Navigate autonomously to an objective", "A* on a crowd costmap; goals by name or by sight", f"Found a dustbin by camera, reached it in {FIND['time']:.0f} s"),
         ("Detect and avoid obstacles", "Depth camera finds what the map does not have", f"Map-only robot hit {len(OB['maponly']['unmapped_hits'])} unmapped objects; Saathi {len(OB['vision']['unmapped_hits'])}"),
         ("Real-time decision making", "30 Hz reflex loop, replans twice a second", f"{s0['trips']} crowds: {NEAR_DROP}% fewer near-misses than a normal robot"),
         ("Object detection, image classification", "YOLO11 people; YOLOE posture: “person lying on the floor”", f"Fall classified {FEAT['fall_alert']['t'] - FALL_T['t']:.1f} s after it happened"),
         ("Scene understanding", "Conversations and queues from tracks; signs read", f"Cut through a conversation in 0 of {s0['trips']} crowds"),
         ("Vision-language models", "Qwen3.5-2B (Apple MLX) describes the scene", "Its description goes with the nurse alert"),
         ("Motor control", "Physics mecanum base, speed command per wheel", f"Forward, sideways and turning within {100 * CAL_ERR:.0f}% of the command"),
         ("Real or simulated environment", "Realistic Webots OPD hall, Hindi + English signs", "Deterministic: every run gives the same numbers")]
ct = checklist.shapes.add_table(len(crows), 3, Inches(0.6), Inches(2.3), Inches(18.8), Inches(0.62 * len(crows))).table
for c, wd in enumerate((5.4, 7.0, 6.4)):
    ct.columns[c].width = Inches(wd)
for r, row in enumerate(crows):
    for c, val in enumerate(row):
        cell = ct.cell(r, c)
        cell.text = ("✓  " if r and c == 0 else "") + val
        cell.margin_left = cell.margin_right = Inches(0.12)
        cell.margin_top = cell.margin_bottom = Inches(0.05)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if r == 0 else (CARD if r % 2 else WHITE)
        f = cell.text_frame.paragraphs[0].runs[0].font
        f.name, f.size, f.bold = FONT, Pt(15), r == 0 or c == 0
        f.color.rgb = WHITE if r == 0 else (TEAL if c == 0 else INK)

# 9. EXTRA: the same crowd in Webots, both robots.
set_title(scene_ab, "EXTRA · SAME CROWD, TWO ROBOTS (WEBOTS)")
clear_body(scene_ab)
picture(scene_ab, IMG["traj"], 0.6, 2.3, 10.4, 5.85, fit="contain", border=False)
for y, img, lab, col in ((2.35, "side_base", "NORMAL ROBOT: cuts through the conversation", MUTED), (6.4, "side_saathi", "SAATHI: goes around it", TEAL)):
    card(scene_ab, 11.3, y, 8.1, 0.5, fill=col, line=None, radius=0.15)
    text(scene_ab, 11.45, y + 0.05, 7.8, 0.4, [(lab, 16, True, WHITE)], anchor=MSO_ANCHOR.MIDDLE)
    picture(scene_ab, IMG[img], 11.3, y + 0.6, 8.1, 3.35)
rows_ab = [("", "Normal robot", "Saathi", "Saathi, camera + LiDAR only")] + [
    (lab, *[f(AB[k]) for k in ("baseline", "saathi", "vision")]) for lab, f in (
        ("Near-misses", lambda s: str(s["near_misses"])),
        ("Cut through the conversation", lambda s: "yes" if s["conversation_cuts"] else "no"),
        ("Time to Radiology", lambda s: f"{s['time']:.0f} s"))]
tb = scene_ab.shapes.add_table(len(rows_ab), 4, Inches(0.6), Inches(8.3), Inches(10.4), Inches(0.42 * len(rows_ab))).table
for c, wd in enumerate((3.6, 2.0, 1.6, 3.2)):
    tb.columns[c].width = Inches(wd)
for r, row in enumerate(rows_ab):
    for c, val in enumerate(row):
        cell = tb.cell(r, c)
        cell.text = val
        cell.margin_left = cell.margin_right = Inches(0.1)
        cell.margin_top = cell.margin_bottom = Inches(0.04)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if r == 0 else (CARD if r % 2 else WHITE)
        f = cell.text_frame.paragraphs[0].runs[0].font if cell.text_frame.paragraphs[0].runs else None
        if f:
            f.name, f.size, f.bold, f.color.rgb = FONT, Pt(14), r == 0 or c == 0, WHITE if r == 0 else INK

# 10. EXTRA: from pixels to decisions (no ground truth).
set_title(pixels, "EXTRA · FROM PIXELS TO DECISIONS")
clear_body(pixels)
picture(pixels, IMG["vision"], 0.6, 2.4, 12.4, 6.98, fit="contain")
text(pixels, 0.6, 9.45, 12.4, 0.9, [("Saathi driving on its own sensors. Map: grey dots are where people really are, teal rings are where Saathi thinks they are.", CAP, False, MUTED)])
v = AB["vision"]
text(pixels, 13.4, 2.4, 6.0, 4.6, [("HOW IT SEES", H, True, TEAL)] + bullets([
    "YOLO11 finds people in the camera image",
    "The depth camera gives each one's distance",
    "The 360° LiDAR adds people beside and behind",
    "A floor tracker keeps IDs and walking speeds",
    "The planner predicts 2 s ahead and picks the path"], SMALL, gap=5))
card(pixels, 13.4, 7.0, 6.0, 3.3, fill=MINT, line=None)
text(pixels, 13.6, 7.1, 5.6, 3.1, [(f"{v['localization_error_median']:.2f} m", 36, True, TEAL),
     para(f"median error placing people on the floor ({v['localization_error_p90']:.2f} m for 9 in 10)", 15, space=0),
     para(f"Drove to Radiology on its own eyes: {v['near_misses']} near-misses, no conversation cut, {v['time']:.0f} s "
          f"({AB['saathi']['time']:.0f} s with perfect positions).", 15, space=8)])

# EXTRA: obstacles that are not on the map, and finding a thing by sight.
set_title(obst, "EXTRA · UNKNOWN OBSTACLES, AND FINDING THINGS BY SIGHT")
clear_body(obst)
text(obst, 0.6, 2.3, 18.8, 0.45, [(f"OBSTACLES NOT ON THE MAP: a “wet floor” board and a cardboard box. Map-only: hit {len(OB['maponly']['unmapped_hits'])}. With depth vision: hit {len(OB['vision']['unmapped_hits'])}.", H, True, TEAL)])
for x, key in ((0.6, "ob_map"), (6.95, "ob_vis")):
    picture(obst, IMG[key], x, 2.85, 6.15, 3.46)
picture(obst, IMG["found_box"], 13.3, 2.85, 4.0, 3.0)
text(obst, 17.45, 2.9, 1.95, 3.4, [(f"At {FEAT['found_box']['t']:.0f} s:", 14, True, TEAL), para("“Found a cardboard box that is not on my map: going around it”", 14, space=2)])
text(obst, 0.6, 6.6, 18.8, 0.45, [("FIND IT BY SIGHT: “dustbin dhoondo”, and the dustbin is not on Saathi's map", H, True, TEAL)])
picture(obst, IMG["dustbin"], 0.6, 7.15, 4.61, 3.46)
picture(obst, IMG["arrive"], 5.4, 7.15, 6.15, 3.46)
text(obst, 11.9, 7.15, 7.5, 3.4, bullets([
    "Turns on the spot and asks YOLOE for “dustbin” about 3 times a second",
    f"Sees it {FEAT['dustbin']['status'].split()[3]} m away after {FEAT['dustbin']['t']:.1f} s; the depth camera puts it on the floor map",
    f"Plans there through the crowd and arrives at {FEAT['dustbin_arrived']['t']:.1f} s",
    "The same works for any word: “water cooler”, “wheelchair”, “sign board”"], SMALL, gap=6))

# EXTRA: a fall, classified from the camera, with an alert the VLM describes.
set_title(fall_s, "EXTRA · A FALL: CLASSIFY, ALERT, STAY, DESCRIBE")
clear_body(fall_s)
picture(fall_s, IMG["fall"], 0.6, 2.4, 8.4, 6.3)
text(fall_s, 0.6, 8.8, 8.4, 0.8, [(f"Saathi's camera {FEAT['fall_alert']['t'] - FALL_T['t']:.1f} s after the fall: YOLOE says “person lying on the floor”.", CAP, False, MUTED)])
picture(fall_s, IMG["stay"], 9.4, 2.4, 10.0, 4.4)
al = FEAT["fall_alert"]
card(fall_s, 9.4, 7.0, 10.0, 3.4, fill=MINT, line=None)
text(fall_s, 9.65, 7.1, 9.5, 3.2, [("ALERT TO THE NURSE STATION", H, True, TEAL),
     para(f"{al['message']} (at {al['t']:.1f} s)", 16, space=4),
     dict(runs=[("VLM, in its own process: ", True, INK), (f"“{al.get('vlm_scene', '')}”", False, INK)], size=16, space_before=6),
     para(f"Then Saathi goes to them, stays until the nurse takes over, and finishes its trip ({FALL['time']:.0f} s).", 15, MUTED, space=6)])

# 11. EXTRA: the black box answers "why?".
set_title(bbox, "EXTRA · BLACK BOX: “TUM RUKE KYUN?”")
clear_body(bbox)
picture(bbox, IMG["blackbox"], 0.6, 2.4, 9.6, 7.2)
text(bbox, 0.6, 9.7, 9.6, 0.7, [(f"Saved by Saathi at {BB['t']:.1f} s: the camera frame of that decision, with what it saw.", CAP, False, MUTED)])
subject = next(w for w in BB["decision"].split() if w.startswith("P"))
mm, ss = divmod(int(BB["t"]), 60)
card(bbox, 10.9, 2.5, 8.5, 1.1, fill=CARD)
text(bbox, 11.15, 2.62, 8.0, 0.9, [dict(runs=[("You:  ", True, MUTED), (f"Saathi, {mm}:{ss:02d} pe tum dheeme kyun hue?", False, INK)], size=18)])
card(bbox, 10.9, 3.85, 8.5, 2.6, fill=MINT, line=None)
text(bbox, 11.15, 3.97, 8.0, 2.4, [dict(runs=[("Saathi:  ", True, TEAL), (f"{mm}:{ss:02d} pe {subject} mere raaste ki taraf aa rahe the. Main {BB['speed']:.2f} m/s pe tha, "
     "isliye dheema hua, phir side khisak ke unhe jaane diya. Ye raha us pal ka camera frame.", False, INK)], size=18)])
text(bbox, 10.9, 6.75, 8.5, 3.6, [("WHAT THE BLACK BOX KEEPS", H, True, TEAL)] + bullets([
    f"Time {BB['t']:.2f} s · decision: {BB['decision']}",
    f"Speed {BB['speed']:.2f} m/s · people in view: {', '.join(BB['in_view'])}",
    "The camera frame, with every box and distance",
    "The answer above is written from this record, so it cannot make things up"], SMALL, gap=5))

# 12. EXTRA: the team's rover is Saathi's body.
set_title(extra2, "EXTRA · OUR ROVER IS SAATHI'S BODY")
clear_body(extra2)
picture(extra2, IMG["rover"], 0.6, 2.4, 6.9, 6.25, fit="contain")
text(extra2, 0.6, 8.75, 6.9, 0.5, [("Team design: AI Rover HiH 2026", CAP, False, MUTED)])
rows = [("Stereo RGB camera", "Find, track and read people's intent"), ("Depth camera", "Distance to each person"),
        ("360° LiDAR", "Map, position, blind spots behind"), ("Ultrasonic + IR", "Close-range stop"),
        ("IMU", "Speed, heading, gentle braking"), ("Mecanum wheels", "Slide sideways in tight crowds"),
        ("Jetson Orin Nano", "Runs the reflex brain on board"), ("+ Face screen, mic, speaker", "Talk, listen, show mood (we add)"),
        ("+ Red e-stop button", "A physical stop anyone can press (we add)")]
tbl = extra2.shapes.add_table(len(rows) + 1, 2, Inches(8.0), Inches(2.4), Inches(11.4), Inches(0.48 * (len(rows) + 1))).table
tbl.columns[0].width, tbl.columns[1].width = Inches(4.4), Inches(7.0)
for r, (a, b) in enumerate([("Part", "What Saathi uses it for")] + rows):
    for c, val in enumerate((a, b)):
        cell = tbl.cell(r, c)
        cell.text = val
        cell.margin_left = cell.margin_right = Inches(0.12)
        cell.margin_top = cell.margin_bottom = Inches(0.05)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if r == 0 else (MINT if rows[r - 1][0].startswith("+") else (CARD if r % 2 else WHITE))
        f = cell.text_frame.paragraphs[0].runs[0].font
        f.name, f.size, f.bold, f.color.rgb = FONT, Pt(15), r == 0 or c == 0, WHITE if r == 0 else INK
picture(extra2, IMG["closeup"], 15.6, 7.55, 3.8, 2.9)
text(extra2, 8.0, 7.55, 7.3, 3.0, [("SAME SENSORS IN SIMULATION", H, True, TEAL),
     para("We built this rover in Webots with the same camera, depth camera, LiDAR and IMU, and gave it the face screen. "
          "The brain talks to the sensors through a small interface, so the same code can drive the real rover once its drivers are in.", SMALL)])

# 9. Thank you: keep the template's art; the tagline sits clear of it, top right.
text(thanks, 15.1, 4.95, 4.3, 2.8, [("SAATHI", 34, True, TEAL), para("Raasta bhi, saath bhi.", 20, INK, True, 2),
     para("The way, and the company.", 15, MUTED, space=2), para("Team Glitch", 15, INK, True, 10), para(TEAM[0][0], 13, MUTED, space=2)])

out = P("ppt", "Saathi_HackInHills26.pptx")
prs.save(out)
print("wrote", out)
