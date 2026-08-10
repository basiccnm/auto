#!/bin/bash
# 폰 실기 전수 스샷 + 자동 측정 (2026-08-10)
#   bash scripts/phone_sweep.sh <출력폴더> <화면...>
# ⚠ 폴드6 는 디스플레이가 둘이라 -d 로 지정해야 한다(안 하면 파일에 경고 «텍스트»가 박힌다)
# ⚠ 폰 API 응답이 ~1.5초 — 대기가 짧으면 「불러오는 중」이 찍혀 «고장»으로 오독된다
ADB="C:/LDPlayer/LDPlayer14/adb.exe"; PH="172.30.1.72:38915"; DISP=4630947194243491972
OUT="$1"; shift
mkdir -p "$OUT"; rm -f "$OUT"/*.png "$OUT"/측정.txt
i=0
for SC in "$@"; do
  i=$((i+1))
  cat > scripts/_nav_ph.js <<JS
(async () => {
  const w=(ms)=>new Promise(r=>setTimeout(r,ms));
  location.hash="#${SC}"; App.render(); await w(2600);
  const scr=document.getElementById("screen");
  const cands=[...scr.querySelectorAll("*")].filter(e=>e.offsetHeight>18 && getComputedStyle(e).position!=="fixed");
  let low=0,nm="";
  for(const e of cands){const r=e.getBoundingClientRect(); if(r.bottom>low && r.bottom<innerHeight+300){low=r.bottom;nm=(e.className||e.tagName).toString().slice(0,18);}}
  const gap=Math.round(innerHeight-low);
  const h=scr.querySelector("h1,h2,.sub-t,.gmp-top,.hv3-ham,.back");
  const top=h?Math.round(h.getBoundingClientRect().top):-999;
  const stuck=(scr.textContent||"").indexOf("불러오는 중")>=0;
  return "${SC} | 아래 "+gap+"px"+(gap<48?" 🔴":"")+" ("+nm+") | 위 "+top+"px"+(top>-900&&top<28?" 🔴":"")+(stuck?" | 🔴로딩갇힘":"");
})();
JS
  R=$(CDP_PORT=9444 node scripts/emul_eval.mjs --file scripts/_nav_ph.js 2>&1 | tail -1)
  echo "$R" >> "$OUT/측정.txt"
  "$ADB" -s $PH exec-out screencap -d $DISP -p > "$OUT/$(printf %02d $i)-$SC.png" 2>/dev/null
done
rm -f scripts/_nav_ph.js
echo "$(ls $OUT/*.png | wc -l)장"
