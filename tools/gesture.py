"""Gesture stop: show Saathi a fist on the laptop webcam and it stops; an open palm lets it carry on.

MediaPipe's hand landmarker (models/hand_landmarker.task) finds 21 points on the hand. A finger is out when its tip is
farther from the wrist than its middle joint, so the reading works at any hand angle. A fist held for 0.5 s sends
{"cmd": "stop"} to out/live/commands.jsonl (a controller in --live=1 holds still); an open palm held for 1 s after that sends
{"cmd": "go"}. The window shows the camera, the hand and what was sent. The robot's own 0.6 m safety stop never depends on this.
Usage: .venv/bin/python tools/gesture.py   (q quits; macOS asks once for camera access for the terminal)
"""
import json, os, sys, time
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMDS = os.path.join(ROOT, "out", "live", "commands.jsonl")
MODEL = os.path.join(ROOT, "models", "hand_landmarker.task")
FINGERS = [(6, 8), (10, 12), (14, 16), (18, 20)]  # (middle joint, tip) for index, middle, ring, little finger; wrist is 0


def read_pose(lm):
    """21x2 landmarks -> 'palm' (3-4 fingers out), 'fist' (none out) or 'other'."""
    out = sum(np.linalg.norm(lm[tip] - lm[0]) > np.linalg.norm(lm[pip] - lm[0]) for pip, tip in FINGERS)
    return "palm" if out >= 3 else "fist" if out == 0 else "other"


def send(cmd):
    os.makedirs(os.path.dirname(CMDS), exist_ok=True)
    with open(CMDS, "a") as f:
        f.write(json.dumps({"cmd": cmd, "via": "gesture", "wall": round(time.time(), 2)}) + "\n")


def main():
    import cv2
    from mediapipe import Image, ImageFormat
    from mediapipe.tasks.python import BaseOptions, vision
    lm_model = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL), running_mode=vision.RunningMode.VIDEO, num_hands=1))
    cap = cv2.VideoCapture(0)
    since, stopped, banner, t0 = {}, False, ("Show a fist to stop Saathi", (90, 90, 90)), time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        res = lm_model.detect_for_video(Image(image_format=ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), int((time.time() - t0) * 1000))
        pose = None
        if res.hand_landmarks:
            lm = np.array([[p.x, p.y] for p in res.hand_landmarks[0]])
            pose = read_pose(lm)
            for x, y in lm:
                cv2.circle(frame, (int(x * frame.shape[1]), int(y * frame.shape[0])), 4, (32, 160, 240), -1)
        now = time.time()
        since = {pose: since.get(pose, now)} if pose else {}
        if pose == "fist" and not stopped and now - since["fist"] > 0.5:
            send("stop"); stopped, banner = True, ("STOP sent: Saathi ruk gaya", (40, 40, 220))
        elif pose == "palm" and stopped and now - since["palm"] > 1.0:
            send("go"); stopped, banner = False, ("GO sent: Saathi chal pada", (60, 150, 40))
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 48), banner[1], -1)
        cv2.putText(frame, f"{banner[0]}   [{pose or 'no hand'}]", (14, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow("Saathi gesture stop", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()


if __name__ == "__main__":
    palm = np.array([[0.5, 0.9]] + [[0.5, 0.9 - 0.05 * i] for i in range(1, 21)])  # every point farther up the hand
    fist = palm.copy()
    for pip, tip in FINGERS:
        fist[tip] = (fist[0] + fist[pip]) / 2  # tips curled back towards the wrist
    assert read_pose(palm) == "palm" and read_pose(fist) == "fist"
    if "--check" not in sys.argv:
        main()
