#!/usr/bin/env bash
# ============================================================
# 아이 모드 PIN API 실측 (2026-08-07)
#   사용: npx wrangler dev --port 8788 --local 을 띄워 두고
#         bash scripts/test_childmode_pin.sh
#
# 왜 스크립트로 두나 — PIN 은 «틀린 횟수»가 상태다. 손으로 누르면 5번 틀리는
# 시점을 매번 다시 만들어야 하고, 잠금이 걸린 뒤에는 5분을 기다려야 한다.
# 잠금 해제는 DB 를 직접 되돌려서 한다(아래 unlock).
# ============================================================
set -u
BASE="${BASE:-http://127.0.0.1:8788}"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  ❌ $1"; echo "     받은 것: $2"; }
# $1 설명 / $2 응답 / $3 이 문자열이 들어 있어야 통과
want() { case "$2" in *"$3"*) ok "$1";; *) bad "$1" "$2";; esac; }

api() { # method path body
  curl -s -X "$1" "$BASE/api/v1$2" \
    -H "Content-Type: application/json" \
    ${TOKEN:+-H "Authorization: Bearer $TOKEN"} \
    ${3:+-d "$3"}
}

unlock() { # 잠금·실패횟수만 되돌린다(테스트를 이어 가려고)
  npx wrangler d1 execute eduthink-db --local \
    --command "UPDATE child_mode_config SET fail_count=0, locked_until=NULL" >/dev/null 2>&1
}

echo "── 준비: 시험용 부모 계정 만들기 ────────────────────────"
SUF=$(date +%s | tail -c 7)
REG=$(curl -s -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json" -d "{
  \"login_id\":\"pintest$SUF\",\"password\":\"testpass123\",\"name\":\"핀시험\",
  \"birth_ymd\":\"19900101\",\"email\":\"pintest$SUF@example.com\",
  \"agree_terms\":true,\"agree_privacy\":true}")
TOKEN=$(echo "$REG" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then echo "가입 실패 — 응답: $REG"; exit 1; fi
echo "  토큰 확보 (${#TOKEN}자)"

echo
echo "── ① PIN 걸기 전 ───────────────────────────────────────"
want "PIN 없음으로 나온다"            "$(api GET /child-mode)" '"has_pin":0'
want "PIN 없으면 검증은 그냥 통과"     "$(api POST /child-mode/pin/verify '{"pin":"0000"}')" '"has_pin":0'

echo
echo "── ② 쉬운 번호 막기 ────────────────────────────────────"
want "1111 거부"                      "$(api POST /child-mode/pin '{"pin":"1111"}')" 'VALIDATION'
want "1234 거부"                      "$(api POST /child-mode/pin '{"pin":"1234"}')" 'VALIDATION'
want "4321 거부"                      "$(api POST /child-mode/pin '{"pin":"4321"}')" 'VALIDATION'
want "세 자리 거부"                    "$(api POST /child-mode/pin '{"pin":"831"}')" 'VALIDATION'
want "숫자 아님 거부"                  "$(api POST /child-mode/pin '{"pin":"83a7"}')" 'VALIDATION'

echo
echo "── ③ 정상 설정 ─────────────────────────────────────────"
want "8317 설정됨"                    "$(api POST /child-mode/pin '{"pin":"8317"}')" '"has_pin":1'
want "걸렸다고 나온다"                 "$(api GET /child-mode)" '"has_pin":1'
want "해시는 안 새어나온다"            "$(api GET /child-mode)" '"has_pin":1'
case "$(api GET /child-mode)" in *pbkdf2*) bad "해시가 응답에 들어 있다" "노출됨";; *) ok "응답에 해시 없음";; esac

echo
echo "── ④ 검증 ──────────────────────────────────────────────"
want "맞는 번호 통과"                  "$(api POST /child-mode/pin/verify '{"pin":"8317"}')" '"ok":1'
want "틀린 번호 거부 · 남은 4회"        "$(api POST /child-mode/pin/verify '{"pin":"8318"}')" '"left":4'
want "맞히면 횟수 초기화"              "$(api POST /child-mode/pin/verify '{"pin":"8317"}')" '"ok":1'
want "초기화 확인 · 다시 남은 4회"      "$(api POST /child-mode/pin/verify '{"pin":"8318"}')" '"left":4'

echo
echo "── ⑤ 5번 틀리면 잠근다 ─────────────────────────────────"
api POST /child-mode/pin/verify '{"pin":"0001"}' >/dev/null   # 2
api POST /child-mode/pin/verify '{"pin":"0002"}' >/dev/null   # 3
api POST /child-mode/pin/verify '{"pin":"0003"}' >/dev/null   # 4
want "5번째에 잠긴다"                  "$(api POST /child-mode/pin/verify '{"pin":"0004"}')" 'LIMIT_EXCEEDED'
want "잠긴 동안엔 **맞아도** 안 열린다" "$(api POST /child-mode/pin/verify '{"pin":"8317"}')" 'LIMIT_EXCEEDED'
want "잠긴 동안 지우기도 막힌다"        "$(api DELETE /child-mode/pin '{"pin":"8317"}')" 'LIMIT_EXCEEDED'
want "잠금 상태가 조회에도 보인다"      "$(api GET /child-mode)" '"has_pin":1'
unlock

echo
echo "── ⑥ 바꾸기 · 지우기 ───────────────────────────────────"
want "지금 번호 없이 바꾸기 거부"       "$(api POST /child-mode/pin '{"pin":"5926"}')" 'FORBIDDEN'
want "지금 번호 틀리면 거부"           "$(api POST /child-mode/pin '{"pin":"5926","current_pin":"0000"}')" 'FORBIDDEN'
want "지금 번호 맞으면 바뀐다"         "$(api POST /child-mode/pin '{"pin":"5926","current_pin":"8317"}')" '"has_pin":1'
want "새 번호로 통과"                  "$(api POST /child-mode/pin/verify '{"pin":"5926"}')" '"ok":1'
want "옛 번호는 막힌다"                "$(api POST /child-mode/pin/verify '{"pin":"8317"}')" '"left":4'
unlock
want "틀린 번호로는 못 지운다"         "$(api DELETE /child-mode/pin '{"pin":"0000"}')" 'FORBIDDEN'
want "맞는 번호로 지워진다"            "$(api DELETE /child-mode/pin '{"pin":"5926"}')" '"has_pin":0'
want "지운 뒤 PIN 없음"                "$(api GET /child-mode)" '"has_pin":0'

echo
echo "── ⑦ 남의 접근 ─────────────────────────────────────────"
SAVED="$TOKEN"; TOKEN=""
want "토큰 없이 조회 거부"             "$(api GET /child-mode)" 'AUTH_REQUIRED'
want "토큰 없이 설정 거부"             "$(api POST /child-mode/pin '{"pin":"8317"}')" 'AUTH_REQUIRED'
TOKEN="$SAVED"

echo
echo "════════════════════════════════════════════════════════"
echo "  통과 $PASS · 실패 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
