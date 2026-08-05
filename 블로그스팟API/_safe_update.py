# -*- coding: utf-8 -*-
"""글 본문을 통째로 교체할 때 쓰는 안전 업데이트 헬퍼.

2026-07-17 사고: 본문을 새로 써서 update()로 덮어쓸 때 기존 대표이미지와
숨긴 쿠팡 상품카드가 통째로 날아갔다. 재작성 스크립트는 반드시 이 헬퍼를 쓸 것.

사용법:
    from _safe_update import extract_assets, assert_assets_kept

    old = post["content"]
    assets = extract_assets(old)          # 썸네일 / 상품카드 / 고지문구 추출
    new = assets["thumb"] + my_new_body   # 새 본문에 썸네일 다시 얹기
    assert_assets_kept(assets, new)       # 유실되면 여기서 중단
"""
import re

THUMB_RE = re.compile(r'<!-- THUMBNAIL_IMAGE_V1 -->.*?</div>', re.DOTALL)
CARD_RE = re.compile(r'<!--COUPANG_HIDDEN_FOR_ADSENSE:\[\[PRODCARD:.*?\[\[/PRODCARD\]\]-->', re.DOTALL)
DISC_RE = re.compile(r'<div style="text-align: center;"><span style="font-size: x-small;">'
                     r'<!--COUPANG_HIDDEN_FOR_ADSENSE:.*?--></span></div>', re.DOTALL)
IMG_RE = re.compile(r'<img[^>]+>', re.IGNORECASE)


def extract_assets(html):
    """기존 본문에서 보존해야 할 자산을 뽑아낸다."""
    html = html or ""
    m = THUMB_RE.search(html)
    d = DISC_RE.search(html)
    # 숨긴 카드 안의 상품 이미지는 제외하고 '보이는' 이미지만 센다
    visible = CARD_RE.sub("", html)
    return {
        "thumb": m.group(0) if m else "",
        "cards": CARD_RE.findall(html),
        "disclosure": d.group(0) if d else "",
        "n_visible_img": len(IMG_RE.findall(visible)),
    }


def assert_assets_kept(assets, new_html, allow_new_img=True):
    """새 본문이 기존 자산을 지키고 있는지 검증. 어기면 예외를 던져 푸시를 막는다."""
    if assets["thumb"] and assets["thumb"] not in new_html:
        raise AssertionError("대표이미지(THUMBNAIL_IMAGE_V1)가 유실됨")

    kept = len(CARD_RE.findall(new_html))
    if kept != len(assets["cards"]):
        raise AssertionError(f"상품카드 유실: {len(assets['cards'])}개 -> {kept}개")

    if assets["disclosure"] and assets["disclosure"] not in new_html:
        raise AssertionError("쿠팡 고지문구가 유실됨")

    now = len(IMG_RE.findall(CARD_RE.sub("", new_html)))
    if now < assets["n_visible_img"] and not allow_new_img:
        raise AssertionError(f"본문 이미지 유실: {assets['n_visible_img']}개 -> {now}개")
    if assets["n_visible_img"] > 0 and now == 0:
        raise AssertionError(f"본문 이미지가 전부 사라짐 (기존 {assets['n_visible_img']}개)")
    return True
