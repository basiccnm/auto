# -*- coding: utf-8 -*-
"""배달 JSON 을 그대로 브랜드 골격으로 만든다 — 골격이 부실할 때 교체용. 2026-07-31
    python scripts/delivery_to_skeleton.py <slug> <배달.json> "<브랜드명>"
[XXXX] 접두사·코드접두사(H1. PS2.)·JUNK 제거. 대표 지시: 골격 틀리면 배달로 다 넣어라.
"""
import io,json,os,re,sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(BASE,'data','brand_menu_list')
slug,dvpath,brand=sys.argv[1],sys.argv[2],sys.argv[3]
BR=re.compile(r'^(?:\[[^\]]*\]\s*|[A-Z]{1,3}\d+\.\s*)+')
JUNK=re.compile(r'^(준비중|검색한 메뉴|인기메뉴|추천메뉴|메뉴|추천 메뉴)$')
dv=json.load(io.open(dvpath,encoding='utf-8'))['prices']
menus=[];seen=set();k=0
for m in dv:
    nm=BR.sub('',m['name']).strip()
    if not nm or JUNK.match(nm) or JUNK.match(m['name']) or nm in seen: continue
    seen.add(nm)
    menus.append({"name":nm,"price":m['price'],"price_source":"delivery_coupangeats","price_note":None,"cats":[["메뉴",k]]});k+=1
doc={"brand":brand,"slug":slug,"source":"쿠팡이츠 앱","collected_at":"2026-07-31",
     "note":"쿠팡이츠 배달가 기준. 배달팁이 포함될 수 있고 지점마다 다를 수 있다. 실제 매장에서 사면 더 저렴하다. 가격은 날마다 달라진다.",
     "cats":[{"name":"메뉴","parent":None,"ext_id":"메뉴"}],"menus":menus}
p=os.path.join(OUT,slug+'.json')
json.dump(doc,io.open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print("%s → 배달 %d개 골격 생성"%(slug,len(menus)))
