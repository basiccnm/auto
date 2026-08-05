# -*- coding: utf-8 -*-
"""식봄 **지역(area) 지도**와 지역별 배송업체. 2026-07-28

    python scripts/foodspring_area.py --tree            # 시도 → 시군구 (한 번만 받아 저장)
    python scripts/foodspring_area.py --area area_1651  # 그 지역 하위
    python scripts/foodspring_area.py --show

왜 필요한가 (대표 질문 2026-07-28: *"전국단위·지역단위·택배단위 배송업체 다 확인할 수 있나?"*)
------------------------------------------------------------------
지금 우리 도매가는 **`area_324` 한 지역**의 최저가다(`foodspring_collect.py`).
그런데 식봄은 중계몰이라 **그 지역에 배송하는 업체만** 상품이 뜬다. 그래서:

  · 대구 사장님이 우리 값을 보고 «이 값에 살 수 있다» 고 믿었는데
    그 업체가 대구 배송을 안 하면 **재현이 안 된다** (`cost-claim-is-reproducible`)
  · 「그 외(택배배송)」 = `id 0` 은 **택배비가 따로 붙는다**
    (`wholesale-must-be-bulk-shipping-included`: 1kg 단품+택배비면 실질 2배)

쓰는 API — 둘 다 **사이트가 실제로 보내는 것 그대로** 잡았다(추측 아님):

  ① 지역 트리 (REST, 파라미터 없으면 시도 17개)
     POST https://www.foodspring.co.kr/API/delivery_area   body: area_id=<번호>
  ② 지역 상세·자식 (GraphQL, 사이트의 LocationSelectPopupPCQuery)
     POST https://api.foodspring.co.kr/v2/graphql
     query($areaId:ID!){ node(id:$areaId){ ... on Area{ id name parent{id name} children{id name} } } }

  ⚠️ REST 는 **숫자 id**(1651), GraphQL 은 **`area_1651`** 로 쓴다. 같은 번호다.
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "research", "foodspring", "_지역.json")
REST = "https://www.foodspring.co.kr/API/delivery_area"
GQL = "https://api.foodspring.co.kr/v2/graphql"
GAP = 1.0

HDR_REST = {"Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.foodspring.co.kr",
            "Referer": "https://www.foodspring.co.kr/main/location",
            "User-Agent": "Mozilla/5.0"}
HDR_GQL = {"Content-Type": "application/json", "X-Device-Type": "pc",
           "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
           "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"}

Q_AREA = ("query($areaId:ID!){node(id:$areaId){__typename ... on Area{"
          "id name parent{id name} children{id name}}}}")

# 🔴 이 쿼리는 **사이트가 실제로 보내는 것**을 그대로 옮긴 것이다(locationQuery /
#    SellerByLocationListPCFragment). 필드명을 추측하지 않았다 — 인트로스펙션이 막혀 있어서
#    `/main/location` 화면에서 지역을 고를 때 나가는 요청을 잡았다(2026-07-28).
#    `typeList` 가 **배송 유형**이다: DIRECT(직배송) · AGGREGATED(합배송)
#    ⚠️ enum 타입 이름(`VendorType`)은 **모른다** — 인트로스펙션이 막혀 있다.
#       그래서 변수로 빼지 않고 사이트가 보낸 그대로 **인라인**으로 넣는다.
Q_SELLER = ("query($areaId:ID!,$first:Int!){"
            "node(id:$areaId){... on Area{id name "
            "sellerList(first:$first,input:{typeList:[%s],order:GOODS_COUNT,"
            "mainDisplay:false}){edges{node{id nid name introduction "
            "sellerCategoryList}}}}}}")


def rest_children(area_id=None):
    """area_id 없으면 시도 17개, 있으면 그 아래 한 단계."""
    body = ("area_id=%s" % area_id).encode() if area_id else b""
    req = urllib.request.Request(REST, data=body, method="POST", headers=HDR_REST)
    with urllib.request.urlopen(req, timeout=30) as r:
        return (json.loads(r.read().decode()) or {}).get("data") or []


def gql_area(area_gid):
    body = json.dumps({"query": Q_AREA, "variables": {"areaId": area_gid}}).encode()
    req = urllib.request.Request(GQL, data=body, method="POST", headers=HDR_GQL)
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    if j.get("errors"):
        return {"error": j["errors"][0].get("message", "")[:120]}
    return (j.get("data") or {}).get("node") or {}


def sellers(area_gid, first=20, types=("DIRECT", "AGGREGATED")):
    """그 지역에 **배송하는 업체** 목록. typeList 로 배송 유형을 가른다."""
    q = Q_SELLER % ", ".join(types)
    body = json.dumps({"query": q, "variables": {
        "areaId": area_gid, "first": first}}).encode()
    req = urllib.request.Request(GQL, data=body, method="POST", headers=HDR_GQL)
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.loads(r.read().decode())
    if j.get("errors"):
        return {"error": j["errors"][0].get("message", "")[:160]}
    n = (j.get("data") or {}).get("node") or {}
    return {"name": n.get("name"),
            "list": [e["node"] for e in ((n.get("sellerList") or {}).get("edges") or [])]}


def build_tree():
    """시도 → 시군구 두 단계만 받는다. 동까지는 5,000개가 넘어 필요할 때만 받는다."""
    sido = rest_children()
    tree = []
    for s in sido:
        kids = []
        if int(s["child_count"] or 0) > 0:
            try:
                kids = [{"id": k["id"], "name": k["name"], "child_count": k["child_count"]}
                        for k in rest_children(s["id"])]
            except Exception as e:
                print("  ! %s %s" % (s["name"], str(e)[:50]))
            time.sleep(GAP)
        tree.append({"id": s["id"], "name": s["name"],
                     "child_count": s["child_count"], "children": kids})
        print("%-14s id=%-5s 시군구 %d개" % (s["name"], s["id"], len(kids)), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(tree, ensure_ascii=False, indent=1))
    print("\n시도 %d개 → %s" % (len(tree), os.path.basename(OUT)))
    return tree


def main():
    if "--sellers" in sys.argv:
        gid = sys.argv[sys.argv.index("--sellers") + 1]
        gid = gid if gid.startswith("area_") else "area_" + gid
        tl = ["DIRECT", "AGGREGATED"]
        if "--type" in sys.argv:
            tl = [sys.argv[sys.argv.index("--type") + 1].upper()]
        r = sellers(gid, first=40, types=tl)
        if r.get("error"):
            print("에러: %s" % r["error"])
            return
        print("● %s (%s) · %s · 업체 %d곳\n" % (r["name"], gid, "+".join(tl), len(r["list"])))
        for v in r["list"]:
            cats = ",".join(v.get("sellerCategoryList") or [])[:40]
            print("  %-30s nid=%-6s [%s]" % ((v.get("name") or "")[:30], v.get("nid"), cats))
            intro = (v.get("introduction") or "").replace("\n", " ").strip()
            if intro:
                print("      %s" % intro[:96])
        return
    if "--area" in sys.argv:
        gid = sys.argv[sys.argv.index("--area") + 1]
        n = gql_area(gid if gid.startswith("area_") else "area_" + gid)
        if n.get("error"):
            print("에러: %s" % n["error"])
            return
        p = n.get("parent") or {}
        print("● %s (%s)   상위: %s" % (n.get("name"), n.get("id"), p.get("name") or "-"))
        for k in (n.get("children") or [])[:60]:
            print("   %-14s %s" % (k["name"], k["id"]))
        print("   … 자식 %d개" % len(n.get("children") or []))
        return
    if "--show" in sys.argv:
        if not os.path.exists(OUT):
            print("아직 없음 — --tree 로 먼저 받는다")
            return
        for s in json.load(io.open(OUT, encoding="utf-8")):
            print("%-14s id=%-5s (%s)" % (
                s["name"], s["id"], ", ".join(k["name"] for k in s["children"][:8])))
        return
    build_tree()


if __name__ == "__main__":
    main()
