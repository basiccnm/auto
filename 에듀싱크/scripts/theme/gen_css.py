# -*- coding: utf-8 -*-
"""theme_tokens.json → style.css 의 테마 블록을 갈아끼운다."""
import json, io
rows = json.load(io.open('theme_tokens.json', encoding='utf-8'))
HEAD = """/* ═══ 테마 배경 18종 (2026-08-03 지시) ═══════════════════════════
   그림 18장 전부를 슬롯에 연결한다(6종이 아니다). **밝기 2종 × 배경 18종** 조합.
   ⚠ 색은 손으로 고르지 않았다 — **각 그림 하단 단색에서 뽑아** 파생했다
     (scratchpad/build_themes.py). 그림과 배경이 이어져 보이는 게 목적이다.
   ⚠ 어두운 그림(밤·서재·숲)은 **라이트에서 밝은 파생**을 쓴다. 어두운 배경 위 흰 카드는
     2.77:1 로 떠서 종이조각처럼 보였다(2026-08-03 night 세트에서 겪음).
   ⚠ 이 블록은 생성물이다. 값을 손으로 고치지 말고 build_themes.py → gen_css.py 를 돌릴 것. */"""
L = [HEAD]
for r in rows:
    k = r['key']
    L.append(f""":root[data-art="{k}"], [data-art="{k}"] {{
  --art-img: url(themes/{k}.webp); --art-1: {r['surf_l']}; --art-2: {r['surf_l']}; --art-3: {r['surf_l']}; --art-4: {r['surf_l']};
  --surf: {r['surf_l']}; --card-a: {r['card_l']}; --card-b: {r['surf_l']};
  --accent: {r['acc_l']}; --accent-ink: {r['acc_l']}; --art-ink: {r['ink_l']};
  --drawer-a: {r['drawer_l']}; --muted-card: #57514A; }}""")
for r in rows:
    k = r['key']
    L.append(f""":root[data-theme="dark"][data-art="{k}"], :root[data-theme="dark"] [data-art="{k}"], [data-theme="dark"][data-art="{k}"] {{
  --art-1: {r['surf_d']}; --art-2: {r['surf_d']}; --art-3: {r['surf_d']}; --art-4: {r['surf_d']};
  --surf: {r['surf_d']}; --card-a: {r['card_d']}; --card-b: {r['surf_d']};
  --accent: {r['acc_d']}; --accent-ink: {r['acc_d']}; --art-ink: {r['ink_d']};
  --drawer-a: {r['drawer_d']}; --muted-card: #B4BECC; }}""")
p = r'C:\Users\hardb\Desktop\블로그수입관련\에듀싱크\app\www\style.css'
s = io.open(p, encoding='utf-8').read()
st = s.index('/* ═══ 테마 배경 18종'); en = s.index('/* 다크 기본값(세트를 안 고른 사람)')
io.open(p, 'w', encoding='utf-8').write(s[:st] + "\n".join(L) + "\n\n" + s[en:])
print("style.css 반영 —", len(rows)*2, "규칙")
