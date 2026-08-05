# -*- coding: utf-8 -*-
"""collect_reply.py — 제미나이가 쓴 회신 문서를 회수해 규약 파일로 저장한다.

왜 필요한가
    제미나이는 **폴더 지정도, .md 파일 생성도 못 한다**(2026-08-01 실측).
    답을 쓰라고 하면 `내 드라이브` 최상단에 **구글 문서**로만 만든다.
    그 문서는 클라우드 전용이라 로컬 G: 에서는 내용을 읽을 수 없다(포인터 파일일 뿐).
    → 드라이브 API 로 본문을 받아 `sajangpick\회신NN.md` 로 옮기는 것이 이 스크립트다.

왜 AI 를 안 쓰는가
    이 작업엔 판단이 없다. "문서 찾기 → 텍스트 받기 → 파일로 쓰기"가 전부다.
    claude -p 를 쓰면 로그인이 풀릴 때마다 멈추고 사용량도 든다(실제로 그래서 막혔다).
    코드로 하면 사람도 AI 도 없이 밤새 돈다.

준비 (최초 1회)
    1) credentials.json 을 이 폴더에 둔다.
       ⚠ 블로그스팟API 폴더의 것을 **복사**해 쓰면 된다(같은 구글 프로젝트).
    2) python collect_reply.py 를 한 번 직접 실행하면 브라우저가 열린다. 동의하면 끝.
       → drive_token.pickle 이 생기고, 이후로는 자동이다.
    ⚠ 블로그 발행용 token.pickle 과 **파일을 나눈다.** 권한 범위가 달라 섞으면 블로그 쪽이 깨진다.

실행
    python collect_reply.py            # 회수할 게 있으면 회수, 없으면 조용히 종료
    python collect_reply.py --list     # 최상단 회신 문서만 확인 (쓰기 없음)
"""
import io
import os
import pickle
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMM = r"G:\내 드라이브\sajangpick"

CREDENTIALS_FILE = os.path.join(HERE, "credentials.json")
TOKEN_FILE = os.path.join(HERE, "drive_token.pickle")
# 읽기 전용으로 충분하다. 쓰기 권한을 안 받는 게 사고 위험이 적다
# (드라이브 파일을 실수로 지우거나 덮어쓸 경로 자체를 만들지 않는다).
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# 회신 문서 이름 규칙.
# ⚠ adb 는 한글을 못 친다(ADBKeyboard 는 편집창이 떠서 안 쓰기로 함, 2026-08-01).
#    그래서 제미나이에겐 **영문 이름**으로 시키고, 여기서 둘 다 받는다.
#    「회신08」 · 「REPLY08」 · 「reply_08」 모두 08 로 본다.
REPLY_RE = re.compile(r"(?:회신|reply)[\s_-]*(\d{2})", re.I)
# 드라이브 검색어 (name contains 는 대소문자 구분 안 함)
NAME_HINTS = ["회신", "REPLY"]


def service():
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print("credentials.json 이 없습니다.")
                print("  블로그스팟API 폴더의 credentials.json 을 이 폴더로 복사한 뒤 다시 실행하세요.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("drive", "v3", credentials=creds)


def find_replies(svc):
    """내 드라이브 최상단의 회신 구글 문서들. 최신순. 한글·영문 이름 둘 다 받는다.

    ⚠ 번호는 **이름에서 못 찾으면 본문에서** 읽는다.
      제미나이가 저장을 건너뛰면 앱의 「Docs로 내보내기」로 뽑는데, 그때 문서 이름이
      제 이름이 아니라 **답변 첫 줄**로 붙는다("You said REPLY09 was saved..." 같은 식).
      이름만 보면 번호를 놓쳐 영영 회수가 안 된다(2026-08-02).
    """
    out, seen = [], set()
    for hint in NAME_HINTS:
        q = ("'root' in parents and trashed = false "
             "and mimeType = 'application/vnd.google-apps.document' "
             f"and name contains '{hint}'")
        res = svc.files().list(q=q, orderBy="modifiedTime desc",
                               fields="files(id,name,modifiedTime)", pageSize=20).execute()
        for f in res.get("files", []):
            if f["id"] in seen:
                continue
            m = REPLY_RE.search(f["name"])
            num = m.group(1) if m else None
            if not num:
                # 이름에 번호가 없다 — 본문 앞부분에서 찾아본다
                head = export_text(svc, f["id"])[:400]
                m2 = REPLY_RE.search(head)
                num = m2.group(1) if m2 else None
            if num:
                seen.add(f["id"])
                out.append({"id": f["id"], "name": f["name"],
                            "num": num, "modified": f.get("modifiedTime", "")})
    # 이름에 회신/REPLY 가 아예 안 들어간 경우까지 잡는다.
    # 내보내기로 만든 문서는 이름이 답변 첫 줄이라 「주제: …」 로 시작할 수도 있다.
    q = ("'root' in parents and trashed = false "
         "and mimeType = 'application/vnd.google-apps.document'")
    res = svc.files().list(q=q, orderBy="modifiedTime desc",
                           fields="files(id,name,modifiedTime)", pageSize=10).execute()
    for f in res.get("files", []):
        if f["id"] in seen:
            continue
        m2 = REPLY_RE.search(export_text(svc, f["id"])[:400])
        if m2:
            seen.add(f["id"])
            out.append({"id": f["id"], "name": f["name"],
                        "num": m2.group(1), "modified": f.get("modifiedTime", "")})

    out.sort(key=lambda x: x["modified"], reverse=True)
    return out


def export_text(svc, file_id):
    """구글 문서를 일반 텍스트로 받는다. (마크다운 export 는 문서 종류에 따라 실패해서 txt 로 통일)"""
    data = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    return data.replace("\r\n", "\n").strip()


def normalize(body, num):
    """규약 형식으로 맞춘다 — 첫 줄 주제, 둘째 줄 STATUS."""
    # ⚠ 구글 문서 export 는 맨 앞에 BOM(﻿)을 붙인다.
    #    이걸 안 벗기면 startswith("주제:") 가 빗나가 «주제:» 가 두 번 찍힌다(2026-08-01 실제 발생).
    body = body.lstrip("﻿")

    cleaned = []
    for l in body.split("\n"):
        l = l.rstrip().lstrip("﻿")
        l = re.sub(r"\*\*(.+?)\*\*", r"\1", l)   # 굵게 표시 제거
        l = re.sub(r"^#{1,6}\s*", "", l)          # 문서에서 넘어온 제목 기호 제거
        cleaned.append(l)
    text = "\n".join(cleaned).strip()

    has_topic = bool(re.match(r"^\s*주제\s*:", text))
    has_status = re.search(r"^\s*STATUS\s*:", text, re.M)

    head = []
    if not has_topic:
        head.append(f"주제: 회신{num}")
    if not has_status:
        head.append("STATUS: 확정")
    if head:
        text = "\n".join(head) + "\n\n" + text

    note = ("\n\n---\n"
            "> 이 파일은 `collect_reply.py` 가 자동 회수한 것입니다.\n"
            "> 제미나이는 폴더 지정·`.md` 생성이 불가해 `내 드라이브` 최상단에 구글 문서로 답을 씁니다.\n"
            "> 그 문서를 텍스트로 받아 규약 형식으로 옮겼습니다. 본문은 원문 그대로입니다.\n")
    return text + note


def main():
    only_list = "--list" in sys.argv
    svc = service()
    items = find_replies(svc)

    if not items:
        print("회수할 회신 문서 없음")
        return 0

    if only_list:
        for it in items:
            print(f"{it['name']}  (회신{it['num']}, {it['modified']})")
        return 0

    done = 0
    for it in items:
        target = os.path.join(COMM, f"회신{it['num']}.md")
        # 이미 있으면 건너뛴다 — 코드탭이 처리 중일 수 있어 덮어쓰지 않는다.
        if os.path.exists(target):
            print(f"건너뜀 (이미 있음): 회신{it['num']}.md")
            continue
        body = export_text(svc, it["id"])
        if not body:
            print(f"건너뜀 (내용 비어있음): {it['name']}")
            continue
        with io.open(target, "w", encoding="utf-8") as f:
            f.write(normalize(body, it["num"]))
        print(f"회수 완료: 회신{it['num']}.md  ({len(body)}자)")
        done += 1

    if done == 0:
        print("새로 회수한 것 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
