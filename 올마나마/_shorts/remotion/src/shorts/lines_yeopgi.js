// 엽기떡볶이 엽기로제 원가편 대사 — 이거 얼마남아 3 (2026-07-26)
//
// 🔴 여성향 톤. 올마=여자(핑크, 진행) / 사장님=남자(노랑).
//    목소리 올마 SunHi(여) / 사장님 InJoon(남), 둘 다 +70%.
//
// 🔴 sec / head 는 voice/trim.json 실측값. 음성 public/voiceY1/01~12.mp3
// 🔴 화면 글은 아라비아 숫자, TTS 대본만 한글 숫자.
// 🔴 LEAD 0.2 고정 — 늘리면 쇼츠가 죽는다(배달편 11회 사고).
//
// 🔴 숫자는 **도매(매장 매입) 기준**. 합 4,244원 · 원가율 27%.
// 🔴 훅에서 원가를 **까지 않는다** — 궁금증만 남기고 8번에서 공개한다.
//
// ── 화면(page) 인덱스 (pages_yeopgi.js) ──
//   0 소스·떡  1 나머지 재료  2 원가공개  3 인사이트

export const LEAD = 0.2;

export const LINES = [
  {
    // 훅 — 첫 프레임이 썸네일
    who: "올마", with: "사장님", sec: 2.56, head: 0.0, gap: 0.25, bg: "soft",
    parts: [
      { text: "16,000원 엽떡, 재료값 얼마일 것 같아?", face: "놀람", sec: 0.12, hook: true, noBubble: true },
      { text: "16,000원 엽기떡볶이,", face: "놀람", sec: 1.28, emo: { who: "올마", text: "헉" } },
      { text: "재료값 얼마일 것 같아?", face: "웃음", sec: 1.16, of: "당황" },
    ],
  },
  {
    // 공지 — 선긋기
    who: "올마", with: "사장님", sec: 2.29, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "우린 재료값만 봐. 만드는 품은 몰라", face: "웃음", sec: 2.29, of: "시치미" }],
  },
  {
    // 재료 ① — 소스·떡
    who: "올마", with: "사장님", sec: 2.57, head: 0.0, gap: 0.22, bg: "soft",
    parts: [{ text: "떡볶이 분말 1,540원, 밀떡 648원", face: "놀람", sec: 2.57, page: 0, of: "시치미" }],
  },
  {
    // 재료 ① 마무리 — 숫자만 말하고 판단은 안 한다
    who: "올마", with: "사장님", sec: 1.96, head: 0.0, gap: 0.22, bg: "soft",
    parts: [{ text: "이 둘이 벌써 52%야", face: "놀람", sec: 1.96, page: 0, of: "당황", emo: { who: "올마", text: "52%!" } }],
  },
  {
    // 사장 반응 ① — 변명
    who: "사장님", with: "올마", sec: 2.4, head: 0.044, gap: 0.22, bg: "soft",
    parts: [{ text: "그 소스가 우리 비법이에요", face: "변명", sec: 2.4, page: 0, of: "웃음" }],
  },
  {
    // 재료 ②
    who: "올마", with: "사장님", sec: 2.52, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "휘핑크림 540원, 모차렐라 499원", face: "웃음", sec: 2.52, page: 1, of: "식은땀" }],
  },
  {
    // 재료 ③
    who: "올마", with: "사장님", sec: 1.6, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "어묵이랑 소시지까지 더해도", face: "웃음", sec: 1.6, page: 1, of: "화들짝" }],
  },
  {
    // 원가 공개 — 정점. 뒤에 0.4초 정적
    who: "올마", with: "사장님", sec: 2.31, head: 0.0, gap: 0.4, bg: "soft",
    parts: [{ text: "4,244원. 원가율 27%야", face: "놀람", sec: 2.31, page: 2, of: "경악", emo: { who: "올마", text: "27%" } }],
  },
  {
    // 사장 버럭
    who: "사장님", with: "올마", sec: 3.57, head: 0.021, gap: 0.2, bg: "soft",
    parts: [{ text: "임대료! 배달 수수료! 그거 다 우리가 내요!", face: "발끈", sec: 3.57, of: "화들짝", emo: { who: "사장님", text: "부들부들" } }],
  },
  {
    // 인사이트 — 소비자 이득
    who: "올마", with: "사장님", sec: 2.07, head: 0.0, gap: 0.28, bg: "soft",
    parts: [{ text: "이거 2~3인분이야", face: "웃음", sec: 2.07, page: 3, of: "좌절" }],
  },
  {
    // 사장 머쓱
    who: "사장님", with: "올마", sec: 1.07, head: 0.051, gap: 0.28, bg: "soft",
    parts: [{ text: "그래도 맛있잖아요", face: "뿌듯", sec: 1.07, of: "웃음", emo: { who: "사장님", text: "히힣" } }],
  },
  {
    // 마무리 — 사이트
    who: "올마", with: "사장님", sec: 2.17, head: 0.0, gap: 0.8, bg: "soft",
    parts: [{ text: "다른 메뉴 원가는 올마나마에서", face: "웃음", sec: 2.17, site: true, of: "뿌듯" }],
  },
];
