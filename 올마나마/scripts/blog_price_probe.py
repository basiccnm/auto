# -*- coding: utf-8 -*-
"""블로그에서 **브랜드 메뉴 가격표**를 찾는다. 2026-07-28
(대표 지시: *"맥도날드 가격 블로그 뒤져봐 버거킹 마찬가지"*)

    python scripts/blog_price_probe.py 맥도날드
    python scripts/blog_price_probe.py 버거킹 --open 2

왜 블로그인가
------------
맥도날드·버거킹은 **공식 홈페이지에 가격이 아예 없다**(DOM 전체에 「원」 0건, 실측 2026-07-28).
플레이스도 점주 등록분만 나온다. 그런데 두 곳 다 **직영 위주라 전국이 같은 값**이라
가격표를 통째로 정리한 블로그가 많다.

⛔ 블로그는 **옛 가격**이 흔하다. 그래서 규칙을 둔다:
   · 최소 **2개 글**에서 같은 값이 나와야 채택 (`menu_price_store.decide`)
   · **글 주소·작성일을 같이 저장**한다 — 나중에 «이 값 어디서 왔지» 를 풀어야 한다
   · 우리 공식 메뉴 이름에 **있는 메뉴만** 붙인다. 블로그에만 있는 이름은 만들지 않는다
⛔ 여기서는 **찾아서 보여주기만** 한다. DB 반영은 사람이 보고 결정한다.
"""
import re
import subprocess
import sys
import time
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
ADB = r"D:\Android\Sdk\platform-tools\adb.exe"
DEV = "emulator-5554"


def sh(*a, timeout=90):
    r = subprocess.run([ADB, "-s", DEV] + list(a), capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace")


def dump():
    sh("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = sh("shell", "cat", "/sdcard/ui.xml")
    return xml, [t for t in re.findall(r'text="([^"]+)"', xml) if t.strip()]


def open_url(url, wait_for=None, tries=10):
    sh("shell", "am", "force-stop", "com.android.chrome")
    time.sleep(2)
    # 🔴 URL 에 `&` 가 있으면 **adb 셸이 거기서 명령을 잘라** 크롬이 새 탭만 띄운다
    #    (2026-07-28. 기존 스크립트는 파라미터가 `?query=` 하나뿐이라 안 걸렸다).
    #    화면엔 즐겨찾기가 뜨는데 «블로그 글 0개» 로만 보여서 원인을 놓치기 쉽다.
    sh("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "'%s'" % url)
    for _ in range(tries):
        time.sleep(3)
        xml, texts = dump()
        if not wait_for or any(wait_for in t for t in texts):
            return xml, texts
    return dump()


def scroll_dump(n=14):
    """아래로 내리며 화면 글자를 모은다 — 가격표는 글 중간에 있다."""
    seen, out = set(), []
    w, h = 1600, 900
    m = re.search(r'bounds="\[0,0\]\[(\d+),(\d+)\]"', dump()[0])
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    for i in range(n):
        _, texts = dump()
        for t in texts:
            if t not in seen:
                seen.add(t)
                out.append(t)
        sh("shell", "input", "swipe", str(w // 2), str(int(h * 0.8)),
           str(w // 2), str(int(h * 0.25)), "350")
        time.sleep(1.4)
    return out


RX_PAIR = re.compile(r"^(.{2,28}?)\s*([\d]{1,2},[\d]{3})\s*원?$")


def pairs_from(texts):
    """«이름 4,500원» 꼴을 뽑는다. 같은 줄에 없으면 다음 줄이 가격인 경우도 본다."""
    out = []
    for i, t in enumerate(texts):
        t = t.strip()
        m = RX_PAIR.match(t)
        if m and not re.match(r"^\d", m.group(1)):
            out.append((m.group(1).strip(), int(m.group(2).replace(",", ""))))
            continue
        if 2 <= len(t) <= 28 and i + 1 < len(texts):
            m2 = re.match(r"^([\d]{1,2},[\d]{3})\s*원?$", texts[i + 1].strip())
            if m2 and not re.search(r"[\d,]{4,}", t):
                out.append((t, int(m2.group(1).replace(",", ""))))
    return out


def main():
    q = sys.argv[1] if len(sys.argv) > 1 else "맥도날드"
    nth = int(sys.argv[sys.argv.index("--open") + 1]) if "--open" in sys.argv else None
    url = ("https://m.search.naver.com/search.naver?ssc=tab.m_blog.all&query="
           + urllib.parse.quote(q + " 가격표"))
    print("■ %s" % url, flush=True)
    xml, texts = open_url(url, wait_for="블로그")

    # 🔴 목록이 늦게 그려진다 — 「… : 네이버 블로그검색」(문서 제목)·URL 줄만 잡히면
    #    아직 안 뜬 것이다. 실제 글 제목이 나올 때까지 기다렸다 다시 읽는다.
    def real_titles(ts):
        out = []
        for t in ts:
            t = t.strip()
            if len(t) < 8 or q not in t:
                continue
            if "네이버 블로그검색" in t or "search.naver" in t or t.startswith("http"):
                continue
            if t in out:
                continue
            out.append(t)
        return out

    titles = real_titles(texts)
    for _ in range(8):
        if titles:
            break
        time.sleep(3)
        xml, texts = dump()
        titles = real_titles(texts)

    if nth is None:
        # 블로그 글 제목 목록만 보여준다 — 어느 글을 열지 사람이 고른다
        print("\n― 블로그 글 후보 %d개 ―" % len(titles))
        for i, t in enumerate(titles[:15], 1):
            print("  %2d. %s" % (i, t[:70]))
        print("\n열어보려면: python scripts/blog_price_probe.py %s --open <번호>" % q)
        return

    if nth > len(titles):
        print("후보가 %d개뿐이다" % len(titles))
        return
    want = titles[nth - 1]
    print("· 여는 글: %s" % want[:60], flush=True)
    # 제목을 눌러 글로 들어간다
    for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if m.group(1) == want:
            x = (int(m.group(2)) + int(m.group(4))) // 2
            y = (int(m.group(3)) + int(m.group(5))) // 2
            if x > 0 and y > 0:
                sh("shell", "input", "tap", str(x), str(y))
                break
    time.sleep(7)
    texts2 = scroll_dump(16)
    got = pairs_from(texts2)
    seen, uniq = set(), []
    for nm, pr in got:
        k = re.sub(r"\s+", "", nm)
        if k in seen or not (500 <= pr <= 100000):
            continue
        seen.add(k)
        uniq.append((nm, pr))
    print("\n― 이 글에서 뽑은 «이름 + 가격» %d개 ―" % len(uniq))
    for nm, pr in uniq[:60]:
        print("  %-30s %s원" % (nm[:30], format(pr, ",")))
    if not uniq:
        # 🔴 «0개» 를 «블로그엔 가격이 없다» 로 읽으면 안 된다.
        #    블로그 가격표는 **이미지 한 장**인 경우가 많다 — 글자로는 안 잡힌다.
        #    글이 안 열렸는지, 열렸는데 이미지인지 **화면 글자를 보고** 갈라야 한다.
        print("\n― 화면에 실제로 잡힌 글자 (앞 40개) ―")
        for t in texts2[:40]:
            print("   %s" % t[:70])
        won = [t for t in texts2 if re.search(r"[\d,]{3,7}\s*원", t)]
        print("\n   「원」이 들어간 줄 %d개: %s" % (len(won), " | ".join(w[:24] for w in won[:8])))


if __name__ == "__main__":
    main()
