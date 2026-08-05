"""
방구석 약국 - 블로그스팟 자동 발행 스크립트

사용 방법:
1. credentials.json 파일을 이 스크립트와 같은 폴더에 둔다.
2. BLOG_URL을 본인 블로그 주소로 수정한다.
3. posts 폴더를 만들고, 그 안에 발행할 글을 텍스트 파일로 넣는다.
   파일 형식은 아래 예시 참고 (한 파일 = 글 1개)
4. 터미널에서 python auto_post.py 실행
5. 처음 실행 시 브라우저가 뜨면 구글 계정으로 로그인 + 권한 허용
6. 이후 posts 폴더의 글들이 순서대로 자동 발행되고, posted 폴더로 이동된다.

--- 글 파일 형식 (posts/001.txt 예시) ---
TITLE: 유산균 먹으면 좋은 점 총정리 - 효능, 부작용, 연령별·성별 고르는 법
LABELS: 성분 및 효능·부작용, 유산균, 프로바이오틱스
---
(본문 내용을 여기에 그대로 붙여넣기. HTML 태그 사용 가능:
 <p>문단</p>, <b>굵게</b>, <table>표</table> 등)
--------------------------------------
"""

import os
import glob
import shutil
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# ===== 설정 (본인 정보로 수정) =====
BLOG_URL = "https://bangpharmacy.blogspot.com/"  # 본인 블로그 주소로 수정
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"
POSTS_FOLDER = "posts"
POSTED_FOLDER = "posted"
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def get_service():
    """구글 인증을 거쳐 Blogger API 서비스 객체를 반환한다."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("blogger", "v3", credentials=creds)


def get_blog_id(service, blog_url):
    """블로그 URL로 블로그 ID를 조회한다."""
    result = service.blogs().getByUrl(url=blog_url).execute()
    return result["id"]


def parse_post_file(filepath):
    """텍스트 파일을 읽어 제목, 라벨, 본문으로 분리한다."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---", 1)
    header = parts[0]
    body = parts[1].strip() if len(parts) > 1 else ""

    title = ""
    labels = []
    for line in header.strip().split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("LABELS:"):
            labels = [l.strip() for l in line.replace("LABELS:", "").split(",")]

    return title, labels, body


def publish_post(service, blog_id, title, labels, body):
    """글 하나를 블로그스팟에 발행한다."""
    post_body = {
        "kind": "blogger#post",
        "title": title,
        "content": body,
        "labels": labels,
    }
    result = service.posts().insert(blogId=blog_id, body=post_body, isDraft=False).execute()
    return result.get("url")


def main():
    if not os.path.exists(POSTED_FOLDER):
        os.makedirs(POSTED_FOLDER)

    service = get_service()
    blog_id = get_blog_id(service, BLOG_URL)
    print(f"블로그 ID 확인 완료: {blog_id}")

    files = sorted(glob.glob(os.path.join(POSTS_FOLDER, "*.txt")))
    if not files:
        print("발행할 글이 posts 폴더에 없습니다.")
        return

    for filepath in files:
        title, labels, body = parse_post_file(filepath)
        if not title or not body:
            print(f"건너뜀 (형식 오류): {filepath}")
            continue

        try:
            url = publish_post(service, blog_id, title, labels, body)
            print(f"발행 완료: {title}")
            print(f"  -> {url}")
            shutil.move(filepath, os.path.join(POSTED_FOLDER, os.path.basename(filepath)))
        except Exception as e:
            print(f"발행 실패: {title}")
            print(f"  오류: {e}")


if __name__ == "__main__":
    main()
