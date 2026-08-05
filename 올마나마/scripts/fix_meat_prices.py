# -*- coding: utf-8 -*-
# 육류·수산 단가 교정 (2026-07-17) — 사용자 지시 "원산지 표시는 필요 없어. 수입산/국산 이것만 알면 됨"
#  수입/국산은 화면에 낼 값이 아니라 **단가를 고르는 내부 기준**이다. 우리 원칙은 "왠만하면 다 수입산".
#  조사 결과 3종이 사실상 **국산/한우 또는 소분 프리미엄 단가**를 쓰고 있었다.
#  근거: data/research/meat_origin_audit.json (미트박스 B2B 실측, confidence high만 반영)
import sqlite3, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
DRY = os.environ.get("DRY") == "1"

# (재료명 LIKE, 새 단가, 사유) — confidence high 만
FIX = [
    ("소고기 국거리/양지", 15000,
     "22,000원은 **한우 양지 단가**였다(연하누 3등급 19,300 / 안심목장한우 2등급 25,000 사이). "
     "'왠만하면 수입산' 원칙과 정면으로 어긋남. 수입 양지늑간 미국 엑셀 14,000 / 뉴질랜드 차돌양지 14,900 / "
     "미국 아이오와프리미엄 15,300 / 오마하 16,500 → 육개장·국밥용은 15,000이 현실적"),
    ("소고기 다짐육", 10000,
     "16,000원은 헤드미트·목심·알전각 같은 **상위 부위 대역**이었다. 버거 패티·소불고기가 실제로 쓰는 "
     "삼겹양지/양지안창 다짐육은 미국 스위프트 9,000 / 호주 AMH-GF 9,480 / 티스 9,600 → 10,000"),
    ("생연어 필렛", 22000,
     "32,000원은 **소분 프리미엄가**였다(500g 33,800 / 1.3kg 30,692 대역). 프랜차이즈 벌크 기준은 "
     "냉동 생연어필렛 10kg 20,900 / 노르웨이 연어스테이크 8kg 24,875 → 22,000. 연어는 전량 수입(국산 없음)"),
]
for name, new, why in FIX:
    r = cur.execute("SELECT ingredient_key, name, manual_price FROM ingredients WHERE name=?", (name,)).fetchone()
    if not r:
        print(f"  ⚠️ '{name}' 재료 없음 — 건너뜀"); continue
    uses = cur.execute("SELECT COUNT(DISTINCT menu_id) FROM menu_ingredients WHERE ingredient_key=?",
                       (r["ingredient_key"],)).fetchone()[0]
    cur.execute("UPDATE ingredients SET manual_price=? WHERE ingredient_key=?", (new, r["ingredient_key"]))
    d = new - r["manual_price"]
    print(f"  {name:16} {r['manual_price']:>6,} → {new:>6,}원/kg ({d:+,}) · {uses}개 메뉴")

# 염통은 어느 메뉴에도 쓰이지 않는다 → 이름에서 뺀다(안 쓰는 품목을 묶어두면 오해만 부른다).
#  '한우' 표기 처리는 보류: 5개 메뉴 중 3개가 메뉴명 자체가 '한우곱창구이/한우대창구이/한우대창덮밥'이라
#  브랜드가 스스로 한우를 내걸고 있다. 한우 자숙곱창은 65,000/kg이라 25,000은 2.6배 과소계상 의심.
#  → 한우 단가 조사 결과를 받고 별도 처리. 여기서 이름만 고치면 오히려 틀린 상태가 고착된다.
print("\n※ '한우곱창/대창/염통' 25,000원은 이번에 손대지 않음 — 한우 단가 조사 중")
print("   (5개 메뉴 중 3개가 메뉴명부터 '한우'. 한우 자숙곱창 65,000/kg이면 2.6배 과소계상)")

if DRY:
    con.rollback(); print("\n[DRY] 롤백함")
else:
    con.commit(); print("\n커밋 완료")
con.close()
