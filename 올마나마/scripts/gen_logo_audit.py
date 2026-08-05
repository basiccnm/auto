# -*- coding: utf-8 -*-
# 로고 검수 시트: _preview/_logo_audit.html
#  로고 108개는 자동 수집이라 "그 브랜드 로고가 맞는지" 아무도 눈으로 확인하지 않았다.
#  = 현재 사이트 최대 미검증 리스크(브랜드 로고를 잘못 달면 상표 문제로 번진다).
#  Claude는 108개를 눈으로 못 본다. 사용자가 3초면 아는 걸 3초 만에 끝내게 하는 화면.
#  사용법: 틀린 것만 클릭 → 하단 "결과 복사" → 채팅에 붙여넣기
import sqlite3, os, html, json

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "_logo_audit.html")
def esc(s): return html.escape(str(s)) if s is not None else ""

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
_c = {r[1] for r in cur.execute("PRAGMA table_info(brands)")}
_pend = "b.logo_pending" if "logo_pending" in _c else "0 AS logo_pending"
rows = cur.execute(f"""SELECT b.id, b.name, b.slug, b.logo_url, b.homepage_url, c.name cn, {_pend},
    (SELECT COUNT(*) FROM menus WHERE brand_id=b.id) mc
    FROM brands b JOIN categories c ON b.category_id=c.id ORDER BY c.name, b.name""").fetchall()

have = [r for r in rows if r["logo_url"]]
miss = [r for r in rows if not r["logo_url"]]
# 2차 재수집분 = 아직 사용자가 안 본 것. 맨 위에 따로 띄워 이것만 보면 되게 한다.
pending = [r for r in have if r["logo_pending"]]

# 메뉴 0개 브랜드는 브랜드 페이지가 아예 생성되지 않아 사이트에 노출되지 않는다(122개 중 35개).
#  → 그 로고는 지금 검수할 필요가 없다. 뒤로 빼고 표시해서 헛일을 막는다.
live = [r for r in have if r["mc"] > 0 and not r["logo_pending"]]
dormant = [r for r in have if r["mc"] == 0 and not r["logo_pending"]]

def card(r, off=False):
    # data-ver = 지금 걸려 있는 로고 파일명. 로고를 새로 받으면 ver가 바뀌어
    # localStorage에 남은 예전 판정이 무효가 된다(안 그러면 새 로고에 옛 '틀림'이 되살아남).
    ver = os.path.basename(r["logo_url"] or "")
    return f'''<button class="lg{' off' if off else ''}" data-id="{r['id']}" data-ver="{esc(ver)}" data-name="{esc(r['name'])}">
<div class="imgbox"><img src="{esc(r['logo_url'])}" alt="" loading="lazy"></div>
<div class="nm">{esc(r['name'])}</div>
<div class="mu">{esc(r['cn'])}{' · 미노출' if off else f" · 메뉴 {r['mc']}"}</div>
<div class="mark">✕ 틀림</div></button>'''

cards = "".join(card(r) for r in live)
cards_off = "".join(card(r, True) for r in dormant)
cards_new = "".join(card(r) for r in pending)

miss_html = "".join(f'<span class="mchip">{esc(r["name"])}</span>' for r in miss)

page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>로고 검수 · 얼마남아</title>
<style>
:root{{--ink:#1a1d21;--muted:#6b7280;--line:#e8eaed;--bg:#f5f6f8;--card:#fff;--accent:#ff6b35;--red:#dc2626}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:var(--bg);
color:var(--ink);line-height:1.5;font-size:15px}}
.wrap{{max-width:1100px;margin:0 auto;padding:16px 14px 120px}}
h1{{font-size:22px;font-weight:800;margin-bottom:4px}}
.sub{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.how{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:11px 13px;
font-size:13px;color:#92400e;margin-bottom:16px;line-height:1.6}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:9px}}
.lg{{background:var(--card);border:2px solid var(--line);border-radius:12px;padding:9px;
cursor:pointer;font-family:inherit;text-align:center;position:relative;transition:.1s}}
.lg:hover{{border-color:#bbb}}
.imgbox{{height:58px;display:flex;align-items:center;justify-content:center;margin-bottom:6px}}
.lg img{{max-width:100%;max-height:58px;object-fit:contain}}
.nm{{font-size:12.5px;font-weight:700;line-height:1.3}}
.mu{{font-size:10.5px;color:var(--muted);margin-top:2px}}
.mark{{display:none;position:absolute;top:5px;right:5px;background:var(--red);color:#fff;
font-size:10px;font-weight:800;padding:2px 6px;border-radius:6px}}
.lg.bad{{border-color:var(--red);background:#fef2f2}}
.lg.bad .mark{{display:block}}
.lg.bad img{{opacity:.35}}
.lg.off{{opacity:.55}}
.newbox{{background:#fff7ed;border:2px solid var(--accent);border-radius:14px;padding:14px;margin-bottom:18px}}
.newbox h2{{font-size:16px;font-weight:800;margin-bottom:5px}}
.newbox p{{font-size:12.5px;color:#92400e;margin-bottom:11px;line-height:1.6}}
.sec{{font-size:14px;font-weight:800;color:var(--muted);margin:18px 0 8px}}
.dorm{{margin-top:18px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}}
.dorm summary{{font-size:13px;font-weight:800;cursor:pointer;color:var(--muted)}}
.miss{{margin-top:22px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px}}
.miss h2{{font-size:14px;font-weight:800;margin-bottom:7px}}
.mchip{{display:inline-block;background:#f3f4f6;border:1px solid var(--line);border-radius:6px;
padding:3px 8px;font-size:12px;margin:2px}}
.bar{{position:fixed;left:0;right:0;bottom:0;background:var(--ink);color:#fff;padding:11px 14px;
display:flex;align-items:center;gap:12px;justify-content:center;flex-wrap:wrap}}
.bar b{{color:#ff9d6b;font-size:17px}}
.btn{{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:9px 16px;
font-size:14px;font-weight:800;cursor:pointer;font-family:inherit}}
.btn.g{{background:#374151}}
#out{{width:100%;max-width:1100px;margin:10px auto 0;font-family:monospace;font-size:12px;
padding:9px;border-radius:8px;border:1px solid var(--line);display:none;min-height:70px}}
</style></head><body>
<div class="wrap">
<h1>🔍 로고 검수 {len(live)}개</h1>
<p class="sub">자동 수집한 로고라 <b>브랜드가 맞는지 아무도 확인하지 않았습니다.</b> 현재 사이트 최대 미검증 리스크입니다.
지금 사이트에 노출 중인 <b>{len(live)}개만</b> 봐주시면 됩니다.</p>
<div class="how">
<b>틀린 것만 눌러주세요.</b> 맞는 건 건드리지 마세요.<br>
· 다른 브랜드 로고 / 로고가 아닌 이미지(광고·배너·사진) / 깨진 이미지 → 클릭<br>
· 다 고르셨으면 맨 아래 <b>결과 복사</b> → 채팅에 붙여넣기
</div>

<div class="newbox">
  <h2>🆕 새로 찾은 {len(pending)}개 — 이것만 봐주세요</h2>
  <p>1차 수집이 홍보 배너·음식 사진을 로고로 잘못 가져와서(22% 오류) 방식을 바꿔 다시 받았습니다.
  받은 19개 중 <b>명백히 로고가 아닌 8개</b>(식칼 사진·버거 사진·빈 이미지 등)는 제가 이미 걸러냈고,
  남은 {len(pending)}개만 확인이 필요합니다.</p>
  <div class="grid">{cards_new}</div>
</div>

<h2 class="sec">이미 확인하신 {len(live)}개 (변동 없음)</h2>
<div class="grid" id="grid">{cards}</div>

<details class="dorm"><summary>💤 지금 사이트에 안 나오는 브랜드 {len(dormant)}개 (메뉴 0개라 페이지 미생성 — 나중에 메뉴 넣을 때 보면 됨)</summary>
<div class="grid" style="margin-top:10px" id="grid2">{cards_off}</div></details>

<div class="miss"><h2>로고 못 받은 {len(miss)}개 (텍스트 배지로 정상 노출 중 — 검수 불필요)</h2>{miss_html}</div>
<textarea id="out" readonly></textarea>
</div>
<div class="bar">
  <span>틀림 <b id="cnt">0</b>개</span>
  <button class="btn" id="copy">📋 결과 복사</button>
  <button class="btn g" id="reset">초기화</button>
</div>
<script>
const grid = document.getElementById('grid');
const bad = new Set();
function sync(){{
  document.getElementById('cnt').textContent = bad.size;
  const recs = [...document.querySelectorAll('.lg.bad')].map(b => ({{id: b.dataset.id, ver: b.dataset.ver}}));
  try{{ localStorage.setItem('logoBad2', JSON.stringify(recs)); }}catch(e){{}}
}}
// 새로고침해도 검수 결과가 유지되게. 단 **로고 파일이 바뀐 브랜드는 복원하지 않는다** —
// 새로 받은 다른 이미지에 예전 '틀림' 판정이 되살아나면 안 된다.
try{{
  JSON.parse(localStorage.getItem('logoBad2') || '[]').forEach(rec => {{
    const el = document.querySelector('.lg[data-id="' + rec.id + '"]');
    if (el && el.dataset.ver === rec.ver) {{ el.classList.add('bad'); bad.add(String(rec.id)); }}
  }});
}}catch(e){{}}
sync();
document.addEventListener('click', e => {{
  const b = e.target.closest('.lg'); if (!b) return;
  const id = b.dataset.id;
  b.classList.toggle('bad');
  b.classList.contains('bad') ? bad.add(id) : bad.delete(id);
  sync();
}});
document.getElementById('copy').addEventListener('click', () => {{
  const list = [...document.querySelectorAll('.lg.bad')]
    .map(b => '- ' + b.dataset.name + ' (brand_id ' + b.dataset.id + ')').join('\\n');
  const txt = bad.size === 0 ? '로고 검수 결과: 전부 맞음 ✅'
    : '로고 검수 결과 — 틀린 것 ' + bad.size + '개:\\n' + list;
  const o = document.getElementById('out');
  o.style.display = 'block'; o.value = txt; o.select();
  navigator.clipboard.writeText(txt).then(
    () => {{ const c = document.getElementById('copy'); c.textContent = '✅ 복사됨'; setTimeout(()=>c.textContent='📋 결과 복사',1500); }},
    () => {{ try{{document.execCommand('copy');}}catch(e){{}} }});
}});
document.getElementById('reset').addEventListener('click', () => {{
  document.querySelectorAll('.lg.bad').forEach(b => b.classList.remove('bad'));
  bad.clear(); sync(); document.getElementById('out').style.display = 'none';
}});
</script>
</body></html>"""

open(OUT, "w", encoding="utf-8").write(page)
print(f"생성: _preview/_logo_audit.html — 검수 대상 {len(have)}개 · 로고 없음 {len(miss)}개")
con.close()
