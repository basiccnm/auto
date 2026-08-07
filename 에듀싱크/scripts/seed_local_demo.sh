#!/usr/bin/env bash
# ============================================================
# 로컬 검수용 시험 데이터 심기 (2026-08-07)
#
#   npx wrangler dev --port 8788 --local 을 띄워 두고
#   bash scripts/seed_local_demo.sh
#
# 왜 필요한가
#   새 화면(별도장 상점·내 티켓·2단계 검증)은 **데이터가 있어야 진짜 모습이 나온다.**
#   빈 상태만 보고 «됩니다»라고 하면 그건 검수가 아니다(메모리: 보고 전 반드시 검수).
#   가입 → 학교검색 → 자녀등록을 손으로 밟으면 매번 5분이라 여기서 한 번에 만든다.
#
# 만드는 것: 부모 1 · 학교 1 · 자녀 1 · 별도장 12개 · 진열대 4종 · 1차검증 2건 · 티켓 2장
# 출력: 앱에 붙여넣을 localStorage 한 줄
#
# ⚠ **--local 전용이다.** 원격에 대고 돌리지 말 것.
# ============================================================
set -u
cd "$(dirname "$0")/../workers/site-renderer" || exit 1
BASE="${BASE:-http://127.0.0.1:8788}"

d1() { npx wrangler d1 execute eduthink-db --local --command "$1" 2>&1; }
d1q() { d1 "$1" | grep -A3 '"results"' | grep -oE '"[a-z_]+": *"?[^",]*' | head -20; }

echo "① 부모 계정 만들기"
SUF=$(date +%s | tail -c 7)
REG=$(printf '%s' "{\"login_id\":\"demo$SUF\",\"password\":\"demopass123\",\"name\":\"검수부모\",\"birth_ymd\":\"19880101\",\"email\":\"demo$SUF@example.com\",\"agree_terms\":true,\"agree_privacy\":true}" \
  | curl -s -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json; charset=utf-8" --data-binary @-)
ACCESS=$(echo "$REG"  | grep -o '"access_token":"[^"]*"'  | head -1 | cut -d'"' -f4)
REFRESH=$(echo "$REG" | grep -o '"refresh_token":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$ACCESS" ]; then echo "  ❌ 가입 실패: $REG"; exit 1; fi
echo "  ✅ 토큰 확보"

# owner_token 은 응답에 없다 — 방금 만든 계정에서 직접 꺼낸다
OWNER=$(d1 "SELECT owner_token FROM accounts WHERE email='demo$SUF@example.com'" \
        | grep -oE '"owner_token": *"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$OWNER" ]; then echo "  ❌ owner_token 을 못 찾음"; exit 1; fi
echo "  ✅ owner_token ${OWNER:0:12}…"

echo "② 학교 · 자녀 심기"
NOW2=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# ⚠ schools 는 NOT NULL 이 많다 — office_code·office_name·school_code·school_kind·sido·slug·last_synced_at.
#   `kind` 가 아니라 **`school_kind`** 다(2026-08-07: 이걸 틀려 학교가 안 만들어졌고,
#   그 바람에 자녀 INSERT 가 조용히 실패했다). 빠뜨리면 여기서부터 전부 무너진다.
# ⚠ schools 는 NOT NULL 이 많다 — office_code·office_name·school_code·school_kind·sido·slug·last_synced_at.
#   `kind` 가 아니라 **`school_kind`** 다.
# ⚠ **한 줄로 쓴다.** wrangler 는 여러 줄 --command 를 «성공»이라 답하고 아무것도 안 한다(실측).
#   그래서 학교가 안 생겼고, 자녀 INSERT 가 FOREIGN KEY 로 죽었다 — 원인이 두 단계 떨어져 있어 헷갈린다.
d1 "INSERT OR IGNORE INTO schools (id, slug, name, school_kind, sido, office_code, office_name, school_code, last_synced_at) VALUES (9001, 'demo-elem', '검수초등학교', '초등학교', '서울특별시', 'B10', '서울특별시교육청', '9999999', '$NOW2')" >/dev/null
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# 체험이 넉넉히 남아 있어야 잠금 화면으로 안 떨어진다
TRIAL=$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+30d +%Y-%m-%dT%H:%M:%SZ)
d1 "DELETE FROM children WHERE owner_token='$OWNER'" >/dev/null
d1 "INSERT INTO children (owner_token, school_id, grade, class_name, nickname, created_at, is_test, trial_expires_at, grade_promoted) VALUES ('$OWNER', 9001, '2', '3', '민준', '$NOW', 1, '$TRIAL', 0)" >/dev/null
CID=$(d1 "SELECT id FROM children WHERE owner_token='$OWNER'" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+')
if [ -z "$CID" ]; then echo "  ❌ 자녀 생성 실패"; exit 1; fi
echo "  ✅ 자녀 id=$CID (민준 · 2학년)"

echo "③ 별도장 12개 (원장에 적는다 — 잔액 컬럼은 없다)"
d1 "INSERT INTO star_ledger (child_id, delta, reason, created_at) VALUES ($CID, 12, 'seed', '$NOW')" >/dev/null

echo "④ 진열대 4종"
# ⚠ **한글 본문은 `-d "$3"` 으로 넘기면 깨진다.** (2026-08-07 실측: 진열대 이름이 DB 에
#   `��ȭ 30��` 로 들어갔다.) 윈도우는 명령줄 인자를 ANSI 코드페이지로 변환해 넘기기 때문이다.
#   → **표준입력**으로 준다(`--data-binary @-`). 그러면 파일 바이트가 그대로 간다.
#   ⚠ 앱 화면이 깨져 보였을 때 앱부터 고치려 들지 말 것 — DB 에 뭐가 들었는지 먼저 볼 것.
api() { printf '%s' "$3" | curl -s -X "$1" "$BASE/api/v1$2" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "Authorization: Bearer $ACCESS" --data-binary @-; }
api POST "/children/$CID/store" '{"title":"만화 30분","stars_required":5,"limit_type":"weekly","limit_count":2}' >/dev/null
api POST "/children/$CID/store" '{"title":"아이스크림","stars_required":8}' >/dev/null
api POST "/children/$CID/store" '{"title":"주말 놀이터 1시간","stars_required":10,"limit_type":"weekly","limit_count":1}' >/dev/null
api POST "/children/$CID/store" '{"title":"장난감 사기","stars_required":40,"limit_type":"monthly","limit_count":1}' >/dev/null
echo "  ✅ 4종 (살 수 있는 것 · 모자란 것 · 상한 있는 것 섞어 뒀다)"

echo "⑤ 1차 검증 2건 — 부모 «확인해 주세요» 목록에 뜬다"
api POST "/children/$CID/verify" '{"mission_code":"문제집 5장","step1_data":"10쪽~20쪽"}' >/dev/null
api POST "/children/$CID/verify" '{"mission_code":"독서 20분","step1_data":"강아지똥 / 사진 있음"}' >/dev/null

echo "⑥ 티켓 2장 — 하나는 «기다리는 중», 하나는 «받았어요»"
B1=$(api POST "/children/$CID/store/$(api GET "/children/$CID/store" '' | grep -oE '"item_id":"[^"]*"' | head -1 | cut -d'"' -f4)/buy" '')
OID=$(echo "$B1" | grep -oE '"reward_order_id":"[^"]*"' | cut -d'"' -f4)
[ -n "$OID" ] && api POST "/rewards/$OID/fulfill" '' >/dev/null
api POST "/children/$CID/store/$(api GET "/children/$CID/store" '' | grep -oE '"item_id":"[^"]*"' | head -1 | cut -d'"' -f4)/buy" '' >/dev/null

echo
echo "════════════════════════════════════════════════════════════"
echo "  앱(8789) 콘솔에 이 한 줄을 붙여넣고 새로고침하세요:"
echo
cat <<JSEOF
localStorage.setItem('eduthink.api','$BASE');
localStorage.setItem('eduthink.tokens', JSON.stringify({access:'$ACCESS',refresh:'$REFRESH'}));
localStorage.setItem('eduthink.introSeen','1'); localStorage.setItem('eduthink.coachSeen','1');
location.reload();
JSEOF
