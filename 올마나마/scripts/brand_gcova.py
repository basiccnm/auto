# -*- coding: utf-8 -*-
"""지코바치킨(gcova) 전용 메뉴판 수집기  →  data/brand_menu_list/gcova.json

⛔ DB 를 import 하지 않는다. JSON 파일 하나만 만든다.

■ 어떤 길로 뚫었나 (2026-07-28)
  http://www.gcova.co.kr/  는 468바이트 프레임셋이다.
      <frame src="up.html">        ← 404 (죽은 프레임)
      <frame src="re_main.htm">    ← 실제 내용
  re_main.htm 의 상단 네비 m_3 (= 메뉴소개) 아래에 하위 5개가 걸려 있고,
  각 메뉴 페이지는 sub_3_1 / sub_3_2 / sub_3_6 / sub_3_3 / sub_3_4 .htm 이다.
  (sub_3_5 「지코바 윙,스틱」은 HTML 주석으로 막혀 있다 = 현재 판매 안 함 → 넣지 않는다)

  인코딩은 euc-kr. 주소는 전부 프레임셋·네비의 href 를 그대로 따라간 것이고 추측한 것이 없다.

■ 자동으로 읽은 것 (본문 텍스트 — 1순위)
  - 카테고리 이름  : <td class="sub_title">양념치킨</td>  같은 본문 텍스트
  - 옵션 라벨/가격 : <td class="sub_price">반반</td><td class="main_price">￦ 23,500</td>
  - 조리 전 중량   : 「조리 전 중량 정보 … 950g 이상」 팝업 본문
  ⇒ 가격은 이미지 판독이 아니라 **글자**로 얻었다. 판독 때문에 비운 값은 없다.

■ 사람이 눈으로 읽은 값 (이미지 판독) — 아래 표. 다음 사람이 대조하라.
  가격·메뉴 구조에는 쓰지 않았고, 「원본 화면이 실제로 이렇게 보인다」는 대조용이다.

  ┌ 왼쪽 네비 탭 라벨 (글자가 아니라 그림이다) ─────────────────────────────
  │ images/left/sub_3_1.jpg  →  "지코바 양념치킨"
  │ images/left/sub_3_2.jpg  →  "지코바 소금구이치킨"
  │ images/left/sub_3_6.jpg  →  "지코바 순살"
  │ images/left/sub_3_3.jpg  →  "지코바 윙"
  │ images/left/sub_3_4.jpg  →  "지코바 스틱"
  │   (본문 <sub_title> 텍스트는 「지코바 」 없이 양념치킨/소금구이치킨/순살/윙/스틱.
  │    카테고리 이름은 오독 위험이 없는 **본문 텍스트** 쪽을 썼다)
  ├ 메뉴 상세 이미지 안에 인쇄된 정식 상품명 ───────────────────────────────
  │ images/menu/menu1.jpg  →  "지코바 양념치킨 (한마리)"   (매콤한 맛/순한 맛)
  │ images/menu/menu2.jpg  →  "지코바 소금구이 (한마리)"
  │ images/menu/menu6.jpg  →  "지코바 순살"               (순한맛/보통맛/매운맛)
  │ images/menu/menu3.jpg  →  "지코바 윙 (날개 + 봉)"     (매콤한 맛/순한 맛/소금구이)
  │ images/menu/menu4.jpg  →  "지코바 스틱 (다리)"        (순한맛/보통맛/매운맛)
  ├ 영양정보 팝업 이미지 (images/pop_info/info_1~5.jpg) ────────────────────
  │ 열량/나트륨/당류/지방/포화지방/단백질 표만 있다. **원산지 표기 없음**
  └ 푸터 images/bottom/address.jpg → "경상남도 양산시 어곡공단로 185 (주)지코바"

■ 원산지
  공식 홈페이지 전 페이지(sub_1_1~4 · sub_2_1~3 · sub_3_* · sub_4_1~3 · sub_5_2)를
  「원산지·국내산·브라질·수입·원재료·알레르기·닭고기」로 훑었지만 **한 건도 없다.**
  메뉴 이미지·영양정보 팝업 이미지에도 원산지 문구가 없다.
  → origin_note = None (추측해서 채우지 않는다)

■ 가격 성격
  홈페이지가 「홀/배달」을 구분해 적지 않는다. 브랜드 공식 표기가라 그대로 담았다.
"""
import sys, os, re, json, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://www.gcova.co.kr/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "gcova.json")

# 프레임셋 → re_main.htm → 상단/좌측 네비에 적힌 순서 그대로. 추측한 주소 없음.
PAGES = ["sub_3_1", "sub_3_2", "sub_3_6", "sub_3_3", "sub_3_4"]
# sub_3_5(「윙,스틱」)는 네비에서 <!-- --> 로 막혀 있어 제외

# 사람이 눈으로 읽은 값 — 대조표 (수집 결과에는 쓰지 않는다)
HUMAN_READ = {
    "sub_3_1": {"nav_img_label": "지코바 양념치킨",   "menu_img_title": "지코바 양념치킨 (한마리)"},
    "sub_3_2": {"nav_img_label": "지코바 소금구이치킨", "menu_img_title": "지코바 소금구이 (한마리)"},
    "sub_3_6": {"nav_img_label": "지코바 순살",       "menu_img_title": "지코바 순살"},
    "sub_3_3": {"nav_img_label": "지코바 윙",         "menu_img_title": "지코바 윙 (날개 + 봉)"},
    "sub_3_4": {"nav_img_label": "지코바 스틱",       "menu_img_title": "지코바 스틱 (다리)"},
}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=40).read().decode("euc-kr", "replace")


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


def check_frameset():
    """프레임셋의 src 를 실제로 읽어서 re_main.htm 이 맞는지 확인한다(주소 추측 금지)."""
    t = fetch(BASE)
    srcs = re.findall(r'<frame[^>]*src=[\'"]([^\'"]+)[\'"]', t, re.I)
    print("frameset src:", srcs)
    if "re_main.htm" not in srcs:
        raise SystemExit("프레임셋 구조가 바뀌었다 — 손으로 다시 확인할 것: %s" % srcs)
    return "re_main.htm"


def parse_page(slug):
    t = fetch(BASE + slug + ".htm")

    heading = strip_tags(re.search(r'class="sub_title"[^>]*>(.*?)</td>', t, re.S).group(1))

    img = re.search(r'<img src="(images/menu/[^"]+)"', t)
    image_url = BASE + img.group(1) if img else None

    w = re.search(r"조리 전 중량[\s\S]{0,400}?([\d,]+g 이상)", t)
    weight = w.group(1) if w else None

    # ⚠️ 영양정보 팝업 레이어의 「950g 이상」 칸도 class="sub_price" 라서
    #    문서 전체를 훑으면 그게 첫 메뉴의 옵션 라벨로 새어 들어온다(실제로 났던 버그).
    #    가격표는 항상 메뉴 이미지 **뒤**에 오므로 그 뒤만 본다.
    body = t[t.find(img.group(1)):] if img else t

    # 본문 순서 그대로 (라벨, 가격) 짝짓기
    rows, label = [], ""
    for m in re.finditer(r'<td[^>]*class="(sub_price|main_price)"[^>]*>(.*?)</td>', body, re.S):
        kind, inner = m.group(1), strip_tags(m.group(2))
        if kind == "sub_price":
            label = inner
        else:
            p = re.search(r"[￦₩]\s*([\d,]+)", inner)
            if p:
                rows.append((label, int(p.group(1).replace(",", ""))))
                label = ""
    return heading, image_url, weight, rows


def main():
    check_frameset()

    cats, menus, order = [], [], {}
    for slug in PAGES:
        heading, image_url, weight, rows = parse_page(slug)
        detail = BASE + slug + ".htm"
        cats.append({"name": heading, "parent": None, "ext_id": slug})
        order[heading] = 0
        print("[%s] %s  중량=%s  가격행=%d  %s"
              % (slug, heading, weight, len(rows), HUMAN_READ[slug]["menu_img_title"]))
        for label, price in rows:
            # 화면상 메뉴명 = 카테고리 제목 + 옵션 라벨.
            # 이 사이트는 옵션 라벨만 찍어놔서(「반반」·「소금구이」) 라벨만 쓰면
            # 카테고리가 다른 서로 다른 메뉴가 같은 이름으로 합쳐진다.
            # 사이트 자신도 영양정보 팝업에서 「순살양념구이」처럼 붙여서 부른다.
            name = heading if not label else "%s %s" % (heading, label)
            menus.append({
                "name": name, "price": price, "price_source": "official",
                "price_note": "공식 홈페이지 본문 텍스트 표기 — " + detail,
                "weight_raw": weight, "origin_raw": None, "allergy_raw": None,
                "detail_url": detail, "image_url": image_url, "ext_id": None,
                "cats": [[heading, order[heading]]],
            })
            print("    - %-14s %s원" % (name, format(price, ",")))
            order[heading] += 1

    if not menus:
        raise SystemExit("메뉴 0개 — 저장하지 않는다")

    # 이름 기준 중복 합치기 (지코바는 중복 없음 — 방어용)
    merged = {}
    for m in menus:
        if m["name"] in merged:
            merged[m["name"]]["cats"] += m["cats"]
        else:
            merged[m["name"]] = m

    data = {
        "brand": "지코바치킨", "slug": "gcova",
        "source": BASE + "re_main.htm  (프레임셋 " + BASE + " → mainFrame)",
        "collected_at": "2026-07-28",
        "origin_note": None,          # 공식 홈페이지 어디에도 원산지 표기가 없다
        "cats": cats,
        "menus": list(merged.values()),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("\n저장: %s  (카테고리 %d · 메뉴 %d)" % (OUT, len(cats), len(merged)))


if __name__ == "__main__":
    main()
