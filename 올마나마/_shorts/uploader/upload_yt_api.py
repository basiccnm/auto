# -*- coding: utf-8 -*-
"""유튜브 쇼츠 업로드 — API 방식 (2026-07-25)

    python upload_yt_api.py                 대기열 첫 편 미리보기 (안 올림)
    python upload_yt_api.py --publish       실제 업로드
    python upload_yt_api.py --id pizza1 --publish

🔴 브라우저 자동화(upload_yt.py)와 달리 셀렉터가 깨질 일이 없다. 로그인도 안 풀린다.
   대신 최초 1회 `python auth_yt.py` 로 인증해야 한다.

🔴 **업로드된 영상은 비공개(private)로 올라간다.**
   구글 미인증 앱은 public 을 지정해도 강제로 private 가 된다(정책, 우회 불가).
   → 업로드 후 유튜브 스튜디오에서 **공개로 바꾸는 클릭 한 번**이 남는다.
   제목·설명·태그는 전부 자동으로 들어가니 복붙은 없어진다.

🔴 할당량: 하루 10,000 유닛, 업로드 1건에 1,600 유닛 → **하루 6편**까지.
   주 11편 페이스면 넉넉하다.

🔴 쇼츠 판정: 세로 영상 + 3분 이하면 유튜브가 알아서 쇼츠로 분류한다. 별도 설정 없음.
   #Shorts 태그는 넣어두면 도움이 된다(queue.json 의 tags 에 이미 있음).
"""
import argparse
import os
import sys
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from common import load_queue, log, mark, need_file

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.path.join(HERE, "yt_token.json")
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
TAG = "YT"

# 유튜브 제목은 100자 제한. 넘으면 API 가 통째로 거부한다
TITLE_MAX = 100
DESC_MAX = 5000


def get_service():
    if not os.path.exists(TOKEN):
        log("인증이 없다. 먼저 python auth_yt.py 를 돌릴 것", TAG)
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    # 🔴 만료됐으면 조용히 갱신한다. refresh token 이 있으니 재로그인 불필요
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        log("토큰 갱신함", TAG)
    return build("youtube", "v3", credentials=creds)


def my_channel(yt):
    """지금 토큰이 가리키는 채널. 업로드는 **여기로** 나간다.

    🔴 2026-07-25 사고 — 확인 없이 올렸다가 엉뚱한 채널(개인 채널)로 갔다.
       계정에 채널이 여러 개면(브랜드 계정 포함) API 는 토큰이 붙은 채널 하나만 본다.
       채널을 바꾸려면 yt_token.json 을 지우고 auth_yt.py 를 다시 돌려 **채널 선택 화면에서 고른다.**
    """
    r = yt.channels().list(part="snippet", mine=True).execute()
    it = r.get("items", [])
    if not it:
        return None, None
    return it[0]["snippet"]["title"], it[0]["id"]


def add_to_playlist(yt, name, vid):
    """재생목록에 담고 **조회수 내림차순**으로 다시 세운다.

    🔴 재생목록 정렬 방식이 '수동'이 아니면 position 을 못 바꾼다
       (API 가 manualSortRequired 로 거부). 스튜디오에서 한 번 바꿔두면 계속 된다.
    🔴 한 항목을 옮기면 나머지가 밀린다 → 매번 목록을 다시 읽어 한 자리씩 확정한다.
    """
    pls = yt.playlists().list(part="snippet", mine=True, maxResults=50).execute()["items"]
    hit = [p for p in pls if p["snippet"]["title"] == name]
    if not hit:
        log(f"재생목록 「{name}」 이 없다 — 만든다", TAG)
        pid = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": name, "description": "메뉴별 재료값·원가율"},
            "status": {"privacyStatus": "public"}}).execute()["id"]
    else:
        pid = hit[0]["id"]

    items = yt.playlistItems().list(part="snippet", playlistId=pid, maxResults=50).execute()["items"]
    if vid not in [i["snippet"]["resourceId"]["videoId"] for i in items]:
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
        log(f"📃 재생목록 「{name}」 에 담음", TAG)

    def fetch():
        it = yt.playlistItems().list(part="snippet", playlistId=pid, maxResults=50).execute()["items"]
        ids = [i["snippet"]["resourceId"]["videoId"] for i in it]
        st = yt.videos().list(part="statistics", id=",".join(ids)).execute()["items"]
        return it, {v["id"]: int(v["statistics"].get("viewCount", 0)) for v in st}

    try:
        items, views = fetch()
        want = [i["snippet"]["resourceId"]["videoId"]
                for i in sorted(items, key=lambda i: -views.get(i["snippet"]["resourceId"]["videoId"], 0))]
        for pos, v2 in enumerate(want):
            items, _ = fetch()
            it = {i["snippet"]["resourceId"]["videoId"]: i for i in items}[v2]
            if it["snippet"]["position"] != pos:
                yt.playlistItems().update(part="snippet", body={"id": it["id"], "snippet": {
                    "playlistId": pid, "resourceId": it["snippet"]["resourceId"], "position": pos}}).execute()
                time.sleep(0.4)
        log("📃 조회수 순으로 정렬함", TAG)
    except HttpError as e:
        if "manualSortRequired" in str(e):
            log("⚠️ 재생목록 정렬이 '수동'이 아니라 순서를 못 바꿨다 (담기는 됨)", TAG)
            log("   스튜디오 → 재생목록 → 정렬 → '수동' 으로 한 번만 바꿀 것", TAG)
        else:
            raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="실제 업로드 (없으면 미리보기)")
    ap.add_argument("--id", help="queue.json 의 특정 id 만")
    # 🔴 2026-07-27 — force-ssl 권한을 받아서 아래가 가능해졌다
    ap.add_argument("--public", action="store_true", help="비공개가 아니라 바로 공개로 올린다")
    ap.add_argument("--comment", action="store_true", help="업로드 후 고정용 첫 댓글을 단다")
    # 🔴 재생목록은 **편 성격에 따라 갈린다**(2026-07-28).
    #    원가편 → 「음식 원가 해부」 / 레시피편 → 「초간단 레시피」
    #    큐 항목에 `playlist` 를 적어두면 그게 1순위다. 매번 --playlist 를 안 써도 된다.
    ap.add_argument("--playlist", default=None,
                    help="담을 재생목록 이름. 빈 문자열이면 안 담는다. "
                         "생략하면 큐의 playlist → 제목에 «레시피» 가 있으면 「초간단 레시피」 → 기본값 순")
    args = ap.parse_args()

    q = load_queue()
    v = None
    for x in q["videos"]:
        if args.id:
            if x["id"] == args.id:
                v = x
                break
        elif x.get("status", {}).get("yt") != "done":
            v = x
            break
    if not v:
        log("올릴 게 없다", TAG)
        sys.exit(0)

    mp4 = need_file(v["file_yt"], "유튜브용 영상")
    if not mp4:
        sys.exit(1)

    title = v.get("title", "")[:TITLE_MAX]
    desc = v.get("desc", "")[:DESC_MAX]
    tags = v.get("tags", [])

    log(f"대상: {v['id']} — {v.get('brand','')}", TAG)
    log(f"파일: {os.path.basename(mp4)} ({os.path.getsize(mp4)/1e6:.1f}MB)", TAG)
    log(f"제목({len(title)}자): {title}", TAG)
    log(f"설명 {len(desc)}자 · 태그 {len(tags)}개", TAG)

    # 🔴 업로드 전에 **어느 채널로 나가는지 반드시 찍는다**(2026-07-25 사고 방지)
    yt = get_service()
    ch_name, ch_id = my_channel(yt)
    if not ch_name:
        log("❌ 채널을 못 찾았다. 인증을 다시 할 것", TAG)
        sys.exit(1)
    log(f"📺 업로드될 채널: 「{ch_name}」 ({ch_id})", TAG)

    if not args.publish:
        log("⏸ 미리보기만. 실제로 올리려면 --publish", TAG)
        log("   ⚠️ 위 채널명이 맞는지 먼저 확인할 것", TAG)
        return

    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "26",  # Howto & Style — 원가·꿀팁 계열에 맞다
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            # 🔴 2026-07-27: force-ssl 권한이 생겨 --public 으로 바로 공개할 수 있다.
            #    안 주면 예전처럼 비공개로 올라간다(검수하고 올리고 싶을 때).
            "privacyStatus": "public" if args.public else "private",
            "selfDeclaredMadeForKids": False,
        },
    }

    # resumable=True 라 중간에 끊겨도 이어 올린다. 큰 파일에 안전
    media = MediaFileUpload(mp4, mimetype="video/mp4", chunksize=-1, resumable=True)
    try:
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        res = None
        while res is None:
            status, res = req.next_chunk()
            if status:
                log(f"업로드 {int(status.progress() * 100)}%", TAG)
        vid = res["id"]
    except HttpError as e:
        log(f"❌ 업로드 실패: {e}", TAG)
        sys.exit(1)

    log(f"✅ 업로드 완료 — https://youtu.be/{vid}", TAG)
    if args.public:
        log("🌐 공개 상태로 올라갔다", TAG)
    else:
        log("⚠️ 비공개 상태다. 공개하려면 --public 또는 스튜디오에서 전환", TAG)
        log(f"   https://studio.youtube.com/video/{vid}/edit", TAG)

    # ── 첫 댓글 (고정은 API 로 안 된다 — 손으로 눌러야 한다)
    if args.comment and v.get("comment"):
        try:
            c = yt.commentThreads().insert(part="snippet", body={"snippet": {
                "videoId": vid,
                "topLevelComment": {"snippet": {"textOriginal": v["comment"]}},
            }}).execute()
            log(f"💬 첫 댓글 달림 ({c['id']}) — 고정은 스튜디오에서 직접", TAG)
        except HttpError as e:
            log(f"⚠️ 댓글 실패: {e}", TAG)

    # ── 재생목록에 담고 조회수 순으로 다시 정렬
    # 재생목록 정하기 — 큐에 적힌 게 1순위, 없으면 제목으로 판별
    pl = args.playlist
    if pl is None:
        pl = v.get("playlist") or ("초간단 레시피" if "레시피" in v["title"] else "음식 원가 해부")
    if pl:
        try:
            add_to_playlist(yt, pl, vid)
        except HttpError as e:
            log(f"⚠️ 재생목록 실패: {e}", TAG)

    mark(q, v["id"], "yt", "done", vid)


main()
