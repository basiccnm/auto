# -*- coding: utf-8 -*-
"""유튜브 API 최초 인증 (2026-07-25)

    python auth_yt.py

🔴 딱 한 번만 돌리면 된다. 브라우저가 열리고 구글 로그인 → 권한 허용하면
   `yt_token.json` 이 생긴다. 그다음부터는 upload_yt_api.py 가 알아서 쓴다.

🔴 준비물: Google Cloud Console 에서 받은 `client_secret.json`
     ① console.cloud.google.com → 프로젝트 생성
     ② "YouTube Data API v3" 사용 설정
     ③ 사용자 인증 정보 → OAuth 클라이언트 ID → **데스크톱 앱**
     ④ JSON 다운로드 → 이 폴더에 `client_secret.json` 으로 저장

🔴 토큰은 refresh token 이라 만료되지 않는다(인스타처럼 60일 갱신 안 해도 됨).
   단, 앱이 "테스트" 상태면 7일마다 만료된다 → OAuth 동의화면에서 **게시(프로덕션)** 로 바꿀 것.
"""
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from common import log

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET = os.path.join(HERE, "client_secret.json")
TOKEN = os.path.join(HERE, "yt_token.json")

# 업로드만 필요하면 youtube.upload 로 충분하다. 최소 권한 원칙.
# 🔴 readonly 를 같이 받는다 — 업로드 전에 **어느 채널인지 확인**하기 위해서다.
#    2026-07-25에 확인 없이 올렸다가 엉뚱한 채널로 갔다(브랜드 계정이 아닌 개인 채널).
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    # 🔴 2026-07-26 추가 — 전체 관리. 재생목록·댓글·공개상태·제목수정에 필요
    "https://www.googleapis.com/auth/youtube.force-ssl",
    # 🔴 2026-07-27 추가 — 성적 분석. 조회율·이탈지점·성별연령·유입경로를 본다
    #    "조회수 11이었다가 떡상" 같은 걸 감이 아니라 날짜별 숫자로 확인하려면 이게 있어야 한다
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]
TAG = "YT-AUTH"


def main():
    if not os.path.exists(SECRET):
        log("client_secret.json 이 없다. 위 주석의 ①~④ 를 먼저 할 것", TAG)
        sys.exit(1)

    if os.path.exists(TOKEN):
        log(f"이미 인증돼 있다 → {TOKEN}", TAG)
        log("다시 받으려면 yt_token.json 을 지우고 실행할 것", TAG)
        sys.exit(0)

    flow = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES)
    log("브라우저가 열린다. 구글 로그인 → 권한 허용할 것", TAG)
    # 🔴 port=0 이면 빈 포트를 알아서 잡는다. 고정 포트는 이미 쓰는 중일 수 있어 피한다
    # 🔴 prompt="select_account consent" — 계정·채널 선택 화면을 **강제로** 띄운다.
    #    "consent" 만 주면 브라우저에 로그인된 기본 채널로 그냥 넘어간다
    #    (2026-07-25: 올마나마 대신 사장픽 채널로 두 번 잡혔다).
    # 🔴 open_browser=False — 기본 브라우저가 제멋대로 열리면 제어가 안 된다.
    #    URL 을 콘솔에 찍고, 그 주소를 원하는 브라우저에서 열어 진행한다.
    creds = flow.run_local_server(
        port=0, prompt="select_account consent", open_browser=False
    )

    with open(TOKEN, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    log(f"✅ 인증 완료 → {TOKEN}", TAG)
    log("이제 python upload_yt_api.py 로 올릴 수 있다", TAG)


main()
