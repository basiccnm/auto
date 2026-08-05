# -*- coding: utf-8 -*-
"""정육 154건(업소용 식자재몰 2026-07-24 수집)을 ingredients 에 반영한다.

정책은 app_apply.py 와 같다.
  도매 = 앱 **상시 판매가**. 쿠폰가는 쓰지 않는다.
  소매 = 건드리지 않는다. 이 수집은 도매 축이라 소매를 만들 근거가 없다.

기존 육류 도매값 상당수가 `coef085(축산물) ×0.70` 또는 `조사 고정단가(출처 비공개)`였다.
전부 추정이라 실제 업소 매입가와 20~40% 어긋난다.

⚠️ 등급·원산지가 갈리는 품목(한우/육우, 국산 닭)은 지금 DB 구조로 나눌 수 없어 SKIP 에 둔다.
   구조를 정한 뒤(§8) 다시 붙인다. SKIP 은 반드시 이유와 함께 남긴다.
"""
import json, io, os, sqlite3, sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "research", "meat154.json")
STAMP = "2026-07-25"
SRC_LABEL = "업소용 식자재몰"      # 거래처 상호는 쓰지 않는다 (원칙 §3)

# 재료키 → 앱 상품명(전체 일치). 같은 물건임이 확인된 것만 넣는다.
APPLY = {
    # ── 닭 (기존값 전부 '조사 고정단가(출처 비공개)' = 근거 불명) ──
    "chicken_breast":  "닭가슴살 (130±10g/덩어리 껍질제거, 1Kg/EA)",
    "chicken_parts":   "닭봉 (45±5g/개 껍질있음, 1Kg/EA)",          # 윙도 같은 11,100
    "chicken_boneless": "동우 닭다리살 (100±10g/덩어리 껍질있음, 2Kg/EA)",
    "raw_chicken_8":   "통닭 (목팁미지제거 1kg±50g/마리 껍질있음, 1Kg/EA)",
    "nc_1415849ca7":   "동우 닭도리 (50±5g/조각 껍질있음, 1Kg/EA)",
    # ── 돼지 ──
    "x_2458074f8e":    "돈등뼈 (탕용 6~7cm 절단, 비닐+박스포장 1Kg/EA)",
    "x_e6d782c93c":    "산우들 돈잡육민찌 (민찌작업_실링+박스포장 다짐볶음용 1Kg/EA)",
    "pork_belly_import": "AURORA 돈삼겹 (25Kg/BOX)",
    "pork_front_leg":  "돈전지 (6*5*0.3cm유형_슬라이스 제육용 1Kg/EA)",
    "x_1294333d76":    "돈전지 (3mm두께_단순슬라이스 다용도용 1Kg/EA)",
    "x_2255eba1be":    "산우들 돈등심 (0.8cm두께_슬라이스+연육작업 돈까스용 1Kg/EA)",
    "x_80a38156df":    "돈오돌뼈 (제육용 3mm, 실링+박스포장 1Kg/EA)",
    # ── 소 ──
    "x_ffd92fa2a9":    "소다짐육 (다짐육_비닐+박스포장 볶음용 1Kg/EA)",
    "beef_bulgogi":    "소볼라전각 (S등급 6*5*0.3cm유형_슬라이스 불고기용 1Kg/EA)",
}

SKIP = {
    "hanwoo_galbi":     "한우 갈비 — 앱에 한우 갈비가 없다. 소탕갈비(11,200)는 원산지 무표기라 한우로 못 쓴다",
    "kv_4401":          "소고기 등심 — 앱 스테이크류는 부채살·척아이롤·살치살이라 부위가 다르다",
    "beef_cube_steak":  "소고기 큐브스테이크 — 앱의 '크레잇 큐브스테이크'는 돈육이다. 소가 아니다",
    "chicken_leg_import": "태국산 조각 닭정육 — 원산지가 재료명에 박혀 있는데 앱 상품은 원산지 무표기",
    "raw_chicken_10":   "염지닭 10호 — 앱에 염지 제품이 없다(생닭뿐)",
    "chicken_feet_bone": "닭발 — 앱 목록에 없다",
    "chicken_feet":     "무뼈닭발 — 앱 목록에 없다",
    "pork_trotter":     "족발 생육 — 앱 목록에 없다(돈족 미취급)",
    "x_hangjeong":      "항정살 — 앱 목록에 없다",
    "pork_stomach":     "오소리감투 — 앱 목록에 없다",
    "x_d191a7196b":     "돈족/머리고기 — 앱 목록에 없다",
    "x_118ff29a25":     "돈육다짐만두소 — 만두소는 배합품이라 민찌 단가로 대체하면 틀린다",
    "x_1c6f238f5f":     "라이스페이퍼만두돈육 — 위와 같음",
    "x_ad6cbb3b0c":     "매운고기 — 양념 가공품이라 원물 단가로 못 바꾼다",
    "x_32bd45bf24":     "함박고기 — 위와 같음",
    "x_gopchang":       "소곱창 — 앱 목록에 내장류가 없다",
    "x_c213e61e77":     "소대창 — 위와 같음",
    "x_ed9421040a":     "자숙소막창 — 위와 같음",
    "x_ca5d31e548":     "자숙특양 — 위와 같음",
    "x_10a10b8b9e":     "자숙소곱창/전골곱창 — 위와 같음",
    "beef_dogani":      "도가니 — 앱 목록에 없다",
    "x_cf6156c6d1":     "소꼬리수육고기 — 앱 목록에 없다",
}

# 앱에 있으나 우리 재료에 대응이 없어 이번엔 안 만든 것 (메뉴에 안 쓰여 추가 실익 없음)
UNUSED = ["닭안심 8,500", "닭뼈 1,200", "돈사골 1,400", "소햄버거패티 18,000",
          "한우정육(불고기) 25,100", "육우정육(불고기) 21,800", "EXCELBEEF 스테이크류"]


def won(s):
    return int(str(s).replace(",", "").replace("원", "").strip())


def pack_kg(name):
    """상품명 괄호에서 총 중량을 뽑는다. 못 뽑으면 None — 단위를 추측하지 않는다."""
    import re
    m = re.search(r"(\d+(?:\.\d+)?)\s*Kg\s*/\s*(?:BOX|EA)", name, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*g\s*/\s*EA", name, re.I)
    if m:
        return int(m.group(1)) / 1000.0
    return None


def main():
    dry = "--apply" not in sys.argv
    raw = json.load(io.open(SRC, encoding="utf-8"))
    by_name = {v[0]: (code, v) for code, v in raw.items()}

    c = sqlite3.connect(DB)
    cur = c.cursor()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print("%-22s %10s %10s %8s   %s" % ("재료", "도매(전)", "도매(후)", "변화", "근거 상품"))
    print("-" * 110)
    n = 0
    for key, pname in APPLY.items():
        hit = by_name.get(pname)
        if not hit:
            print("  ! %s — 수집분에 '%s' 이 없다" % (key, pname))
            continue
        code, v = hit
        kg = pack_kg(pname)
        if not kg:
            print("  ! %s — 상품명에서 중량을 못 읽었다: %s" % (key, pname))
            continue
        price = won(v[3])
        wp_new = round(price / kg)

        row = cur.execute("select name, base_unit, wholesale_price from ingredients "
                          "where ingredient_key=?", (key,)).fetchone()
        if not row:
            print("  ! %s — DB에 없는 재료키" % key)
            continue
        name, unit, wp_old = row
        if unit != "kg":
            print("  ! %s(%s) — base_unit 이 '%s' 다. kg 단가를 그대로 넣으면 안 된다" % (name, key, unit))
            continue

        pct = (wp_new - (wp_old or 0)) / (wp_old or 1) * 100
        print("%-22s %10s %10s %+7.0f%%   %s %s (%s원 / %sKg)" % (
            name, f"{wp_old or 0:,}", f"{wp_new:,}", pct, code, pname[:34], f"{price:,}", kg))

        basis = "%s %s %s %s — %s원 / %sKg = %s원/kg" % (
            SRC_LABEL, STAMP, code, pname, f"{price:,}", kg, f"{wp_new:,}")
        if not dry:
            cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, "
                        "updated_at=? where ingredient_key=?", (wp_new, basis, STAMP, key))
            cur.execute("insert into price_history(ingredient_key, price_date, retail_price, "
                        "source, created_at, wholesale_price) values(?,?,?,?,?,?)",
                        (key, STAMP, None, "app", now, wp_new))
        n += 1

    print("\n[반영 제외 — 이유]")
    for k, why in SKIP.items():
        print("  %s" % why)
    print("\n[앱에 있으나 대응 재료 없음 — 이번엔 안 만듦]")
    print("  " + " / ".join(UNUSED))

    if dry:
        print("\n※ 미리보기다. 실제로 쓰려면  python scripts/meat_apply.py --apply")
    else:
        c.commit()
        print("\n%d종 반영 완료." % n)


main()
