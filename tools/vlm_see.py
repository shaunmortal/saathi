"""Saathi's thinking-brain eyes: a small vision-language model (Qwen3.5-2B on Apple MLX) that describes a camera frame,
reads the sign boards in it and answers a question about it. It takes about 3 s, so it runs beside the 30 Hz reflex loop,
on demand ("Saathi, saamne kya hai?", "Radiology kahan hai?", explaining a black-box frame).

Usage: .venv-brain/bin/python tools/vlm_see.py OUT.json IMAGE [IMAGE ...]   -> scene, signs and a Hinglish answer per image
"""
import json, os, sys, time
from mlx_vlm import apply_chat_template, load, stream_generate

MODEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "qwen35_2b")
QUESTIONS = {
    "scene": "You are the eyes of Saathi, a guide robot in an Indian hospital OPD hall. In 2-3 short sentences say what is happening: "
             "where people are and what they are doing (walking, standing in a queue, talking, lying on the floor), and anything on the floor in the way.",
    "signs": "List every sign board you can read in this image, with its text and whether it is on the left, centre or right. "
             'Answer only JSON: {"signs": [{"text": "...", "where": "left|centre|right"}]}',
    "hinglish": "A patient asks the robot: 'Saamne kya hai?' Answer in one or two short sentences of simple Hinglish (Hindi written in English letters).",
}


def ask(model, proc, image, question, max_tokens=150):
    prompt = apply_chat_template(proc, model.config, question, num_images=1)
    text, t0 = "", time.perf_counter()
    for r in stream_generate(model, proc, prompt, image=[image], max_tokens=max_tokens, temperature=0.0):
        text += r.text
    return text.strip(), round(time.perf_counter() - t0, 2)


if __name__ == "__main__":
    if sys.argv[1] == "--alert":  # vlm_see.py --alert ALERT.json IMAGE: add a scene description to a nurse alert
        model, proc = load(MODEL)
        text, secs = ask(model, proc, sys.argv[3], QUESTIONS["scene"])
        alert = json.load(open(sys.argv[2]))
        alert.update(vlm_scene=text, vlm_seconds=secs)
        json.dump(alert, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
        sys.exit(0)
    out, images = sys.argv[1], sys.argv[2:]
    model, proc = load(MODEL)
    results = []
    for img in images:
        rec = {"image": img}
        for key, q in QUESTIONS.items():
            rec[key], rec[key + "_s"] = ask(model, proc, img, q)
        results.append(rec)
        print(json.dumps(rec, ensure_ascii=False, indent=1), flush=True)
    json.dump(results, open(out, "w"), ensure_ascii=False, indent=1)
