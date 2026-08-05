# -*- coding: utf-8 -*-
# 레시피 재료명 → ingredients 테이블 매칭 엔진 (2026-07-20)
#
# 왜 필요한가: OpenAI가 만든 레시피는 재료를 **사람 말**로 쓴다("생중화면", "강력분", "통닭").
#   우리 DB는 ingredient_key로 돌아간다. 실측(6종)에서 고유 재료 52종 중 21종이 안 맞았다.
#   손으로 매번 이으면 관리페이지를 만든 의미가 없어서, 자동 매칭 + 별칭 학습으로 줄인다.
#
# 매칭 순서: 물자동 → 정확 → 별칭 → 정규화 → 부분포함 → 퍼지(difflib)
#   사람이 고른 결과는 ingredient_alias에 저장돼 **다음 요리부터 자동**으로 잡힌다.
#
# ⚠️ Flask·OpenAI에 의존하지 않는다. CLI로 단독 검증할 수 있어야 한다:
#     python scripts/recipe_mapping.py            # _recipes/*.md 전부 드라이런
#     python scripts/recipe_mapping.py jjajangmyeon
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import admin_store as st          # noqa: E402
from apply_recipe_md import parse  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "_recipes")

# 물 계열 — 전부 water(0원)로. 실측 7종: 면 삶는 물/미지근한 물/밥 짓는 물/손 적실 물/
#   전분물용 물/찬물/김치국물. 사람에게 묻지 않는다.
#   🔴 **얼음·생수도 물이다**(2026-08-03 · 우리의식탁 77건). 「생수」를 사서 넣는 게 아니라
#      수돗물·정수기 물이고, 얼음은 그 물을 얼린 것이다. 원가 0.
#   ⛔ **「물」로 끝난다고 물이 아니다** — `(물)$` 하나로 **콩나물·숙주나물·세발나물·돌나물·
#      시래기나물·명이나물·김칫국물·사골국물·전분물·달걀물**이 전부 `water`(0원)로 잡혔다
#      (2026-08-03 · 우리의식탁 61종 119건). 아래 `NOT_WATER` 가 **먼저** 이긴다.
#      ⚠️ 「다시마 우린 물」·「쌀뜨물」·「차가운 물」은 **그대로 물이다** — 건드리지 않았다.
NOT_WATER = re.compile(r"(나물|국물|원물|해산물)$|^전분\s*물|^(달걀|계란)\s*물")
WATER_PAT = re.compile(r"(물|육수용\s*물|김치\s*국물)$|^물$|물\s*\d*ml"
                       r"|^얼음|^생수|^정수|^찬물|^끓는\s*물|^뜨거운\s*물|^따뜻한\s*물|^미지근")

# 🔴 **한 칸에 재료가 둘** — `소금, 후추` 처럼 쉼표·마침표로 묶여 온다(2026-08-03 · 218건).
#    ⛔ **앞것만 잡으면 안 된다.** 소금과 후추는 다른 재료다 — 뒤엣것이 원가에서 통째로 빠진다.
#       (대표 지적 2026-08-03: *"소금 후추가 다른 건데 따로따로 잡아야지"*)
#    → `split_pair()` 가 **둘 다** 돌려주고, 부르는 쪽에서 각각 재료로 잡는다.
SPLIT_PAIR = re.compile(r"^([가-힣]{2,12})[\s]*[,.·/][\s]*([가-힣\s]{2,14})$")


def split_pair(raw):
    """`소금, 후추` → ['소금','후추']. 한 칸이면 [] 를 돌려준다."""
    m = SPLIT_PAIR.match((raw or "").strip())
    if not m:
        return []
    return [m.group(1).strip(), m.group(2).strip()]


def split_amount(amount, n):
    """한 칸에 재료가 n개면 **양도 나눈다** — `소금, 후추 5g` → 소금 2.5g + 후추 2.5g.
    (대표 지시 2026-08-03: *"소금후추 5그램이면 소금 2.5 후추 2.5g 이런 식으로 나눠 쓰면 되는 걸"*)
    ⛔ 한쪽에 몰아주면 안 된다 — 뒤엣것이 원가에서 통째로 빠진다."""
    try:
        a = float(amount)
    except (TypeError, ValueError):
        return None
    return round(a / max(1, n), 4)

# 🔴 **육수는 재료로 되돌린다** — `멸치 다시마 육수` 는 상품이 아니라 «다시마+멸치로 낸 것».
#    우리의식탁 192건. 다시마를 대표 재료로 잡는다(멸치는 종류가 갈려 따로 못 정한다).
BROTH_PAT = re.compile(r"(다시마|멸치|가쓰오|가츠오|디포리).*육수|육수.*(다시마|멸치)"
                       r"|^(채수|야채육수|채소육수)$")
# 닭 육수는 닭으로 — 다시마가 아니다
BROTH_CHICKEN = re.compile(r"^(닭\s*육수|치킨스톡|치킨\s*스톡|닭\s*국물)$")

# 🔴 **밥은 쌀이다** — 밥 218건. 지은 밥 200g ≈ 쌀 90g 이라 **양 환산이 필요**하지만,
#    지금은 재료 연결만 한다(양 환산은 원가 계산 쪽에서 별도).
RICE_PAT = re.compile(r"^(밥|현미밥|찬밥|공기밥|따뜻한\s*밥|불린\s*쌀|불린쌀|쌀밥)$")

# 첫 실행 시 심는 별칭 — 실측에서 나온 것들. 이후 사람이 고른 건 source='human'으로 누적된다.
SEED_ALIASES = {
    "강력분": "cg_flour_strong", "중력분": "cg_flour_medium",
    "밀가루": "cg_flour_medium", "부침가루": "cg_flour_medium",
    "생중화면": "noodles_fresh", "중화면": "noodles_fresh",
    "통닭": "raw_chicken_10", "토막닭": "raw_chicken_10", "생닭": "raw_chicken_10",
    "횟감용연어": "salmon_raw", "연어": "salmon_raw",
    "양송이버섯": "at_양송이버섯",
    "돼지고기다짐육": "x_e6d782c93c", "다진돼지고기": "x_e6d782c93c",
    "치킨튀김가루": "frying_powder", "튀김가루": "frying_powder",
    "감자전분": "x_80310d61c8", "전분": "x_80310d61c8", "옥수수전분": "x_80310d61c8",
    "다진마늘": "garlic_minced", "간마늘": "garlic_minced",
    "설탕": "cg_sugar_white", "백설탕": "cg_sugar_white",
    "진간장": "cg_soy_sauce_jin", "간장": "cg_soy_sauce_jin",
    "식용유": "cg_cooking_oil", "카놀라유": "cg_cooking_oil", "대두유": "cg_cooking_oil",
    "춘장": "sauce_jjajang", "고추장": "cg_gochujang", "된장": "cg_doenjang",
    "참기름": "cg_sesame_oil", "소금": "cg_salt", "꽃소금": "cg_salt",
    "우유": "milk", "모짜렐라치즈": "mozzarella_cheese", "피자치즈": "mozzarella_cheese",
    "대파": "kv_246", "파": "kv_246", "양파": "kv_245", "당근": "kv_232",
    "애호박": "aehobak_mart", "양배추": "yangbaechu_mart", "감자": "kv_152",
    "쌀": "rice_uncooked", "백미": "rice_uncooked",
    # 2차 드라이런에서 추가로 잡힌 것들
    "배추김치": "kimchi_fresh", "포기김치": "kimchi_fresh", "신김치": "kimchi_fresh",
    "빨강파프리카": "kv_256", "파프리카": "kv_256",
    "닭다리살": "chicken_boneless", "닭가슴살": "chicken_breast",
    "돼지고기목살": "x_1294333d76", "삼겹살": "pork_belly_import",
    "두부": "x_cee737406a", "떡볶이떡": "tteok", "어묵": "fish_cake",
    "김": "gim", "미역": "kv_642", "달걀": "egg_fresh", "계란": "egg_fresh",
}

# 튀김 흡유율 — 냄비에 부은 기름 중 실제로 음식에 흡수되는 비율.
#  지시서가 10~15%로 제시. 중간값 12%를 쓴다. 나머지는 남아서 다시 쓰거나 버린다.
FRY_ABSORB = 0.12

# 개 단위 재료의 표준 중량(kg) — 레시피가 g으로 적었을 때 개수로 되돌린다.
#  추측이 아니라 통용 규격: 계란 특란 60g, 버거번 60g, 핫도그빵 55g, 파인애플 1.2kg 등
PIECE_WEIGHT = {
 "egg_fresh": 0.06, "burger_bun": 0.06, "hotdog_bread": 0.055,
 "kv_420": 1.2, "noodles_ramen": 0.11, "takeout_cup": 0.02,
}

_STRIP_WORDS = ("국산", "국내산", "수입", "냉동", "냉장", "시판", "손질", "생", "삶은",
                "다진", "썬", "채썬", "얇게", "굵은", "곱게", "잘게")


def normalize(s):
    """비교용 정규화 — 괄호·브랜드·용량·공백·수식어 제거.

    ⚠️ **괄호 안이 통째로 날아간다.** 그래서 `밀가루(중력분)` 과 `밀가루(박력분)` 이
       둘 다 `밀가루` 가 되어 충돌한다 — 별칭으로 넣으면 **나중에 넣은 것이 이긴다**
       (2026-08-03: 「밀가루」가 박력분으로 붙었다).
       👉 **별칭에는 괄호 표기를 쓰지 마라.** `중력분`·`박력분` 처럼 구분되는 낱말로 넣는다.
    """
    s = re.sub(r"\(.*?\)", "", s or "")          # (해표 900ml) 같은 괄호
    s = re.sub(r"\d+(\.\d+)?\s*(kg|g|ml|L|개|장|모|봉|구|매)", "", s, flags=re.I)
    for w in _STRIP_WORDS:
        s = s.replace(w, "")
    return re.sub(r"[\s·,/]", "", s).strip()


class Matcher:
    def __init__(self, c=None):
        self.c = c or st.conn()
        st.init(self.c)
        self._seed()
        rows = self.c.execute("SELECT ingredient_key, name, display_name, base_unit "
                              "FROM ingredients").fetchall()
        self.by_name = {r["name"]: r["ingredient_key"] for r in rows}
        self.by_norm = {}
        for r in rows:                            # 정규화 충돌 시 먼저 온 것 유지
            self.by_norm.setdefault(normalize(r["name"]), r["ingredient_key"])
        # 🔴 **화면 이름(display_name)도 매칭에 쓴다** (2026-08-03 신설).
        #    `name` 만 보면 화면에 나가는 말로 찾을 수 없다 — 실제로 `kv_243` 은
        #    name 이 「붉은고추」이고 display_name 이 「홍고추」인데, 레시피가 쓰는 말은
        #    「홍고추」라서 **249건이 통째로 미매칭**이었다(우리의식탁 대조).
        #    `name` 을 덮지 않도록 setdefault 로만 넣는다.
        for r in rows:
            d = (r["display_name"] or "").strip()
            if d:
                self.by_norm.setdefault(normalize(d), r["ingredient_key"])
        self.base_unit = {r["ingredient_key"]: r["base_unit"] for r in rows}
        self.names = [r["name"] for r in rows]
        # 🔴 **없는 재료를 가리키는 별칭은 버린다**(고아 별칭 · 2026-08-03).
        #    재료가 지워졌는데 별칭이 남아 `cg_flour_medium`·`kv_246` 을 가리켰고,
        #    매칭은 «성공»으로 잡히는데 값이 없어 **레시피 252개가 조용히 빠졌다.**
        have = {r["ingredient_key"] for r in rows}
        self.alias = {}
        self.alias_orphan = []
        for r in self.c.execute("SELECT alias_norm, alias_raw, ingredient_key FROM ingredient_alias"):
            if r["ingredient_key"] in have:
                self.alias[r["alias_norm"]] = r["ingredient_key"]
            else:
                self.alias_orphan.append((r["alias_raw"], r["ingredient_key"]))

    def _seed(self):
        have = {r[0] for r in self.c.execute("SELECT ingredient_key FROM ingredients")}
        for raw, key in SEED_ALIASES.items():
            if key in have:
                self.c.execute("""INSERT INTO ingredient_alias(alias_norm,alias_raw,ingredient_key,source,created_at)
                    VALUES(?,?,?,'seed',?) ON CONFLICT(alias_norm) DO NOTHING""",
                    (normalize(raw), raw, key, st.now()))
        self.c.commit()

    # ── 단일 재료명 → 후보 ────────────────────────────────────────
    def match(self, raw):
        """→ dict(key, how, score, candidates). key=None이면 미매칭."""
        n = normalize(raw)
        if (WATER_PAT.search(raw) and not NOT_WATER.search(raw)) or n in ("물", ""):
            return {"key": "water", "how": "물자동", "score": 1.0, "candidates": []}
        # 한 칸에 둘 (`소금, 후추`) → **둘 다** 돌려준다. 앞것만 잡으면 뒤엣것이 원가에서 빠진다.
        pair = split_pair(raw)
        if pair:
            keys = [self.match(p)["key"] for p in pair]
            keys = [k for k in keys if k]
            if keys:
                return {"key": keys[0], "keys": keys, "parts": pair,
                        "how": "한칸둘", "score": 0.9, "candidates": []}
        # 닭 육수 → 치킨스톡
        if BROTH_CHICKEN.match(raw.strip()):
            for nm in ("태태락 치킨스톡", "치킨스톡"):
                k = self.by_name.get(nm) or self.by_norm.get(normalize(nm))
                if k:
                    return {"key": k, "how": "닭육수", "score": 0.85, "candidates": []}
        # 육수 → 다시마
        if BROTH_PAT.search(raw):
            for nm in ("건다시마", "다시마"):
                k = self.by_name.get(nm) or self.by_norm.get(normalize(nm))
                if k:
                    return {"key": k, "how": "육수→다시마", "score": 0.85, "candidates": []}
        # 밥 → 쌀  (⚠️ 지은 밥 200g ≈ 쌀 90g — 양 환산은 원가 계산 쪽에서)
        if RICE_PAT.match(raw.strip()):
            k = self.by_name.get("쌀") or self.by_norm.get(normalize("쌀"))
            if k:
                return {"key": k, "how": "밥→쌀", "score": 0.9, "candidates": []}
        if raw in self.by_name:
            return {"key": self.by_name[raw], "how": "정확", "score": 1.0, "candidates": []}
        if n in self.alias:
            return {"key": self.alias[n], "how": "별칭", "score": 1.0, "candidates": []}
        if n in self.by_norm:
            return {"key": self.by_norm[n], "how": "정규화", "score": 1.0, "candidates": []}
        # 부분 포함 — "양송이버섯" ⊂ "양송이버섯(경락)"처럼 **거의 같은 말**일 때만.
        # 🔴 길이 비율을 안 보면 프로젝트 노트의 그 함정이 재현된다("콩"이 "킹콩모둠햄"에).
        #    실제로 "쌀"⊂"쌀식초" → 쌀식초가 쌀로, "고추"⊂"고추냉이" → 고추냉이가 생고추로 갔다
        #    (2026-07-20). 짧은 쪽이 긴 쪽의 70% 이상일 때만 같은 재료로 본다.
        subs = []
        for nm in self.names:
            m2 = normalize(nm)
            if not n or not m2 or len(n) < 2 or len(m2) < 2:
                continue
            if n in m2 or m2 in n:
                if min(len(n), len(m2)) / max(len(n), len(m2)) >= 0.7:
                    subs.append(nm)
        if len(subs) == 1:
            return {"key": self.by_name[subs[0]], "how": "부분일치", "score": 0.95, "candidates": []}
        # 퍼지
        cands = []
        for nm in self.names:
            r = difflib.SequenceMatcher(None, n, normalize(nm)).ratio()
            if r >= 0.55:
                cands.append((r, nm))
        cands.sort(reverse=True)
        if cands and cands[0][0] >= 0.85:
            return {"key": self.by_name[cands[0][1]], "how": f"퍼지 {cands[0][0]:.2f}",
                    "score": cands[0][0], "candidates": [n for _, n in cands[:4]]}
        return {"key": None, "how": "미매칭", "score": cands[0][0] if cands else 0,
                "candidates": [n for _, n in cands[:4]] or subs[:4]}

    # ── 분량 파싱 + 단위 검증 ─────────────────────────────────────
    @staticmethod
    def parse_amount(txt):
        m = re.match(r"^([\d,.]+)\s*(kg|g|ml|L|개|장|모|봉|구|매)", (txt or "").strip(), re.I)
        if not m:
            return None, None
        return float(m.group(1).replace(",", "")), m.group(2)

    def unit_ok(self, key, unit):
        """healthcheck.py의 'dish 재료 base_unit ≠ dish unit' 규칙과 같은 판정.
        여기서 막아야 DB를 다 쓴 뒤 배포 관문에서 안 터진다."""
        b = self.base_unit.get(key)
        if not b or not unit:
            return False
        if b in ("kg", "L"):
            return unit.lower() in ("g", "ml", "kg", "l")
        return unit == b                       # 개 단위는 개끼리만

    def to_piece(self, key, amount, unit, note=""):
        """개 단위 재료를 g으로 적었을 때 개수로 환산 (2026-07-20).

        레시피가 "달걀 50g (1개)"처럼 쓰는데 우리 달걀은 개당 단가다.
        그대로 두면 단위 불일치로 반영이 막히고, 억지로 넣으면 원가가 수십 배가 된다.
        ① 비고의 "(N개)"를 먼저 보고 ② 없으면 표준 중량으로 나눈다.
        """
        if self.base_unit.get(key) != "개" or unit not in ("g", "ml") or not amount:
            return amount, unit
        m = re.search(r"(\d+(?:\.\d+)?)\s*개", note or "")
        if m:
            return float(m.group(1)), "개"
        w = PIECE_WEIGHT.get(key)
        if w:
            # ⚠️ amount는 g/ml, PIECE_WEIGHT는 kg/L다. 환산을 빼먹으면 1000배가 된다.
            #   실제로 "달걀 50g"이 833개가 되어 탕수육 원가가 22만원으로 나왔다(2026-07-20).
            n = (amount / 1000.0) / w
            n = max(0.5, round(n * 2) / 2)      # 0.5개 단위로 반올림
            return n, "개"
        return amount, unit          # 모르면 그대로 둔다 → 단위 불일치로 사람에게 넘어간다

    # ── 레시피 전체 매핑 ──────────────────────────────────────────
    def map_recipe(self, ing_groups):
        """→ rows[], 동일 키는 g/ml로 환산해 합산."""
        rows = []
        for g in ing_groups:
            for it in g["items"]:
                amt, unit = self.parse_amount(it["amount"])
                m = self.match(it["name"])
                # ★ 튀김용 기름은 냄비에 붓는 양이지 먹는 양이 아니다(2026-07-20).
                #   그대로 넣으면 탕수육 기름값만 6,543원이 된다(실측). 흡수분만 계산한다.
                #   지시서 §: "튀김·조림용 기름은 총량을 적되 '(튀김용)'을 표기하라" → 그 표기를 본다.
                _tag = (it.get("note", "") or "") + " " + (it.get("amount", "") or "")
                if m["key"] and "튀김용" in _tag and amt:
                    m = {"key": "frying_oil", "how": "튀김흡수분", "score": 1.0, "candidates": []}
                    amt = round(amt * FRY_ABSORB)
                elif m["key"]:          # 개 단위 재료를 g으로 적은 경우 환산
                    amt, unit = self.to_piece(m["key"], amt, unit, it.get("note", ""))
                # 🔴 **한 칸에 재료가 둘이면 행을 나누고 양도 나눈다** (2026-08-03 대표 지시)
                #    `소금, 후추 5g` → 소금 2.5g + 후추 2.5g.
                #    앞것에 몰아주면 뒤엣것이 원가에서 통째로 빠진다.
                if len(m.get("keys") or []) > 1:
                    ks, parts = m["keys"], (m.get("parts") or [])
                    each = split_amount(amt, len(ks))
                    for i2, k2 in enumerate(ks):
                        a2, u2 = each, unit
                        if a2 is not None:
                            a2, u2 = self.to_piece(k2, a2, unit, it.get("note", ""))
                        rows.append({"raw": (parts[i2] if i2 < len(parts) else it["name"]),
                                     "group": g["group"], "amount": a2, "unit": u2,
                                     "amount_raw": it["amount"], "key": k2,
                                     "how": "한칸둘(%d분할)" % len(ks), "score": m["score"],
                                     "candidates": [],
                                     "unit_ok": self.unit_ok(k2, u2)})
                    continue
                rows.append({"raw": it["name"], "group": g["group"], "amount": amt, "unit": unit,
                             "amount_raw": it["amount"], **m,
                             "unit_ok": self.unit_ok(m["key"], unit) if m["key"] else False})
        # 동일 키 합산 (짜장면 진간장: 양념 10ml + 밑간 5ml = 15ml)
        merged, order = {}, []
        for r in rows:
            k = r["key"]
            if not k:
                order.append(r); continue
            if k in merged:
                if r["amount"] and merged[k]["amount"] and r["unit"] == merged[k]["unit"]:
                    merged[k]["amount"] += r["amount"]
                    merged[k]["parts"].append(f'{r["group"]} {r["amount_raw"]}')
                continue
            r["parts"] = [f'{r["group"]} {r["amount_raw"]}']
            merged[k] = r; order.append(r)
        return order


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    mt = Matcher()
    tot = miss = 0
    allmiss = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        if only and slug != only:
            continue
        d = parse(open(os.path.join(SRC, fn), encoding="utf-8").read())
        rows = mt.map_recipe(d["ing_groups"])
        m = [r for r in rows if not r["key"]]
        bad_unit = [r for r in rows if r["key"] and not r["unit_ok"]]
        tot += len(rows); miss += len(m)
        allmiss += [r["raw"] for r in m]
        print(f"{slug:16s} 재료 {len(rows):2d}종 · 미매칭 {len(m):2d} · 단위불일치 {len(bad_unit):2d}")
        if only:
            for r in rows:
                mark = "❌" if not r["key"] else ("⚠️" if not r["unit_ok"] else "✅")
                print(f"   {mark} {r['raw']:20s} {str(r['amount_raw']):10s} → "
                      f"{r['key'] or '(미매칭)':22s} [{r['how']}]"
                      + (f"  후보: {', '.join(r['candidates'][:3])}" if not r["key"] and r["candidates"] else "")
                      + (f"  합산: {' + '.join(r['parts'])}" if r.get("parts") and len(r["parts"]) > 1 else ""))
    print(f"\n=== 합계: {tot}줄 · 미매칭 {miss}줄 ===")
    if allmiss:
        print("미매칭 목록:", ", ".join(sorted(set(allmiss))))


if __name__ == "__main__":
    main()
