#!/bin/zsh
# Renders a .pptx with Keynote (in the background) to slide PNGs and, with --pdf, a PDF next to it.
# Usage: tools/render_ppt.sh ppt/Saathi_HackInHills26.pptx [--pdf]
F=${1:A}; O=${F:r}_render; rm -rf $O; mkdir -p $O
# Keynote crashes if an export request arrives while it is still starting up: wait until it answers a harmless question.
pgrep -x Keynote >/dev/null || { open -g -a "Keynote Creator Studio"; for i in {1..30}; do pgrep -x Keynote >/dev/null && break; sleep 1; done; sleep 15; }
for i in {1..20}; do osascript -e 'tell application id "com.apple.Keynote" to get count of documents' >/dev/null 2>&1 && break; sleep 1; done
osascript <<OSA
tell application id "com.apple.Keynote"
  set d to open POSIX file "$F"
  delay 2
  export d to POSIX file "$O" as slide images with properties {image format:PNG, skipped slides:false}
  if "$2" is "--pdf" then export d to POSIX file "${F:r}.pdf" as PDF with properties {PDF image quality:Best}
  close d saving no
end tell
OSA
ls $O | wc -l
