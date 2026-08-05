# -*- coding: utf-8 -*-
# 얼마남아 — 레시피 관리 페이지 (2026-07-20)
#
#   실행:  레시피관리.bat  더블클릭   또는   python admin_server.py
#   주소:  http://127.0.0.1:8796
#
# 🔴 규칙 (사고 이력에서 나온 것들)
#   · debug=False / use_reloader=False 고정 — 자동리로더가 남의 파일 변경에 반응해
#     서버가 튕긴 사고(2026-07-17)와, 긴 작업(90초)이 리로드로 죽는 문제 때문.
#   · 배포 버튼 없음 — '반영' 옆에 배포가 있으면 검수 안 된 게 나간다. 명령어만 안내한다.
#   · OpenAI 호출 없음(2026-07-20 사용자 지시) — 이미 _recipes\에 있는 파일만 다룬다.
#     생성 기능은 나중에 붙인다.
#   · dishes/dish_ingredients에 직접 쓰지 않는다. dish_def에만 쓴다(gen_dishes가 매번 지움).
import json
import os
import sqlite3
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime

from flask import Flask, jsonify, request, render_template_string, send_file, redirect

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import admin_store as st              # noqa: E402
from apply_recipe_md import parse     # noqa: E402
from recipe_mapping import Matcher    # noqa: E402

PORT = 8796
RECIPES = os.path.join(BASE, "_recipes")
IMGDIR = os.path.join(RECIPES, "img")
app = Flask(__name__)

# 전역 단일 잡 — 반영은 동시에 돌면 안 된다(파이프라인이 DB·파일을 함께 만진다)
JOB = {"running": False, "slug": None, "log": [], "state": "idle"}


def job_log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    JOB["log"].append(line)
    print(line, flush=True)


# ── 데이터 조회 ───────────────────────────────────────────────────
def drafts():
    """_recipes\\*.md 목록 + 반영 여부."""
    out = []
    if not os.path.isdir(RECIPES):
        return out
    c = st.conn()
    applied = {r[0] for r in c.execute(
        "SELECT slug FROM dishes WHERE COALESCE(recipe_serving,'')<>''")}
    known = {r[0]: r[1] for r in c.execute("SELECT slug, name FROM dish_def")}
    c.close()
    for fn in sorted(os.listdir(RECIPES)):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        imgs = sum(1 for i in (1, 2, 3)
                   if os.path.exists(os.path.join(IMGDIR, f"{slug}_{i}.png")))
        out.append({"slug": slug, "name": known.get(slug, slug),
                    "known": slug in known, "imgs": imgs,
                    "applied": slug in applied,
                    "mtime": datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(RECIPES, fn))).strftime("%m-%d %H:%M")})
    return out


def review_data(slug):
    p = os.path.join(RECIPES, f"{slug}.md")
    if not os.path.exists(p):
        return None
    raw = open(p, encoding="utf-8").read()
    d = parse(raw)
    mt = Matcher()
    rows = mt.map_recipe(d["ing_groups"])
    ing_names = {r["ingredient_key"]: r["name"] for r in
                 mt.c.execute("SELECT ingredient_key, name FROM ingredients")}
    for r in rows:
        r["key_name"] = ing_names.get(r["key"], "")
    mt.c.close()
    return {"slug": slug, "raw": raw, "d": d, "rows": rows,
            "miss": [r for r in rows if not r["key"]],
            "badunit": [r for r in rows if r["key"] and not r["unit_ok"]],
            "imgs": [i for i in (1, 2, 3)
                     if os.path.exists(os.path.join(IMGDIR, f"{slug}_{i}.png"))]}


# ── 화면 ─────────────────────────────────────────────────────────
CSS = """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Malgun Gothic',-apple-system,sans-serif;background:#f5f6f8;color:#1a1d21;padding:0 0 60px}
a{color:#1a56b0}
header{background:#1a1d21;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:14px}
header b{font-size:16px}header .sub{font-size:12px;color:#9aa1ac}
header a{color:#ffb08a;text-decoration:none;font-size:13px;margin-left:auto}
.wrap{max-width:1180px;margin:0 auto;padding:18px 16px}
h2{font-size:16px;margin:20px 0 10px}
.card{background:#fff;border:1px solid #e8eaed;border-radius:12px;padding:14px 16px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;color:#6b7280;padding:7px 8px;border-bottom:1px solid #e8eaed}
td{padding:8px;border-bottom:1px solid #f1f2f4;vertical-align:top}
tr:last-child td{border-bottom:0}
.badge{display:inline-block;font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:6px}
.ok{background:#e7f6ec;color:#16a34a}.warn{background:#fffbeb;color:#a16207}
.bad{background:#fdeaea;color:#dc2626}.mut{background:#f1f2f4;color:#6b7280}
.btn{display:inline-block;padding:8px 14px;border:1px solid #d4d7dc;border-radius:9px;background:#fff;
color:#1a1d21;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;font-family:inherit}
.btn:hover{background:#f7f8fa}
.btn.pri{background:#ff6b35;border-color:#ff6b35;color:#fff}
.btn:disabled{opacity:.45;cursor:not-allowed}
#joblog{background:#12151a;color:#a8e6a0;font-family:Consolas,monospace;font-size:12px;
padding:11px 13px;border-radius:9px;height:190px;overflow-y:auto;white-space:pre-wrap;line-height:1.55}
.imgs{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}
.imgs img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:9px;border:1px solid #e8eaed}
.imgs figcaption{font-size:11px;color:#6b7280;text-align:center;margin-top:4px}
pre.md{background:#fafbfc;border:1px solid #e8eaed;border-radius:9px;padding:12px;font-size:12.5px;
line-height:1.7;white-space:pre-wrap;font-family:inherit;max-height:460px;overflow-y:auto}
.note{background:#eef7ff;border:1px solid #bfdcff;color:#1a56b0;border-radius:9px;
padding:10px 12px;font-size:12.5px;line-height:1.6;margin-bottom:12px}
.note.warn{background:#fffbeb;border-color:#fde68a;color:#78530b}
select,input{font-family:inherit;font-size:12.5px;padding:5px 7px;border:1px solid #d4d7dc;border-radius:7px}
</style>"""

NAV = ('<header><b>🍳 얼마남아 레시피 관리</b>'
       '<span class="sub">생성물 검수 → 사이트 반영</span>'
       '<a href="/">목록</a><a href="http://127.0.0.1:8792" target="_blank">프리뷰(8792)</a></header>')

INDEX = CSS + NAV + """<div class="wrap">
<div class="note">이 페이지는 <b>이미 만들어진 레시피 파일</b>(_recipes\\*.md)을 검수해 사이트에 반영합니다.
OpenAI 생성 기능은 아직 붙이지 않았습니다.</div>
<h2>레시피 파일 {{rows|length}}건</h2>
<div class="card"><table>
<tr><th>요리</th><th>slug</th><th>사진</th><th>DB 요리</th><th>반영</th><th>수정</th><th></th></tr>
{% for r in rows %}<tr>
<td><b>{{r.name}}</b></td><td style="color:#6b7280">{{r.slug}}</td>
<td>{% if r.imgs==3 %}<span class="badge ok">3장</span>{% elif r.imgs %}<span class="badge warn">{{r.imgs}}장</span>{% else %}<span class="badge mut">없음</span>{% endif %}</td>
<td>{% if r.known %}<span class="badge ok">있음</span>{% else %}<span class="badge warn">신규</span>{% endif %}</td>
<td>{% if r.applied %}<span class="badge ok">반영됨</span>{% else %}<span class="badge mut">대기</span>{% endif %}</td>
<td style="color:#6b7280">{{r.mtime}}</td>
<td><a class="btn" href="/review/{{r.slug}}">검수 →</a></td>
</tr>{% endfor %}
</table></div>
<h2>작업 로그</h2><div id="joblog"></div>
</div>
<script>
setInterval(async()=>{const r=await(await fetch('/api/joblog')).json();
 const el=document.getElementById('joblog');el.textContent=r.log.join('\\n');
 el.scrollTop=el.scrollHeight;},2000);
</script>"""

REVIEW = CSS + NAV + """<div class="wrap">
<h2>{{v.slug}} 검수</h2>
{% if v.miss %}<div class="note warn"><b>미매칭 재료 {{v.miss|length}}건</b> — DB에 없는 재료입니다.
등록해야 원가가 계산됩니다: {% for m in v.miss %}<b>{{m.raw}}</b>{% if not loop.last %}, {% endif %}{% endfor %}</div>{% endif %}
{% if v.badunit %}<div class="note warn"><b>단위 불일치 {{v.badunit|length}}건</b> —
그대로 넣으면 원가가 수십 배로 튑니다(부대찌개 17만원 전례).</div>{% endif %}

{% if v.imgs %}<div class="card"><h2 style="margin-top:0">사진</h2><div class="imgs">
{% for i in v.imgs %}<figure><img src="/img/{{v.slug}}/{{i}}">
<figcaption>{{['재료','조리','완성'][i-1]}}</figcaption></figure>{% endfor %}
</div></div>{% endif %}

<div class="card"><h2 style="margin-top:0">재료 매핑 {{v.rows|length}}줄</h2>
<table><tr><th>원문</th><th>분량</th><th>그룹</th><th>매칭</th><th>근거</th><th>단위</th></tr>
{% for r in v.rows %}<tr>
<td><b>{{r.raw}}</b></td>
<td>{{r.amount_raw or '—'}}{% if r.parts and r.parts|length>1 %}<div style="font-size:11px;color:#6b7280">= {{r.parts|join(' + ')}}</div>{% endif %}</td>
<td style="color:#6b7280">{{r.group}}</td>
<td>{% if r.key %}{{r.key_name}}<div style="font-size:11px;color:#6b7280">{{r.key}}</div>
{% else %}<span class="badge bad">미매칭</span>
{% if r.candidates %}<div style="font-size:11px;color:#6b7280">후보: {{r.candidates[:3]|join(', ')}}</div>{% endif %}{% endif %}</td>
<td><span class="badge {{'ok' if r.score>=0.95 else ('warn' if r.key else 'bad')}}">{{r.how}}</span></td>
<td>{% if not r.key %}—{% elif r.unit_ok %}<span class="badge ok">OK</span>{% else %}<span class="badge bad">불일치</span>{% endif %}</td>
</tr>{% endfor %}</table></div>

<div class="card"><h2 style="margin-top:0">레시피 원문</h2><pre class="md">{{v.raw}}</pre></div>

<div class="card">
<button class="btn pri" id="applyBtn" {{'disabled' if v.miss or v.badunit else ''}}>사이트에 반영</button>
<span style="font-size:12px;color:#6b7280;margin-left:10px">
{% if v.miss or v.badunit %}미매칭·단위불일치를 먼저 해결해야 반영할 수 있습니다{% else %}DB 백업 후 페이지까지 생성합니다{% endif %}</span>
</div>
<h2>작업 로그</h2><div id="joblog"></div>
</div>
<script>
const slug={{v.slug|tojson}};
const b=document.getElementById('applyBtn');
if(b) b.addEventListener('click',async()=>{
  if(!confirm(slug+' 을(를) 사이트에 반영합니다. DB를 백업한 뒤 진행됩니다. 계속할까요?'))return;
  b.disabled=true;b.textContent='반영 중...';
  const r=await(await fetch('/api/apply/'+slug,{method:'POST'})).json();
  if(!r.ok){alert(r.error);b.disabled=false;b.textContent='사이트에 반영';}
});
setInterval(async()=>{const r=await(await fetch('/api/joblog')).json();
 const el=document.getElementById('joblog');el.textContent=r.log.join('\\n');
 el.scrollTop=el.scrollHeight;
 if(b&&r.state==='done'){b.textContent='반영 완료';}
 if(b&&r.state==='error'){b.disabled=false;b.textContent='사이트에 반영';}},2000);
</script>"""


# ── 라우트 ───────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(INDEX, rows=drafts())


@app.route("/review/<slug>")
def review(slug):
    v = review_data(slug)
    if not v:
        return redirect("/")
    return render_template_string(REVIEW, v=v)


@app.route("/img/<slug>/<int:i>")
def img(slug, i):
    p = os.path.join(IMGDIR, f"{slug}_{i}.png")
    return send_file(p) if os.path.exists(p) else ("", 404)


@app.route("/api/joblog")
def api_joblog():
    return jsonify({"running": JOB["running"], "state": JOB["state"],
                    "slug": JOB["slug"], "log": JOB["log"][-200:]})


@app.route("/api/apply/<slug>", methods=["POST"])
def api_apply(slug):
    if JOB["running"]:
        return jsonify({"ok": False, "error": "다른 작업이 실행 중입니다"})
    if not os.path.exists(os.path.join(RECIPES, f"{slug}.md")):
        return jsonify({"ok": False, "error": "레시피 파일이 없습니다"})
    JOB.update(running=True, slug=slug, log=[], state="running")

    def worker():
        try:
            import admin_pipeline
            admin_pipeline.apply(slug, job_log)
            JOB["state"] = "done"
        except Exception as e:
            job_log(f"❌ 실패: {e}")
            JOB["state"] = "error"
        finally:
            JOB["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


if __name__ == "__main__":
    st.init()
    print(f"레시피 관리 페이지 → http://127.0.0.1:{PORT}")
    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    # ⚠️ debug/reloader 금지 — 자동리로더 사고 + 긴 작업이 리로드로 죽는 문제
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)
