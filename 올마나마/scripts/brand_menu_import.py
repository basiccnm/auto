# -*- coding: utf-8 -*-
"""수집 세션이 만든 **JSON 한 장**을 메뉴판에 적재한다. 2026-07-28 신설

왜 JSON 을 거치나
----------------
수집은 세션을 따로 띄워 여러 브랜드를 동시에 돌린다. 그 세션들이 각자 DB 에 쓰면
① `database is locked` · ② 누가 무엇을 넣었는지 또 모르게 된다(출처 없는 행 113건이 그렇게 생겼다).
그래서 **수집 세션은 파일만 만들고, DB 는 여기서만 건드린다.**

    python scripts/brand_menu_import.py data/brand_menu_list/burgerking.json          # 검사만
    python scripts/brand_menu_import.py data/brand_menu_list/burgerking.json --apply  # 적재

JSON 모양 — `브랜드메뉴판등록방식.md` 와 같다
    {"brand","slug","source","collected_at",
     "cats":[{"name","parent"(상위 경로|null),"ext_id"}],      ← 화면 순서 그대로, 상위 먼저
     "menus":[{"name","price"(없으면 null),"price_source", …,
               "cats":[["카테고리 경로", 그_안에서의_자리], …]}]}

⛔ 검사에서 걸린 줄은 **넣지 않고 목록으로 보여준다.** 조용히 통과시키면 화면에 그대로 나간다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

# 메뉴가 아닌 줄 — 실제로 들어와 있던 것들에서 뽑은 규칙
#   `새로 나왔어요!` · `안주에 제격, 아이들 간식으로 제격` · `NEW` · `정상가` · `상품명` · `2026년 07월 23일`
RX_NAV = re.compile(r"^(NEW|BEST|HOT|추천순|추천메뉴|전체|정상가|합계|최저|할인|상품명|상품금액|"
                    r"번역|주문 금액|Large|Regular|모두 닫기|판매가|1마리|억원)$", re.I)
RX_DATE = re.compile(r"^\d{4}년|^\d{4}[-.]\d{2}")


def junk(nm, top_names):
    """왜 메뉴가 아닌지 — 이유를 돌려준다(없으면 None). 이유를 남겨야 나중에 규칙을 고칠 수 있다.

    🔴 카테고리 이름과 같은지는 **최상위 탭 이름만** 본다.
       하위 카테고리 이름은 실제 메뉴명인 경우가 많다 — 버거킹 「와퍼」, bhc 「뿌링클」.
       걸러야 할 건 BBQ `피자&버거 5,000원` 처럼 **탭이 메뉴 행으로 둔갑한 것**이다.
    """
    s = (nm or "").strip()
    if not s:
        return "빈 이름"
    if RX_NAV.match(s):
        return "네비게이션·UI 문자열"
    if RX_DATE.match(s):
        return "날짜"
    # 🔴 «탭 이름과 같으면 버린다» 는 **버리지 않고 알리기만** 한다 (2026-07-28 지코바).
    #    지코바 「양념치킨」·「소금구이치킨」은 탭 이름이면서 **가격·중량이 있는 진짜 메뉴**다.
    #    원래 겨냥한 건 BBQ `피자&버거 5,000원` 처럼 범용 수집기가 탭을 메뉴로 밀어 넣은 경우인데,
    #    전용 수집기 JSON 에는 그런 게 안 들어온다. 버리면 진짜 메뉴가 사라진다.
    if s in top_names:
        return "!탭 이름과 같다 — 눈으로 확인할 것"
    # 🔴 «쉼표가 있으면 문장» 은 **진짜 메뉴를 죽인다** (2026-07-28 교촌).
    #    「아, 귀한 먹태[홀전용메뉴]」 · 「문베어 윈디힐 라거 (500ml CAN, KEG)」 가 걸렸다.
    #    문장은 **끝맺음**으로 알아본다 — `새로 나왔어요!` · `마늘 치킨이 아닙니다.`
    if re.search(r"[.!?]$|(?:니다|세요|어요|네요|아요)$", s):
        return "문장(설명문·홍보문구)"
    # 🔴 길이만으로 자르면 **세트·규격 메뉴가 죽는다.**
    #    `황금올리브치킨 반마리+BBQ 감자튀김+…` 는 40자 넘는 실제 메뉴고,
    #    `문베어 짙은밤 페일에일 (500ml CAN)` 은 규격이 붙어 길어진 것이다.
    #    배스킨라빈스 `(Lessly Edition) 엄마는 외계인 (트리플 주니어)` 도 규격이 붙어 길어진 실제 메뉴다.
    if len(s) >= 30 and not re.search(
            r"[+＋]|세트|콤보|박스|패키지|PICK|SET|\d+\s*(?:ml|L|g|kg|PCS|조각|개|인분)|CAN|KEG"
            # 사이즈·규격 표기 — 이게 붙으면 길어도 메뉴다
            r"|싱글|더블|트리플|주니어|레귤러|파인트|패밀리|하프갤론|쿼터|킹\b"
            r"|\b[SMLR]\b|라지|미디엄|스몰|톨|그란데|벤티|케이크|Edition",
            s, re.I):
        return "너무 길다(설명문 의심)"
    return None


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    apply_ = "--apply" in sys.argv
    force = "--force" in sys.argv          # 검사에 걸린 줄까지 넣는다(사람이 확인했을 때만)
    d = json.load(io.open(path, encoding="utf-8"))

    cats = d.get("cats") or []
    menus = d.get("menus") or []
    print("■ %s (%s) — 카테고리 %d · 메뉴 %d"
          % (d.get("brand"), d.get("slug"), len(cats), len(menus)))
    # 🔴 **탭이 없는 브랜드가 실제로 있다** (2026-07-28 60계치킨: 메뉴판이 한 줄로 쭉 이어진다).
    #    이때 카테고리를 하나 만들어 담는다 — 화면에는 탭이 **하나면 탭바가 안 나오므로**
    #    지어낸 이름이 눈에 띄지 않고, 대신 **브랜드가 깔아둔 순서**를 그대로 지킬 수 있다.
    #    카테고리를 안 만들면 표준 탭 폴백으로 떨어져 우리가 「치킨/사이드」를 지어내게 된다.
    if not cats and menus:
        cats = [{"name": "메뉴", "parent": None}]
        for m in menus:
            m["cats"] = ["메뉴"]
        print("  · 탭이 없는 메뉴판 — 하나로 묶는다(화면엔 탭바가 안 나온다)")
    elif not cats:
        print("  ⚠️ 카테고리도 메뉴도 없다 — 수집을 다시 볼 것")

    # ① 카테고리 — 경로를 만들고 상위가 먼저 나오는지 본다
    # 🔴 최상위인지는 **`parent` 로만** 판단한다 (2026-07-28 자담).
    #    경로에 `/` 가 있는지로 세면 「피자/파스타」 처럼 **이름에 `/` 가 든 탭**이
    #    하위 카테고리로 잘못 잡힌다. 브랜드가 쓰는 말은 우리 구분자를 피해 가지 않는다.
    paths, bad, top = [], [], []
    for ct in cats:
        nm = (ct.get("name") or "").strip()
        par = (ct.get("parent") or "").strip() or None
        if not nm:
            bad.append("이름 없는 카테고리")
            continue
        if par and par not in paths:
            bad.append("상위가 먼저 안 나온다: %s (상위 %s)" % (nm, par))
        p = "%s/%s" % (par, nm) if par else nm
        if p in paths:
            bad.append("카테고리 중복: %s" % p)
        paths.append(p)
        if not par:
            top.append(p)
    names = set(top)
    print("  탭 %d개: %s" % (len(top), " → ".join(top)))
    sub = [p for p in paths if p not in top]
    if sub:
        print("  하위 %d개: %s%s" % (len(sub), ", ".join(sub[:8]), " …" if len(sub) > 8 else ""))

    # ② 메뉴 — 메뉴가 아닌 줄, 카테고리 못 찾는 줄
    ok, drop, warn, orphan = [], [], [], 0
    for m in menus:
        nm = (m.get("name") or "").strip()
        why = junk(nm, names)
        if why and why.startswith("!"):      # 알리기만 — 버리지 않는다
            warn.append((nm, why[1:]))
            why = None
        if why and not force:
            drop.append((nm, why))
            continue
        cs = []
        for e in (m.get("cats") or []):
            cp, pos = (e, None) if isinstance(e, str) else (e[0], e[1])
            if cp not in paths:
                bad.append("없는 카테고리를 가리킨다: %s → %s" % (nm, cp))
                continue
            cs.append((cp, pos) if pos is not None else cp)
        if not cs:
            orphan += 1
        it = dict(m)
        it["cats"] = cs
        it["category"] = " · ".join(dict.fromkeys(
            p for p in ((c[0] if isinstance(c, tuple) else c) for c in cs) if p in top))
        ok.append(it)

    # 🔴 **같은 이름에 가격이 여럿인 브랜드가 있다** (2026-07-28 피자마루).
    #    `페퍼로니 피자` 가 클래식 10,900 / 골드&바이트 15,900 / 퍼스널 4,900 로 셋이다 —
    #    사이즈·엣지가 다른 **다른 제품**인데 브랜드는 이름을 안 바꾸고 **카테고리로 구분**한다.
    #    우리 키는 `(brand_id, name)` 이라 셋을 못 담는다 → 그대로 넣으면 UNIQUE 로 죽는다.
    #    ⛔ 하나만 남기면 나머지 가격이 사라진다. 그래서 **브랜드가 쓰는 카테고리 이름을 빌려** 구분한다.
    #    첫 번째는 이름을 그대로 둔다 — 우리 원가 메뉴와의 연결(`menu_id`)이 끊기지 않게.
    seen_nm, renamed = {}, []
    for it in ok:
        nm = it["name"]
        seen_nm[nm] = seen_nm.get(nm, 0) + 1
        if seen_nm[nm] == 1:
            continue
        cat = next((c[0] if isinstance(c, tuple) else c) for c in it["cats"]) if it["cats"] else ""
        cat = cat.split("/")[-1]
        new = "%s (%s)" % (nm, cat) if cat else "%s (%d)" % (nm, seen_nm[nm])
        while new in seen_nm:
            new += "."
        seen_nm[new] = 1
        renamed.append((nm, new, it.get("price")))
        it["name"] = new
    if renamed:
        print("  ↔ 이름이 겹쳐 카테고리로 구분한 %d줄 (브랜드가 같은 이름을 여러 규격에 쓴다):" % len(renamed))
        for a, b, p in renamed[:8]:
            print("     · %-22s → %-30s %s원" % (a[:22], b[:30], format(p or 0, ",")))

    n_price = sum(1 for m in ok if m.get("price"))
    print("  메뉴 %d개 채택 · 가격 있는 것 %d · 카테고리 없는 메뉴 %d" % (len(ok), n_price, orphan))
    if drop:
        print("  ⛔ 메뉴가 아니라 판단해 뺀 %d줄:" % len(drop))
        for nm, why in drop[:12]:
            print("     · %-34s %s" % (nm[:34], why))
        if len(drop) > 12:
            print("     … 외 %d줄" % (len(drop) - 12))
        print("     (정말 메뉴면 --force 로 넣는다)")
    if warn:
        print("  ⚠️ 넣긴 넣었지만 확인이 필요한 %d줄:" % len(warn))
        for nm, why in warn[:8]:
            print("     · %-34s %s" % (nm[:34], why))
    if bad:
        print("  ⚠️ 구조 문제 %d건:" % len(bad))
        for x in bad[:10]:
            print("     · %s" % x)
    if bad and apply_ and not force:
        raise SystemExit("구조 문제가 있어 적재하지 않는다. 수집 JSON 을 고치거나 --force")

    if not apply_:
        print("\n(검사만 — 넣으려면 --apply)")
        return

    c = store.connect()
    store.ensure(c)
    bid = store.brand_id(c, slug=d.get("slug"), name=d.get("brand"))
    tree = [{"name": (ct.get("name") or "").strip(),
             "parent": (ct.get("parent") or "").strip() or None,
             "ext_id": ct.get("ext_id")} for ct in cats if (ct.get("name") or "").strip()]
    store.replace_brand(c, bid, tree, ok,
                        collector="import:" + os.path.basename(path))
    c.close()


if __name__ == "__main__":
    main()
