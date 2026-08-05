# -*- coding: utf-8 -*-
"""wtable 원본 레시피(2,683건)를 카테고리별로 훑어볼 수 있는 로컬 전용 뷰어.
사진·영상 URL은 wtable CDN을 그대로 링크(다운로드 안 함).

⚠️ 이건 검토·소재 발굴용이다. 저작권 있는 원본(wtable.co.kr) 그대로라
   _dist(배포)에 절대 섞이면 안 된다. 여기서 골라 recipe_rewrite.py로
   우리 말투로 다시 쓴 것만 dish_ingredients/사이트에 올라간다.
"""
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WTABLE = os.path.join(BASE, "data", "wtable")
OUT = os.path.join(BASE, "_recipe_review")

os.makedirs(OUT, exist_ok=True)


CAT_SLUG = {
    "한식": "hansik", "양식": "yangsik", "디저트·음료": "dessert",
    "이탈리아": "italian", "일식": "ilsik", "중식": "jungsik",
    "아시안": "asian", "기타": "etc",
}


def slug(s):
    if s in CAT_SLUG:
        return CAT_SLUG[s]
    base = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    return base if base else f"c{abs(hash(s)) % 100000}"


def load():
    cats = {r["token"]: r for r in json.load(open(os.path.join(WTABLE, "classify.json"), encoding="utf-8"))}
    recipes = []
    with open(os.path.join(WTABLE, "merged_recipes.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            c = cats.get(d["token"], {})
            d["cat"] = c.get("cat", "기타")
            d["sub"] = c.get("sub", "")
            recipes.append(d)
    return recipes


HEAD = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{title}</title>
<style>
body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#FBEFE0;margin:0;padding:20px;color:#333}}
a{{color:inherit;text-decoration:none}}
.bar{{max-width:1100px;margin:0 auto 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.bar a{{background:#fff;border-radius:8px;padding:6px 12px;font-size:14px;border:1px solid #eee}}
.bar a.on{{background:#FF7A59;color:#fff}}
.grid{{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}}
.card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.card img{{width:100%;height:140px;object-fit:cover;background:#eee;display:block}}
.card .t{{padding:8px 10px}}
.card .name{{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.card .sub{{font-size:12px;color:#999;margin-top:2px}}
h2.subhead{{max-width:1100px;margin:24px auto 8px;font-size:15px;color:#B5502A}}
.count{{color:#999;font-size:13px}}
.detail{{max-width:760px;margin:0 auto;background:#fff;border-radius:14px;padding:24px}}
.detail img.hero{{width:100%;border-radius:10px;margin-bottom:14px;background:#eee}}
.ing-group{{margin:10px 0}}
.ing-group h4{{margin:0 0 4px;font-size:14px;color:#B5502A}}
.ing-group ul{{margin:0;padding-left:18px;font-size:14px}}
.steps li{{margin-bottom:14px;font-size:14px;line-height:1.5}}
.steps img{{width:100%;max-width:400px;border-radius:8px;margin-top:6px;display:block}}
.back{{display:inline-block;margin-bottom:14px;font-size:14px;color:#B5502A}}
.search{{max-width:1100px;margin:0 auto 16px}}
.search input{{width:100%;box-sizing:border-box;padding:12px 14px;border-radius:10px;border:1px solid #eee;font-size:16px;background:#fff}}
.hit{{font-size:13px;color:#999;margin:6px 2px}}
</style></head><body>
"""
FOOT = "</body></html>"

SEARCH_JS = """
<script>
let DB = null;
async function ensureDB(){
  if (DB) return DB;
  const res = await fetch('data.json');
  DB = await res.json();
  return DB;
}
function cardHtml(r, matchedIng){
  const sub = matchedIng ? ('재료: '+matchedIng) : (r.cat+(r.sub? ' · '+r.sub:''));
  return '<a class="card" href="r_'+r.id+'.html"><img loading="lazy" src="'+(r.img||'')+'" alt="">'
    + '<div class="t"><div class="name">'+r.title+'</div><div class="sub">'+sub+'</div></div></a>';
}
async function doSearch(q){
  const grid = document.getElementById('grid');
  const hit = document.getElementById('hit');
  q = q.trim();
  if (!q){ grid.innerHTML=''; hit.textContent=''; return; }
  const db = await ensureDB();
  const found = [];
  for (const r of db){
    if (r.title.includes(q)){ found.push([r, null]); continue; }
    const m = (r.ings||[]).find(i => i.includes(q));
    if (m){ found.push([r, m]); }
  }
  const top = found.slice(0, 200);
  hit.textContent = found.length + '건 (제목+재료)';
  grid.innerHTML = top.map(([r, m]) => cardHtml(r, m)).join('');
}
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('q');
  if (!input) return;
  input.addEventListener('input', () => doSearch(input.value));
  const params = new URLSearchParams(location.search);
  const q0 = params.get('q');
  if (q0){ input.value = q0; doSearch(q0); }
});
</script>
"""


def write_search_page():
    parts = [HEAD.format(title="레시피 검색")]
    parts.append('<div class="bar"><a href="index.html">← 전체</a></div>')
    parts.append('<div class="search"><input id="q" type="search" placeholder="레시피 이름 또는 재료 검색 (예: 목이버섯)" autofocus></div>')
    parts.append('<p class="hit" id="hit"></p>')
    parts.append('<div class="grid" id="grid"></div>')
    parts.append(SEARCH_JS)
    parts.append(FOOT)
    open(os.path.join(OUT, "search.html"), "w", encoding="utf-8").write("".join(parts))


def write_data_json(recipes):
    rows = []
    for r in recipes:
        ings = []
        for g in r.get("groups", []):
            for ing in g.get("ings", []):
                n = ing.get("n", "").strip()
                if n and n not in ings:
                    ings.append(n)
        rows.append({
            "id": r["id"], "title": r["title"], "cat": r["cat"], "sub": r.get("sub", ""),
            "img": r.get("img_title", ""), "ings": ings,
        })
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)


def write_index(by_cat):
    parts = [HEAD.format(title="레시피 리뷰")]
    parts.append('<div class="search"><input id="q" type="search" placeholder="레시피 이름 또는 재료 검색 (예: 목이버섯)" onfocus="location.href=&quot;search.html&quot;" readonly></div>')
    parts.append('<div class="bar">')
    parts.append('<a href="search.html">🔍 검색</a>')
    for cat, items in by_cat.items():
        parts.append(f'<a href="cat_{slug(cat)}.html">{cat} <span class="count">({len(items)})</span></a>')
    parts.append("</div>")
    parts.append(f'<p style="text-align:center;color:#999">wtable 원본 {sum(len(v) for v in by_cat.values())}건 · 검토·소재 발굴용, 배포 안 됨</p>')
    parts.append(FOOT)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write("".join(parts))


def write_cat_page(cat, items, cat_names):
    parts = [HEAD.format(title=cat)]
    parts.append('<div class="bar">')
    parts.append('<a href="index.html">← 전체</a>')
    parts.append('<a href="search.html">🔍 검색</a>')
    for c in cat_names:
        cls = "on" if c == cat else ""
        parts.append(f'<a class="{cls}" href="cat_{slug(c)}.html">{c}</a>')
    parts.append("</div>")

    subs = {}
    for r in items:
        subs.setdefault(r.get("sub") or "기타", []).append(r)

    for sub, rs in subs.items():
        parts.append(f'<h2 class="subhead">{sub} <span class="count">({len(rs)})</span></h2>')
        parts.append('<div class="grid">')
        for r in rs:
            img = r.get("img_title") or ""
            parts.append(
                f'<a class="card" href="r_{r["id"]}.html">'
                f'<img loading="lazy" src="{img}" alt="">'
                f'<div class="t"><div class="name">{r["title"]}</div>'
                f'<div class="sub">{r.get("time","?")}분 · 난이도{r.get("level","?")}</div></div></a>'
            )
        parts.append("</div>")
    parts.append(FOOT)
    open(os.path.join(OUT, f"cat_{slug(cat)}.html"), "w", encoding="utf-8").write("".join(parts))


def write_detail(r):
    parts = [HEAD.format(title=r["title"])]
    parts.append(f'<a class="back" href="cat_{slug(r["cat"])}.html">← {r["cat"]}</a>')
    parts.append('<div class="detail">')
    if r.get("img_title"):
        parts.append(f'<img class="hero" src="{r["img_title"]}" alt="">')
    parts.append(f'<h1 style="margin:0 0 4px">{r["title"]}</h1>')
    parts.append(f'<p style="color:#999;margin:0 0 16px">{r.get("desc","")} · {r.get("time","?")}분 · 난이도{r.get("level","?")} · {r["cat"]}/{r.get("sub","")}</p>')

    for g in r.get("groups", []):
        parts.append(f'<div class="ing-group"><h4>{g.get("name","")} {("· "+g["desc"]) if g.get("desc") else ""}</h4><ul>')
        for ing in g.get("ings", []):
            parts.append(f'<li>{ing.get("n","")} — {ing.get("v","")}</li>')
        parts.append("</ul></div>")

    parts.append('<ol class="steps">')
    step_imgs = r.get("step_imgs", [])
    for i, s in enumerate(r.get("steps", [])):
        parts.append(f"<li>{s}")
        if i < len(step_imgs):
            for im in step_imgs[i]:
                parts.append(f'<img loading="lazy" src="{im}" alt="">')
        parts.append("</li>")
    parts.append("</ol>")

    if r.get("video"):
        parts.append(f'<p><a href="{r["video"]}" target="_blank">영상 원본 보기 ↗</a></p>')

    parts.append("</div>")
    parts.append(FOOT)
    open(os.path.join(OUT, f'r_{r["id"]}.html'), "w", encoding="utf-8").write("".join(parts))


def main():
    recipes = load()
    by_cat = {}
    for r in recipes:
        by_cat.setdefault(r["cat"], []).append(r)
    # 큰 카테고리부터
    by_cat = dict(sorted(by_cat.items(), key=lambda kv: -len(kv[1])))
    cat_names = list(by_cat.keys())

    write_index(by_cat)
    write_search_page()
    write_data_json(recipes)
    for cat, items in by_cat.items():
        write_cat_page(cat, items, cat_names)
    for r in recipes:
        write_detail(r)

    print(f"✅ {len(recipes)}건 생성 완료 → {OUT}")
    print(f"   카테고리: " + ", ".join(f"{c}({len(v)})" for c, v in by_cat.items()))


if __name__ == "__main__":
    main()
