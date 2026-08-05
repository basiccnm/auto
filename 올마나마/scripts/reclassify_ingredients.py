# -*- coding: utf-8 -*-
# 재료 전수 재분류 — 대분류(축산물/농산물/수산물/가공식품) + 하위분류 (2026-07-20)
#
# 지시(사용자 2026-07-20):
#   · 4개 대분류로 전수조사해 알맞은 곳에 넣을 것
#   · '시판'은 가공식품으로 옮기고, 가공식품도 하위 분류를 나눌 것
#   · '경락'이라는 표기는 축산물에만 남기고 나머지는 정리할 것
#
# 원칙: 출처가 분류를 알려주면(=공공API 대분류) 그걸 최우선으로 쓰고,
#       모르는 것만 이름 규칙으로 판정한다. 애매하면 '기타'로 두고 억지로 끼워넣지 않는다.
import os, re, sqlite3

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eolmanama.db")

# (하위분류, 정규식) — 위에서부터 먼저 맞는 것을 채택하므로 **순서가 규칙**이다.
#  예: '닭갈비 양념'은 소스지 닭이 아니다 → 소스 규칙이 축산 규칙보다 앞에 와야 한다.
RULES = [
    # ── 가공식품 (원물이 아닌 것부터 걸러야 오분류가 없다)
    ("가공식품", "소스·양념", r"소스|양념|드레싱|시즈닝|케첩|마요|머스타드|스리라차|다대기|육수|스톡|카레|짜장|춘장|쌈장|고추장|된장|간장|식초|맛술|미림|물엿|올리고당|설탕|소금|후추|참기름|들기름|식용유|올리브유|튀김가루|부침가루|전분|베이킹"),
    ("가공식품", "면·떡", r"면$|국수|라면|우동|파스타|스파게티|당면|쌀국수|떡$|떡볶이떡|가래떡|만두피|피자도우|도우"),
    ("가공식품", "육가공", r"햄|소시지|베이컨|스팸|패티|너겟|훈제|살라미|페퍼로니|어묵|맛살|순대"),
    ("가공식품", "유제품", r"우유|치즈|버터|생크림|크림|요거트|연유|분유|휘핑"),
    ("가공식품", "빵·디저트", r"빵|번$|도넛|와플|시럽|초코|잼|팥|앙금|아이스크림|빙수|쿠키|비스킷"),
    ("가공식품", "음료·기타가공", r"음료|주스|커피|원두|차$|시럽|탄산|컵$|용기|포장|봉투|김치$|단무지|피클|절임|통조림|캔$"),
    # ── 수산물
    ("수산물", "어류", r"고등어|갈치|명태|황태|코다리|북어|조기|굴비|삼치|꽁치|참치|연어|장어|가자미|넙치|광어|우럭|도미|병어|민어|아귀|대구|멸치|정어리|임연수|서대|가오리|홍어"),
    ("수산물", "연체류", r"오징어|낙지|문어|주꾸미|쭈꾸미|한치|갑오징어"),
    ("수산물", "패류", r"조개|전복|홍합|바지락|굴\(|^굴$|꼬막|소라|가리비|키조개|백합|해삼|멍게|성게"),
    ("수산물", "갑각류", r"새우|꽃게|대게|털게|랍스터|가재|^게$"),
    ("수산물", "해조류", r"미역|다시마|김$|^김\(|파래|톳|매생이|우뭇|해조|한천"),
    # ── 축산물
    ("축산물", "소", r"한우|소고기|쇠고기|우삼겹|차돌|양지|사태|우둔|설도|채끝|안심|등심|목심|앞다리|사골|우족|갈비|다짐육|불고기감|소막창|소대창|소곱창|도가니|꼬리"),
    ("축산물", "돼지", r"돼지|삼겹|목살|항정|가브리|족발|지육|돈까스용|뒷다리|앞다리살|등갈비|대창|막창|곱창"),
    ("축산물", "닭·계란", r"닭|치킨|염지|계란|달걀|오리|메추리"),
    # ── 농산물
    ("농산물", "곡식", r"쌀|찹쌀|보리|밀가루|현미|잡곡|콩$|콩\(|팥|녹두|고구마|감자|옥수수|귀리"),
    ("농산물", "채소", r"양파|대파|파$|배추|양배추|무$|무\(|당근|상추|깻잎|시금치|오이|호박|가지|고추|마늘|생강|부추|미나리|브로콜리|파프리카|피망|샐러드|채소|나물|버섯|콩나물|숙주|열무|알배기|얼갈이|쑥갓|청경채"),
    ("농산물", "과일", r"사과|배$|배\(|포도|딸기|수박|참외|메론|멜론|복숭아|자두|감귤|오렌지|레몬|바나나|망고|파인애플|키위|참다래|체리|블루베리|아보카도|토마토|방울토마토"),
]


def by_name(name):
    for top, sub, pat in RULES:
        if re.search(pat, name):
            return top, sub
    return None, None


# 🔴 출처(수집기)가 분류를 이미 알고 있다 — 이름 규칙보다 **출처를 먼저** 본다.
#    이름만 보면 '갓 도매'·'박 도매' 같은 aT 품목 192종이 통째로 미분류가 된다(2026-07-20 실측).
SUB_BY_KEY = {
    "ek_": ("축산물", None),      # 축평원 경락 = 국산 축산
    "cs_": ("축산물", None),      # 관세청 수입 육류
    "fw_": ("수산물", None),      # 산지 위판가
    "at_": ("농산물", None),      # aT 청과 도매시장 (해조·수산가공은 아래 이름 규칙이 덮음)
}
KAMIS_CAT = {"100": ("농산물", "곡식"), "200": ("농산물", "채소"), "300": ("농산물", "채소"),
             "400": ("농산물", "과일"), "500": ("축산물", None), "600": ("수산물", None)}


def classify(key, name, kamis_cat):
    nm_top, nm_sub = by_name(name)
    for pfx, (top, _) in SUB_BY_KEY.items():
        if key.startswith(pfx):
            # aT(청과시장)에도 해조류·수산가공이 소량 섞여 온다 → 이름이 수산이면 수산으로 보낸다
            if top == "농산물" and nm_top == "수산물":
                return nm_top, nm_sub
            return top, (nm_sub if nm_top == top and nm_sub else "기타")
    if key.startswith("kv_") and kamis_cat in KAMIS_CAT:
        top, sub = KAMIS_CAT[kamis_cat]
        return top, (sub or (nm_sub if nm_top == top and nm_sub else "기타"))
    return nm_top, nm_sub


def main():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

    # ① '경락' 표기는 축산물에만 남긴다 — 농산·수산 경매도 경락이지만 화면에선 '도매'로 충분하고,
    #    같은 꼬리표가 여기저기 붙으면 무슨 값인지 오히려 흐려진다(사용자 지시).
    n = 0
    for r in cur.execute("SELECT ingredient_key k, name FROM ingredients WHERE name LIKE '%경락%'").fetchall():
        top, _ = classify(r["k"], r["name"], None)
        if top != "축산물":
            new = r["name"].replace(" 도매(경락)", " 도매").replace("(경락)", "")
            cur.execute("UPDATE ingredients SET name=? WHERE ingredient_key=?", (new, r["k"]))
            n += 1
    print(f"① '경락' 표기 정리(축산물 외): {n}종")

    # ② 전수 재분류
    stat = {}
    unknown = []
    for r in cur.execute("""SELECT ingredient_key k, name, COALESCE(is_retail,0) ir,
                            kamis_cat, subcat FROM ingredients""").fetchall():
        top, sub = classify(r["k"], r["name"], r["kamis_cat"])
        # 시판(is_retail=1)은 완제품이므로 무조건 가공식품 (사용자 지시)
        if r["ir"] and top != "가공식품":
            top, sub = "가공식품", (sub if top == "가공식품" else "시판 완제품")

        if not top:
            unknown.append(r["name"]); top, sub = "가공식품", "기타"
        cur.execute("UPDATE ingredients SET subcat=? WHERE ingredient_key=?", (f"{top}/{sub}", r["k"]))
        stat[f"{top}/{sub}"] = stat.get(f"{top}/{sub}", 0) + 1

    con.commit()
    print("\n② 전수 재분류 결과")
    for top in ("축산물", "농산물", "수산물", "가공식품"):
        rows = sorted(((k, v) for k, v in stat.items() if k.startswith(top + "/")), key=lambda x: -x[1])
        print(f"  ■ {top}: {sum(v for _, v in rows)}종")
        for k, v in rows:
            print(f"      {k.split('/')[1]}: {v}")
    if unknown:
        print(f"\n  ⚠️ 이름으로 판정 못해 '가공식품/기타'로 둔 것: {len(unknown)}종")
        print("     ", ", ".join(unknown[:15]), "…" if len(unknown) > 15 else "")
    con.close()


if __name__ == "__main__":
    main()
