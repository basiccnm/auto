# -*- coding: utf-8 -*-
"""식봄 포장·일회용품 카테고리 수집 (일회성) — 배달 원가용 용기값.

트리(2026-07-25 확인):
  450 포장용기.일회용품
    451 일회용 용기.컵   → 457 그릇 458 접시 459 도시락 460 컵 461 병 462 기타포장용기
    452 숟가락.젓가락...  → 463 숟가락 464 젓가락 465 포크 466 꼬지 467 이쑤시개 468 빨대
    453 봉투.박스.종이   → 469 비닐봉투 470 김장봉투 471 종이봉투 472 박스 473 종이 474 기타
    454 면장갑.특수장갑  → 475 면장갑 476 특수장갑
    455 일회용품 케이스  → 477 휴지케이스
    456 기타 일회용품    → 478 기타 일회용품
  420 주방용품 > 422 지퍼백.랩.호일.비닐장갑 → 429 지퍼백 430 크린백 431 롤백 432 랩 433 호일 434 비닐장갑

포장재는 매/장/개 단위라 won_per_kg 는 대개 null(정상). name·salePrice 가 핵심.
JSON 파일에만 쓴다. DB 는 안 건드린다.
"""
import json, os, sys, time, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foodspring_collect as fc

sys.stdout.reconfigure(encoding="utf-8")
OUTDIR = fc.OUTDIR
GAP = 2.0

# {대분류nid: (대분류명, {중분류nid: (중분류명, {잎nid: 라벨})})}
TREE = {
    450: ("포장용기.일회용품", {
        451: ("일회용 용기.컵", {457: "포장_일회용그릇", 458: "포장_일회용접시",
                                459: "포장_일회용도시락", 460: "포장_일회용컵",
                                461: "포장_일회용병", 462: "포장_기타포장용기"}),
        452: ("숟가락.젓가락.꼬지.빨대", {463: "포장_숟가락", 464: "포장_젓가락",
                                        465: "포장_포크", 466: "포장_꼬지",
                                        467: "포장_이쑤시개", 468: "포장_빨대"}),
        453: ("봉투.박스.종이", {469: "포장_비닐봉투", 470: "포장_김장봉투",
                                471: "포장_종이봉투", 472: "포장_박스", 473: "포장_종이",
                                474: "포장_봉투박스종이기타"}),
        454: ("면장갑.특수장갑", {475: "포장_면장갑", 476: "포장_특수장갑"}),
        455: ("일회용품 케이스", {477: "포장_휴지케이스"}),
        456: ("기타 일회용품", {478: "포장_기타일회용품"}),
    }),
    420: ("주방용품(포장 관련 가지만)", {
        422: ("지퍼백.랩.호일.비닐장갑", {429: "포장_지퍼백", 430: "포장_크린백",
                                        431: "포장_롤백", 432: "포장_랩", 433: "포장_호일",
                                        434: "포장_비닐장갑"}),
    }),
}


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    out = {}
    md = ["# 식봄 포장.일회용품 카테고리 트리 (2026-07-25) — 배달 용기 원가용\n",
          "구조: 대분류(nid) > 중분류(nid) > 잎(nid) · 총건수/파싱건수\n"]
    stop = False
    for root_nid, (root_name, mids) in TREE.items():
        md.append("\n## %s (nid %d)\n" % (root_name, root_nid))
        for mid_nid, (mid_name, leaves) in mids.items():
            md.append("- **%s** (nid %d)\n" % (mid_name, mid_nid))
            for leaf_nid, label in leaves.items():
                try:
                    total, rows = fc.cat_search(leaf_nid)
                except urllib.error.HTTPError as e:
                    print("  !! %s(nid %d) HTTP %s — 중단" % (label, leaf_nid, e.code))
                    stop = True; break
                except Exception as e:
                    print("  !! %s(nid %d) %s" % (label, leaf_nid, e))
                    md.append("    - %s (nid %d) · ERROR\n" % (label, leaf_nid))
                    time.sleep(GAP); continue
                out[label] = rows
                md.append("    - %s (nid %d) · 총%d·수집%d\n" % (label, leaf_nid, total, len(rows)))
                print("%-24s(nid %3d) 총%4d·수집%3d" % (label, leaf_nid, total, len(rows)),
                      flush=True)
                time.sleep(GAP)
            if stop:
                break
        if stop:
            break

    with open(os.path.join(OUTDIR, "_포장카테고리.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUTDIR, "_포장카테고리_트리.md"), "w", encoding="utf-8") as f:
        f.writelines(md)
    print("\n포장 잎 %d개 수집" % len(out))
    print("→ data/research/foodspring/_포장카테고리.json")
    print("→ data/research/foodspring/_포장카테고리_트리.md")
    if stop:
        print("!! 차단 징후로 중단됨 — 부분 저장")


if __name__ == "__main__":
    main()
