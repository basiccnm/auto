// 카드뉴스 — 배달 옵션 꼼수의 비밀 (앵커링) 2026-07-24
//
// 🔴 정본 v2(드라이브 `올마나마/00_정본_카드뉴스_v2.md`) 기준으로 만든다.
//    프레임·타이포·색은 정본 §3·5·6 고정값. 임의로 바꾸지 말 것.
//
// 🔴 카드뉴스는 **답을 다 주지 않는다**(2026-07-24 확정).
//    문제·구조까지만 보여주고 타파법은 사이트로 보낸다 = 정보갭.
//
// 🔴 숫자는 대표님이 준 실제 사례. "예)"를 붙여 특정 가게가 아님을 밝힌다.
//    A집 = 즉시할인 큰 곳(옵션가 부풀림) / B집 = 즉시할인 적은 곳(옵션가 정상)

export const EP = {
  series: "배달 꿀팁",
  title: "배달 옵션 꼼수의 비밀",
  site: "olmanama.com",

  // 계산 근거 — 카드 ③④가 이걸 그대로 쓴다
  calc: {
    base: 13900, // 치즈피자 (양쪽 같다)
    A: { combo: 4000, topping: 4000, sale: 5000, label: "A집" },
    B: { combo: 2000, topping: 2000, sale: 2000, label: "B집" },
  },
};

// 합계는 계산해서 쓴다 — 손으로 적으면 숫자가 어긋난다
export const sum = (s) => EP.calc.base + s.combo + s.topping;
export const pay = (s) => sum(s) - s.sale;

// 🔴 글자를 대폭 키웠다(2026-07-24 지시). TTS가 없는 정지 이미지라
//    **읽는 시간이 곧 이해 시간**이다. 문장을 길게 쓰면 큰 글씨가 안 들어간다.
//    그래서 문구를 짧게 깎았다 — 이해되는 최소한만 남긴다.
export const CARDS = [
  {
    // 🔴 표지 = 썸네일(2026-07-24). 쇼츠는 첫 화면이 목록에 뜨는 얼굴이다.
    //    편 제목("배달 옵션 꼼수의 비밀")을 여기서 제일 크게 박는다 — 이게 훅이다.
    id: "cover",
    type: "훅",
    face: "놀람",
    doodle: "놀람",
    cover: true, // 표지 전용 레이아웃 (배지·리드 없이 제목만 크게)
    coverTop: "배달 옵션",
    coverBig: "꼼수의 비밀",
    coverSub: "할인 큰 집이 왜 더 비쌀까?",
  },
  {
    id: "hook",
    type: "훅",
    face: "놀람",
    tag: "훅",
    doodle: "놀람",
    big: "할인 큰 집이",
    bigPoint: "더 비싸다?",
    sub: "배달 옵션의 함정",
    note: "이 할인, 진짜 이득?",
  },
  {
    id: "problem",
    type: "손님",
    face: "눈치",
    tag: "문제",
    doodle: "계산",
    lead: "같은 피자, 다른 가게",
    rows: [
      ["A집 할인", "5,000원"],
      ["B집 할인", "2,000원"],
    ],
    note: "어디가 쌀까?",
  },
  {
    id: "option",
    type: "계산",
    face: "계산",
    prop: "계산기",
    tag: "옵션 가격",
    doodle: "계산",
    table: true, // ③ 옵션 비교표
    note: "옵션이 두 배",
  },
  {
    id: "result",
    type: "계산",
    face: "놀람",
    tag: "결과",
    doodle: "놀람",
    result: true, // ④ 최종 결제액
    note: "B집이 더 쌌다",
  },
  {
    id: "why",
    type: "사장",
    face: "기본",
    prop: "요리사모자",
    tag: "이유",
    doodle: "화내기",
    big: "할인은 한 번",
    bigPoint: "옵션은 계속",
    sub: "기본가는 그대로,\n옵션만 올려둡니다",
    note: "이게 앵커링",
  },
  {
    id: "cta",
    type: "맺음말",
    face: "웃음",
    tag: "그래서",
    doodle: "화내기",
    big: "타파법 2가지",
    sub: "할인만 보지 마세요",
    cta: true,
  },
];
