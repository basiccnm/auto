#!/usr/bin/env bash
# ============================================================
# 🏫 학교 미션 제공자 실측 (기획서 v2 §09)
#
#   npx wrangler dev --port 8788 --local 을 띄워 두고
#   bash scripts/test_school_missions.sh
#
# 여기서 확인하는 것 —
#   ① 「오늘 뭘 했나」를 서버가 말해 주는가 (화면이 세지 않는다)
#   ② 급식·친구·수업이 각각 ★1 을 주고, **하루 한 번**만 되는가
#   ③ 셋 다 하면 세트 보너스를 **한 번만** 주는가
#   ④ 부모는 읽을 수 있고, **보너스는 아이만** 받는가
#   ⑤ 학교가 없으면 available:false — 해외판이 이 길로 3칸이 된다
#
# ⚠ 이 시험은 **국내판 전용**이다. school_missions.js 를 빼면 통째로 404 가 정답이다.
# ⚠ 한글 본문은 표준입력으로 준다 — 윈도우는 명령줄 인자를 ANSI 로 바꿔 깨뜨린다.
# ============================================================
set -u
BASE="${BASE:-http://127.0.0.1:8788}"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  OK   $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL $1"; echo "       받은 것: ${2:0:240}"; }
want(){ case "$2" in *"$3"*) ok "$1";; *) bad "$1" "$2";; esac; }
no()  { case "$2" in *"$3"*) bad "$1" "$2";; *) ok "$1";; esac; }
eq()  { [ "$2" = "$3" ] && ok "$1 ($3)" || bad "$1" "받음=$2 기대=$3"; }
num() { echo "$1" | grep -oE "\"$2\":-?[0-9]+" | head -1 | grep -oE '\-?[0-9]+'; }

pa() { # 부모 토큰
  if [ -n "${3:-}" ]; then printf '%s' "$3" | curl -s -X "$1" "$BASE/api/v1$2" \
      -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Bearer $TOKEN" --data-binary @-
  else curl -s -X "$1" "$BASE/api/v1$2" -H "Authorization: Bearer $TOKEN"; fi
}
ka() { # 아이 토큰
  if [ -n "${3:-}" ]; then printf '%s' "$3" | curl -s -X "$1" "$BASE/api/v1$2" \
      -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Bearer $KID" --data-binary @-
  else curl -s -X "$1" "$BASE/api/v1$2" -H "Authorization: Bearer $KID"; fi
}
d1() { (cd "$(dirname "$0")/../workers/site-renderer" && npx wrangler d1 execute eduthink-db --local --command "$1" 2>/dev/null); }

echo "── 준비: 부모·자녀·아이 토큰 ────────────────────────────"
SUF=$(date +%s | tail -c 7)
REG=$(printf '%s' "{\"login_id\":\"sm$SUF\",\"password\":\"testpass123\",\"name\":\"학교시험\",\"birth_ymd\":\"19900101\",\"email\":\"sm$SUF@example.com\",\"agree_terms\":true,\"agree_privacy\":true}" \
  | curl -s -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json; charset=utf-8" --data-binary @-)
TOKEN=$(echo "$REG" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
[ -z "$TOKEN" ] && { echo "가입 실패: $REG"; exit 1; }
OWNER=$(d1 "SELECT owner_token FROM accounts WHERE email='sm$SUF@example.com'" | grep -oE '"owner_token": *"[^"]*"' | head -1 | cut -d'"' -f4)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TRIAL=$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+30d +%Y-%m-%dT%H:%M:%SZ)
d1 "INSERT OR IGNORE INTO schools (id, slug, name, school_kind, sido, office_code, office_name, school_code, last_synced_at) VALUES (9004,'sm-elem','학교시험초등학교','초등학교','서울특별시','B10','서울특별시교육청','9999996','$NOW')" >/dev/null
d1 "INSERT INTO children (owner_token, school_id, grade, class_name, nickname, created_at, is_test, trial_expires_at, grade_promoted) VALUES ('$OWNER',9004,'4','2','학교아이','$NOW',1,'$TRIAL',0)" >/dev/null
CID=$(d1 "SELECT id FROM children WHERE owner_token='$OWNER'" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+')
[ -z "$CID" ] && { echo "자녀 생성 실패"; exit 1; }
# 아이 토큰 — 연결 코드를 만들어 교환한다
LINK=$(pa POST "/children/$CID/invite" '{}')
CODE=$(echo "$LINK" | grep -oE '"code":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$CODE" ]; then
  KIDR=$(printf '%s' "{\"code\":\"$CODE\"}" | curl -s -X POST "$BASE/api/v1/auth/child-claim" -H "Content-Type: application/json; charset=utf-8" --data-binary @-)
  KID=$(echo "$KIDR" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
fi
[ -z "${KID:-}" ] && { echo "아이 토큰 발급 실패 — 연결 경로를 확인할 것"; echo "$LINK"; exit 1; }
echo "  OK   자녀 id=$CID · 아이 토큰 확보"

echo
echo "── ① 서버가 «오늘 뭘 했나»를 말해 준다 ──────────────────"
S0=$(pa GET "/children/$CID/school-missions")
want "학교가 있으니 available"  "$S0" '"available":true'
eq   "아직 0/3"                "$(num "$S0" done)" "0"
want "3개짜리다"               "$S0" '"all":3'
want "제목은 서버가 준다"       "$S0" '오늘 급식'
want "어디로 갈지도 서버가 준다" "$S0" 'childmealrate'
want "세트 보너스 값도 온다"     "$S0" '"bonus":'

echo
echo "── ② 급식·친구·수업 — 각각 ★1, 하루 한 번 ───────────────"
M1=$(ka POST "/missions/meal-rate" '{"stars":4,"items":[]}')
want "급식 ★1"        "$M1" '"got":1'
M2=$(ka POST "/missions/meal-rate" '{"stars":5,"items":[]}')
want "급식 두 번은 막힌다" "$M2" '이미'
F1=$(ka POST "/missions/play-log" '{"friends":["민서"]}')
want "친구 ★1"        "$F1" '"got":1'
J1=$(ka POST "/missions/subject-log" '{"subject":"체육"}')
want "수업 ★1"        "$J1" '"got":1'

S1=$(pa GET "/children/$CID/school-missions")
eq   "이제 3/3"       "$(num "$S1" done)" "3"
want "아직 보너스 전"  "$S1" '"bonus_taken":false'

echo
echo "── ③ 세트 보너스는 한 번만 ──────────────────────────────"
B1=$(ka POST "/children/$CID/school-missions/bonus" '{}')
G1=$(num "$B1" granted)
[ "${G1:-0}" -gt 0 ] && ok "세트 보너스를 받았다 (★$G1)" || bad "세트 보너스" "$B1"
B2=$(ka POST "/children/$CID/school-missions/bonus" '{}')
eq   "두 번째는 0"    "$(num "$B2" granted)" "0"
want "이미 받았다고 알려준다" "$B2" '"already":true'
S2=$(pa GET "/children/$CID/school-missions")
want "받았다고 표시된다" "$S2" '"bonus_taken":true'

BAL=$(d1 "SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
eq   "잔액 = 미션 3 + 보너스"  "${BAL:-0}" "$((3 + G1))"

echo
echo "── ④ 보너스는 아이만 ────────────────────────────────────"
d1 "DELETE FROM star_ledger WHERE child_id=$CID AND reason LIKE 'school-set:%'" >/dev/null
BP=$(pa POST "/children/$CID/school-missions/bonus" '{}')
want "부모가 누르면 막힌다" "$BP" 'FORBIDDEN'
SP=$(pa GET "/children/$CID/school-missions")
want "부모도 읽기는 된다"   "$SP" '"available":true'

echo
echo "── ⑤ 해외판 경로 — 이 파일을 빼면 길 자체가 사라진다 ────"
# ⚠ children.school_id 는 NOT NULL 이라 «학교 없는 아이»는 실제로 만들 수 없다.
#   그래서 해외판의 진짜 스위치는 index.js 의 import 를 빼는 것이고,
#   그때 이 경로는 **404**(HTML) 가 된다. 앱은 404 를 «카드 없음»으로 처리한다.
#   여기서는 «이 파일이 자기 경로만 잡고 나머지는 안 건드리는가»를 확인한다.
S3=$(pa GET "/children/$CID/school-missions/없는길")
no   "제 것이 아닌 경로는 안 잡는다" "$S3" '"available"'
S4=$(pa GET "/children/$CID/school-missions")
want "제 경로는 잡는다"             "$S4" '"available":true'
echo "     → 해외판은 index.js 의 school_missions import 한 줄을 빼면 된다"

echo
echo "── ⑥ 🔑 아이 폰이 게임 경로를 지나갈 수 있는가 ───────────"
#    아이 폰이 게임의 집이다. index.js 의 «자녀 토큰 관문»에 경로를 안 올리면
#    서버는 멀쩡한데 **아이 화면에서만** 「권한이 없어요」가 뜬다(2026-08-08 실측으로 잡음).
QK=$(ka GET "/children/$CID/quiz")
no   "퀴즈가 막히지 않는다"     "$QK" 'FORBIDDEN'
want "퀴즈가 열린다"            "$QK" '"total":10'
SK=$(ka GET "/children/$CID/store")
no   "상점이 막히지 않는다"     "$SK" 'FORBIDDEN'
RK=$(ka GET "/children/$CID/rewards")
no   "티켓이 막히지 않는다"     "$RK" 'FORBIDDEN'
SMK=$(ka GET "/children/$CID/school-missions")
no   "학교 미션이 막히지 않는다" "$SMK" 'FORBIDDEN'
#    반대로 «부모 것»은 아이가 못 건드려야 한다
AK=$(ka POST "/children/$CID/store" '{"title":"몰래","stars_required":1}')
want "진열대 편집은 아이가 못 한다" "$AK" 'FORBIDDEN'

echo
echo "── ⑦ 아침·방과후 세트 완주 보너스 ────────────────────────"
#    학교 세트와 «같은 규칙, 다른 파일»이다(학교는 해외판에서 통째로 빠져야 하므로).
#    ⚠ 오늘 배정된 미션이 0개면 «완주»가 아니다 — 아무것도 안 하고 먹는 길을 막는다.
MS0=$(pa GET "/children/$CID/mission-sets")
want "세트 상태가 온다"        "$MS0" '"morning"'
E0=$(ka POST "/children/$CID/mission-sets/bonus" '{"slot":"morning"}')
want "배정이 없으면 못 받는다" "$E0" '오늘은 그 세트가 없어요'
E1=$(ka POST "/children/$CID/mission-sets/bonus" '{"slot":"없는것"}')
want "없는 세트는 거절"        "$E1" '그런 세트는 없어요'

# 아침 미션 2개를 배정하고 하나만 끝낸 상태를 만든다
YMD=$(echo "$MS0" | grep -oE '"ymd":"[0-9]+"' | cut -d'"' -f4)
# 로컬 D1 에는 카탈로그가 비어 있을 수 있다 — 시험이 쓸 미션 2개를 직접 심는다
d1 "INSERT OR IGNORE INTO missions (code, band, season, title, area, minutes, cycle, verify, slot, stars, active, created_at) VALUES ('T-MORN-1','all','weekday','시험 아침미션1','body',0,'daily','self','morning',1,1,'$NOW')" >/dev/null
d1 "INSERT OR IGNORE INTO missions (code, band, season, title, area, minutes, cycle, verify, slot, stars, active, created_at) VALUES ('T-MORN-2','all','weekday','시험 아침미션2','body',0,'daily','self','morning',1,1,'$NOW')" >/dev/null
MC=$(d1 "SELECT code FROM missions WHERE slot='morning' AND active=1 LIMIT 2" | grep -oE '"code": *"[^"]*"' | cut -d'"' -f4)
i=0
for c in $MC; do
  i=$((i+1))
  d1 "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, stars, created_at) VALUES ($CID,'$c','$YMD','$([ $i = 1 ] && echo done || echo open)',1,'$NOW')" >/dev/null
done
E2=$(ka POST "/children/$CID/mission-sets/bonus" '{"slot":"morning"}')
want "덜 했으면 «몇 개 더»로 막는다" "$E2" '개 더 하면'
d1 "UPDATE mission_assign SET status='done' WHERE child_id=$CID AND ymd='$YMD'" >/dev/null
E3=$(ka POST "/children/$CID/mission-sets/bonus" '{"slot":"morning"}')
G3=$(num "$E3" granted)
[ "${G3:-0}" -gt 0 ] && ok "다 하면 세트 보너스 (★$G3)" || bad "아침 세트 보너스" "$E3"
E4=$(ka POST "/children/$CID/mission-sets/bonus" '{"slot":"morning"}')
want "두 번은 안 준다" "$E4" '"already":true'
MS1=$(pa GET "/children/$CID/mission-sets")
want "받았다고 표시된다" "$MS1" '"taken":true'

echo
echo "════════════════════════════════════════════════════════"
echo "  통과 $PASS · 실패 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
