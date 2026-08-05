# -*- coding: utf-8 -*-
"""메뉴판에서 **메뉴가 아닌 줄**을 걷어낸다. 2026-07-28

    python scripts/menu_board_clean.py            # 미리보기
    python scripts/menu_board_clean.py --apply

수집기가 목록 페이지를 «가격 줄 기준» 으로 자르다 보니 UI 글자·안내문·설명문이 섞였다.
실제로 본 것:

    » 본문 바로가기 / 공지사항 상세 / 등록일 : 2025-10-01
    신메뉴 ※ 매장마다 판매 가격이 상이 할 수 있습니다.
    마늘 간장 맛과 매콤한 맛이 어우러진        ← 설명문이 메뉴명 자리에
    소비자가 10,000원 / 판매가 10,000원      ← 라벨이 메뉴명 자리에
    585kcal / 1094~1233kcal                ← 칼로리
    [ESG] / 브랜드 ] / 제 3조 [약관의 효력 및 개정]

🔴 **메뉴판은 우리 무기다.** 「비밀번호 찾기 27,000원」 이 한 줄 섞이면
   그 브랜드 페이지 전체를 못 믿게 된다. 지우는 쪽이 남기는 쪽보다 안전하다.

⛔ 애매하면 지우지 않는다 — 진짜 메뉴를 지우면 되돌릴 수 없다.
   그래서 «확실한 쓰레기» 만 규칙으로 잡고, 지운 것은 전부 출력한다.
"""
import io
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# ① UI·안내문 — 메뉴명일 수 없는 말
RX_UI = re.compile(
    r"(비밀번호|로그인|회원가입|장바구니|바로가기|공지사항|등록일\s*[:：]|더보기|"
    r"매장찾기|매장 찾기|가까운 매장|정보공개서|개발자에게|검색 폼|검색된 내역|"
    # ⚠️ 「퀴즈」를 그냥 넣었더니 **「병맥주(카스레몬스퀴즈0.0)」** 가 지워졌다(2026-07-28).
    #    낱말 안에 묻힌 글자를 잡으면 진짜 메뉴가 날아간다 — 앞뒤를 함께 본다.
    r"이벤트|EVENT|깜짝\s*퀴즈|수험표|쿠폰 이벤트|약관|제\s*\d+\s*조|개인정보|"
    r"^\[?ESG\]?$|^(브랜드|신제품|프로모션|메뉴안내|열정가득|전체메뉴)\s*\]?$|"
    r"^(소비자가|판매가|정가|할인가|가격)\s*[:：]?$|^가격\s*[:：]|"
    r"본문 바로가기|퀵서베이|참여 감사)", re.I)

# ② 칼로리·중량만 있는 줄
RX_NUMONLY = re.compile(r"^[\d,~\s]+(kcal|칼로리|g|ml|개|인분)?$", re.I)

# ③ 설명문 — 메뉴명은 짧다. 문장 종결·조사로 끝나면 설명이다.
RX_SENT = re.compile(r"(하세요|합니다|입니다|드립니다|있습니다|없습니다|어우러진|가득한|"
                     r"담백한|상이 할 수|다양하고|참여 해보세요|찾은 한국의 맛)")

# ④ 「※」 로 시작하는 주석
RX_NOTE = re.compile(r"^\s*[※*＊]")

# ⑤ 🔴 **이름만 긁어온 줄**에서 나오는 쓰레기 (2026-07-28 `--names` 도입 후)
#    홈페이지 목록에 가격이 없으면 `anchor_labels` 폴백이 **링크 글자를 다 담는다.**
#    그래서 회사소개·홍보문구·이미지 alt·재료명이 메뉴로 들어왔다:
#        교촌     「알레르기 정보 보기」 「양파분」 「웨지감자 제품 이미지」
#        와플대학  「사회공헌 WAFFLE UNIV.」 「오시는길 OFFICE MAP」 「브랜드 아이덴티티」
#        맥도날드  「참을 수 없는 달콤 바삭함!」 「우리 쌀의 바삭한 매력!」
#    ⛔ 여기 걸린 이름에 나중에 가격을 붙이러 검색을 돌리면 그게 더 큰 낭비다.
RX_JUNK2 = re.compile(
    r"(제품\s*이미지$|이미지$|알레르기|영양\s*정보|성분\s*정보|원산지\s*표시|"
    r"사회공헌|오시는\s*길|OFFICE MAP|아이덴티티|IDENTITY|브랜드\s*스토리|"
    r"연혁|채용|창업|가맹|문의|고객의\s*소리|매장\s*안내|캠퍼스\s*찾기|"
    r"보기$|더보기$|안내$|소개$|찾기$|"
    r"^(외래어|영문|ENGLISH)\s*메뉴판)", re.I)

# ⑥ 홍보 문구 — 느낌표로 끝나거나 «~한 매력/맛» 꼴
RX_PROMO = re.compile(r"(!$|！$|매력!?$|출시!?$|리프레시|참을 수 없는|겉은 .*속은|"
                      r"^(NEW|신메뉴)\s|시즌 한정|한정 간식)")


# 🔴 **꼬리표만 떼면 살릴 수 있는 이름이 있다** (2026-07-28).
#    「새우튀김우동 자세히보기」 「웨지감자 제품 이미지」 는 진짜 메뉴에 링크 글자가 붙은 것이다.
#    통째로 지우면 그 메뉴가 사라진다 — **떼고 남는 게 메뉴면 살린다.**
RX_TAIL = re.compile(r"\s*(자세히\s*보기|제품\s*이미지|이미지|바로가기|더보기|보기)\s*$")


def strip_tail(name):
    t = (name or "").strip()
    for _ in range(3):                     # 「… 제품 이미지 보기」 처럼 겹칠 수 있다
        t2 = RX_TAIL.sub("", t).strip()
        if t2 == t:
            break
        t = t2
    return t


def junk_reason(name, price=None):
    t = (name or "").strip()
    if not t:
        return "빈 이름"
    # ⚠️ 길다고 지우면 **진짜 세트 메뉴**가 날아간다(2026-07-28):
    #    「BBQ 떡볶이+뿜치킹 BBQ볼+롱김말이(1개)+레몬보이 2」 16,000원 은 실제 메뉴다.
    #    가격이 붙어 있으면 남긴다 — 설명문에는 대개 가격이 안 붙는다.
    #    가격이 붙은 설명문(「맥도날드가 찾은 한국의 맛! 14,900원」)은 아래 RX_SENT 가 잡는다.
    if len(t) > 34 and not price:
        return "너무 길다(설명문)"
    if RX_UI.search(t):
        return "UI·안내문"
    if RX_NUMONLY.match(t):
        return "숫자·칼로리만"
    if RX_SENT.search(t):
        return "설명문"
    if RX_NOTE.match(t):
        return "※ 주석"
    # ⚠️ 아래 둘은 **가격이 붙은 줄에는 적용하지 않는다.**
    #    가격이 있다는 건 그 줄이 메뉴판 블록에서 나왔다는 뜻이라 진짜일 가능성이 높다.
    #    (「BBQ 떡볶이+…+레몬보이 2」 를 길다고 지웠던 실수와 같은 갈래)
    if not price:
        if RX_JUNK2.search(t):
            return "이름만 긁힌 쓰레기(안내·이미지·회사소개)"
        if RX_PROMO.search(t):
            return "홍보 문구"
    if not re.search(r"[가-힣A-Za-z]", t):
        return "글자가 없다"
    return None


def main():
    apply_ = "--apply" in sys.argv
    c = sqlite3.connect(DB, timeout=90)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    rows = cur.execute("""SELECT o.rowid rid, b.name bn, o.name, o.price, o.decided_at
                          FROM brand_menu_official o JOIN brands b ON b.id=o.brand_id
                          ORDER BY b.name""").fetchall()
    bad, fix = [], []
    for r in rows:
        # 사람이 확정한 행은 건드리지 않는다
        if r["decided_at"]:
            continue
        # ① 꼬리표만 떼서 살릴 수 있나 — 「새우튀김우동 자세히보기」 → 「새우튀김우동」
        s = strip_tail(r["name"])
        if s and s != (r["name"] or "").strip() and not junk_reason(s, r["price"]):
            fix.append((r, s))
            continue
        why = junk_reason(r["name"], r["price"])
        if why:
            bad.append((r, why))

    by = {}
    for r, why in bad:
        by.setdefault(r["bn"], []).append((r, why))
    print("공식 메뉴판 %d줄 중 **메뉴가 아닌 줄 %d개**\n" % (len(rows), len(bad)))
    for bn, v in sorted(by.items(), key=lambda x: -len(x[1])):
        print("● %-16s %d개" % (bn[:16], len(v)))
        for r, why in v[:8]:
            print("     · %-32s %-9s [%s]"
                  % (r["name"][:32], ("%s원" % format(r["price"], ",")) if r["price"] else "-", why))
        if len(v) > 8:
            print("     … %d개 더" % (len(v) - 8))

    if fix:
        print("\n― 꼬리표만 떼서 살리는 이름 %d개 ―" % len(fix))
        for r, s in fix[:10]:
            print("   %-34s → %s" % (r["name"][:34], s))
    if apply_:
        for r, s in fix:
            # 같은 이름이 이미 있으면 중복이 되니 지운다(꼬리표 있는 쪽이 사본이다)
            dup = cur.execute("""SELECT rowid FROM brand_menu_official
                                 WHERE brand_id=(SELECT brand_id FROM brand_menu_official
                                                 WHERE rowid=?) AND name=? AND rowid<>?""",
                              (r["rid"], s, r["rid"])).fetchone()
            if dup:
                cur.execute("DELETE FROM brand_menu_official WHERE rowid=?", (r["rid"],))
            else:
                cur.execute("UPDATE brand_menu_official SET name=? WHERE rowid=?", (s, r["rid"]))
        if bad:
            cur.executemany("DELETE FROM brand_menu_official WHERE rowid=?",
                            [(r["rid"],) for r, _ in bad])
        c.commit()
        left = cur.execute("SELECT COUNT(*) n FROM brand_menu_official").fetchone()["n"]
        print("\n✅ %d줄 삭제 · %d줄 이름 정리 · 남은 메뉴판 %d줄" % (len(bad), len(fix), left))
    elif bad or fix:
        print("\n미적용 — --apply")


if __name__ == "__main__":
    main()
