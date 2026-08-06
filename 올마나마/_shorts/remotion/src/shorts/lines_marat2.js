// 마라탕 2편 대사 — 셀프마라탕 채소 원가 공개 (2026-07-23)
//
// ── 화면 객체 번호 (대표님과 소통용 고정 체계) ──────────────────────
//    대표님이 "12초 ③ 내려" 하면 그 시점 화면에서 아래 번호로 대상을 찾는다.
//      ① 배경        bg (marat01~06)
//      ② 카드        hook(썸네일) · upto(단가표) · dried(마른것) · all(전체표) 중 켜진 것
//      ③ 말풍선      text
//      ④ 왼쪽 캐릭터  항상 올마
//      ⑤ 오른쪽 캐릭터 who가 올마면 with, 아니면 who
//      ⑥ 효과음      Talk2.jsx 하단 Hit 목록
//
// ── 필드 뜻 ────────────────────────────────────────────────────
//    sec/head = voice\trim.json 실측, parts 경계 = voice\align.json 단어 시작 시각. 손대지 말 것
//    gap = 대사 뒤 숨. 여기로 전체 길이를 맞춘다
//    upto = EP.fresh 를 몇 개까지 띄울지 · hot = 방금 뜬 줄(강조) · dried = 마른것 몇 개까지
//
// 🔴 배경 흐름: 도매시장(marat06)에서 시작 → 셀프바(marat01)에서 단가 공개 → 매장(marat03)에서 마무리
//    "원가는 도매시장에서 오고, 손님은 셀프바에서 담는다"는 흐름을 배경으로 깐다.

export const LEAD = 0.2;

export const LINES = [
  {
    // 훅 — 🔴 첫 0.5초는 썸네일 정지 화면(캐릭터 없음). 그 뒤 브랜드볼이 등장한다
    who: "올마",
    with: "사장님",
    sec: 4.46,
    head: 0.085,
    gap: 0.15,
    bg: "marat06",
    parts: [
      {
        text: "야채 듬뿍 담으면 이득일까요?",
        face: "시치미",
        sec: 0.5,
        hook: true,
        noBubble: true,
      },
      { text: "마라탕에 야채 듬뿍 담으면 이득일까요?", face: "놀람", sec: 2.22 },
      { text: "사장님은 개이득입니다", face: "웃음", sec: 1.74, of: "웃음" },
    ],
  },
  {
    // 공지 — 초반에 넣는다(끝에 두면 이탈해서 못 본다)
    who: "올마",
    with: "사장님",
    sec: 2.51,
    head: 0.102,
    gap: 0.15,
    bg: "marat06",
    parts: [
      {
        text: "궁금한 거 댓글 주시면 쇼츠로 만들어 드려요",
        face: "웃음",
        sec: 2.51,
        of: "웃음",
      },
    ],
  },
  {
    // 안내 — 사장님이 전제를 깐다. 이게 없으면 "이렇게 싼데 왜 비싸냐" 소리가 나온다
    who: "사장님",
    with: "올마",
    sec: 3.36,
    head: 0.0,
    gap: 0.15,
    bg: "marat06",
    parts: [
      { text: "야채값은 매일 바뀌고", face: "시치미", sec: 1.64, of: "시치미" },
      {
        text: "이건 손질비 뺀 재료값입니다",
        face: "지침",
        sec: 1.72,
        of: "놀람",
      },
    ],
  },

  // ── 단가 공개 — 한 재료씩 뜨고, 방금 뜬 줄이 노랗게 강조된다 ──────
  {
    who: "올마",
    with: "사장님",
    sec: 2.98,
    head: 0.112,
    gap: 0.12,
    bg: "marat01",
    parts: [
      { text: "알배기배추 220원", face: "시치미", sec: 1.65, upto: 1, hot: 0, drop: 0, of: "시치미" },
      { text: "양배추 230원", face: "시치미", sec: 1.33, upto: 2, hot: 1, drop: 1, of: "시치미" },
    ],
  },
  {
    who: "올마",
    with: "사장님",
    sec: 3.0,
    head: 0.097,
    gap: 0.12,
    bg: "marat01",
    parts: [
      { text: "숙주나물 250원", face: "시치미", sec: 1.62, upto: 3, hot: 2, drop: 2, of: "당황" },
      { text: "팽이버섯 270원", face: "시치미", sec: 1.38, upto: 4, hot: 3, drop: 3, of: "당황" },
    ],
  },
  {
    who: "올마",
    with: "사장님",
    sec: 4.04,
    head: 0.105,
    gap: 0.12,
    bg: "marat01",
    parts: [
      { text: "청경채 380원", face: "시치미", sec: 1.9, upto: 5, hot: 4, drop: 4, of: "변명" },
      { text: "얼갈이배추 430원", face: "시치미", sec: 2.14, upto: 6, hot: 5, drop: 5, of: "변명" },
    ],
  },
  {
    who: "올마",
    with: "사장님",
    sec: 3.35,
    head: 0.117,
    gap: 0.12,
    bg: "marat01",
    parts: [
      { text: "느타리버섯 480원", face: "시치미", sec: 1.38, upto: 7, hot: 6, drop: 6, of: "진땀" },
      { text: "새송이버섯 530원", face: "시치미", sec: 1.97, upto: 8, hot: 7, drop: 7, of: "진땀" },
    ],
  },
  {
    who: "올마",
    with: "사장님",
    sec: 3.06,
    head: 0.104,
    gap: 0.12,
    bg: "marat01",
    parts: [
      { text: "쑥갓 670원", face: "시치미", sec: 1.66, upto: 9, hot: 8, drop: 8, of: "진땀" },
      { text: "표고버섯 790원", face: "놀람", sec: 1.4, upto: 10, hot: 9, drop: 9, of: "지침" },
    ],
  },
  {
    // 1위 고수 — 여기가 이 편의 정점. 놀람 표정으로 받는다
    who: "올마",
    with: "사장님",
    sec: 3.36,
    head: 0.078,
    gap: 0.35,
    bg: "marat01",
    parts: [
      { text: "생물 중 제일 비싼 건 고수", face: "놀람", sec: 1.68, upto: 10 },
      {
        text: "1,670원",
        face: "놀람",
        sec: 1.68,
        upto: 11,
        hot: 10,
        drop: 10,
        of: "진땀",
      },
    ],
  },
  {
    // 마른 것 — 불린 기준이라 따로 뗀다
    who: "올마",
    with: "사장님",
    sec: 5.45,
    head: 0.106,
    gap: 0.15,
    bg: "marat01",
    parts: [
      {
        text: "마른 재료는 불린 기준입니다",
        face: "시치미",
        sec: 2.19,
        upto: 11,
        dried: 0,
      },
      { text: "흑목이 350원", face: "시치미", sec: 1.94, upto: 11, dried: 1, dropDry: 0, of: "지침" },
      { text: "백목이 460원", face: "시치미", sec: 1.32, upto: 11, dried: 2, dropDry: 1, of: "지침" },
    ],
  },
  {
    // 전체 표 — 캡처해서 저장할 만한 화면
    who: "올마",
    with: "사장님",
    sec: 1.65,
    head: 0.108,
    // 🔴 대사(1.65초)가 끝나도 표는 더 보여준다 — gap을 1.6으로 늘려 총 3.2초쯤 머문다.
    //    캡처해서 저장할 만한 화면이라 여기만 길게 잡는다.
    gap: 1.6,
    bg: "marat01",
    // 🔴 여기선 브랜드볼을 숨긴다(2026-07-23 지시) — 볼이 표를 가려서 안 보인다.
    //    noBall이면 엔진이 캐릭터·말풍선을 안 그리고 표만 크게 남긴다.
    parts: [
      {
        text: "전부 모으면 이렇게 됩니다",
        face: "웃음",
        sec: 1.65,
        all: true,
        noBall: true,
        noBubble: true,
      },
    ],
  },
  {
    // 회수 — 훅에서 던진 말을 그대로 돌려준다
    who: "올마",
    with: "사장님",
    sec: 2.97,
    head: 0.088,
    gap: 0.15,
    bg: "marat03",
    parts: [
      {
        text: "그래서 야채 듬뿍 담으면 사장님은 개이득이죠",
        face: "웃음",
        sec: 2.97,
        of: "웃음",
      },
    ],
  },
  {
    // 마무리 — 사장님이 손님 편도 들어준다. 업계와 안 싸우는 장치
    who: "사장님",
    with: "올마",
    sec: 4.74,
    head: 0.0,
    gap: 0.8,
    bg: "marat03",
    parts: [
      {
        text: "그래도 야채가 양은 제일 많이 나와요",
        face: "웃음",
        sec: 2.66,
        of: "시치미",
      },
      {
        text: "배부르게 드시려면 야채가 맞습니다",
        face: "웃음",
        sec: 2.08,
        site: true,
        of: "웃음",
      },
    ],
  },
];
