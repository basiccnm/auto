# -*- coding: utf-8 -*-
"""로그인된 주문 앱 화면에서 가격을 읽어 브랜드 JSON 에 채운다 (범용 래퍼).

핵심 로직은 `app_menu_reader.AppMenuReader` (공통모듈 복사본). 여기서는
브랜드별 «slug·기기·상단탭(선택)»만 넘기고, 결과를 골격 JSON 에 병합한다.

사람이 앱을 «매장 선택 끝난 메뉴 목록» 화면에 띄운 상태에서 실행:
    python scripts/brand_app_read.py <slug> <device> [--tops "탭1,탭2,..."] [--apply]

  --apply 없으면 무엇을 채울지 미리보기만.
  --tops  자동 발견이 틀릴 때만 수동 지정.

⛔ DB 는 건드리지 않는다. `data/brand_menu_list/<slug>.json` 의 price 만 채운다(골격 유지).
⛔ 로그인 토큰을 꺼내지 않는다. 화면에 그려진 것만 읽는다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from app_menu_reader import AppMenuReader                       # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(s):
    return re.sub(r"[\s()（）]+", "", s).lower()


def main():
    if len(sys.argv) < 3:
        print("사용: python scripts/brand_app_read.py <slug> <device> "
              "[--tops \"a,b,c\"] [--apply]")
        return
    slug, device = sys.argv[1], sys.argv[2]
    apply_ = "--apply" in sys.argv
    tops = None
    if "--tops" in sys.argv:
        tops = [t.strip() for t in sys.argv[sys.argv.index("--tops") + 1].split(",") if t.strip()]

    jpath = os.path.join(BASE, "data", "brand_menu_list", "%s.json" % slug)
    if not os.path.exists(jpath):
        print("🔴 골격 JSON 없음:", jpath)
        return
    doc = json.load(io.open(jpath, encoding="utf-8"))
    menus = doc.get("menus", [])
    by_norm = {}
    for i, m in enumerate(menus):
        by_norm.setdefault(norm(m["name"]), []).append(i)

    r = AppMenuReader(device)
    method = r.detect()
    print("■ %s · 기기 %s · 방식=%s" % (slug, device, method), flush=True)
    if method == "canvas":
        print("🔴 캔버스 앱(글자 0·DevTools 잠김) — 이 래퍼로는 못 읽는다. OCR 필요."
              " 화면이 메뉴 목록이 맞는지도 확인할 것.")
        return
    if method == "devtools":
        print("⚠️ uiautomator 글자 0 · 웹뷰만 있음 — DOM 방식은 별도(webview_dom.py)로."
              " 우선 메뉴 화면에서 글자가 잡히는지 확인.")
        return

    data = r.collect(tops=tops)
    # 화면 판독분 → 브랜드×카테고리 형태로 저장(원본)
    scr = os.path.join(BASE, "data", "brand_menu_list", "_raw", "%s_app.json" % slug)
    os.makedirs(os.path.dirname(scr), exist_ok=True)
    json.dump(data, io.open(scr, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 이름 기준 병합
    flat = {}
    for cat, items in data.items():
        for it in items:
            flat.setdefault(it["name"], it["price"])
    hit = miss = 0
    unmatched = []
    for name, price in flat.items():
        idx = by_norm.get(norm(name))
        if idx:
            for i in idx:
                if not menus[i].get("price"):
                    menus[i]["price"] = price
                    menus[i]["price_source"] = "official"
                    menus[i]["price_note"] = "앱 매장주문 화면 판독"
            hit += 1
        else:
            miss += 1
            unmatched.append((name, price))

    n_price = sum(1 for m in menus if m.get("price"))
    print("판독 카테고리 %d · 판독 메뉴 %d(고유) · 골격매칭 %d · 골격에없음 %d"
          % (len(data), len(flat), hit, miss), flush=True)
    print("→ 골격 %d개 중 가격 %d개" % (len(menus), n_price), flush=True)
    if unmatched:
        print("  ⚠️ 골격에 없는 판독분(앱에만 있음) 예:",
              [u[0] for u in unmatched[:8]])
    print("  화면 판독 원본:", scr)

    if apply_:
        # 골격에 없던 앱 전용 메뉴는 app_menus 로 보관(버리지 않음)
        doc["app_menus"] = [{"name": n, "price": p} for n, p in unmatched]
        doc.setdefault("source", "")
        json.dump(doc, io.open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("✅ 저장:", jpath)
    else:
        print("(미리보기 — 반영하려면 --apply)")


if __name__ == "__main__":
    main()
