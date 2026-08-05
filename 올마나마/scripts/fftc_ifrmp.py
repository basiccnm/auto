# -*- coding: utf-8 -*-
"""정보공개서 공개본 API — 우리 브랜드와 매칭하고 본문을 받는다. 2026-07-26

왜 필요한가 — 사장이 알아야 하는 건 **이 메뉴를 완제품으로 받는가 원물로 받는가**이고,
그 판별의 1차 근거가 정보공개서의 **필수공급품목(가맹점사업자의 부담)** 항목이다.
(다 나오지는 않는다 — 대표 확인. 홈페이지·배민과 함께 쓴다)

명세 (대표가 준 것 + franchise.ftc.go.kr/openApi/guide.do)
    목록  https://franchise.ftc.go.kr/api/search.do?type=list&yr=&serviceKey=
    목차  https://franchise.ftc.go.kr/api/search.do?type=title&jngIfrmpSn=&serviceKey=
    본문  https://franchise.ftc.go.kr/api/search.do?type=content&jngIfrmpSn=&serviceKey=
    뷰어  https://franchise.ftc.go.kr/api/viewer.do?jngIfrmpSn=&serviceKey=

⚠️ serviceKey 는 **URL 인코딩된 상태 그대로** 붙인다(`%2F`·`%2B` 가 들어있다).
   디코딩해서 넣으면 인증이 깨진다.
⚠️ `.env` 의 키 이름은 `OLMANAMA_` 접두어를 쓴다 — wrangler 가 집어가는 이름을 피한다(2026-07-25 사고).

    python scripts/fftc_ifrmp.py --list           # 연도별 목록 받아 캐시
    python scripts/fftc_ifrmp.py --match          # 우리 브랜드와 매칭
    python scripts/fftc_ifrmp.py --title <sn>     # 목차 보기
    python scripts/fftc_ifrmp.py --content <sn>   # 본문 받기
"""
import io
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CACHE = os.path.join(BASE, "data", "fftc_ifrmp")
API = "https://franchise.ftc.go.kr/api/search.do"
SLEEP = 0.7
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def key():
    k = os.environ.get("OLMANAMA_FFTC_API_KEY")
    if not k:
        for line in io.open(os.path.join(BASE, ".env"), encoding="utf-8", errors="ignore"):
            if line.strip().startswith("OLMANAMA_FFTC_API_KEY"):
                k = line.split("=", 1)[1].strip()
                break
    if not k:
        raise SystemExit(".env 에 OLMANAMA_FFTC_API_KEY 가 없다")
    return k


def get(**kw):
    """⚠️ type=content 는 **gzip 으로 온다**(Content-Encoding: gzip, 1.1MB XML).
    그냥 read().decode() 하면 깨진 바이너리로 보여서 '못 쓰는 응답'으로 오판한다(2026-07-26)."""
    q = "&".join("%s=%s" % (a, b) for a, b in kw.items())
    u = "%s?%s&serviceKey=%s" % (API, q, key())
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=60, context=_CTX)
    raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        import gzip as _gz
        raw = _gz.decompress(raw)
    return raw.decode("utf-8", "replace")


def fetch_list(yr):
    """연도별 공개본 목록 전체."""
    fp = os.path.join(CACHE, "list_%s.json" % yr)
    if os.path.exists(fp):
        return json.load(io.open(fp, encoding="utf-8"))
    first = ET.fromstring(get(type="list", yr=yr, pageNo=1, numOfRows=1))
    total = int((first.findtext("totalCount") or "0"))
    out = []
    per = 1000
    for p in range(1, (total // per) + 2):
        root = ET.fromstring(get(type="list", yr=yr, pageNo=p, numOfRows=per))
        for it in root.iter("item"):
            out.append({t: (it.findtext(t) or "") for t in
                        ("jngIfrmpSn", "corpNm", "brandNm", "brno", "jngIfrmpRgsno")})
        print("   yr=%s page %d → %d건" % (yr, p, len(out)), flush=True)
        time.sleep(SLEEP)
    os.makedirs(CACHE, exist_ok=True)
    io.open(fp, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    return out


def norm(s):
    """브랜드명 비교용 — 공백·괄호·주식회사 표기를 떼고 붙인다."""
    s = re.sub(r"\([^)]*\)|주식회사|\(주\)|㈜", "", s or "")
    return re.sub(r"[\s·\-_.]+", "", s).lower()


def main():
    a = sys.argv[1:]
    if "--title" in a:
        print(get(type="title", jngIfrmpSn=a[a.index("--title") + 1]))
        return
    if "--content" in a:
        sn = a[a.index("--content") + 1]
        body = get(type="content", jngIfrmpSn=sn)
        os.makedirs(CACHE, exist_ok=True)
        fp = os.path.join(CACHE, "content_%s.xml" % sn)
        io.open(fp, "w", encoding="utf-8").write(body)
        print("저장: %s (%d자)" % (fp, len(body)))
        return

    # 연도별로 공개본이 흩어져 있다 — 2025 에 3,239건이 몰려 있고 옛 연도에도 남아 있다.
    # 교촌·bhc·BBQ·맥도날드 같은 큰 브랜드가 2025 목록에 없어서 연도를 넓힌다.
    years = ("2025", "2024", "2023", "2022", "2021", "2020", "2019")
    rows = []
    for y in years:
        rows += [dict(r, yr=y) for r in fetch_list(y)]
    print("정보공개서 공개본 %d건 (연도 %s)" % (len(rows), ", ".join(years)))

    if "--match" not in a:
        return
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    brands = [dict(r) for r in c.execute("""
        SELECT b.id, b.name, b.published,
               (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) n
        FROM brands b WHERE (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY n DESC""")]
    idx = {}
    for r in rows:
        idx.setdefault(norm(r["brandNm"]), r)
    # 🔴 포함 매칭은 **양쪽 다 4자 이상**일 때만 한다.
    #    2026-07-26: "청"(비컨홀딩스) 하나가 청담동마녀김밥·청년다방을 둘 다 먹었고
    #    투썸플레이스가 "플레이(pley)"에 붙었다. 짧은 브랜드명은 오매칭 공장이다.
    hit, miss, loose = [], [], []
    for b in brands:
        nb = norm(b["name"])
        r = idx.get(nb)
        if r:
            (hit).append((b, r, "정확"))
            continue
        cand = [v for k2, v in idx.items()
                if len(nb) >= 4 and len(k2) >= 4 and (nb in k2 or k2 in nb)]
        if len(cand) == 1:
            hit.append((b, cand[0], "부분"))
        elif len(cand) > 1:
            loose.append((b, cand))
            miss.append((b, None))
        else:
            miss.append((b, None))
    print()
    print("우리 브랜드 %d개 중 정보공개서 찾음 %d개 · 못 찾음 %d개" % (len(brands), len(hit), len(miss)))
    print()
    print("%-18s %4s %5s %8s %-20s %s" % ("브랜드", "메뉴", "매칭", "일련번호", "법인", "정보공개서 브랜드명"))
    print("-" * 100)
    for b, r, how in hit:
        print("%-18s %3d개 %5s %8s %-20s %s" % (b["name"][:18], b["n"], how, r["jngIfrmpSn"],
                                                r["corpNm"][:20], r["brandNm"]))
    if loose:
        print()
        print("■ 후보가 여럿이라 보류 %d개 (사람이 골라야 함)" % len(loose))
        for b, cand in loose:
            print("   %-16s → %s" % (b["name"][:16],
                                     " / ".join("%s(%s)" % (x["brandNm"], x["jngIfrmpSn"]) for x in cand[:5])))
    print()
    print("■ 못 찾음 %d개" % len(miss))
    print("   %s" % ", ".join(b["name"] for b, _ in miss))
    out = os.path.join(BASE, "data", "research", "fftc_brand_match.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"hit": [{"brand": b["name"], "menus": b["n"], "how": how, "sn": r["jngIfrmpSn"],
                  "corp": r["corpNm"], "fftc_brand": r["brandNm"], "yr": r["yr"]} for b, r, how in hit],
         "loose": [{"brand": b["name"], "cands": [{"nm": x["brandNm"], "sn": x["jngIfrmpSn"]} for x in cd]}
                   for b, cd in loose],
         "miss": [b["name"] for b, _ in miss]}, ensure_ascii=False, indent=1))
    print()
    print("→ %s" % out)


if __name__ == "__main__":
    main()
