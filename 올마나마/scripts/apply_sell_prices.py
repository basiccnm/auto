# -*- coding: utf-8 -*-
# 메뉴 판매가 실검증 반영 (2026-07 웹서치 8그룹)
#  1) scratchpad/sellverify_*.json 병합 → data/research/sell_prices.json (영구 기록: 출처·기준 포함)
#  2) confidence high/med & verified 존재 & 차이 있음 → menus.sell_price 갱신 (판매가는 소액 차이도 반영)
#  3) 원가율 재계산은 compute_line_costs.py 재실행으로
#  4) _preview/_sell_audit.html 검수표
import sqlite3, json, glob, os, sys, html

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SP = r"C:\Users\hardb\AppData\Local\Temp\claude\C--Users-hardb-Desktop--------------API\42c5a406-b4c6-4c3f-9036-4a06231e1eeb\scratchpad"
OUT_JSON = os.path.join(BASE, "data", "research", "sell_prices.json")
OUT_HTML = os.path.join(BASE, "_preview", "_sell_audit.html")
DRY = "--dry" in sys.argv
def esc(s): return html.escape(str(s)) if s is not None else ""

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
items = []
for fp in sorted(glob.glob(os.path.join(SP, "sellverify_*.json"))):
    grp = os.path.basename(fp)[11:-5]
    try: data = json.load(open(fp, encoding="utf-8"))
    except Exception as e: print("ERR", fp, e); continue
    for it in data:
        it["_group"] = grp; items.append(it)

applied, hold, keep = [], [], []
for it in items:
    mid = it.get("menu_id"); v = it.get("verified"); cu = it.get("current")
    conf = (it.get("confidence") or "low").lower()
    if conf == "med": conf = "medium"
    row = cur.execute("SELECT sell_price FROM menus WHERE id=?", (mid,)).fetchone()
    if not row:
        hold.append((it, "menu_id 없음")); continue
    now = row["sell_price"] or 0
    if v is None:
        hold.append((it, "확인 실패 → 기존값 유지")); continue
    if conf == "low":
        hold.append((it, f"low 신뢰 (제안 {v:,})")); continue
    if v == now:
        keep.append((it, "일치")); continue
    if not DRY:
        cur.execute("UPDATE menus SET sell_price=? WHERE id=?", (v, mid))
    applied.append((mid, it.get("brand",""), it.get("menu",""), now, v, it))
if not DRY: con.commit()

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
json.dump({"surveyed_at": "2026-07-16", "note": "판매가 웹서치 전수검증(8그룹). basis=배달앱/공식/매장.",
           "items": items,
           "applied": [{"menu_id": m, "brand": b, "menu": n, "old": o, "new": v} for m, b, n, o, v, _ in applied]},
          open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def tr(cls, it, old, new, status):
    link = f'<a href="{esc(it.get("source",""))}" target=_blank>출처</a>' if it.get("source") else ""
    new_s = f"<b>{new:,}</b>" if isinstance(new, int) else "-"
    old_s = f"{old:,}" if isinstance(old, int) else "-"
    return (f'<tr class="{cls}"><td class=n>{esc(it.get("brand",""))}</td><td class=m>{esc(it.get("menu",""))}</td>'
            f'<td class=r>{old_s}</td><td class=r>{new_s}</td><td>{esc(it.get("basis",""))}</td>'
            f'<td class=s>{link} {esc(it.get("confidence",""))}</td><td class=note>{esc(status)} {esc((it.get("note") or "")[:60])}</td></tr>')
rows = []
for m, b, n, o, v, it in sorted(applied, key=lambda x: -abs(x[4]-x[3])):
    pct = (v-o)/o*100 if o else 0
    rows.append(tr("ok", it, o, v, f"✅ {pct:+.0f}%"))
for it, why in hold: rows.append(tr("hd", it, it.get("current"), it.get("verified"), f"⏸ {why}"))
for it, why in keep: rows.append(tr("", it, it.get("current"), it.get("verified"), "· 일치"))

open(OUT_HTML, "w", encoding="utf-8").write(f"""<!doctype html><meta charset=utf-8><title>판매가 전수검증 · 얼마남아</title>
<style>body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#f5f6f8;margin:0;padding:20px;color:#1a1d21}}
.wrap{{max-width:1050px;margin:0 auto}}h1{{font-size:20px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:12.5px}}
th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid #eee;vertical-align:top}}
th{{background:#eef2f7;font-size:12px;color:#555}}
td.n{{font-weight:700;white-space:nowrap}}td.m{{white-space:nowrap}}
td.r{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}td.note{{font-size:11.5px;color:#666}}
tr.ok{{background:#f2fbf5}}tr.hd{{background:#fff8ec}}
</style><div class=wrap><h1>🏷️ 판매가 전수검증 (2026-07-16 웹서치)</h1>
<p style="font-size:13px;color:#555">✅변경 {len(applied)} · ⏸보류(미확인/low) {len(hold)} · 일치 {len(keep)} / 총 {len(items)}. 원본: data/research/sell_prices.json</p>
<table><tr><th>브랜드</th><th>메뉴</th><th>이전</th><th>검증가</th><th>기준</th><th>출처</th><th>상태</th></tr>
{''.join(rows)}</table></div>""")

print(f"{'[DRY] ' if DRY else ''}변경 {len(applied)} / 보류 {len(hold)} / 일치 {len(keep)} (총 {len(items)})")
for m, b, n, o, v, _ in sorted(applied, key=lambda x: -abs(x[4]-x[3]))[:25]:
    print(f"  {b} {n}: {o:,} → {v:,}")
con.close()
