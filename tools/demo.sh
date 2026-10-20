#!/bin/zsh
# GUI demo: Saathi drives to Radiology on its own camera, an unmapped box on the way, a fall at 25 s; Webots stays open at the end.
R=${0:A:h:h}
$R/.venv/bin/python $R/tools/make_world.py --mode=saathi --perception=vision --goal=Radiology --unmapped=1 --fall=25 --every=0 --until=120 --quit=0 --out=../../out/run "$@" >/dev/null || exit 1
~/Applications/Webots.app/Contents/MacOS/webots --mode=realtime $R/worlds/opd.wbt
