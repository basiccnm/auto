# -*- coding: utf-8 -*-
"""구글 인증 한 번에 — GA4(방문자) + 애드센스(수익). 2026-07-27

    python scripts/auth_google.py

🔴 유튜브 토큰(_shorts/uploader/yt_token.json)과 **따로 관리한다.**
   유튜브 쪽에 스코프를 더 붙이면 재인증이 필요해지고, 업로드가 막히면 그날 작업이 통째로 멈춘다.
   그래서 사이트 분석용 토큰은 scripts/google_token.json 으로 분리했다.

🔴 미리 켜야 하는 것 (구글 클라우드 콘솔, 프로젝트 cnm1-502614)
     · Google Analytics Data API
     · Google Analytics Admin API   ← 속성 ID 를 자동으로 찾는 데 쓴다
     · AdSense Management API
   안 켜면 인증은 되는데 조회에서 403 이 난다.

🔴 OAuth 동의 화면의 '테스트 사용자'에 본인 계정이 들어 있어야 한다(미게시 앱이라).
"""
import io
import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(BASE, "_shorts", "uploader", "client_secret.json")
TOKEN = os.path.join(BASE, "scripts", "google_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/adsense.readonly",
    # 🔴 2026-07-28 추가 — 서치 콘솔. 색인 상태·검색어·평균 순위를 본다.
    #    구글 클라우드에서 **Google Search Console API** 도 같이 켜야 한다.
    # 🔴 readonly 로는 사이트맵 **제출**이 안 된다(403 insufficient scopes, 2026-07-28).
    #    색인 상태만 볼 거면 readonly 면 되지만, 재제출까지 하려면 webmasters 가 필요하다.
    "https://www.googleapis.com/auth/webmasters",
]
sys.stdout.reconfigure(encoding="utf-8")


def creds():
    """저장된 토큰을 주고, 없거나 만료면 새로 받는다. 다른 스크립트도 이걸 쓴다."""
    c = None
    # 스코프를 추가하면 옛 토큰은 못 쓴다 — 지우고 새로 받게 한다
    if os.path.exists(TOKEN):
        c = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if c and c.expired and c.refresh_token:
        c.refresh(Request())
    if not c or not c.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
        # 🔴 로컬 서버 방식이 편하지만, 브라우저가 다른 계정으로 로그인돼 있으면
        #    엉뚱한 계정에 붙는다(2026-07-25 유튜브에서 실제로 당함).
        #    그래서 계정 선택 화면을 강제로 띄운다.
        c = flow.run_local_server(port=0, prompt="consent", authorization_prompt_message="")
        io.open(TOKEN, "w", encoding="utf-8").write(c.to_json())
    return c


if __name__ == "__main__":
    c = creds()
    print("✅ 인증 완료 →", TOKEN)
    from googleapiclient.discovery import build

    try:
        admin = build("analyticsadmin", "v1beta", credentials=c)
        for acc in admin.accountSummaries().list().execute().get("accountSummaries", []):
            for p in acc.get("propertySummaries", []):
                print(f"   GA4 속성  {p['property']}  {p['displayName']}")
    except Exception as e:
        print("   ⚠️ GA4 속성 조회 실패 — Analytics Admin API 를 켰는지 확인:", str(e)[:120])
    try:
        ads = build("adsense", "v2", credentials=c)
        for a in ads.accounts().list().execute().get("accounts", []):
            print(f"   애드센스   {a['name']}  {a.get('displayName')}")
    except Exception as e:
        print("   ⚠️ 애드센스 조회 실패 — AdSense Management API 를 켰는지 확인:", str(e)[:120])
