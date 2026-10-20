#!/bin/zsh
# Renders hospital signs (Hindi + English) to textures/ with headless Chrome, which shapes Devanagari correctly.
R=${0:A:h:h}; C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; P=$R/out/chrome-prof
shot() { "$C" --headless=new --disable-gpu --no-first-run --user-data-dir=$P --hide-scrollbars --window-size=$2 --screenshot=$R/textures/$1.png "file://$R/tools/sign.html#$3" >/dev/null 2>&1; }
shot sign_registration 1200,300 "sign|OPD REGISTRATION|ओपीडी पंजीकरण|#1f4e8c|Counters 1–4 · काउंटर 1–4|✚"
shot sign_radiology 1200,300 "sign|RADIOLOGY|रेडियोलॉजी|#5b3a9e|X-Ray · CT · MRI|☢"
shot sign_pharmacy 1200,300 "sign|PHARMACY|फार्मेसी|#1d7a4a|Free medicines · निःशुल्क दवा|℞"
shot sign_lab 1200,300 "sign|LABORATORY|प्रयोगशाला|#9a6512|Blood test · खून की जाँच|⚗"
shot sign_emergency 1200,300 "sign|EMERGENCY|आपातकालीन|#c0392b|24 × 7|✚"
shot sign_wards 1200,300 "sign|WARDS & LIFT|वार्ड और लिफ्ट|#5d4037|Wards 1–6 · Lift →|⇅"
shot sign_entrance 1200,300 "sign|DISTRICT HOSPITAL · OPD|जिला अस्पताल · ओपीडी|#0f6b5c|Entrance · प्रवेश|⌂"
shot token 800,400 "token|A-047|||Counter 3|"
shot poster_hands 600,800 "poster|Wash your hands|हाथ धोएं||||🧼"
shot poster_left 600,800 "poster|Keep left|बाएँ चलें||||⬅"
shot caution_wet 600,900 "caution|||||"
ls -la $R/textures
