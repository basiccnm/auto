# -*- coding: utf-8 -*-
"""배포 — 지금까지 낸 배포 사고를 전부 코드로 막는다 (2026-07-26 신설).

    python scripts/deploy.py            # 검사 → 배포 → 반영확인
    python scripts/deploy.py --build    # build_dist 부터 다시

막는 사고 (프로젝트 CLAUDE.md 사고 색인 참고):
 1. **빈 _dist 배포로 사이트 전체 404** (2026-07-26) — 다른 세션이 동시에 build_dist 를
    돌리면 rmtree 직후의 빈 폴더를 배포하게 된다. 그래서 파일 수를 세고 미달이면 멈춘다.
 2. **엉뚱한 워커로 배포하고 "성공" 보고** (2026-07-24) — 출력에서 워커명·도메인을 직접 확인한다.
 3. **배포 출력만 믿고 반영 확인 안 함** — 끝나고 실제 응답으로 확인한다.
"""
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "_dist")
CONFIG = os.path.join("workers", "site-renderer", "wrangler.toml")
WORKER = "eolmanama-site-renderer"
SITE = "https://www.olmanama.com"
# 🔴 이 검사가 막으려는 것은 **빈 `_dist` 배포로 사이트 전체가 404** 되는 것이다
#    (2026-07-26 실제 발생). 장수를 정확히 맞추는 검사가 아니다.
#    2026-07-27: 900/800 으로 잡아뒀다가 정상 배포를 막았다 — 숨긴 브랜드의 고아 페이지
#    203장을 지우니 651장이 됐는데 하한선이 800이었다. 브랜드를 숨기거나 켤 때마다
#    장수가 바뀌므로 **여유 있게** 잡는다. 빈 빌드는 0~50장이라 이 선에서 확실히 걸린다.
MIN_FILES = 400
MIN_HTML = 300


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=BASE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", shell=True, **kw)


def fail(msg):
    print("\n❌ " + msg)
    sys.exit(1)


if "--build" in sys.argv:
    print("■ build_dist 실행")
    r = run("python scripts/build_dist.py")
    print(r.stdout[-800:] or r.stderr[-800:])
    if r.returncode != 0:
        fail("build_dist 실패")

# ── 1. _dist 검사 ────────────────────────────────────────────────
print("■ _dist 검사")
if not os.path.isdir(DST):
    fail("_dist 폴더가 없다. python scripts/build_dist.py 먼저.")
files = sum(len(fs) for _, _, fs in os.walk(DST))
htmls = len([f for f in os.listdir(DST) if f.endswith(".html")])
print("   파일 %d건 · 최상위 HTML %d건" % (files, htmls))
if files < MIN_FILES or htmls < MIN_HTML:
    fail("_dist 가 비었거나 부족하다 (파일 %d/%d · HTML %d/%d).\n"
         "   다른 세션이 build_dist 를 동시에 돌리는 중일 수 있다. 빌드를 다시 하고 재시도할 것.\n"
         "   ⚠️ 이 상태로 배포하면 사이트 전체가 404 가 된다(2026-07-26 실제 발생)."
         % (files, MIN_FILES, htmls, MIN_HTML))
for must in ("index.html", "sitemap.xml", "robots.txt", "_headers"):
    if not os.path.exists(os.path.join(DST, must)):
        fail("_dist/%s 가 없다." % must)
print("   ✅ 통과")

# ── 2. 배포 ──────────────────────────────────────────────────────
print("■ wrangler deploy")
r = run('npx wrangler deploy --config "%s"' % CONFIG)
out = (r.stdout or "") + (r.stderr or "")
tail = [l for l in out.splitlines() if l.strip()][-12:]
print("\n".join("   " + l for l in tail))
if r.returncode != 0:
    fail("배포 실패")
if ("Uploaded " + WORKER) not in out:
    fail("**다른 워커로 나갔다.** 출력에 'Uploaded %s' 가 없다.\n"
         "   --config 를 빼면 루트 wrangler.jsonc(name=eolmanama)가 잡힌다." % WORKER)
if "olmanama.com" not in out:
    fail("커스텀 도메인이 출력에 없다. 라이브에 안 붙었을 수 있다.")
ver = re.search(r"Current Version ID:\s*(\S+)", out)
print("   ✅ %s · olmanama.com · 버전 %s" % (WORKER, ver.group(1) if ver else "?"))

# ── 3. 반영 확인 ─────────────────────────────────────────────────
#  ⚠️ 자산(이미지)에 ?cb= 쿼리를 붙이면 Workers 정적자산이 404를 준다. 캐시 우회는 헤더로만.
#  ⚠️ 레이트리밋이 촘촘해서 연속 요청은 429 가 난다 → 사이 간격을 둔다.
print("■ 라이브 확인")
UA = {"User-Agent": "olmanama-deploy-check", "Cache-Control": "no-cache"}
bad = []
for p in ("/", "/prices", "/sitemap.xml"):
    try:
        with urllib.request.urlopen(urllib.request.Request(SITE + p, headers=UA), timeout=25) as resp:
            n = len(resp.read())
            print("   %-14s %s %d자" % (p, resp.status, n))
            if n < 500:
                bad.append((p, "내용이 너무 짧다"))
    except urllib.error.HTTPError as e:
        # 429 는 레이트리밋이라 배포 실패가 아니다. 구분해서 알려준다.
        if e.code == 429:
            print("   %-14s ⚠️ 429 (레이트리밋 — 배포 문제 아님)" % p)
        else:
            bad.append((p, "HTTP %s" % e.code))
            print("   %-14s ❌ %s" % (p, e.code))
    except Exception as e:
        bad.append((p, str(e)[:40]))
        print("   %-14s ❌ %s" % (p, str(e)[:40]))
    import time
    time.sleep(3)          # 레이트리밋 회피

if bad:
    fail("라이브 확인 실패: %s" % bad)
print("   ✅ 라이브 정상")
print()
print("끝. 바뀐 페이지 캐시를 지우려면:  python scripts/cf_purge.py <경로들>")
