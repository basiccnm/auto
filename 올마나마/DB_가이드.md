# 얼마남아 DB 가이드 (data/eolmanama.db)

> 이 파일은 **DB를 처음 보는 사람이 값의 의미를 오해하지 않도록** 만든 문서다.
> 2026-07-21 작성. 실제로 오해가 발생한 지점(★)을 우선 적었다.

---

## ★ 헷갈리기 쉬운 것 — 먼저 읽을 것

### 1. 원가가 **두 개**다

| 컬럼 (`menus`) | 뜻 | 기준 |
|---|---|---|
| `est_cost` / `cost_ratio` | **장보기 원가** | 마트에서 사면 얼마 = **소매가** |
| `store_cost` / `store_ratio` | **매장 원가** | 가게가 납품받으면 얼마 = **도매가** |

예) BBQ 황금올리브치킨 — 판매 23,000 / `est_cost` 7,455(32.4%) / `store_cost` 6,264(27.2%)

**어느 쪽을 쓰느냐가 결론을 바꾼다.** 쇼츠·사이트에서 무엇을 쓰는지 반드시 통일할 것.
(2026-07-21 기준: 쇼츠는 **소매(`est_cost`)** 로 통일)

### 2. "등록가"는 도매가 아니라 **소매가**다

| 컬럼 (`ingredients`) | 화면 표기 | 실제 의미 |
|---|---|---|
| `manual_price` | "등록가" | **소매가.** 조사해서 확정한 값 |
| `wholesale_price` | "도매가" | 소매 × 계수(카테고리별 0.7~0.85) |
| `naver_price` | "네이버 조사가" | **원시 참고값. 그대로 쓰면 안 됨** |

`manual_price`라는 **기술 컬럼명이 화면에 "등록가"로 그대로 노출**되어 소매인지 도매인지
안 보이게 됐다. 화면 표기를 "소매가"로 바꾸는 게 맞다(미처리).

### 3. `naver_price`는 검수 전 원시값이다

네이버쇼핑에서 긁은 값이라 **단위·포장이 튄다.** 검수해서 `manual_price`로 확정하는 재료일 뿐.

실제로 얼마나 튀는지:
- 치킨무 — 등록 500원 vs 네이버 5,480원 (박스 단위가 잡힘)
- 올리브유 — 등록 20,217원 vs 네이버 57,800원 (고급품이 잡힘)

### 4. 경락가는 우리가 쓸 값이 아니다

산지 → **대도매 경매(경락)** → 중도매 → 소도매 → 식당. 경락은 대도매만 접근 가능하다.
가게 입장의 "도매"는 **소도매에서 넘어오는 값**. 경락가를 도매 자리에 넣으면 안 된다.
(2026-07-20에 경락 기반 119종을 제거함)

### 5. `dishes`는 매 실행 지워지고 다시 생긴다

`gen_dishes.py`가 `dishes` / `dish_ingredients` / `dish_menus`를 **DELETE 후 재생성**한다.
→ 여기에 직접 쓰면 다음 실행에 날아간다. **`dish_def` / `dish_def_ingredient`에 써야 살아남는다.**

---

## 테이블 지도

### 프랜차이즈 쪽 (브랜드 실제 메뉴)

| 테이블 | 행수 | 내용 |
|---|---|---|
| `categories` | 13 | 치킨·피자·버거·떡볶이… |
| `brands` | 122 | BBQ·교촌·bhc… + 가맹점수/평균매출(공정위 정보공개서) |
| `menus` | 378 | 메뉴 + 판매가 + 원가 2종 + 레시피 |
| `menu_ingredients` | 2,082 | 메뉴별 재료·분량·줄원가(`line_cost` 소매 / `wholesale_cost` 도매) |

### 집밥 레시피 쪽

| 테이블 | 행수 | 내용 |
|---|---|---|
| `dish_def` | 69 | **요리 정본.** 재생성에서 살아남는 곳 |
| `dish_def_ingredient` | 383 | 요리별 재료 |
| `dishes` / `dish_ingredients` / `dish_menus` | 68 / 381 / 272 | **자동 생성물.** 직접 쓰지 말 것 |

### 재료·가격

| 테이블 | 행수 | 내용 |
|---|---|---|
| `ingredients` | 355 | **재료 마스터.** 가격의 원천 |
| `price_history` | 110 | 날짜별 가격 이력 (KAMIS 등) |
| `ingredient_alias` | 120 | 별칭 → 재료키 (매칭 학습용) |
| `ingredient_pack` | 55 | 포장 단위 (1박스 = 몇 kg) |
| `ingredient_subst` | 19 | 대체 안내 문구 |
| `naver_offer` | 9,379 | 네이버 수집 원본 (검수 전) |

### 기타

`brand_origins`(31) 원산지 · `banners`(0) · `recipe_draft`(0) · `gen_job`(0) 관리페이지용

---

## 자주 쓰는 조회

```sql
-- 원가율 낮은 순 = 제일 많이 남기는 메뉴
SELECT b.name, m.name, m.sell_price, m.est_cost, m.cost_ratio,
       m.sell_price - m.est_cost AS margin
FROM menus m JOIN brands b ON m.brand_id = b.id
WHERE m.sell_price > 0 AND m.est_cost > 0
ORDER BY m.cost_ratio ASC LIMIT 20;

-- 특정 메뉴의 재료 구성
SELECT i.name, mi.amount, mi.unit, mi.line_cost, mi.wholesale_cost
FROM menu_ingredients mi
JOIN menus m ON mi.menu_id = m.id
JOIN ingredients i ON mi.ingredient_key = i.ingredient_key
WHERE m.name = '황금올리브치킨';

-- 재료 가격 3종 비교 (소매 / 도매 / 네이버원시)
SELECT name, manual_price, wholesale_price, naver_price, base_unit
FROM ingredients WHERE name LIKE '%올리브%';
```

---

## 처리 완료 (2026-07-21)

- **올리브블랜딩유 신설** — BBQ는 EV50% + 해바라기유50% 블렌드로 튀긴다.
  업소용 18L 실측: 올리브유 20만원(11,111/L) · 해바라기유 6.5만원(3,611/L) → **블렌드 7,361원/L**
  BBQ 3종(황금올리브·반반·양념)의 튀김유를 교체. 치킨 1마리 흡수분 144ml = **1,060원**
  ⚠️ 이 값은 실측치다. **계수를 또 곱하지 말 것**
- **해바라기유 신설** (3,611원/L)
- **도매가 미기입 45종 전부 채움** — 가공품 ×0.80 / 농축산물 ×0.75 (실측 평균 0.803 / 0.758)
  `생닭(육계)` 도매 **4,611원** 확보

## 알려진 데이터 문제 (미처리)

- **화면의 "등록가" 표기** → "소매가"로 바꿔야 함
- **치킨무 500원**이 소매·도매 어느 쪽도 아닌 애매한 값 (시중 소매 1,000 / 납품 370~400)
- **황금올리브 닭** — `염지닭 10호`(도매 5,100)로 들어가 있음. 이대로 유지.
  (※ 이전 판에 "대표는 절단닭이 아니라 생닭이라고 함"이라고 적혀 있었으나
   **그건 AI가 지어낸 말이었고 대표 발언이 아니다.** 2026-07-21 정정)
- B2B 가격 미확보 60여 종 (가공부재료·부재료·속재료는 확보 불가로 판단)
- ⏰ **네이버 쇼핑 API가 2026-07-31 24:00 종료.** 그 전에 재료 가격 전량 수집 필요

---

## 백업

변경 전 반드시 `data/backup/eolmanama_YYYYmmdd_HHMMSS.db`로 복사.
배포 전 `healthcheck.py` 통과가 관문.
