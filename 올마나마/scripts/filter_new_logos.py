# -*- coding: utf-8 -*-
# 재수집 로고 1차 필터 (2026-07-17) — Claude가 브라우저로 눈으로 보고 걸러낸 결과.
#  사용자에게 넘기기 전에 명백한 것부터 내가 거른다. 사용자 시간을 19개→11개로 줄인다.
#  ※ 최종 판정은 여전히 사용자 몫(_logo_audit.html). 여기선 "명백히 로고가 아닌 것"만 제거.
import sqlite3, json, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

# 브라우저로 확대해 직접 확인한 결과 — 로고가 아닌 것들
DROP = {
    "구구족":        "식칼(cleaver) 사진. 로고 아님",
    "롯데리아":      "버거·감자튀김·콜라 음식 사진. 로고 아님",
    "뚜레쥬르":      "빈 이미지처럼 보임(흰 배경에 흰 로고 추정) — 화면에 아무것도 안 뜸",
    "백채김치찌개":   "빈 이미지. 화면에 아무것도 안 뜸 (footer_02.png = 푸터 장식)",
    "원할머니보쌈":   "favicon.ico 16px — 먼지만 하고 식별 불가",
    "청담동마녀김밥":  "정체불명 빨간 도형. 브랜드 로고로 보이지 않음",
    "빽보이피자":    "더본코리아 공통 'BEST' 가게 일러스트. 브랜드 로고 아님 (홍콩반점과 바이트 단위로 동일 파일)",
    "홍콩반점0410":  "〃 빽보이피자와 완전히 같은 파일. 두 브랜드가 같은 로고일 수 없음",
}

dropped, kept = [], []
for r in cur.execute("SELECT id,name,logo_url FROM brands WHERE logo_pending=1 ORDER BY name").fetchall():
    if r["name"] in DROP:
        # 2차 시도도 실패 → 이름 배지로 확정. logo_rejected=1 로 재수집도 막는다.
        cur.execute("UPDATE brands SET logo_url=NULL, logo_pending=0, logo_rejected=1 WHERE id=?", (r["id"],))
        dropped.append({"name": r["name"], "url": r["logo_url"], "why": DROP[r["name"]]})
        print(f"  ✕ {r['name']:14} {DROP[r['name']]}")
    else:
        kept.append(r["name"])

con.commit()
print(f"\n제거 {len(dropped)}개 → 이름 배지 확정")
print(f"사용자 확인 대기 {len(kept)}개: {', '.join(kept)}")

os.makedirs("data/research", exist_ok=True)
json.dump({
    "filtered_at": "2026-07-17",
    "context": "1차 수집이 og:image(홍보 배너·음식 사진)를 폴백으로 써서 22% 오류 → 헤더 로고 <img>를 찾는 방식으로 재수집",
    "method": "Claude가 Chrome으로 19개를 확대해 육안 확인 → 명백히 로고가 아닌 8개 제거. 나머지는 사용자 최종 확인.",
    "dropped": dropped,
    "pending_user_check": kept,
    "note": "제거된 8개는 logo_rejected=1 → 이름 배지 확정. 2차까지 실패했으므로 더 시도하지 않는다(사용자 지시).",
}, open("data/research/logo_refetch.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("기록: data/research/logo_refetch.json")
con.close()
