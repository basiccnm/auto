# -*- coding: utf-8 -*-
# A단계: DB 재료 마스터 청소 (2026-07-20 수정사항 정리 6~9번)
#
#  6. 원산지: ingredients.origin 컬럼 신설, 이름 단서로 1차 자동 부여(억지 분류 금지 — 애매하면 NULL)
#  7. 카테고리: subcat을 "대분류/하위" 형식으로 전수 통일(구세대 '채소'/'과일' 단독형 제거)
#  8. 중복 병합: 수동(x_) 진짜 중복 3쌍 + KAMIS 우유 중복 1건 (kv↔at 쌍은 소매/도매 축이라 유지)
#  9. 껍데기 삭제: at_기타* 등 통계 집계행 17건 (수집기 EXCLUDE와 세트 — collect_at_auction.py)
#
# 수집기 쪽 근본수정과 반드시 세트로 유지할 것:
#  - collect_at_auction.py: EXCLUDE_ITEMS / ITEM_ALIAS / SUB 전체형
#  - collect_kamis_all.py: EXCLUDE_CODES(9908 우유 중복)
import os, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
con = sqlite3.connect(DB); cur = con.cursor()

# ── 9. 통계 껍데기 삭제 (실제 재료가 아닌 집계행) ─────────────────────
SHELLS = ["at_기타", "at_기타과채", "at_기타근채류", "at_기타두류", "at_기타버섯", "at_기타버섯류",
          "at_기타양채", "at_기타양채류", "at_기타엽경채류", "at_기타엽채", "at_기타엽채류",
          "at_기타채소", "at_양상추기타", "at_엽경채기타", "at_엽경채류(기타)", "at_채소기타",
          "at_신선해조류",
          # 구체 품목이 따로 있는 뭉뚱그림(마스터문서 ④): 버섯→양송이/느타리, 고추→꽈리/풋/붉은
          "at_버섯", "at_고추"]
# ── 8. 중복 병합: (지울 키, 옮길 키) — dish/menu 참조 repoint 후 삭제 ──
MERGES = [("x_c7e8c1d3cd", "vienna_sausage"),   # 비엔나소시지(중복 수동 등록)
          ("x_1f61217b12", "fish_cake"),         # 사각어묵(중복 수동 등록)
          ("x_49e0319313", "x_30ceefec1f"),      # 연유시럽(중복 수동 등록)
          ("kv_9908", "milk"),                   # 우유: milk(연동 완료)와 같은 KAMIS 시계열
          # aT 이름 변형(수집기 ITEM_ALIAS와 세트):
          ("at_가지(표준)", "at_가지"), ("at_강낭콩(울타리콩)", "at_강낭콩"),
          ("at_고구마순(줄기)", "at_고구마순"), ("at_고구마순(표준)", "at_고구마순"),
          ("at_고추(풋고추)", "at_풋고추"), ("at_고추(붉은고추)", "at_붉은고추"),
          ("at_귤(일반)", "at_귤"), ("at_깻잎(표준)", "at_깻잎"),
          ("at_무청(무시래기)", "at_무청"), ("at_바나나(수입)", "at_바나나"),
          ("at_버섯(양송이)", "at_양송이버섯"), ("at_버섯(느타리)", "at_느타리버섯"),
          ("at_복숭아(표준)", "at_복숭아"), ("at_블루베리(일반)", "at_블루베리"),
          ("at_비트(붉은사탕무우)", "at_비트"), ("at_자두(표준)", "at_자두"),
          ("at_자몽(수입)", "at_자몽"), ("at_참다래(키위)", "at_참다래"),
          ("at_콩(콩)", "at_콩"), ("at_콩(강낭콩)", "at_강낭콩"),
          ("at_파(대파)", "at_파"), ("at_파세리(향미나리)", "at_파세리"),
          ("at_파인애플(수입)", "at_파인애플"), ("at_피망(단고추)", "at_피망"),
          ("at_고추(꽈리고추)", None)]  # 꽈리고추: 대상 없음 → 이름만 바꿔 유지

def exists(k):
    return cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (k,)).fetchone() is not None

n_shell = 0
for k in SHELLS:
    if exists(k):
        cur.execute("DELETE FROM price_history WHERE ingredient_key=?", (k,))
        cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (k,))
        n_shell += 1
print(f"9. 껍데기 삭제: {n_shell}건")

n_merge = 0
for src, dst in MERGES:
    if not exists(src):
        continue
    if dst is None:  # 꽈리고추처럼 병합 대상이 없으면 개명 유지
        cur.execute("UPDATE ingredients SET name='꽈리고추 도매(경락)' WHERE ingredient_key=?", (src,))
        continue
    if not exists(dst):
        # 대상이 없으면 키를 대상 이름으로 개명(다음 수집부터 alias로 합쳐짐)
        cur.execute("UPDATE ingredients SET ingredient_key=? WHERE ingredient_key=?", (dst, src))
        cur.execute("UPDATE price_history SET ingredient_key=? WHERE ingredient_key=?", (dst, src))
        n_merge += 1
        continue
    for t, col in (("dish_ingredients", "ingredient_key"), ("menu_ingredients", "ingredient_key")):
        cur.execute(f"UPDATE {t} SET {col}=? WHERE {col}=?", (dst, src))
    cur.execute("DELETE FROM price_history WHERE ingredient_key=?", (src,))
    cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (src,))
    n_merge += 1
print(f"8. 중복 병합: {n_merge}건")

# ── 7. subcat 전수 통일: "대분류/하위" ────────────────────────────────
LEGACY = {"채소": "농산물/채소", "과일": "농산물/과일", "곡식": "농산물/곡물",
          "버섯·견과": "농산물/버섯·견과", "가공": "가공식품/기타",
          "농산물/곡식": "농산물/곡물", "축산물/기타": "축산물/기타"}
for old, new in LEGACY.items():
    cur.execute("UPDATE ingredients SET subcat=? WHERE subcat=?", (new, old))
# 수산(구형 단독) → 이름 단서로 하위 부여
for k, n in cur.execute("SELECT ingredient_key,name FROM ingredients WHERE subcat='수산'").fetchall():
    if any(w in n for w in ("미역", "다시마", "김", "파래", "톳", "매생이")): sub = "수산물/해조류"
    elif any(w in n for w in ("새우", "게", "꽃게", "대게")): sub = "수산물/갑각류"
    elif any(w in n for w in ("오징어", "낙지", "문어", "주꾸미", "쭈꾸미")): sub = "수산물/연체류"
    elif any(w in n for w in ("굴", "홍합", "바지락", "전복", "조개", "가리비")): sub = "수산물/조개류"
    else: sub = "수산물/어류"
    cur.execute("UPDATE ingredients SET subcat=? WHERE ingredient_key=?", (sub, k))
# 참가격(cg_) 시판 기초재료 — subcat 미부여분
CG_SUB = {"cg_sesame_oil": "가공식품/소스·양념", "cg_cooking_oil": "가공식품/소스·양념",
          "cg_sugar_white": "가공식품/소스·양념", "cg_salt": "가공식품/소스·양념",
          "cg_soy_sauce_jin": "가공식품/소스·양념", "cg_soy_sauce_brew": "가공식품/소스·양념",
          "cg_vinegar": "가공식품/소스·양념", "cg_gochujang": "가공식품/소스·양념",
          "cg_doenjang": "가공식품/소스·양념", "cg_ssamjang": "가공식품/소스·양념",
          "cg_red_pepper_powder": "가공식품/소스·양념", "cg_mayonnaise": "가공식품/소스·양념",
          "cg_starch_syrup": "가공식품/소스·양념", "cg_oligo_syrup": "가공식품/소스·양념",
          "cg_flour_medium": "가공식품/기타", "cg_flour_strong": "가공식품/기타",
          "cg_noodle_somyeon": "가공식품/면·떡", "cg_dangmyeon": "가공식품/면·떡",
          "cg_butter": "가공식품/유제품", "cg_sliced_cheese": "가공식품/유제품"}
for k, s in CG_SUB.items():
    cur.execute("UPDATE ingredients SET subcat=? WHERE ingredient_key=? AND subcat IS NULL", (s, k))
# 지목된 오분류: 치킨무는 닭이 아니다
cur.execute("UPDATE ingredients SET subcat='가공식품/기타' WHERE ingredient_key='sidedish_set'")
# 우유·유제품 계열이 축산물로 남아있으면 유제품으로
cur.execute("""UPDATE ingredients SET subcat='가공식품/유제품'
  WHERE (name LIKE '%우유%' OR name LIKE '%치즈%' OR name LIKE '%생크림%' OR name LIKE '%연유%' OR name LIKE '%버터%')
    AND subcat LIKE '축산물%'""")
left = cur.execute("SELECT count(*) FROM ingredients WHERE subcat IS NULL OR instr(subcat,'/')=0").fetchone()[0]
print(f"7. subcat 통일 완료 — 미통일 잔여 {left}건")
for r in cur.execute("SELECT ingredient_key,name,subcat FROM ingredients WHERE subcat IS NULL OR instr(subcat,'/')=0").fetchall():
    print("   잔여:", r)

# ── 6. origin 컬럼 + 이름 단서 1차 부여 (애매하면 NULL 유지) ─────────
cols = {r[1] for r in cur.execute("PRAGMA table_info(ingredients)")}
if "origin" not in cols:
    cur.execute("ALTER TABLE ingredients ADD COLUMN origin TEXT")
    print("6. 컬럼 신설: ingredients.origin")
IMPORT_WORDS = ("수입", "미국", "미국산", "호주", "호주산", "칠레", "스페인", "브라질", "캐나다",
                "태국", "베트남", "중국", "노르웨이", "러시아", "페루", "덴마크", "독일")
KOREA_WORDS = ("한우", "국내산", "국산", "한돈", "제주")
cur.execute("UPDATE ingredients SET origin=NULL")
for k, n in cur.execute("SELECT ingredient_key,name FROM ingredients").fetchall():
    org = None
    if any(w in n for w in IMPORT_WORDS): org = "수입산"
    elif any(w in n for w in KOREA_WORDS): org = "국산"
    elif k.startswith("ek_"): org = "국산"       # 축평원 = 국산 축산물 경락
    elif k.startswith("cs_"): org = "수입산"     # 관세청 통관단가 = 수입
    if org:
        cur.execute("UPDATE ingredients SET origin=? WHERE ingredient_key=?", (org, k))
n_org = cur.execute("SELECT count(*) FROM ingredients WHERE origin IS NOT NULL").fetchone()[0]
print(f"6. origin 부여: {n_org}건 (나머지는 미표기 유지 — 억지 분류 금지)")

con.commit(); con.close()
print("완료")
