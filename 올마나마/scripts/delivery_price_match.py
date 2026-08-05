# -*- coding: utf-8 -*-
"""배달가 JSON 을 브랜드 골격 JSON 에 붙인다 — 브랜드 공용. 2026-07-31 신설

    python scripts/delivery_price_match.py <골격.json> <배달가.json>            # 미리보기
    python scripts/delivery_price_match.py <골격.json> <배달가.json> --apply    # 반영

🔴 왜 공용인가
   파리바게트·던킨에서 같은 매칭 코드를 두 번 새로 짰다. 브랜드가 달라도 하는 일은 늘 같다
   (대표 지적: *"매번 파이썬을 새로 짜다가 토큰만 태웠다"*).

붙이는 규칙 — 대표 지시 2026-07-31: *"비슷하거나 글씨가 살짝 다르고 띄어쓰기가 틀린건 다 붙여야함"*
   ① 완전일치(공백·기호 무시)
   ② 규격 꼬리·수식어를 떼고 다시 대조 — `(18cm)`·`(조각)`·`(5개입)`·`[NEW]`·`HMR`
   ③ 후보가 둘 이상이면 **붙이지 않고 보류로 내놓는다** — 사람이 값을 보고 정한다

🔴 단위기호를 **제일 먼저** 보통 글자로 바꾼다(㎖→ml, ℓ→l).
   안 그러면 `[^0-9a-z가-힣]` 에 지워져 「930㎖」가 「930」이 되고 「930ml」과 어긋난다
   (2026-07-31 아침엔후레쉬우유 4종이 이래서 빠졌다 — 대표가 직접 짚었다).
⛔ 사이즈가 다르면 붙이지 않는다 — 골격에 15cm/18cm 가 따로 있다. 조각과 홀케이크도 다른 줄.
⛔ 골격에 없는 메뉴는 **추가하지 않는다.** 공식 목록이 정본이다 (대표 지시: *"골격에 없는건 빼고"*).
⛔ 카테고리 제목(`/`·`#` 든 줄)은 메뉴가 아니다.
"""
import collections
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brand_price_fill import fill, norm                                # noqa: E402
# 카테고리 제목 판정은 **파서와 같은 것**을 쓴다 — 따로 두면 한쪽만 고쳐져 어긋난다
# (2026-07-31 얌샘: 파서는 고쳤는데 여기가 「치즈김밥1/2+참치김밥1/2」 를 계속 뺐다)
from brand_coupangeats_parse import is_cat_title                       # noqa: E402

SIZECM = re.compile(r"(\d+(?:\.\d+)?)\s*cm")
# 규격 꼬리 — 이름의 일부가 아니라 «몇 개들이·몇 cm» 표시다
SPEC = re.compile(r"[\(（]\s*(?:\d+(?:\.\d+)?\s*(?:cm|호|ml|l|g|개입|개|입|ea|조각)"
                  r"|조각|낱개|대|소|가성비|완제|시즌과일|1개)\s*[\)）]", re.I)


def base(s):
    """규격·수식어를 떼고 «같은 물건인가» 를 보는 키."""
    s = (s or "").lower()
    for a, b in (("㎖", "ml"), ("㎗", "dl"), ("ℓ", "l"), ("㎏", "kg"), ("㎝", "cm")):
        s = s.replace(a, b)                       # 🔴 단위기호부터 — 순서가 중요하다
    s = s.replace("아침&", "아침엔").replace("big", "빅").replace("멜론", "메론")
    s = re.sub(r"\[[^\]]*\]|\bnew\b|\bhmr\b|\bfresh\b|시즌과일|!", "", s)
    s = SPEC.sub("", s)
    return re.sub(r"[^0-9a-z가-힣]+", "", s)


def cm(s):
    return SIZECM.findall((s or "").replace("㎝", "cm"))


def match(skeleton_path, delivery_path, note=None, apply=False):
    """돌려주는 것: {filled, pairs, hold(후보 여럿), miss(골격에 없음), cattitle}"""
    dv = json.load(io.open(delivery_path, encoding="utf-8"))
    pm = {m["name"]: m["price"] for m in dv.get("prices", []) if m.get("price")}
    note = note or dv.get("note")
    cattitle = [n for n in pm if is_cat_title(n)]
    pm = {k: v for k, v in pm.items() if k not in cattitle}

    # ① 완전일치
    r1 = fill(skeleton_path, pm, source="delivery_coupangeats", note=note, dry=not apply)
    filled = r1["filled"]
    pairs = []

    # ② 규격·수식어를 떼고
    sk = json.load(io.open(skeleton_path, encoding="utf-8"))["menus"]
    openm = [m["name"] for m in sk if not m.get("price")]
    bk = collections.defaultdict(list)
    for n in openm:
        bk[base(n)].append(n)
    second, hold = {}, []
    for n in r1["unmatched"]:
        c = [x for x in (bk.get(base(n)) or []) if x not in second]
        if len(c) > 1:                            # 사이즈로 한 번 더 가른다
            want = cm(n)
            ok = [x for x in c if cm(x) == want]
            c = ok if len(ok) == 1 else c
        if len(c) == 1:
            second[c[0]] = pm[n]
            pairs.append((c[0], n, pm[n]))
        elif c:
            hold.append((n, pm[n], c))
    if second:
        r2 = fill(skeleton_path, second, source="delivery_coupangeats",
                  note=note, dry=not apply)
        filled += r2["filled"]

    used = {n for _, n, _ in pairs}
    miss = [(n, v) for n, v in pm.items()
            if n in r1["unmatched"] and n not in used
            and n not in {h[0] for h in hold}]
    return {"filled": filled, "pairs": pairs, "hold": hold,
            "miss": miss, "cattitle": cattitle, "total": r1["total"]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit("사용법: python scripts/delivery_price_match.py <골격.json> <배달가.json> [--apply]")
    apply = "--apply" in sys.argv
    r = match(args[0], args[1], apply=apply)
    print("%s %d개 → 붙음 %d개%s" % ("반영" if apply else "미리보기",
                                   r["total"], r["filled"], "" if apply else " (아직 안 씀)"))
    if r["pairs"]:
        print("\n■ 규격·띄어쓰기만 달라 붙은 것 %d개" % len(r["pairs"]))
        for a, b, v in r["pairs"][:40]:
            print("   %-30s ← %-30s %s원" % (a[:30], b[:30], format(v, ",")))
    if r["hold"]:
        print("\n■ 후보가 여럿이라 보류 %d개 — 값을 보고 사람이 정한다" % len(r["hold"]))
        for n, v, c in r["hold"][:15]:
            print("   ? %-28s %7s원 → %s" % (n[:28], format(v, ","), c[:3]))
    if r["cattitle"]:
        print("\n■ 카테고리 제목이라 뺀 것 %d개: %s" % (len(r["cattitle"]), r["cattitle"][:8]))
    print("\n■ 골격에 없어 못 붙인 것 %d개" % len(r["miss"]))
    for n, v in r["miss"][:30]:
        print("   · %-34s %s원" % (n[:34], format(v, ",")))
    if not apply:
        print("\n실제로 반영하려면 --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
