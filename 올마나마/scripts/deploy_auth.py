# -*- coding: utf-8 -*-
"""인증 워커 배포 — 라이브 사이트를 죽일 수 있는 경로를 코드로 막는다 (2026-07-27 신설).

    python scripts/deploy_auth.py            # 검사 → 배포 → 반영확인
    python scripts/deploy_auth.py --check    # 배포 없이 검사만

scripts/deploy.py(정적 사이트용)와 **완전히 별개**다. 서로를 부르지 않는다.
워커가 둘이므로 배포 스크립트도 둘이어야 "무엇을 배포했는지"가 헷갈리지 않는다.

막는 사고:
 1. 🔴 **routes 패턴 오타** — `olmanama.com/*` 로 쓰면 이 워커가 943페이지를 전부 삼켜
    사이트가 전멸한다. 이 프로젝트에서 가장 위험한 실수라 배포 전에 파싱해서 거부한다.
 2. **--config 누락으로 엉뚱한 워커에 배포** (2026-07-24) — 명령에 하드코딩하고,
    출력에 'Uploaded olmanama-auth' 가 없으면 실패로 본다.
 3. **.env 의 CF 토큰을 wrangler 가 집어가 배포 실패** (2026-07-25) — 미리 검사해서 멈춘다.
 4. **출력만 믿고 반영 미확인** — 배포 후 /api/health 와 **정적 페이지 둘 다** 확인한다.
    인증 워커를 올렸는데 정적 페이지가 죽었는지를 반드시 같이 본다.
"""
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

# 콘솔이 cp949 면 ✅·❌ 에서 UnicodeEncodeError 로 죽는다(터미널에 따라 갈린다).
# 배포 스크립트가 인코딩 때문에 멈추는 건 말이 안 되므로 출력만 UTF-8 로 고정한다.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_REL = os.path.join("workers", "auth", "wrangler.toml")
CONFIG = os.path.join(BASE, CONFIG_REL)
WORKER = "olmanama-auth"
SITE = "https://www.olmanama.com"
APEX = "https://olmanama.com"

# 이 워커가 가져가도 되는 경로. 여기 없는 패턴이 wrangler.toml 에 있으면 배포를 거부한다.
ALLOWED_PREFIX = ("/api/", "/auth/")

# 배포 후 "정적 사이트가 여전히 살아 있는가"를 확인할 페이지들
LIVE_PAGES = ("/", "/prices")


def run(cmd):
    return subprocess.run(cmd, cwd=BASE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", shell=True)


def fail(msg):
    print("\n❌ " + msg)
    sys.exit(1)


# ── 1. .env 오염 검사 (2026-07-25 사고) ───────────────────────────
#  .env 에 CF_API_TOKEN / CLOUDFLARE_API_TOKEN 이 있으면 wrangler 가 그걸 자기 인증으로
#  집어가서, 권한 없는 토큰이면 "계정 ID 를 못 가져온다"는 엉뚱한 에러로 죽는다.
print("■ .env 검사")
ENV_PATH = os.path.join(BASE, ".env")
BAD_ENV = ("CF_API_TOKEN", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8", errors="replace") as f:
        names = {ln.split("=", 1)[0].strip() for ln in f if "=" in ln and not ln.strip().startswith("#")}
    hit = sorted(names & set(BAD_ENV))
    if hit:
        fail(".env 에 %s 가 있다. wrangler 가 이걸 자기 인증 토큰으로 집어가 배포가 깨진다"
             "(2026-07-25 실제 발생).\n"
             "   이름을 OLMANAMA_ 접두어로 바꾸고, 워커 시크릿은 .env 가 아니라\n"
             "   `wrangler secret put --config %s` 또는 workers/auth/.dev.vars 를 쓸 것."
             % (", ".join(hit), CONFIG_REL))
print("   ✅ 통과")

# ── 2. 🔴 라우트 패턴 검사 — 가장 중요 ────────────────────────────
print("■ 라우트 패턴 검사")
if not os.path.exists(CONFIG):
    fail("%s 가 없다." % CONFIG_REL)
with open(CONFIG, "r", encoding="utf-8") as f:
    toml_src = f.read()

# 주석을 걷어내고 pattern = "..." 만 뽑는다 (주석 속 예시 패턴에 속지 않기 위해)
no_comment = "\n".join(ln.split("#", 1)[0] for ln in toml_src.splitlines())
patterns = re.findall(r'pattern\s*=\s*"([^"]+)"', no_comment)
if not patterns:
    fail("routes 에 pattern 이 하나도 없다. 라우트 없이 배포하면 아무도 이 워커를 못 부른다.")

print("   " + " · ".join(patterns))
for p in patterns:
    # 호스트 뒤의 경로 부분만 본다
    path = "/" + p.split("/", 1)[1] if "/" in p else "/"
    if not path.startswith(ALLOWED_PREFIX):
        fail("**위험한 라우트 패턴: %s**\n"
             "   경로가 %s 로 시작하지 않는다. 이대로 배포하면 이 워커가\n"
             "   정적 페이지 943개를 전부 삼켜서 **사이트가 전멸한다.**\n"
             "   %s 를 고칠 것." % (p, " 또는 ".join(ALLOWED_PREFIX), CONFIG_REL))
if 'name = "%s"' % WORKER not in no_comment:
    fail('%s 의 name 이 "%s" 가 아니다.' % (CONFIG_REL, WORKER))
print("   ✅ 통과 — 정적 페이지를 삼키지 않는다")

if "--check" in sys.argv:
    print("\n검사만 하고 끝냈다(--check).")
    sys.exit(0)

# ── 3. 배포 ──────────────────────────────────────────────────────
if "--verify" in sys.argv:
    print("■ 배포 건너뜀(--verify) — 라이브 확인만 한다")
else:
    print("■ wrangler deploy")
    r = run('npx wrangler deploy --config "%s"' % CONFIG_REL)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if l.strip()][-15:]
    print("\n".join("   " + l for l in tail))
    if r.returncode != 0:
        fail("배포 실패")
    if ("Uploaded " + WORKER) not in out:
        fail("**다른 워커로 나갔다.** 출력에 'Uploaded %s' 가 없다.\n"
             "   --config 를 확인할 것 — 2026-07-24 에 같은 방식으로 엉뚱한 워커에 배포하고\n"
             "   '성공'이라고 보고한 사고가 있다." % WORKER)
    if "eolmanama-site-renderer" in out:
        fail("출력에 site-renderer 가 보인다. **정적 사이트 워커를 덮어썼을 수 있다.** 즉시 확인할 것.")
    ver = re.search(r"Current Version ID:\s*(\S+)", out)
    print("   ✅ %s · 버전 %s" % (WORKER, ver.group(1) if ver else "?"))

# ── 4. 반영 확인 ─────────────────────────────────────────────────
#  ⚠️ 레이트리밋이 촘촘해서 연속 요청은 429 가 난다 → 사이에 간격을 둔다(deploy.py 와 동일).
print("■ 라이브 확인")
UA = {"User-Agent": "olmanama-deploy-auth-check", "Cache-Control": "no-cache"}
bad = []


def get(u, want_json=False):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, resp.read().decode("utf-8", "replace"), resp.headers


# 4-1. 인증 워커가 응답하는가
#  ⚠️ **라우트 전파에 시간이 걸린다.** 배포 직후 몇 초 동안은 요청이 여전히 Custom Domain
#     워커(site-renderer)로 가서 빈 404 가 온다. 2026-07-27 첫 배포 때 이걸 장애로 오판했다.
#     그래서 실패로 단정하기 전에 최대 ROUTE_WAIT 초까지 기다린다.
ROUTE_WAIT = 90


def health_ok(base):
    """(성공여부, 마지막메시지) — 전파를 기다리며 재시도한다."""
    u = base + "/api/health"
    deadline = time.time() + ROUTE_WAIT
    last = "?"
    tries = 0
    while time.time() < deadline:
        tries += 1
        try:
            st, body, _ = get(u)
            if '"ok":true' in body.replace(" ", ""):
                return True, "%s (%d번째 시도)" % (st, tries)
            last = body[:120]
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:120] if e.fp else ""
            if e.code == 429:
                last = "429 레이트리밋"
            elif e.code == 404 and not detail:
                # 빈 404 = 아직 site-renderer 가 받고 있다 = 전파 대기 중
                last = "404 (라우트 전파 대기 중)"
            else:
                last = "HTTP %s %s" % (e.code, detail)
        except Exception as e:
            last = str(e)[:60]
        time.sleep(6)
    return False, last


for base in (APEX, SITE):
    ok, msg = health_ok(base)
    print("   %-38s %s %s" % (base + "/api/health", "✅" if ok else "❌", msg))
    if not ok:
        bad.append((base + "/api/health", msg))
    time.sleep(2)

# 4-2. 🔴 정적 사이트가 여전히 살아 있는가 — 이게 이 스크립트의 진짜 목적이다
for p in LIVE_PAGES:
    u = SITE + p
    try:
        st, body, hdrs = get(u)
        ctype = hdrs.get("Content-Type", "")
        ok = st == 200 and "text/html" in ctype and len(body) > 5000
        print("   %-38s %s %s %d자 %s" % (u, st, ctype.split(";")[0], len(body), "✅" if ok else "❌"))
        if not ok:
            bad.append((u, "정적 페이지가 정상 HTML 이 아니다 (%s, %d자)" % (ctype, len(body))))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("   %-38s ⚠️ 429 (레이트리밋 — 판정 보류)" % u)
        else:
            print("   %-38s ❌ %s" % (u, e.code))
            bad.append((u, "HTTP %s — 인증 워커가 정적 페이지를 삼켰을 수 있다" % e.code))
    except Exception as e:
        print("   %-38s ❌ %s" % (u, str(e)[:60]))
        bad.append((u, str(e)[:60]))
    time.sleep(3)

if bad:
    fail("확인 실패:\n" + "\n".join("   · %s → %s" % b for b in bad) +
         "\n\n   정적 페이지가 죽었다면 라우트 패턴이 원인이다. 되돌리려면:\n"
         "     npx wrangler delete --config %s" % CONFIG_REL)

print("   ✅ 인증 워커 정상 · 정적 사이트 정상")
print()
print("끝. 시크릿을 넣으려면:  npx wrangler secret put <이름> --config %s" % CONFIG_REL)
