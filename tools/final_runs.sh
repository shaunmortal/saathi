#!/bin/zsh
# Every recorded Webots run behind the PPT, in order. Each prints its summary; all are deterministic.
R=${0:A:h:h}; cd $R
tools/run_webots.sh ab_baseline --mode=baseline
tools/run_webots.sh ab_saathi --mode=saathi
tools/run_webots.sh ab_vision --mode=saathi --perception=vision
tools/run_webots.sh ob_maponly --mode=saathi --unmapped=1
tools/run_webots.sh ob_vision --mode=saathi --perception=vision --unmapped=1
tools/run_webots.sh find_dustbin --mode=saathi --perception=vision --goal=find:dustbin
tools/run_webots.sh fall_vision --mode=saathi --perception=vision --fall=4 --until=80
echo ALL DONE
