# -*- coding: utf-8 -*-
"""피쉬세일(fishsale.co.kr) '식자재 마트 > 대용량' 수집 — 수산물 **도매** 값.

왜 여기인가: 우리 수산 재료(멸치·다시마·미역·액젓·젓갈·명란)가 전부 네이버 소매값이었다.
여기는 10~20kg 업소 규격만 모아둔 코너라 그대로 도매 축에 쓸 수 있고, 국내산 표기도 있다.

구조 (2026-07-24 확인):
  · 대용량 코너 한 페이지에 **90여 종이 전부** 들어 있다 — 카테고리별로 돌 필요가 없다.
    URL: /event/main.do?eventId=27800000443105
  · 상품명이 `[대용량]브랜드 품목10kg` 꼴이라 **이름 끝에서 용량을 딴다.**
  · `1.5kgx4` 처럼 곱셈 표기가 있으므로 그걸 먼저 처리해야 총량이 맞는다.

⚠️ 이 페이지는 **JS로 그려진다.** curl로 받으면 가격 자리가 비어 있다.
   (같은 이유로 진보람몰도 curl에선 전부 'SOLD OUT'으로 보인다)
   그래서 이 스크립트는 **브라우저에서 뽑아둔 JSON을 정리하는 역할**만 한다.
   수집 자체는 브라우저로 하고, 결과를 data/research/fishsale_raw.json 에 넣어두면
   이 스크립트가 용량을 파싱해 원/kg를 붙인다.
"""
import io, os, re, json, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "research", "fishsale_raw.json")
OUT = os.path.join(BASE, "data", "research", "fishsale_bulk.json")

MUL = re.compile(r"([\d.]+)\s*kg\s*[x×]\s*(\d+)", re.I)      # 1.5kgx4
MUL2 = re.compile(r"\(\s*([\d.]+)\s*g\s*[x×]\s*(\d+)", re.I)  # (350gx20봉)
WT = re.compile(r"([\d.]+)\s*(kg|L)\b", re.I)


def size_kg(name):
    """상품명에서 총 중량(kg)을 뽑는다. 곱셈 표기를 먼저 본다."""
    m = MUL.search(name)
    if m:
        return float(m.group(1)) * int(m.group(2))
    m = MUL2.search(name)
    if m:
        return float(m.group(1)) / 1000 * int(m.group(2))
    w = WT.findall(name)
    return float(w[-1][0]) if w else None


def main():
    if not os.path.exists(RAW):
        print("[i] %s 가 없습니다." % os.path.relpath(RAW))
        print("    브라우저로 아래 주소를 열고, 상품 목록을 JSON으로 저장한 뒤 다시 실행하세요:")
        print("    https://www.fishsale.co.kr/event/main.do?eventId=27800000443105")
        return 1
    items = json.load(io.open(RAW, encoding="utf-8"))
    out = []
    for it in items:
        nm = it["name"].strip()
        kg = size_kg(nm)
        out.append({"name": nm, "price": it["price"], "kg": kg,
                    "won_per_kg": round(it["price"] / kg) if kg else None,
                    "source": "fishsale-대용량", "tier": "도매"})
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    ok = [x for x in out if x["won_per_kg"]]
    print("%d종 (용량 파싱 %d종) → %s\n" % (len(out), len(ok), os.path.relpath(OUT)))
    for x in sorted(ok, key=lambda v: v["won_per_kg"])[:15]:
        print("  %8s원/kg  %s" % ("{:,}".format(x["won_per_kg"]), x["name"][:48]))
    return 0


sys.exit(main())
