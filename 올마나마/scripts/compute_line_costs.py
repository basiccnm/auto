# menu_ingredients.line_cost 를 실제 가격(live 시세 or manual 단가)으로 재계산
# → 화면의 재료 라인가격 = 실시세와 일치. 완전가격 메뉴는 est_cost도 합계로 갱신.
import sqlite3, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

# 단위 → base_unit(kg/L/개) 환산계수
#  ⚠️ 액체/고체 교차(kg↔ml, L↔g)를 반드시 처리할 것. 안 하면 amount가 그대로 곱해져
#     (예: 우유 180ml × 2,938원/kg = 528,840원) 안전장치에 걸려 라인이 통째로 스킵되고
#     est_cost 재계산까지 막힌다. 2026-07-17 우유 42개 메뉴에서 실제 발생한 버그.
def to_base(amount, unit, base):
    u = (unit or "").strip()
    if base == "kg":
        if u == "kg": return amount
        if u in ("g", "ml"): return amount / 1000   # 물성 밀도 ≈1 가정
        if u == "L": return amount
        return None            # 개/세트 등 → 환산 불가(호출부에서 오류 처리)
    if base == "L":
        if u == "L": return amount
        if u in ("ml", "g"): return amount / 1000
        if u == "kg": return amount
        return None
    if base == "개":
        if u in ("개", "세트", "장", "마리"): return amount
        return None            # g/ml로 적힌 개수 단위 재료 = 데이터 오류
    return amount

# 재료별 현재가격(원/base_unit)
#  🔴 1순위는 `ingredient_retail`(사람이 고른 쿠팡 상품)이다 — 2026-07-27 사고:
#     소매 트랙을 다 만들어 놓고 **여기서 안 읽어서** 쿠팡 상품을 바꿔도 원가가 안 바뀌었다.
#     자메이카 통다리 소매 상품을 19,990원(용량 미확인) → 12,500원/1kg 으로 고쳤는데
#     소매 원가가 13,230원 그대로였다. price_of() 가 manual_price 만 보고 있었다.
#  · pack_g 가 있어야 단위당 단가를 낼 수 있다. 없으면 다음 순위로 넘어간다(추측 금지).
#  · status='ok' 만 쓴다. pending/skip 은 아직 사람이 확정하지 않은 후보다.
def retail_of(key, base):
    r = cur.execute("""SELECT price, pack_g FROM ingredient_retail
                       WHERE ingredient_key=? AND status='ok' AND price>0 AND pack_g>0""",
                    (key,)).fetchone()
    if not r:
        return None
    b = (base or "").lower()
    if b in ("kg", "l"):
        return r["price"] / (r["pack_g"] / 1000.0)      # 원/kg
    if b in ("g", "ml"):
        return r["price"] / r["pack_g"]                 # 원/g
    return None            # 개·세트·장 단위는 팩당 개수를 모르니 쓰지 않는다


def store_only(key):
    """소매에서 뺄 재료인가.
    🔴 치킨무처럼 **한 개 단위로 못 사는 것**은 소매 원가에 넣으면 왜곡된다(대표 지시 2026-07-27:
       "치킨무는 한개씩 살수가 없어서 동네마트가서 사야함 · 도매로만 빼두세요").
       도매(매장 원가)에는 그대로 넣고, 소매(집에서 만들기)에서만 제외한다."""
    r = cur.execute("SELECT status FROM ingredient_retail WHERE ingredient_key=?", (key,)).fetchone()
    return bool(r) and r["status"] == "store"


def price_of(key):
    ing = cur.execute("SELECT type, manual_price, base_unit, markup_factor FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
    if not ing: return None, None
    rp = retail_of(key, ing["base_unit"])
    if rp is not None:
        return rp, ing["base_unit"]
    if ing["type"] in ("live", "live_composite"):
        r = cur.execute("SELECT retail_price FROM price_history WHERE ingredient_key=? AND retail_price>0 ORDER BY price_date DESC LIMIT 1", (key,)).fetchone()
        if r: return r["retail_price"], ing["base_unit"]
        # live인데 시세 없으면 manual_price 폴백
        return ing["manual_price"], ing["base_unit"]
    return ing["manual_price"], ing["base_unit"]

# 도매(업소 공급가) — 매장 원가 계산용. apply_wholesale.py가 채운 값.
def wholesale_of(key):
    r = cur.execute("SELECT wholesale_price, base_unit FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
    if not r or not r["wholesale_price"]: return None, None
    return r["wholesale_price"], r["base_unit"]


def wholesale_line(r, sell):
    """도매 라인가격을 계산해 저장하고 값을 돌려준다(못 내면 None).

    🔴 **소매 값 유무와 무관하게** 계산한다 — 2026-07-27 사고:
       소매가 없는 재료를 만나면 위쪽 `continue` 로 빠져 **도매까지 통째로 날아갔다.**
       `머리고기(통편육)` 4개 메뉴의 매장원가에서 9,000원/kg 짜리 재료가 빠진 채로
       발행되고 있었고, 출력은 "✅ 스킵된 라인 없음" 이라 아무도 몰랐다.
       도매·소매는 **별도 트랙**이다(대표: "도매랑 소매는 별도야 / 따로 DB를 보관하라고")."""
    wp, wbase = wholesale_of(r["ingredient_key"])
    wq = to_base(r["amount"], r["unit"], wbase) if wp is not None else None
    if wp is None or wq is None:
        cur.execute("UPDATE menu_ingredients SET wholesale_cost=NULL WHERE id=?", (r["id"],))
        return None
    wline = round(wp * wq)
    if sell and wline > sell * 1.5:      # 단위파싱 오류로 보고 스킵(소매와 같은 안전장치)
        cur.execute("UPDATE menu_ingredients SET wholesale_cost=NULL WHERE id=?", (r["id"],))
        return None
    cur.execute("UPDATE menu_ingredients SET wholesale_cost=? WHERE id=?", (wline, r["id"]))
    return wline

# menus에 매장 원가 컬럼 추가(없으면)
_mc = {r[1] for r in cur.execute("PRAGMA table_info(menus)")}
for c, t in (("store_cost", "INTEGER"), ("store_ratio", "REAL")):
    if c not in _mc:
        cur.execute(f"ALTER TABLE menus ADD COLUMN {c} {t}")
        print(f"  + 컬럼: menus.{c}")

# 도매 라인가격도 여기서 한 번만 계산해 저장한다(단일 출처).
#  렌더러가 소매 line_cost에 비율을 다시 곱해 도매를 구하면 반올림이 두 번 일어나
#  표의 도매 합계와 헤드라인 store_cost가 어긋난다. 2026-07-17 실제 발생(빽스치노 2원).
_mic = {r[1] for r in cur.execute("PRAGMA table_info(menu_ingredients)")}
if "wholesale_cost" not in _mic:
    cur.execute("ALTER TABLE menu_ingredients ADD COLUMN wholesale_cost INTEGER")
    print("  + 컬럼: menu_ingredients.wholesale_cost")

# 전체 메뉴 실시세 재계산. 라인단가는 최대한 채우고, 총액은 "정상 범위일 때만" 갱신(비정상은 Gemini값 유지).
menus = [r["id"] for r in cur.execute("SELECT id FROM menus").fetchall()]
updated_lines, recomputed_menus, store_menus = 0, 0, 0
unit_errors, oversize, no_price = [], [], []   # 조용히 스킵되면 버그를 못 찾는다 → 끝에 반드시 리포트
for mid in menus:
    m = cur.execute("SELECT sell_price, est_cost FROM menus WHERE id=?", (mid,)).fetchone()
    sell = m["sell_price"] or 0
    rows = cur.execute("SELECT id, ingredient_key, amount, unit FROM menu_ingredients WHERE menu_id=?", (mid,)).fetchall()
    total, all_priced = 0, True
    w_total, w_priced = 0, True     # 매장(도매) 원가
    for r in rows:
        # ── 도매 먼저. 소매가 어떻게 되든 **항상** 계산한다(위 wholesale_line 주석 참조).
        wline = wholesale_line(r, sell)
        if wline is None:
            w_priced = False
        else:
            w_total += wline

        # ── 소매. 여기서 빠져도 위의 도매는 이미 저장돼 있다.
        # 소매 제외 재료(매장전용) — 소매 라인만 비운다.
        #  all_priced 를 깨지 않는다(메뉴 총액은 나머지 재료로 정상 산출).
        if store_only(r["ingredient_key"]):
            cur.execute("UPDATE menu_ingredients SET line_cost=NULL WHERE id=?", (r["id"],))
            continue
        p, base = price_of(r["ingredient_key"])
        # 🔴 `0` 도 "없음"으로 본다 — `manual_price=0` 인 재료가 라인가 0원으로 조용히 들어가
        #    소매 원가를 낮춰버린다(머리고기 4개 순대국 메뉴에서 실제로 그랬다).
        if not p:       # 쿠팡 상품도 manual_price 도 없다 = 사람이 아직 안 고른 재료
            no_price.append((mid, r["ingredient_key"]))
            all_priced = False
            cur.execute("UPDATE menu_ingredients SET line_cost=NULL WHERE id=?", (r["id"],))
            continue
        q = to_base(r["amount"], r["unit"], base)
        if q is None:   # 단위 불일치(개 단위 재료를 g로 적는 등) = 데이터 오류
            unit_errors.append((mid, r["ingredient_key"], r["amount"], r["unit"], base))
            all_priced = False
            cur.execute("UPDATE menu_ingredients SET line_cost=NULL WHERE id=?", (r["id"],))
            continue
        line = round(p * q)
        # 안전장치: 재료 1개가 판매가의 1.5배 초과면 단위파싱 오류로 보고 라인 스킵
        if sell and line > sell * 1.5:
            oversize.append((mid, r["ingredient_key"], r["amount"], r["unit"], line, sell))
            all_priced = False
            cur.execute("UPDATE menu_ingredients SET line_cost=NULL WHERE id=?", (r["id"],))
            continue
        cur.execute("UPDATE menu_ingredients SET line_cost=? WHERE id=?", (line, r["id"]))
        total += line
        updated_lines += 1
    # 모든 재료 가격이 있고 총액이 정상 범위(판매가의 5~120%)일 때만 est_cost/원가율 갱신
    if all_priced and rows and sell and (sell * 0.05 <= total <= sell * 1.2):
        ratio = round(total / sell * 100, 1)
        cur.execute("UPDATE menus SET est_cost=?, cost_ratio=? WHERE id=?", (total, ratio, mid))
        recomputed_menus += 1
    # 매장 원가(store_cost/store_ratio) — 동일 조건
    if w_priced and rows and sell and (sell * 0.03 <= w_total <= sell * 1.2):
        cur.execute("UPDATE menus SET store_cost=?, store_ratio=? WHERE id=?",
                    (w_total, round(w_total / sell * 100, 1), mid))
        store_menus += 1

con.commit()
print(f"라인가격 갱신: {updated_lines}건, 전체가격 메뉴 총액 재계산: {recomputed_menus}개, 매장원가 계산: {store_menus}개")

# ⚠️ 스킵 리포트 — 조용히 넘어가면 원가가 틀린 채로 발행된다
if unit_errors:
    print(f"\n⚠️ 단위 불일치로 스킵 {len(unit_errors)}건 (재료 base_unit ≠ 메뉴 unit → 데이터 수정 필요)")
    for mid, k, a, u, base in unit_errors[:10]:
        nm = cur.execute("SELECT name FROM menus WHERE id=?", (mid,)).fetchone()[0]
        print(f"   [{mid}] {nm}: {k} {a:g}{u} (base={base})")
if oversize:
    print(f"\n⚠️ 판매가 1.5배 초과로 스킵 {len(oversize)}건 (단가·양 확인 필요)")
    for mid, k, a, u, line, sell in oversize[:10]:
        nm = cur.execute("SELECT name FROM menus WHERE id=?", (mid,)).fetchone()[0]
        print(f"   [{mid}] {nm}: {k} {a:g}{u} → {line:,}원 (판매가 {sell:,})")
if no_price:
    print(f"\n⚠️ 소매값이 없어 스킵 {len(no_price)}건 (쿠팡 상품도 manual_price 도 없음 — 사람이 고를 차례)")
    seen_np = []
    for mid, k in no_price:
        if k in seen_np:
            continue
        seen_np.append(k)
        nm = cur.execute("SELECT name FROM menus WHERE id=?", (mid,)).fetchone()[0]
        iname = cur.execute("SELECT name FROM ingredients WHERE ingredient_key=?", (k,)).fetchone()
        print(f"   {k:24} {(iname['name'] if iname else '?')[:26]:26} 예: [{mid}] {nm}")
    print("   (도매 라인은 정상 계산됐다 — 도매·소매는 별도 트랙)")
if not unit_errors and not oversize and not no_price:
    print("✅ 스킵된 라인 없음")
# 샘플
r = cur.execute("SELECT name,est_cost,cost_ratio FROM menus WHERE name LIKE '%허니콤보%'").fetchone()
print(f"교촌 허니콤보: 재료비 {r['est_cost']:,} / 원가율 {r['cost_ratio']}%")
con.close()
