#!/bin/bash
# 최종 검수 몽타주 — 화면을 CDP 로 넘기고 adb 로 찍는다
ADB="C:/LDPlayer/LDPlayer14/adb.exe"
OUT="$LOCALAPPDATA/Temp/final_shots"
SCREENS="home meal timetable calendar timeline afterschool mission store tickets mypage pay notify"
i=0
for MODE in light dark; do
  # 테마 전환 — 실제 설정 함수로 (dark 는 «어둡게» 계열 대표 dark)
  cat > scripts/_set_theme.js <<JS
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  App.setTheme("${MODE}" === "dark" ? "dark" : "light");
  await wait(400);
  return document.documentElement.getAttribute("data-theme");
})();
JS
  node scripts/emul_eval.mjs --file scripts/_set_theme.js > /dev/null 2>&1
  i=0
  for SC in $SCREENS; do
    i=$((i+1))
    cat > scripts/_nav_one.js <<JS
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  location.hash = "#${SC}"; App.render(); await wait(900);
  return location.hash;
})();
JS
    node scripts/emul_eval.mjs --file scripts/_nav_one.js > /dev/null 2>&1
    "$ADB" -s emulator-5554 exec-out screencap -p > "$OUT/$MODE/$(printf %02d $i)-$SC.png" 2>/dev/null
  done
done
rm -f scripts/_set_theme.js scripts/_nav_one.js
echo "light: $(ls $OUT/light | wc -l)장 / dark: $(ls $OUT/dark | wc -l)장"
