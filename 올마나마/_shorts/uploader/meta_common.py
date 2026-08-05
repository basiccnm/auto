# -*- coding: utf-8 -*-
"""인스타·스레드 API 공통 (2026-07-24)

🔴 두 API는 형제처럼 생겼지만 주소·파라미터가 다르다. 헷갈리면 401이 난다.

              인스타                        스레드
  주소        graph.instagram.com          graph.threads.net
  버전        v23.0                        v1.0
  갱신 파라미터 ig_refresh_token             th_refresh_token
  계정        olma_nama                    dnd_mbol

🔴 토큰은 60일짜리다. refresh_token.py 를 월 1회 돌려 갱신한다.
   완전히 만료되면 갱신도 안 되고 앱 대시보드에서 새로 발급받아야 한다.
"""
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")

IG_BASE = "https://graph.instagram.com"
IG_VER = "v23.0"
TH_BASE = "https://graph.threads.net"
TH_VER = "v1.0"


def load_env():
    """.env 를 dict 로. python-dotenv 안 쓴다 — 의존성 하나라도 줄인다."""
    env = {}
    if not os.path.exists(ENV_PATH):
        raise SystemExit(".env 가 없다: {}".format(ENV_PATH))
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(updates):
    """키 값만 갈아끼운다. 주석·순서는 그대로 둔다(사람이 읽는 파일이다)."""
    with open(ENV_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    done = set()
    out = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in updates:
                out.append("{}={}\n".format(k, updates[k]))
                done.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in done:
            out.append("{}={}\n".format(k, v))
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(out)


def api(url, params=None, post=False, timeout=60):
    """GET/POST 한 방. 에러면 본문을 그대로 보여준다 — 메타 에러 메시지가 꽤 친절하다."""
    params = params or {}
    if post:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data)
    else:
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit("[API 오류 {}] {}\n  요청: {}".format(e.code, body, url))


def log(msg, tag=""):
    print(("[{}] ".format(tag) if tag else "") + msg)
