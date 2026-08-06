// 마라탕 1편 대사 — 셀프마라탕 A/B 업태 비교 (2026-07-22)
//
// 🔴 왜 Talk.jsx에서 빼냈나(2026-07-23): Talk.jsx가 1,125줄이라 대사 한 줄 고치려고
//    파일 전체를 읽어야 했다. 토큰이 반복해서 크게 나갔다. 대사는 편마다 통째로 바뀌므로
//    편별 파일로 분리한다. 새 편은 lines_marat2.js 를 만들고 Talk.jsx의 import만 바꾼다.
//
// ── 화면 객체 번호 (대표님과 소통용 고정 체계, 2026-07-23 합의) ──────────
//    대표님이 "12초 ③ 내려" 하면 그 시점 화면에서 아래 번호로 대상을 찾는다.
//      ① 배경        bg (marat01~05)
//      ② 카드        shopA·shopB·basket·scaleA·upto/total·compare·tip·site·hook 중 켜진 것
//      ③ 말풍선      text
//      ④ 왼쪽 캐릭터  항상 올마
//      ⑤ 오른쪽 캐릭터 who가 올마면 with, 아니면 who
//      ⑥ 효과음      Talk.jsx 하단 Hit 목록
//
// ── 필드 뜻 ────────────────────────────────────────────────────
//    who   말하는 쪽          with  상대역
//    sec   무음 뺀 발화 길이   head  건너뛸 앞무음      gap  대사 뒤 숨
//    bg    그 대사 동안 배경
//    parts 한 대사가 읽히는 동안 바뀌는 화면들. sec 경계는 align.json의 단어 시작 시각
//    face  말하는 쪽 표정      of    듣는 쪽 표정
//
// 🔴 sec/head는 `voice\trim.json`, parts 경계는 `voice\align.json` 실측값이다. 손대지 말 것.
//    대사를 바꾸면  make_voice.py → normalize.py → trim.py → align.py  를 다시 돌린다.
// 🔴 gap은 대사 사이 숨. 여기로 전체 길이를 맞춘다.

export const LEAD = 0.2;

export const LINES = [
  {
    // 훅 — 🔴 썸네일은 0.5초만 딱 정지해서 보여주고, 그 다음 브랜드볼이 나오면서 시작한다
    //    (2026-07-22 지시). 그래서 첫 문장을 0.5초 지점에서 쪼갰다 — 앞쪽만 hook(썸네일 전용),
    //    나머지는 캐릭터+말풍선이 있는 평소 화면이다. 대사 오디오는 그대로 이어진다.
    who: "올마",
    with: "사장님",
    sec: 4.12,
    head: 0.084,
    gap: 0.15,
    bg: "marat03",
    parts: [
      {
        text: "육천 원이면 되는 셀프마라탕이",
        face: "시치미",
        sec: 0.5,
        hook: true,
        noBubble: true,
      },
      {
        text: "육천 원이면 되는 셀프마라탕이",
        face: "시치미",
        sec: 1.14,
      },
      {
        text: "구천 원짜리보다 비쌀 수 있다?",
        face: "놀람",
        sec: 2.48,
      },
    ],
  },
  {
    // 사장님 등장 — 웃는 얼굴. 폭로가 아니라 알려주는 사람이다
    who: "사장님",
    with: "올마",
    sec: 4.98,
    head: 0.0,
    gap: 0.15,
    bg: "marat03",
    parts: [
      {
        text: "제가 진짜 마라탕집 사장인데요",
        face: "웃음",
        sec: 2.02,
        of: "시치미",
      },
      {
        text: "셀프마라탕이 두 종류라는 걸 잘 모르시더라고요",
        face: "시치미",
        sec: 2.96,
        of: "놀람",
      },
    ],
  },
  {
    // A소개 — 배경도 소스바로 바뀐다
    who: "올마",
    with: "사장님",
    sec: 4.16,
    head: 0.081,
    gap: 0.15,
    bg: "marat04",
    parts: [
      {
        text: "A집은 100g에 이천칠백 원",
        face: "시치미",
        sec: 1.68,
        shopA: 1,
      },
      {
        text: "대신 소스바에 밥이랑 음료까지 무한리필",
        face: "웃음",
        sec: 2.48,
        shopA: 2,
        of: "웃음",
      },
    ],
  },
  {
    // B소개
    who: "올마",
    with: "사장님",
    sec: 6.08,
    head: 0.083,
    gap: 0.15,
    bg: "marat02",
    parts: [
      {
        text: "B집은 100g에 천구백 원",
        face: "시치미",
        sec: 1.38,
        shopB: 1,
      },
      { text: "싸죠?", face: "웃음", sec: 0.98, shopB: 1 },
      {
        text: "대신 고기, 음료, 꼬치가 전부 별도예요",
        face: "시치미",
        sec: 3.72,
        shopB: 2,
        of: "시치미",
      },
    ],
  },
  {
    // 검증 — 같은 장바구니 선언
    who: "올마",
    with: "사장님",
    sec: 6.26,
    head: 0.106,
    gap: 0.15,
    bg: "marat01",
    parts: [
      {
        text: "같은 한 끼를 양쪽에서 먹어보겠습니다",
        face: "시치미",
        sec: 2.81,
        basket: true,
      },
      {
        text: "고기 100g에 채소, 밥, 음료까지",
        face: "시치미",
        sec: 3.45,
        basket: true,
        of: "웃음",
      },
    ],
  },
  {
    // A집 저울 — 키오스크 배경
    who: "올마",
    with: "사장님",
    sec: 6.4,
    head: 0.093,
    gap: 0.15,
    bg: "marat05",
    parts: [
      {
        text: "A집은 고기까지 저울에 다 올려서 구천백팔십 원",
        face: "놀람",
        sec: 3.01,
        scaleA: true,
      },
      { text: "끝입니다", face: "시치미", sec: 1.22, scaleA: true },
      {
        text: "소스도 밥도 음료도 포함이니까요",
        face: "웃음",
        sec: 2.17,
        scaleA: true,
        of: "웃음",
      },
    ],
  },
  {
    // B집 장부 — 한 줄씩 쌓인다
    who: "올마",
    with: "사장님",
    sec: 4.4,
    head: 0.101,
    gap: 0.15,
    bg: "marat02",
    parts: [
      {
        text: "B집은 재료 육천 원에",
        face: "시치미",
        sec: 1.76,
        upto: 1,
        hot: 0,
      },
      {
        text: "고기 100g 삼천 원",
        face: "시치미",
        sec: 1.48,
        upto: 2,
        hot: 1,
      },
      {
        text: "음료 이천 원",
        face: "놀람",
        sec: 1.16,
        upto: 3,
        hot: 2,
        of: "시치미",
      },
    ],
  },
  {
    // 합계 첫 공개 + 정적 0.7초. 화면 변화 없는 정적은 0.8초가 한계
    who: "올마",
    with: "사장님",
    sec: 1.19,
    head: 0.071,
    gap: 0.7,
    bg: "marat02",
    parts: [
      { text: "합쳐서 만천 원", face: "놀람", sec: 1.19, upto: 3, total: true },
    ],
  },
  {
    // 역전 공개 — A vs B 비교 카드
    who: "올마",
    with: "사장님",
    sec: 2.74,
    head: 0.089,
    gap: 0.15,
    bg: "marat03",
    parts: [
      {
        text: "싸 보이던 B집이 이천 원 가까이 더 나왔습니다",
        face: "놀람",
        sec: 2.74,
        compare: true,
        of: "시치미",
      },
    ],
  },
  {
    // 사장님 균형 발언 — B집 편들기. 업계와 안 싸우는 장치
    who: "사장님",
    with: "올마",
    sec: 7.07,
    head: 0.0,
    gap: 0.15,
    bg: "marat03",
    parts: [
      {
        text: "B집이 나쁜 게 아니에요",
        face: "시치미",
        sec: 2.02,
        compare: true,
        of: "놀람",
      },
      {
        text: "혼자 가볍게 먹으면 육천 원으로 끝나거든요",
        face: "웃음",
        sec: 3.02,
        of: "시치미",
      },
      {
        text: "많이 먹을 때 계산이 달라지는 거죠",
        face: "웃음",
        sec: 2.03,
        of: "시치미",
      },
    ],
  },
  {
    // 꿀팁 — 이 편의 결론 카드
    who: "올마",
    with: "사장님",
    sec: 5.08,
    head: 0.087,
    gap: 0.15,
    bg: "marat03",
    parts: [
      {
        text: "고기 넣고 배부르게 먹을 거면 소스바 있는 집",
        face: "웃음",
        sec: 2.91,
        tip: 1,
      },
      {
        text: "가볍게 한 그릇이면 없는 집이 유리합니다",
        face: "웃음",
        sec: 2.17,
        tip: 2,
        of: "웃음",
      },
    ],
  },
  {
    who: "올마",
    with: "사장님",
    sec: 4.06,
    head: 0.112,
    gap: 0.8,
    bg: "marat03",
    parts: [
      { text: "100g 가격만 보고 고르셨다면", face: "시치미", sec: 1.63 },
      {
        text: "오늘부터는 소스바부터 확인해 보세요",
        face: "웃음",
        sec: 2.43,
        site: true,
        of: "웃음",
      },
    ],
  },
];
