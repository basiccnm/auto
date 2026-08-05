# -*- coding: utf-8 -*-
# 네이버 개발자센터 API 공통 설정 — 키는 코드에 절대 박지 않는다.
#
# 🔴 키 조달 순서: ① 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET
#                  ② 같은 폴더/상위의 .env
#                  ③ naver_config.json (방구석약국이 쓰던 기존 형식 — 이관 편의용)
#    .env / naver_config.json 은 .gitignore에 넣는다.
#
# ⚠️ 애플리케이션은 프로젝트마다 따로 만들 것.
#    - 일일 호출 한도가 앱 단위라, 한 키를 여러 프로젝트가 나눠 쓰면 한쪽이 조용히 죽는다.
#    - 같은 앱에 '네이버 로그인'을 추가하면 검색 API가 막히는 사례가 있었다([[bangpharmacy-project]]).
#      로그인이 필요하면 반드시 별도 앱으로 만들 것.
import json
import os

_ENV_CACHE = None


def _load_dotenv():
    """가장 가까운 .env를 한 번만 읽어 dict로. python-dotenv 의존 없이 최소 파싱."""
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    _ENV_CACHE = {}
    here = os.path.dirname(os.path.abspath(__file__))
    # 이 폴더 → 상위 2단계까지 .env 탐색(프로젝트로 복사해 써도 찾히게)
    for d in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        p = os.path.join(d, ".env")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                _ENV_CACHE.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break
    return _ENV_CACHE


def _load_legacy_json():
    """naver_config.json({client_id, client_secret}) — 기존 프로젝트에서 그대로 옮겨올 때."""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.getcwd(), here, os.path.dirname(here)):
        p = os.path.join(d, "naver_config.json")
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except (ValueError, OSError):
                pass
    return {}


def get(name, default=None):
    return os.environ.get(name) or _load_dotenv().get(name) or default


def credentials():
    """(client_id, client_secret) 반환. 없으면 안내와 함께 예외."""
    cid = get("NAVER_CLIENT_ID")
    sec = get("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        legacy = _load_legacy_json()
        cid = cid or legacy.get("client_id")
        sec = sec or legacy.get("client_secret")
    if not (cid and sec):
        raise RuntimeError(
            "네이버 API 키가 없습니다.\n"
            '  방법 1) PowerShell:  setx NAVER_CLIENT_ID "..."  /  setx NAVER_CLIENT_SECRET "..."\n'
            "  방법 2) 이 폴더(또는 상위)에 .env 생성 후:\n"
            "            NAVER_CLIENT_ID=...\n"
            "            NAVER_CLIENT_SECRET=...\n"
            "  방법 3) 실행 폴더에 naver_config.json  {\"client_id\": \"...\", \"client_secret\": \"...\"}\n"
            "  ※ 키는 https://developers.naver.com 에서 앱을 만들어 발급. 프로젝트마다 별도 앱 권장")
    return cid, sec


HTTP_TIMEOUT = int(get("NAVER_HTTP_TIMEOUT", "15"))
# 연속 호출 간격(초). 재료 수십 종을 한 번에 돌릴 때 API에 대한 예의이자 차단 방지.
CALL_INTERVAL = float(get("NAVER_CALL_INTERVAL", "0.5"))
USER_AGENT = get("NAVER_USER_AGENT", "Mozilla/5.0 (compatible; basiccnm-bot/1.0)")
