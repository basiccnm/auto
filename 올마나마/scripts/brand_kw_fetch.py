# -*- coding: utf-8 -*-
"""브랜드별 쿠팡 검색 수집 — 프랜차이즈 **공식 냉동/밀키트 제품**을 찾기 위한 것. 2026-07-25

왜 필요한가:
  기존 캐시는 '메뉴명 + 냉동' 위주라 브랜드 공식몰 제품을 못 잡았다.
  실제로는 쿠팡에 "[비비큐] BBQ 자메이카 통다리 바베큐"처럼 **공식몰 상품이 있다**.
  브랜드명으로 검색해야 이게 잡힌다(2026-07-25 대표 확인).

mealkit_run.py 의 get_items/cache_path 를 재사용한다(같은 캐시 폴더 공유 → 검수 빌더가 바로 씀).
사용법: python scripts/brand_kw_fetch.py [--budget=150]
"""
import io, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mealkit_run as mk  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(BASE, "data", "research", "brand_kw_todo.json")


def main():
    budget = 150
    for a in sys.argv[1:]:
        if a.startswith("--budget="):
            budget = int(a.split("=", 1)[1])

    env = mk.load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY", ""), env.get("COUPANG_SECRET_KEY", "")
    if not ak or not sk:
        print("[X] .env 에 쿠팡 키가 없습니다.")
        return 1

    kws = json.load(io.open(TODO, encoding="utf-8"))
    state = {"used": 0, "budget": budget, "gap": 2.2,
             "logf": io.open(os.path.join(BASE, "data", "research", "brand_kw.log"),
                             "a", encoding="utf-8")}
    done = hit = 0
    for kw in kws:
        if state["used"] >= budget:
            print("예산 소진 — 남은 검색어 %d개" % (len(kws) - done))
            break
        if os.path.exists(mk.cache_path(kw)):
            done += 1
            continue
        items, from_cache, ok = mk.get_items(kw, ak, sk, state)
        if ok == "429":
            print("!!! 429 — 중단 (%d/%d 완료)" % (done, len(kws)))
            break
        if ok == "BUDGET":
            break
        done += 1
        if ok is True and items:
            hit += 1
            print("OK  %-26s %d건" % (kw, len(items)), flush=True)
        else:
            print("--  %-26s 0건" % kw, flush=True)

    state["logf"].close()
    # 아직 못 받은 것만 남겨 다음 실행에서 이어간다
    rest = [k for k in kws if not os.path.exists(mk.cache_path(k))]
    json.dump(rest, io.open(TODO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n호출 %d회 · 완료 %d · 결과있음 %d · 남은 검색어 %d"
          % (state["used"], done, hit, len(rest)))
    return 0


sys.exit(main())
