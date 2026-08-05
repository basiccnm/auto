# -*- coding: utf-8 -*-
# _recipes/{slug}.md (OpenAI 생성물) → DB 반영 (2026-07-20)
#   지시서 §5: [1]~[6] 블록을 파싱 가능한 구조로 저장.
#
# 사람이 검수한 뒤 이 스크립트로 넣는다. 생성 즉시 라이브 반영은 하지 않는다.
#   python scripts/apply_recipe_md.py            # _recipes의 모든 md
#   python scripts/apply_recipe_md.py jjajangmyeon
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "_recipes")


def parse(md):
    """[1]~[6] 블록 분해 → dict."""
    out = {"serving": "", "ing_groups": [], "steps": [], "tips": [],
           "seo_title": "", "seo_intro": "", "faq": []}
    m = re.search(r"\((\d+인분[^)]*)\)", md.split("\n")[0])
    if m:
        # "1인분 기준"에서 '기준'을 떼어 저장한다 — 화면이 뒤에 '기준'을 또 붙여
        # "1인분 기준 기준"이 되던 문제(2026-07-20).
        out["serving"] = re.sub(r"\s*기준\s*$", "", m.group(1)).strip()

    blocks = {}
    cur_k = None
    for line in md.split("\n"):
        b = re.match(r"^\[(\d)\]", line.strip())
        if b:
            cur_k = int(b.group(1)); blocks[cur_k] = []
            continue
        if cur_k:
            blocks[cur_k].append(line)

    # [1] 재료 — 그룹 헤더 아래 재료 줄.
    #  ⚠️ 모델이 두 형식을 섞어 쓴다(2026-07-20 실측):
    #     A) "- 주재료" + 들여쓴 "  - 닭 300g"      B) "**주재료**" + "- 닭 300g"
    #     B를 못 읽어서 양념치킨이 재료 0종으로 파싱됐다. 둘 다 처리한다.
    group, items = None, []
    for line in blocks.get(1, []):
        s = line.rstrip()
        if not s.strip():
            continue
        indent = len(s) - len(s.lstrip())
        t = s.strip().lstrip("-").strip()
        bold = re.match(r"^\*\*(.+?)\*\*$", t)     # **주재료** 형식
        if bold:
            if group and items:
                out["ing_groups"].append({"group": group, "items": items})
            group, items = bold.group(1).strip(), []
            continue
        t = t.strip("*").strip()
        if not t:
            continue
        # 볼드 헤더를 쓰는 문서에선 재료 줄이 들여쓰기 없이 온다 → 분량이 있으면 재료로 본다
        has_amt = re.search(r"\d+(\.\d+)?\s*(kg|g|ml|L|개|장|모|봉|구|매)", t, re.I)
        if indent <= 1 and not has_amt:       # 그룹 헤더
            if group and items:
                out["ing_groups"].append({"group": group, "items": items})
            group, items = t, []
        else:                                # 재료 줄
            mm = re.match(r"^(.+?)\s+([\d,.]+\s*(?:kg|g|ml|L|개|장|모|봉))\b(.*)$", t)
            if mm:
                items.append({"name": mm.group(1).strip(),
                              "amount": mm.group(2).replace(" ", ""),
                              "note": mm.group(3).strip()})
            else:
                items.append({"name": t, "amount": "", "note": ""})
    if group and items:
        out["ing_groups"].append({"group": group, "items": items})

    # [2] 만드는 법 / [3] 팁 — 번호 줄
    def numbered(k):
        res, buf = [], ""
        for line in blocks.get(k, []):
            s = line.strip()
            if re.match(r"^\d+\.", s):
                if buf:
                    res.append(buf.strip())
                buf = re.sub(r"^\d+\.\s*", "", s)
            elif s:
                buf += " " + s
        if buf:
            res.append(buf.strip())
        return res
    out["steps"] = numbered(2)
    out["tips"] = numbered(3)

    # [4] 제목 / [5] 소개 — 첫 비어있지 않은 줄
    def firstline(k):
        for line in blocks.get(k, []):
            s = line.strip()
            if s and not s.startswith("-"):
                return s
        return ""
    out["seo_title"] = firstline(4)
    out["seo_intro"] = firstline(5)

    # [6] FAQ — 모델이 두 형식을 섞어 쓴다(2026-07-20 실측):
    #   A) "1. 질문" + 다음 줄 답   B) "**Q1. 질문**" + "A1. 답"   C) "- **질문**" + 들여쓴 답
    #   B·C를 못 읽어 양념치킨·탕수육·부대찌개 FAQ가 0건으로 나왔다.
    q, a = None, ""
    for line in blocks.get(6, []):
        bold_q = re.match(r"^\s*-?\s*\*\*(.+?)\*\*\s*$", line)   # C형: 볼드 한 줄이 곧 질문
        if bold_q:
            if q:
                out["faq"].append({"q": q, "a": a.strip()})
            q, a = bold_q.group(1).strip(), ""
            continue
        s = line.strip().strip("*").strip()
        if not s:
            continue
        mq = re.match(r"^(?:Q\s*\d*[.)]?|\d+[.)])\s*(.+)$", s)
        ma = re.match(r"^A\s*\d*[.)]?\s*(.+)$", s)
        if ma and q:                      # 답 줄
            a += (" " if a else "") + ma.group(1).strip()
        elif mq:                          # 질문 줄
            if q:
                out["faq"].append({"q": q, "a": a.strip()})
            q, a = mq.group(1).strip(), ""
        elif q:                           # 답의 이어지는 줄
            a += " " + s.lstrip("-").strip()
    if q:
        out["faq"].append({"q": q, "a": a.strip()})
    return out


def main():
    con = sqlite3.connect(DB); cur = con.cursor()
    cols = {r[1] for r in cur.execute("PRAGMA table_info(dishes)")}
    for c, t in (("tips_json", "TEXT"), ("faq_json", "TEXT"),
                 ("seo_title", "TEXT"), ("seo_intro", "TEXT"),
                 ("ing_json", "TEXT"), ("recipe_serving", "TEXT")):
        if c not in cols:
            cur.execute(f"ALTER TABLE dishes ADD COLUMN {c} {t}")
            print(f"  + 컬럼: dishes.{c}")

    only = sys.argv[1] if len(sys.argv) > 1 else None
    n = 0
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        if only and slug != only:
            continue
        d = parse(open(os.path.join(SRC, fn), encoding="utf-8").read())
        r = cur.execute("SELECT id,name FROM dishes WHERE slug=?", (slug,)).fetchone()
        if not r:
            print(f"  !! dishes에 slug '{slug}' 없음 — 건너뜀")
            continue
        cur.execute("""UPDATE dishes SET recipe_steps=?, tips_json=?, faq_json=?,
            seo_title=?, seo_intro=?, ing_json=?, recipe_serving=? WHERE id=?""",
            ("\n".join(d["steps"]), json.dumps(d["tips"], ensure_ascii=False),
             json.dumps(d["faq"], ensure_ascii=False), d["seo_title"], d["seo_intro"],
             json.dumps(d["ing_groups"], ensure_ascii=False), d["serving"], r[0]))
        n += 1
        print(f"  ✅ {r[1]}({slug}): 단계 {len(d['steps'])} · 팁 {len(d['tips'])} · "
              f"FAQ {len(d['faq'])} · 재료그룹 {len(d['ing_groups'])} · {d['serving']}")
    con.commit(); con.close()
    print(f"반영 {n}건")


if __name__ == "__main__":
    main()
