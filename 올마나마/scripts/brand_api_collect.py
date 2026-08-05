# -*- coding: utf-8 -*-
"""**이미 뚫려 있는 브랜드 API** 로 메뉴판을 한 번에 받는다. 2026-07-28

    python scripts/brand_api_collect.py                  # 미리보기
    python scripts/brand_api_collect.py --apply
    python scripts/brand_api_collect.py --only 본죽 --apply

근거는 `데이터소스와스크립트.md` §브랜드 API 표다. **경로를 추측하지 않는다** —
그 표에 적힌 주소만 쓴다(2026-07-16 방화벽 차단 · 2026-07-28 본도시락 오적재 둘 다 추측이 원인).

🔴 가격은 계속 바뀐다. 화면 긁기는 갱신 때마다 사람이 붙어야 하지만 **API 는 다시 돌리면 끝**이다.
   그래서 뚫린 브랜드는 전부 이 스크립트로 모은다.
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

GAP = 3
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get(url, referer, timeout=30):
    hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120 Safari/537.36",
           "Accept": "application/json, text/plain, */*",
           "Accept-Language": "ko-KR,ko;q=0.9",
           "Referer": referer,
           "Origin": referer.rstrip("/")}
    r = urllib.request.urlopen(urllib.request.Request(url, headers=hdr),
                               timeout=timeout, context=ctx)
    return json.loads(r.read().decode("utf-8", "replace"))


def walk_pairs(obj, name_keys, price_keys):
    """중첩 JSON 어디에 있든 (이름, 가격) 쌍을 찾아낸다."""
    out = []

    def go(o):
        if isinstance(o, list):
            for x in o:
                go(x)
        elif isinstance(o, dict):
            nm = next((o[k] for k in name_keys if o.get(k)), None)
            pr = next((o[k] for k in price_keys if o.get(k)), None)
            if nm and isinstance(nm, str) and isinstance(pr, (int, float)) and pr > 0:
                out.append((nm.strip(), int(pr)))
            for v in o.values():
                go(v)
    go(obj)
    seen, uniq = set(), []
    for nm, pr in out:
        k = re.sub(r"\s+", "", nm)
        if k in seen:
            continue
        seen.add(k)
        uniq.append((nm, pr))
    return uniq


# ── 브랜드별 수집기 ────────────────────────────────────────────────
def bonif(code):
    """본아이에프. ⚠️ 본도시락은 **BF104** (BF102 는 본죽과 같은 내용을 준다)."""
    j = get("https://api.bonif.co.kr/brand/v1/menu?brdCd=%s&cmdtCateIdx=&orderBy=" % code,
            "https://www.bonif.co.kr/")
    return walk_pairs(j, ("cmdtNm", "menuNm", "name"), ("price", "cmdtPrice", "salePrice"))


def pizzahut(store="0996"):
    """피자헛. 🔴 `price`/`hhPrice` 가 **홀 매장가**(우리 기준).
       `memberDlv`(배달)·`memberPack`(포장)은 쓰지 않는다."""
    got = []
    for cat in ("best", "premium"):
        try:
            j = get("https://www.pizzahut.co.kr/api/menu/%s/list/%s/VISIT" % (store, cat),
                    "https://www.pizzahut.co.kr/")
            got += walk_pairs(j, ("name", "menuNm", "prodNm"), ("price", "hhPrice"))
        except Exception as e:
            print("    ! %s %s" % (cat, str(e)[:50]))
        time.sleep(GAP)
    return got


def bhc():
    j = get("https://www.bhc.co.kr/api/v1/web/categories/list", "https://www.bhc.co.kr/")
    cats = [c.get("cateIdx") for c in walk_dicts(j) if c.get("cateIdx")]
    got = []
    for ci in dict.fromkeys(cats):
        try:
            p = get("https://www.bhc.co.kr/api/v1/web/categories/%s/products" % ci,
                    "https://www.bhc.co.kr/")
            got += walk_pairs(p, ("productNm", "name", "prodNm"), ("price", "salePrice"))
        except Exception:
            pass
        time.sleep(GAP)
    return got


def walk_dicts(o):
    if isinstance(o, list):
        for x in o:
            yield from walk_dicts(x)
    elif isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk_dicts(v)


SOURCES = [
    ("본죽", lambda: bonif("BF101")),
    ("본도시락", lambda: bonif("BF104")),
    ("피자헛", pizzahut),
    ("bhc치킨", bhc),
]


def main():
    apply_ = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    db = PS.connect()
    cur = db.cursor()
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    for bname, fn in SOURCES:
        if only and only not in bname:
            continue
        print("■ %s" % bname, flush=True)
        try:
            got = fn()
        except Exception as e:
            print("  🔴 실패: %s" % str(e)[:90], flush=True)
            continue
        if not got:
            print("  🔴 0개 — **API 응답 모양이 바뀌었다.** 조용히 넘기지 말 것", flush=True)
            continue
        print("  메뉴 %d개 · 예: %s" % (len(got), " / ".join(
            "%s %s원" % (n, format(p, ",")) for n, p in got[:3])), flush=True)
        if not apply_:
            continue
        br = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
        if not br:
            print("  🔴 DB 에 «%s» 없음" % bname, flush=True)
            continue
        st, changed = {"new": 0, "changed": 0, "same": 0, "skip": 0}, []
        for nm, pr in got:
            before = cur.execute("""SELECT price FROM brand_menu_official
                                    WHERE brand_id=? AND name=?""", (br["id"], nm)).fetchone()
            r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL,
                       note="공식 API", now=now)
            db.commit()                    # 한 건씩 즉시 저장
            st[r] = st.get(r, 0) + 1
            if r == "changed":
                changed.append((nm, before["price"], pr))
        print("  저장: 새로 %d · **바뀜 %d** · 그대로 %d · 사람확정 건너뜀 %d"
              % (st["new"], st["changed"], st["same"], st["skip"]), flush=True)
        for nm, a, b in changed[:15]:      # 값이 바뀐 것만 보고한다
            print("    💰 %-26s %s → %s" % (nm[:26], format(a or 0, ","), format(b, ",")),
                  flush=True)
        time.sleep(GAP)


if __name__ == "__main__":
    main()
