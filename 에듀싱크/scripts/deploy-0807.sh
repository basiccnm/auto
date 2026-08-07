#!/usr/bin/env bash
# 보상 시스템 배포 (지시서 0807) — PC 에서 한 번에 돌린다.
#   bash scripts/deploy-0807.sh          미리보기(아무것도 안 바꾼다)
#   bash scripts/deploy-0807.sh --apply  실제 적용
#
# 🔴 코드탭 컨테이너에서는 못 돈다 — Cloudflare 자격증명이 없다.
# ⚠ 순서 A(DB) → B(워커) 는 바꾸지 말 것. 워커가 먼저 나가면 아직 없는 표를 찾아 500 이 난다.
set -euo pipefail
cd "$(dirname "$0")/.."

CFG="workers/site-renderer/wrangler.toml"
DB="eduthink-db"
WORKER="eduthink-site-renderer"        # 🔴 배포 대상. olmanama 이 아니다(07-21 오배포 사고)
APPLY="${1:-}"
d1() { npx wrangler d1 execute "$DB" --remote --config "$CFG" "$@"; }
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

TABLES="'store_items','reward_orders','child_mode_config','reactions','mission_verifications','parent_mission_templates'"

say "0. 지금 상태"
d1 --command "SELECT name FROM sqlite_master WHERE type='table' AND name IN ($TABLES)" || true

if [ "$APPLY" != "--apply" ]; then
  cat <<'MSG'

미리보기만 했다. 실제로 적용하려면:
    bash scripts/deploy-0807.sh --apply

적용될 것
  A. DB  migrate_reward_2026-08-07.sql  (표 6 · 인덱스 7 · orders 확장 2)
         migrate_pin_2026-08-07.sql     (PIN 시도제한 2컬럼)
  B. 워커 eduthink-site-renderer        (보상 13 + PIN 3 + 리롤 1 라우트)
  C. APK  는 따로 — docs/배포점검-0807-보상시스템.md 의 C 단계
MSG
  exit 0
fi

say "A-1. 표·인덱스 (추가만 한다)"
d1 --file scripts/migrate_reward_2026-08-07.sql

say "A-2. PIN 시도 제한 (A-1 이 child_mode_config 를 만든 뒤라야 한다)"
d1 --file scripts/migrate_pin_2026-08-07.sql

say "A-3. 확인 — 6 이 나와야 한다"
d1 --command "SELECT COUNT(*) AS tables FROM sqlite_master WHERE type='table' AND name IN ($TABLES)"

say "B. 워커 배포"
# ⚠ --config 를 빼면 엉뚱한 워커로 나간다(올마나마에서 실제로 났던 사고)
out=$(npx wrangler deploy --config "$CFG" 2>&1 | tee /dev/stderr)
if ! grep -q "$WORKER" <<<"$out"; then
  echo; echo "🔴 출력에 '$WORKER' 가 없다 — 엉뚱한 워커로 나갔을 수 있다. 확인할 것." >&2
  exit 1
fi

say "B-2. 라우트가 살아 있나 (AUTH_REQUIRED 가 나와야 정상 · 404 면 화이트리스트를 볼 것)"
url=$(grep -oE 'https://[a-z0-9.-]*workers\.dev' <<<"$out" | head -1)
[ -n "$url" ] && curl -s "$url/api/v1/child-mode/pin" | head -c 200 || echo "(주소를 못 읽었다 — 손으로 확인)"

cat <<'MSG'


✅ A·B 끝. 다음은 C(APK) — 화면은 APK 안에 들어 있어서 이걸 해야 새 화면이 나온다.

    export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"
    cd app/android && ./gradlew assembleDebug
    adb install -r "$LOCALAPPDATA/eduthink-build/android/app/outputs/apk/debug/app-debug.apk"

그다음 실기기 8항목 — docs/배포점검-0807-보상시스템.md 맨 아래.
6·7 은 «되는지»가 아니라 «막히는지»를 본다(리롤 2회차 · PIN 5회 잠금).
MSG
