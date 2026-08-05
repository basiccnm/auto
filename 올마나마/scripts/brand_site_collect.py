# -*- coding: utf-8 -*-
"""브랜드 홈페이지에서 **이름(+가격이 있으면 가격까지)** 을 받아 저장한다. 2026-07-28

    python scripts/brand_site_collect.py            # 미리보기
    python scripts/brand_site_collect.py --apply
    python scripts/brand_site_collect.py --only 멕시카나 --apply

대표 지시(2026-07-28): *"메뉴만 있으면 그냥 메뉴만 넣어서 조사해. 가격있으면 가격까지 다 넣고"*

🔴 버거킹에서 배운 것 — **`innerText` 로 보면 «메뉴가 없다» 고 오판한다.**
   안 눌린 탭이 `display:none` 이라 화면 글자에서 빠질 뿐, DOM 엔 다 들어 있다.
   그래서 여기서는 **렌더된 DOM 전체**를 글자로 펴서 읽는다.

🔴 가격이 «23,000» 과 «원» 으로 **쪼개져** 오는 사이트가 많다(롯데리아·본죽).
   `to_lines()` 끝에서 다시 붙인다 — 안 붙이면 그 사이트가 통째로 0건이 된다.

⛔ 가격이 없으면 **이름만 넣는다.** 가격을 지어내지 않는다.
⛔ 이름만 넣을 때 **기존 가격을 지우지 않는다**(`price` 는 건드리지 않는다).
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GAP = 4

# 브랜드 → 메뉴 페이지들 (대표가 준 주소 + DB 주소)
SITES = {
    "멕시카나치킨": ["https://www.mexicana.co.kr/menu/product.asp?catecode=1000001"],
    "호식이지두마리치킨": ["https://www.9922.co.kr/chicken"],
    "지코바치킨": ["http://www.gcova.co.kr/"],
    "피자마루": ["https://www.pizzamaru.co.kr/menu/10"],
    "59쌀피자": ["https://xn--2e0b622b4gcxwb8x8a.kr/menu/list?ca_id=01"],
    "프랭크버거": ["https://frankburger.co.kr/html/menu_1.html"],
    "청년피자": ["https://www.youngmanpizza.co.kr/sub01/menu.php"],
    "원할머니보쌈": ["https://wonandone.co.kr/bossam/menu.asp"],
    "노랑통닭": ["https://www.norangtongdak.co.kr/"],
    "가장맛있는족발": ["http://www.jogbal.co.kr/"],
    "땅스부대찌개": ["https://tsbudae.com/"],
    "탕화쿵푸마라탕": ["https://www.tanghuokungfu.co.kr/"],
}

RX_PRICE = re.compile(r"^([\d]{1,3}(?:,[\d]{3})+)\s*원?$")
# 메뉴명이 아닌 줄
BAD = re.compile(
    r"(로그인|회원가입|장바구니|검색|바로가기|공지|이벤트|더보기|매장찾기|가맹|창업|문의|"
    r"고객센터|채용|약관|개인정보|사업자|대표이사|주소|전화|팩스|COPYRIGHT|All rights|"
    r"^\d+$|^[A-Za-z]$|^메뉴$|^전체$|^홈$|^HOME$|^MENU$|영양성분|알레르기|원산지)", re.I)


def render(url, budget=15000):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,6000",
             "--virtual-time-budget=%d" % budget, "--dump-dom", url],
            capture_output=True, timeout=120)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def to_lines(dom):
    s = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h[1-6]|a|span|dt|dd|strong|em)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#39;", "'"),
                 ("&quot;", '"'), ("&#8482;", "™")):
        s = s.replace(a, b)
    out = [x.strip() for x in re.sub(r"[ \t　]+", " ", s).split("\n") if x.strip()]
    # 🔴 «23,000» + «원» 이 두 줄로 갈린 사이트를 다시 붙인다
    merged, i = [], 0
    while i < len(out):
        if (i + 1 < len(out) and out[i + 1] == "원"
                and re.match(r"^\d{1,3}(?:,\d{3})+$|^\d{3,6}$", out[i])):
            merged.append(out[i] + "원")
            i += 2
            continue
        merged.append(out[i])
        i += 1
    return merged


def is_name(t):
    t = t.strip()
    if not (2 <= len(t) <= 34):
        return False
    if RX_PRICE.match(t) or BAD.search(t):
        return False
    if not re.search(r"[가-힣A-Za-z]", t):
        return False
    if len(t) > 24 and re.search(r"[,。]", t):        # 설명문
        return False
    return True


def parse(lines, allow_names=False):
    """가격 줄이 있으면 «이름+가격», 없으면 이름만 모은다.

    🔴 **가격이 없을 때 이름만 담는 건 기본으로 하지 않는다** (2026-07-28 사고).
       호식이에서 「알림」·「뒤로」·「Alarm」·「나눔 활동」 같은 화면 글자 68개가
       메뉴로 들어가 전부 지웠다. 화면 글자와 메뉴명은 글자만 봐서 못 가른다.
       이름만 담으려면 `--names` 로 **명시**해야 한다.
    """
    pairs, names, seen = [], [], set()
    for i, t in enumerate(lines):
        m = RX_PRICE.match(t)
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        if not (500 <= price <= 300000):
            continue
        # 가격 위로 올라가며 이름 — 짧고 띄어쓰기 적은 것을 고른다
        cands = [lines[j] for j in range(i - 1, max(-1, i - 6), -1) if is_name(lines[j])]
        if not cands:
            continue
        nm = min(cands, key=lambda x: (x.count(" "), len(x)))
        k = re.sub(r"\s+", "", nm)
        if k not in seen:
            seen.add(k)
            pairs.append((nm, price))
    if pairs or not allow_names:
        return pairs, []
    # 가격이 하나도 없을 때만, 그리고 --names 를 줬을 때만 이름을 담는다
    for t in lines:
        if not is_name(t):
            continue
        k = re.sub(r"\s+", "", t)
        if k not in seen:
            seen.add(k)
            names.append(t.strip())
    return [], names


def main():
    apply_ = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    db = PS.connect()
    cur = db.cursor()
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")

    for bname, urls in SITES.items():
        if only and only not in bname:
            continue
        br = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
        if not br:
            print("🔴 %-16s DB 에 브랜드가 없다" % bname[:16], flush=True)
            continue
        allp, alln, seen = [], [], set()
        for u in urls:
            dom = render(u)
            if not dom:
                print("🔴 %-16s 렌더 실패 %s" % (bname[:16], u[:50]), flush=True)
                continue
            p, n = parse(to_lines(dom), allow_names="--names" in sys.argv)
            for nm, pr in p:
                k = re.sub(r"\s+", "", nm)
                if k not in seen:
                    seen.add(k)
                    allp.append((nm, pr))
            for nm in n:
                k = re.sub(r"\s+", "", nm)
                if k not in seen:
                    seen.add(k)
                    alln.append(nm)
            time.sleep(GAP)

        kind = "가격+이름" if allp else ("이름만" if alln else "0건")
        print("● %-16s %-8s 가격 %3d · 이름 %3d" % (bname[:16], kind, len(allp), len(alln)),
              flush=True)
        for nm, pr in allp[:5]:
            print("     %-30s %s원" % (nm[:30], format(pr, ",")))
        for nm in alln[:5]:
            print("     %s" % nm[:40])
        if not apply_:
            continue

        new = same = 0
        for nm, pr in allp:
            r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL,
                       note="공식 홈페이지", now=now)
            db.commit()
            new += 1 if r == "new" else 0
            same += 1 if r in ("same", "changed") else 0
        for nm in alln:
            # ⚠️ 이름만 — **가격은 건드리지 않는다**
            ex = cur.execute("""SELECT rowid, decided_at FROM brand_menu_official
                                WHERE brand_id=? AND name=?""", (br["id"], nm)).fetchone()
            if ex:
                same += 1
                continue
            cur.execute("""INSERT INTO brand_menu_official
                (brand_id,name,price,price_source,collected_at) VALUES(?,?,NULL,?,?)""",
                        (br["id"], nm, PS.SRC_OFFICIAL, now))
            db.commit()
            new += 1
        print("     저장: 새로 %d · 이미 있던 것 %d" % (new, same), flush=True)


if __name__ == "__main__":
    main()
