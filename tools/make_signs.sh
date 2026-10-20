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
shot sign_lift 1200,320 "sign|LIFT|लिफ्ट|#37474f|1st floor: Blood Bank · ICU · OT|⇅"
shot sign_floor1 900,400 "sign|1st FLOOR|पहली मंज़िल|#37474f|Blood Bank · ICU · OT · Wards|①"
shot sign_nurse 1200,300 "sign|NURSE STATION|नर्स स्टेशन|#00695c|Ask here · यहाँ पूछें|✚"
shot sign_bloodbank 1200,300 "sign|BLOOD BANK|ब्लड बैंक|#b71c1c|Donate · रक्तदान|🩸"
shot sign_icu 1200,300 "sign|ICU|आई.सी.यू.|#0d47a1|Silence please · कृपया शांति|♥"
shot sign_ot 1200,300 "sign|OPERATION THEATRE|ऑपरेशन थिएटर|#4e342e|OT 1–3 · No entry|⚕"
shot sign_stairs 1200,400 "sign|STAIRS ↓ Ground floor|सीढ़ियाँ ↓ भूतल|#455a64|OPD · Registration · Pharmacy|⇩"
shot poster_donate 600,800 "poster|Donate blood|रक्तदान करें||||🩸"
shot sign_wards2 1200,300 "sign|WARDS|वार्ड|#5d4037|Wards 1–6 · General · Female|🛏"
shot token 800,400 "token|A-047|||Counter 3|"
shot poster_hands 600,800 "poster|Wash your hands|हाथ धोएं||||🧼"
shot poster_left 600,800 "poster|Keep left|बाएँ चलें||||⬅"
shot caution_wet 600,900 "caution|||||"
ls -la $R/textures
