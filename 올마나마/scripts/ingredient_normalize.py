# -*- coding: utf-8 -*-
"""재료 이름·분류를 대표 규칙대로 정리한다. 2026-08-03

**왜** — 하루 종일 같은 것을 반복해서 물어봤다. 규칙은 이미 다 나왔는데 코드에 없어서
매번 손으로 했다. 대표: *"지금 내가 이야기한 걸 토대로 분류하고 쪼개고 나누고 해라.
이름 변경할 건 하고 다 스크립트 만들어서 진행해라. 이제 그만 물어보고"*

담은 규칙 (2026-08-03 대표 확정)
  ① **띄어쓰기 없앤다** — `다진 소고기` → `다진소고기`. 괄호 안은 그대로.
  ② **실제 쓰는 말이 주명칭** — `붉은고추`→`홍고추`. 옛 이름은 별칭으로 남긴다.
  ③ **값이 다른 물건은 쪼갠다** — 밀가루(강력·중력·박력)·설탕(흰·황·흑)·소금(꽃·천일·맛·구운)
     ·식초(양조·현미·사과)·마늘(깐·다진·가루·흑)·고추(풋·오이·청양·꽈리·홍)
  ④ **가공형태가 다르면 다른 재료** — 즙·가루·분말·퓨레·시럽은 원물에 붙이지 않는다
     (`흑마늘즙`≠`다진마늘`, `마늘가루`≠`다진마늘`)
  ⑤ **분류(subcat)는 32개로 통일** — `양념·소스`/`소스·드레싱` 처럼 갈린 것을 합친다
  ⑥ **제철 재료는 「없는 것」이 아니다** — `ingredient_seasonal` 표로 관리

    python scripts/ingredient_normalize.py           # 미리보기
    python scripts/ingredient_normalize.py --apply
"""
import collections
import os
import re
import shutil
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recipe_mapping import normalize          # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ⑤ 분류 통일 — 갈린 것을 합친다
SUBCAT = {
    "가공식품/가루·전분": "가공식품/분말·가루", "가공식품/곡물": "농산물/곡물",
    "가공식품/기름": "가공식품/유지", "조미료/기름": "가공식품/유지",
    "가공식품/두부": "가공식품/두부·묵", "가공식품/떡": "가공식품/면·떡",
    "가공식품/면류": "가공식품/면·떡", "가공식품/수산": "가공식품/수산가공",
    "가공식품/양념·소스": "가공식품/소스·드레싱", "가공식품/양념·다대기": "가공식품/소스·드레싱",
    "조미료/양념": "가공식품/소스·드레싱", "가공식품/장·조미료": "가공식품/장류",
    "가공식품/제빵": "가공식품/빵·디저트", "가공식품/빙과": "가공식품/빵·디저트",
    "가공식품/음료": "가공식품/커피·음료", "가공식품/육가공": "가공식품/햄·소시지",
    "수산가공/어묵": "가공식품/수산가공", "수산물/가공수산": "가공식품/수산가공",
    "수산물": "수산물/기타", "농산물/가공채소": "농산물/채소", "채소": "농산물/채소",
    "농산물/버섯·견과": "농산물/견과", "축산물": "축산물/기타",
    "축산물/가공육": "가공식품/햄·소시지", "기타/소모품": "포장·소모품",
}

# ③ 쪼개진 재료가 제대로 있는지 검사할 묶음
SPLIT_GROUPS = {
    "밀가루": ("밀가루강력분", "밀가루중력분", "밀가루박력분"),
    "전분": ("옥수수전분", "감자전분", "고구마전분"),
    "설탕": ("설탕", "황설탕", "흑설탕"),
    "간장": ("간장", "진간장", "국간장", "양조간장"),
    "식초": ("식초", "양조식초", "현미식초", "사과식초"),
    "술": ("맛술", "청주", "미림"),
    "소금": ("꽃소금", "천일염", "맛소금", "구운소금"),
    "고추": ("풋고추", "오이고추", "청양고추", "꽈리고추", "홍고추"),
    "마늘": ("깐마늘", "다진마늘", "마늘가루", "흑마늘"),
    "고구마": ("고구마", "밤고구마", "호박고구마"),
    "밤": ("밤", "깐밤"),
    "올리브유": ("올리브유엑스트라버진", "올리브오일압착유"),
}

# ④ 가공형태 — 원물에 붙이면 안 되는 꼬리말.
#    ⚠️ 이름에 그 말이 이미 있으면(`참깨가루`→`참깨가루`) 정상이다. **어근이 같을 때만** 잡는다.
#    실제 사고: `흑마늘즙`을 `다진마늘` 로, `마늘가루` 를 `다진마늘` 로 붙일 뻔했다.
PROCESSED_TAIL = re.compile(r"(즙|가루|분말|파우더|퓨레|시럽|잼)$")


def is_bad_alias(raw, name):
    """별칭이 «가공형태»인데 붙은 재료는 원물이면 True."""
    raw, name = (raw or "").strip(), (name or "").strip()
    if not PROCESSED_TAIL.search(raw) or PROCESSED_TAIL.search(name):
        return False
    root = PROCESSED_TAIL.sub("", raw).strip()          # 흑마늘즙 → 흑마늘
    if len(root) < 2:
        return False
    # 어근이 재료 이름에 통째로 들어가면 «같은 계열의 다른 형태» = 붙이면 안 된다
    return normalize(root) in normalize(name) or normalize(name) in normalize(root)


def squash(s):
    """① 낱말 사이 공백만 없앤다. 괄호 안은 건드리지 않는다."""
    return re.sub(r"(?<=[가-힣A-Za-z0-9])\s+(?=[가-힣A-Za-z0-9(])", "", s or "").strip()


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    if apply:
        bak = os.path.join(BASE, "data",
                           "eolmanama_bak_norm_%s.db" % time.strftime("%Y%m%d_%H%M%S"))
        shutil.copy(DB, bak)
        print("백업 → %s" % os.path.basename(bak))
        print()

    rows = c.execute("""SELECT ingredient_key k, name, display_name dn, subcat,
        wholesale_price wp FROM ingredients""").fetchall()
    print("재료 %d종" % len(rows))
    print()

    # ─ ① 띄어쓰기 ────────────────────────────────────────────
    taken = {r["name"] for r in rows}
    fixed = []
    for r in rows:
        new = squash(r["name"])
        if new == r["name"] or (new in taken and new != r["name"]):
            continue
        fixed.append((r["k"], r["name"], new))
        taken.discard(r["name"]); taken.add(new)
    print("① 띄어쓰기 없앨 재료 %d종" % len(fixed))
    for k, old, new in fixed[:8]:
        print("     %-22s %-24s → %s" % (k, old[:24], new))
    if apply:
        for k, old, new in fixed:
            c.execute("""UPDATE ingredients SET name=?, display_name=?, page_slug=?,
                         updated_at=datetime('now') WHERE ingredient_key=?""",
                      (new, new, "price_" + new, k))
            c.execute("""INSERT INTO ingredient_alias(alias_norm,alias_raw,ingredient_key,source,created_at)
                         VALUES(?,?,?,'normalize',date('now'))
                         ON CONFLICT(alias_norm) DO NOTHING""", (normalize(old), old, k))

    # ─ ⑤ 분류 통일 ──────────────────────────────────────────
    print()
    move = [(r["k"], r["subcat"], SUBCAT[r["subcat"]]) for r in rows
            if r["subcat"] in SUBCAT]
    print("⑤ 분류 합칠 재료 %d종 (%d → %d개)"
          % (len(move), len({r["subcat"] for r in rows}),
             len({SUBCAT.get(r["subcat"], r["subcat"]) for r in rows})))
    for old, new in list(dict.fromkeys((o, n) for _, o, n in move))[:8]:
        print("     %-24s → %s" % (old, new))
    if apply:
        for k, old, new in move:
            c.execute("UPDATE ingredients SET subcat=? WHERE ingredient_key=?", (new, k))

    # ─ 분류 없는 재료 ────────────────────────────────────────
    nosub = [r for r in rows if not (r["subcat"] or "").strip()]
    if nosub:
        print()
        print("⚠️ 분류가 빈 재료 %d종 — 손으로 채울 것" % len(nosub))
        for r in nosub[:10]:
            print("     %-22s %s" % (r["k"], r["dn"] or r["name"]))

    # ─ ③ 쪼개짐 검사 ────────────────────────────────────────
    print()
    print("③ 값이 다른 물건이 제대로 쪼개져 있나")
    have = {(r["dn"] or r["name"]): r["wp"] for r in rows}
    for label, members in SPLIT_GROUPS.items():
        miss = [m for m in members if m not in have]
        mark = "✅" if not miss else "⚠️"
        print("   %s %-8s %s" % (mark, label,
                                 " · ".join("%s %s" % (m, format(have[m] or 0, ","))
                                            for m in members if m in have)))
        if miss:
            print("        빠짐: %s" % " · ".join(miss))

    # ─ ④ 가공형태가 원물에 붙었나 ─────────────────────────────
    print()
    bad = []
    for r in c.execute("""SELECT a.alias_raw, a.ingredient_key, i.name FROM ingredient_alias a
                          JOIN ingredients i ON i.ingredient_key=a.ingredient_key"""):
        if is_bad_alias(r["alias_raw"], r["name"]):
            bad.append(((r["alias_raw"] or "").strip(), (r["name"] or "").strip()))
    print("④ 가공형태가 원물에 붙은 별칭 %d건  (즙·가루가 원물로 가면 원가가 틀린다)" % len(bad))
    for raw, nm in bad[:12]:
        print("     %-22s → %s" % (raw, nm))
    if apply and bad:
        for raw, _ in bad:
            c.execute("DELETE FROM ingredient_alias WHERE alias_raw=?", (raw,))
        print("     → %d건 제거" % len(bad))

    # ─ ⑥ 제철 ──────────────────────────────────────────────
    print()
    try:
        se = c.execute("SELECT name, season FROM ingredient_seasonal").fetchall()
        print("⑥ 제철 재료 %d종 — 「없는 것」이 아니다" % len(se))
        print("     " + " · ".join("%s(%s)" % (r["name"], r["season"]) for r in se))
    except sqlite3.OperationalError:
        print("⑥ ingredient_seasonal 표가 없다")

    # ─ 이름 겹침 ────────────────────────────────────────────
    print()
    dup = {k: v for k, v in collections.Counter(
        squash(r["name"]) for r in rows).items() if v > 1}
    print("이름 겹침 %d개%s" % (len(dup), (" — " + " · ".join(dup)) if dup else ""))

    if apply:
        c.commit()
        print()
        print("✅ 반영 완료 · 재료 %d종 · 분류 %d개"
              % (c.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0],
                 c.execute("SELECT COUNT(DISTINCT subcat) FROM ingredients").fetchone()[0]))
    else:
        print()
        print("→ 반영하려면 `--apply`")


if __name__ == "__main__":
    main()
