# -*- coding: utf-8 -*-
"""미트박스 수집분을 우리 재료에 붙이는 **미리보기**. DB는 건드리지 않는다.

집계 키를 다시 잡았다.
  전:  (원산지)(부위)(등급·브랜드)      ← 소·돼지가 같은 '미국' 칸에 섞였다
  후:  (축종·원산지)(부위)(등급·브랜드)   ← 축종을 넣어야 갈린다

등급 파싱도 고쳤다. 상품명 마지막 ` - ` 뒤 조각을 등급으로 쓰되,
그 조각에 `|`가 들어 있으면 브랜드/원산지가 딸려온 것이라 등급 없음으로 본다.
  `[국산] 양지 | 태랑 - 2등급`            → 2등급
  `삼겹양지 - 미국 | 오마하(클래식헤어포드)`   → 등급 없음 (전에는 이게 등급으로 들어갔다)

가격 3단:
  도매   = 원물(박스)
  도소매 = 낱개 · 육마트(1kg)
  소매   = 쿠팡 (여기서는 다루지 않는다)
"""
import json, io, os, sys, collections

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "research", "meatbox", "_전량.json")
OUT = os.path.join(BASE, "data", "research", "meatbox", "_매핑미리보기.md")

# 값을 못 믿어서 기준값으로 안 쓰는 부위
DROP_PARTS = {"잡육", "지방", "지방(A)", "지방돈피/돼지껍데기", "돈피/돼지껍데기",
              # 반골 계열 제외 — 꼬리를 뺀 등뼈라 소꼬리도 아니고 사골·잡뼈와도 다르다.
              # 최저가(1,000원)라 그냥 두면 뼈류 최저가를 계속 가로챈다.
              "반골(꼬리제외)", "알꼬리(반골제외)", "꼬리반골"}

# 재료 → (후보 부위들, 형태). 형태: W=원물(도매) / C=세절&분쇄 / R=낱개·육마트(도소매)
MAP = [
    ("우삼겹",            ["삼겹양지", "차돌양지"],                      "C"),
    ("소고기 양지",        ["삼겹양지", "차돌양지", "양지"],              "W"),
    ("차돌박이",          ["차돌박이"],                                "W"),
    ("소고기 다짐육",      ["분쇄육"],                                  "W"),
    ("소불고기용 쇠고기",   ["앞다리/전각", "알전각/볼라전각", "설도", "우둔"], "W"),
    ("소고기 큐브스테이크",  ["알목심"],                                  "W"),
    ("소고기 등심",        ["등심"],                                    "W"),
    ("사골 [신설]",        ["사골"],                                    "W"),
    ("잡뼈 [신설]",        ["잡뼈", "갈비잡뼈"],                          "W"),
    ("우족 [신설]",        ["우족"],                                    "W"),
    ("소꼬리 [신설]",      ["꼬리"],                                    "W"),
]
BEEF_KINDS = {"한우암소", "한우거세", "한우수소", "육우암소", "육우거세", "수입소"}
FORM = {"W": {"원물"}, "C": {"세절&분쇄"}, "R": {"낱개"}}


def grade(name):
    parts = (name or "").split(" - ")
    if len(parts) < 2:
        return None
    last = parts[-1].strip()
    return None if ("|" in last or not last) else last


def main():
    rows = json.load(io.open(SRC, encoding="utf-8"))
    for r in rows:
        r["등급"] = grade(r.get("상품명"))
        r["축종원산지"] = "%s·%s" % (r.get("축종") or "?", r.get("원산지") or "?")

    # 대량조건 상품도 도매 후보에 넣는다 — 도매는 원래 대량으로 받는 자리다(2026-07-25 지시).
    # 최소수량 조건은 근거에 남긴다. 가격이 아예 안 보이는 대량상품은 원per_kg이 없어 자동 제외된다.
    ok = [r for r in rows if r.get("원per_kg") and r.get("부위") not in DROP_PARTS]
    nb = sum(1 for r in ok if r.get("대량상품"))
    print("전체 %d건 → 쓸 수 있는 것 %d건 (그중 대량조건 %d건 포함 · 잡육/지방·단가불명 제외)\n"
          % (len(rows), len(ok), nb))

    f = io.open(OUT, "w", encoding="utf-8")
    f.write("# 미트박스 → 재료 매핑 미리보기 (2026-07-25)\n\n")
    f.write("DB 미반영. 각 재료마다 **(축종·원산지)(부위)(등급·브랜드)** 그룹별 최저가다.\n")
    f.write("`도매`=원물 박스 / `도소매`=낱개·육마트(1kg). 소매(쿠팡)는 따로 붙인다.\n\n")

    for label, parts, form in MAP:
        cand = [r for r in ok if r.get("부위") in parts
                and r.get("가공방법") in FORM[form]
                and r.get("축종") in BEEF_KINDS]
        f.write("\n## %s  ←  %s (%s)\n\n" % (
            label, " / ".join(parts), {"W": "원물", "C": "세절&분쇄", "R": "낱개"}[form]))
        if not cand:
            f.write("**후보 없음** — 미트박스에서 이 조건으로 잡히는 상품이 없다.\n")
            print("%-22s 후보 없음" % label)
            continue

        grp = collections.defaultdict(list)
        for r in cand:
            grp[(r["축종원산지"], r["부위"], r["등급"])].append(r)

        f.write("| 키 | 원/kg | n | 중앙 | 최고 | 최저가 상품 |\n")
        f.write("|---|---:|---:|---:|---:|---|\n")
        out = []
        for k, rs in grp.items():
            rs.sort(key=lambda r: r["원per_kg"])
            ps = [r["원per_kg"] for r in rs]
            out.append((rs[0]["원per_kg"], k, len(rs), ps[len(ps) // 2], ps[-1], rs[0]))
        out.sort(key=lambda t: t[0])
        for p, k, n, mid, hi, best in out[:12]:
            f.write("| (%s)(%s)(%s·%s)%s | %s | %d | %s | %s | %s |\n" % (
                k[0], k[1], k[2] or "-", best.get("브랜드") or "-",
                " 〈대량〉" if best.get("대량상품") else "",
                f"{p:,}", n, f"{mid:,}", f"{hi:,}",
                ((best.get("상품명") or "")[:40] +
                 (" — " + best["대량조건"] if best.get("대량조건") else ""))))
        lo = out[0]
        print("%-22s 최저 %8s원/kg  %s  (그룹 %d개)"
              % (label, f"{lo[0]:,}", "(%s)(%s)(%s)" % (lo[1][0], lo[1][1], lo[1][2] or "-"),
                 len(out)))
    f.close()
    print("\n→ %s" % OUT)


main()
