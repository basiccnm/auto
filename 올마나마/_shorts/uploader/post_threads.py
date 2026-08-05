# -*- coding: utf-8 -*-
"""스레드 글 발행 (2026-07-24)

    python post_threads.py --text "올릴 글"              미리보기
    python post_threads.py --text "올릴 글" --publish    실제 발행
    python post_threads.py --from-queue --publish        queue_cards.json 캡션 재활용

🔴 인스타 캐러셀과 달리 **2단계**다: 컨테이너 생성 → 발행.
🔴 글자 수 500자 제한. 넘으면 잘리는 게 아니라 에러가 난다.
🔴 이미지를 붙일 거면 인스타와 마찬가지로 **공개 HTTPS 주소**가 필요하다.
   여러 장이면 CAROUSEL(자식 컨테이너 → 부모)로, 인스타와 같은 구조다.
"""
import argparse
import json
import os
import sys
import time

from meta_common import TH_BASE, TH_VER, api, load_env, log

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue_cards.json")
TAG = "TH"
LIMIT = 500


def create_text(uid, token, text):
    r = api(
        "{}/{}/{}/threads".format(TH_BASE, TH_VER, uid),
        {"media_type": "TEXT", "text": text, "access_token": token},
        post=True,
    )
    return r["id"]


def create_image_child(uid, token, url):
    r = api(
        "{}/{}/{}/threads".format(TH_BASE, TH_VER, uid),
        {"media_type": "IMAGE", "image_url": url, "is_carousel_item": "true",
         "access_token": token},
        post=True,
    )
    return r["id"]


def create_carousel(uid, token, children, text):
    r = api(
        "{}/{}/{}/threads".format(TH_BASE, TH_VER, uid),
        {"media_type": "CAROUSEL", "children": ",".join(children), "text": text,
         "access_token": token},
        post=True,
    )
    return r["id"]


def publish(uid, token, container_id):
    r = api(
        "{}/{}/{}/threads_publish".format(TH_BASE, TH_VER, uid),
        {"creation_id": container_id, "access_token": token},
        post=True,
    )
    return r["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="올릴 글")
    ap.add_argument("--images", nargs="*", default=[], help="이미지 공개 URL (없으면 글만)")
    ap.add_argument("--from-queue", action="store_true", help="queue_cards.json 것 재활용")
    ap.add_argument("--id")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    env = load_env()
    uid = env["TH_USER_ID"]
    token = env["TH_ACCESS_TOKEN"]

    text = args.text
    images = list(args.images)

    if args.from_queue:
        if not os.path.exists(QUEUE):
            log("발행 목록이 없다: {}".format(QUEUE), TAG)
            sys.exit(1)
        q = json.load(open(QUEUE, encoding="utf-8"))
        item = None
        for x in q["cards"]:
            if args.id:
                if x["id"] == args.id:
                    item = x
                    break
            elif x.get("th_status") != "done":
                item = x
                break
        if not item:
            log("올릴 게 없다", TAG)
            sys.exit(0)
        # 🔴 스레드는 500자라 인스타 캡션을 그대로 쓰면 넘친다 — th_text 를 따로 두는 게 낫다
        text = item.get("th_text") or item.get("caption", "")
        # 🔴 스레드는 이미지도 따로 고른다(2026-07-24). 인스타 캐러셀 6장을 그대로 올렸더니
        #    "너무 많다" — 스레드는 넘겨 보는 사람이 적어 뒷장이 안 읽힌다. th_images 로 추린다
        images = (item.get("th_images") or item.get("images", []))[:10]

    if not text:
        log("올릴 글이 없다 — --text 또는 --from-queue", TAG)
        sys.exit(1)

    if len(text) > LIMIT:
        log("❌ {}자 — 스레드 한도 {}자를 넘는다".format(len(text), LIMIT), TAG)
        log("   앞 {}자: {}".format(LIMIT, text[:LIMIT]), TAG)
        sys.exit(1)

    log("글 {}자 · 이미지 {}장".format(len(text), len(images)), TAG)
    log("─" * 40, TAG)
    print(text)
    log("─" * 40, TAG)

    if not args.publish:
        log("⏸ 미리보기만. 실제로 올리려면 --publish", TAG)
        return

    if not images:
        cid = create_text(uid, token, text)
    elif len(images) == 1:
        r = api(
            "{}/{}/{}/threads".format(TH_BASE, TH_VER, uid),
            {"media_type": "IMAGE", "image_url": images[0], "text": text,
             "access_token": token},
            post=True,
        )
        cid = r["id"]
    else:
        children = []
        for i, u in enumerate(images, 1):
            children.append(create_image_child(uid, token, u))
            log("자식 {}/{}".format(i, len(images)), TAG)
            time.sleep(1)
        cid = create_carousel(uid, token, children, text)

    log("컨테이너 {}".format(cid), TAG)
    time.sleep(3)  # 🔴 바로 publish 하면 아직 처리 중이라 실패한다
    post_id = publish(uid, token, cid)
    log("✅ 발행 완료 — {}".format(post_id), TAG)

    if args.from_queue:
        item["th_status"] = "done"
        item["th_post_id"] = post_id
        json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
