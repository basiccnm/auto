#!/usr/bin/env bash
# ============================================================
# 데일리 퀴즈 + 스타코인 리밋 실측 (2026-08-08) — 기획서 §02·§04
#
#   npx wrangler dev --port 8788 --local 을 띄워 두고
#   bash scripts/test_quiz_coin.sh
#
# 여기서 확인하는 것은 «화면이 아니라 서버가 막는가» 다:
#   ① 정답이 응답에 새어나오지 않는가        ← 새면 퀴즈의 존재 이유가 사라진다
#   ② 하루 한 세트가 강제되는가
#   ③ 채점이 맞는가 / 만점 보너스가 붙는가
#   ④ 리밋이 걸리면 «깎아서» 주는가(0을 주지 않는가)
#   ⑤ 리밋을 넘겨도 잔액이 안 늘어나는가
#
# ⚠ 한글 본문은 표준입력으로 준다 — 윈도우는 명령줄 인자를 ANSI 로 바꿔 깨뜨린다.
# ============================================================
set -u
BASE="${BASE:-http://127.0.0.1:8788}"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ✅ $1"; }
bad() { FAIL=$((FAIL+1)); echo "  ❌ $1"; echo "     받은 것: ${2:0:220}"; }
want(){ case "$2" in *"$3"*) ok "$1";; *) bad "$1" "$2";; esac; }
no()  { case "$2" in *"$3"*) bad "$1" "$2";; *) ok "$1";; esac; }

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

echo "── 준비: 부모·자녀 ───────────────────────────────────────"
SUF=$(date +%s | tail -c 7)
REG=$(printf '%s' "{\"login_id\":\"quiz$SUF\",\"password\":\"testpass123\",\"name\":\"퀴즈시험\",\"birth_ymd\":\"19900101\",\"email\":\"quiz$SUF@example.com\",\"agree_terms\":true,\"agree_privacy\":true}" \
  | curl -s -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json; charset=utf-8" --data-binary @-)
TOKEN=$(echo "$REG" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
[ -z "$TOKEN" ] && { echo "가입 실패: $REG"; exit 1; }
OWNER=$(d1 "SELECT owner_token FROM accounts WHERE email='quiz$SUF@example.com'" | grep -oE '"owner_token": *"[^"]*"' | head -1 | cut -d'"' -f4)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TRIAL=$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+30d +%Y-%m-%dT%H:%M:%SZ)
d1 "INSERT OR IGNORE INTO schools (id, slug, name, school_kind, sido, office_code, office_name, school_code, last_synced_at) VALUES (9002,'quiz-elem','퀴즈초등학교','초등학교','서울특별시','B10','서울특별시교육청','9999998','$NOW')" >/dev/null
d1 "INSERT INTO children (owner_token, school_id, grade, class_name, nickname, created_at, is_test, trial_expires_at, grade_promoted) VALUES ('$OWNER',9002,'3','1','퀴즈',' $NOW',1,'$TRIAL',0)" >/dev/null
CID=$(d1 "SELECT id FROM children WHERE owner_token='$OWNER'" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+')
[ -z "$CID" ] && { echo "자녀 생성 실패"; exit 1; }
echo "  ✅ 자녀 id=$CID"

echo
echo "── ① 문제를 받는다 · 정답은 안 새는가 ────────────────────"
Q=$(api GET "/children/$CID/quiz")
want "10문제가 온다"            "$Q" '"total":10'
want "문제당 5초"               "$Q" '"sec_per_q":5'
no   "정답(answer)이 안 새어나온다"  "$Q" '"answer"'
no   "정답 위치가 안 새어나온다"      "$Q" '"a1"'
CODES=$(echo "$Q" | grep -oE '"code":"[^"]*"' | cut -d'"' -f4)
CNT=$(echo "$CODES" | grep -c . )
[ "$CNT" = "10" ] && ok "문제 code 10개 확인" || bad "문제 code 수" "$CNT"

echo
echo "── ② 채점 — 전부 1번으로 찍는다 ──────────────────────────"
BODY='{"answers":['
first=1
for c in $CODES; do
  [ $first = 0 ] && BODY="$BODY,"; first=0
  BODY="$BODY{\"code\":\"$c\",\"picked\":1}"
done
BODY="$BODY]}"
R1=$(api POST "/children/$CID/quiz" "$BODY")
want "채점 결과가 온다"          "$R1" '"correct"'
want "틀린 문제는 정답을 알려준다" "$R1" '"answer_text"'
want "코인 필드가 온다"          "$R1" '"coins"'
GOT=$(echo "$R1" | grep -oE '"correct":[0-9]+' | head -1 | grep -oE '[0-9]+')
COINS=$(echo "$R1" | grep -oE '"coins":[0-9]+' | head -1 | grep -oE '[0-9]+')
echo "     → 맞힌 수 $GOT · 받은 코인 $COINS (전부 1번 찍었으니 2~3개가 정상)"
[ "$GOT" = "$COINS" ] && ok "맞힌 수 = 받은 코인" || bad "맞힌 수와 코인 불일치" "correct=$GOT coins=$COINS"

echo
echo "── ③ 하루 한 세트 ────────────────────────────────────────"
R2=$(api POST "/children/$CID/quiz" "$BODY")
want "두 번째 제출은 막힌다"     "$R2" 'LIMIT_EXCEEDED'
Q2=$(api GET "/children/$CID/quiz")
want "끝난 세트는 문제를 다시 안 준다" "$Q2" '"items":[]'
want "결과는 계속 보인다"        "$Q2" '"done":true'

echo
echo "── ④ 리밋 — 29/30 에서 5개를 벌면 1개만 ──────────────────"
d1 "DELETE FROM star_ledger WHERE child_id=$CID" >/dev/null
d1 "INSERT INTO star_ledger (child_id, delta, reason, created_at) VALUES ($CID, 29, 'test-fill', '$NOW')" >/dev/null
d1 "DELETE FROM quiz_session WHERE child_id=$CID" >/dev/null
Q3=$(api GET "/children/$CID/quiz")
C3=$(echo "$Q3" | grep -oE '"code":"[^"]*"' | cut -d'"' -f4)
# 정답을 DB 에서 읽어 만점을 만든다(리밋이 걸리는지 보려면 많이 벌어야 한다)
BODY3='{"answers":['
first=1
for c in $C3; do
  A=$(d1 "SELECT answer FROM quiz_questions WHERE code='$c'" | grep -oE '"answer": *[0-9]+' | grep -oE '[0-9]+')
  [ $first = 0 ] && BODY3="$BODY3,"; first=0
  BODY3="$BODY3{\"code\":\"$c\",\"picked\":$A}"
done
BODY3="$BODY3]}"
R3=$(api POST "/children/$CID/quiz" "$BODY3")
want "만점이 나온다"             "$R3" '"perfect":true'
want "리밋에 걸렸다고 알려준다"   "$R3" '"capped":true'
C3G=$(echo "$R3" | grep -oE '"coins":[0-9]+' | head -1 | grep -oE '[0-9]+')
[ "$C3G" = "1" ] && ok "15개를 벌 자격이지만 1개만 준다(0이 아니다)" || bad "리밋 깎기" "coins=$C3G (1이어야 함)"
BAL=$(d1 "SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id=$CID" | grep -oE '"n": *[0-9]+' | grep -oE '[0-9]+')
[ "$BAL" = "30" ] && ok "잔액이 리밋을 안 넘는다 (30)" || bad "잔액" "$BAL (30이어야 함)"

echo
echo "── ⑤ 분야별 통계(박사 뱃지 근거) ─────────────────────────"
ST=$(api GET "/children/$CID/quiz/stats")
want "분야별 정답률이 온다"      "$ST" '"rate"'
want "제일 잘하는 분야를 뽑아준다" "$ST" '"best"'

echo
echo "════════════════════════════════════════════════════════"
echo "  통과 $PASS · 실패 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
