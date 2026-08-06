// 식탁 + 접시 + 음식 — 올마와 같은 그림체(두꺼운 검은 선 + 파스텔)
//
// 왜 그림인가: AI 사진은 뽑을 때마다 시즈닝이 이상하게 뿌려지고 손가락이 나온다
//   (2026-07-21 "저건 시즈닝이 잘못 뿌려짐"). 좌표로 그리면 그런 일이 없다.
//
// 🔴 정면(옆에서 본 모습)으로 그리면 상판이 선 하나가 돼서 음식이 얹힌 게 안 보인다.
//    **위에서 비스듬히 내려다본 사다리꼴**로 그린다(2026-07-21 지시).
//    뒤가 좁고 앞이 넓어야 원근이 생긴다.
// 🔴 메뉴가 바뀌면 <Plate> 안의 음식만 갈아끼운다. 식탁·접시는 그대로.
//    → 롱폼에서 "배경은 그대로, 음식만 바뀜"이 되어 조각 이어붙이기가 매끄럽다.
import React from "react";

const LINE = "#000";
const LW = 7;

// 🔴 단색 주황 덩어리는 안 맛있어 보인다(2026-07-21 "먹음직스러워 보이지 않는다").
//    튀김은 ① 두 톤 색 ② 아래쪽 그늘 ③ 기름 윤기 ④ 우둘투둘한 부스러기 — 이 넷이 있어야 산다.
const FRY = "#F0A93C";      // 밝은 황금
const FRY_DARK = "#C97B22";  // 그늘·진한 부분
const GLOSS = "#FFE9B0";     // 윤기 하이라이트

// 튀김옷 부스러기 — 가장자리에 우둘투둘 붙은 알갱이
const Crumbs = ({ pts, x, y }) =>
  pts.map(([dx, dy, r], i) => (
    <circle key={i} cx={x + dx} cy={y + dy} r={r} fill={FRY} stroke={LINE} strokeWidth={3.5} />
  ));

// 공통 — 덩어리 안쪽 그늘 + 윤기
const Shade = ({ d, gloss }) => (
  <>
    <path d={d} fill={FRY_DARK} opacity={0.55} />
    {gloss}
  </>
);

// ── 닭다리 하나
//  🔴 덩어리 한가운데에 동그라미·곡선을 넣으면 **얼굴로 보인다**(2026-07-21 1차 시도).
//     결 표시는 가장자리로 빼고, 뼈는 바깥으로 삐져나오게 한다.
export const Drumstick = ({ x, y, rot = 0, scale = 1, seasoning = false }) => (
  <g
    style={{
      transformBox: "view-box",
      transformOrigin: `${x}px ${y}px`,
      rotate: `${rot}deg`,
      scale,
    }}
  >
    {/* 🔴 흰 뼈를 삐죽 내밀면 안 된다(2026-07-21). 튀김가루가 뼈까지 덮어서 튀겨지므로
        실제로는 뼈가 안 보인다. 덩어리 아래가 살짝 좁아지는 것으로만 다리를 표현한다. */}

    {/* 튀김옷 부스러기 — 가장자리에 우둘투둘 (덩어리보다 먼저 그려 뒤에 깔린다) */}
    <Crumbs x={x} y={y} pts={[[-52, -18, 8], [-46, 16, 7], [50, -22, 8], [54, 10, 7], [-14, -60, 8], [26, -58, 7]]} />

    {/* 튀김옷 덩어리 */}
    <path
      d={`M${x} ${y - 58}
          c 30 0 54 20 56 44
          c 1 13 -6 19 -8 28
          c -3 15 -14 25 -26 27
          c -8 2 -12 8 -22 8
          c -10 0 -14 -6 -22 -8
          c -12 -2 -23 -12 -26 -27
          c -2 -9 -9 -15 -8 -28
          c 2 -24 26 -44 56 -44 z`}
      fill={FRY}
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    {/* 아래쪽 그늘 — 입체감 */}
    <path
      d={`M${x - 52} ${y + 6}
          c 6 26 22 40 52 40
          c 30 0 46 -14 52 -40
          c 2 12 -4 18 -6 26
          c -3 15 -14 25 -26 27
          c -8 2 -12 8 -20 8
          c -10 0 -14 -6 -22 -8
          c -12 -2 -23 -12 -26 -27
          c -2 -9 -6 -14 -4 -26 z`}
      fill={FRY_DARK}
      opacity={0.5}
    />
    {/* 기름 윤기 — 왼쪽 위 */}
    <ellipse cx={x - 22} cy={y - 34} rx={17} ry={10} fill={GLOSS} opacity={0.85} style={{ rotate: "-24deg", transformBox: "fill-box", transformOrigin: "center" }} />
    <ellipse cx={x + 16} cy={y - 40} rx={8} ry={5} fill={GLOSS} opacity={0.6} />

    {/* 바삭한 결 — 가장자리 쪽으로만 */}
    <path d={`M${x - 45} ${y - 14} q10 10 4 22`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d={`M${x + 45} ${y - 14} q-10 10 -4 22`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d={`M${x - 28} ${y - 44} q14 -8 28 -2`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />

    {/* 시즈닝 — 흰 점. 🔴 뿌링클처럼 가루 뿌린 메뉴에만. 황금올리브는 그냥 후라이드라 없다 */}
    {seasoning &&
      [
        [-30, -20], [-6, -36], [22, -28], [33, -2], [-37, 4], [8, 6],
        [-18, 21], [27, 22], [0, -13], [-39, -28], [39, -32], [15, 34], [-15, 37],
      ].map(([dx, dy], i) => <circle key={i} cx={x + dx} cy={y + dy} r={3.6} fill="#FFFDF2" />)}
  </g>
);

// ── 봉 (윙스틱) — 다리보다 작고, 한쪽이 좁아지는 원뿔형
const Wingstick = ({ x, y, rot = 0, scale = 1 }) => (
  <g style={{ transformBox: "view-box", transformOrigin: `${x}px ${y}px`, rotate: `${rot}deg`, scale }}>
    <Crumbs x={x} y={y} pts={[[-38, -12, 7], [40, -16, 7], [-8, -42, 7], [34, 8, 6]]} />
    <path
      d={`M${x} ${y - 40}
          c 22 0 38 15 39 32
          c 1 12 -6 18 -9 24
          c -4 9 -16 14 -30 14
          c -14 0 -26 -5 -30 -14
          c -3 -6 -10 -12 -9 -24
          c 1 -17 17 -32 39 -32 z`}
      fill={FRY}
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    {/* 그늘 + 윤기 */}
    <path
      d={`M${x - 39} ${y + 4} c 4 20 18 32 39 32 c 21 0 35 -12 39 -32
          c 1 8 -6 14 -9 20 c -4 9 -16 14 -30 14 c -14 0 -26 -5 -30 -14 c -3 -6 -10 -12 -9 -20 z`}
      fill={FRY_DARK}
      opacity={0.5}
    />
    <ellipse cx={x - 14} cy={y - 22} rx={13} ry={7} fill={GLOSS} opacity={0.85} />
    <path d={`M${x - 30} ${y - 8} q8 8 3 16`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d={`M${x + 20} ${y - 30} q10 -4 18 4`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
  </g>
);

// ── 날개 (윙) — 납작하고 두 갈래로 꺾인 모양
const Wing = ({ x, y, rot = 0, scale = 1 }) => (
  <g style={{ transformBox: "view-box", transformOrigin: `${x}px ${y}px`, rotate: `${rot}deg`, scale }}>
    <Crumbs x={x} y={y} pts={[[-48, -14, 7], [44, 18, 6], [-6, -30, 6]]} />
    <path
      d={`M${x - 44} ${y - 6}
          c -6 -18 8 -30 24 -26
          c 12 3 18 14 20 24
          c 10 -6 26 -4 32 8
          c 7 14 -4 28 -19 28
          c -10 0 -16 -5 -19 -12
          c -8 8 -22 8 -30 0
          c -6 -6 -9 -14 -8 -22 z`}
      fill={FRY}
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    <path
      d={`M${x - 44} ${y + 2} c 0 10 3 16 8 20 c 8 8 22 8 30 0
          c 3 7 9 12 19 12 c 15 0 26 -14 19 -28 c 3 14 -6 24 -19 24
          c -10 0 -16 -5 -19 -12 c -8 8 -22 8 -30 0 c -5 -4 -8 -10 -8 -16 z`}
      fill={FRY_DARK}
      opacity={0.55}
    />
    <ellipse cx={x - 22} cy={y - 18} rx={12} ry={6} fill={GLOSS} opacity={0.85} />
    <path d={`M${x - 26} ${y - 14} q10 6 6 16`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d={`M${x + 18} ${y + 4} q8 6 2 14`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
  </g>
);

// ── 살코기 조각 (가슴·안심) — 뼈 없이 울퉁불퉁한 덩어리
const Chunk = ({ x, y, rot = 0, scale = 1 }) => (
  <g style={{ transformBox: "view-box", transformOrigin: `${x}px ${y}px`, rotate: `${rot}deg`, scale }}>
    <Crumbs x={x} y={y} pts={[[-44, -8, 7], [46, 6, 7], [10, -38, 7], [-20, 34, 6]]} />
    <path
      d={`M${x} ${y - 32}
          c 20 -4 40 6 44 22
          c 3 12 -4 16 -2 26
          c 2 12 -12 22 -30 22
          c -10 0 -14 4 -24 2
          c -18 -4 -28 -16 -25 -28
          c 2 -9 -3 -14 0 -22
          c 5 -14 20 -20 37 -22 z`}
      fill={FRY}
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    <path
      d={`M${x - 44} ${y + 8} c 0 16 12 28 30 32 c 10 2 14 -2 24 -2
          c 18 0 32 -10 30 -22 c 1 10 -12 18 -30 18
          c -10 0 -14 4 -24 2 c -18 -4 -30 -14 -30 -28 z`}
      fill={FRY_DARK}
      opacity={0.55}
    />
    <ellipse cx={x - 16} cy={y - 14} rx={15} ry={8} fill={GLOSS} opacity={0.85} />
    <path d={`M${x - 32} ${y + 2} q10 8 4 18`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d={`M${x + 12} ${y - 22} q12 2 16 12`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d={`M${x - 10} ${y + 26} q12 -6 24 2`} stroke={LINE} strokeWidth={4} fill="none" strokeLinecap="round" />
  </g>
);

// ── 포크에 꽂힌 치킨
//  🔴 손과 치킨이 안 이어져 붕 떠 보였다(2026-07-21). 포크로 이어준다.
//     포크 손잡이 끝이 손 위치에 오고, 갈퀴에 치킨이 꽂힌다.
// ── 손에 쥔 포크 (올마 viewBox 좌표계에 직접 그린다)
//  🔴 손 위치(x,y)를 받아서 거기서 위로 뻗는다. 팔 회전을 같이 받으므로 절대 안 어긋난다.
//     밖에서 따로 배치하면 팔이 움직일 때마다 어긋난다(2026-07-21 "포크 에러가 많다").
export const ForkInHand = ({ x, y, eaten = false }) => (
  <g>
    {/* 손잡이 — 손에서 위로. 🔴 길면 닭이 머리 위로 넘어간다. 짧게(2026-07-21) */}
    <path d={`M${x} ${y + 6} L${x} ${y - 40}`} stroke={LINE} strokeWidth={11} strokeLinecap="round" />
    <path d={`M${x} ${y + 6} L${x} ${y - 40}`} stroke="#CFD8DC" strokeWidth={6} strokeLinecap="round" />
    {/* 갈퀴 */}
    {[-11, 0, 11].map((dx, i) => (
      <g key={i}>
        <path d={`M${x} ${y - 38} L${x + dx} ${y - 62}`} stroke={LINE} strokeWidth={9} strokeLinecap="round" />
        <path d={`M${x} ${y - 38} L${x + dx} ${y - 62}`} stroke="#CFD8DC" strokeWidth={5} strokeLinecap="round" />
      </g>
    ))}
    {/* 꽂힌 닭 — 먹고 나면 사라진다 */}
    {!eaten && <Drumstick x={x} y={y - 88} rot={-6} scale={0.58} />}
  </g>
);

export const ForkChicken = ({ scale = 1, eaten = false }) => (
  <svg viewBox="0 0 300 420" width={300 * scale} style={{ overflow: "visible" }}>
    {/* 손잡이 — 아래(손) → 위(치킨) */}
    <path d="M150 400 L150 210" stroke={LINE} strokeWidth={16} strokeLinecap="round" />
    <path d="M150 400 L150 210" stroke="#CFD8DC" strokeWidth={9} strokeLinecap="round" />
    {/* 갈퀴 3개 */}
    {[-26, 0, 26].map((dx, i) => (
      <g key={i}>
        <path d={`M150 214 L${150 + dx} 150`} stroke={LINE} strokeWidth={13} strokeLinecap="round" />
        <path d={`M150 214 L${150 + dx} 150`} stroke="#CFD8DC" strokeWidth={7} strokeLinecap="round" />
      </g>
    ))}
    {/* 갈퀴에 꽂힌 치킨 — 🔴 먹고 나면 사라진다(빈 포크만 남음) */}
    {!eaten && <Drumstick x={150} y={120} rot={-8} scale={1.15} />}
  </svg>
);

// ── 김 (모락모락)
const Steam = ({ x, y, delay = 0, wave = 0 }) => (
  <path
    d={`M${x} ${y} c -14 -20 14 -30 0 -50 c -12 -18 10 -28 0 -44`}
    stroke="#B9B2A4"
    strokeWidth={6}
    strokeLinecap="round"
    fill="none"
    style={{ translate: `${Math.sin(wave + delay) * 5}px ${Math.cos(wave + delay) * 4}px` }}
  />
);

// ── 접시 + 음식 (상판 좌표계 위에 얹힌다)
export const Plate = ({ steam = 0 }) => (
  <>
    {/* 🔴 김은 뺐다(2026-07-21). 영수증 뒤로 들어가 잘려 보여서 지저분했다. */}

    {/* 접시 — 위에서 본 원이라 세로로 눌린 타원.
        🔴 접시를 치킨보다 먼저 그려야 한다. 나중에 그리면 치킨을 덮는다(2026-07-21). */}
    <ellipse cx={450} cy={236} rx={186} ry={66} fill="#FFFFFF" stroke={LINE} strokeWidth={LW} />
    <ellipse cx={450} cy={236} rx={148} ry={48} fill="#F3F3F3" stroke={LINE} strokeWidth={4} />

    {/* 🔴 닭다리만 3개 놓으면 "치킨 한 마리"로 안 보인다(2026-07-21 "치킨 같지가 않잖아").
        실제 치킨은 다리·봉·날개·살코기가 섞여 수북이 쌓인다.
        뒤쪽(작고 위) → 앞쪽(크고 아래) 순으로 그려야 쌓인 것처럼 보인다. */}

    {/* 🔴 접시에 평평하게 깔면 허술해 보인다(2026-07-21 "탑을 쌓으라니까, 산더미").
        치킨집 치킨은 **산처럼 수북이** 쌓여 있다.
        아래층(넓게) → 위층(좁게) 순서로 그려야 위에 얹힌 것처럼 보인다. */}

    {/* 1층 — 접시 바닥, 제일 넓게 */}
    <Wing x={330} y={252} rot={-34} scale={0.62} />
    <Wingstick x={382} y={258} rot={-16} scale={0.6} />
    <Drumstick x={452} y={262} rot={-2} scale={0.6} />
    <Wingstick x={522} y={258} rot={18} scale={0.6} />
    <Wing x={574} y={252} rot={32} scale={0.62} />

    {/* 2층 */}
    <Chunk x={368} y={214} rot={-20} scale={0.6} />
    <Drumstick x={430} y={218} rot={-10} scale={0.6} />
    <Wingstick x={492} y={218} rot={12} scale={0.6} />
    <Chunk x={548} y={214} rot={22} scale={0.6} />

    {/* 3층 */}
    <Drumstick x={404} y={178} rot={-16} scale={0.58} />
    <Wing x={460} y={174} rot={6} scale={0.58} />
    <Chunk x={512} y={178} rot={18} scale={0.58} />

    {/* 꼭대기 */}
    <Wingstick x={434} y={142} rot={-12} scale={0.56} />
    <Drumstick x={486} y={140} rot={14} scale={0.56} />
  </>
);

// ── 식탁 전체 — 원형
//  🔴 사각 식탁은 화면을 너무 많이 먹는다(2026-07-21 "사각형 너무 커").
//     원형 + 외다리(기둥)로 바꾸면 폭이 확 줄어 올마가 걸어올 공간이 생긴다.
//     위에서 비스듬히 보므로 원은 **세로로 눌린 타원**이 된다.
export const Table = ({ width = 700, steam = 0, children }) => (
  <svg viewBox="0 0 900 810" width={width} xmlns="http://www.w3.org/2000/svg" style={{ overflow: "visible" }}>
    {/* 🔴 기둥다리·받침을 **맨 먼저** 그린다. 나중에 그리면 상판 위로 튀어나와 보인다
        (2026-07-21 "식탁 다리가 상판보다 앞에 나와 있다"). */}
    <path d="M408 400 v330 h84 v-330 z" fill="#E0AE74" stroke={LINE} strokeWidth={LW} strokeLinejoin="round" />
    <ellipse cx={450} cy={742} rx={150} ry={44} fill="#D9A46A" stroke={LINE} strokeWidth={LW} />

    {/* 상판 옆면(두께) — 윗면보다 먼저 그린다 */}
    <path
      d="M90 330 a360 118 0 0 0 720 0 v42 a360 118 0 0 1 -720 0 z"
      fill="#C98F53"
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    {/* 상판 윗면 */}
    <ellipse cx={450} cy={330} rx={360} ry={118} fill="#E0AE74" stroke={LINE} strokeWidth={LW} />
    {/* 나뭇결 */}
    <path d="M215 300 q30 40 -10 74" stroke="#C98F53" strokeWidth={4} strokeLinecap="round" fill="none" />
    <path d="M690 300 q-30 40 10 74" stroke="#C98F53" strokeWidth={4} strokeLinecap="round" fill="none" />

    {/* 접시·음식 — 상판 위에 얹힌다. children을 주면 그걸 올린다(치킨 세트 등) */}
    <g style={{ translate: "0px 68px" }}>{children || <Plate steam={steam} />}</g>
  </svg>
);

// 🔴 상판 위에 임의의 내용을 올릴 때 쓰는 껍데기.
//    Table의 children은 SVG 좌표계 안이라 외부 컴포넌트를 그대로 못 넣는다.
export const TableTop = ({ width = 1000, children }) => (
  <div style={{ position: "relative", width }}>
    <Table width={width} />
    <div style={{ position: "absolute", left: 0, top: 0, width: "100%" }}>{children}</div>
  </div>
);
