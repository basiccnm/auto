// 설빙 애플망고치즈설빙 원가편 대사 — 이거 얼마남아 2 (2026-07-25)
//
// 🔴 **이 편부터 여성향 톤이다.** 올마=여자(핑크, 진행) / 나마=남자(노랑, 사장님).
//    목소리도 스왑됐다 — 올마 SunHi(여) / 사장님 InJoon(남), 둘 다 +70%.
//
// 🔴 sec / head 는 voice/trim.json 실측값. 음성 public/voiceB1/01~12.mp3
// 🔴 화면 글은 아라비아 숫자, TTS 대본만 한글 숫자.
// 🔴 LEAD 0.2 고정 — 늘리면 쇼츠가 죽는다(배달편 11회 사고).
//
// 🔴 숫자는 **도매(매장 매입) 기준**이다(2026-07-25 변경). 합 4,534원 · 원가율 31%.
// 🔴 훅에서 원가를 **까지 않는다** — 궁금증만 남기고 8번에서 공개한다.
//    전엔 1번이 "재료값이 사천 원이래"로 답을 먼저 말해서 볼 이유가 없었다.
//
// ── 화면(page) 인덱스 (pages_bingsu.js) ──
//   0 재료 절반(치즈·우유)  1 나머지 재료  2 원가공개  3 인사이트

export const LEAD = 0.2;

export const LINES = [
  {
    // 훅 — 첫 프레임이 썸네일
    who: "올마", with: "사장님", sec: 2.7, head: 0.0, gap: 0.25, bg: "soft",
    parts: [
      { text: "14,500원 망고빙수, 재료값 얼마일 것 같아?", face: "놀람", sec: 0.12, hook: true, noBubble: true },
      { text: "14,500원 망고빙수,", face: "놀람", sec: 1.33, emo: { who: "올마", text: "헉" } },
      { text: "재료값 얼마일 것 같아?", face: "웃음", sec: 1.25, of: "당황" },
    ],
  },
  {
    // 공지 — 선긋기
    who: "올마", with: "사장님", sec: 2.29, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "우린 재료값만 봐. 만드는 품은 몰라", face: "웃음", sec: 2.29, of: "시치미" }],
  },
  {
    // 재료 ① — 치즈·우유
    who: "올마", with: "사장님", sec: 2.26, head: 0.0, gap: 0.22, bg: "soft",
    parts: [{ text: "큐브치즈 1,496원, 우유 1,200원", face: "놀람", sec: 2.26, page: 0, of: "시치미" }],
  },
  {
    // 재료 ② — 둘이 절반 넘음
    who: "올마", with: "사장님", sec: 2.0, head: 0.0, gap: 0.22, bg: "soft",
    parts: [{ text: "이 둘이 벌써 59%야", face: "놀람", sec: 2.0, page: 0, of: "당황", emo: { who: "올마", text: "59%!" } }],
  },
  {
    // 사장 반응 ① — 변명
    who: "사장님", with: "올마", sec: 2.29, head: 0.045, gap: 0.22, bg: "soft",
    parts: [{ text: "치즈가 비싸요, 진짜 비싼 거예요", face: "변명", sec: 2.29, page: 0, of: "웃음" }],
  },
  {
    // 재료 ③
    who: "올마", with: "사장님", sec: 2.46, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "망고퓨레 915원, 냉동망고 558원", face: "웃음", sec: 2.46, page: 1, of: "식은땀" }],
  },
  {
    // 재료 ④
    who: "올마", with: "사장님", sec: 1.63, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "연유랑 아이스크림까지 더해도", face: "웃음", sec: 1.63, page: 1, of: "화들짝" }],
  },
  {
    // 원가 공개 — 정점. 뒤에 0.4초 정적
    who: "올마", with: "사장님", sec: 2.38, head: 0.0, gap: 0.4, bg: "soft",
    parts: [{ text: "4,534원. 원가율 31%야", face: "놀람", sec: 2.38, page: 2, of: "경악", emo: { who: "올마", text: "31%" } }],
  },
  {
    // 사장 버럭
    who: "사장님", with: "올마", sec: 2.51, head: 0.041, gap: 0.2, bg: "soft",
    parts: [{ text: "여름 한 철 장사예요! 자리값은요!", face: "발끈", sec: 2.51, of: "화들짝", emo: { who: "사장님", text: "부들부들" } }],
  },
  {
    // 인사이트 — 소비자 이득
    who: "올마", with: "사장님", sec: 2.13, head: 0.0, gap: 0.28, bg: "soft",
    parts: [{ text: "그래서 빙수는 나눠 먹는 게 남아", face: "웃음", sec: 2.13, page: 3, of: "좌절" }],
  },
  {
    // 사장 머쓱
    who: "사장님", with: "올마", sec: 1.12, head: 0.05, gap: 0.28, bg: "soft",
    parts: [{ text: "그래도 시원하잖아요", face: "뿌듯", sec: 1.12, of: "웃음", emo: { who: "사장님", text: "히힣" } }],
  },
  {
    // 마무리 — 사이트
    who: "올마", with: "사장님", sec: 2.17, head: 0.0, gap: 0.8, bg: "soft",
    parts: [{ text: "다른 메뉴 원가는 올마나마에서", face: "웃음", sec: 2.17, site: true, of: "뿌듯" }],
  },
];
