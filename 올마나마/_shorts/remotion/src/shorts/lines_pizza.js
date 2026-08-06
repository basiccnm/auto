// 도미노 포테이토 피자 원가편 대사 — 원가 시리즈 1 (2026-07-24)
//
// 🔴 톤 = 반말 + 웃기게 (쇼츠 규칙). 근데 숫자·팩트·원산지는 정확하게.
// 🔴 sec / head 는 voice/trim.json 실측값. 음성 public/voiceP1/01~12.mp3 (+70%)
// 🔴 화면 글은 아라비아 숫자, TTS 대본만 한글 숫자.
// 🔴 상시 자막 "원재료 기준 원가" 는 판(page)에 박는다.
//
// ── 화면(page) 인덱스 (pages_pizza.js) ──
//   0 재료 절반(치즈·도우)  1 재료 더  2 원산지  3 원가공개  4 인사이트
//   page 없는 대사는 캐릭터·말풍선만
//
// ── LEAD 0.2 고정 (늘리면 죽는다) · 훅 파트 0.12 ──

export const LEAD = 0.2;

export const LINES = [
  {
    // 훅 — 첫 프레임이 썸네일. 큰 숫자 대비로 바로 터뜨린다
    who: "올마", with: "사장님", sec: 3.4, head: 0.036, gap: 0.2, bg: "pizza01",
    parts: [
      { text: "27,900원 피자, 원가가 4,200원인 거 알면 못 참지", face: "웃음", sec: 0.12, hook: true, noBubble: true },
      { text: "27,900원짜리 피자,", face: "시치미", sec: 1.7, emo: { who: "올마", text: "ㅋㅋ" } },
      { text: "원가가 4,200원이래", face: "웃음", sec: 1.58, of: "당황" },
    ],
  },
  {
    // 공지 — 선긋기 (가볍게)
    who: "올마", with: "사장님", sec: 3.38, head: 0.044, gap: 0.2, bg: "pizza01",
    parts: [
      { text: "미리 말하는데 우린 재료값만 봐", face: "웃음", sec: 1.9, prop: "megaphone", of: "시치미", emo: { who: "올마", text: "재료값만!" } },
      { text: "조리비 인건비 그런 건 몰라", face: "놀람", sec: 1.48, of: "당황" },
    ],
  },
  {
    // 재료 ① — 치즈·도우가 절반
    who: "올마", with: "사장님", sec: 2.9, head: 0.045, gap: 0.25, bg: "pizza03",
    parts: [{ text: "치즈 1,300원, 도우 1,000원. 이 둘이 벌써 반 넘었어", face: "놀람", sec: 2.9, page: 0, of: "시치미" }],
  },
  {
    // 재료 ② — 툭툭
    who: "올마", with: "사장님", sec: 3.78, head: 0.045, gap: 0.25, bg: "pizza03",
    parts: [{ text: "베이컨 530원, 감자 370원, 소스 310원 툭툭", face: "웃음", sec: 3.78, page: 1, of: "당황" }],
  },
  {
    // 원산지 — 팩트 (공식 표시)
    who: "올마", with: "사장님", sec: 2.52, head: 0.044, gap: 0.2, bg: "pizza03",
    parts: [{ text: "근데 이 베이컨, 돼지고기 외국산인 거 알지?", face: "시치미", sec: 2.52, page: 2, of: "식은땀", emo: { who: "올마", text: "외국산 ㅇㅇ" } }],
  },
  {
    // 사장 발끈 ①
    who: "사장님", with: "올마", sec: 1.52, head: 0.0, gap: 0.25, bg: "pizza02",
    parts: [{ text: "야, 그건 원래 다 그래!", face: "발끈", sec: 1.52, page: 2, of: "웃음", emo: { who: "사장님", text: "발끈" } }],
  },
  {
    // 남은 재료 쌓기
    who: "올마", with: "사장님", sec: 1.98, head: 0.05, gap: 0.2, bg: "pizza02",
    parts: [{ text: "양파 버섯 옥수수 마요까지 다 때려박아도", face: "웃음", sec: 1.98, page: 3, of: "화들짝" }],
  },
  {
    // 원가 공개 — 정점. 뒤에 0.4초 정적
    who: "올마", with: "사장님", sec: 2.39, head: 0.04, gap: 0.4, bg: "pizza02",
    parts: [{ text: "넉넉하게 잡아 4,200원. 원가율 15%야", face: "놀람", sec: 2.39, page: 3, of: "경악", emo: { who: "올마", text: "15%!" } }],
  },
  {
    // 사장 버럭 — 불 뿜기
    who: "사장님", with: "올마", sec: 3.06, head: 0.0, gap: 0.2, bg: "pizza02",
    parts: [{ text: "임대료! 인건비! 배달 수수료 얼만데!", face: "발끈", sec: 3.06, prop: "fire", of: "화들짝", emo: { who: "사장님", text: "부들부들" } }],
  },
  {
    // 인사이트 — 소비자 이득 (할인 강한 이유)
    who: "올마", with: "사장님", sec: 3.88, head: 0.043, gap: 0.3, bg: "pizza04",
    parts: [{ text: "그니까 만 원 깎아도 남아. 피자가 맨날 세일하는 게 다 이유가 있어", face: "웃음", sec: 3.88, page: 4, of: "좌절" }],
  },
  {
    // 사장 머쓱 — 태세 전환
    who: "사장님", with: "올마", sec: 1.24, head: 0.0, gap: 0.3, bg: "pizza04",
    parts: [{ text: "그래도 맛있으면 됐지 뭐", face: "뿌듯", sec: 1.24, of: "웃음", emo: { who: "사장님", text: "히힣" } }],
  },
  {
    // 마무리 — 사이트
    who: "올마", with: "사장님", sec: 3.53, head: 0.053, gap: 0.8, bg: "pizza04",
    parts: [{ text: "정가 주고 사면 호구인 거임. 원가 궁금하면 올마나마 ㄱㄱ", face: "웃음", sec: 3.53, site: true, of: "뿌듯" }],
  },
];
