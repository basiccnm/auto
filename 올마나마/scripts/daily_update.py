# -*- coding: utf-8 -*-
"""매일 한 번 도는 갱신 파이프라인 — 수집 → 이력기록 → 원가재계산 → 생성 → 빌드 → 검사 → 배포.

작업 스케줄러에서 `일일갱신.bat` 이 이 파일을 부른다.

설계 원칙 두 가지:
  1. **healthcheck를 통과할 때만 배포한다.** 자동 배포는 잘못된 값이 그대로 라이브로
     나가는 게 유일한 위험이라, 관문을 넘지 못하면 배포 단계를 건너뛰고 로그만 남긴다.
  2. **수집 실패는 치명적이지 않다.** 공공 API는 자주 죽는다. 한 소스가 실패해도
     나머지로 계속 간다 — 어제 값이 그대로 남을 뿐 사이트가 깨지지는 않는다.

⚠️ 배포는 반드시 `--config workers/site-renderer/wrangler.toml` 로 한다.
   빼면 루트 wrangler.jsonc(도메인 없는 워커)로 나가서 라이브에 아무것도 안 올라간다.
"""
import os, sys, io, subprocess, sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
LOG = os.path.join(BASE, "data", "daily_update.log")
PY = sys.executable

# (표시이름, 스크립트, 실패해도 계속갈지)
COLLECT = [
    ("KAMIS 농산물 시세", "collect_prices.py", True),
    ("관세청 수입육 통관단가", "collect_customs_meat.py", True),
]
BUILD = [
    ("원가 재계산", "compute_line_costs.py", False),
    ("메뉴·브랜드·홈", "gen_preview_html.py", False),
    ("레시피", "gen_dishes.py", False),
    ("시세", "gen_prices_page.py", False),
    # 🔴 2026-07-27 추가 — 이게 빠져 있어서 재료 페이지 348장이 통째로 낡은 채 배포됐다.
    #    브랜드를 비공개로 돌려도 price_*.html 이 지워진 menu_*.html 을 계속 링크했다
    #    (본도시락을 끄고 나서 죽은 링크 33건으로 드러남). 재료명 변경도 반영이 안 됐다.
    ("재료 페이지", "gen_ingredient_pages.py", False),
    ("마라탕 단가표", "gen_malatang_price.py", False),
    ("정보 코너", "gen_posts.py", False),
    # 🔴 2026-07-28 추가 — 이게 빠져서 **첫 배포 때 사이트맵에 지역 페이지가 0개**였다.
    #    페이지는 라이브에 떠 있는데 사이트맵에 없으면 색인이 안 붙는다.
    #    반드시 gen_sitemap **앞**에 둔다.
    ("지역 식자재", "gen_area_pages.py", False),
    ("사이트맵", "gen_sitemap.py", False),
    ("_dist 빌드", "build_dist.py", False),
]


def log(msg):
    line = "%s  %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(script, timeout=1800):
    p = subprocess.run([PY, os.path.join(BASE, "scripts", script)],
                       cwd=BASE, capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out, err


def snapshot_history():
    """오늘 가격을 price_history에 남긴다.

    이게 없으면 시세 페이지의 **상승·하락·보합이 영원히 안 뜬다** — 등락은 어제 값과
    비교해서 내는데, 지금까지 ingredients만 덮어쓰고 이력을 안 쌓아서 685종 중
    70종만 비교가 가능했다(2026-07-24 확인).
    """
    c = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().isoformat(timespec="seconds")
    n = 0
    # ⚠️ 커서를 돌면서 같은 커서로 다시 쿼리하면 순회가 깨진다 — 먼저 fetchall()
    rows = c.execute(
        "select ingredient_key, manual_price, wholesale_price, wholesale_basis "
        "from ingredients where manual_price is not null and manual_price>0").fetchall()
    for k, mp, wp, wb in rows:
        if c.execute("select 1 from price_history where ingredient_key=? and price_date=?",
                     (k, today)).fetchone():
            continue
        src = ("app" if wb and "오늘얼마" in wb
               else "coef" if (wb or "").startswith("coef") else "snapshot")
        c.execute("insert into price_history(ingredient_key,price_date,retail_price,"
                  "source,created_at,wholesale_price) values(?,?,?,?,?,?)",
                  (k, today, mp, src, now, wp))
        n += 1
    c.commit()
    return n


def main():
    log("=" * 46)
    log("일일 갱신 시작 %s" % datetime.now().strftime("%Y-%m-%d"))

    for label, script, tolerant in COLLECT:
        if not os.path.exists(os.path.join(BASE, "scripts", script)):
            log("  건너뜀 %s (스크립트 없음)" % label)
            continue
        try:
            rc, out, err = run(script)
        except subprocess.TimeoutExpired:
            log("  ! %s 시간초과 — 계속 진행" % label)
            continue
        log(("  OK %s" if rc == 0 else "  ! %s 실패(계속 진행)") % label)
        if rc != 0 and not tolerant:
            log("배포 중단 — 필수 단계 실패")
            return 1

    log("  이력 기록 %d종" % snapshot_history())

    for label, script, _ in BUILD:
        rc, out, err = run(script)
        if rc != 0:
            log("  X %s 실패 — 배포 중단" % label)
            log((err or out)[-800:])
            return 1
        log("  OK %s" % label)

    rc, out, err = run("healthcheck.py")
    if rc != 0 or "전 항목 통과" not in out:
        log("  X healthcheck 미통과 — 배포하지 않음")
        log(out[-1200:])
        return 1
    log("  OK healthcheck")

    p = subprocess.run(["npx", "wrangler", "deploy", "--config",
                        "workers/site-renderer/wrangler.toml"],
                       cwd=BASE, capture_output=True, shell=True, timeout=1800)
    out = (p.stdout or b"").decode("utf-8", "replace")
    # 워커명 확인 — 이게 안 보이면 엉뚱한 워커로 나간 것이다(2026-07-24 실제 사고)
    if p.returncode == 0 and "eolmanama-site-renderer" in out:
        log("  OK 배포 (eolmanama-site-renderer → olmanama.com)")
    else:
        log("  X 배포 실패 또는 워커명 불일치")
        log(out[-800:])
        return 1

    log("완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
