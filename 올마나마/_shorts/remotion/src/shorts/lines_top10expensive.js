// 마라탕 3편 대사 — 종합 TOP10 · 담으면 인상 쓰는(제일 비싼) 재료 (2026-07-23)
//
// 🔴 2편과 정반대 방향 — 여기선 **1위가 제일 비싸다.** 공지에 경고 문구 필수.
// 🔴 사장님 감정은 2편과 반대 진행: 처음부터 긴장(당황)으로 시작해서
//    화들짝 → 경악을 여러 번 거쳐 정점(1위 양고기)에서 "멘붕"으로 폭발한다.
//    2편이 "억울한 발각"이었다면 3편은 "예상된 재앙"이라 처음부터 아는 얼굴로 간다.
//
// ── 화면 객체 번호 ────────────────────────────────────────────
//    ① 배경  ② 카드  ③ 말풍선  ④ 왼쪽=올마  ⑤ 오른쪽=사장님  ⑥ 효과음

export const LEAD = 0.2;

const RANK_TEXT = [
  "10위 유부모찌 1,100원",
  "9위 유부 1,133원",
  "8위 두부피쉬볼 1,160원",
  "7위 우삼겹 1,200원",
  "6위 넓은두유피 1,300원",
  "5위 펭귄피쉬볼 1,480원",
  "4위 고수 1,615원",
  "3위 날치알주머니 1,630원",
  "2위 참돔치즈볼 1,640원",
  "그리고 대망의 1위, 양고기 1,980원",
];

// trim.json 실측 (06_올마.mp3 ~ 15_올마.mp3)
const RANK_TIMING = [
  { sec: 2.33, head: 0.031 },
  { sec: 2.33, head: 0.096 },
  { sec: 2.81, head: 0.105 },
  { sec: 2.59, head: 0.1 },
  { sec: 2.6, head: 0.092 },
  { sec: 2.77, head: 0.111 },
  { sec: 2.59, head: 0.045 },
  { sec: 2.89, head: 0.042 },
  { sec: 2.85, head: 0.087 },
  { sec: 3.21, head: 0.096 },
];

// 사장님 표정 — 처음부터 위태롭게 시작(2편과 다르게 "이미 각오한 얼굴")
const RANK_FACE = [
  "당황", "식은땀", "변명", "화들짝", "진땀",
  "멘붕", "억울", "좌절", "경악", "멘붕", // 1위(양고기)는 "멘붕"으로 — 예상은 했지만 실제 숫자에 다시 무너진다
];

const rankLines = RANK_TEXT.map((text, i) => ({
  who: "올마",
  with: "사장님",
  sec: RANK_TIMING[i].sec,
  head: RANK_TIMING[i].head,
  gap: i === RANK_TEXT.length - 2 ? 0.55 : 0.28,
  bg: "marat01",
  parts: [
    {
      text,
      face: "놀람",
      sec: RANK_TIMING[i].sec,
      rank: i,
      of: RANK_FACE[i],
      ...(i === RANK_TEXT.length - 1 ? { emo: { who: "사장님", text: "올 것이 왔다" } } : {}),
    },
  ],
}));

export const LINES = [
  {
    who: "올마", with: "사장님", sec: 3.88, head: 0.078, gap: 0.2, bg: "marat06",
    parts: [
      { text: "사장님이 쳐다볼 때 눈치 보이는 재료, 원가가 무려 이 정도입니다", face: "시치미", sec: 0.5, hook: true, noBubble: true },
      { text: "사장님이 쳐다볼 때 눈치 보이는 재료", face: "시치미", sec: 1.72, emo: { who: "올마", text: "쓱" } },
      { text: "원가가 무려 이 정도입니다", face: "웃음", sec: 1.66, of: "당황" },
    ],
  },
  {
    // 🔴 3파트 — 공지 / 경고 / 시작. align.json 실측 경계로 나눴다
    who: "올마", with: "사장님", sec: 7.63, head: 0.101, gap: 0.2, bg: "marat06",
    parts: [
      { text: "궁금하신 메뉴 댓글 달아주시면 쇼츠로 만들어보겠습니다", face: "웃음", sec: 3.8, prop: "handcall", of: "웃음", emo: { who: "올마", text: "댓글 ㄱㄱ" } },
      { text: "이번엔 1위가 제일 비쌉니다", face: "놀람", sec: 2.64, of: "식은땀", emo: { who: "올마", text: "주의!" } },
      { text: "10위부터 갑니다", face: "놀람", sec: 1.19, prop: "megaphone", of: "당황" },
    ],
  },
  {
    who: "올마", with: "사장님", sec: 0.66, head: 0.05, gap: 0.35, bg: "marat01",
    parts: [{ text: "3", face: "놀람", sec: 0.66, count: 3, noBubble: true, of: "당황", emo: { who: "사장님", text: "어어" } }],
  },
  {
    who: "올마", with: "사장님", sec: 0.63, head: 0.0, gap: 0.35, bg: "marat01",
    parts: [{ text: "2", face: "놀람", sec: 0.63, count: 2, noBubble: true, of: "식은땀" }],
  },
  {
    who: "올마", with: "사장님", sec: 0.63, head: 0.093, gap: 0.55, bg: "marat01",
    parts: [{ text: "1", face: "발끈", sec: 0.63, count: 1, noBubble: true, of: "화들짝", emo: { who: "사장님", text: "잠깐" } }],
  },

  ...rankLines,

  {
    who: "올마", with: "사장님", sec: 1.65, head: 0.108, gap: 1.6, bg: "marat01",
    parts: [{ text: "전부 모으면 이렇게 됩니다", face: "웃음", sec: 1.65, all: true, noBall: true, noBubble: true }],
  },
  {
    who: "올마", with: "사장님", sec: 3.19, head: 0.086, gap: 0.2, bg: "marat03",
    parts: [
      {
        text: "대박, 이것만 꽉꽉 담으면 사장님 망하는 거네요?",
        face: "웃음",
        sec: 3.19,
        of: "멘붕",
        emo: { who: "올마", text: "꺼드럭꺼드럭" },
      },
    ],
  },
  {
    who: "사장님", with: "올마", sec: 2.67, head: 0.0, gap: 0.2, bg: "marat03",
    parts: [
      {
        text: "사람 양심이 있으면 야채도 좀 같이 담아줘야지!",
        face: "발끈",
        sec: 2.67,
        prop: "fire",
        of: "화들짝",
        emo: { who: "사장님", text: "부들부들" },
      },
    ],
  },
  {
    who: "사장님", with: "올마", sec: 1.98, head: 0.0, gap: 0.8, bg: "marat03",
    parts: [
      {
        text: "제발 야채 좀 팍팍 넣어주세요",
        face: "억울",
        sec: 1.98,
        site: true,
        of: "웃음",
        emo: { who: "사장님", text: "제발요" },
      },
    ],
  },
];
