# -*- coding: utf-8 -*-
"""서치콘솔에서 «많이 찾는 검색어» 를 받아 홈에 쓸 JSON 으로 저장한다. (2026-07-31 신설)

    python scripts/gsc_keywords.py            최근 7일 · data/gsc_keywords.json 갱신
    python scripts/gsc_keywords.py --days 14  기간 바꿔서
    python scripts/gsc_keywords.py --show     저장된 것만 보기

🔴 **실시간이 아니다. 2~3일 지연이다.**
   구글 서치콘솔은 원래 최근 2~3일 데이터를 안 준다. 그래서 조회 기간의 끝을
   «오늘 - 2일» 로 잡는다. 화면에도 반드시 «○월 ○일 기준» 을 같이 보여줘야 한다 —
   실시간처럼 보이면 거짓말이 된다(2026-07-31 대표 지시: "2일에 한번 갱신이라고, 실시간 아니라고").

🔴 갱신 주기는 **2일에 한 번**이면 충분하다. 더 자주 불러도 값이 안 바뀐다.

🔴 왜 네이버가 아니라 서치콘솔인가:
     · 네이버 검색광고 API — **월간** 검색량만 준다. 몇 시간마다 돌려도 값이 그대로다
     · 네이버 데이터랩 급상승 — API 가 없어졌다
     · 서치콘솔 — 우리 사이트가 **실제로 노출된** 검색어라 «지금 뜨는 것» 에 제일 가깝다
"""
import argparse
import io
import json
import os
import sys
from datetime import date, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(BASE, "data", "gsc_keywords.json")
SITE = "sc-domain:olmanama.com"
LAG = 2          # 🔴 서치콘솔 지연. 이 값보다 최근 데이터는 안 온다
TOP = 12         # 홈에 보여줄 개수

# 검색어가 아니라 우리 사이트 이름인 것 — 순위에 넣으면 의미가 없다
SELF = ("올마나마", "얼마남아", "olmanama")


def fetch(days):
    from googleapiclient.discovery import build
    from auth_google import creds
    sc = build("searchconsole", "v1", credentials=creds())
    end = date.today() - timedelta(days=LAG)
    start = end - timedelta(days=days - 1)
    rows = sc.searchanalytics().query(siteUrl=SITE, body={
        "startDate": str(start), "endDate": str(end),
        "dimensions": ["query"], "rowLimit": 200,
    }).execute().get("rows", [])

    # 🔴 **띄어쓰기만 다른 건 같은 검색어로 합친다**(2026-07-31 지시).
    #    「블랙알리오 치킨 16」·「블랙 알리오 치킨 7」 이 1·2위를 나란히 먹고 있었다.
    #    화면엔 **제일 많이 쓰인 표기**를 보여주고, 노출·클릭은 더한다.
    merged = {}
    for r in rows:
        q = r["keys"][0]
        if any(s in q.replace(" ", "").lower() for s in SELF):
            continue
        key = q.replace(" ", "")
        d = merged.setdefault(key, {"q": q, "imp": 0, "clk": 0, "pos": [], "top": 0})
        imp = int(r["impressions"])
        d["imp"] += imp
        d["clk"] += int(r["clicks"])
        d["pos"].append(r["position"])
        if imp > d["top"]:          # 노출이 제일 많은 표기를 대표로 쓴다
            d["top"], d["q"] = imp, q

    out = [{"q": d["q"], "imp": d["imp"], "clk": d["clk"],
            "pos": round(sum(d["pos"]) / len(d["pos"]), 1)} for d in merged.values()]
    out.sort(key=lambda x: (-x["imp"], x["pos"]))
    return {
        "updated": date.today().isoformat(),
        "period": {"start": str(start), "end": str(end), "days": days},
        # 🔴 화면에 그대로 박는 문구. 실시간이 아니라는 걸 여기서 못 박는다
        "label": "%s ~ %s 구글 검색 기준" % (start.strftime("%m.%d"), end.strftime("%m.%d")),
        "note": "구글 서치콘솔 집계라 2~3일 지연됩니다. 실시간 순위가 아닙니다.",
        "total": len(out),
        "rows": out[:TOP],
        "all": out,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--show", action="store_true", help="저장된 것만 출력")
    a = ap.parse_args()

    if a.show:
        if not os.path.exists(OUT):
            print("아직 없다. 인자 없이 한 번 돌릴 것")
            return 1
        d = json.loads(io.open(OUT, encoding="utf-8").read())
    else:
        d = fetch(a.days)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1))

    print("■ %s (검색어 %d개)" % (d["label"], d["total"]))
    print("  %s" % d["note"])
    for i, x in enumerate(d["rows"], 1):
        print("  %2d %-24s 노출%4d 클릭%3d 순위%5.1f" % (i, x["q"][:24], x["imp"], x["clk"], x["pos"]))
    if not a.show:
        print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
