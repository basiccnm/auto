# -*- coding: utf-8 -*-
"""베이킹팜(bakingfarm.co.kr) 제빵 재료 가격 수집.

왜 필요한가: 우리 재료 중 **제빵 쪽이 통째로 비어 있다.** 그래서 모카빵 80.6%,
밤식빵 77.7% 같은 말이 안 되는 원가율이 나온다(2026-07-24 확인). 식자재몰(업소용)에는
강력분·버터·이스트·앙금이 거의 없어서 그쪽으로는 못 채운다.

수집 방식: **모바일 웹을 그대로 읽는다.** 앱도 에뮬레이터도 필요 없다.
  · 플랫폼 Makeshop — 목록 `/m/product_list.html?xcode=..&mcode=..`,
    상세 `/m/product.html?branduid=..`
  · 목록 HTML에 `<span class="price">10,800원</span>` 이 그대로 들어 있다(로그인 불필요)
  · ⚠️ **인코딩이 EUC-KR이다.** utf-8로 읽으면 한글이 전부 깨진다.

🔴 **요청 간격을 줄이지 말 것.** 0.4초 간격으로 200번쯤 돌렸다가 IP가 차단됐다(2026-07-24):
     "초단위로 페이지를 너무 많이 요청하였습니다 … 서버보호차원에서 차단"
   차단되면 응답이 448바이트짜리 안내문으로 바뀌므로 **본문에 '초단위'가 있으면 즉시 멈춘다.**
   푸는 데 10분쯤 걸린다. 3초 간격이면 문제없다.

값의 성격:
  · 일반 소포장 상품 = **소매**  (집에서 만들면 축)
  · 같은 몰의 **대용량** 카테고리 = 도매에 가까운 값 (매장 원가 축)
  둘을 계수로 환산하지 말고 각각 수집한다.
"""
import io, os, re, sys, json, time
import urllib.request, urllib.error
from http.cookiejar import CookieJar

BASE = "https://bakingfarm.co.kr"
UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
      "Chrome/126 Mobile Safari/537.36")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "research", "bakingfarm.json")

# 재료 대분류(xcode=004) 아래 하위분류를 훑는다. 없는 mcode는 빈 목록이 온다.
XCODE = "004"
MCODES = ["%03d" % i for i in range(1, 21)]


# 🔴 쿠키 세션이 없으면 목록 요청이 302로 튕긴다(2026-07-24). 홈을 먼저 한 번 열어
#    쿠키를 받고, 이후 요청에 Referer까지 붙여야 200이 온다.
_OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def warmup():
    _OP.open(urllib.request.Request(BASE + "/m/index.html",
                                    headers={"User-Agent": UA}), timeout=25).read()
    time.sleep(3.0)


def get(path, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers={
                "User-Agent": UA, "Referer": BASE + "/m/index.html"})
            raw = _OP.open(req, timeout=25).read()
            for enc in ("euc-kr", "cp949", "utf-8"):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode("euc-kr", "replace")
        except Exception as e:
            if i == tries - 1:
                print("  ! %s %s" % (path[:60], e))
                return ""
            time.sleep(4.0)


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


ITEM = re.compile(
    r'<a href="(/m/product\.html\?branduid=(\d+)[^"]*)"[^>]*>(.*?)</a>', re.S)
PRICE = re.compile(r'class="price"[^>]*>\s*([\d,]+)\s*원')


def parse_list(html):
    """목록 페이지에서 (상품코드, 이름, 가격)을 뽑는다.

    Makeshop 목록은 상품 블록마다 <a>(이름) 와 <span class="price"> 가 붙어 나온다.
    블록 경계를 정확히 잡기 어려워 **가격 span 위치를 기준으로 직전 상품 링크와 짝**짓는다.
    """
    out = []
    links = [(m.start(), m.group(2), strip_tags(m.group(3))) for m in ITEM.finditer(html)]
    for pm in PRICE.finditer(html):
        prev = [l for l in links if l[0] < pm.start()]
        if not prev:
            continue
        pos, uid, name = prev[-1]
        if not name or len(name) < 2:
            continue
        out.append({"uid": uid, "name": name, "price": int(pm.group(1).replace(",", ""))})
    # 같은 상품이 여러 번 잡히면 첫 것만
    seen, uniq = set(), []
    for it in out:
        if it["uid"] in seen:
            continue
        seen.add(it["uid"])
        uniq.append(it)
    return uniq


def main():
    warmup()
    all_items, cats = {}, []
    for mc in MCODES:
        page, got = 1, 0
        while page <= 10:
            path = ("/m/product_list.html?type=N&xcode=%s&mcode=%s&page=%d"
                    % (XCODE, mc, page))
            h = get(path)
            if not h:
                break
            if "초단위" in h:      # 차단 안내문 — 더 두드리면 오래 막힌다
                print("  ! IP 차단됨 — 중단합니다. 10분쯤 뒤 다시 실행하세요.")
                return -1
            items = parse_list(h)
            if not items:
                break
            new = 0
            for it in items:
                if it["uid"] not in all_items:
                    it["xcode"], it["mcode"] = XCODE, mc
                    all_items[it["uid"]] = it
                    new += 1
            got += new
            if new == 0:          # 같은 페이지가 반복되면 마지막
                break
            page += 1
            time.sleep(3.0)   # ⚠️ 아래 차단 경고 참조
        if got:
            cats.append((mc, got))
            print("  xcode=%s mcode=%s  %d건" % (XCODE, mc, got))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(list(all_items.values()), ensure_ascii=False, indent=1))
    print("\n총 %d건 · 저장 %s" % (len(all_items), os.path.relpath(OUT)))


main()
