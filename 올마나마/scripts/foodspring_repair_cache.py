# -*- coding: utf-8 -*-
"""식봄 캐시의 won_per_kg 를 고친 파서로 재계산한다 (2026-07-25 신설).

배경: 옛 pack_kg() 가 이름의 첫 kg/g 숫자만 읽어서 "5kg2팩"·"2.5kg*6입 15Kg/BOX" 같은
묶음 상품의 kg당 단가가 통째로 틀렸다. 우리는 "받을 수 있는 최저가"를 쓰므로
**버그로 낮게 나온 행이 자동 채택**돼 원가가 틀어졌다.

파서 원본은 `공통모듈\foodspring\foodspring_collect.py`. 여기선 그걸 복사해 쓴다
(공통모듈 규칙: 원본을 import 하지 말고 복사).

    python scripts/foodspring_repair_cache.py           # 무엇이 바뀌는지 보기만
    python scripts/foodspring_repair_cache.py --write    # 실제로 캐시 갱신
"""
import glob
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE, "data", "research", "foodspring")

# ── 공통모듈 원본에서 복사한 파서 ─────────────────────────────────
KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I)
G = re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.I)
_UNIT_KG = {"kg": 1.0, "g": 0.001, "l": 1.0, "ml": 0.001}
_MULT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*x×X]?\s*(\d+)\s*"
    r"(?:개입|개|입|팩|봉지|봉|매|장|ea|병|캔|포|pack)", re.I)
_BOX = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g)\s*/\s*(?:box|박스)", re.I)
_PAREN = re.compile(r"[(\[]\s*(\d+(?:\.\d+)?)\s*(kg|g)\s*[)\]]", re.I)
_HINT = re.compile(r"\d+\s*(?:개입|입|팩|봉지|봉|매|장|ea|병|캔|포)|/\s*(?:box|박스)", re.I)


def pack_kg(name):
    n = (name or "").replace(",", "")
    cands = []
    m = _MULT.search(n)
    if m:
        base = float(m.group(1)) * _UNIT_KG[m.group(2).lower()]
        cands.append((base * int(m.group(3)), "배수 %s%s×%s" % (m.group(1), m.group(2), m.group(3))))
    m = _BOX.search(n)
    if m:
        cands.append((float(m.group(1)) * _UNIT_KG[m.group(2).lower()], "BOX총량 " + m.group(0)))
    m = _PAREN.search(n)
    if m:
        cands.append((float(m.group(1)) * _UNIT_KG[m.group(2).lower()], "괄호총량 " + m.group(0)))
    if cands:
        return max(cands)
    m = KG.search(n)
    if m:
        return float(m.group(1)), "단일 kg"
    m = G.search(n)
    if m:
        return float(m.group(1)) / 1000.0, "단일 g"
    m = re.search(r"(\d+(?:\.\d+)?)\s*g(?![a-z가-힣])", n, re.I)
    if m:
        return float(m.group(1)) / 1000.0, "단일 g(경계없음)"
    return None, None


def pack_suspect(name, kg, how, wpk):
    if kg is None:
        return "중량 파싱 실패"
    if how and how.startswith("단일") and _HINT.search(name or ""):
        return "이름에 묶음 표기가 있는데 배수를 못 읽음"
    if wpk is not None and wpk < 300:
        return "kg당 %d원 — 업소용 식자재로 비현실적" % wpk
    return None


# ── 캐시 순회 ────────────────────────────────────────────────────
WRITE = "--write" in sys.argv
changed, total, suspects = [], 0, []


def fix(node):
    """가격 행 하나를 제자리에서 고친다. 바뀌면 True."""
    global total
    name = node.get("name")
    sp = node.get("sale_price") or node.get("price") or node.get("salePrice")
    if not name or not sp:
        return False
    total += 1
    kg, how = pack_kg(name)
    wpk = round(sp / kg) if kg else None
    sus = pack_suspect(name, kg, how, wpk)
    old = node.get("won_per_kg")
    node["pack_kg"] = kg
    node["pack_how"] = how
    node["won_per_kg"] = wpk
    node["suspect"] = sus
    if sus:
        suspects.append((name, wpk, sus))
    if old != wpk:
        changed.append((name, old, wpk, how))
        return True
    return False


def walk(o, group=None, bucket=None):
    """bucket 에는 같은 카테고리/검색어 묶음의 행들을 모아둔다(이상치 판정용)."""
    n = 0
    if isinstance(o, dict):
        if "name" in o and ("won_per_kg" in o or "sale_price" in o):
            n += 1 if fix(o) else 0
            if bucket is not None:
                bucket.append(o)
        else:
            for k, v in o.items():
                # dict 키가 카테고리 경로(예: "치즈.유가공품>치즈")면 그게 묶음이다
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    b = []
                    n += walk(v, str(k), b)
                    GROUPS.append((str(k), b))
                else:
                    n += walk(v, group, bucket)
    elif isinstance(o, list):
        for v in o:
            n += walk(v, group, bucket)
    return n


# ── 이상치 판정 (2026-07-25) ──────────────────────────────────────
#  파싱을 고쳐도 **원 데이터 자체가 이상한 행**이 남는다.
#  예: "돈등심 국내산 5kg2팩" 은 배수를 고치면 900원/kg 이 되는데, 국내산 돼지 등심이
#      kg당 900원일 수는 없다(실제 도매 6,000~8,000원). 판매가 자체가 1팩 값으로 보인다.
#  우리는 "받을 수 있는 최저가"를 쓰므로 이런 행이 **자동으로 채택된다.** 그래서
#  같은 카테고리 중앙값의 35% 미만이면 의심으로 찍어 최저가 후보에서 뺀다.
GROUPS = []
OUTLIER_RATIO = 0.35


def mark_outliers():
    n = 0
    for cat, rows in GROUPS:
        vals = sorted(r["won_per_kg"] for r in rows if r.get("won_per_kg"))
        if len(vals) < 5:
            continue
        med = vals[len(vals) // 2]
        cut = med * OUTLIER_RATIO
        for r in rows:
            w = r.get("won_per_kg")
            if w and w < cut and not r.get("suspect"):
                r["suspect"] = "카테고리 중앙값(%s원)의 35%% 미만 — 원 데이터 의심" % format(med, ",")
                suspects.append((r["name"], w, r["suspect"]))
                n += 1
    return n


for fp in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
    try:
        d = json.load(io.open(fp, encoding="utf-8"))
    except Exception as e:
        print("  (읽기 실패 %s: %s)" % (os.path.basename(fp), e))
        continue
    GROUPS[:] = []
    n = walk(d)
    ol = mark_outliers()
    print("  %-28s %d행 수정 · 이상치 %d행" % (os.path.basename(fp), n, ol))
    if WRITE and (n or ol):
        with io.open(fp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)

print()
print("전체 %d행 중 %d행 단가 변경 · 의심 %d행" % (total, len(changed), len(suspects)))
print()
print("=== 변경 폭 큰 것 30개 (옛값 → 새값) ===")
def _mag(x):
    _, o, n2, _h = x
    if not o or not n2:
        return 0
    return max(o, n2) / max(1, min(o, n2))
for name, o, n2, how in sorted(changed, key=_mag, reverse=True)[:30]:
    print("   %9s → %9s  (%-18s) %s" % (
        format(o, ",") if o else "-", format(n2, ",") if n2 else "-", how or "-", (name or "")[:52]))

print()
print("=== 의심 행 상위 20 (최저가 자동채택에서 빼야 하는 것) ===")
for name, wpk, sus in sorted(suspects, key=lambda x: x[1] or 0)[:20]:
    print("   %9s원/kg  %-34s %s" % (format(wpk, ",") if wpk else "-", sus[:34], (name or "")[:44]))

if not WRITE:
    print()
    print("※ 보기만 했다. 실제로 고치려면  --write  를 붙여라.")
