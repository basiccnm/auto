# -*- coding: utf-8 -*-
# 재료 단가 실시세 반영 (2026-07-16 웹서치 4그룹 + KAMIS 수산 교차검증)
#  1) scratchpad/prices_*.json 병합 → data/research/ingredient_prices.json (영구 단가표)
#  2) 적용 정책: confidence high/med(medium) & 변동 ±10%↑ → 적용 / low·특수 → 보류 / 나머지 → 유지
#     - live_check 그룹은 '계란 단위버그'만 적용(닭 6,000은 도매기준이라 보류)
#     - live 재료 교정 시 manual 전환+KAMIS 코드 해제(크론이 안 덮게)
#  3) _preview/_price_audit.html 검수표 생성
import sqlite3, json, glob, os, sys, html

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
SP = r"C:\Users\hardb\AppData\Local\Temp\claude\C--Users-hardb-Desktop--------------API\42c5a406-b4c6-4c3f-9036-4a06231e1eeb\scratchpad"
OUT_JSON = os.path.join(BASE, "data", "research", "ingredient_prices.json")
OUT_HTML = os.path.join(BASE, "_preview", "_price_audit.html")
DRY = "--dry" in sys.argv
def esc(s): return html.escape(str(s)) if s is not None else ""

# 조사항목 → DB 키 매핑 (key 또는 name 기준, 리스트=여러 키에 동일 적용)
ALIAS = {
    "tuna_cube": ["x_1e5f6864ee", "x_216cb905a2", "x_cda2501f42"],
    "octopus_slice": ["x_0466d85de0"],
    "squid_body": ["x_05a19b44fc", "x_9a434b1c9e", "x_a91c620ea2", "x_eae7691f7c", "x_ff1a467c6d"],
    "octopus_small": ["x_f71eeb8b7b"],
    "egg": ["egg_fresh"],
    "소곱창/대창/염통 (한우곱창/대창)": ["x_c213e61e77"],
    "자숙 소곱창(전골용)": ["x_10a10b8b9e"],
    "자숙 소막창": ["x_ed9421040a"],
    "자숙 특양(양깃머리)": ["x_ca5d31e548"],
    "감자탕 돈뼈(등뼈)": ["x_2458074f8e"],
    "머리고기/순대/돈족 세트류": ["x_a0ada5ee05", "x_99df42166b", "x_d191a7196b"],
    "전지돈육(앞다리)": ["x_1294333d76"],
    "양지 슬라이스(쌀국수용)": ["x_0efb9306fb", "x_46abf4267c"],
}
HOLD_KEYS = {"raw_chicken_10"}          # 도매(마리당) 기준 제안 → 소매 컨셉과 달라 보류
SKIP_ITEMS = {("processed", "egg")}      # 계란 중복(30구가) — live_check 쪽만 사용

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
valid = {r[0] for r in cur.execute("SELECT ingredient_key FROM ingredients")}

items = []
for fp in sorted(glob.glob(os.path.join(SP, "prices_*.json"))):
    grp = os.path.basename(fp)[7:-5]
    for it in json.load(open(fp, encoding="utf-8")):
        it["_group"] = grp; items.append(it)

applied, hold, keep = [], [], []
for it in items:
    key = it.get("key"); name = it.get("name", ""); grp = it["_group"]
    rec = it.get("recommended"); conf = (it.get("confidence") or "low").lower()
    if conf == "med": conf = "medium"
    if (grp, key) in SKIP_ITEMS: continue
    keys = ALIAS.get(key) or ALIAS.get(name) or ([key] if key in valid else [])
    keys = [k for k in keys if k in valid]
    if not keys:
        hold.append((it, [], "키 매칭 실패")); continue
    if rec is None:
        keep.append((it, keys, "적정 판정(변경 없음)")); continue
    if key in HOLD_KEYS or keys[0] in HOLD_KEYS:
        hold.append((it, keys, f"보류: 도매기준 제안({rec:,}) — 소매 컨셉 재검토")); continue
    if conf == "low":
        hold.append((it, keys, f"보류: low 신뢰(제안 {rec:,})")); continue
    for k in keys:
        row = cur.execute("SELECT manual_price FROM ingredients WHERE ingredient_key=?", (k,)).fetchone()
        now = row["manual_price"] or 0
        if now and abs(rec - now) / now < 0.10:
            keep.append((it, [k], f"변동 10% 미만({now:,}→{rec:,})")); continue
        if not DRY:
            cur.execute("""UPDATE ingredients SET manual_price=?, type='manual',
                kamis_cat=NULL, kamis_item_code=NULL, ekape_item=NULL, markup_factor=1.0,
                updated_at=datetime('now') WHERE ingredient_key=?""", (rec, k))
        applied.append((k, name, now, rec, it))
if not DRY: con.commit()

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
json.dump({"surveyed_at": "2026-07-16",
           "note": "웹서치 4그룹 + KAMIS 수산(600) 교차검증. 단가=소비자 소매가 원/kg(빵류는 원/개).",
           "kamis_seafood_snapshot": "kamis_seafood_2026-07-15.json",
           "items": items,
           "applied": [{"key": k, "name": n, "old": o, "new": r} for k, n, o, r, _ in applied]},
          open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def tr(cls, key, name, old, new, basis, product, source, conf, status):
    old_s = f"{old:,}" if old else "-"
    new_s = f"<b>{new:,}</b>" if new else "-"
    link = f'<a href="{esc(source)}" target=_blank>출처</a>' if source else ""
    return (f'<tr class="{cls}"><td class=k>{esc(key)}</td><td class=n>{esc(name)}</td>'
            f'<td class=r>{old_s}</td><td class=r>{new_s}</td><td>{esc(basis or "")}</td>'
            f'<td class=p>{esc(product or "")}</td><td class=s>{link} {esc(conf or "")}</td>'
            f'<td class=note>{esc(status)}</td></tr>')
rows = []
for k, n, o, r, it in applied:
    rows.append(tr("ok", k, n, o, r, it.get("basis"), it.get("product"), it.get("source"), it.get("confidence"), "✅ 적용"))
for it, keys, why in hold:
    rows.append(tr("hd", ",".join(keys), it.get("name",""), it.get("current") or it.get("kamis_now") or 0,
                   it.get("recommended") or 0, it.get("basis"), it.get("product"), it.get("source"), it.get("confidence"), f"⏸ {why}"))
for it, keys, why in keep:
    rows.append(tr("", ",".join(keys), it.get("name",""), it.get("current") or it.get("kamis_now") or 0,
                   it.get("recommended") or 0, it.get("basis"), it.get("product"), it.get("source"), it.get("confidence"), f"· {why}"))

open(OUT_HTML, "w", encoding="utf-8").write(f"""<!doctype html><meta charset=utf-8><title>재료 단가 실시세 감사 · 얼마남아</title>
<style>body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#f5f6f8;margin:0;padding:20px;color:#1a1d21}}
.wrap{{max-width:1150px;margin:0 auto}}h1{{font-size:20px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:12.5px}}
th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid #eee;vertical-align:top}}
th{{background:#eef2f7;font-size:12px;color:#555}}
td.k{{font-family:monospace;font-size:10.5px;color:#888;max-width:150px;word-break:break-all}}td.n{{font-weight:700;white-space:nowrap}}
td.r{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
td.p{{color:#1a56b0;font-size:12px}}td.note{{font-size:11.5px;color:#666}}
tr.ok{{background:#f2fbf5}}tr.hd{{background:#fff8ec}}
</style><div class=wrap><h1>💰 재료 단가 실시세 감사 (2026-07-16)</h1>
<p style="font-size:13px;color:#555">✅적용 {len(applied)} · ⏸보류 {len(hold)} · 유지 {len(keep)} — 기준: 소비자 소매가(수입산 통상등급). 원본: data/research/ingredient_prices.json · KAMIS 수산 스냅샷 교차검증</p>
<table><tr><th>키</th><th>재료</th><th>이전</th><th>적용/제안가</th><th>기준</th><th>근거 상품</th><th>출처·신뢰</th><th>상태</th></tr>
{''.join(rows)}</table></div>""")

print(f"{'[DRY] ' if DRY else ''}적용 {len(applied)} / 보류 {len(hold)} / 유지 {len(keep)}")
for k, n, o, r, _ in applied:
    print(f"  {n:<20} {o:>8,} → {r:>8,}  ({k})")
con.close()
