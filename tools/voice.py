"""Saathi's Hindi voice agent: listen on the Mac's microphone, understand Hindi / Hinglish / English, answer in a Hindi
voice, and tell the robot what to do.

Speech -> text: Whisper large-v3-turbo (4-bit, Apple MLX, offline; models/whisper_turbo_q4), nudged with hospital words.
Text -> intent: a phrasebook of hospital words in Devanagari and Roman script. It also turns a lost child's description into
the English words the memory searches with ("laal t-shirt wala beta" -> "a photo of a small boy in a red shirt").
Text -> speech: the Mac's offline Hindi voice (say -v Lekha). Commands go to out/live/commands.jsonl, which the Webots
controller reads when it runs with --live=1.

Usage (in .venv-brain):
  python tools/voice.py                                   talk: press Enter, speak for 5 s, hear Saathi; Ctrl-C to stop
  python tools/voice.py --text "Mujhe X-ray karwana hai"  type instead of speaking
  python tools/voice.py --selftest                        Lekha says test sentences, Whisper hears them, intents are checked
Say "Saathi, ruko" to stop it: a single short word on its own is often misheard.
"""
import json, os, re, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMDS = os.path.join(ROOT, "out", "live", "commands.jsonl")
MODEL = os.path.join(ROOT, "models", "whisper_turbo_q4")
HINT = "अस्पताल, ओपीडी, एक्स-रे, लैब, खून की जांच, दवाई, पर्ची, इमरजेंसी, वार्ड, लिफ्ट, ब्लड बैंक, आईसीयू, मेरा बेटा खो गया, लाल टी-शर्ट, रुको"

DEPTS = {  # where to go: the words people use for it
    "Radiology": ["एक्स-रे", "एक्सरे", "एक्स रे", "रेडियोलॉजी", "अल्ट्रासाउंड", "x-ray", "xray", "x ray", "radiology", "ultrasound"],
    "Lab": ["लैब", "खून", "ब्लड", "जांच", "जाँच", "टेस्ट", "सैंपल", "lab", "blood", "test", "sample", "khoon", "jaanch", "janch"],
    "Pharmacy": ["दवा", "दवाई", "दवाइयां", "दवाइयाँ", "फार्मेसी", "मेडिकल", "dawa", "dawai", "pharmacy", "medicine"],
    "Emergency": ["इमरजेंसी", "आपातकालीन", "emergency"],
    "Blood Bank": ["ब्लड बैंक", "ब्लडबैंक", "रक्तदान", "रक्त", "blood bank", "bloodbank", "raktdaan", "rakt"],
    "ICU": ["आईसीयू", "आई सी यू", "आई.सी.यू", "icu"],
    "OT": ["ऑपरेशन", "ओटी", "ओ टी", "operation", "surgery", "theatre"],
    "Wards": ["वार्ड", "भर्ती", "ward", "wards", "admit"],
    "Wards & Lift": ["लिफ्ट", "lift"],
    "Registration": ["पर्ची", "रजिस्ट्रेशन", "काउंटर", "parchi", "registration", "counter"],
}
DEPT_HI = {"Radiology": "एक्स-रे विभाग", "Lab": "लैब", "Pharmacy": "दवा की खिड़की", "Emergency": "इमरजेंसी",
           "Wards & Lift": "लिफ्ट", "Registration": "पर्ची काउंटर", "Blood Bank": "ब्लड बैंक, पहली मंज़िल पर", "ICU": "आई.सी.यू., पहली मंज़िल पर",
           "OT": "ऑपरेशन थिएटर, पहली मंज़िल पर", "Wards": "वार्ड, पहली मंज़िल पर"}
LOST = ["खो गया", "खो गयी", "खो गई", "खोया", "खो", "नहीं मिल रहा", "नहीं मिल रही", "गुम", "लापता", "kho gaya", "kho gayi", "kho", "lost", "missing"]
STOP = ["रुको", "रुक जाओ", "रुकिए", "रुक", "ruko", "ruk", "stop"]
HELLO = ["नमस्ते", "नमस्कार", "हेलो", "namaste", "hello", "hi"]
WHO = {"boy": ["बेटा", "बेटे", "लड़का", "लड़के", "भाई", "beta", "ladka", "bhai", "son", "boy"],
       "girl": ["बेटी", "लड़की", "बहन", "beti", "ladki", "behen", "daughter", "girl"],
       "child": ["बच्चा", "बच्चे", "बच्ची", "bachcha", "baccha", "bacha", "child", "kid"]}
WHO_HI = {"boy": "बेटा", "girl": "बेटी", "child": "बच्चा"}
COLORS = {"red": ["लाल", "laal", "lal", "red"], "blue": ["नीला", "नीली", "नीले", "neela", "neeli", "nila", "blue"],
          "green": ["हरा", "हरी", "हरे", "hara", "hari", "green"], "yellow": ["पीला", "पीली", "पीले", "peela", "peeli", "yellow"],
          "black": ["काला", "काली", "काले", "kaala", "kala", "kaali", "black"], "white": ["सफ़ेद", "सफेद", "safed", "white"],
          "pink": ["गुलाबी", "gulabi", "pink"], "orange": ["नारंगी", "narangi", "orange"]}
COLOR_HI = {"red": "लाल", "blue": "नीले", "green": "हरे", "yellow": "पीले", "black": "काले", "white": "सफ़ेद", "pink": "गुलाबी", "orange": "नारंगी"}
CLOTHES = {"shirt": ["टी-शर्ट", "टीशर्ट", "टी शर्ट", "शर्ट", "t-shirt", "tshirt", "t shirt", "shirt"], "dress": ["फ्रॉक", "ड्रेस", "frock", "dress"],
           "kurta": ["कुर्ता", "कुर्ते", "kurta"], "jacket": ["जैकेट", "स्वेटर", "jacket", "sweater"]}
CLOTH_HI = {"shirt": "टी-शर्ट", "dress": "फ्रॉक", "kurta": "कुर्ते", "jacket": "जैकेट"}


def has(text, words):
    """Whole-word match for Roman words, plain substring for Devanagari (whose words carry vowel signs)."""
    return next((w for w in words if (re.search(rf"\b{re.escape(w)}\b", text) if w.isascii() else w in text)), None)


def pick(text, table):
    """The key of `table` whose word appears earliest in the text (so 'laal t-shirt, neeli jeans' gives red)."""
    hits = [(m.start(), k) for k, words in table.items() for w in words
            for m in [re.search(rf"\b{re.escape(w)}\b" if w.isascii() else re.escape(w), text)] if m]
    return min(hits)[1] if hits else None


def understand(text, pending=None):
    """text -> dict(intent, reply (Devanagari, for the Hindi voice), cmd (for the robot) or None).
    pending: the last lost-child report still missing a description, so 'laal t-shirt' alone completes it."""
    t = text.lower().strip()
    if has(t, STOP):
        return dict(intent="stop", reply="ठीक है, रुक गया।", cmd=dict(cmd="stop"))
    lost = has(t, LOST) or (pending is not None and (pick(t, COLORS) or pick(t, CLOTHES)))
    if lost:
        who = pick(t, WHO) or (pending or {}).get("who") or "child"
        color, cloth = pick(t, COLORS) or (pending or {}).get("color"), pick(t, CLOTHES) or (pending or {}).get("cloth")
        if not color:
            return dict(intent="lost_ask", who=who, color=None, cloth=cloth,
                        reply="घबराइए मत, हम ढूंढ लेंगे। बच्चे ने किस रंग के कपड़े पहने हैं?", cmd=None)
        query = f"a photo of a small {who} in a {color} {cloth or 'shirt'}"
        said = f"{WHO_HI[who]} खो गया। {COLOR_HI[color]} {CLOTH_HI.get(cloth, 'कपड़े')}।"
        return dict(intent="lost", who=who, color=color, cloth=cloth, query=query,
                    reply=f"घबराइए मत। मैं अपने साथियों से पूछता हूँ: {COLOR_HI[color]} {CLOTH_HI.get(cloth, 'कपड़ों')} वाला {WHO_HI[who]}। आप यहीं रहिए, मैं आपके साथ हूँ।",
                    cmd=dict(cmd="lost", query=query, said=said, child=True))
    dept = pick(t, DEPTS)
    if dept:
        return dict(intent="goto", goal=dept, reply=f"ठीक है, चलिए। मैं आपको {DEPT_HI[dept]} ले चलता हूँ। आराम से मेरे साथ चलिए।",
                    cmd=dict(cmd="goto", goal=dept))
    if has(t, HELLO):
        return dict(intent="hello", reply="नमस्ते! मैं साथी हूँ। आपको कहाँ जाना है?", cmd=None)
    return dict(intent="unknown", reply="माफ़ कीजिए, मैं समझ नहीं पाया। आपको कहाँ जाना है?", cmd=None)


def speak(text_hi):
    subprocess.run(["say", "-v", "Lekha", text_hi], check=False)


def send(cmd):
    os.makedirs(os.path.dirname(CMDS), exist_ok=True)
    with open(CMDS, "a") as f:
        f.write(json.dumps({**cmd, "wall": round(time.time(), 2)}, ensure_ascii=False) + "\n")


def record(path, seconds=5):
    """The Mac's default microphone, 16 kHz mono. macOS asks once for microphone access for the terminal."""
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "avfoundation", "-i", ":0", "-t", str(seconds), "-ac", "1", "-ar", "16000", "-y", path], check=True)


_stt = None


def hear(path):
    global _stt
    if _stt is None:
        from mlx_audio.stt.utils import load_model
        _stt = load_model(MODEL)
    return _stt.generate(path, language="hi", initial_prompt=HINT, return_timestamps=False, verbose=False,
                         hotwords=["साथी", "रुक जाओ", "एक्स-रे", "दवाई", "खो गया"]).text.strip()


def turn(text, pending=None, act=True):
    u = understand(text, pending)
    print(f"  heard : {text}\n  intent: {u['intent']}" + (f" -> {u['cmd']}" if u["cmd"] else "") + f"\n  saathi: {u['reply']}")
    if act:
        if u["cmd"]:
            send(u["cmd"])
        speak(u["reply"])
    return u


def selftest():
    cases = [("मुझे एक्स-रे करवाना है", "goto", "Radiology"), ("दवाई कहाँ मिलेगी", "goto", "Pharmacy"),
             ("मेरा बेटा खो गया, लाल टी-शर्ट पहनी है", "lost", "a photo of a small boy in a red shirt"),
             ("खून की जांच कहाँ होती है", "goto", "Lab"), ("साथी रुको", "stop", None)]  # one short word alone ("रुको") is misheard
    ok = 0
    with tempfile.TemporaryDirectory() as d:
        for said, intent, want in cases:
            aiff, wav = os.path.join(d, "x.aiff"), os.path.join(d, "x.wav")
            subprocess.run(["say", "-v", "Lekha", "-o", aiff, said], check=True)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-i", aiff, "-ac", "1", "-ar", "16000", "-y", wav], check=True)
            t0 = time.time()
            text = hear(wav)
            u = understand(text)
            got = u.get("goal") or u.get("query")
            good = u["intent"] == intent and (want is None or got == want)
            ok += good
            print(f"{'OK ' if good else 'BAD'} said: {said} | heard: {text} | {u['intent']} {got or ''} | {time.time() - t0:.1f} s")
    print(f"{ok}/{len(cases)} understood")
    return ok == len(cases)


if __name__ == "__main__":
    # Text-only checks of the phrasebook (no audio): Hinglish, Devanagari and a two-turn lost-child report.
    assert understand("Mujhe X-ray karwana hai")["cmd"] == dict(cmd="goto", goal="Radiology")
    assert understand("mera beta kho gaya, laal t-shirt")["cmd"]["query"] == "a photo of a small boy in a red shirt"
    first = understand("मेरी बेटी नहीं मिल रही")
    assert first["intent"] == "lost_ask" and understand("हरी फ्रॉक पहनी है", pending=first)["cmd"]["query"] == "a photo of a small girl in a green dress"
    assert understand("ruko")["intent"] == "stop" and understand("दवाई कहाँ है")["cmd"]["goal"] == "Pharmacy"
    assert understand("blood bank kahan hai")["cmd"]["goal"] == "Blood Bank" and understand("khoon ki jaanch")["cmd"]["goal"] == "Lab" and understand("ICU le chalo")["cmd"]["goal"] == "ICU"
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if "--text" in sys.argv:
        turn(sys.argv[sys.argv.index("--text") + 1])
        sys.exit(0)
    print("Saathi sun raha hai. Enter dabaiye aur 5 second boliye (Ctrl-C: band).")
    pending = None
    with tempfile.TemporaryDirectory() as d:
        while True:
            input("\n[Enter] ")
            wav = os.path.join(d, "in.wav")
            record(wav)
            u = turn(hear(wav), pending)
            pending = u if u["intent"] == "lost_ask" else None
