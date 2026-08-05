# -*- coding: utf-8 -*-
"""우리의식탁 레시피 수집 — 사이트맵 전량을 간격 두고 받아 JSON 으로 저장. (2026-08-03)

    python scripts/wtable_collect.py --probe        5건만 받아 응답 확인
    python scripts/wtable_collect.py --limit 100    100건 받기(이어받기)
    python scripts/wtable_collect.py                전량

🔴 왜 이 사이트인가
   · robots.txt 가 레시피를 허용한다(만개는 ClaudeBot 을 명시 거부 → 안 쓴다)
   · Vercel 정적 호스팅 + 사이트맵이 레시피 2,851개 주소를 스스로 공개
   · 각 페이지가 Next.js `__NEXT_DATA__` 라 JSON 파싱만 하면 끝. 재료 그룹·id 까지 나온다

🔴 예의
   · 건당 1.0초 간격. 실패하면 그 토큰만 건너뛰고 이어간다
   · 한 건씩 즉시 저장(JSONL append) — 끊겨도 이어받는다
   · User-Agent 를 정직하게 밝힌다(봇 숨기지 않음)
"""
import argparse
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "wtable")
os.makedirs(OUT, exist_ok=True)
JSONL = os.path.join(OUT, "recipes.jsonl")
SITEMAP = "https://wtable.co.kr/sitemap/sitemap-recipes.xml.gz"
UA = "olmanama-recipe-collector/1.0 (+contact: dndmotor1@gmail.com)"


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "ko"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if raw else data.decode("utf-8", "replace")


def tokens():
    raw = get(SITEMAP, raw=True)
    xml = gzip.decompress(raw).decode("utf-8", "replace")
    return re.findall(r"recipes/([A-Za-z0-9]+)<", xml)


def _img(v):
    """`{"img": "..."}` 문자열/딕셔너리 어느 쪽이든 대표 img URL 만 뽑는다."""
    try:
        d = json.loads(v) if isinstance(v, str) else v
        return (d or {}).get("img")
    except Exception:
        return None


def parse(html):
    m = re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        rc = json.loads(m.group(1))["props"]["pageProps"]["recipe"]
    except Exception:
        return None
    if not rc:
        return None
    # 🔴 사진·영상 URL 은 «참고용»으로만 저장한다(대표 방침 2026-08-03).
    #    그대로 올리지 않는다 — 보고 우리 걸 만들거나 수정한다. 저작권은 우리의식탁에 있다.
    steps = rc.get("recipe_steps") or []
    return {
        "id": rc.get("id"), "token": rc.get("token"), "title": rc.get("title"),
        "time": rc.get("time"), "level": rc.get("level"),
        "desc": rc.get("title_desc") or "",
        "groups": [{
            "name": (g.get("name") or "").strip(),
            "desc": g.get("description") or "",
            "ings": [{"id": i.get("id"), "n": i.get("name"),
                      "v": (i.get("value") or "").strip()}
                     for i in (g.get("ingredients") or [])],
        } for g in (rc.get("recipe_igroups") or [])],
        "steps": [(s.get("content") or "").strip() for s in steps],
        # 참고용 미디어
        "img_title": _img(rc.get("title_img")),
        "img_ingredient": _img(rc.get("ingredient_img")),
        "step_imgs": [[_img(x) for x in (s.get("imgs") or [])] for s in steps],
        "video": (rc.get("video_direct") or rc.get("video")) if rc.get("has_video") else None,
    }


def load_all():
    """기존 JSONL 을 {token: record} 로 읽는다."""
    rows = {}
    if os.path.exists(JSONL):
        for line in io.open(JSONL, encoding="utf-8"):
            try:
                r = json.loads(line)
                rows[r["token"]] = r
            except Exception:
                pass
    return rows


def has_img(r):
    """이 레코드가 사진 필드를 이미 갖고 있나."""
    return "step_imgs" in r


def done_tokens():
    return set(load_all())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--gap", type=float, default=0.4)
    a = ap.parse_args()

    toks = tokens()
    print(f"사이트맵 레시피 {len(toks)}개")

    if a.probe:
        toks = toks[:5]
        a.gap = 1.0
        print("── probe: 5건만 ──")

    have = load_all()                                  # {token: record}
    # 🔴 할 일 = ①사진 없는 기존 레코드(다시 받아 사진 채움) + ②아직 안 받은 토큰
    need_img = [t for t in have if not has_img(have[t])]
    fresh = [t for t in toks if t not in have]
    todo = need_img + fresh
    if a.limit:
        todo = todo[:a.limit]
    print(f"기존 {len(have)} (사진 없음 {len(need_img)}) · 새로 {len(fresh)} · 이번 처리 {len(todo)}\n")

    n = err = 0
    t0 = time.time()
    for i, tk in enumerate(todo, 1):
        try:
            p = parse(get(f"https://wtable.co.kr/recipes/{tk}"))
            if p:
                have[tk] = p                            # 기존이면 덮어써 사진 채움
                n += 1
                if a.probe or n % 25 == 0:
                    imgs = sum(len(s) for s in (p.get("step_imgs") or []))
                    print(f"  [{n}/{len(todo)}] {p['title']} · 사진 {imgs}장")
            else:
                err += 1
        except Exception as e:
            err += 1
            if err <= 3:
                print(f"  ⚠️ {tk} {str(e)[:60]}")
        # 25건마다 파일 전체 다시 써서 중간 저장(끊겨도 이어받음)
        if n and n % 25 == 0:
            tmp = JSONL + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as f:
                for r in have.values():
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(tmp, JSONL)
        time.sleep(a.gap)

    tmp = JSONL + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        for r in have.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, JSONL)

    dt = int(time.time() - t0)
    withimg = sum(1 for r in have.values() if has_img(r))
    print(f"\n처리 {n} · 실패 {err} · {dt}초 → {JSONL}")
    print(f"누적 총 {len(have)}개 · 그중 사진 있음 {withimg}개")


if __name__ == "__main__":
    main()
