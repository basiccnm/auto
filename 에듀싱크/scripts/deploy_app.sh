#!/usr/bin/env bash
# ============================================================
# 📲 앱 배포 한 방 — 찍고 · 옮기고 · 굽고 · **붙어 있는 폰 전부에** 넣고 · 확인까지
#
#   bash scripts/deploy_app.sh
#
# 왜 스크립트인가 (2026-08-08 실제로 두 번 겪음)
#   ① 캐시 표시(?v=)를 안 찍고 구우면 **덮어 설치해도 웹뷰가 옛 파일을 계속 쓴다.**
#      깨끗한 설치에서는 새 파일이 뜨므로 «될 때도 있고 안 될 때도 있는» 최악의 버그가 된다.
#   ② 폰이 두 대인데 **한 대에만 넣고** 「다 올렸다」고 보고했다.
#      부모 폰만 새 것이고 자녀 폰은 옛 것이었다.
#
# 그래서 마지막에 **각 폰이 실제로 물고 있는 해시**를 읽어 소스와 대조한다.
# 대조까지 통과해야 성공이다 — 「설치 Success」는 증거가 아니다.
# ============================================================
set -u
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
ADB="${ADB:-C:/LDPlayer/LDPlayer14/adb.exe}"
APK="${APK:-C:/Users/hardb/AppData/Local/eduthink-build/android/app/outputs/apk/debug/app-debug.apk}"
export JAVA_HOME="${JAVA_HOME:-C:/Program Files/Android/Android Studio/jbr}"

echo "── ① 캐시 표시를 실제 파일로 찍는다 ─────────────────────"
PYTHONUTF8=1 python scripts/stamp_cache.py || exit 1

echo
echo "── ② 웹 자산을 안드로이드로 옮긴다 ──────────────────────"
(cd app && npx cap sync android 2>&1 | tail -2) || exit 1

echo
echo "── ③ APK 를 굽는다 ─────────────────────────────────────"
(cd app/android && ./gradlew assembleDebug -q 2>&1 | tail -5)
[ -f "$APK" ] || { echo "  ❌ APK 가 없다: $APK"; exit 1; }
echo "  ✅ $(ls -la "$APK" | awk '{print $6, $7, $8}')"

echo
echo "── ④ 붙어 있는 폰 **전부** 에 넣는다 ────────────────────"
DEVS=$("$ADB" devices | awk '/device$/ {print $1}')
[ -z "$DEVS" ] && { echo "  ❌ 붙어 있는 폰이 없다"; exit 1; }
for D in $DEVS; do
  echo -n "  $D: "
  "$ADB" -s "$D" install -r "$APK" 2>&1 | tail -1
  "$ADB" -s "$D" shell am force-stop com.eduthink.app
  "$ADB" -s "$D" shell am start -n com.eduthink.app/.MainActivity >/dev/null 2>&1
done

echo
echo "── ⑤ 각 폰이 **실제로 물고 있는 것**을 소스와 대조 ──────"
sleep 12
WANT=$(PYTHONUTF8=1 python -c "
import hashlib
print(hashlib.sha1(open('app/www/app.js','rb').read()).hexdigest()[:8])")
echo "  소스: app.js?v=$WANT"
FAIL=0
PORT=9400
for D in $DEVS; do
  PORT=$((PORT+1))
  PID=$("$ADB" -s "$D" shell "cat /proc/net/unix" 2>/dev/null | grep -o "webview_devtools_remote_[0-9]*" | head -1 | grep -oE "[0-9]+$")
  if [ -z "$PID" ]; then echo "  ⚠ $D — 웹뷰를 못 찾았다(앱이 아직 안 떴나)"; FAIL=1; continue; fi
  MSYS_NO_PATHCONV=1 "$ADB" -s "$D" forward tcp:$PORT localabstract:webview_devtools_remote_$PID >/dev/null
  GOT=$(CDP_PORT=$PORT node scripts/emul_eval.mjs "[...document.scripts].map(s=>s.src).filter(x=>x.includes('app.js'))[0].split('?v=')[1]||''" 2>/dev/null | tail -1)
  if [ "$GOT" = "$WANT" ]; then echo "  ✅ $D — $GOT"; else echo "  ❌ $D — $GOT (소스와 다르다)"; FAIL=1; fi
done

echo
echo "════════════════════════════════════════════════════════"
[ "$FAIL" = "0" ] && echo "  ✅ 모든 폰이 최신을 물고 있다" || { echo "  ❌ 최신이 아닌 폰이 있다"; exit 1; }
