# -*- coding: utf-8 -*-
"""쿠팡 파트너스 API — **부작용 없는 공용 핵심**. (공통모듈 원본 · 2026-07-31)

    from coupang_api import keys, search, ok, items, deeplink, parse_pack
    ak, sk = keys()
    body = search("동치미 냉면육수", ak, sk)
    if ok(body):
        for it in items(body):
            print(it["productName"], it["productPrice"])

⚠️ 이 파일은 **원본(금고)** 이다. 프로젝트에 붙일 때는 import 하지 말고 **복사**해서 쓴다
   (`공통모듈/CLAUDE.md` 규칙 1 — 폴더 간 직접 참조는 로컬서버 얽힘을 재발시킨다).

────────────────────────────────────────────────────────────
왜 이 파일이 따로 있나 (2026-07-31 실제 사고)
────────────────────────────────────────────────────────────
프로젝트의 `coupang_search.py` 는 파일 맨 끝에 **`sys.exit(main())`** 이 있었다.
그래서 다른 데서 `import coupang_search` 만 해도 그 자리에서 프로세스가 죽는다.
관리자 서버에서 「쿠팡 찾기」를 눌렀더니 **서버가 통째로 죽었다.**
→ 부르는 쪽이 늘어날수록 위험하니 **«불러 쓰는 부분»만** 여기로 갈랐다.
   이 파일에는 `main()` 도 `sys.exit` 도 두지 않는다. 그게 이 파일의 존재 이유다.

────────────────────────────────────────────────────────────
반드시 지킬 것
────────────────────────────────────────────────────────────
🔴 **분당 50회.** 여러 번 부를 때는 부르는 쪽이 `time.sleep(1.3)` 을 넣는다(분당 46회).
   2026-07-27 에 쿠팡 용량을 3초 간격으로 몰아 읽다 **11건에서 차단**당한 적이 있다.
🔴 이 API 는 **실패해도 HTTP 200** 을 준다 — `rCode` 를 반드시 본다. `ok()` 가 그걸 한다.
   200 이라고 믿으면 «0건 정상» 으로 착각한다.
🔴 `limit` **최대 10.** 20 을 주면 `rCode=400 «limit is out of range»` (2026-07-31 확인).
🔴 `signed-date` 는 **GMT** 여야 한다. 로컬시간을 쓰면 401.
🔴 링크를 싣는 페이지에는 **파트너스 고지문(`DISCLOSURE`)이 반드시 있어야** 한다.
⛔ 제목·설명·도메인에 **「쿠팡」·「로켓배송」을 쓰지 않는다**(상표 사용 제한).
   본문에서 사실 서술("조사한 상품은 모두 로켓배송입니다")은 괜찮다.
"""
import hashlib
import hmac
import io
import json
import os
import re
import ssl
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
LIMIT = 10          # 🔴 최대 10

ENV_KEYS = ("COUPANG_ACCESS_KEY", "COUPANG_SECRET_KEY")


# ── 인증 ────────────────────────────────────────────────────────────────────
def load_env(path=None):
    """`.env` 를 읽어 dict 로. 환경변수가 있으면 그쪽이 이긴다.

    🔴 **경로를 프로젝트에 박지 않는다**(이식형 모듈이라). 찾는 순서:
       ① 인자로 준 `path`
       ② 현재 작업폴더에서 위로 5단계까지 올라가며 `.env`
       ③ 이 파일이 있는 폴더와 그 부모
    """
    cands = []
    if path:
        cands.append(path)
    here = os.path.abspath(os.getcwd())
    for _ in range(5):
        cands.append(os.path.join(here, ".env"))
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    mod = os.path.dirname(os.path.abspath(__file__))
    cands += [os.path.join(mod, ".env"), os.path.join(os.path.dirname(mod), ".env")]

    env = {}
    for p in cands:
        if not p or not os.path.exists(p):
            continue
        for line in io.open(p, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
        break                      # 처음 찾은 `.env` 하나만 쓴다
    for k in ENV_KEYS:
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def keys(path=None):
    e = load_env(path)
    return e.get("COUPANG_ACCESS_KEY", ""), e.get("COUPANG_SECRET_KEY", "")


def sign(method, url_path, secret, access):
    """CEA HMAC-SHA256. `signed-date` 는 **GMT** 여야 한다 — 로컬시간 쓰면 401."""
    parts = url_path.split("?")
    path, query = parts[0], (parts[1] if len(parts) > 1 else "")
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    msg = dt + method + path + query
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return ("CEA algorithm=HmacSHA256, access-key=%s, signed-date=%s, signature=%s"
            % (access, dt, sig))


# ── 분당 호출 제한 (문서로 막지 말고 코드로 막는다) ─────────────────────────
# 🔴 **분당 50회.** 넘기면 차단당한다 — 2026-07-27 에 3초 간격으로 몰아 읽다
#    11건에서 실제로 막혔다. 부르는 쪽이 sleep 을 넣어주길 기대하지 않고 여기서 지킨다.
#    분당 46회(1.3초)로 잡아 여유를 둔다.
RATE_GAP = 1.3
_rate_lock = threading.Lock()
_last_call = [0.0]


def _throttle():
    with _rate_lock:
        wait = RATE_GAP - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


# ── 호출 ────────────────────────────────────────────────────────────────────
def search(keyword, ak, sk, limit=LIMIT):
    """상품 검색. **상위 10개**만 오고 호출마다 결과가 조금씩 바뀐다."""
    _throttle()
    url_path = "%s?keyword=%s&limit=%d" % (PATH, urllib.parse.quote(keyword), limit)
    req = urllib.request.Request(DOMAIN + url_path, method="GET")
    req.add_header("Authorization", sign("GET", url_path, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    with urllib.request.urlopen(req, timeout=25,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def deeplink(urls, ak, sk):
    """쿠팡 상품 주소 → **제휴가 붙은 주소**.

    🔴 왜 필요한가 — 검색 API 는 상위 10개만 주고 호출마다 결과가 바뀐다.
       웹에서 눈으로 찾은 더 싼 상품을 쓰려면 그 주소를 제휴 링크로 바꿔야 한다.
       **그냥 상품 주소를 걸면 수수료가 안 붙는다.**

    응답 `data:[{originalUrl, shortenUrl, landingUrl}]` — 짧은 건 `shortenUrl`.
    """
    _throttle()
    if isinstance(urls, str):
        urls = [urls]
    body = json.dumps({"coupangUrls": urls}).encode()
    req = urllib.request.Request(DOMAIN + DEEPLINK_PATH, data=body, method="POST")
    req.add_header("Authorization", sign("POST", DEEPLINK_PATH, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    with urllib.request.urlopen(req, timeout=25,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def ok(body):
    """`rCode` 0 이 아니면 실패다 — 200 이라고 믿으면 «0건 정상» 으로 착각한다."""
    return str((body or {}).get("rCode")) == "0"


def items(body):
    """응답에서 상품 목록. 키는 `data.productData` 다.

    ⚠️ 저장할 때는 이 원본 키를 그대로 쓰지 말고 프로젝트 정본 형식으로 눕히는 편이 낫다.
       올마나마는 «0건» 오독을 반복하다 정본을 못박았다:
       `{keyword, fetched_at, count, items:[{name, price, rocket, free, id, url, image}]}`
    """
    return ((body or {}).get("data") or {}).get("productData") or []


# ── 파트너스 필수 고지 ──────────────────────────────────────────────────────
# 🔴 링크를 싣는 페이지에 이 문구가 있어야 한다. API 응답 `rMessage` 로도 계속 내려온다.
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."


# ── 상품명 파싱 ─────────────────────────────────────────────────────────────
RX_PACK = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l|리터)(?![a-z가-힣])", re.I)
# 🔴 「개입」·「개들이」를 먼저 놓는다 (2026-07-31 공통모듈로 옮기며 발견한 버그).
#    전에는 `개|입|…` 뿐이라 **「500g 2개입」의 배수를 통째로 놓쳤다**(500g 로 읽혔다).
#    「2개」 까지 맞춘 뒤 뒤따르는 「입」이 `(?![가-힣])` 에 걸려 매칭이 통째로 취소된 것이다.
RX_CNT = re.compile(
    r"(?<![\d.])(\d{1,3})\s*(?:개입|개들이|개|입|팩|봉|포|구|알|장|병|캔)(?![가-힣])")


def parse_pack(title):
    """상품명에서 **총 용량**을 읽는다 → (양, 단위). 못 읽으면 (None, None).

    🔴 **배수를 반드시 곱한다.** 식봄에서 「5kg 2팩」 의 배수를 놓쳐 562건이 틀렸다(2026-07-25).
       쿠팡은 `냉면육수, 20개, 310ml` 처럼 **개수가 용량 앞에 오기도** 한다.

    ⛔ 개수가 여러 개 나오면(예: `(4인분)x3개, 1.816kg, 3개`) **추측하지 않고 None** 을 준다.
       틀린 용량은 「몇 인분 커버」 를 통째로 망가뜨린다 — **빈칸이 가짜보다 낫다.**
    """
    tt = title or ""
    # 🔴 **값이 아니라 «몇 번 나왔나»로 센다** (2026-07-31 공통모듈로 옮기며 고침).
    #    전에는 집합(set)으로 모아 값이 같으면 하나로 합쳐졌다. 그래서 문서가
    #    «None 이어야 한다» 고 적어둔 `(4인분)x3개, 1.816kg, 3개` 가 5,448g 으로 나왔다.
    #    개수 표기가 **두 군데 이상** 나오면 무엇을 곱해야 하는지 알 수 없다 → 비운다.
    hits = [int(x) for x in RX_CNT.findall(tt) if 1 < int(x) <= 200]
    m = RX_PACK.search(tt)
    if not m:
        # 무게·부피가 없고 **개수만** 있는 것 — 계란 10구, 오이 3입.
        # 이런 재료는 필요량도 「개」 로 적으므로 그대로 쓰면 된다.
        if len(hits) == 1:
            return float(hits[0]), "개"
        return None, None
    v, u = float(m.group(1)), m.group(2).lower()
    if u == "kg":
        v, u = v * 1000, "g"
    elif u in ("l", "리터"):
        v, u = v * 1000, "ml"
    if len(hits) > 1:
        return None, None            # 개수 표기가 여럿이다 — 사람이 봐야 한다
    if hits:
        v *= hits[0]
    return round(v, 1), u


def product_id_of(url):
    """주소에서 상품번호 — `/vp/products/2233944921?...` → `2233944921`"""
    m = re.search(r"/products/(\d+)", url or "")
    return m.group(1) if m else None


def item_id_of(url):
    """옵션 식별자. 같은 상품(productId)이라도 **옵션마다 itemId 가 다르다.**"""
    m = re.search(r"itemId=(\d+)", url or "")
    return m.group(1) if m else None


def group_options(rows):
    """같은 productId 를 **옵션 묶음**으로 표시한다(각 행에 `opt_n` 을 넣어 돌려준다).

    🔴 왜 — 「면사랑 함흥면사리(2kg)」 가 1,250원·5,200원 **두 줄**로 왔다. productId 가 같다.
       상품명은 옵션 하나의 이름일 뿐이라 **1,250원이 2kg 값이라는 근거가 없다.**
       (같은 목록의 「10인분 9,900원」 = 1인분 990원과 견주면 1인분 104원은 말이 안 된다)

    ⛔ 그렇다고 버리지 않는다 — 옵션이 곧 «작은 용량» 인 경우가 많다.
       옵션을 전부 살려두고 **몇 개짜리인지 사람이 보고 고르게** 한다.
    """
    seen = {}
    for x in rows:
        seen.setdefault(str(x.get("product_id") or x.get("productId") or ""), []).append(x)
    for x in rows:
        pid = str(x.get("product_id") or x.get("productId") or "")
        x["opt_n"] = len(seen.get(pid, []))
    return rows


# 로켓프레시는 별도 칸이 없다 — **상품명에 붙어서** 온다(2026-07-31 확인).
#    예: `[로켓프레시] 면사랑 함흥면사리 10인분 (냉동)`
RX_FRESH = re.compile(r"로켓프레시|로켓\s*프레시", re.I)


def is_fresh(title):
    return bool(RX_FRESH.search(title or ""))
