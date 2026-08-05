# coupang_eats — 쿠팡이츠 앱 화면으로 배달가 수집

배달앱(쿠팡이츠) 화면의 **텍스트 노드**를 읽어 메뉴·가격을 받는다. OCR 아님 — `uiautomator`
가 주는 화면 글자를 그대로 읽어 오독이 없고, 차단도 없다(정상적으로 앱을 쓰는 것).

공식 홈페이지에 가격이 없는 브랜드(파바·뚜레·던킨·공차 등)나, 홀 가격만 있고 배달 메뉴를
알고 싶을 때 쓴다. 2026-07~08 올마나마에서 30여 개 브랜드를 이걸로 받았다.

## 준비 (에뮬/폰 1대, adb 연결)

```bash
# 한글 검색을 위한 ADBKeyboard (에뮬 기본 IME 는 중국어뿐)
adb install ADBKeyboard.apk        # github.com/senzhk/ADBKeyBoard
adb shell ime enable com.android.adbkeyboard/.AdbIME
adb shell ime set    com.android.adbkeyboard/.AdbIME
```
`ADB` 경로는 각 스크립트 상단 상수에서 맞춘다(기본 `D:\Android\Sdk\platform-tools\adb.exe`).

## 순서

```bash
# ① 브랜드 검색 → 가게 진입 (지금 다른 가게에 있으면 뒤로 나가서)
python ce_search_enter.py emulator-5554 "한신포차" "한신포차"

# ② 그 가게 화면을 원본 그대로 수집 (스크롤하며 화면마다 append 저장)
python brand_coupangeats.py <slug> emulator-5554
#   → data/brand_menu_list/_ce_raw/<slug>.tsv   (화면번호·y·x·글자)

# ③ 원본을 메뉴·가격으로 가공 (파서만 고치면 몇 번이든 다시 가능)
python brand_coupangeats_parse.py <slug>
#   → data/brand_menu_list/<slug>_delivery.json
```

## 4대 함정 (2026-07-31 하루에 다 겪음)

1. **검색 결과 목록에서 수집 금지.** 「광고」에 걸려 30~80줄로 끝난다. 반드시 가게 상세로
   진입(`ce_search_enter.py` 가 「매장∙원산지정보」로 확인) 후 수집.
2. **END_MARK 에 「추천해요」 단독 금지** — 메뉴·리뷰의 「추천」에 걸려 첫 화면에서 끝난다.
   `^광고$|비슷한 맛집|맛집 추천` 으로 좁혔다.
3. **두 기기 동시 수집 금지** — adb 충돌로 swipe 가 씹혀 첫 화면(48줄)만 남는다. 순차로.
4. **그리드 레이아웃** — 한 줄에 메뉴 여러 개(x=36·252·468·684)면 이름·가격이 같은 세로열에
   온다. 파서가 `abs(xx-x)<90` 같은 열에서 위 줄을 이름으로 잡는다.

## 주의

- 가격은 **배달가**다 — 배달비·수수료가 얹혀 매장가보다 높고, **지역·지점마다 다르다.**
  붙이는 쪽 화면에 반드시 안내를 남긴다.
- 가게 이름이 「맛잇어용」처럼 리뷰로 잘못 잡히기도 한다 — 메뉴가 브랜드와 맞는지 눈으로 확인.
- 원본(`_ce_raw/*.tsv`)은 지우지 말 것. 파서만 고쳐 다시 돌리면 폰/에뮬 없이 재가공된다.
