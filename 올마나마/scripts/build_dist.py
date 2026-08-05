# -*- coding: utf-8 -*-
# 배포용 폴더 빌드: _preview → _dist (2026-07-17)
#
# 왜 _preview를 그대로 안 올리나:
#   _preview에는 **검수용 페이지**가 섞여 있다(_logo_audit·_menu_audit·_sauce_review·_price_audit·_sell_audit).
#   내부 확인용이라 공개되면 안 되고, robots.txt로 막는 것보다 **아예 안 올리는 게** 확실하다.
#
# 사용법: python scripts/build_dist.py   (생성기들 + gen_sitemap 다음에 마지막)
import os, shutil, glob, re

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
SRC = os.path.join(BASE, "_preview")
DST = os.path.join(BASE, "_dist")

def _force(fn, path, exc):
    # Windows에서 읽기전용/잠김 파일 삭제 실패 대응
    import stat
    import time
    os.chmod(path, stat.S_IWRITE)
    # 🔴 백신·검색인덱서가 방금 쓴 파일을 훑는 동안 WinError 32(사용 중)가 난다(2026-07-27).
    #    매번 **다른 파일**에서 걸리는 게 특징 — 진짜 점유가 아니라 스캔이라 곧 풀린다.
    #    그래서 한 번 실패했다고 멈추지 말고 잠깐 기다렸다 다시 시도한다.
    # 🔴 `PermissionError` 만 잡으면 부족하다(2026-07-28). 잠긴 파일 때문에 폴더가 안 비면
    #    마지막 `os.rmdir` 에서 **OSError WinError 145(디렉터리가 비어 있지 않음)** 가 난다.
    #    같은 원인(백신 스캔)이라 잠깐 기다리면 풀린다 → OSError 전체를 재시도한다.
    for wait in (0.3, 0.7, 1.5, 3.0, 5.0):
        try:
            return fn(path)
        except OSError:
            time.sleep(wait)
    fn(path)  # 그래도 안 되면 원래 예외를 그대로 올린다

if os.path.isdir(DST):
    # ⚠️ 프리뷰 서버(python -m http.server)가 _dist를 잡고 있으면 rmtree가 WinError 5로 실패한다.
    #    서버는 _preview를 서빙하므로 보통은 안 겹치지만, 겹치면 명확히 알려준다.
    # 🔴 절반쯤 지워진 채로 실패하면 _dist 가 깨진다(2026-07-27 실제 발생 — index.html 이 사라졌다).
    #    deploy.py 의 파일 수·index.html 검사가 그 상태의 배포를 막아준다. 검사를 없애지 말 것.
    try:
        shutil.rmtree(DST, onerror=_force)
    except PermissionError as e:
        raise SystemExit(f"❌ _dist 삭제 실패(파일이 잠겨 있음): {e}\n"
                         f"   _dist를 열어둔 프로그램(탐색기·에디터·http.server)을 닫고 다시 실행하세요.")
os.makedirs(DST)

copied = skipped = 0
for f in glob.glob(os.path.join(SRC, "*")):
    name = os.path.basename(f)
    if name.startswith("_"):          # 검수용 = 발행 대상 아님
        skipped += 1
        continue
    if os.path.isdir(f):
        shutil.copytree(f, os.path.join(DST, name))
    else:
        shutil.copy2(f, os.path.join(DST, name))
    copied += 1

# 검증: 발행물에 검수용 페이지로 가는 링크가 남아 있으면 404가 된다
#  정식 URL은 확장자 없는 주소(2026-07-19) — href="menu_6" → menu_6.html 존재 확인.
broken = []
files = set(os.listdir(DST))
for f in glob.glob(os.path.join(DST, "*.html")):
    s = open(f, encoding="utf-8").read()
    for href in re.findall(r'href="([A-Za-z0-9_\-]+)(?:#[^"]*)?"', s):
        if href + ".html" not in files:
            broken.append((os.path.basename(f), href))
    # 옛 형식(.html 링크)이 다시 새어들면 307 리다이렉트 재발 — 정책 위반으로 잡는다
    for href in re.findall(r'href="([^"#?:]+\.html)"', s):
        if "'" in href or "+" in href: continue
        broken.append((os.path.basename(f), href + " ← .html 링크 잔존(확장자 없는 주소로)"))

# ── _headers — 자산 캐시 수명 (2026-07-25 사고 대응) ──────────────
#  🔴 Workers 정적자산의 기본값이 `Cache-Control: public, max-age=0, must-revalidate` 다.
#     그래서 일러스트·로고까지 **매번 워커로 되돌아왔고**, 페이지 한 장이 이미지를
#     동시에 여러 개 받는 순간 레이트리밋에 걸려 사이트가 `error 1015` 를 뱉었다.
#     (실측: 동시 20요청 중 4건이 429)
#  이미지는 파일명이 고정이고 내용이 거의 안 바뀌니 길게 잡는다. 바뀌면 그 경로만 퍼지한다:
#     python scripts/cf_purge.py illust/s16_01.png
#  HTML 은 매일 시세가 바뀌므로 짧게. 그래도 0초는 아니어야 원본 부하가 준다.
#  🔴 규칙이 겹치면 안 된다 — `_headers` 는 같은 헤더를 **덮어쓰지 않고 이어붙인다.**
#     `/*` 와 `/illust/*` 를 같이 뒀더니 실제 응답이 이렇게 나갔다:
#       Cache-Control: public, max-age=600, …, public, max-age=604800, …, public, max-age=604800, …
#     값이 3개 붙은 잘못된 헤더라 앞의 600초가 먹혔다. 그래서 **경로별로 딱 하나만 매칭**시킨다.
#  · HTML(확장자 없는 주소)에는 규칙을 걸지 않는다 — Workers 기본값(max-age=0)을 그대로 둔다.
#    페이지 HTML 은 매일 시세가 바뀌고, 페이지당 1요청뿐이라 부하의 원인이 아니다.
#    부하는 **이미지**다(한 페이지가 일러스트·로고를 동시에 여러 개 받는다).
HEADERS = """# 자동 생성 — scripts/build_dist.py 가 만든다. 손으로 고치지 말 것.
# 왜 필요한지는 그 스크립트의 주석 참고 (error 1015 사고, 2026-07-25).
# ⚠️ 규칙을 겹치게 만들지 말 것 — 같은 헤더가 이어붙어 잘못된 값이 나간다.

/illust/*
  Cache-Control: public, max-age=604800, stale-while-revalidate=86400

/logos/*
  Cache-Control: public, max-age=604800, stale-while-revalidate=86400

/og/*
  Cache-Control: public, max-age=604800, stale-while-revalidate=86400

/cards/*
  Cache-Control: public, max-age=604800, stale-while-revalidate=86400

/reels/*
  Cache-Control: public, max-age=604800, stale-while-revalidate=86400

/favicon.ico
  Cache-Control: public, max-age=2592000

/favicon-16.png
  Cache-Control: public, max-age=2592000

/favicon-32.png
  Cache-Control: public, max-age=2592000

/apple-touch-icon.png
  Cache-Control: public, max-age=2592000
"""
with open(os.path.join(DST, "_headers"), "w", encoding="utf-8", newline="\n") as _f:
    _f.write(HEADERS)

html = len([f for f in os.listdir(DST) if f.endswith(".html")])
logos = len(glob.glob(os.path.join(DST, "logos", "*")))
size = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(DST) for x in fs)
print(f"_dist 빌드: HTML {html}개 · 로고 {logos}개 · {size/1e6:.1f}MB")
print(f"  복사 {copied} · 검수용 제외 {skipped}")
for extra in ("sitemap.xml", "robots.txt", "_headers"):
    print(f"  {extra}: {'✅' if os.path.exists(os.path.join(DST, extra)) else '❌ 없음'}")
if broken:
    print(f"\n❌ 발행물이 없는 파일을 링크한다: {len(broken)}건")
    for b in broken[:5]:
        print(f"   {b[0]} → {b[1]}")
else:
    print("  ✅ 깨진 링크 없음")
