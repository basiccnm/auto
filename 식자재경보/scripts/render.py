# -*- coding: utf-8 -*-
"""render.py — data.json 을 한 장짜리 HTML 로 굽는다.

디자인 방향 (왜 이렇게 생겼나)
    보는 사람은 **주방에서 폰으로 3초 보는 사장님**이다. 예쁜 것보다 숫자가 먼저 읽혀야 한다.
    그래서 가락시장 시세판·가격표를 본떴다.
      · 한국 시세 관례를 따른다 — **오름 = 빨강**, 내림 = 파랑. 서양식(오름=초록)을 쓰면 반대로 읽힌다.
      · 상승률을 가장 큰 글자로 둔다. 품목명보다 크다. 사장님이 찾는 건 «얼마나 올랐나» 다.
      · 폰트는 시스템 것만 쓴다. 외부 폰트를 불러오면 주방 와이파이에서 늦고, 배포처 CSP 에도 걸린다.
      · 숫자는 tabular-nums 로 자리를 고정해 세로로 눈이 흐르게 한다.
    장식은 넣지 않는다. 이 페이지의 값어치는 «대체재가 바로 옆에 있다» 하나다.
"""
import html


def _won(n):
    return f"{int(n):,}"


CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#fbfbf9; --fg:#16150f; --dim:#6d6a5e; --line:#e3e0d5;
  --up:#c8102e; --up-bg:#fdf0f1; --card:#fff;
}
@media (prefers-color-scheme:dark){
  :root{--bg:#14140f;--fg:#f2f0e8;--dim:#98948a;--line:#2c2b24;
        --up:#ff5c6e;--up-bg:#241417;--card:#1c1b16}
}
:root[data-theme=light]{--bg:#fbfbf9;--fg:#16150f;--dim:#6d6a5e;--line:#e3e0d5;
  --up:#c8102e;--up-bg:#fdf0f1;--card:#fff}
:root[data-theme=dark]{--bg:#14140f;--fg:#f2f0e8;--dim:#98948a;--line:#2c2b24;
  --up:#ff5c6e;--up-bg:#241417;--card:#1c1b16}

body{margin:0;background:var(--bg);color:var(--fg);
  font-family:system-ui,-apple-system,"Malgun Gothic","Apple SD Gothic Neo",sans-serif;
  font-size:16px;line-height:1.5;-webkit-text-size-adjust:100%}
.wrap{max-width:720px;margin:0 auto;padding:20px 16px 64px}

header{border-bottom:3px solid var(--fg);padding-bottom:12px;margin-bottom:6px}
h1{margin:0;font-size:26px;font-weight:800;letter-spacing:-.02em}
.lead{font-size:15px;font-weight:600;margin-top:4px}
.sub{color:var(--dim);font-size:13px;margin-top:6px;font-variant-numeric:tabular-nums}

/* 이 페이지의 논거. 「비싼데 왜 사냐」에 3초 안에 답해야 한다 */
.why{background:var(--up-bg);border-left:3px solid var(--up);margin:16px 0 4px;
  padding:12px 14px;font-size:14px;line-height:1.6;border-radius:0 8px 8px 0}

.none{margin-top:12px;color:var(--dim);font-size:13px;
  border:1px dashed var(--line);border-radius:8px;padding:10px 12px}
.cta{margin-top:9px;font-size:13px;font-weight:700;color:var(--up)}

.always{margin-top:34px;padding-top:20px;border-top:3px solid var(--fg)}
.always h2{margin:0;font-size:18px;font-weight:800}
.always .s{color:var(--dim);font-size:13px;margin:5px 0 12px}

.row{border-bottom:1px solid var(--line);padding:18px 0}
.head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.pct{color:var(--up);font-size:38px;font-weight:800;line-height:1;
  font-variant-numeric:tabular-nums;letter-spacing:-.03em}
.pct::before{content:"▲";font-size:.5em;vertical-align:.22em;margin-right:.15em}
.name{font-size:19px;font-weight:700}
.move{color:var(--dim);font-size:13px;margin-top:6px;font-variant-numeric:tabular-nums}
.move b{color:var(--fg);font-weight:600}

.alts{margin-top:12px;display:grid;gap:8px}
.alt{display:flex;gap:10px;align-items:center;background:var(--card);
  border:1px solid var(--line);border-radius:10px;padding:9px 11px;
  text-decoration:none;color:inherit}
.alt:hover{border-color:var(--up)}
.alt:focus-visible{outline:2px solid var(--up);outline-offset:2px}
.alt img{width:44px;height:44px;object-fit:cover;border-radius:6px;flex:none;background:var(--line)}
.alt .t{flex:1;min-width:0;font-size:14px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.alt .p{font-weight:700;font-size:15px;white-space:nowrap;font-variant-numeric:tabular-nums}
.tag{display:inline-block;background:var(--up-bg);color:var(--up);
  font-size:11px;font-weight:700;padding:2px 7px;border-radius:4px;margin-bottom:8px}

footer{margin-top:32px;padding-top:16px;border-top:1px solid var(--line);
  color:var(--dim);font-size:12px}
@media (max-width:420px){.pct{font-size:32px}h1{font-size:22px}}
"""

# 문구는 **기획(제미나이)이 쓴 것**을 그대로 쓴다. 개발자가 고쳐 쓰지 않는다.
# ⚠ 제목·설명에 「쿠팡」·「로켓배송」을 넣지 않는다 (상표 제한). 그래서 버튼도 「앱에서 확인하기」다.
TPL = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>식자재 경보 — 오늘자 도매가 폭등 품목 &amp; 원가 방어 대체재</title>
<meta name="description" content="일주일 새 도매가가 급등한 식자재와, 원가를 방어할 업소용 대체재를 하루 한 번 정리합니다.">
<style>{css}</style>
<div class="wrap">
<header>
  <h1>🚨 식자재 경보</h1>
  <div class="lead">오늘자 도매가 폭등 품목 &amp; 원가 방어 대체재</div>
  <div class="sub">{base} → {date} 도매가 기준 · {n}개 품목이 {th}% 이상 올랐습니다</div>
</header>

<p class="why">가공품이 생물보다 kg 단가가 비싸 보이나요?
버리는 잎 0%, 다듬는 인건비 0원, 1년 내내 고정 단가.
국물·볶음용은 가공·냉동이 무조건 원가 이득입니다.</p>

{rows}
{always}
<footer>
  <p>도매가는 농산물유통정보(KAMIS) 공개 데이터입니다. 지역·등급에 따라 실제 매입가와 다를 수 있습니다.</p>
  <p>{disclosure}</p>
</footer>
</div>
"""

CTA = "👉 최저가 업소용 대체재 앱에서 확인하기"


def _card(a):
    return (
        f'<a class="alt" href="{html.escape(a["url"])}" target="_blank" rel="nofollow sponsored noopener">'
        f'<img src="{html.escape(a["image"])}" alt="" loading="lazy">'
        f'<span class="t">{html.escape(a["name"])}</span>'
        f'<span class="p">{_won(a["price"])}원</span></a>'
    )


def _row(r):
    alts = "".join(_card(a) for a in r.get("alts", []) if a.get("url"))
    if alts:
        block = (f'<div class="tag">원가 방어 대체재</div>'
                 f'<div class="alts">{alts}</div><div class="cta">{CTA}</div>')
    else:
        # 대체가 없는 품목도 줄은 남긴다. 링크 자리에 없다고 밝힌다 (회신11 확정).
        block = '<div class="none">신선·쌈채소류 — 가공 대체 불가</div>'
    return (
        '<div class="row">'
        f'<div class="head"><span class="pct">{r["pct"]:.1f}%</span>'
        f'<span class="name">{html.escape(r["name"])}</span></div>'
        f'<div class="move">1kg <b>{_won(r["was"])}원</b> → <b>{_won(r["now"])}원</b></div>'
        f'{block}</div>'
    )


def _always(items):
    if not items:
        return ""
    cards = "".join(_card(a) for a in items if a.get("url"))
    return (f'<section class="always"><h2>상시 — 주방 인건비 절감템</h2>'
            f'<p class="s">시세와 상관없이 1년 내내 쓰는 것들입니다.</p>'
            f'<div class="alts">{cards}</div></section>')


def render(data):
    from coupang import coupang_api as cp
    return TPL.format(
        css=CSS,
        base=data["base_date"],
        date=data["date"],
        n=len(data["items"]),
        th=int(data["threshold"]),
        rows="".join(_row(r) for r in data["items"]),
        always=_always(data.get("always", [])),
        disclosure=html.escape(cp.DISCLOSURE),
    )
