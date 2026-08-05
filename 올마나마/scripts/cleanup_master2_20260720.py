# -*- coding: utf-8 -*-
# A단계 3차: 사용자 실검수 반영 (2026-07-20 오후)
#  ① 수산가공 신설: 필렛·참치·멸치·자반 등 가공/손질 수산물 + 해물믹스 + 새우살 + 기존 어묵류
#  ② 새우젓·멸치액젓 → 장·조미료(젓갈) / 오돌뼈용등심살 → 돼지 / 계란 → 축산물/계란 분리
#  ③ 미상 집계 삭제: 과일과채류 도매 · 김(KAMIS)(장 단위를 kg처럼 기록해 1,426원/kg로 왜곡)
#  ④ 이름 '도매' 제거 — kv/마트 짝이 있는 at_ 품목은 그 행의 도매 컬럼으로 병합(한 품목 한 줄),
#     짝 없는 것은 "이름(경락)"으로 개명. 무우→무 같은 표기 변형 통합.
#  ⑤ '신선 채소'(3종 뭉뚱그림) 분해 삭제 → 양파50%·양배추30%·당근20% (menu 182건 + dish는 gen_dishes 원본)
import os, re, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

# ── ①② 분류 이동 (이름/키 명시) ──────────────────────────────
MOVES = {
    "salmon_raw": "가공식품/수산가공", "white_fish_raw": "가공식품/수산가공",
    "x_cda2501f42": "가공식품/수산가공", "x_216cb905a2": "가공식품/수산가공",
    "x_1e5f6864ee": "가공식품/수산가공", "x_16f05e25aa": "가공식품/수산가공",
    "kv_638": "가공식품/수산가공", "kv_662": "가공식품/수산가공",
    "x_752586dabe": "가공식품/수산가공", "godeungeo_mart": "가공식품/수산가공",
    "seafood_mix": "가공식품/수산가공", "shrimp_meat": "가공식품/수산가공",
    "kv_650": "가공식품/장·조미료",   # 새우젓(젓갈)
    "kv_651": "가공식품/장·조미료",   # 멸치액젓
    "x_80a38156df": "축산물/돼지",    # 오돌뼈용등심살
    "egg_fresh": "축산물/계란", "kv_9903": "축산물/계란",
}
n = 0
for k, sub in MOVES.items():
    n += cur.execute("UPDATE ingredients SET subcat=? WHERE ingredient_key=?", (sub, k)).rowcount
# 기존 '어묵·수산가공' 버킷도 '수산가공'으로 흡수 통일
n += cur.execute("UPDATE ingredients SET subcat='가공식품/수산가공' WHERE subcat='가공식품/어묵·수산가공'").rowcount
print(f"①② 분류 이동: {n}건")

# ── ③ 삭제 ─────────────────────────────────────────────────
for k, why in (("at_과일과채류", "aT 집계행"), ("kv_641", "KAMIS 김: 장 단위 → kg 환산 불가 왜곡. 우리 '김'(김밥김 실조사)만 유지")):
    if cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?", (k,)).fetchone():
        cur.execute("DELETE FROM price_history WHERE ingredient_key=?", (k,))
        cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (k,))
        print(f"③ 삭제: {k} ({why})")

# ── ③-2 뭉뚱그림 콤보 이름 명확화 (방토=방울토마토) ─────────
RENAMES = {"x_01dcc4020b": "방울토마토·무순 토핑", "x_c8a1430d5c": "방울토마토·날치알 토핑",
           "x_296d13616d": "방울토마토·날치알·김가루 토핑", "x_adf187d686": "아몬드·방울토마토·옥수수 토핑",
           "x_2ab27ebba7": "방울토마토(손질)"}
for k, nm in RENAMES.items():
    cur.execute("UPDATE ingredients SET name=? WHERE ingredient_key=?", (nm, k))
print(f"③ 콤보 이름 명확화: {len(RENAMES)}건")

# ── ④ at_ '도매' 이름 정리 + 짝 병합 ─────────────────────────
SYN = {"무우": "무", "알타리무우": "알타리무"}   # 표기 변형(수집기 ALIAS와 세트)
def norm_at(name):
    s = re.sub(r"\s*도매(\(경락\))?$", "", name).strip()
    return SYN.get(s, s)

# 병합 우선 대상: 요리용 마트 재료(kg) → 이름 그대로 매칭되는 kg 단위 재료
at_rows = cur.execute("SELECT ingredient_key, name, wholesale_price FROM ingredients WHERE ingredient_key LIKE 'at_%'").fetchall()
others = {r["name"]: (r["ingredient_key"], r["base_unit"]) for r in
          cur.execute("SELECT ingredient_key, name, base_unit FROM ingredients WHERE ingredient_key NOT LIKE 'at_%'")}
merged, renamed, target_map = 0, 0, {}
for r in at_rows:
    nm = norm_at(r["name"])
    tgt = others.get(nm) or others.get(nm + "(KAMIS)")
    if tgt and tgt[1] == "kg":
        tkey = tgt[0]
        cur.execute("""UPDATE ingredients SET wholesale_price=?, wholesale_basis='at_auction'
                       WHERE ingredient_key=?""", (r["wholesale_price"], tkey))
        cur.execute("DELETE FROM price_history WHERE ingredient_key=?", (r["ingredient_key"],))
        cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (r["ingredient_key"],))
        target_map[nm] = tkey
        merged += 1
    else:
        new_name = nm + "(경락)"
        cur.execute("UPDATE ingredients SET name=? WHERE ingredient_key=?", (new_name, r["ingredient_key"]))
        renamed += 1
print(f"④ kv/마트 짝으로 병합(한 품목 한 줄): {merged}건 / '(경락)' 개명: {renamed}건")

# ── ⑤ 신선 채소 분해 (양파50·양배추30·당근20) ─────────────────
VEG = [("kv_245", 0.5), ("yangbaechu_mart", 0.3), ("kv_232", 0.2)]
mrows = cur.execute("SELECT id, menu_id, amount, unit, sort_order FROM menu_ingredients WHERE ingredient_key='vegetables_fresh'").fetchall()
for r in mrows:
    cur.execute("DELETE FROM menu_ingredients WHERE id=?", (r["id"],))
    for k, ratio in VEG:
        cur.execute("""INSERT INTO menu_ingredients(menu_id, ingredient_key, amount, unit, sort_order)
                       VALUES(?,?,?,?,?)""", (r["menu_id"], k, round(r["amount"] * ratio, 1), r["unit"], r["sort_order"]))
drows = cur.execute("SELECT count(*) c FROM dish_ingredients WHERE ingredient_key='vegetables_fresh'").fetchone()["c"]
print(f"⑤ 신선 채소 분해: menu {len(mrows)}건 → 3분할 (dish {drows}건은 gen_dishes.py 원본 수정으로)")
# dish_ingredients는 gen_dishes가 재시딩하므로 여기서는 안 지움 — 원본 수정 후 재실행하면 사라짐

# 사용처가 완전히 사라진 뒤에만 재료 삭제 (menu는 위에서 정리 — dish는 재생성 후 0이 됨)
cur.execute("DELETE FROM dish_ingredients WHERE ingredient_key='vegetables_fresh'")
cur.execute("DELETE FROM price_history WHERE ingredient_key='vegetables_fresh'")
cur.execute("DELETE FROM ingredients WHERE ingredient_key='vegetables_fresh'")
print("⑤ '신선 채소' 재료 삭제")

con.commit()
print("\n[수집기 KV_WHOLESALE_TARGET 반영용 매핑]")
for nm, k in sorted(target_map.items()):
    print(f'    "{nm}": "{k}",')
print("\n총 재료:", cur.execute("SELECT count(*) FROM ingredients").fetchone()[0])
con.close()
