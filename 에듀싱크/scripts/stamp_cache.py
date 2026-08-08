#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
`app/www/index.html` 의 캐시 끊기 표시(?v=…)를 **실제 파일 내용**으로 다시 찍는다.

  python scripts/stamp_cache.py          # 찍는다
  python scripts/stamp_cache.py --check  # 다른지 보기만 한다(다르면 종료코드 1)

⚠ **빌드 전에 반드시 돌린다.** 안 돌리면 이런 일이 난다(2026-08-08 실제로 겪음):
   app.js·style.css 를 고치고 APK 를 덮어 설치했는데 **웹뷰가 옛 파일을 계속 썼다.**
   깨끗한 설치에서는 캐시가 비어 있어 새 파일이 뜨므로 «될 때도 있고 안 될 때도 있는»
   제일 나쁜 종류의 버그가 된다.

⚠ 값은 **파일 내용의 해시**여야 한다. 날짜·일련번호로 하면 안 바뀐 파일까지 매번 다시 받는다.
"""
import hashlib, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(HERE, "..", "app", "www")
HTML = os.path.join(WWW, "index.html")

# (index.html 안의 참조, 실제 파일)
TARGETS = [
    ("style.css", "style.css"),
    ("app.js", "app.js"),
    ("fonts/tabler-subset.css", os.path.join("fonts", "tabler-subset.css")),
]


def h(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def main():
    check = "--check" in sys.argv
    html = io.open(HTML, encoding="utf-8").read()
    out, changed = html, []

    for ref, rel in TARGETS:
        p = os.path.join(WWW, rel)
        if not os.path.exists(p):
            print("  ! 없는 파일: %s" % rel)
            continue
        want = h(p)
        # "style.css?v=xxxxxxxx" 같은 자리를 찾는다 (따옴표 안이든 밖이든)
        pat = re.compile(re.escape(ref) + r"\?v=([0-9a-f]{6,10})")
        found = pat.findall(out)
        if not found:
            print("  ! index.html 에 %s?v=… 자리가 없다" % ref)
            continue
        if found[0] != want:
            changed.append("%s  %s → %s" % (ref, found[0], want))
        out = pat.sub(ref + "?v=" + want, out)

    if not changed:
        print("캐시 표시가 파일과 같다 — 고칠 것 없음")
        return 0

    for c in changed:
        print("  " + c)
    if check:
        print("\n⚠ 빌드 전에 `python scripts/stamp_cache.py` 를 돌려야 한다")
        return 1

    tmp = HTML + ".tmp"
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(out)
    os.replace(tmp, HTML)
    print("\nindex.html 갱신 완료 (%d곳)" % len(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
