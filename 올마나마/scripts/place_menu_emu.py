# -*- coding: utf-8 -*-
"""에뮬레이터(또는 실제 폰)로 **네이버 플레이스 메뉴판**을 읽는다. 2026-07-27

🔴 왜 필요한가 (대표 지시)
   *"웹사이트는 느리니 에뮬에서 플레이스 검색해서 메뉴판 확인하고 작성하는 수밖에 없어"*

   오늘 브랜드 홈페이지를 49곳 훑은 결과 **가격을 공개하는 곳이 15곳뿐**이었다.
   나머지 34곳은 홈페이지에 가격이 아예 없다(와플대학 129메뉴·설빙 100·미스터피자 98 전부 가격 0건).
   네이버 플레이스 메뉴판은 **홀 매장가**라 배달앱(배달비 포함)보다 우리 기준에 맞는다.

⚠️ 네이버 플레이스는 PC 쪽 3경로(in-app·WebFetch·Chrome)가 다 정책 차단이다.
   그래서 **안드로이드 크롬**으로 연다.

    python scripts/place_menu_emu.py 맘스터치
    python scripts/place_menu_emu.py 맘스터치 --device emulator-5554
"""
import io
import os
import re
import subprocess
import sys
import time
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
ADB = r"D:\Android\Sdk\platform-tools\adb.exe"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "place_menu")


def sh(dev, *args, timeout=60):
    r = subprocess.run([ADB, "-s", dev] + list(args), capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace")


def screen(dev):
    """화면 크기 (가로 모드일 수 있다 — 좌표를 여기서 계산해야 한다)."""
    m = re.search(r"(\d+)x(\d+)", sh(dev, "shell", "wm", "size"))
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 1920)


def dump(dev):
    """현재 화면의 텍스트 노드를 뽑는다."""
    sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = sh(dev, "shell", "cat", "/sdcard/ui.xml")
    return [t for t in re.findall(r'text="([^"]+)"', xml) if t.strip()]


def tap_text(dev, texts, want, exact=False):
    """화면에서 `want` 노드를 눌러본다. bounds 를 다시 읽어야 하므로 xml 을 직접 판다.

    🔴 `exact=True` 면 **정확히 그 글자**인 노드를 누른다 (2026-07-27).
       부분 일치로 누르면 «설빙 명동점» 을 찾다가 첫 번째 매장만 계속 눌려
       2·3번째 매장이 목록 화면에 그대로 머물렀다.
    """
    sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = sh(dev, "shell", "cat", "/sdcard/ui.xml")
    for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        t = m.group(1)
        if (t == want) if exact else (want in t):
            x = (int(m.group(2)) + int(m.group(4))) // 2
            y = (int(m.group(3)) + int(m.group(5))) // 2
            if x <= 0 or y <= 0:
                continue
            sh(dev, "shell", "input", "tap", str(x), str(y))
            return True
    return False


def tap_scroll(dev, want, tries=10):
    """화면 밖에 있는 노드를 **스크롤해 가며** 누른다.

    🔴 화면 밖 노드는 `bounds="[0,0][0,0]"` 로 나온다 — 좌표가 0 이라 탭이 안 먹는다.
       그걸 «못 찾음» 으로 끝내서 매장 진입이 계속 실패했다(2026-07-27 · 2026-07-28).
       「플레이스」 목록은 검색 결과 한참 아래에 있어 **거의 항상 화면 밖**이다.
    """
    w, h = screen(dev)
    for i in range(tries):
        if tap_text(dev, dump(dev), want, exact=True):
            return True
        # 아래로 조금씩 — 한 번에 많이 내리면 목록을 지나친다
        sh(dev, "shell", "input", "swipe",
           str(w // 2), str(int(h * 0.75)), str(w // 2), str(int(h * 0.3)), "400")
        time.sleep(1.6)
    return False


def search_stores(dev, q, texts):
    """**검색 화면**의 「플레이스」 목록에서 (지점명, 주소) 를 읽는다.

    🔴 지도(`m.place.naver.com/restaurant/list`)로 가지 않는다 — 두 번 지적받은 실수다
       (2026-07-27, 2026-07-28). 지도는 목록이 화면에 안 그려져 탭이 안 먹는다.
       **검색 결과 하단 「플레이스」에 매장이 이미 여러 곳 나열돼 있다:**

           빽다방 태평로점테이크아웃커피
           370m
           서울 중구 태평로2가 상세주소 열기
           빽다방 종로새문안점테이크아웃커피
           …

    ⚠️ 웹뷰라 uiautomator 덤프에 **링크 주소(restaurant/id)가 안 실린다.**
       id 가 없다고 «검색으로는 안 된다» 로 읽으면 안 된다 — **이름으로 누르면 된다.**
       지점명·주소도 여기서 그대로 얻는다(규칙: 어느 지점에서 봤는지 같이 저장).
    """
    out, i = [], 0
    while i < len(texts):
        t = texts[i].strip()
        # 「빽다방 태평로점테이크아웃커피」 — 브랜드명으로 시작하고 «점» 이 들어간다
        if t.startswith(q) and len(t) > len(q) and re.search(r"점(?=[^0-9]|$)", t):
            nm = t
            addr = ""
            for j in range(i + 1, min(i + 5, len(texts))):
                if re.match(r"^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충[북남]|"
                            r"전[북남]|경[북남]|제주)", texts[j]):
                    addr = texts[j].replace("상세주소 열기", "").strip()
                    break
            if not any(o[0] == nm for o in out):
                out.append((nm, addr))
        i += 1
    return out


def main():
    # 🔴 `--shops 3` 의 `3` 이 브랜드명으로 먹히던 버그(2026-07-27). 옵션 값을 먼저 걷어낸다.
    argv, skip = sys.argv[1:], set()
    for i, a in enumerate(argv):
        if a in ("--device", "--shops") and i + 1 < len(argv):
            skip.add(i + 1)
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in skip]
    dev = "emulator-5554"
    if "--device" in sys.argv:
        dev = sys.argv[sys.argv.index("--device") + 1]

    # --need : 공개 브랜드 중 아직 도장이 안 끝난 곳을 DB 에서 뽑아 순서대로 돈다
    if "--need" in sys.argv:
        import sqlite3
        db = sqlite3.connect(os.path.join(BASE, "data", "eolmanama.db"))
        db.row_factory = sqlite3.Row
        args = [r["name"] for r in db.execute("""
            SELECT b.name FROM brands b WHERE b.published=1
              AND (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
              AND (SELECT COUNT(*) FROM menus m JOIN menu_verified v ON v.menu_id=m.id
                     WHERE m.brand_id=b.id)
                  < (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id)
            ORDER BY b.frcs_cnt DESC""")]
        print("대상 %d곳: %s\n" % (len(args), ", ".join(args[:8]) + " …"))

    if not args:
        print("사용법: python scripts/place_menu_emu.py <브랜드명> | --need")
        return

    # 매장 몇 곳을 볼지 — **브랜드마다 다르다**(`menu_price_store.N_STORES`).
    #   맥도날드·버거킹은 직영이라 전국이 같은 값이다 → 1곳
    #   가맹 브랜드는 점주가 값을 정할 수 있다 → 3곳
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import menu_price_store as PS
    force_shops = int(sys.argv[sys.argv.index("--shops") + 1]) if "--shops" in sys.argv else None
    save = "--apply" in sys.argv
    db = PS.connect()
    cur = db.cursor()
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")

    for i, one in enumerate(args, 1):
        shops = force_shops or PS.n_stores(one)
        print("\n%s [%d/%d] %s (매장 %d곳) %s"
              % ("=" * 22, i, len(args), one, shops, "=" * 14))
        br = cur.execute("SELECT id FROM brands WHERE name=?", (one,)).fetchone()
        allpairs = {}
        broke = []
        # 🔴 **메뉴판이 빈 지점이 많다** (2026-07-28 대표 지시: *"없으면 더 찾아"*).
        #    빽다방 2·3번 매장은 메뉴를 1~3개만 올려놨다. «3곳을 봤다» 가 아니라
        #    **«메뉴가 있는 곳 3곳»** 을 채워야 비교가 된다.
        #    그래서 빈 곳은 세지 않고 다음 매장으로 넘어간다(상한 MAX_TRY).
        MAX_TRY = max(shops * 4, 10)
        got_stores, nth = 0, 0
        while got_stores < shops and nth < MAX_TRY:
            try:
                pairs, meta = one_brand(dev, one, nth)
                if not pairs:
                    if meta.get("store_id") is None and meta.get("store") is None:
                        broke.append("매장 목록이 %d곳까지밖에 없다" % nth)
                        break                       # 더 찾을 매장이 없다
                    broke.append("%s 메뉴 0개" % (meta.get("store") or "매장%d" % (nth + 1)))
                    nth += 1
                    continue
                got_stores += 1
                for nm, pr, desc in pairs:
                    allpairs.setdefault(nm, []).append(
                        {"price": pr, "store": meta["store"], "store_id": meta["store_id"],
                         "addr": meta.get("addr"), "url": meta["url"], "at": now})
            except Exception as e:
                broke.append("매장%d %s" % (nth + 1, str(e)[:50]))
                print("  ✗ 매장%d 실패: %s" % (nth + 1, str(e)[:60]))
            nth += 1
        print("  · 메뉴가 있는 지점 %d/%d곳 확보 (매장 %d곳 확인)" % (got_stores, shops, nth))
        # 🔴 **깨지면 깨졌다고 보고한다.** 조용히 실패하면 옛 가격이 그대로 서빙된다.
        if broke:
            print("  🔴 수집이 깨진 곳: %s" % " / ".join(broke))
        if not allpairs:
            print("  🔴 %s — 한 건도 못 모았다. 사이트 구조가 바뀌었을 수 있다." % one)
            continue

        stats = {"new": 0, "changed": 0, "same": 0, "skip": 0}
        diffs, changed_rows = [], []
        for nm, samples in allpairs.items():
            price, agreed, note = PS.decide(samples, need=shops)
            if not price:
                continue
            if note:
                diffs.append((nm, note))
            if save and br:
                # 🔴 **한 건씩 즉시 저장** — 중간에 끊겨도 이어서 할 수 있게
                before = cur.execute("""SELECT price FROM brand_menu_official
                    WHERE brand_id=? AND name=?""", (br["id"], nm)).fetchone()
                r = PS.put(cur, br["id"], nm, price, source=PS.SRC_PLACE,
                           samples=samples, note=note, now=now)
                db.commit()
                stats[r] = stats.get(r, 0) + 1
                if r == "changed":
                    changed_rows.append((nm, before["price"], price))
            else:
                stats["same"] += 1

        print("  ▣ 메뉴 %d개 · 지점별로 갈린 것 %d개" % (len(allpairs), len(diffs)))
        for nm, note in diffs[:10]:
            print("      ⚠️ %-24s %s" % (nm[:24], note))
        if save:
            print("     저장: 새로 %d · **바뀜 %d** · 그대로 %d · 사람확정이라 건너뜀 %d"
                  % (stats["new"], stats["changed"], stats["same"], stats["skip"]))
            # 🔴 **값이 바뀐 것만** 보고한다 — 전체를 다시 볼 필요가 없다
            for nm, a, b in changed_rows[:15]:
                print("      💰 %-24s %s → %s"
                      % (nm[:24], format(a or 0, ","), format(b, ",")))
        else:
            print("     (미저장 — 반영하려면 --apply)")
        # 원문도 남긴다 — 판정이 틀렸을 때 되돌릴 수 있게
        p = os.path.join(OUT, re.sub(r"[^0-9A-Za-z가-힣]+", "", one) + "_menu.txt")
        with io.open(p, "w", encoding="utf-8") as f:
            for nm, samples in allpairs.items():
                price, agreed, note = PS.decide(samples, need=shops)
                f.write("%s\t%s\t%s\t%s\n" % (
                    nm, price, note or "",
                    " | ".join("%s@%s" % (s["price"], s["store"]) for s in samples)))
        print("      → %s" % os.path.relpath(p, BASE))


def one_brand(dev, q, nth=0):
    # 🔴 탭이 쌓이면 화면이 엉킨다 — 실제로 70개까지 쌓여 2·3번째 매장이 «0개» 가 됐다.
    #    브랜드/매장을 바꿀 때마다 크롬을 새로 시작한다.
    # 🔴 `m.place.naver.com/restaurant/list` 로 바로 가면 **지도 화면**이 뜨고
    #    목록이 화면에 안 그려져 탭이 안 먹는다. 매장에 들어갈 수가 없다. (2026-07-27 삽질)
    #    대표 지적: *"왜 어렵게. 네이버에서 홍콩반점 치면 하단에 여러 개가 나와"*
    #
    #    ✅ **그냥 네이버 검색**이면 「플레이스 → 주요 메뉴」에 **가격이 바로 나온다.**
    #       매장에 들어갈 필요도 없다. 홍콩반점0410 → 짜장면 7,000 · 짬뽕 9,000 …
    sh(dev, "shell", "am", "force-stop", "com.android.chrome")
    time.sleep(2)
    url = "https://m.search.naver.com/search.naver?query=" + urllib.parse.quote(q)
    print("■ %s 열기" % url)
    sh(dev, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)
    # 🔴 고정 대기로는 부족하다 (2026-07-27). 크롬을 새로 띄우면 12초에도 목록이 안 뜬 채
    #    이전 화면이 남아 «찾았다» 고 오판했다. **목록이 실제로 보일 때까지** 기다린다.
    for _ in range(10):
        time.sleep(3)
        if any("주요 메뉴" in t or "플레이스" in t for t in dump(dev)):
            break
    texts = dump(dev)

    # 🔴 검색 결과의 「주요 메뉴」는 **6~10개 요약**이다 (2026-07-27).
    #    전체 메뉴판은 **매장 페이지**에 있다 — 맘스터치 39개·처갓집 37개가 그렇게 나왔다.
    #    검색 결과 안에 매장 id 가 있으면 그 메뉴판으로 넘어가 **싹 긁는다.**
    #    (대표 지시: *"가격정보를 싹 모아"*)
    ids = list(dict.fromkeys(re.findall(r"restaurant/(\d{5,})", sh(
        dev, "shell", "cat", "/sdcard/ui.xml"))))
    if not ids:
        sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
        ids = list(dict.fromkeys(re.findall(r"restaurant/(\d{5,})",
                                            sh(dev, "shell", "cat", "/sdcard/ui.xml"))))
    store_id = None
    if ids:
        store_id = ids[min(nth, len(ids) - 1)]
        murl = "https://m.place.naver.com/restaurant/%s/menu/list" % store_id
        print("  · 매장 메뉴판 %s" % murl)
        sh(dev, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", murl)
        for _ in range(8):
            time.sleep(3)
            t2 = dump(dev)
            if any("원" in x and re.search(r"[\d,]{3,7}\s*원", x) for x in t2):
                texts = t2
                break
    # ⛔ **지도(`m.place.naver.com/restaurant/list`)로 가지 않는다.**
    #    두 번 지적받은 실수다(2026-07-27 · 2026-07-28 *"또 왜 지도 쓰는거야 검색하라니깐?"*).
    #    지도는 목록이 화면에 안 그려져 탭이 안 먹고, 어쩌다 들어가도 **늘 첫 매장**만 잡혀
    #    같은 매장을 세 번 보고 «3곳 일치» 로 기록될 뻔했다.
    #    ✅ 검색 결과 하단 「플레이스」에 매장이 이미 여러 곳 나열돼 있다 — **거기서 고른다.**
    store_nm = store_addr = ""
    if not ids:
        # 🔴 「플레이스」 라는 **글자만 보고 다 그려졌다고 판단하면 안 된다** (2026-07-28).
        #    상단 탭에도 「플레이스」 가 있어서, 매장 목록이 뜨기 전에 덤프하고
        #    «매장 0곳» 으로 끝냈다(1회차엔 3곳을 찾던 브랜드가 2회차에 0곳이 됐다).
        #    **매장 줄이 실제로 잡힐 때까지** 다시 읽는다.
        cands = search_stores(dev, q, texts)
        for _ in range(8):
            if cands:
                break
            time.sleep(3)
            texts = dump(dev)
            cands = search_stores(dev, q, texts)
        # 검색 결과는 매장 3곳만 보여준다 — 더 필요하면 「펼쳐서 더보기」를 눌러 늘린다
        # (대표 지시 2026-07-28: *"없으면 더 찾아"*)
        for _ in range(4):
            if len(cands) > nth:
                break
            if not tap_scroll(dev, "펼쳐서 더보기", tries=8):
                break
            time.sleep(4)
            texts = dump(dev)
            n0 = len(cands)
            cands = search_stores(dev, q, texts)
            if len(cands) <= n0:            # 더 안 늘어나면 그만
                break
        if nth >= len(cands):
            print("  · 검색 플레이스에 매장이 %d곳뿐 — %d번째는 건너뛴다" % (len(cands), nth + 1))
            return [], {"store_id": None, "store": None, "addr": None, "url": None}
        store_nm, store_addr = cands[nth]
        print("  · 검색 플레이스 %d/%d: %s (%s)"
              % (nth + 1, len(cands), store_nm[:26], store_addr[:20]))
        if tap_scroll(dev, store_nm):
            time.sleep(7)
            for _ in range(4):
                sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml")
                mm = re.search(r"m\.place\.naver\.com/restaurant/(\d+)",
                               sh(dev, "shell", "cat", "/sdcard/ui.xml")) or \
                    re.search(r"m\.place\.naver\.com/restaurant/(\d+)",
                              sh(dev, "shell", "dumpsys", "activity", "activities"))
                if mm:
                    store_id = mm.group(1)
                    break
                time.sleep(3)
            if store_id:
                murl = "https://m.place.naver.com/restaurant/%s/menu/list" % store_id
                print("    → 메뉴판 %s" % murl)
                sh(dev, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", murl)
                for _ in range(8):
                    time.sleep(3)
                    t2 = dump(dev)
                    if any(re.search(r"[\d,]{3,7}\s*원", x) for x in t2):
                        texts = t2
                        break
            else:
                print("    🔴 매장 id 를 못 얻었다 — 검색 화면의 「주요 메뉴」만 쓴다")
        else:
            print("    🔴 매장을 못 눌렀다 — 검색 화면의 「주요 메뉴」만 쓴다")

    # 🔴 **어느 지점에서 봤는지 같이 돌려준다** (`작업순서-2026-07-28.md` §플레이스 수집 규칙).
    #    나중에 «왜 이 가격이지» 를 풀려면 지점을 알아야 한다. 값만 남기면 되돌릴 수 없다.
    if not store_nm:
        store_nm = next((t for t in texts
                         if q in t and len(t) > len(q) and "메뉴" not in t), "")
    return scroll_collect(dev, texts, q), {
        "store_id": store_id,
        "store": (store_nm or "")[:40] or ("매장 %s" % (store_id or "?")),
        "addr": store_addr or None,
        "url": ("https://m.place.naver.com/restaurant/%s" % store_id) if store_id else None,
    }

    texts = dump(dev)
    # 위치 권한 팝업이 뜨면 '차단'
    if any("위치에 액세스" in t for t in texts):
        print("  · 위치 권한 팝업 → 차단")
        tap_text(dev, texts, "차단")
        time.sleep(3)
        texts = dump(dev)

    # ── 매장을 여러 곳 본다 (대표 지시 2026-07-27: *"혹시 모르니깐 플레이스를 2개 정도 더 확인해"*).
    #    프랜차이즈는 본사 권장가라 대체로 같지만, 한 매장만 보고 단정하면
    #    그 매장의 지역·특수 가격을 전체 가격으로 잘못 쓸 수 있다.
    #
    # 🔴 **매장을 클릭하지 않는다** (2026-07-27). 클릭하면 지도 화면으로 새 탭이 열려
    #    2·3번째 매장이 «메뉴 0개» 가 됐고 탭이 70개까지 쌓였다.
    #    목록 화면의 DOM 에 이미 각 매장의 `restaurant/{id}` 가 들어 있으니 **id 만 긁어서**
    #    메뉴 주소로 바로 간다.
    # ⚠️ 목록은 웹뷰라 uiautomator 덤프에 `restaurant/{id}` 가 안 나온다.
    #    그래서 **n번째 매장을 눌러** 주소창에서 id 를 읽는다.
    # 🔴 플레이스 검색 결과는 **지도 화면**으로 먼저 뜬다 (2026-07-27).
    #    매장 목록은 DOM 에는 있지만 화면에 안 그려져 있어 **탭이 안 먹는다**.
    #    화면엔 「목록보기」 버튼만 있다 — 그걸 먼저 눌러야 목록이 그려진다.
    #    (이걸 몰라서 «매장을 못 눌렀다» 를 계속 봤다)
    if any("목록보기" in t for t in texts):
        tap_text(dev, texts, "목록보기", exact=True)
        time.sleep(4)
        texts = dump(dev)

    # 매장 줄은 «설빙 명동점빙수» 처럼 «브랜드 + 지점명 + 업종» 꼴이다.
    #   · 제목(«설빙 메뉴»)·안내문은 뺀다
    #   · «점»·«店» 이 들어가면 지점이다. 없으면 브랜드명보다 길고 안내어가 없는 줄
    BAD = ("메뉴", "목록", "프로필", "현재 위치", "상세주소", "영업", "리뷰", "전화",
           "길찾기", "저장", "공유", "배달", "네이버")

    def pick(ts):
        return [t for t in dict.fromkeys(ts)
                if q in t and not any(b in t for b in BAD) and len(t) > len(q)]

    # 🔴 크롬을 재시작하면 목록이 늦게 뜬다 — 한 번 읽고 0곳이면 몇 번 더 기다린다.
    #    (기다리지 않고 «0곳» 으로 끝내던 버그, 2026-07-27)
    stores = pick(texts)
    for _ in range(6):
        if stores:
            break
        time.sleep(4)
        texts = dump(dev)
        stores = pick(texts)
    if nth >= len(stores):
        print("  · 매장이 %d곳뿐이라 건너뜀" % len(stores))
        return []
    print("  · 매장 %d/%d: %s" % (nth + 1, len(stores), stores[nth][:34]))
    # 🔴 스와이프 좌표는 **화면 크기에서 계산**한다 (2026-07-27).
    #    에뮬이 가로 모드(1600×900)인데 세로 기준 y=1400 을 쓰다가 스크롤이 아예 안 먹었고,
    #    2·3번째 매장을 «못 눌렀다» 로 끝냈다.
    # 🔴 화면 밖 노드는 `bounds="[0,0][0,0]"` 로 나온다 (2026-07-27).
    #    그걸 «못 찾음» 으로 끝내서 2·3번째 매장이 계속 실패했다.
    #    → 유효한 좌표가 나올 때까지 **스크롤하면서** 찾는다.
    sw, sh_ = screen(dev)
    ok = False
    for _ in range(12):
        if tap_text(dev, texts, stores[nth], exact=True):
            ok = True
            break
        sh(dev, "shell", "input", "swipe", str(sw // 2), str(int(sh_ * 0.80)),
           str(sw // 2), str(int(sh_ * 0.30)), "400")
        time.sleep(2)
    if not ok:
        print("  ✗ 매장을 못 눌렀다")
        return []
    time.sleep(8)

    # ── 매장 id 를 URL 에서 뽑아 **메뉴 주소로 직접 간다**.
    #    탭을 누르는 것보다 확실하다(가로/세로 모드에 따라 좌표가 달라진다).
    #    주소 형태: m.place.naver.com/restaurant/{id}/menu/list
    # 🔴 2·3번째 매장에서 id 를 못 잡아 «메뉴 0개» 가 나왔다(2026-07-27).
    #    `dumpsys activity activities` 에는 **직전 주소**가 남아 있을 때가 있어 한 번으로는 부족하다.
    #    주소창 텍스트(uiautomator)까지 같이 보고, 몇 번 다시 읽는다.
    m = None
    for _ in range(4):
        for src in (sh(dev, "shell", "dumpsys", "activity", "activities"),
                    (sh(dev, "shell", "uiautomator", "dump", "/sdcard/ui.xml"),
                     sh(dev, "shell", "cat", "/sdcard/ui.xml"))[1]):
            mm = re.search(r"m\.place\.naver\.com/restaurant/(\d+)", src)
            if mm:
                m = mm
                break
        if m:
            break
        time.sleep(3)
    if m:
        murl = "https://m.place.naver.com/restaurant/%s/menu/list" % m.group(1)
        print("  · 메뉴판 %s" % murl)
        sh(dev, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", murl)
        time.sleep(8)
    texts = dump(dev)
    return scroll_collect(dev, texts, q)


def scroll_collect(dev, texts, q):
    """메뉴판 화면을 끝까지 훑어 «메뉴명·가격·구성» 을 뽑는다."""
    # ── 아래로 훑으며 모으기. 화면 크기를 읽어 그에 맞게 쓸어내린다
    wm = sh(dev, "shell", "wm", "size")
    sz = re.search(r"(\d+)x(\d+)", wm)
    W, H = (int(sz.group(1)), int(sz.group(2))) if sz else (1080, 1920)
    x, y1, y2 = W // 2, int(H * 0.85), int(H * 0.25)
    seen, allt = set(texts), list(texts)
    still = 0
    for _ in range(20):
        sh(dev, "shell", "input", "swipe", str(x), str(y1), str(x), str(y2), "400")
        time.sleep(2)
        new = [t for t in dump(dev) if t not in seen]
        if not new:
            still += 1
            if still >= 2:
                break
        else:
            still = 0
            seen.update(new)
            allt.extend(new)
    texts = allt

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, re.sub(r"[^0-9A-Za-z가-힣]+", "", q) + ".txt")
    io.open(p, "w", encoding="utf-8").write("\n".join(texts))
    print("  · 텍스트 노드 %d개 → %s" % (len(texts), os.path.relpath(p, BASE)))

    # 🔴 네이버 플레이스는 «메뉴명 + 구성설명 + 가격» 이 **한 줄**로 들어온다:
    #      "대표 싸이버거 세트 싸이버거단품+케이준양념감자(중)+콜라 9,500원"
    #      "휠렛버거 세트 휠렛버거단품+케이준양념감자(중)+콜라 9,300원"
    #    그래서 «가격 앞줄이 이름» 규칙이 안 통한다. 한 줄에서 끝의 가격을 떼고,
    #    남은 앞부분에서 «구성 설명»(+ 가 들어간 조각·긴 문장)을 잘라 이름만 남긴다.
    pairs, seenname = [], set()
    for t in texts:
        # `&#127798;` 같은 이모지 코드와 변형선택자를 턴다 — 매운맛 고추 표시가 이름에 붙는다
        s = re.sub(r"&#\d+;|️", "", t).replace("&amp;", "&").strip()
        m2 = re.search(r"([\d,]{3,7})\s*원\s*$", s)
        if not m2:
            continue
        price = int(m2.group(1).replace(",", ""))
        if not (500 <= price <= 300000):
            continue
        head = s[:m2.start()].strip()
        head = re.sub(r"^(대표|신메뉴|인기|NEW)\s+", "", head)
        # 구성 설명은 보통 «A1+B1+C1» 이나 긴 문장이다 — 첫 덩어리만 이름으로 본다
        head = re.split(r"\s{2,}", head)[0]
        # ① 구성 설명(«A1+B1») 앞까지가 이름
        mm = re.match(r"^(.{2,30}?)\s+(?=\S*\+)", head)
        name = (mm.group(1) if mm else head).strip()
        # ② 설명 문장이 붙은 경우 — 설명은 **띄어쓰기가 많다**.
        #    "맘스양념치킨(순살) 매콤달콤 특제 양념소스로 꿀맛" → 앞 1~2어절만 이름
        if name is head and head.count(" ") >= 2:
            w = head.split()
            for take in (1, 2):
                cand = " ".join(w[:take])
                # 괄호가 닫히지 않으면 더 붙인다: "치즈스틱(2조각)"
                if cand.count("(") == cand.count(")") and 2 <= len(cand) <= 24:
                    name = cand
                    break
        if not name or len(name) > 40 or name in seenname:
            continue
        seenname.add(name)
        pairs.append((name, price, head[len(name):].strip()))
    print("  · 메뉴+가격 %d개" % len(pairs))
    return pairs


if __name__ == "__main__":
    main()
