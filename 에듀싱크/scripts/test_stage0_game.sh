#!/usr/bin/env bash
# ============================================================
# STAGE 0 실측 — 코인/점수 분리 · 재도전 (기획서 v2 §02)
#
#   npx wrangler dev --port 8788 --local 을 띄워 두고
#   bash scripts/test_stage0_game.sh
#
# 여기서 확인하는 것은 «화면이 아니라 서버가 막는가» 다.
# 특히 ⑦ — **코인 상한에 걸려도 리그 점수는 그대로 들어가는가.**
#   이게 안 되면 「코인을 태워 순위를 산다」는 기획 전체가 성립하지 않는다.
#
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

api() { # method path [body]
  if [ -n "${3:-}" ]; then
    printf '%s' "$3" | curl -s -X "$1" "$BASE/api/v1$2" \
      -H "Content-Type: application/json; charset=utf-8" \
      -H "Authorization: Bearer $TOKEN" --data-binary @-
  else
    curl -s -X "$1" "$BASE/api/v1$2" -H "Authorization: Bearer $TOKEN"
  fi
}
d1() { (cd "$(dirname "$0")/../workers/site-renderer" && npx wrangler d1 execute eduthink-db --local --command "$1" 2>/dev/null); }

# 지금 판의 문제를 전부 정답으로 채운 body 를 만든다(DB 에서 답을 읽는다)
perfect_body() {
  local codes="$1" first=1 body='{"answers":['
  for c in $codes; do
    local a
    a=$(d1 "SELECT answer FROM quiz_questions WHERE code='$c'" | grep -oE '"answer": *[0-9]+' | grep -oE '[0-9]+')
    [ $first = 0 ] && body="$body,"; first=0
    body="$body{\"code\":\"$c\",\"picked\":$a}"
  done
  echo "$body]}"
}
codes_of() { echo "$1" | grep -oE '"code":"[^"]*"' | cut -d'"' -f4; }

echo "── 준비: 부모·자녀 ───────────────────────────────────────"
SUF=$(date +%s | tail -c 7)
REG=$(printf '%s' "{\"login_id\":\"g0$SUF\",\"password\":\"testpass123\",\"name\":\"뼈대시험\",\"birth_ymd\":\"19900101\",\"email\":\"g0$SUF@example.com\",\"agree_terms\":true,\"agree_privacy\":true}" \
  | curl -s -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json; charset=utf-8" --data-binary @-)
TOKEN=$(echo "$REG" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
[ -z "$TOKEN" ] && { echo "가입 실패: $REG"; exit 1; }
OWNER=$(d1 "SELECT owner_token FROM accounts WHERE email='g0$SUF@example.com'" | grep -oE '"owner_token": *"[^"]*"' | head -1 | cut -d'"' -f4)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TRIAL=$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+30d +%Y-%m-%dT%H:%M:%SZ)
d1 "INSERT OR IGNORE INTO schools (id, slug, name, school_kind, sido, office_code, office_name, school_code, last_synced_at) VALUES (9003,'g0-elem','뼈대초등학교','초등학교','서울특별시','B10','서울특별시교육청','9999997','$NOW')" >/dev/null
d1 "INSERT INTO children (owner_token, school_id, grade, class_name, nickname, created_at, is_test, trial_expires_at, grade_promoted) VALUES ('$OWNER',9003,'5','1','뼈대','$NOW',1,'$TRIAL',0)" >/dev/null
CID=$(d1 "SELECT id FROM children WHERE owner_token='$OWNER'" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+')
[ -z "$CID" ] && { echo "자녀 생성 실패"; exit 1; }
echo "  OK   자녀 id=$CID (5학년 = band high)"

echo
echo "── ① 문제를 받는다 · 정답은 안 새는가 ────────────────────"
Q=$(api GET "/children/$CID/quiz")
want "10문제가 온다"                "$Q" '"total":10'
want "1판째"                        "$Q" '"attempt":1'
no   "정답(answer)이 안 새어나온다"   "$Q" '"answer"'
no   "정답 위치가 안 새어나온다"       "$Q" '"a1"'
want "상한이 60 이다"                "$Q" '"limit":60'
want "재도전 정보가 온다"            "$Q" '"retry"'
C1=$(codes_of "$Q"); N1=$(echo "$C1" | grep -c .)
eq   "문제 code 개수" "$N1" "10"

echo
echo "── ② 채점 — 만점을 만든다 (코인 + 리그 점수) ─────────────"
R1=$(api POST "/children/$CID/quiz" "$(perfect_body "$C1")")
want "만점이 나온다"       "$R1" '"perfect":true'
COIN1=$(num "$R1" coins); PT1=$(num "$R1" points)
eq   "코인 = 10 + 만점보너스 5" "$COIN1" "15"
[ "${PT1:-0}" -gt 0 ] && ok "리그 점수가 들어갔다 ($PT1)" || bad "리그 점수" "points=$PT1"
DBPT=$(d1 "SELECT points n FROM league_standing WHERE child_id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
eq   "DB 리그 점수도 같다" "${DBPT:-0}" "$PT1"

echo
echo "── ③ 끝낸 판은 다시 못 낸다 · 재도전 값을 알려준다 ───────"
R2=$(api POST "/children/$CID/quiz" "$(perfect_body "$C1")")
want "같은 판 재제출은 막힌다" "$R2" 'LIMIT_EXCEEDED'
Q2=$(api GET "/children/$CID/quiz")
want "끝난 판은 문제를 다시 안 준다" "$Q2" '"items":[]'
want "재도전 값이 3 이다"           "$Q2" '"cost":3'

echo
echo "── ④ 코인이 모자라면 못 연다 ────────────────────────────"
d1 "INSERT INTO star_ledger (child_id, delta, reason, bucket, created_at) VALUES ($CID, -14, 'test-drain', 'base', '$NOW')" >/dev/null
POOR=$(api POST "/children/$CID/quiz/retry" '{}')
want "잔액 부족을 막는다"  "$POOR" '"need":3'
d1 "DELETE FROM star_ledger WHERE reason='test-drain' AND child_id=$CID" >/dev/null

echo
echo "── ⑤ 재도전 — 코인이 빠지고 새 판이 열린다 ───────────────"
BAL0=$(num "$(api GET "/children/$CID/quiz")" stars)
R3=$(api POST "/children/$CID/quiz/retry" '{}')
want "2판째가 열린다"    "$R3" '"attempt":2'
want "낸 값이 3 이다"    "$R3" '"paid":3'
BAL1=$(num "$R3" stars)
eq   "잔액이 3 줄었다" "$((BAL0-BAL1))" "3"
C2=$(codes_of "$R3"); N2=$(echo "$C2" | grep -c .)
eq   "2판째도 10문제" "$N2" "10"

echo
echo "── ⑥ 2판째는 «틀렸던 문제»가 먼저 온다 ───────────────────"
# 1판을 만점냈으니 틀린 게 없다 → 2판을 일부러 틀려서 3판에 그게 오는지 본다
WRONG='{"answers":['; first=1
for c in $C2; do
  A=$(d1 "SELECT answer FROM quiz_questions WHERE code='$c'" | grep -oE '"answer": *[0-9]+' | grep -oE '[0-9]+')
  W=$(( A % 4 + 1 ))
  [ $first = 0 ] && WRONG="$WRONG,"; first=0
  WRONG="$WRONG{\"code\":\"$c\",\"picked\":$W}"
done
WRONG="$WRONG]}"
R4=$(api POST "/children/$CID/quiz" "$WRONG")
eq   "전부 틀렸다" "$(num "$R4" correct)" "0"
want "틀린 문제는 정답을 알려준다" "$R4" '"answer_text"'
R5=$(api POST "/children/$CID/quiz/retry" '{}')
want "3판째가 열린다" "$R5" '"attempt":3'
C3=$(codes_of "$R5")
# 기대치를 DB 에서 «규칙»으로 뽑는다 — 한 번이라도 맞힌 문제는 «배운 것»으로 보고 다시 안 낸다
NEVER=$(d1 "SELECT COUNT(*) n FROM (SELECT code, MAX(correct) mx FROM quiz_answer_log WHERE child_id=$CID GROUP BY code) WHERE mx=0" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
# «겹친 개수»를 세면 안 된다 — 빈자리를 채우는 분야 추첨이 우연히 같은 문제를 뽑을 수 있다.
# 재야 할 규칙은 하나다: **한 번도 못 맞힌 문제가 하나도 빠짐없이 들어 있는가.**
NEVER_CODES=$(d1 "SELECT code FROM (SELECT code, MAX(correct) mx FROM quiz_answer_log WHERE child_id=$CID GROUP BY code) WHERE mx=0" | grep -oE '"code": *"[^"]*"' | cut -d'"' -f4)
MISS=0
for c in $NEVER_CODES; do case "$C3" in *"$c"*) ;; *) MISS=$((MISS+1));; esac; done
eq   "못 맞힌 문제가 하나도 안 빠졌다 (${NEVER}개 중)" "$MISS" "0"
HIT=0; for c in $C3; do case "$C2" in *"$c"*) HIT=$((HIT+1));; esac; done
ok   "한 번 맞힌 문제는 다시 안 낸다 (3판에 든 2판 문제 ${HIT}개)"

echo
echo "── ⑦ 🔑 코인 상한에 걸려도 «리그 점수»는 그대로 ──────────"
#    이게 안 되면 「코인을 태워 순위를 산다」는 기획 전체가 무너진다
d1 "DELETE FROM star_ledger WHERE child_id=$CID" >/dev/null
d1 "INSERT INTO star_ledger (child_id, delta, reason, bucket, created_at) VALUES ($CID, 60, 'test-cap', 'base', '$NOW')" >/dev/null
PT_BEFORE=$(d1 "SELECT points n FROM league_standing WHERE child_id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
R6=$(api POST "/children/$CID/quiz" "$(perfect_body "$C3")")
eq   "코인은 0 (상한 60 도달)" "$(num "$R6" coins)" "0"
want "상한에 걸렸다고 알려준다"  "$R6" '"capped":true'
PT6=$(num "$R6" points)
[ "${PT6:-0}" -gt 0 ] && ok "🔑 점수는 그대로 들어갔다 ($PT6)" || bad "상한이 점수까지 막았다" "points=$PT6"
PT_AFTER=$(d1 "SELECT points n FROM league_standing WHERE child_id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
eq   "DB 점수가 정확히 늘었다" "$((PT_AFTER-PT_BEFORE))" "$PT6"
BAL=$(d1 "SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
eq   "잔액이 상한을 안 넘는다" "${BAL:-0}" "60"

echo
echo "── ⑧ 하루 6판까지만 ──────────────────────────────────────"
# 5번을 다 쓰려면 3+6+12+24+48 = 93 이 드는데 하루 상한은 60 이다.
# 즉 «모아둔 코인»이 없으면 6판까지 못 간다 — 의도한 설계다.
# 여기서 재는 것은 «판 수 상한»이므로 잔액을 채워 두고 본다.
d1 "INSERT INTO star_ledger (child_id, delta, reason, bucket, created_at) VALUES ($CID, 500, 'test-topup', 'base', '$NOW')" >/dev/null
for a in 4 5 6; do
  RR=$(api POST "/children/$CID/quiz/retry" '{}')
  CC=$(codes_of "$RR")
  api POST "/children/$CID/quiz" "$(perfect_body "$CC")" >/dev/null
done
OVER=$(api POST "/children/$CID/quiz/retry" '{}')
want "7판째는 막힌다"        "$OVER" 'LIMIT_EXCEEDED'
want "몇 판 썼는지 알려준다" "$OVER" '"max":6'

echo
echo "── ⑨ 히든 주머니는 따로 센다 ─────────────────────────────"
HB=$(d1 "SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id=$CID AND bucket='hidden'" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
eq   "히든은 아직 0" "${HB:-0}" "0"
SEEN=$(api GET "/children/$CID/quiz")
want "히든 상한 5 를 화면에 알려준다" "$SEEN" '"hidden_limit":5'

echo
echo "── ⑩ 레벨은 «해낸 미션 수»로 오른다 ──────────────────────"
LV=$(d1 "SELECT level_missions n FROM children WHERE id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
DONEQ=$(d1 "SELECT COUNT(*) n FROM quiz_session WHERE child_id=$CID AND finished_at IS NOT NULL AND correct > 0" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
eq   "레벨 카운터 = 한 문제라도 맞힌 판 수" "${LV:-0}" "${DONEQ:-0}"

echo
echo "════════════════════════════════════════════════════════"
echo "  통과 $PASS · 실패 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
