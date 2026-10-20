#!/bin/zsh
# Live demo: Webots in real time (GUI) with the lost-child scene; Saathi waits at the entrance for spoken commands.
# In a second terminal:  .venv-brain/bin/python tools/voice.py      (press Enter, speak in Hindi / Hinglish / English)
# Extra arguments go to tools/make_world.py, e.g. --robots=2 for Saathi Parivaar with two robots.
R=${0:A:h:h}
$R/.venv/bin/python $R/tools/make_world.py --perception=vision --lost=1 --live=1 --goal=at:-7.0,0.0 --until=100000 --every=0 --out=../../out/live "$@" >/dev/null || exit 1
~/Applications/Webots.app/Contents/MacOS/webots --mode=realtime $R/worlds/opd.wbt
