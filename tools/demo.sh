#!/bin/zsh
# GUI demo of the whole hospital: Saathi on its own camera tours Pharmacy -> Blood Bank (lift, first floor) -> Lab, an unmapped box on the way,
# a fall at 25 s; Webots stays open at the end. Extra arguments go to make_world.py (e.g. --tour=ICU,Emergency).
R=${0:A:h:h}
$R/.venv/bin/python $R/tools/make_world.py --mode=saathi --perception=vision --floors=2 "--tour=Pharmacy,Blood Bank,Lab" --unmapped=1 --fall=25 --every=0 --until=400 --quit=0 --out=../../out/run "$@" >/dev/null || exit 1
~/Applications/Webots.app/Contents/MacOS/webots --mode=realtime $R/worlds/opd.wbt
