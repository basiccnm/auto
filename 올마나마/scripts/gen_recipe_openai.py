# -*- coding: utf-8 -*-
# 레시피 자동 생성 파이프라인 (2026-07-20)
#   지시서: 얼마남아\얼마남아-레시피파이프라인-지시서-2026-07-20.md
#   요리 1종당 → 텍스트 레시피 1회 + 이미지 3장(재료·조리·완성)
#
# 🔴 검증 우선(지시서 §6, 14:25 개정): 기본은 **짜장면 1종만** 생성한다.
#    확인받은 뒤에야 --all 로 확장. 이미지는 비싸므로 실수로 68종을 돌리지 않게 기본값을 좁게 뒀다.
# 🔴 유료 호출 = 사용자 사전 승인 필수(2026-07-20 사고). 임의 실행 금지.
#
# 사용법:
#   python scripts/gen_recipe_openai.py --check          # 키·모델만 확인(과금 없음)
#   python scripts/gen_recipe_openai.py                  # 검증 1종(짜장면), 텍스트만
#   python scripts/gen_recipe_openai.py --images         # 검증 1종, 텍스트+사진 3장
#   python scripts/gen_recipe_openai.py --dish 짜장면     # 특정 요리
#   python scripts/gen_recipe_openai.py --all --images   # 전체(비용 큼 — 확인 후에만)
#
# 산출물은 DB에 바로 안 넣는다. _recipes\ 에 파일로 떨군 뒤 사람이 검수하고,
# 별도 삽입 스크립트로 dishes.recipe_steps에 반영한다(생성 즉시 라이브 반영 금지).
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "openai_mod"))
import config as cfg          # noqa: E402
from client import complete, gen_images, list_models   # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_recipes")

VERIFY_DISHES = ["짜장면"]     # 지시서 §6 (2026-07-20 14:25 개정: 짜장면 1종만)

# DB 요리명 → 레시피를 뽑을 때 쓸 실제 이름.
#  DB에는 '칼국수'로만 있지만 실제로 만들 건 바지락칼국수처럼, 품목이 더 구체적인 경우가 있다.
#  DB를 건드리지 않고(슬러그·매핑 유지) 생성 내용만 구체화하려고 둔 표다. 2026-07-20.
ALIAS = {
    "칼국수": "바지락칼국수",
    "미역국": "소고기미역국",
}

# ── 시스템 프롬프트 — 지시서 §3 전문 그대로(말투 섹션 포함, 14:25판) ────────────────────────
SYSTEM = """너는 한국 요리 콘텐츠 에디터다. '올마나마'라는 사이트에 올릴 레시피를 만든다.
이 사이트는 각 요리의 재료 원가를 실시간 시세로 자동 계산해 보여주는 곳이다.
네가 쓴 재료 분량이 그대로 원가 계산에 들어가므로, 분량 정확도가 이 일의 생명이다.

## 절대 규칙 (하나라도 어기면 실패)
1. 가격·원가·비용·"~원"을 절대 쓰지 마라. 원가는 사이트가 자체 시세로 계산한다.
2. 사진·이미지를 텍스트로 언급하지 마라. 레시피 텍스트만 출력.
3. 모든 재료 분량은 정확한 숫자 단위(g, ml, 개, 큰술, 작은술)로 적어라.
   - "약간", "적당량", "1.5~2컵" 같은 모호·범위 표기 금지.
   - 큰술·작은술을 쓸 때는 반드시 g 또는 ml을 함께 병기하라. (예: 설탕 20g (1과 1/3큰술))
4. 만드는 법에 등장하는 모든 재료는 반드시 재료 목록에 분량과 함께 있어야 한다.

## 인분 규칙 (2026-07-20 개정 — 최소 구매 단위 기준)
- 🔴 기준은 '1인분'이 아니라 **메인 재료를 실제로 살 수 있는 최소 판매 단위**다.
  온라인 마트(쿠팡)에서 그 재료가 300g 팩으로 팔리면 재료 목록에도 '돼지등심 300g'으로 적어라.
  메인 재료를 판매 단위보다 잘게 쪼개지 마라(150g 같은 표기 금지). 장바구니에 그대로
  담을 수 있는 양이어야 한다.
- 인분 수는 그 메인 재료 양에서 자연스럽게 나오는 결과값이다. 먼저 인분을 정하지 마라.
- 메인 재료 = 그게 없으면 그 요리가 성립하지 않는 재료(탕수육의 돼지등심, 치킨의 닭 등).
- 🔴 메인 재료가 둘 이상인 요리는 **그 전부를 각각 최소 판매 단위로** 적어라.
  예: 소고기미역국 → 소고기(국거리)와 건미역 둘 다 판매 단위. 바지락칼국수 → 바지락과 칼국수면 둘 다.
  요리 이름에 재료가 박혀 있으면(○○미역국, ○○칼국수) 그 재료는 메인으로 본다.
- 소스·양념·향신료는 이 규칙에서 제외한다. 한 번 사두고 여러 번 쓰는 것이므로
  **실제 사용량(g·ml)** 으로 적어라. 채소·부재료도 사용량 기준으로 적는다.
- 계산된 인분 수를 제목과 [1] 재료 첫 줄에 반드시 명시하라.

## 재료·조리 원칙
- 마트에서 쉽게 구하는 재료로. 특수 도구·구하기 힘든 재료 배제.
- 주재료가 통짜(통닭 등)면 손질(부위별로 자르기) 단계를 반드시 포함하라.
- 튀김·조림용 기름처럼 다 흡수되지 않는 재료는 총량을 적되 "(튀김용)" 용도를 표기하라.
- 양념·부재료도 빠짐없이 전부 적어라. 소스의 간장·설탕·마늘 하나까지 분량으로.

## 말투 (깔끔한 친근체)
- 친근한 존댓말로 써라 — "~하세요", "~해주세요", "~좋아요".
- "~한다", "~된다" 같은 설명서·논문 말투 금지.
- 담백하고 깔끔하게. 과하게 수다스럽지 않되, 옆에서 알려주듯 다정하게.

## 출력 형식 (반드시 이 구조 그대로)
○○ 레시피 (N인분 기준)

[1] 재료 (N인분 기준)
- 성격별로 묶기: 주재료 / 튀김옷(또는 양념·소스) / 밑간 / 부재료
- 각 항목: 재료명 + 정확한 분량

[2] 만드는 법
- 번호 단계, 5~6단계 이내, 온도(℃)·시간(분) 구체적으로

[3] 실패 안 하는 팁 3가지

[4] 제목 (검색용) — 원가 각도, 가격 숫자는 비워둘 것
- 형식: "○○ 원가, 집에서 해먹으면? (레시피)"  또는  "○○, 사 먹기 vs 집에서 해먹기 (레시피)"
- 가격 숫자는 절대 넣지 마라. (코드탭이 우리 시세로 "집에서 해먹으면 8,760원?"처럼 채운다)

[5] 한 줄 소개 (검색용)
- 80자 이내. 요리명 + "집에서 해먹는 법" + "재료비" 키워드 자연스럽게. 가격 숫자 금지.

[6] 자주 묻는 질문 3가지 (FAQ)
- 실제 검색할 법한 질문 3개 + 답. 조리 팁·재료 대체·보관법. 가격 숫자 금지."""

# ── 이미지 — 지시서 §4 개정판(2026-07-20 14:25) ────────────────────
#  🔴 사진 3장을 **각각 따로** 뽑는다. 합치거나 크롭하지 않는다.
#     (14:06판의 '3분할 한 장 → 크롭'은 폐기됨. 배치·가공은 페이지에 올릴 때 코드가 한다.)
# ⚠️ 배경을 여기에 박지 않는다(2026-07-20 14:34 개정): '원목 도마' 고정 때문에 중식·양식이
#    전부 같은 나무 상판으로 나왔다. 배경은 요리 국적에 맞게 PROMPT_BUILDER가 정한다.
#    품질 문구도 '매끈한 스톡사진'이 아니라 '진짜 카메라로 찍은 것 같은' 쪽으로.
# 🔆 2026-07-20 개정: 결과물이 계속 어두침침하게 나와서 밝기를 STYLE에 못박았다.
#    (기존 'natural imperfect lighting' + 아래 설정별 'dim' 지시가 겹쳐 전부 어두웠음)
STYLE = ("candid photorealistic food photography, shot on a real camera, BRIGHT and clearly "
         "well-lit scene, abundant soft daylight, clean airy exposure, light background, "
         "no dark or moody shadows, nothing underexposed, authentic textures, subtle "
         "real-world details such as steam, oil sheen, moisture and crumbs, slight depth of "
         "field. Not glossy, not over-saturated, not CGI, not an over-polished stock photo. "
         "No hands, no people, no text, no letters, no numbers, no captions, no watermark, "
         "no logo.")

# 레시피(한국어)를 읽어 3장의 영어 프롬프트를 만들게 하는 지시.
#  재료의 '현실적 준비 상태'(닭=부위별 조각, 마늘=다진 것, 시판품=포장 뜯은 상태)와
#  조리컷의 '조리 도구·환경'을 모델이 레시피에서 직접 판단하게 한다 — 지시서 §4.
PROMPT_BUILDER = """You turn a Korean recipe into THREE separate English image-generation prompts.

Output exactly three prompts, each on its own line, separated by a line containing only ---
No numbering, no labels, no explanation, no quotes. Just the three prompts.

LIGHTING — applies to ALL three photos, overrides every setting choice below:
- Every photo must be BRIGHT, clearly lit and easy to read. Plenty of soft daylight,
  clean and airy, light-toned surfaces and background.
- NEVER dim, moody, dark, shadowy, candle-lit, night-time or underexposed. Even for
  restaurant settings, imagine the lights fully on and daylight coming in from a window.

FIRST decide the SETTING from the dish's cuisine, and write it into all three prompts.
- Do NOT default to a plain light-wood table. Pick what suits this specific dish.
- Korean-Chinese (jjajangmyeon, jjamppong, tangsuyuk) -> Chinese restaurant mood: polished
  stainless or light lacquered table, black or deep-blue rimmed ceramic bowls, steel wok,
  brightly lit dining room with warm but strong light.
- Korean home food (jjigae, guk, bokkeum) -> Korean table setting: earthenware ttukbaegi,
  stainless or brass side-dish bowls, patterned tablecloth, bright kitchen daylight.
- Western (pasta, steak, burger) -> European kitchen: marble or slate counter, white porcelain,
  linen napkin, bright daylight.
- Japanese (sushi, udon, donkatsu) -> Japanese setting: matte ceramic, bamboo mat, light grey
  or pale wood, bright soft side light.
- Fried chicken / snack food -> casual modern kitchen or diner table, paper liner, metal tray,
  bright overhead light.
- Whatever you pick, the SAME setting must run through all three photos, and all three must
  be bright.

PROMPT 1 (ingredients photo):
- Top-down flat lay showing EVERY ingredient from the recipe in one frame.
- Show them as they would REALISTICALLY look after shopping and prepping for this dish.
  Not whole raw lumps. Examples: whole chicken -> cut into parts (wings, drumsticks, thighs);
  vegetables -> already sliced or diced; green onion -> finely chopped; garlic -> minced paste
  in a small dish (NOT whole bulbs); packaged products (rice cake, fish cake, sauce, noodles,
  dough) -> opened out of the package, ready to use. Korea sells much produce pre-trimmed.
- Ask yourself: "if someone actually shopped for this dish, what would be on the table?"

PROMPT 2 (cooking photo):
- The actual cooking equipment and environment must be clearly visible.
- Deep-fried -> food frying INSIDE hot oil in a deep pot on a visible gas flame, oil bubbles,
  rising steam. Soup/stew -> vigorously boiling in a pot. Stir-fry -> tossing in a wok with
  visible heat and flame. Noodles -> boiling in water or sauce being stirred in a wok.
- NEVER show the food plated here. Plated belongs to prompt 3 only.

PROMPT 3 (finished photo):
- The finished dish plated in the serving vessel that suits this cuisine, appetizing,
  in the setting you chose above.

Keep the three photos visually consistent: the same setting, tableware family and lighting
you chose at the start. Make each photo read like a real photograph someone took in that
kitchen, not a polished studio stock image."""


def build_image_prompts(name, recipe_text):
    """레시피 본문 → 영어 프롬프트 3개(재료·조리·완성). 지시서 §4."""
    raw = complete(PROMPT_BUILDER,
                   f"Dish (Korean): {name}\n\nRecipe:\n{recipe_text}\n\n"
                   f"Now write the three English image prompts, separated by ---")
    # 구분 방식을 여러 개 시도해 '정확히 3블록'이 나오는 걸 채택한다.
    #  2026-07-20: 루나가 본문은 빈 줄로 나누고 '---'는 맨 끝에 하나만 붙여서 파싱이 터졌다.
    #  모델마다 형식이 흔들리므로 한 방식에 의존하지 않는다.
    import re
    candidates = [
        re.split(r"\n\s*-{3,}\s*\n", raw),   # 줄 하나가 통째로 --- 인 경우
        raw.split("---"),                    # 아무데나 --- 인 경우
        re.split(r"\n\s*\n", raw),           # 빈 줄로만 나눈 경우
    ]
    for c in candidates:
        blocks = [p.strip().strip("-").strip() for p in c]
        blocks = [p for p in blocks if len(p) > 40]   # 빈 줄·꼬리 구분자·라벨 조각 제거
        if len(blocks) == 3:
            return [p + " " + STYLE for p in blocks]
    raise RuntimeError("이미지 프롬프트 3개 파싱 실패 — 원문 앞부분: " + raw[:300])


def check():
    """과금 없는 사전 점검: 키 + 모델 존재 확인."""
    try:
        cfg.api_key()
        print("✅ API 키: 확인됨 (값은 출력하지 않음)")
    except RuntimeError as e:
        print("❌", e)
        return False
    try:
        gpts = list_models("gpt")
        print(f"✅ 계정에서 쓸 수 있는 gpt* 모델 {len(gpts)}종")
        ok_t = cfg.TEXT_MODEL in gpts
        print(("✅ " if ok_t else "❌ ") + f"텍스트 모델 '{cfg.TEXT_MODEL}' " +
              ("사용 가능" if ok_t else "목록에 없음 → .env의 OPENAI_TEXT_MODEL을 바꿔야 함"))
        if not ok_t:
            print("   후보:", ", ".join(gpts[:15]) + (" ..." if len(gpts) > 15 else ""))
        imgs = [m for m in list_models() if "image" in m or "dall" in m]
        ok_i = cfg.IMAGE_MODEL in imgs
        print(("✅ " if ok_i else "❌ ") + f"이미지 모델 '{cfg.IMAGE_MODEL}' " +
              ("사용 가능" if ok_i else f"목록에 없음 → 후보: {', '.join(imgs) or '(없음)'}"))
        return ok_t
    except Exception as e:
        print("❌ 모델 목록 조회 실패:", str(e)[:200])
        return False


def dish_list(args):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT name, slug, serving FROM dishes ORDER BY name").fetchall()
    con.close()
    if args.dish:
        want = [x.strip() for x in args.dish.split(",") if x.strip()]
        got = [r for r in rows if r["name"] in want]
        miss = set(want) - {r["name"] for r in got}
        if miss:
            _die(f"DB에 없는 요리: {', '.join(sorted(miss))}")
        return got
    if args.all:
        return rows
    return [r for r in rows if r["name"] in VERIFY_DISHES]


def _die(msg):
    print("❌", msg); sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="키·모델만 확인(과금 없음)")
    ap.add_argument("--all", action="store_true", help="전체 요리(비용 큼)")
    ap.add_argument("--dish", help="특정 요리명")
    ap.add_argument("--images", action="store_true", help="이미지 3장도 생성")
    ap.add_argument("--regen", action="store_true", help="기존 텍스트가 있어도 다시 생성")
    args = ap.parse_args()

    if args.check:
        sys.exit(0 if check() else 1)
    if not check():
        print("\n사전 점검 실패 — 위 항목을 고친 뒤 다시 실행하세요.")
        sys.exit(1)

    dishes = dish_list(args)
    n_img = len(dishes) * 3 if args.images else 0
    print(f"\n대상 {len(dishes)}종 · 텍스트 {len(dishes)}회" +
          (f" · 이미지 {n_img}장" if n_img else " · 이미지 생략"))
    if args.all:
        if input("전체 실행은 비용이 큽니다. 진행하려면 'yes' 입력: ").strip() != "yes":
            print("취소"); return

    os.makedirs(OUT, exist_ok=True)
    for d in dishes:
        name, slug = d["name"], d["slug"]
        label = ALIAS.get(name, name)   # 생성에 쓰는 이름(DB명과 다를 수 있음)
        print(f"\n=== {name} ===" + (f"  → '{label}'로 생성" if label != name else ""))
        p = os.path.join(OUT, f"{slug}.md")
        # 이미 만든 레시피는 재생성하지 않는다(2026-07-20): 검수 중인 텍스트가 바뀌면 안 되고,
        #  이미지만 추가로 뽑을 때 텍스트 비용을 또 낼 이유도 없다. 다시 만들려면 --regen.
        if os.path.exists(p) and not args.regen:
            txt = open(p, encoding="utf-8").read()
            print(f"  텍스트: 기존 파일 재사용 ({len(txt)}자)  ※ 새로 만들려면 --regen")
        else:
            txt = complete(SYSTEM, f"{label} 레시피를 위 형식대로 작성해줘.")
            with open(p, "w", encoding="utf-8") as f:
                f.write(txt)
            print(f"  텍스트 저장: {p}  ({len(txt)}자)")

        # 자체 점검 — 지시서의 '절대 규칙' 위반 자동 탐지
        bad = []
        if "원" in txt and any(c.isdigit() for c in txt.split("원")[0][-6:]):
            bad.append("가격 표기(숫자+원) 의심")
        for w in ("약간", "적당량", "사진", "이미지"):
            if w in txt:
                bad.append(f"금지어 '{w}'")
        print("  규칙 점검:", "✅ 통과" if not bad else "⚠️ " + " / ".join(bad))

        if args.images:
            img_dir = os.path.join(OUT, "img")
            prompts = build_image_prompts(label, txt)
            with open(os.path.join(OUT, f"{slug}.imgprompt.txt"), "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(prompts))
            # 지시서 §4(14:25): 3장 각각 따로. 합치거나 크롭하지 않는다.
            paths = gen_images(prompts, img_dir, slug, size="1024x1024")
            print(f"  사진 {len(paths)}장 완료 (재료·조리·완성)")

    print(f"\n완료. 산출물: {OUT}")
    print("※ DB에는 아직 반영하지 않았습니다. 검수 후 삽입 스크립트로 넣으세요.")


def _ing_of(slug):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT i.name nm FROM dish_ingredients di
        JOIN dishes d ON d.id=di.dish_id JOIN ingredients i ON i.ingredient_key=di.ingredient_key
        WHERE d.slug=? ORDER BY di.sort_order""", (slug,)).fetchall()
    con.close()
    return rows


if __name__ == "__main__":
    main()
