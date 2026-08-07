#!/usr/bin/env bash
# ============================================================
# 로컬 D1 되살리기 — 원격 스키마를 그대로 복제 (2026-08-07)
#
#   bash scripts/reset_local_db.sh
#
# 왜 «마이그레이션 다시 붓기»가 아닌가  ← 2026-08-07 실측으로 알아낸 것
#   scripts/migrate_*.sql 은 **전부 기존 표를 고치는 파일**이다. 기반 스키마가 아니다.
#   빈 DB 에 날짜순으로 부어 봤더니 첫 파일(migrate_prod_2026-07-17)부터
#   `no such table: personal_events` 로 죽었고, 24개 중 11개가 같은 이유로 실패했다.
#   기반은 프로젝트 루트의 `schema.sql` 인데 **07-18 판이라 표가 26개뿐**이다
#   (원격은 61개). 그래서 그걸 쓰지 않고 **원격에서 현재 모양을 그대로 받아온다.**
#
# 🔴 schema.sql 은 git 에 없다 — `.gitignore:39` 의 `*.sql` 이 통째로 막고 있다.
#    (migrate_*.sql·rollback_*.sql 만 예외로 풀려 있다.)
#    지금 스키마의 정본은 **원격 D1 하나뿐**이다. 이 스크립트가 뽑는 덤프를
#    주기적으로 git 에 넣어 두는 게 맞다 — 미결, 대표님 판단 대기.
#
# ⚠ 로컬 D1 파일을 **지우고** 다시 만든다. 로컬에 담아 둔 시험 데이터는 사라진다.
# ⚠ dev 서버가 떠 있으면 파일을 물고 있어 실패한다 — 먼저 내릴 것.
# ============================================================
set -u
cd "$(dirname "$0")/../workers/site-renderer" || exit 1

DUMP="${TMPDIR:-/tmp}/eduthink_schema_$(date +%Y%m%d_%H%M%S).sql"

echo "① 원격 스키마 받아오기 (데이터 없이)"
npx wrangler d1 export eduthink-db --remote --no-data --output "$DUMP" >/dev/null 2>&1
if [ ! -s "$DUMP" ]; then echo "   ❌ 받지 못했습니다."; exit 1; fi
echo "   ✅ 표 $(grep -c 'CREATE TABLE' "$DUMP") 개"

echo "② 로컬 D1 지우기"
D1DIR=".wrangler/state/v3/d1/miniflare-D1DatabaseObject"
if [ -d "$D1DIR" ]; then
  # metadata.sqlite 는 miniflare 것이라 남긴다. 우리 DB 파일만 지운다.
  find "$D1DIR" -name '*.sqlite*' ! -name 'metadata.sqlite*' -delete 2>/dev/null
fi
echo "   ✅"

echo "③ 스키마 붓기"
OUT=$(npx wrangler d1 execute eduthink-db --local --file="$DUMP" 2>&1)
echo "   ✅ 문장 $(echo "$OUT" | grep -c '"success": true') 개"

echo "④ 원격에 아직 없는 마이그레이션 얹기"
# 원격에 이미 적용된 것은 스키마에 들어 있으므로 다시 부으면 안 된다.
# **원격보다 앞선 것만** 여기 적는다. 원격에 적용하고 나면 이 줄을 지운다.
for f in migrate_childmode_pin_2026-08-07.sql; do
  if [ -f "../../scripts/$f" ]; then
    printf '   %-42s ' "$f"
    npx wrangler d1 execute eduthink-db --local --file="../../scripts/$f" 2>&1 \
      | grep -q '"success": true' && echo "✅" || echo "❌"
  fi
done

echo
echo "════════════════════════════════════════════════════"
npx wrangler d1 execute eduthink-db --local \
  --command "SELECT COUNT(*) n FROM sqlite_master WHERE type='table'" 2>&1 \
  | grep -A2 '"results"' | grep -oE '[0-9]+' | head -1 | xargs -I{} echo "  로컬 표 {} 개 — 준비 끝"
echo "  이제: npx wrangler dev --port 8788 --local"
