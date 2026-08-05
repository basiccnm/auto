# -*- coding: utf-8 -*-
"""**제목·설명에 「쿠팡」·「로켓배송」이 들어갔나** 전수 검사. 2026-07-31 신설

    python scripts/check_trademark.py            # _preview 전체 검사
    python scripts/check_trademark.py --dist     # _dist 도 함께
    python scripts/check_trademark.py --json     # 콘텐츠 JSON(쇼츠 대사 등)까지

🔴 왜 코드로 막나
   쿠팡 파트너스 약관상 **제목·설명·도메인에 상표를 쓸 수 없다.**
   README 에 적어두는 것만으로는 몇 번이고 다시 어긴다 — 프로젝트 원칙이
   «문서로 막지 말고 코드로 막는다» 이다(`CLAUDE.md` 사고 색인 머리말).

✅ **본문에서 사실 서술은 괜찮다.**
   「조사한 상품은 모두 로켓배송입니다」 · 파트너스 고지문은 문제없다.
   막아야 하는 건 **`<title>` · `meta[name=description]` · `og:title` · `og:description`** 이다.

⛔ 그래서 본문 전체를 훑지 않는다. 훑으면 고지문까지 걸려서 «경고 피로» 로 무시하게 된다.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 상표 — 붙여쓰기·띄어쓰기 둘 다
RX_MARK = re.compile(r"쿠\s*팡|로켓\s*배송|로켓\s*프레시|COUPANG|ROCKET\s*DELIVERY", re.I)

# 검사 대상은 **머리말 4곳뿐**이다 (본문은 사실 서술이 허용된다)
FIELDS = (
    ("<title>", re.compile(r"<title>(.*?)</title>", re.S | re.I)),
    ("meta description", re.compile(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.S | re.I)),
    ("og:title", re.compile(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', re.S | re.I)),
    ("og:description", re.compile(
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', re.S | re.I)),
)


def scan_html(paths):
    bad = []
    for p in paths:
        try:
            h = io.open(p, encoding="utf-8").read()
        except Exception:                       # noqa: BLE001
            continue
        for label, rx in FIELDS:
            for m in rx.finditer(h):
                val = re.sub(r"\s+", " ", m.group(1)).strip()
                hit = RX_MARK.search(val)
                if hit:
                    bad.append((os.path.basename(p), label, hit.group(0), val[:90]))
    return bad


def scan_json(paths):
    """쇼츠 대사·설명 같은 콘텐츠 JSON — `title`·`desc`·`description` 키만 본다."""
    import json
    bad = []
    for p in paths:
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:                       # noqa: BLE001
            continue

        def walk(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and k.lower() in (
                            "title", "desc", "description", "subtitle", "caption"):
                        hit = RX_MARK.search(v)
                        if hit:
                            bad.append((os.path.basename(p), "%s.%s" % (path, k),
                                        hit.group(0), v[:90]))
                    else:
                        walk(v, path + "." + k)
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, "%s[%d]" % (path, i))
        walk(d)
    return bad


def main():
    targets = [os.path.join(BASE, "_preview")]
    if "--dist" in sys.argv:
        targets.append(os.path.join(BASE, "_dist"))

    html = []
    for t in targets:
        html += glob.glob(os.path.join(t, "*.html"))
    bad = scan_html(html)
    print("HTML %d장 검사 (제목·설명 4개 필드만)" % len(html))

    if "--json" in sys.argv:
        js = glob.glob(os.path.join(BASE, "data", "**", "*.json"), recursive=True)
        js = [p for p in js if "_ce_raw" not in p]
        jb = scan_json(js)
        print("콘텐츠 JSON %d개 검사" % len(js))
        bad += jb

    if not bad:
        print("\n✅ 제목·설명에 상표 없음")
        return 0
    print("\n🔴 상표가 들어간 곳 %d건 — 파트너스 약관 위반" % len(bad))
    for fn, label, mark, val in bad[:40]:
        print("   %-26s %-16s 「%s」  %s" % (fn[:26], label, mark, val))
    print("\n   → 제목·설명에서 빼라. **본문 사실 서술·고지문은 그대로 둬도 된다.**")
    return 1


if __name__ == "__main__":
    sys.exit(main())
