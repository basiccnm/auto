# -*- coding: utf-8 -*-
"""현재값 vs 네이버 규격별 단가 — 눈으로 대보는 표 (2026-07-20)

식봄 값을 자동으로 가져오지는 않는다(로그인 필요한 상용 사이트). 대표님이 화면을
띄워놓고 직접 대보실 수 있게, **한 재료의 규격별 단가를 한 줄에** 펼쳐서 보여준다.

🔴 base_unit이 다르면 비교하지 않는다.
   치킨무는 DB가 500원/개인데 네이버는 63,043원/kg이라 +12,509%로 찍혔다.
   가격이 틀린 게 아니라 **비교가 성립하지 않는 것**이라, 섞어두면 판단을 망친다.

  python scripts/naver_compare.py            콘솔
  python scripts/naver_compare.py --html     _preview/_naver_compare.html
"""
import argparse
import html
import os
import sqlite3
import statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "_naver_compare.html")
TIERS = ("소포장", "가정용", "대용량", "업소용")


def load():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT ingredient_key k, name, base_unit bu, is_retail ir,
        manual_price mp, wholesale_price wp, wholesale_basis wb, naver_unit nu, naver_title nt
        FROM ingredients WHERE naver_price IS NOT NULL ORDER BY name""").fetchall()
    out = []
    for r in rows:
        tier = {}
        for t in TIERS:
            per = [x[0] for x in con.execute(
                "SELECT per_unit FROM naver_offer WHERE ingredient_key=? AND tier=?",
                (r["k"], t))]
            if per:
                tier[t] = (round(statistics.median(per)), len(per))
        # 단위가 다르면 비교 불가로 표시만 하고 숫자는 안 만든다
        ok = (r["bu"] or "") == (r["nu"] or "") and not r["ir"]
        d = dict(r); d["tier"] = tier; d["cmp_ok"] = ok
        # 🔴 소포장을 섞으면 안 된다. 300g 팩은 원/kg이 1kg짜리의 2~4배라
        #    섞는 순간 '집밥 값'이 통째로 부풀어 치즈가 12,812 → 49,642가 됐다(2026-07-20).
        #    집밥 기준은 **가정용(600g~3kg)**. 그게 없을 때만 소포장으로 내려간다.
        d["home"] = (tier["가정용"][0] if "가정용" in tier
                     else (tier["소포장"][0] if "소포장" in tier else None))
        # 매장 축은 반대로 **큰 쪽**을 본다. 업소용이 있으면 그게 매입가에 제일 가깝다.
        d["big"] = (tier["업소용"][0] if "업소용" in tier
                    else (tier["대용량"][0] if "대용량" in tier else None))
        d["gap"] = ((d["home"] - r["mp"]) / r["mp"] * 100
                    if ok and r["mp"] and d["home"] else None)
        out.append(d)
    con.close()
    return out


def fmt(v, suffix="원"):
    return f"{v:,}{suffix}" if v else "—"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    rs = load()
    if not rs:
        print("수집된 게 없습니다 — python scripts/naver_shop.py --limit 30"); return

    cmpable = [r for r in rs if r["cmp_ok"] and r["gap"] is not None]
    skipped = [r for r in rs if not r["cmp_ok"]]
    cmpable.sort(key=lambda r: abs(r["gap"]), reverse=True)

    if not a.html:
        print(f'{"재료":<18}{"현재":>9}{"집밥":>9}{"차이":>8}{"대용량":>9}{"업소용":>9}')
        print("─" * 68)
        for r in cmpable:
            t = r["tier"]
            print(f'{r["name"][:17]:<18}{r["mp"]:>8,}원{fmt(r["home"]):>9}'
                  f'{r["gap"]:>+7.0f}%{fmt(t.get("대용량",[None])[0] if "대용량" in t else None):>9}'
                  f'{fmt(t.get("업소용",[None])[0] if "업소용" in t else None):>9}')
        close = [r for r in cmpable if abs(r["gap"]) <= 20]
        print(f'\n비교가능 {len(cmpable)}종 · ±20% 안 {len(close)}종 · 단위불일치 제외 {len(skipped)}종')
        return

    def row(r, cmpok=True):
        t = r["tier"]
        cells = ""
        for tn in TIERS:
            if tn in t:
                v, n = t[tn]
                cells += f'<td class="n">{v:,}<span class="m"> ({n})</span></td>'
            else:
                cells += '<td class="n m">—</td>'
        if cmpok:
            g = r["gap"]
            col = "#d33" if abs(g) >= 50 else ("#e8a33d" if abs(g) >= 20 else "#2a7")
            gs = f'<td class="n" style="color:{col};font-weight:800">{g:+.0f}%</td>'
        else:
            gs = '<td class="n m">비교불가</td>'
        # 매장 매입가 추정 = 대용량·업소용 중앙값 × 0.85 (대표님 실측 0.8~0.9의 가운데)
        est = f'{round(r["big"]*0.85):,}' if r["big"] else "—"
        return (f'<tr><td><b>{html.escape(r["name"])}</b>'
                f'<div class="m">{html.escape((r["nt"] or "")[:46])}</div></td>'
                f'<td class="n">{(r["mp"] or 0):,}<span class="m">/{html.escape(r["bu"] or "")}</span></td>'
                f'{cells}{gs}'
                f'<td class="n">{r["wp"] or 0:,}<div class="m">{html.escape(r["wb"] or "")}</div></td>'
                f'<td class="n" style="color:#06c">{est}</td></tr>')

    hdr = ("<tr><th>재료</th><th>현재<br>소매</th>"
           + "".join(f"<th>{t}</th>" for t in TIERS)
           + "<th>차이<br><span style='font-weight:400'>집밥 vs 현재</span></th>"
           + "<th>현재<br>도매</th><th>매장매입<br>추정 ×0.85</th></tr>")
    body = "".join(row(r) for r in cmpable)
    body2 = "".join(row(r, False) for r in skipped)

    doc = f"""<!doctype html><meta charset="utf-8"><title>네이버 규격별 시세 비교</title>
<style>body{{font-family:'Malgun Gothic',sans-serif;margin:22px;background:#fafafa;color:#222}}
h1{{font-size:19px;margin:0 0 6px}}h2{{font-size:15px;margin:26px 0 8px}}
p{{color:#666;font-size:12.5px;line-height:1.75;margin:0 0 14px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:12.5px}}
th,td{{border:1px solid #e5e5e5;padding:7px 9px;text-align:left;vertical-align:top}}
th{{background:#f2f2f2;position:sticky;top:0;font-size:11.5px;line-height:1.35}}
.n{{text-align:right;white-space:nowrap}}.m{{color:#999;font-size:10.5px;font-weight:400}}
</style>
<h1>네이버 쇼핑 — 규격별 단가</h1>
<p>단위는 전부 <b>원/kg(또는 원/L)</b>. 괄호는 잡힌 상품 수, 값은 <b>중앙값</b>입니다(최저가 아님).<br>
정확도순 상위 40개에서 뽑았습니다 — <b>싼 순이 아니라 많이 찾는 순</b>입니다.<br>
<b>식봄 값과 나란히 대보세요.</b> 식봄이 중간대라, 식봄보다 한참 비싸면 손질품·소용량이 잡힌 것이고
한참 싸면 다른 물건이 잡힌 것입니다.<br>
<span style="color:#2a7">■ ±20%</span> ·
<span style="color:#e8a33d">■ 20~50%</span> ·
<span style="color:#d33">■ 50%↑ 검토 필요</span></p>
<table>{hdr}{body}</table>

<h2>비교 제외 {len(skipped)}종 — 단위가 다르거나 시판 완제품</h2>
<p>DB가 <b>개당 가격</b>인데 네이버는 kg 단가라 비교가 성립하지 않습니다(치킨무 500원/개 vs 63,043원/kg).
가격이 틀린 게 아닙니다. 규격별 단가는 참고용으로 그대로 둡니다.</p>
<table>{hdr}{body2}</table>"""
    open(OUT, "w", encoding="utf-8").write(doc)
    print(f"생성: {OUT}")
    print(f"  비교가능 {len(cmpable)}종 / 단위불일치·시판 제외 {len(skipped)}종")


if __name__ == "__main__":
    main()
