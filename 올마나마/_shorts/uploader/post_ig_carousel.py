# -*- coding: utf-8 -*-
"""인스타 카드뉴스(캐러셀) 발행 (2026-07-24)

    python post_ig_carousel.py --dry              무엇을 올릴지 보기만
    python post_ig_carousel.py --publish          실제 발행

🔴 **API는 로컬 파일을 못 받는다.** 이미지가 공개된 HTTPS 주소에 떠 있어야 한다.
   올마나마가 Cloudflare에 있으니 거기 올리고 그 주소를 넘긴다.
   발행되면 인스타가 이미지를 자기 서버로 복사하므로 원본은 지워도 된다.

🔴 캐러셀은 3단계다. 중간에 끊기면 컨테이너만 남고 게시는 안 된다(무해하니 재시도하면 된다).
     ① 이미지 장수만큼 자식 컨테이너 생성 (is_carousel_item=true)
     ② 그 id들을 묶어 부모 컨테이너 생성 (+ 캡션)
     ③ 부모를 media_publish 로 발행

🔴 제약 (메타 문서 기준)
     - 이미지 2~10장
     - JPEG 권장. 정사각(1:1)이 안전하다
     - 캡션 2,200자 · 해시태그 30개까지
     - 하루 게시 한도가 있다(대략 50건). 우리 사용량으론 문제없다
"""
import argparse
import json
import os
import sys
import time

from meta_common import IG_BASE, IG_VER, api, load_env, log

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue_cards.json")
TAG = "IG"


def create_child(uid, token, image_url):
    """자식 컨테이너 하나 — 캐러셀 낱장"""
    r = api(
        "{}/{}/{}/media".format(IG_BASE, IG_VER, uid),
        {"image_url": image_url, "is_carousel_item": "true", "access_token": token},
        post=True,
    )
    return r["id"]


def create_parent(uid, token, children, caption):
    r = api(
        "{}/{}/{}/media".format(IG_BASE, IG_VER, uid),
        {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": token,
        },
        post=True,
    )
    return r["id"]


def wait_ready(token, container_id, tries=20, gap=3):
    """인스타가 이미지를 내려받아 처리할 때까지 기다린다.
    🔴 안 기다리고 바로 publish 하면 '아직 준비 안 됨' 에러가 난다."""
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
        time.sleep(gap)
    log("대기 시간 초과 — 나중에 다시 시도", TAG)
    return False


def publish(uid, token, container_id):
    r = api(
        "{}/{}/{}/media_publish".format(IG_BASE, IG_VER, uid),
        {"creation_id": container_id, "access_token": token},
        post=True,
    )
    return r["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="실제 발행 (없으면 미리보기)")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--id", help="queue_cards.json 의 특정 id만")
    args = ap.parse_args()

    env = load_env()
    uid = env["IG_USER_ID"]
    token = env["IG_ACCESS_TOKEN"]

    if not os.path.exists(QUEUE):
        log("발행 목록이 없다: {}".format(QUEUE), TAG)
        log("queue_cards.json 을 만들고 이미지 주소·캡션을 넣을 것", TAG)
        sys.exit(1)

    q = json.load(open(QUEUE, encoding="utf-8"))
    item = None
    for x in q["cards"]:
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

    images = item["images"]
    caption = item.get("caption", "")
    if item.get("tags"):
        caption += "\n\n" + " ".join("#" + t for t in item["tags"])

    log("대상: {} ({}장)".format(item["id"], len(images)), TAG)
    for i, u in enumerate(images, 1):
        log("  {}. {}".format(i, u), TAG)
    log("캡션 {}자".format(len(caption)), TAG)

    if not (2 <= len(images) <= 10):
        log("❌ 이미지는 2~10장이어야 한다 (지금 {}장)".format(len(images)), TAG)
        sys.exit(1)

    if not args.publish or args.dry:
        log("⏸ 미리보기만. 실제로 올리려면 --publish", TAG)
        return

    # ① 자식 컨테이너
    children = []
    for i, url in enumerate(images, 1):
        cid = create_child(uid, token, url)
        children.append(cid)
        log("자식 {}/{} 생성 {}".format(i, len(images), cid), TAG)
        time.sleep(1)

    # ② 부모 컨테이너
    parent = create_parent(uid, token, children, caption)
    log("부모 컨테이너 {}".format(parent), TAG)

    # ③ 처리 대기 후 발행
    if not wait_ready(token, parent):
        sys.exit(1)
    post_id = publish(uid, token, parent)
    log("✅ 발행 완료 — 게시물 {}".format(post_id), TAG)

    item["status"] = "done"
    item["post_id"] = post_id
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
