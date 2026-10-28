"""Demo video from our own runs -> out/media/Saathi_demo.mp4 (1080p, ~2 min). Narration: macOS 'Rishi' (English, India) via `say`.
Each segment = one visual (slide render, still, clip, GIF) + one sentence of narration; the segment lasts as long as the narration."""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
R = P("ppt", "Saathi_Round2_render", "Saathi_Round2_render.%03d.png")
TMP = tempfile.mkdtemp(prefix="saathi_video_")
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
VOICE = "Rishi"

SEGS = [  # (visual path | list of stills, start s, caption, narration)
    (R % 1, 0, "", "Saathi. A guide robot that reads Indian hospital crowds. Team Glitch, Hack in Hills twenty twenty-six, problem statement one."),
    (R % 2, 0, "", "Big Indian O P Ds are packed and signed in English. Fifteen thousand patients a day at one hospital. Seven in ten first-time visitors need a person to find their way. Most older patients come alone, and nurses leave their patients to show the way."),
    (P("out", "media", "dashboard.mp4"), 0, "Saathi on its own camera, depth and LiDAR",
     "This is Saathi, driving on its own camera, depth camera and lidar in our Webots hospital. YOLO finds every person, the planner predicts where each one will be in two seconds, and Saathi slows, waits, or slides sideways to let people pass."),
    (P("docs", "side_by_side.jpg"), 0, "Same crowd: a normal planner vs Saathi", "Same crowd, two robots. A normal planner cuts straight through a conversation. Saathi reads the group and goes around it."),
    ([P("docs", "obstacles.jpg"), P("docs", "dustbin.jpg")], 0, "Obstacles not on the map · finding things by sight",
     "A wet-floor board and a cardboard box that are not on its map: the depth camera sees them and Saathi goes around. Ask for a dustbin, and it finds one by sight and drives there."),
    ("fall", 0, "A fall: classified, alerted, stayed with", "A patient falls. Saathi classifies it in three tenths of a second, a vision language model gives a second opinion, the nurse station is alerted, and Saathi stays with the patient until the nurse comes."),
    ([P("docs", "lift.gif"), P("docs", "floor2.gif")], 0, "Blood Bank is upstairs: Saathi takes the lift",
     "Blood bank kahan hai? It is upstairs. Saathi drives to the lobby, calls the lift, rides up, and its map switches to the first floor: Blood Bank, I C U, O T and the wards."),
    (P("out", "media", "team4", "parivaar.mp4"), 38, "Saathi Parivaar: two robots, one memory of people",
     "Saathi Parivaar. A father says, mera beta kho gaya, laal t-shirt. Two robots share one memory of people: clothes and height, never faces. One stays with the father, the other goes where the boy is now. With one robot, memory halves the search time."),
    (R % 6, 0, "", "Measured, not promised. On two hundred seeded crowds: seventy-three percent fewer near-misses, zero conversations cut, and one hundred ninety-nine of two hundred trips arrived."),
    (R % 9, 0, "", "Everything runs offline on an eight gigabyte laptop. Code, benchmarks and GIFs of every run are on GitHub: shaunmortal slash saathi. Saathi. Raasta bhi, saath bhi."),
]


def run(*cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode:
        sys.exit("\n".join(r.stderr.decode(errors="ignore").splitlines()[-6:]))


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).decode().strip())


def narrate(i, text):
    aiff, wav = os.path.join(TMP, f"n{i}.aiff"), os.path.join(TMP, f"n{i}.wav")
    run("say", "-v", VOICE, "-r", "175", "-o", aiff, text)
    run("ffmpeg", "-y", "-i", aiff, "-ar", "44100", "-ac", "2", wav)
    return wav, dur(wav)


def fall_clip():
    """CCTV frames of the fall run, 2-16 s, at their 10 Hz."""
    import glob, re, shutil
    d = os.path.join(TMP, "fall"); os.makedirs(d, exist_ok=True)
    fs = sorted(glob.glob(P("out", "fall_vision", "cctv_*.jpg")), key=lambda f: float(re.search(r"_(\d+\.\d+)", f).group(1)))
    fs = [f for f in fs if 2.0 <= float(re.search(r"_(\d+\.\d+)", f).group(1)) <= 16.0]
    for k, f in enumerate(fs):
        shutil.copy(f, os.path.join(d, f"{k:04d}.jpg"))
    out = os.path.join(TMP, "fall.mp4")
    run("ffmpeg", "-y", "-framerate", "10", "-i", os.path.join(d, "%04d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p", out)
    return out


SCALE = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x1b1f1e,setsar=1"


def caption_png(i, cap):
    """A lower-third band with the caption, drawn with PIL (this ffmpeg has no drawtext)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (1920, 110), (15, 92, 82, 217))
    ImageDraw.Draw(im).text((48, 30), cap, font=ImageFont.truetype(FONT, 40), fill="white")
    path = os.path.join(TMP, f"cap{i}.png"); im.save(path)
    return path


def segment(i, vis, start, cap, length):
    """One segment of `length` seconds: a still, a list of stills (equal shares), a clip (trimmed, frozen at the end if short) or a GIF."""
    out = os.path.join(TMP, f"s{i}.mp4")
    vf = SCALE
    if isinstance(vis, list):
        parts = []
        for k, v in enumerate(vis):
            p = os.path.join(TMP, f"s{i}_{k}.mp4")
            share = length / len(vis)
            if v.endswith(".gif"):
                run("ffmpeg", "-y", "-ignore_loop", "0", "-i", v, "-t", f"{share:.2f}", "-vf", vf + ",fps=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", p)
            else:
                run("ffmpeg", "-y", "-loop", "1", "-i", v, "-t", f"{share:.2f}", "-vf", vf + ",fps=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", p)
            parts.append(p)
        lst = os.path.join(TMP, f"s{i}.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out)
    elif vis.endswith((".png", ".jpg")):
        run("ffmpeg", "-y", "-loop", "1", "-i", vis, "-t", f"{length:.2f}", "-vf", vf + ",fps=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", out)
    else:
        avail = dur(vis) - start
        pad = max(0.0, length - avail)
        run("ffmpeg", "-y", "-ss", str(start), "-i", vis, "-t", f"{length:.2f}", "-vf", vf + f",tpad=stop_mode=clone:stop_duration={pad:.2f},fps=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", out)
    if cap:
        capped = os.path.join(TMP, f"s{i}c.mp4")
        run("ffmpeg", "-y", "-i", out, "-i", caption_png(i, cap), "-filter_complex", "[0:v][1:v]overlay=0:970", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", capped)
        return capped
    return out


parts = []
for i, (vis, start, cap, text) in enumerate(SEGS):
    wav, n = narrate(i, text)
    length = n + 0.8
    if vis == "fall":
        vis = fall_clip()
    v = segment(i, vis, start, cap, length)
    out = os.path.join(TMP, f"seg{i}.mp4")
    run("ffmpeg", "-y", "-i", v, "-i", wav, "-filter_complex", f"[1:a]adelay=400|400,apad=whole_dur={length:.2f}[a]", "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", out)
    parts.append(out)
    print(f"segment {i}: {length:.1f} s", flush=True)
lst = os.path.join(TMP, "all.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
final = P("out", "media", "Saathi_demo.mp4")
run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", final)
print("wrote", final, f"{dur(final):.0f} s")
