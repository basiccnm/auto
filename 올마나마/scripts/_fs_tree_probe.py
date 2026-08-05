# -*- coding: utf-8 -*-
"""식봄 카테고리 트리 탐색 (일회성). 루트 후보 nid 를 트리쿼리로 훑는다."""
import json, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
API = "https://api.foodspring.co.kr/v2/graphql"
TREE = ("query($nid:Int!){goodsCategory(nid:$nid){nid name "
        "children{nid name children{nid name}}}}")


def tree(nid):
    body = json.dumps({"query": TREE, "variables": {"nid": nid}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Device-Type": "pc",
        "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
        "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    return j.get("data", {}).get("goodsCategory"), j.get("errors")


def show(nid):
    c, err = tree(nid)
    if err:
        print("nid %s ERR %s" % (nid, err)); return
    if not c:
        print("nid %s -> null" % nid); return
    print("=== nid %s : %s ===" % (c["nid"], c["name"]))
    for ch in (c.get("children") or []):
        print("  %s %s" % (ch["nid"], ch["name"]))
        for g in (ch.get("children") or []):
            print("      %s %s" % (g["nid"], g["name"]))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        show(int(a))
        time.sleep(1.5)
