# -*- coding: utf-8 -*-
"""식봄 카테고리 nid → 이름 지도 만들기. (2026-07-27)

왜 필요한가 — `meat_price_table.py` 의 nid 지도가 사람이 눈으로 붙인 것이라
**틀린 칸이 있다.** 실제로 소 «불고기용: 수입 [632]» 의 최저가가 `맛술 혼미린 1.8L` 였다
(육류 카테고리가 아니었다). 카테고리 이름을 받아두면 이런 오배치를 바로 볼 수 있다.

쓰는 API 는 이미 뚫려 있는 것 그대로 — 필드만 `name` 하나로 줄였다:
    POST https://api.foodspring.co.kr/v2/graphql
    query($nid:Int!){ goodsCategory(nid:$nid){ name } }

    python scripts/foodspring_cat_names.py 585 735      # 범위
    python scripts/foodspring_cat_names.py --show       # 저장된 것 보기
"""
import io
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "research", "foodspring", "_카테고리이름.json")
API = "https://api.foodspring.co.kr/v2/graphql"
GAP = 1.2
QUERY = "query($nid:Int!){goodsCategory(nid:$nid){name}}"

HDR = {"Content-Type": "application/json", "X-Device-Type": "pc",
       "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
       "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"}


def load():
    if os.path.exists(OUT):
        return json.load(io.open(OUT, encoding="utf-8"))
    return {}


def save(m):
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(m, ensure_ascii=False, indent=1))


def name_of(nid):
    body = json.dumps({"query": QUERY, "variables": {"nid": nid}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers=HDR)
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    cat = (j.get("data") or {}).get("goodsCategory")
    return (cat or {}).get("name")


def main():
    m = load()
    if "--show" in sys.argv:
        for k in sorted(m, key=int):
            print("%4s  %s" % (k, m[k]))
        return
    args = [a for a in sys.argv[1:] if a.isdigit()]
    lo, hi = (int(args[0]), int(args[1])) if len(args) >= 2 else (585, 735)
    got = 0
    for nid in range(lo, hi + 1):
        if str(nid) in m:                      # 이미 받은 것은 건너뛴다 — 끊겨도 이어감
            continue
        try:
            nm = name_of(nid)
        except Exception as e:
            print("  ! %d %s" % (nid, str(e)[:40]))
            time.sleep(GAP)
            continue
        m[str(nid)] = nm
        got += 1
        print("%4d  %s" % (nid, nm))
        save(m)                                # 한 건씩 저장 (차단돼도 남는다)
        time.sleep(GAP)
    print("\n새로 받은 것 %d개 · 전체 %d개 → %s" % (got, len(m), os.path.basename(OUT)))


if __name__ == "__main__":
    main()
