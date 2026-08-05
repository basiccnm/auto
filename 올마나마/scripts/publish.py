# -*- coding: utf-8 -*-
"""**발행 한 줄** — 재생성 → 고아정리 → 사이트맵 → 배포 → 캐시퍼지 → 라이브확인. 2026-07-28 신설

    python scripts/publish.py --dry      # 무엇을 할지만 보여준다(기본, 안전)
    python scripts/publish.py --apply    # 실제로 배포까지
    python scripts/publish.py --apply --menu-only    # 메뉴/브랜드만 바뀌었을 때(재료·요리 생략)

왜 만들었나
----------
브랜드 하나 넣을 때마다 아래를 **손으로 이어 붙였다.** 2026-07-28 하루에만 10번 넘게 했고,
그때마다 하나씩 빠뜨릴 위험이 있었다(사이트맵을 안 만들거나, 퍼지를 빼먹거나).

⛔ **한 단계라도 실패하면 즉시 멈춘다.** 특히 생성이 실패한 채로 배포하면
   빈 `_dist` 가 올라가 사이트 전체가 404 가 된다(2026-07-26 실제 발생).
   `deploy.py` 가 파일 수를 세어 한 번 더 막지만, 여기서도 막는다.

⚠️ 캐시 퍼지는 **바뀐 경로만.** 전체 퍼지는 `error 1015` 를 부른다(2026-07-25 실제 발생).
⚠️ `deploy.py` 는 콘솔이 cp949 라 `PYTHONIOENCODING=utf-8` 없이 돌리면 죽는다 — 여기서 넣어준다.
"""
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "_dist")
SITE = "https://www.olmanama.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126 Safari/537.36"}

# 🔴 라이브 확인은 **브라우저 UA** 로 — `urllib` 기본 UA 는 403 이다(2026-07-28 확인)

# 순서가 곧 의존 관계다. 앞이 실패하면 뒤는 돌리지 않는다.
STEPS_FULL = [
    ("원가 재계산",   "python scripts/compute_line_costs.py"),
    ("요리 페이지",   "python scripts/gen_dishes.py"),
    ("브랜드·메뉴",   "python scripts/gen_preview_html.py"),
    ("재료 페이지",   "python scripts/gen_ingredient_pages.py"),
    ("재료 가격표",   "python scripts/gen_prices_page.py"),
]
STEPS_MENU = [
    ("브랜드·메뉴",   "python scripts/gen_preview_html.py"),
]


def sh(cmd, timeout=1800):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(cmd, cwd=BASE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", shell=True,
                          env=env, timeout=timeout)


def die(msg, r=None):
    print("\n❌ " + msg)
    if r is not None:
        print((r.stdout or "")[-900:])
        print((r.stderr or "")[-500:])
    sys.exit(1)


def step(name, cmd, dry):
    print("■ %s" % name, flush=True)
    if dry:
        print("   (dry) %s" % cmd)
        return None
    r = sh(cmd)
    tail = [x for x in (r.stdout or "").strip().splitlines() if x.strip()]
    if tail:
        print("   " + tail[-1][:120])
    if r.returncode != 0:
        die("%s 실패 — 여기서 멈춘다. 배포하지 않았다." % name, r)
    return r


def changed_paths():
    """이번에 바뀐 페이지만 퍼지한다 — 전체 퍼지는 error 1015 를 부른다.

    `_dist` 안에서 **최근 30분 내 수정된** 최상위 html 을 고른다. 방금 생성기가 만든 것들이다.
    """
    if not os.path.isdir(DST):
        return []
    now, out = time.time(), []
    for f in os.listdir(DST):
        if not f.endswith((".html", ".xml")):
            continue
        try:
            if now - os.path.getmtime(os.path.join(DST, f)) < 1800:
                out.append(f)
        except OSError:
            continue
    return sorted(out)


def main():
    dry = "--apply" not in sys.argv
    steps = STEPS_MENU if "--menu-only" in sys.argv else STEPS_FULL

    print("=" * 68)
    print("발행 %s" % ("(dry — 아무것도 안 한다)" if dry else "— 실제 배포까지 간다"))
    print("=" * 68)

    for name, cmd in steps:
        step(name, cmd, dry)

    # 고아 페이지 — DB 에 근거가 없는 파일을 지운다(브랜드를 지우거나 이름을 바꿨을 때 남는다)
    step("고아 페이지 정리", "python scripts/preview_orphans.py" + ("" if dry else " --apply"), dry)
    step("사이트맵", "python scripts/gen_sitemap.py", dry)

    # 🔴 **상표 검사 — 배포를 막는 관문** (2026-07-31 신설).
    #    쿠팡 파트너스 약관상 **제목·설명·도메인에 「쿠팡」·「로켓배송」을 쓸 수 없다.**
    #    README 에 적어두기만 했더니 `_calc.html` meta description 에 그대로 들어가
    #    라이브에 나가 있었다. 문서로 막지 말고 코드로 막는다.
    #    ✅ 본문 사실 서술·파트너스 고지문은 검사하지 않는다(머리말 4개 필드만 본다).
    print("\n■ 상표 검사 (제목·설명)")
    r = sh("python scripts/check_trademark.py")
    print((r.stdout or "").strip()[-700:])
    if r.returncode != 0:
        die("제목·설명에 상표가 들어 있다 — 배포하지 않았다. 위 목록을 고치고 다시 돌려라.", r)

    if dry:
        print("\n■ 배포 (dry)")
        print("   (dry) python scripts/deploy.py --build")
        print("   (dry) python scripts/cf_purge.py <바뀐 경로들>")
        print("\n실제로 하려면:  python scripts/publish.py --apply")
        return

    # 🔴 배포 — deploy.py 가 _dist 파일 수·워커명·도메인·라이브응답까지 스스로 검사한다.
    #    실패하면 exit(1) 이므로 여기서 그대로 멈춘다.
    print("■ 배포")
    r = sh("python scripts/deploy.py --build")
    print((r.stdout or "")[-700:])
    if r.returncode != 0:
        die("배포 실패", r)

    paths = changed_paths()
    print("■ 캐시 퍼지 — 바뀐 경로 %d개" % len(paths))
    if not paths:
        print("   바뀐 파일이 없다 — 퍼지 생략")
    else:
        # 🔴 한 줄에 다 넣으면 **Windows 명령줄 길이 제한(8,191자)** 을 넘겨 조용히 아무것도 안 한다
        #    (2026-07-28: 730개를 한 번에 넘겼더니 출력이 비었다). 150개씩 끊어 부른다.
        bad = 0
        for i in range(0, len(paths), 150):
            chunk = paths[i:i + 150]
            r = sh("python scripts/cf_purge.py " + " ".join('"%s"' % x for x in chunk))
            good = r.returncode == 0 and "✅" in (r.stdout or "")
            print("   %3d~%-3d  %s" % (i + 1, i + len(chunk), "✅" if good else "⚠️ 실패"))
            if not good:
                bad += 1
                print("      " + ((r.stdout or "") + (r.stderr or ""))[-200:])
        if bad:
            print("   ⚠️ %d묶음이 실패했다 — 엣지에 옛 페이지가 남을 수 있다" % bad)

    # 라이브 확인 — 출력만 믿지 않는다(2026-07-24 사고: Success 인데 라이브는 그대로였다)
    print("■ 라이브 확인")
    ok = True
    for p in ("/", "/prices", "/sitemap.xml"):
        try:
            res = urllib.request.urlopen(
                urllib.request.Request(SITE + p, headers=UA), timeout=25)
            n = len(res.read())
            print("   %-12s %s %d자" % (p, res.status, n))
            if res.status != 200 or n < 1000:
                ok = False
        except Exception as e:
            print("   %-12s ✗ %s" % (p, str(e)[:60]))
            ok = False
    print("\n%s" % ("✅ 발행 완료" if ok else "⚠️ 라이브 확인에서 이상이 있다 — 직접 볼 것"))


if __name__ == "__main__":
    main()
