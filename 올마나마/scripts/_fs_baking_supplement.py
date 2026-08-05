# -*- coding: utf-8 -*-
"""베이킹/제과제빵 재료 보완 수집 (일회성).

식봄에는 '제과제빵/베이킹' 전용 대분류가 없다(루트 1~478 전수 확인, 2026-07-25).
베이킹 재료는 기존 카테고리에 흩어져 있고 대부분 이미 163개 잎에 포함됐다:
  밀가루 487·부침가루 490·튀김가루 491·빵가루 493·전분 495·콩가루 488 (285>486)
  버터 318·잼 316·꿀 317·시럽 319 (285>291) / 설탕 234·물엿 235·올리고당 236 (209>214)
  치즈 148·크림치즈 149·유가공품 150 (114>121, 생크림·휘핑 여기) / 빵 320 (285>292)
기존 6개 루트 밖이라 빠진 베이킹 잎만 여기서 추가한다.
"""
import json, os, sys, time, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foodspring_collect as fc

sys.stdout.reconfigure(encoding="utf-8")
OUTDIR = fc.OUTDIR
GAP = 2.0
JSON_PATH = os.path.join(OUTDIR, "_가공카테고리.json")
MD_PATH = os.path.join(OUTDIR, "_가공카테고리_트리.md")

# 기존 6루트 밖의 베이킹 관련 잎만. (label, nid)
BAKING_LEAVES = [
    ("베이킹_초콜릿", 334),   # 322 스낵.안주류 > 325 캔디.젤리.초코렛.껌 > 334 초코렛
    ("베이킹_우유", 381),     # 336 커피.차.음료.생수 > 347 우유.라떼류... > 381 우유
    ("베이킹_씨리얼", 328),   # 322 > 323 일반스낵.강냉이.씨리얼 > 328 씨리얼
]

# 이미 수집된 잎 중 베이킹 재료가 섞여 있는지 확인할 키워드
CHECK_KW = ["생크림", "휘핑", "이스트", "베이킹파우더", "베이킹 파우더", "베이킹소다",
            "코코아", "제빵", "제과", "생지", "박력", "강력", "슈가파우더", "슈거파우더",
            "아몬드가루", "마가린", "쇼트닝"]


def main():
    out = json.load(open(JSON_PATH, encoding="utf-8"))
    md_add = ["\n## 베이킹/제과제빵 (전용 대분류 없음 — 흩어져 있음)\n",
              "식봄에 '제과제빵/베이킹' 전용 루트 카테고리는 없음(루트 1~478 전수 확인).\n",
              "대부분 기존 잎에 포함. 기존 6루트 밖 베이킹 잎만 추가 수집:\n"]
    for label, nid in BAKING_LEAVES:
        try:
            total, rows = fc.cat_search(nid)
        except urllib.error.HTTPError as e:
            print("  !! %s(nid %d) HTTP %s — 중단" % (label, nid, e.code)); break
        except Exception as e:
            print("  !! %s(nid %d) %s" % (label, nid, e)); time.sleep(GAP); continue
        out[label] = rows
        priced = [r for r in rows if r["won_per_kg"]]
        md_add.append("- **%s** (nid %d) · 총%d·파싱%d\n" % (label, nid, total, len(priced)))
        print("%-16s(nid %3d) 총%4d·파싱%3d" % (label, nid, total, len(priced)), flush=True)
        time.sleep(GAP)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 기존 수집분에서 베이킹 키워드가 어느 잎에 들어있는지 확인
    print("\n[베이킹 키워드 커버리지 — 이미 수집된 잎 안에서]")
    md_add.append("\n### 베이킹 키워드가 포함된 기존 잎(확인)\n")
    for kw in CHECK_KW:
        hits = {}
        for label, rows in out.items():
            c = sum(1 for r in rows if kw.replace(" ", "") in r["name"].replace(" ", ""))
            if c:
                hits[label] = c
        if hits:
            top = sorted(hits.items(), key=lambda x: -x[1])[:4]
            s = ", ".join("%s(%d)" % (l, c) for l, c in top)
            print("  %-12s → %s" % (kw, s))
            md_add.append("- `%s`: %s\n" % (kw, s))
        else:
            print("  %-12s → 없음" % kw)
            md_add.append("- `%s`: (없음)\n" % kw)

    with open(MD_PATH, "a", encoding="utf-8") as f:
        f.writelines(md_add)
    print("\n→ 베이킹 보완 완료. 총 잎 %d개" % len(out))


if __name__ == "__main__":
    main()
