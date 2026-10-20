#!/bin/zsh
# One recorded Webots run. Usage: tools/run_webots.sh <name> [--mode=..] [--perception=..] [--goal=..] [--every=..] [--until=..]
# Writes worlds/opd.wbt for these settings, runs Webots minimized in fast mode, prints out/<name>/summary.json.
R=${0:A:h:h}; NAME=$1; shift
rm -rf $R/out/$NAME; mkdir -p $R/out/$NAME
$R/.venv/bin/python $R/tools/make_world.py --out=../../out/$NAME "$@" >/dev/null || exit 1
~/Applications/Webots.app/Contents/MacOS/webots --batch --stdout --stderr --minimize --mode=fast $R/worlds/opd.wbt > $R/out/$NAME/webots.log 2>&1 < /dev/null &
pid=$!; for i in {1..${TIMEOUT:-400}}; do kill -0 $pid 2>/dev/null || break; sleep 1; done  # TIMEOUT=seconds for long runs
kill -0 $pid 2>/dev/null && { echo "TIMEOUT"; kill $pid; }
grep -i "crash\|Traceback\|Error" $R/out/$NAME/webots.log | grep -v "^UNSUPPORTED" | head -5
echo "$NAME (${i}s):"; cat $R/out/$NAME/summary.json 2>/dev/null || tail -20 $R/out/$NAME/webots.log
