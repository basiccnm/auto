// 마라탕 3편 대사 — 면·떡류 18종 원가 카운트다운 (2026-07-23)
//
// 🔴 2편과 같은 형식(1랭킹 1대사 + 숨고르기). 18종이라 랭킹 사이 gap은
//    0.25초로 살짝 좁혔다 — 안 그러면 전체가 90초를 넘어간다.
// 🔴 사장님 표정 8단계를 18개 순위에 2개씩 배분했다(2026-07-23 확정 표정셋 재사용):
//    시치미→당황→식은땀→변명→화들짝→진땀→멘붕→억울→좌절→경악(정점, 1위만)
//
// ── 화면 객체 번호 ────────────────────────────────────────────
//    ① 배경  ② 카드  ③ 말풍선  ④ 왼쪽=올마  ⑤ 오른쪽=사장님  ⑥ 효과음

export const LEAD = 0.2;

const RANK_TEXT = [
  "18위 뉴진면 800원",
  "17위 넙적뉴진면 710원",
  "16위 원형뉴진면 700원",
  "15위 팬더분모자 690원",
  "14위 수정당면 571원",
  "13위 물만두 559원",
  "12위 왕치즈떡 520원",
  "11위 치즈떡 480원",
  "10위 분모자 456원",
  "9위 고구마떡 420원",
  "8위 연근모양분모자 400원",
  "7위 수제비 360원",
  "6위 넙적분모자 347원",
  "5위 중화당면 340원",
  "4위 중국당면 325원",
  "3위 쌀국수 310원",
  "2위 곤약말이 300원",
  "그리고 대망의 1위, 옥수수면 280원",
];

// trim.json 실측 (06_올마.mp3 ~ 23_올마.mp3)
const RANK_TIMING = [
  { sec: 2.36, head: 0.037 },
  { sec: 2.91, head: 0.044 },
  { sec: 2.56, head: 0.041 },
  { sec: 2.73, head: 0.039 },
  { sec: 3.0, head: 0.04 },
  { sec: 2.59, head: 0.04 },
  { sec: 2.65, head: 0.035 },
  { sec: 2.7, head: 0.03 },
  { sec: 2.56, head: 0.034 },
  { sec: 2.5, head: 0.096 },
  { sec: 2.77, head: 0.098 },
  { sec: 2.64, head: 0.108 },
  { sec: 3.1, head: 0.099 },
  { sec: 2.37, head: 0.102 },
  { sec: 2.87, head: 0.038 },
  { sec: 2.44, head: 0.035 },
  { sec: 2.25, head: 0.081 },
  { sec: 3.37, head: 0.094 },
];

// 사장님 표정 진행 — 8단계를 18순위에 2개씩(1위만 단독, 정점 "경악")
const RANK_FACE = [
  "시치미", "시치미", "당황", "당황", "식은땀", "식은땀",
  "변명", "변명", "화들짝", "화들짝", "진땀", "진땀",
  "멘붕", "멘붕", "억울", "억울", "좌절", "경악",
];

const rankLines = RANK_TEXT.map((text, i) => ({
  who: "올마",
  with: "사장님",
  sec: RANK_TIMING[i].sec,
  head: RANK_TIMING[i].head,
  gap: i === RANK_TEXT.length - 2 ? 0.5 : 0.25, // 1위 직전만 길게 — 숨고르기
  bg: "marat01",
  parts: [
    {
      text,
      face: i >= 16 ? "놀람" : "시치미",
      sec: RANK_TIMING[i].sec,
      rank: i,
      of: RANK_FACE[i],
      ...(i === RANK_TEXT.length - 1 ? { emo: { who: "사장님", text: "털렸다" } } : {}),
    },
  ],
}));

export const LINES = [
  {
    who: "올마", with: "사장님", sec: 4.46, head: 0.084, gap: 0.2, bg: "marat06",
    parts: [
      { text: "마라탕에 옥수수면 한 움큼? 사장님 마진율 폭발하는 순간입니다", face: "시치미", sec: 0.5, hook: true, noBubble: true },
      { text: "마라탕에 옥수수면 한 움큼?", face: "시치미", sec: 1.9, emo: { who: "올마", text: "쓱" } },
      { text: "사장님 마진율 폭발하는 순간입니다", face: "웃음", sec: 2.06, of: "당황" },
    ],
  },
  {
    who: "올마", with: "사장님", sec: 5.61, head: 0.101, gap: 0.2, bg: "marat06",
    parts: [
      { text: "궁금하신 메뉴 댓글 달아주시면 쇼츠로 만들어보겠습니다", face: "웃음", sec: 3.8, prop: "handcall", of: "웃음", emo: { who: "올마", text: "댓글 ㄱㄱ" } },
      { text: "면 떡류 18종 갑니다", face: "놀람", sec: 1.81, prop: "megaphone", of: "시치미", emo: { who: "올마", text: "두구두구" } },
    ],
  },
  {
    who: "올마", with: "사장님", sec: 0.65, head: 0.05, gap: 0.35, bg: "marat01",
    parts: [{ text: "3", face: "놀람", sec: 0.65, count: 3, noBubble: true, of: "시치미", emo: { who: "사장님", text: "어어" } }],
  },
  {
    who: "올마", with: "사장님", sec: 0.63, head: 0.0, gap: 0.35, bg: "marat01",
    parts: [{ text: "2", face: "놀람", sec: 0.63, count: 2, noBubble: true, of: "당황" }],
  },
  {
    who: "올마", with: "사장님", sec: 0.63, head: 0.093, gap: 0.5, bg: "marat01",
    parts: [{ text: "1", face: "발끈", sec: 0.63, count: 1, noBubble: true, of: "당황", emo: { who: "사장님", text: "잠깐" } }],
  },

  ...rankLines,

  {
    who: "올마", with: "사장님", sec: 1.65, head: 0.108, gap: 1.6, bg: "marat01",
    parts: [{ text: "전부 모으면 이렇게 됩니다", face: "웃음", sec: 1.65, all: true, noBall: true, noBubble: true }],
  },
  {
    who: "올마", with: "사장님", sec: 3.05, head: 0.086, gap: 0.2, bg: "marat03",
    parts: [
      {
        text: "마라탕에 옥수수면 팍팍 넣으면, 완전 개이득이네요?",
        face: "웃음",
        sec: 3.05,
        of: "좌절",
        emo: { who: "올마", text: "꺼드럭꺼드럭" },
      },
    ],
  },
  {
    who: "사장님", with: "올마", sec: 3.46, head: 0.0, gap: 0.2, bg: "marat03",
    parts: [
      {
        text: "아오! 그거 삶고 찬물에 헹구는 노동력이 얼만데!",
        face: "발끈",
        sec: 3.46,
        prop: "fire",
        of: "화들짝",
        emo: { who: "사장님", text: "부들부들" },
      },
    ],
  },
  {
    who: "사장님", with: "올마", sec: 1.54, head: 0.0, gap: 0.8, bg: "marat03",
    parts: [
      {
        text: "솔직히 이득이긴 하죠",
        face: "뿌듯",
        sec: 1.54,
        site: true,
        of: "웃음",
        emo: { who: "사장님", text: "히힣" },
      },
    ],
  },
];
