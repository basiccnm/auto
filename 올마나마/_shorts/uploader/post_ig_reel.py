# -*- coding: utf-8 -*-
"""인스타 릴스 발행 — Graph API (2026-07-25)

    python post_ig_reel.py --dry                     무엇을 올릴지 보기만
    python post_ig_reel.py --publish                 실제 발행
    python post_ig_reel.py --publish --comment       발행 후 첫 댓글까지

🔴 **브라우저 자동화(upload_ig.py) 대신 이걸 쓴다.** 클릭 흉내는 인스타 UI가 바뀔 때마다 깨졌다.
   캐러셀(post_ig_carousel.py)이 이미 API로 잘 돌고 있어서 같은 방식으로 맞췄다.

🔴 **API는 로컬 파일을 못 받는다.** mp4 가 공개된 HTTPS 주소에 떠 있어야 한다.
   올마나마가 Cloudflare에 있으니 `_dist/` 에 넣고 배포한 뒤 그 주소를 쓴다.
   발행되면 인스타가 파일을 자기 서버로 복사하므로 원본은 나중에 지워도 된다.

🔴 릴스는 **인코딩 때문에 이미지보다 훨씬 오래 걸린다.** 캐러셀은 20회×3초면 됐지만
   여기는 넉넉히 기다린다(기본 40회×5초 = 최대 3분 20초).

🔴 **음원(오디오 트랙)은 API로 못 넣는다.** 앱에서 처음부터 만들어야만 붙는다.
   그래서 이 채널은 **음원 없이 간다**(2026-07-25 결정).

🔴 댓글은 API로 **달 수는 있지만 고정(pin)은 못 한다.** 고정은 폰에서 눌러야 한다.

🔴 제약 (메타 문서 기준)
     - MP4 / H.264 + AAC, 세로 9:16 권장
     - 3초 ~ 15분, 1GB 이하
     - 캡션 2,200자 · 해시태그 30개까지
"""
import argparse
import json
import os
import sys
import time

from meta_common import IG_BASE, IG_VER, api, load_env, log

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue_reels.json")
TAG = "IG릴스"


def create_container(uid, token, video_url, caption, cover_url=None, share_to_feed=True):
    """릴스 컨테이너 생성. 캐러셀과 달리 자식 단계가 없다 — 한 번에 만든다."""
    p = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        # 피드에도 같이 노출한다. false 면 릴스 탭에만 남는다
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": token,
    }
    if cover_url:
        # 표지를 안 주면 인스타가 첫 프레임을 쓴다. 우리 첫 프레임이 곧 썸네일이라 보통 생략해도 된다
        p["cover_url"] = cover_url
    return api("{}/{}/{}/media".format(IG_BASE, IG_VER, uid), p, post=True)["id"]


def wait_ready(token, container_id, tries=40, gap=5):
    """인스타가 영상을 내려받아 인코딩할 때까지 기다린다.
    🔴 안 기다리고 publish 하면 '아직 준비 안 됨' 에러가 난다."""
    for i in range(tries):
        r = api(
            "{}/{}/{}".format(IG_BASE, IG_VER, container_id),
            {"fields": "status_code,status", "access_token": token},
        )
        code = r.get("status_code")
        if code == "FINISHED":
            return True
        if code == "ERROR":
            log("컨테이너 처리 실패: {}".format(r.get("status")), TAG)
            return False
        log("  인코딩 대기 {}/{} ({})".format(i + 1, tries, code), TAG)
        time.sleep(gap)
    log("대기 시간 초과 — 컨테이너는 남아 있으니 나중에 publish 만 다시 하면 된다", TAG)
    return False


def publish(uid, token, container_id):
    return api(
        "{}/{}/{}/media_publish".format(IG_BASE, IG_VER, uid),
        {"creation_id": container_id, "access_token": token},
        post=True,
    )["id"]


def add_comment(token, media_id, text):
    """첫 댓글(원가 기준 안내). 🔴 고정은 API로 안 되니 폰에서 눌러야 한다."""
    return api(
        "{}/{}/{}/comments".format(IG_BASE, IG_VER, media_id),
        {"message": text, "access_token": token},
        post=True,
    )["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="실제 발행 (없으면 미리보기)")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--comment", action="store_true", help="발행 후 첫 댓글까지 단다")
    ap.add_argument("--id", help="queue_reels.json 의 특정 id만")
    args = ap.parse_args()

    env = load_env()
    uid = env["IG_USER_ID"]
    token = env["IG_ACCESS_TOKEN"]

    if not os.path.exists(QUEUE):
        log("발행 목록이 없다: {}".format(QUEUE), TAG)
        sys.exit(1)

    q = json.load(open(QUEUE, encoding="utf-8"))
    item = None
    for x in q["reels"]:
        if args.id:
            if x["id"] == args.id:
                item = x
                break
        elif x.get("status") != "done":
            item = x
            break

    if not item:
        log("올릴 게 없다", TAG)
        sys.exit(0)

    caption = item.get("caption", "")
    if item.get("tags"):
        caption += "\n\n" + " ".join("#" + t for t in item["tags"])

    log("대상: {}".format(item["id"]), TAG)
    log("영상: {}".format(item["video"]), TAG)
    log("캡션 {}자".format(len(caption)), TAG)
    if item.get("comment"):
        log("첫 댓글 {}자 (--comment 줘야 달린다)".format(len(item["comment"])), TAG)

    if not args.publish or args.dry:
        log("⏸ 미리보기만. 실제로 올리려면 --publish", TAG)
        return

    cid = create_container(uid, token, item["video"], caption, item.get("cover"))
    log("컨테이너 {}".format(cid), TAG)

    if not wait_ready(token, cid):
        sys.exit(1)

    post_id = publish(uid, token, cid)
    log("✅ 발행 완료 — 게시물 {}".format(post_id), TAG)

    if args.comment and item.get("comment"):
        c = add_comment(token, post_id, item["comment"])
        log("💬 첫 댓글 {} — 고정은 폰에서 직접 눌러야 한다".format(c), TAG)

    item["status"] = "done"
    item["post_id"] = post_id
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
