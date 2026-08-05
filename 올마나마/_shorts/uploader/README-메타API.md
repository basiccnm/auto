# 인스타·스레드 API 발행 (2026-07-24 구축)

브라우저 자동화(Playwright)가 아니라 **공식 API**로 올린다.
기존 `upload_ig.py`(릴스, 브라우저 방식)와는 별개다 — 그건 그대로 둔다.

## 연결된 것

| | 인스타 | 스레드 |
|---|---|---|
| 계정 | `olma_nama` | `dnd_mbol` |
| 앱 | olmanama (앱 ID `975523475517795`) | 같은 앱 |
| 주소 | graph.instagram.com | graph.threads.net |
| 권한 | 5종(게시·댓글·지표·DM·기본) | 11종 전부 |
| 토큰 | 60일, 갱신 가능 | 60일, 갱신 가능 |

⚠️ **스레드 계정이 인스타와 다르다**(`dnd_mbol`). 올마나마용 스레드 계정을 따로 만들면 그때 바꿀 것.

## 파일

```
.env                  토큰·ID (🔴 공유 금지)
meta_common.py        공통 — .env 읽기, API 호출
refresh_token.py      토큰 갱신
post_ig_carousel.py   인스타 카드뉴스(캐러셀)
post_threads.py       스레드 글
queue_cards.json      발행 목록
```

## 쓰는 법

```
python post_ig_carousel.py                        미리보기
python post_ig_carousel.py --publish              인스타 발행
python post_threads.py --from-queue --publish     스레드 발행
python post_threads.py --text "한 줄 글" --publish  글만 바로
python refresh_token.py                           토큰 갱신
```

## 🔴 제일 중요한 제약 — 이미지는 공개 URL이어야 한다

**API는 로컬 파일을 못 받는다.** 이미지가 인터넷에 떠 있어야 하고, 그 주소를 넘긴다.

```
① 카드 이미지를 olmanama.com 에 올린다 (예: /cards/xxx.jpg)
② queue_cards.json 의 images 에 그 주소를 적는다
③ 발행한다
④ 발행되면 인스타가 이미지를 자기 서버로 복사하므로 원본은 지워도 된다
```

올마나마는 파이썬 생성기 → `_dist` → wrangler deploy 구조다.
카드 이미지를 `_dist`에 같이 넣어 배포하면 공개 주소가 생긴다.

## 🔴 토큰 만료 — 이것만 신경 쓰면 된다

- 60일짜리다. `refresh_token.py` 를 돌리면 다시 60일이 된다(횟수 제한 없음)
- **완전히 만료되면 갱신도 안 된다** — 앱 대시보드에서 새로 발급받아 `.env`에 손으로 넣어야 한다
- 그러니 **월 1회 스케줄러**를 걸어두는 게 안전하다 (한두 번 걸러도 60일 안에 들어옴)
- 발급 후 24시간이 지나야 갱신된다(메타 정책)

작업 스케줄러 등록 — 관리자 PowerShell에서 한 번만:

```
schtasks /create /tn "메타토큰갱신" /sc monthly /d 1 /st 10:00 /tr "python \"C:\Users\hardb\Desktop\블로그수입관련\올마나마\_shorts\uploader\refresh_token.py\""
```

## 알아둘 제약

| | 인스타 캐러셀 | 스레드 |
|---|---|---|
| 이미지 | 2~10장 | 최대 10장(선택) |
| 글자 | 캡션 2,200자 | **500자** |
| 해시태그 | 30개 | 본문에 포함 |
| 권장 비율 | 1:1 정사각 JPEG | 자유 |

스레드가 500자라 인스타 캡션을 그대로 못 쓴다 — `queue_cards.json` 에 `th_text` 를 따로 둔다.

## 앱 심사는 필요 없다

앱이 **개발 모드**지만, 등록된 테스터 계정(우리 계정)으로는 게시가 정상 작동한다.
심사는 *남의 계정*을 우리 앱에 연결시킬 때만 필요하다 — 우리는 해당 없음.

⚠️ 다만 키워드 검색·프로필 조회처럼 **남의 데이터를 읽는 권한**은 개발 모드에서 제한될 수 있다.
실제로 호출해봐야 안다. 게시 기능부터 쓰고 나중에 확인할 것.

## 대시보드에서 헷갈렸던 것 (기록)

- 권한 "추가" 버튼을 누르면 **"문제가 발생했습니다" 에러가 뜨는데 실제로는 추가된다.**
  새로고침해서 확인할 것. 두세 번 눌러도 중복 안 된다
- 대시보드 권한 목록의 ✅/❌ 표시와 **토큰에 실제 부여된 권한이 다르다.**
  진짜 확인은 `refresh_access_token` 응답의 `permissions` 필드로 한다
- 인스타 권한 중 `instagram_business_` 로 시작하지 않는 것들(`instagram_basic`,
  `pages_*`, `ads_*` 등)은 **구 Facebook 로그인 방식용**이라 우리 설정에선 작동하지 않는다
