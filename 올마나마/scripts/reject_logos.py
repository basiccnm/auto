# -*- coding: utf-8 -*-
# 로고 검수 결과 반영 (2026-07-17) — 사용자가 _logo_audit.html로 78개를 눈으로 확인한 결과
#  78개 중 17개(22%)가 오류. 자동 수집 로고를 아무도 검증하지 않은 상태로 두면 안 된다는 게 확인됨.
#  ⚠️ 남의 브랜드 로고를 다는 건 상표 문제 → 즉시 내리고 텍스트 배지로 폴백(이미 14개가 그렇게 정상 노출 중).
#
#  ★ logo_rejected=1 을 박는 이유:
#    fetch_logos.py 는 `WHERE logo_url IS NULL` 로 대상을 뽑는다. 그냥 NULL 로 지우면
#    다음 실행 때 똑같이 틀린 로고를 다시 가져온다. 거부 기록을 DB에 남겨야 재발이 없다.
import sqlite3, json, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

REJECTED = [41, 37, 112, 108, 54, 44, 99, 59, 65, 62, 82, 12, 10, 98, 21, 29, 74]

cols = {r[1] for r in cur.execute("PRAGMA table_info(brands)")}
if "logo_rejected" not in cols:
    cur.execute("ALTER TABLE brands ADD COLUMN logo_rejected INTEGER DEFAULT 0")
    print("  + 컬럼: brands.logo_rejected")

log = []
for bid in REJECTED:
    r = cur.execute("SELECT name, logo_url FROM brands WHERE id=?", (bid,)).fetchone()
    if not r:
        print(f"  ⚠️ brand_id {bid} 없음"); continue
    log.append({"brand_id": bid, "name": r["name"], "rejected_url": r["logo_url"]})
    cur.execute("UPDATE brands SET logo_url=NULL, logo_rejected=1 WHERE id=?", (bid,))
    print(f"  ✕ [{bid}] {r['name']}: 로고 내림 → 텍스트 배지")
con.commit()

os.makedirs("data/research", exist_ok=True)
json.dump({
    "audited_at": "2026-07-17",
    "method": "_logo_audit.html — 사용자가 노출 중인 78개를 눈으로 전수 확인",
    "result": f"78개 중 {len(log)}개(약 {len(log)/78*100:.0f}%) 오류 → 로고 내리고 텍스트 배지로 폴백",
    "why_rejected": "다른 브랜드 로고이거나 로고가 아닌 이미지(광고·배너·사진). 상표 리스크라 즉시 제거.",
    "⚠️_재수집_금지": "brands.logo_rejected=1 로 표시함. fetch_logos.py / upgrade_logos.py 가 이 값을 보고 건너뛴다. "
                      "이 가드를 지우면 똑같이 틀린 로고가 되살아난다.",
    "rejected": log,
    "남은_상태": "로고 91개 · 텍스트 배지 31개(기존 14 + 이번 17)",
}, open("data/research/logo_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n기록: data/research/logo_audit.json ({len(log)}건)")

n_logo = cur.execute("SELECT COUNT(*) FROM brands WHERE logo_url IS NOT NULL").fetchone()[0]
n_badge = cur.execute("SELECT COUNT(*) FROM brands WHERE logo_url IS NULL").fetchone()[0]
print(f"로고 {n_logo}개 · 텍스트 배지 {n_badge}개")
con.close()
