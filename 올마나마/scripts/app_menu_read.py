# -*- coding: utf-8 -*-
"""**브랜드 앱 화면**에서 메뉴 이름·가격을 읽는다. 2026-07-28

    python scripts/app_menu_read.py --device 172.30.1.59:44737 --peek
    python scripts/app_menu_read.py --device ... --brand 버거킹 --scroll 20
    python scripts/app_menu_read.py --device ... --brand 버거킹 --scroll 20 --apply

왜 앱인가
--------
버거킹·맥도날드는 **공식 홈페이지에 가격이 아예 없다**(DOM 전체에 「원」 0건, 실측).
플레이스는 점주 등록분만 나온다. 그런데 **공식 앱에는 전 메뉴 가격이 다 있다.**
두 브랜드는 직영 위주라 **전국이 같은 값**이므로(대표 확인) 한 화면이면 충분하다.

⛔ 사람이 쓰는 폰이다. **스크롤만** 한다 — 누르거나 주문 화면으로 들어가지 않는다.
⛔ 「원」이 붙은 숫자를 다 가져오면 배달비·쿠폰·총액이 섞인다. 이름과 짝지어진 것만 쓴다.
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

ADB = r"D:\Android\Sdk\platform-tools\adb.exe"

# 🔴 앱은 «13,100원 ~» 처럼 **물결표**를 붙인다 (옵션에 따라 값이 오르는 메뉴).
#    `원$` 으로 끝나야 한다고 만들었더니 그런 줄이 전부 빠졌다 —
#    버거킹이 162개 중 23개만 잡힌 것도 이것 때문이었다(2026-07-28).
#    물결표가 붙은 값은 **최저가**다. 그대로 쓰되 뒤에 오는 기호는 무시한다.
RX_PRICE = re.compile(r"^([\d]{1,3}(?:,[\d]{3})+)\s*원?\s*[~〜]?\s*$")
# 메뉴명이 아닌 줄
BAD = ("배달", "포장", "매장", "장바구니", "주문", "결제", "쿠폰", "적립", "로그인", "검색",
       "홈", "메뉴", "이벤트", "더보기", "전체", "선택", "담기", "총", "합계", "할인",
       "최소", "배송비", "닫기", "확인", "취소", "내역", "설정", "알림")


def sh(dev, *a, timeout=90):
    r = subprocess.run([ADB, "-s", dev] + list(a), capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace")


def unesc(s):
    # 🔴 uiautomator 덤프는 XML 이라 `&` 가 `&amp;` 로 들어온다 (2026-07-28).
    #    그대로 비교하면 「와퍼&주니어」 탭을 **영영 못 찾는다.**
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&apos;", "'"), ("&#10;", " ")):
        s = s.replace(a, b)
    return s


def dump(dev):
    sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = sh(dev, "shell", "cat", "/sdcard/ui.xml")
    return xml, [unesc(t) for t in re.findall(r'text="([^"]+)"', xml) if t.strip()]


def screen(dev):
    m = re.search(r"(\d+)x(\d+)", sh(dev, "shell", "wm", "size"))
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)


def is_name(t):
    t = t.strip()
    if not (2 <= len(t) <= 34):
        return False
    if RX_PRICE.match(t) or re.match(r"^[\d,\s원%]+$", t):
        return False
    if any(b == t or (len(b) > 1 and t.startswith(b) and len(t) < len(b) + 3) for b in BAD):
        return False
    return bool(re.search(r"[가-힣A-Za-z]", t))


def pairs(texts):
    """«이름» 바로 아래 «5,900원» 이 오는 꼴. 앱 목록은 대부분 이 순서다.

    🔴 «5,200원 ~» 의 물결표는 **단품 최저가**라는 뜻이다 (대표 확인 2026-07-28).
       세트를 고르면 그 이상이 된다. 우리 원가율은 **단품 기준**이라 이 값이 맞지만,
       «단품가인지 확정가인지» 를 안 남기면 나중에 세트값과 섞인다.
       → 물결표 여부를 함께 돌려준다.
    """
    out = []
    for i, t in enumerate(texts):
        s = t.strip()
        m = RX_PRICE.match(s)
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        if not (500 <= price <= 100000):
            continue
        base_only = ("~" in s) or ("〜" in s)
        for j in range(i - 1, max(-1, i - 4), -1):
            if is_name(texts[j]):
                out.append((texts[j].strip(), price, base_only))
                break
    return out


def main():
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "emulator-5554"
    n = int(sys.argv[sys.argv.index("--scroll") + 1]) if "--scroll" in sys.argv else 0
    brand = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    apply_ = "--apply" in sys.argv

    w, h = screen(dev)
    print("기기 %s · 화면 %dx%d" % (dev, w, h), flush=True)
    xml, texts = dump(dev)
    if "--peek" in sys.argv or not brand:
        print("\n― 지금 화면 글자 %d개 ―" % len(texts))
        for t in texts[:50]:
            print("   %s" % t[:70])
        got = pairs(texts)
        print("\n― 이 화면의 «이름 + 가격» %d개 ―" % len(got))
        for nm, pr, base_only in got[:20]:
            print("   %-30s %s원%s" % (nm[:30], format(pr, ","),
                                       "  (단품 최저가)" if base_only else ""))
        return

    # 🔴 **탭을 안 누르면 한 탭만 읽는다** (2026-07-28 버거킹에서 22개로 멈춘 진짜 원인).
    #    스크롤을 아무리 해도 안 늘어서 «스와이프가 약하다» 로 오판했는데,
    #    실제로는 상단 카테고리(프리미엄/와퍼&주니어/치킨&슈림프/사이드/음료…) 중
    #    첫 탭만 보고 있었다. **탭마다 들어가서** 스크롤한다.
    tab_names = [t.strip() for t in sys.argv[sys.argv.index("--tabs") + 1].split(",")] \
        if "--tabs" in sys.argv else []

    def tap(want, ymax=0.35):
        """🔴 **같은 글자가 화면에 두 개씩 있다** (2026-07-28 버거킹 사고).
           「메뉴 소개」·「주문하기」 가 상단 탭에도, 서랍 메뉴에도 있어서
           엉뚱한 걸 눌러 **설정 화면으로 빠져나갔다**(탭 8개가 전부 «0개 추가»).
           탭 바는 화면 **위쪽**에 있으니 y 범위를 제한한다."""
        xml2, _ = dump(dev)
        hits = []
        for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml2):
            if unesc(m.group(1)).strip() != want:
                continue
            x = (int(m.group(2)) + int(m.group(4))) // 2
            y = (int(m.group(3)) + int(m.group(5))) // 2
            if x > 0 and y > 0:
                hits.append((y, x))
        if not hits:
            return False
        hits.sort()                        # 위에 있는 것부터
        y, x = hits[0]
        if y > h * ymax:
            print("    ⚠️ «%s» 가 탭 바 밖(y=%d)이다 — 안 누른다" % (want, y), flush=True)
            return False
        sh(dev, "shell", "input", "tap", str(x), str(y))
        return True

    # 아래로 내리며 모은다 — 사람 폰이니 **스크롤·탭만** 한다(주문 화면엔 안 들어간다)
    # 🔴 한 메뉴에 **값이 둘** 나온다 (2026-07-28 버거킹 앱):
    #        콰트로치즈와퍼 1인팩   15,300원 / 10,700원
    #    큰 값이 정가, 작은 값이 **앱 할인가**다.
    #    우리 판매가 기준은 **매장 홀 가격**이므로 정가를 쓴다
    #    (`sell-price-is-hall-not-delivery` 와 같은 갈래. 앱 할인은 한시적이고
    #     앱 주문에만 붙는다 — 그걸 판매가로 쓰면 원가율이 부풀려진다).
    #    ⚠️ 두 값을 **둘 다 기록**한다. 나중에 «왜 이 값이지» 를 풀어야 한다.
    allp = {}
    rounds = [(t, n) for t in tab_names] or [(None, n)]
    def to_top(times=14):
        """🔴 탭을 누르기 전에 **맨 위로 되돌린다** (2026-07-28).
           앞 탭에서 스크롤을 내린 채로 다음 탭을 찾으면 **탭 바가 화면 밖**이라 못 누른다."""
        for _ in range(times):
            sh(dev, "shell", "input", "swipe", str(w // 2), str(int(h * 0.3)),
               str(w // 2), str(int(h * 0.85)), "300")
            time.sleep(0.5)
        time.sleep(1.2)

    def tab_scroll_left():
        """탭 바는 **가로 스크롤**이다 — 오른쪽 탭은 화면 밖이라 bounds 가 0 으로 나온다."""
        _, ts = dump(dev)
        y = int(h * 0.30)
        for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                             dump(dev)[0]):
            if unesc(m.group(1)).strip() in (tab_names or []):
                yy = (int(m.group(3)) + int(m.group(5))) // 2
                if yy > 0:
                    y = yy
                    break
        sh(dev, "shell", "input", "swipe", str(int(w * 0.85)), str(y),
           str(int(w * 0.15)), str(y), "420")
        time.sleep(1.3)

    for tname, nn in rounds:
        if tname:
            to_top()
            ok = tap(tname)
            for _ in range(4):             # 오른쪽 탭이면 탭 바를 옆으로 밀어 찾는다
                if ok:
                    break
                tab_scroll_left()
                ok = tap(tname)
            print("― 탭 «%s» %s" % (tname, "진입" if ok else "🔴 못 눌렀다"), flush=True)
            if not ok:
                continue
            time.sleep(3)
        before_n = len(allp)
        for i in range(max(nn, 1)):
            _, texts = dump(dev)
            for nm, pr, base_only in pairs(texts):
                k = re.sub(r"\s+", "", nm)
                d = allp.setdefault(k, {"name": nm, "prices": set(), "base": False,
                                        "tab": tname})
                d["prices"].add(pr)
                if base_only:
                    d["base"] = True
                # 🔴 **어느 탭에서 나왔는지 남긴다** (대표 지시 2026-07-28).
                #    메뉴판 탭(치킨·버거·사이드…)을 브랜드마다 통일하려면 원본 탭이 있어야 한다.
                if not d.get("tab"):
                    d["tab"] = tname
            if i < nn - 1:
                # 길고 느리게 민다 — 짧고 빠르면 되튕겨서 화면이 안 바뀐다
                sh(dev, "shell", "input", "swipe", str(w // 2), str(int(h * 0.80)),
                   str(w // 2), str(int(h * 0.29)), "500")
                time.sleep(2.0)
        print("   → «%s» 에서 %d개 추가 (누적 %d)"
              % (tname or "현재 화면", len(allp) - before_n, len(allp)), flush=True)

    got = []
    for v in allp.values():
        ps = sorted(v["prices"], reverse=True)
        note = ("정가 %s · 앱할인가 %s" % (format(ps[0], ","), format(ps[-1], ","))
                if len(ps) > 1 else None)
        # 🔴 «5,200원 ~» 은 **단품 최저가**다. 세트는 메뉴를 눌러야 나오는데
        #    메뉴판엔 단품가면 충분하다(대표 확인 2026-07-28) — 세트는 모으지 않는다.
        if v.get("base"):
            note = (note + " · " if note else "") + "단품 최저가"
        got.append((v["name"], ps[0], note, v.get("tab")))

    print("\n― %s 앱에서 읽은 메뉴 %d개 ―" % (brand, len(got)))
    for nm, pr, note, tab in got:
        print("   [%-10s] %-28s %8s원  %s"
              % ((tab or "-")[:10], nm[:28], format(pr, ","), note or ""))
    if not apply_:
        print("\n(미저장 — --apply)")
        return

    import menu_price_store as PS
    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (brand,)).fetchone()
    if not br:
        print("🔴 DB 에 «%s» 브랜드가 없다" % brand)
        return
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    st, changed = {"new": 0, "changed": 0, "same": 0, "skip": 0}, []
    for nm, pr, note, tab in got:
        before = cur.execute("SELECT price FROM brand_menu_official WHERE brand_id=? AND name=?",
                             (br["id"], nm)).fetchone()
        # 앱은 **본사 기준 전 매장 공통가**다 — 출처를 official 로 남긴다
        r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL,
                   note="공식 앱 기준" + (" · " + note if note else ""), now=now)
        # 탭 이름을 원본 카테고리로 남긴다 — `menu_tab_apply.py` 가 표준 탭으로 바꾼다
        if tab:
            cur.execute("""UPDATE brand_menu_official
                           SET category_raw=COALESCE(category_raw, ?)
                           WHERE brand_id=? AND name=?""", (tab, br["id"], nm))
        db.commit()
        st[r] = st.get(r, 0) + 1
        if r == "changed":
            changed.append((nm, before["price"], pr))
    print("\n저장: 새로 %d · 바뀜 %d · 그대로 %d · 사람확정 건너뜀 %d"
          % (st["new"], st["changed"], st["same"], st["skip"]))
    for nm, a, b in changed[:15]:
        print("  💰 %-26s %s → %s" % (nm[:26], format(a or 0, ","), format(b, ",")))


if __name__ == "__main__":
    main()
