#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  QA 데이터 정리 (2026-07-24) — 회신22 "QA 정리 GO"
#
#  사용법:   bash qa_cleanup_2026-07-24.sh <base_url> <admin_pw> <local|remote> [--apply]
#  예:       bash qa_cleanup_2026-07-24.sh http://127.0.0.1:8788 <pw> remote          # 드라이런
#            bash qa_cleanup_2026-07-24.sh http://127.0.0.1:8788 <pw> remote --apply  # 실행
#
#  🔴 --apply 없이는 아무것도 지우지 않는다. 세기만 한다.
#
#  ── base_url과 DB 대상을 왜 따로 받는가 (2026-07-24, 실행 직전에 걸렀다) ──
#  원격 데이터를 정리할 때 **배포된 워커(workers.dev)에 요청하면 안 된다.**
#  거기엔 오늘 고친 연쇄가 안 올라가 있다 — `orders.child_id` de-link이 없어서
#  **주문이 달린 자녀에서 FOREIGN KEY 500이 나고 정리가 중간에 멈춘다.**
#  올바른 조합은 **로컬 dev 서버(`wrangler dev --remote`) + 원격 D1**이다:
#  코드는 지금 것, 데이터는 진짜 것. 그래서 base_url(로컬 8788)과 DB 대상(remote)을 따로 받는다.
#
#  ── 왜 SQL로 한 방에 안 지우는가 ──────────────────────────────────
#  자녀에 딸린 기록은 R2에 원본+썸네일이 있다. `DELETE FROM children`만 돌리면
#  **R2에 아이 사진이 영구히 남는다**(D1에서 image_key를 잃어 복구 경로도 사라진다).
#  그래서 자녀는 반드시 admin 연쇄 삭제 엔드포인트를 태운다 → deleteChildCascade()가
#  R2를 먼저 지운다. 계정 껍데기(users·accounts·auth_methods·free_trials)만 SQL로 정리한다.
#  이게 ①에서 단일 진입점을 만든 이유 그 자체다.
# ════════════════════════════════════════════════════════════════════
set -u
BASE="${1:?base_url 필요 (예: http://127.0.0.1:8788)}"
PW="${2:?admin_password 필요}"
DB_TARGET="${3:?DB 대상 필요: local | remote}"
APPLY="${4:-}"
case "$DB_TARGET" in
  local)  REMOTE_FLAG="--local" ;;
  remote) REMOTE_FLAG="--remote" ;;
  *) echo "DB 대상은 local 또는 remote여야 합니다 (받은 값: $DB_TARGET)"; exit 1 ;;
esac
# 배포 워커로 원격을 정리하려는 조합을 막는다(위 주석의 이유).
case "$BASE" in *workers.dev*) echo "🚫 배포 워커(workers.dev)로는 정리하지 마세요 — 옛 연쇄 코드라 FK 500이 납니다."; exit 1 ;; esac

# 이 스크립트는 workers/site-renderer 에서 wrangler를 부른다
cd "$(dirname "$0")/../workers/site-renderer" || exit 1

# 여러 줄 SQL을 그대로 넘기면 wrangler가 삼키는 경우가 있어 한 줄로 눌러서 보낸다.
d1() { npx wrangler d1 execute eduthink-db $REMOTE_FLAG --command "$(printf '%s' "$1" | tr '\n' ' ')" 2>&1; }

# ── 정리 대상 owner_token (명시 목록) ─────────────────────────────
# 와일드카드(LIKE 'qa-%')를 안 쓴다 — 운영 DB에서 패턴 삭제는 오폭이 조용히 일어난다.
# 근거: 카카오 닉네임이 "QA계정"인 users 12건 + qa-* 시딩 4건 + 고아 쿠키 3건.
QA_TOKENS=(
  # 소셜 닉네임 "QA계정" — 블록1·5 검수 때 만든 계정들(기록 74건이 전부 여기 있다)
  203a45a2-38c3-47ab-bdc3-000a35c30e92
  349559c5-7bec-4a42-9d7f-e32ddaa7b978
  466cb9ac-7412-4e2f-b173-10899e2f3ccc
  6239cd42-072e-460d-a089-9eeb0428b446
  6829d301-dc4e-4061-a1e5-aa72e68eb037
  82f362b1-1d92-4606-97bd-6b65f8515f28
  8760c938-4294-4865-9114-aa20b3ca54e4
  88bd85c9-ff7d-44b7-9fd5-f63ac34bc8dc
  89db231c-6814-4cb4-8cb6-0caa5fc85143
  baa4e4ad-3806-4312-b50f-f80275c369f4
  cbdd8e24-0d40-4d17-be6d-5dc246a104f6
  f28c33f7-6d00-4e6e-a229-8a950814a813
  # 2026-07-17 QA 시딩 스크립트(seed_qa_accounts.sql)가 만든 계정
  qa-free-1
  qa-paid-1
  qa-paid-2
  qa-paid-3
  # 소셜 로그인 없이 쿠키만으로 만들어진 초기 테스트 — 별명이 "QA테스트"·"때윤"(4중복)·"마라픽"
  5eafc5b1-796d-4a00-bbfe-e03d0acd4a09
  ed6875b5-276b-464d-8164-0614aceeac4d
  d02a9c79-b2f7-4954-9c06-7b5cf0730848
  # ── 클린 슬레이트 확정(2026-07-24, 대표님 "다 지우고 다시 해") ──
  # 처음엔 실명 닉네임이라 보류했던 두 계정. 함께 지운다.
  3d59d82e-2e76-43aa-8d0d-6f9bb12dd639   # kakao "현준"  — 자녀 2(마라픽·555), payments 2건도 이 토큰
  4f58dd08-60a3-4f7c-bd83-c3c1351f42ae   # google "김현준" — 자녀 1(태윤)
)

# 보존: schools · meals · timetables · academic_schedules 등 **수집 데이터 전부**.
# 지우는 건 사용자가 만든 것뿐이다.
#
# beta_feedback도 클린 슬레이트에 포함(대표님 지시). 지우기 전 내용을 찍어 로그에 남긴다 —
# 실측 결과 1건이고 내용은 `__WRITE_TEST__쓰기확인`(2026-07-18), 실제 의견이 아니라 쓰기 점검이었다.

IN_LIST=$(printf "'%s'," "${QA_TOKENS[@]}"); IN_LIST="${IN_LIST%,}"

echo "═══ 대상: ${#QA_TOKENS[@]}개 owner_token  (DB: $REMOTE_FLAG) ═══"
echo ""
echo "── 삭제 전 ──"
# ⚠️ 서브쿼리를 한 SELECT에 몰아넣지 말 것. 토큰 21개 × IN 목록이 곱해지면 명령 문자열이
#    너무 길어져 **wrangler가 조용히 아무것도 출력하지 않는다**(에러도 안 뜬다, 2026-07-24 실측).
#    나눠서 물어본다.
d1 "SELECT (SELECT COUNT(*) FROM children WHERE owner_token IN ($IN_LIST)) children,
          (SELECT COUNT(*) FROM records WHERE child_id IN (SELECT id FROM children WHERE owner_token IN ($IN_LIST))) records_R2,
          (SELECT COUNT(*) FROM activity_schedules WHERE child_id IN (SELECT id FROM children WHERE owner_token IN ($IN_LIST))) activities;" \
  | sed -n '/results/,/]/p'
d1 "SELECT (SELECT COUNT(*) FROM users WHERE owner_token IN ($IN_LIST)) users,
          (SELECT COUNT(*) FROM accounts WHERE owner_token IN ($IN_LIST)) accounts,
          (SELECT COUNT(*) FROM free_trials WHERE owner_token IN ($IN_LIST)) free_trials,
          (SELECT COUNT(*) FROM payments WHERE owner_token IN ($IN_LIST)) payments;" \
  | sed -n '/results/,/]/p'

echo ""
echo "── beta_feedback 전문 (지우기 전 기록으로 남긴다) ──"
d1 "SELECT id, category, message, status, created_at FROM beta_feedback;" | sed -n '/results/,/]/p'

if [ "$APPLY" != "--apply" ]; then
  echo ""
  echo "🔎 드라이런입니다. 실제로 지우려면 마지막에 --apply 를 붙이세요."
  exit 0
fi

echo ""
echo "── ① 자녀 연쇄 삭제 (admin 경로 → R2 먼저 지워진다) ──"
for t in "${QA_TOKENS[@]}"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -u "admin:$PW" \
         "$BASE/admin/members/token-delete" --data-urlencode "owner_token=$t")
  printf "  %-40s → %s\n" "${t:0:36}" "$code"
done

echo ""
echo "── ② 계정 껍데기 정리 (R2 무관, SQL) ──"
# 🔴 **한 번에 몰아 보내지 말 것.** 여러 DELETE를 하나의 --command로 묶으면 토큰 21개 IN 목록이
#    반복돼 명령이 길어지고, wrangler가 **에러도 없이 아무것도 안 하고 성공처럼 끝난다**
#    (2026-07-24 실제로 당함 — ②가 통째로 안 돌았는데 스크립트는 다음 단계로 넘어갔다).
#    한 줄씩 보내고 결과를 각각 확인한다.
#
# 순서 주의: orders → auth_methods/revoked_tokens → accounts (orders·auth_methods가
#            accounts를 NOT NULL FK로 참조하므로 부모를 먼저 지우면 FK 위반).
#
# payments·beta_feedback은 클린 슬레이트 확정으로 포함(2026-07-24 대표님 "다 지우고 다시 해").
# ⚠️ 평소 원칙(결제 이력 보존)의 **예외**다 — 베타 전 더미 2건이라 가능했다.
#    실사용자 결제가 생긴 뒤에는 payments 줄을 절대 그대로 쓰지 말 것.
ACC_SUB="SELECT id FROM accounts WHERE owner_token IN ($IN_LIST)"
STMTS=(
  "DELETE FROM orders           WHERE account_id IN ($ACC_SUB)"
  "DELETE FROM auth_methods     WHERE account_id IN ($ACC_SUB)"
  "DELETE FROM revoked_tokens   WHERE account_id IN ($ACC_SUB)"
  "DELETE FROM accounts         WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM users            WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM free_trials      WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM notif_settings   WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM push_subscriptions WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM payments         WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM info_reports     WHERE owner_token IN ($IN_LIST)"
  "DELETE FROM beta_feedback"
)
for s in "${STMTS[@]}"; do
  # 성공 판정은 "executed successfully" 문구가 아니라 **응답에 success가 있는지**로 본다 —
  # 단문/다문에 따라 wrangler 출력 문구가 달라서 문구로 재면 멀쩡한 실행을 실패로 읽는다.
  out=$(d1 "$s;")
  if echo "$out" | grep -q '"success": true'; then
    printf "  OK   %s\n" "$(echo "$s" | cut -c1-58)"
  else
    printf "  실패 %s\n" "$(echo "$s" | cut -c1-58)"
    echo "$out" | tail -3
  fi
done

echo ""
echo "── 삭제 후 — 사용자 데이터 표 **전체** 카운트 (클린 슬레이트라 전부 0이어야 함) ──"
# 대상 토큰만 세지 않는다. 클린 슬레이트가 목표이므로 **표 전체**를 센다 —
# 목록에서 빠뜨린 토큰이 있으면 여기서 0이 아닌 값으로 드러난다.
d1 "SELECT (SELECT COUNT(*) FROM children) children, (SELECT COUNT(*) FROM records) records,
          (SELECT COUNT(*) FROM identifiers) identifiers, (SELECT COUNT(*) FROM activity_schedules) activities,
          (SELECT COUNT(*) FROM users) users, (SELECT COUNT(*) FROM accounts) accounts,
          (SELECT COUNT(*) FROM auth_methods) auth_methods, (SELECT COUNT(*) FROM free_trials) free_trials,
          (SELECT COUNT(*) FROM orders) orders, (SELECT COUNT(*) FROM payments) payments,
          (SELECT COUNT(*) FROM beta_feedback) beta_feedback, (SELECT COUNT(*) FROM community_posts) posts;" \
  | sed -n '/results/,/]/p'

echo ""
echo "── 수집 데이터는 그대로여야 한다 (여기가 줄었으면 사고다) ──"
d1 "SELECT (SELECT COUNT(*) FROM schools) schools, (SELECT COUNT(*) FROM meals) meals,
          (SELECT COUNT(*) FROM timetables) timetables, (SELECT COUNT(*) FROM academic_schedules) academic_schedules;" \
  | sed -n '/results/,/]/p'

echo ""
echo "── ③ 옛 잔재 청소 (연쇄가 이 표들을 안 잡던 시절의 고아) ──"
# 2026-07-19 이전에는 삭제 경로가 personal_events·schedule_settings 등을 안 지웠다.
# 그때 남은 고아가 실제로 있다(로컬에서 '가족여행'·'신혼여행' 2건 확인, 2026-07-16자).
# **부모가 이미 없는 행만** 지운다 — 살아 있는 자녀 데이터는 건드리지 않는다.
# ②와 같은 이유로 한 줄씩 보낸다(묶어 보내면 조용히 안 돈다).
# 순서 주의: community_reports를 community_posts보다 먼저 — post_id가 NOT NULL FK다.
ORPHANS=(
  "DELETE FROM personal_events    WHERE child_id NOT IN (SELECT id FROM children)"
  "DELETE FROM personal_schedule  WHERE child_id NOT IN (SELECT id FROM children)"
  "DELETE FROM schedule_settings  WHERE child_id NOT IN (SELECT id FROM children)"
  "DELETE FROM activity_schedules WHERE child_id NOT IN (SELECT id FROM children)"
  "DELETE FROM identifiers        WHERE child_id NOT IN (SELECT id FROM children)"
  "DELETE FROM community_reports  WHERE post_id  NOT IN (SELECT id FROM community_posts)"
  "DELETE FROM community_posts    WHERE child_id NOT IN (SELECT id FROM children)"
)
for s in "${ORPHANS[@]}"; do
  out=$(d1 "$s;")
  if echo "$out" | grep -q '"success": true'; then printf "  OK   %s\n" "$(echo "$s" | cut -c1-58)"
  else printf "  실패 %s\n" "$(echo "$s" | cut -c1-58)"; echo "$out" | tail -3; fi
done
# ⚠️ records는 여기서 건드리지 않는다 — R2 원본이 딸려 있어 SQL로 지우면 사진이 고아가 된다.
#    고아 records가 있으면 아래 점검에 잡히고, 그건 별도로 R2까지 함께 처리해야 한다.

echo ""
echo "── 고아 점검 (자녀 없는 잔재가 남았는지) ──"
d1 "SELECT (SELECT COUNT(*) FROM records r LEFT JOIN children c ON c.id=r.child_id WHERE c.id IS NULL) orphan_records,
          (SELECT COUNT(*) FROM identifiers i LEFT JOIN children c ON c.id=i.child_id WHERE c.id IS NULL) orphan_identifiers,
          (SELECT COUNT(*) FROM activity_schedules a LEFT JOIN children c ON c.id=a.child_id WHERE c.id IS NULL) orphan_activities,
          (SELECT COUNT(*) FROM personal_events p LEFT JOIN children c ON c.id=p.child_id WHERE c.id IS NULL) orphan_events;" \
  | sed -n '/results/,/]/p'
