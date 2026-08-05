# -*- coding: utf-8 -*-
"""본아이에프(본죽·본도시락·본설렁탕 …) 메뉴판 — **웹 화면에서** 이름·가격. 2026-07-28

    python scripts/brand_bonif_web.py            # 미리보기
    python scripts/brand_bonif_web.py --apply

🔴 API 는 안 열린다 — `api.bonif.co.kr/brand/v1/menu?brdCd=` 가 JSON 이 아닌 걸 돌려준다.
   그런데 **화면(`www.bonif.co.kr/brand/menu?brdCd=`)에는 가격이 다 있다**(본죽 64개 실측).
   가격이 `<span>13,500</span><span>원</span>` 처럼 쪼개져 있어 기존 파서가 못 붙였을 뿐이다.

⚠️ 본죽·본도시락이 **같은 사이트**라 예전에 두 브랜드 파일이 섞였다(둘 다 268개였다).
   그래서 `brdCd` 로 브랜드를 갈라서 받는다.
"""
import io
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GAP = 5

# 사이트 brdCd → 우리 DB 브랜드명
# 🔴 **BF102 는 본도시락이 아니다** (2026-07-28 사고).
#    `데이터소스와스크립트.md` 에 «본도시락 = BF104» 라고 **이미 적혀 있었는데** 안 읽고
#    BF102 로 추측해서 본죽 메뉴 87개를 본도시락에 넣었다. BF102 는 본죽과 같은 내용을 준다.
#    ⛔ 코드를 추측하지 마라. 문서에 있다.
BRANDS = {
    "BF101": "본죽",
    "BF104": "본도시락",
}

RX_PRICE = re.compile(r"^([\d]{1,2},[\d]{3})$")
_first_seen = {}          # brdCd → 받은 메뉴 이름 집합 (브랜드가 섞였는지 검사용)


def render(url, budget=15000):
    r = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
         "--disable-extensions", "--hide-scrollbars", "--window-size=1280,6000",
         "--virtual-time-budget=%d" % budget, "--dump-dom", url],
        capture_output=True, timeout=120)
    return r.stdout.decode("utf-8", "replace")


def to_lines(dom):
    s = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h[1-6]|a|span|dt|dd|strong|em)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return [l.strip() for l in re.sub(r"[ \t　]+", " ", s).split("\n") if l.strip()]


def pairs(lines):
    """«이름» 다음다음 줄쯤에 «13,500» 이 온다. 가격 줄을 기준으로 위를 본다."""
    out, seen = [], set()
    for i, t in enumerate(lines):
        m = RX_PRICE.match(t)
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        if not (1000 <= price <= 200000):
            continue
        for j in range(i - 1, max(-1, i - 5), -1):
            nm = lines[j].strip()
            if (2 <= len(nm) <= 30 and not RX_PRICE.match(nm)
                    and not re.match(r"^[\d,원\s]+$", nm)
                    and re.search(r"[가-힣A-Za-z]", nm)
                    and nm not in ("원", "메뉴 소개", "주문하기", "매장 찾기")):
                k = re.sub(r"\s+", "", nm)
                if k not in seen:
                    seen.add(k)
                    out.append((nm, price))
                break
    return out


def one(code, bname, apply_):
    url = "https://www.bonif.co.kr/brand/menu?brdCd=%s" % code
    print("■ %-10s %s" % (bname, url), flush=True)
    dom = render(url)
    if not dom:
        print("  🔴 렌더 실패")
        return 0
    got = pairs(to_lines(dom))
    if not got:
        print("  🔴 이름+가격 0개 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return 0

    # 🔴 **`brdCd` 가 헤드리스에서 안 먹는다** (2026-07-28 실제 사고).
    #    `?brdCd=BF102`(본도시락)를 열어도 **기본 브랜드(본죽) 화면**이 그려져서
    #    본도시락에 본죽 메뉴 87개가 들어갔다(둘이 78개 겹쳤다).
    #    → 브랜드마다 **그 브랜드에만 있는 메뉴**가 실제로 나오는지 확인하고,
    #      아니면 저장하지 않는다. «받았다» 와 «맞는 걸 받았다» 는 다르다.
    names = {re.sub(r"\s+", "", n) for n, _ in got}
    if code != "BF101":
        base = _first_seen.get("BF101")
        if base and len(names & base) > len(names) * 0.5:
            print("  🔴 받은 메뉴가 **본죽과 %d/%d 겹친다** — brdCd 가 안 먹은 것이다. 저장 안 함"
                  % (len(names & base), len(names)))
            return 0
    _first_seen[code] = names
    print("  메뉴 %d개 · 예: %s" % (len(got), " / ".join(
        "%s %s원" % (n, format(p, ",")) for n, p in got[:3])))
    if not apply_:
        return len(got)

    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
    if not br:
        print("  🔴 DB 에 «%s» 브랜드가 없다" % bname)
        return 0
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    st, changed = {"new": 0, "changed": 0, "same": 0, "skip": 0}, []
    for nm, pr in got:
        before = cur.execute("SELECT price FROM brand_menu_official WHERE brand_id=? AND name=?",
                             (br["id"], nm)).fetchone()
        r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL, now=now)
        db.commit()                       # 한 건씩 즉시 저장
        st[r] = st.get(r, 0) + 1
        if r == "changed":
            changed.append((nm, before["price"], pr))
    print("  저장: 새로 %d · 바뀜 %d · 그대로 %d · 사람확정 건너뜀 %d"
          % (st["new"], st["changed"], st["same"], st["skip"]))
    for nm, a, b in changed[:12]:
        print("    💰 %-24s %s → %s" % (nm[:24], format(a or 0, ","), format(b, ",")))
    db.close()
    return len(got)


def main():
    apply_ = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    tot = 0
    for code, bname in BRANDS.items():
        if only and only not in (code, bname):
            continue
        tot += one(code, bname, apply_)
        time.sleep(GAP)
    print("\n끝. 메뉴 %d개%s" % (tot, "" if apply_ else "  (미저장 — --apply)"))


if __name__ == "__main__":
    main()
