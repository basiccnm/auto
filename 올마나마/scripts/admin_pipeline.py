# -*- coding: utf-8 -*-
# 레시피 '반영' 파이프라인 (2026-07-20)
#
# 순서가 핵심이다 (바꾸면 조용히 깨진다):
#   0. DB 백업                     ← 타협 불가
#   1. dish_def / dish_def_ingredient UPSERT   ← 재생성에서 살아남는 유일한 곳
#   2. 사진 복사 _recipes/img → _preview/recipe
#   3. gen_dishes                  ← dishes 행 생성 (신규 요리는 여기서 처음 생김)
#   4. apply_recipe_md             ← dishes에 행이 있어야 동작하므로 반드시 3 이후
#   5. gen_dishes 재실행           ← _KEEP이 4의 결과를 집어 사진·팁·FAQ를 렌더
#   6. 나머지 생성기 → healthcheck (배포 관문)
#
# gen_dishes는 API 비용이 0이라 두 번 돌려도 무해하다.
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import admin_store as st              # noqa: E402
from apply_recipe_md import parse     # noqa: E402
from recipe_mapping import Matcher    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(BASE, "_recipes")
IMGDIR = os.path.join(RECIPES, "img")
PREVIEW_IMG = os.path.join(BASE, "_preview", "recipe")
BACKUP = os.path.join(BASE, "data", "backup")

# 🔴 gen_ingredient_pages 가 빠져 있었다(2026-07-27). 재료 페이지 348장이 갱신되지 않아
#    브랜드를 숨겨도 price_*.html 이 죽은 menu_*.html 을 계속 링크했다. 순서는 이름·값이
#    확정된 뒤여야 하므로 gen_prices_page 다음에 둔다.
# 🔴 gen_area_pages 도 같은 이유로 넣는다(2026-07-28). 처음 배포에서 **사이트맵에 지역
#    페이지 17장이 하나도 안 들어갔다** — 파이프라인에 없어서 sitemap 이 먼저 만들어졌다.
#    같은 사고를 두 번째로 낸 것이다(gen_ingredient_pages, 2026-07-27).
#    **생성기를 새로 만들면 이 목록과 daily_update.py 양쪽에 넣는다. sitemap 보다 앞이어야 한다.**
STEPS = ["compute_line_costs", "gen_preview_html", "gen_dishes", "gen_prices_page",
         "gen_ingredient_pages", "gen_area_pages", "gen_sitemap",
         "build_dist", "healthcheck"]


def _run(script, log):
    """생성기 1개 실행. 실패하면 예외 — 파이프라인이 멈춘다."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join("scripts", f"{script}.py")],
                       cwd=BASE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        tail = "\n".join((r.stdout or "").splitlines()[-40:])
        log(f"❌ {script} 실패 (exit {r.returncode})")
        for ln in tail.splitlines()[-12:]:
            log(f"    {ln}")
        raise RuntimeError(f"{script} 실패")
    last = [x for x in (r.stdout or "").splitlines() if x.strip()]
    log(f"✅ {script}" + (f" — {last[-1][:80]}" if last else ""))


def backup_db(log):
    os.makedirs(BACKUP, exist_ok=True)
    from datetime import datetime
    dst = os.path.join(BACKUP, f"eolmanama_{datetime.now():%Y%m%d_%H%M%S}.db")
    shutil.copy2(os.path.join(BASE, "data", "eolmanama.db"), dst)
    log(f"💾 DB 백업 → {os.path.basename(dst)}")
    return dst


def apply(slug, log):
    log(f"=== {slug} 반영 시작 ===")
    backup_db(log)

    # ── 1. 매핑 확정 → dish_def ──────────────────────────────────
    md = open(os.path.join(RECIPES, f"{slug}.md"), encoding="utf-8").read()
    d = parse(md)
    mt = Matcher()
    rows = mt.map_recipe(d["ing_groups"])
    miss = [r for r in rows if not r["key"]]
    bad = [r for r in rows if r["key"] and not r["unit_ok"]]
    if miss:
        raise RuntimeError(f"미매칭 재료 {len(miss)}건: " + ", ".join(r["raw"] for r in miss))
    if bad:
        raise RuntimeError(f"단위 불일치 {len(bad)}건: " + ", ".join(r["raw"] for r in bad))

    c = mt.c
    st.init(c)
    row = c.execute("SELECT name, serving, category, icon, sort_order, match_pattern "
                    "FROM dish_def WHERE slug=?", (slug,)).fetchone()
    if not row:
        raise RuntimeError(f"dish_def에 '{slug}'가 없습니다 — 신규 요리는 먼저 등록해야 합니다")
    serving = d["serving"] or row["serving"]
    c.execute("""UPDATE dish_def SET serving=?, updated_at=? WHERE slug=?""",
              (serving, st.now(), slug))
    c.execute("DELETE FROM dish_def_ingredient WHERE slug=?", (slug,))
    n = 0
    for i, r in enumerate(rows):
        if r["key"] == "water" and not r["amount"]:
            continue
        c.execute("""INSERT INTO dish_def_ingredient(slug,ingredient_key,amount,unit,sort_order)
            VALUES(?,?,?,?,?) ON CONFLICT(slug,ingredient_key) DO UPDATE SET
              amount=excluded.amount, unit=excluded.unit""",
            (slug, r["key"], r["amount"] or 0, r["unit"] or "g", i))
        n += 1
    c.commit()
    log(f"📝 dish_def 갱신 — 재료 {n}줄 ({serving})")

    # 별칭 학습 카운트
    for r in rows:
        if r["how"] == "별칭":
            c.execute("UPDATE ingredient_alias SET hits=hits+1 WHERE ingredient_key=?", (r["key"],))
    c.commit()
    c.close()          # ★ subprocess 전에 반드시 닫는다 — 안 그러면 database is locked

    # ── 2. 사진 복사 ────────────────────────────────────────────
    os.makedirs(PREVIEW_IMG, exist_ok=True)
    cp = 0
    for i in (1, 2, 3):
        src = os.path.join(IMGDIR, f"{slug}_{i}.png")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(PREVIEW_IMG, f"{slug}_{i}.png"))
            cp += 1
    log(f"🖼️ 사진 {cp}장 복사" + (" (없음 — 페이지에 사진이 안 나옵니다)" if not cp else ""))

    # ── 3~5. 순서가 중요한 구간 ─────────────────────────────────
    _run("gen_dishes", log)                       # dishes 행 생성
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-X", "utf8",
                        os.path.join("scripts", "apply_recipe_md.py"), slug],
                       cwd=BASE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("apply_recipe_md 실패: " + (r.stdout or "")[-300:])
    log("✅ apply_recipe_md — " + (r.stdout or "").strip().splitlines()[-1][:80])

    # ── 6. 나머지 파이프라인 ────────────────────────────────────
    for s in STEPS:
        _run(s, log)

    log(f"🎉 완료 — http://127.0.0.1:8792/dish_{slug} 에서 확인하세요")
    log("배포하려면: cd workers\\site-renderer && npx wrangler deploy  (검수 후 직접 실행)")
