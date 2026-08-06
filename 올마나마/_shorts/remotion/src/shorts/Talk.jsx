// 마라탕 1편 — 셀프마라탕 A/B 업태 비교, 만담 약 60초 (2026-07-22)
// (3편 교촌 버전은 configs/Talk_03_kyochon.jsx.bak 에 백업)
//
// ── 구조 ──────────────────────────────────────────────────────
// 🔴 훅 → 설정(사장님 등장) → A소개 → B소개 → 같은 한 끼 검증 → A 9,180 → B 쌓기
//    → 합계 11,000 + 정적 → 역전 공개 → 사장님 균형 발언 → 꿀팁 → 마무리
// 🔴 어두운 폭로가 아니라 **소비자 꿀팁** 톤이다(2026-07-22 방향 확정).
//    사장님이 B집을 편들어줘서("나쁜 게 아니에요") 업계와 안 싸운다.
// 🔴 A업태 숫자는 마라정도(의정부) 실측 — 대표님 배우자 가게다.
// 🔴 진행은 올마(추후 올마나마 마라탕 계산기로 유입), 사장님은 검증·증언.
//
// ── 고칠 때 주의 ──────────────────────────────────────────────
// 🔴 sec/head는 `voice\trim.json`, parts 경계는 `voice\align.json` 실측값이다. 손대지 말 것.
//    대사를 바꾸면  make_voice.py → normalize.py → trim.py → align.py  를 다시 돌린다.
// 🔴 gap은 대사 사이 숨. 여기로 전체 길이를 59초대에 맞춘다.
// 🔴 배경은 편 공통이 아니라 **장면별**이다(marat01~05). 카드 안전영역(top 200)은 동일.
import React from "react";
import { z } from "zod";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { useAudioData } from "@remotion/media-utils";
import { BrandBall } from "../olma/BrandBall";
import { C } from "./config";
import { EP, B_TOTAL, DIFF } from "./ep_marat1";
import { BLACK, JUA } from "./fonts";
import { LEAD, LINES } from "./lines_marat1";

// 🔴 훅 카드(=썸네일) 숫자값들 — 매번 나한테 말로 고쳐달라고 하면 왕복이 손해라서(2026-07-22 지시)
//    스튜디오 오른쪽 Props 패널에서 대표님이 직접 슬라이더/숫자칸으로 조절하게 뺐다.
//    Root.jsx의 defaultProps가 시작값. 패널에서 바꾼 채로 스튜디오 자체 "Render" 버튼을 누르면
//    그 값 그대로 영상이 나온다 — 나를 거치지 않아도 된다.
//    ⚠️ 그릇 일러스트의 위치·크기(Img의 translate/scale)는 여기 포함 안 했다.
//    그건 캔버스에서 직접 드래그하는 게 더 편해서 그대로 코드에 하드코딩돼 있다(건드리지 말 것).
export const talkSchema = z.object({
  hookTop: z.number(),
  cardBottomPad: z.number(),
  subtitleSize: z.number(),
  line1Size: z.number(),
  line2Size: z.number(),
  line3Size: z.number(),
  badgeFontSize: z.number(),
  badgeGapTop: z.number(),
});

export const talkDefaultProps = {
  hookTop: 230,
  cardBottomPad: 26, // 🔴 그릇을 flow 밖으로 뺀 뒤론 텍스트만 채우면 되니 정상 패딩으로 복귀
  subtitleSize: 62,
  line1Size: 128,
  line2Size: 138,
  line3Size: 128,
  badgeFontSize: 62, // "셀프마라탕 두 종류..." 부제(subtitleSize)와 같은 크기(2026-07-22 지시)
  badgeGapTop: 16,
};

const won = (n) => n.toLocaleString() + "원";


export const TALK_SEC =
  LEAD + LINES.reduce((a, l) => a + l.sec + (l.gap || 0), 0);

const LINE_AT = LINES.reduce((acc, l, i) => {
  acc.push(
    i === 0 ? LEAD : acc[i - 1] + LINES[i - 1].sec + (LINES[i - 1].gap || 0),
  );
  return acc;
}, []);

const partAt = (li, pi) =>
  LINE_AT[li] + LINES[li].parts.slice(0, pi).reduce((a, p) => a + p.sec, 0);

const LEFT = -225;
const RIGHT = 225;
const BIG = 1.28;
const SMALL = 1.0;

// ── 카드 공통 ────────────────────────────────────────────────
// 🔴 안전 영역(3편에서 데임): 카드는 top 200부터, 캐릭터 발끝 1660 이내.
// 🔴 top prop은 훅 카드를 "살짝 내려" 달라는 지시(2026-07-22) 대응용 — 기본값은 그대로 200.
const Card = ({ children, wide = false, top = 200 }) => (
  <div
    style={{
      position: "absolute",
      top,
      left: "50%",
      transform: "translateX(-50%)",
      width: wide ? 1000 : 880,
      background: "rgba(12,12,14,0.82)",
      border: "8px solid #000",
      borderRadius: 30,
      padding: "26px 34px 22px",
    }}
  >
    {children}
  </div>
);

// 🔴 "글씨 크게"는 썸네일(훅 카드) 얘기였다(2026-07-22 정정) — 카드 폰트는 원래 크기로 되돌린다.
const Row = ({ name, val, hi, big, dim }) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "baseline",
      gap: 16,
      fontFamily: big ? BLACK : JUA,
      fontSize: big ? 84 : hi ? 60 : 50,
      color: big || hi ? C.yellow : dim ? "#B9B4A8" : "#fff",
      marginTop: big ? 10 : 8,
    }}
  >
    <span style={{ whiteSpace: "nowrap" }}>{name}</span>
    {val != null && (
      <span
        style={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}
      >
        {val}
      </span>
    )}
  </div>
);

const Title = ({ children, color = C.yellow }) => (
  <div
    style={{
      fontFamily: BLACK,
      fontSize: 62,
      color,
      lineHeight: 1.05,
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </div>
);

// A집 소개 — step 1: 가격만 / step 2: 무료 목록까지
// 🔴 화면 표기는 숫자로 통일한다: "100g"(2026-07-22 재지시 — 한글 "백 그램"에서 되돌림).
//    음성은 그대로 "백 그램"으로 읽는다(TTS는 이미 그렇게 녹음됨) — 자막만 숫자.
const ShopA = ({ step }) => (
  <Card>
    <Title>A집 · {EP.A.title}</Title>
    <div
      style={{
        fontFamily: BLACK,
        fontSize: 96,
        color: "#fff",
        marginTop: 8,
        whiteSpace: "nowrap",
      }}
    >
      100g {won(EP.A.per100)}
    </div>
    {step >= 2 && (
      <>
        <div style={{ borderTop: "6px solid #4A4A4A", margin: "16px 0 4px" }} />
        {EP.A.free.map((x) => (
          <Row key={x} name={`무료  ${x}`} hi />
        ))}
        <Row name={EP.A.note} dim />
      </>
    )}
  </Card>
);

// B집 소개 — step 1: 가격만 / step 2: 무료(밥)·별도 목록까지
// 🔴 B집도 밥은 무료다(2026-07-22 지시) — 별도 목록에서 빼고 A집처럼 "무료" 줄로 보여준다.
const ShopB = ({ step }) => (
  <Card>
    <Title color="#8ECBF5">B집 · {EP.B.title}</Title>
    <div
      style={{
        fontFamily: BLACK,
        fontSize: 96,
        color: "#fff",
        marginTop: 8,
        whiteSpace: "nowrap",
      }}
    >
      100g {won(EP.B.per100)}
    </div>
    {step >= 2 && (
      <>
        <div style={{ borderTop: "6px solid #4A4A4A", margin: "16px 0 4px" }} />
        {EP.B.free.map((x) => (
          <Row key={x} name={`무료  ${x}`} hi />
        ))}
        <Row name="별도  고기 100g" val="3,000원" />
        <Row name="별도  음료" val="2,000원" />
        <Row name="별도  꼬치" val="1,000원" />
      </>
    )}
  </Card>
);

// 같은 한 끼 — 검증 조건 선언
const Basket = () => (
  <Card>
    <Title color="#fff">같은 한 끼로 비교</Title>
    <div
      style={{
        fontFamily: JUA,
        fontSize: 58,
        color: C.yellow,
        marginTop: 12,
        whiteSpace: "nowrap",
      }}
    >
      고기 100g + 채소 + 밥 + 음료
    </div>
  </Card>
);

// A집 저울 — 한 방
const ScaleA = () => (
  <Card>
    <Title>A집 저울</Title>
    <div
      style={{
        fontFamily: BLACK,
        fontSize: 130,
        color: C.yellow,
        marginTop: 6,
        whiteSpace: "nowrap",
      }}
    >
      {won(EP.A.scaleTotal)}
    </div>
    <div
      style={{
        fontFamily: JUA,
        fontSize: 46,
        color: "#B9B4A8",
        marginTop: 4,
        whiteSpace: "nowrap",
      }}
    >
      고기 · 소스 · 밥 · 음료 전부 포함
    </div>
  </Card>
);

// B집 장부 — 쌓기 + 합계
const LedgerB = ({ upto = 0, hot = -1, total }) => (
  <Card>
    <Title color="#8ECBF5">B집 계산서</Title>
    {EP.B.rows.slice(0, upto).map(([name, v], i) => (
      <Row
        key={name}
        name={name}
        val={won(v)}
        hi={i === hot}
        dim={hot >= 0 && i !== hot}
      />
    ))}
    {total && (
      <>
        <div style={{ borderTop: "8px solid #fff", margin: "16px 0 2px" }} />
        <Row name="합계" val={won(B_TOTAL)} big />
      </>
    )}
  </Card>
);

// 역전 비교
const Compare = () => (
  <Card>
    <Row name="A집 (소스바 있음)" val={won(EP.A.scaleTotal)} />
    <Row name="B집 (소스바 없음)" val={won(B_TOTAL)} hi />
    <div style={{ borderTop: "8px solid #fff", margin: "16px 0 2px" }} />
    <Row name="B집이" val={`+ ${won(DIFF)}`} big />
  </Card>
);

// 꿀팁 결론
const Tip = ({ step }) => (
  <Card wide>
    <Title color="#fff">오늘의 결론</Title>
    <Row name="배부르게 먹는 날 → 소스바 있는 집" hi />
    {step >= 2 && <Row name="가볍게 한 그릇 → 소스바 없는 집" hi />}
  </Card>
);

// 마무리 — 🔴 카드를 키우고 댓글 유도 문구를 크게 넣는다(2026-07-22 지시).
//    "궁금한 거 물어보면 다음 편 소재로 쓴다"는 채널 참여 유도가 이 편의 CTA다.

// 🔴 손그림 SVG는 뺐다(2026-07-22 지시 — "제외"). 대신 실제 마라탕 일러스트를
//    그릇 모양대로 배경 제거해서 쓴다 → bg/marat_bowl.png (원본: Gemini 생성, 흰 배경 색상키 제거).

// 시리즈 배지 — 제목엔 못 박지만(2026-07-22 지시) 썸네일(=훅 카드)엔 늘 붙는다.
// 🔴 카드 위에 얹는 작은 배지였다가, 카드 밑으로 옮기고 카드 너비만큼 키웠다(2026-07-22 지시).
//    이제 흐름(flow) 안의 형제 요소라서 absolute를 뺐다 — 부모(HookWrap)가 폭을 정해준다.
// 🔴 크게 키웠다(2026-07-22 지시) — 빨간 배너가 두꺼워지는 건 괜찮다고 확인받음.
const SeriesBadge = ({ fontSize = 64 }) => (
  <div
    style={{
      width: "100%",
      boxSizing: "border-box",
      background: C.red,
      border: "6px solid #000",
      borderRadius: 26,
      padding: "26px 0",
      textAlign: "center",
      fontFamily: BLACK,
      fontSize,
      color: "#fff",
    }}
  >
    마라탕 시리즈 1
  </div>
);

const Site = ({ pop }) => (
  <Card wide>
    <div
      style={{
        textAlign: "center",
        fontFamily: BLACK,
        fontSize: 100,
        color: "#fff",
        opacity: pop,
      }}
    >
      {EP.site}
    </div>
    <div
      style={{
        textAlign: "center",
        fontFamily: JUA,
        fontSize: 46,
        color: "#B9B4A8",
        marginTop: 8,
      }}
    >
      음식 원가, 여기 다 있습니다
    </div>
    <div style={{ borderTop: "6px solid #4A4A4A", margin: "22px 0 18px" }} />
    {/* 🔴 댓글 유도 CTA — 크게, 느낌표 확실히(2026-07-22 지시) */}
    <div
      style={{
        textAlign: "center",
        fontFamily: BLACK,
        fontSize: 64,
        color: C.yellow,
        lineHeight: 1.25,
      }}
    >
      마라탕 궁금한 거 있으면
      <br />
      쇼츠로 알려드려요!
    </div>
    <div
      style={{
        textAlign: "center",
        fontFamily: BLACK,
        fontSize: 72,
        color: "#fff",
        marginTop: 10,
        lineHeight: 1.15,
      }}
    >
      댓글 남겨주세요!!!!
    </div>
    <div style={{ borderTop: "4px solid #4A4A4A", margin: "20px 0 0" }} />
    <div
      style={{
        textAlign: "center",
        fontFamily: JUA,
        fontSize: 34,
        color: "#9C978C",
        marginTop: 12,
        lineHeight: 1.35,
      }}
    >
      {EP.disc.split("\n").map((x) => (
        <div key={x}>{x}</div>
      ))}
    </div>
  </Card>
);

// 🔴 항상 1줄로만 나오게 한다(2026-07-22 지시) — 대사 길이에 따라 2줄로 접히면
//    말풍선 높이가 그때그때 달라져서 자리가 안 잡힌 것처럼 보였다. 1줄이면 y는 고정이고
//    박스 크기만 살짝 숨쉬는 정도라 훨씬 안정적이다. 글자는 길면 조금 작아져도 된다(지시 확인).
const BASE_FONT = 72;
const MAX_CHARS_AT_BASE = 16; // 이 글자수까지는 72px 그대로 (말풍선 폭을 넓혀서 14→16)
const MIN_FONT = 44; // 🔴 너무 길면 쪼개서 보여주니(아래) 바닥값을 덜 낮춰도 된다
const bubbleFontSize = (text) => {
  const n = (text || "").length;
  if (n <= MAX_CHARS_AT_BASE) return BASE_FONT;
  return Math.max(MIN_FONT, Math.round((BASE_FONT * MAX_CHARS_AT_BASE) / n));
};

// 🔴 대사가 많이 길면 억지로 줄이지 않고, 한 번 보여줬다 지우고 다음 절반을 보여준다
//    (2026-07-22 지시: "말이 길 때는 한번 나오고 지워지고 다음 말 나오게 해").
//    공백 중 중앙에 제일 가까운 곳에서 자연스럽게 둘로 쪼갠다.
const SPLIT_CHAR_THRESHOLD = 20;
const SPLIT_MIN_SEC = 1.6; // 이보다 짧은 part는 쪼개봐야 각 조각이 너무 잠깐이라 그냥 축소로 처리
const SPLIT_GAP_SEC = 0.12; // 지워지는 짧은 틈
const splitBubbleText = (text) => {
  if (!text || text.length <= SPLIT_CHAR_THRESHOLD) return [text];
  const mid = Math.floor(text.length / 2);
  let bestIdx = -1;
  let bestDist = Infinity;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === " ") {
      const d = Math.abs(i - mid);
      if (d < bestDist) {
        bestDist = d;
        bestIdx = i;
      }
    }
  }
  if (bestIdx === -1) return [text]; // 공백이 없으면 못 쪼갠다
  return [text.slice(0, bestIdx).trim(), text.slice(bestIdx + 1).trim()];
};

const Bubble = ({ children, y, pop, side }) => {
  const tail = side === "left" ? "24%" : "76%";
  const fontSize = bubbleFontSize(children);
  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: "50%",
        // 🔴 캐릭터(zIndex 1~2)가 말풍선을 덮는 사고 발견(2026-07-22).
        //    zIndex:auto인 요소는 명시적 zIndex가 있는 형제보다 항상 아래에 깔린다(CSS 스택 규칙).
        //    말풍선은 항상 맨 위여야 하므로 캐릭터보다 큰 값을 명시한다.
        zIndex: 5,
        transform: `translateX(-50%) scale(${pop})`,
        // 🔴 항상 가운데서 펼쳐지게 고정한다(2026-07-22 지시).
        //    전엔 꼬리 위치(24%/76%)를 기준으로 팝업해서 대사가 짧을 때마다
        //    말풍선이 좌우로 튀는 것처럼 보였다. 꼬리(삼각형)는 그대로 두고
        //    펼쳐지는 기준점만 중앙(50%)으로 고정한다.
        transformOrigin: "50% 100%",
        opacity: Math.min(pop * 1.6, 1),
      }}
    >
      <div
        style={{
          position: "relative",
          background: "#fff",
          border: "11px solid #000",
          borderRadius: 34,
          padding: "20px 38px 28px",
          fontFamily: JUA,
          fontSize,
          lineHeight: 1.2,
          color: "#111",
          textAlign: "center",
          maxWidth: 1040,
          whiteSpace: "nowrap",
        }}
      >
        {children}
        <div
          style={{
            position: "absolute",
            bottom: -40,
            left: tail,
            marginLeft: -24,
            width: 0,
            height: 0,
            borderLeft: "24px solid transparent",
            borderRight: "24px solid transparent",
            borderTop: "40px solid #000",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -22,
            left: tail,
            marginLeft: -14,
            width: 0,
            height: 0,
            borderLeft: "14px solid transparent",
            borderRight: "14px solid transparent",
            borderTop: "24px solid #fff",
          }}
        />
      </div>
    </div>
  );
};

// 효과음 — 끝 0.35초 페이드아웃 필수(뚝 소리 방지)
const Hit = ({ t, src, vol = 0.7, dur = 1.2 }) => {
  const { fps } = useVideoConfig();
  const n = Math.round(dur * fps);
  const fade = Math.min(Math.round(0.35 * fps), Math.floor(n / 2));
  return (
    <Sequence from={Math.round(t * fps)} durationInFrames={n} name={src}>
      <Audio
        src={staticFile(`sfx/${src}`)}
        volume={(x) =>
          interpolate(x, [0, 1, n - fade, n], [0, vol, vol, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })
        }
      />
    </Sequence>
  );
};

// 목소리 파형 → 입 벌림. 12개를 항상 같은 순서로 불러둔다(LINES 고정)
const useMouths = () =>
  LINES.map((_, i) =>
    useAudioData(staticFile(`voice/${String(i + 1).padStart(2, "0")}.mp3`)),
  );

const mouthAt = (data, sec) => {
  if (!data) return null;
  const wave = data.channelWaveforms[0];
  const at = Math.floor(sec * data.sampleRate);
  const win = Math.floor(data.sampleRate / 25);
  let peak = 0;
  for (let i = at; i < at + win && i < wave.length; i += 8) {
    const v = Math.abs(wave[i]);
    if (v > peak) peak = v;
  }
  return Math.min(peak / 0.32, 1);
};

export const Talk = (props) => {
  const {
    hookTop,
    cardBottomPad,
    subtitleSize,
    line1Size,
    line2Size,
    line3Size,
    badgeFontSize,
    badgeGapTop,
  } = { ...talkDefaultProps, ...props };
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const voices = useMouths();

  let li = 0;
  for (let i = 0; i < LINES.length; i++) {
    if (t >= LINE_AT[i]) li = i;
  }
  const L = LINES[li];
  const inLine = t - LINE_AT[li];
  const silent = inLine > L.sec;

  let acc = 0;
  let p = L.parts[L.parts.length - 1];
  let pStart = 0;
  for (const q of L.parts) {
    if (inLine < acc + q.sec) {
      p = q;
      pStart = acc;
      break;
    }
    acc += q.sec;
    pStart = acc;
  }
  const inPart = (inLine - pStart) * fps;

  // 🔴 긴 대사는 절반씩 나눠서 순서대로 보여준다 — 캐릭터 통통 튐(pop/bounce)은
  //    part 전체 기준(inPart) 그대로 두고, 말풍선 팝인만 조각 기준으로 따로 계산한다.
  const inPartSec = inLine - pStart;
  const bubbleChunks = splitBubbleText(p.text);
  let bubbleText = p.text;
  let bubbleLocalSec = inPartSec;
  let bubbleVisible = true;
  if (bubbleChunks.length === 2 && p.sec >= SPLIT_MIN_SEC) {
    const w1 = bubbleChunks[0].length;
    const w2 = bubbleChunks[1].length;
    const avail = p.sec - SPLIT_GAP_SEC;
    const dur1 = avail * (w1 / (w1 + w2));
    if (inPartSec < dur1) {
      bubbleText = bubbleChunks[0];
      bubbleLocalSec = inPartSec;
    } else if (inPartSec < dur1 + SPLIT_GAP_SEC) {
      bubbleVisible = false; // 지워지는 짧은 틈
    } else {
      bubbleText = bubbleChunks[1];
      bubbleLocalSec = inPartSec - dur1 - SPLIT_GAP_SEC;
    }
  }
  const bubblePop = spring({
    fps,
    frame: bubbleLocalSec * fps,
    config: { damping: 11, stiffness: 220, mass: 0.6 },
  });
  const bounce = interpolate(
    spring({
      fps,
      frame: inPart,
      config: { damping: 9, stiffness: 260, mass: 0.5 },
    }),
    [0, 1],
    [0.9, 1],
  );
  const wobble = silent ? 1 : 1 + Math.sin(inPart / 4.5) * 0.016;
  const bigIn = spring({
    fps,
    frame: inPart - 2,
    config: { damping: 12, stiffness: 200 },
  });

  const cast = [
    { who: "올마", x: LEFT },
    { who: L.who === "올마" ? L.with : L.who, x: RIGHT },
  ];

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* 🔴 배경이 장면별로 바뀐다 — 대사 시작에 맞춰 하드컷 */}
      <Img
        src={staticFile(`bg/${L.bg || "marat03"}.png`)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,.5) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 44%, rgba(0,0,0,.62) 100%)",
        }}
      />
      {/* 장면 카드 — parts 플래그 하나당 카드 하나 */}
      {p.shopA && <ShopA step={p.shopA} />}
      {p.shopB && <ShopB step={p.shopB} />}
      {p.basket && <Basket />}
      {p.scaleA && <ScaleA />}
      {(p.upto || p.total) && (
        <LedgerB upto={p.upto} hot={p.hot ?? -1} total={p.total} />
      )}
      {p.compare && <Compare />}
      {p.tip && <Tip step={p.tip} />}
      {p.site && <Site pop={bigIn} />}
      {/* 훅 = 썸네일. 0프레임에 최종 크기로 완성돼 있어야 한다(커지는 애니메이션 금지) */}
      {/* 🔴 "글씨 크게"는 이 훅 카드(=썸네일) 얘기였다(2026-07-22 정정). 여기만 더 키운다. */}
      {/* 🔴 2026-07-22 스샷 피드백 3건 — ①손그림 아이콘 제외, 실제 일러스트로 교체
          ②"9,000원 집보다" 줄이기  ③카드 살짝 내리기(top 200→230) */}
      {/* 🔴 2026-07-22 재수정 — 배지를 카드 밑으로 내려 카드 너비만큼 키우고,
          카드 안쪽 빈 공간(비싸다? 아래)을 줄이려고 아래쪽 패딩을 크게 줄였다.
          Img의 translate/scale은 대표님이 스튜디오에서 직접 잡은 값이라 그대로 둔다. */}
      {p.hook && (
        <div
          style={{
            position: "absolute",
            top: hookTop,
            left: "50%",
            transform: "translateX(-50%)",
            width: 1000,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              position: "relative",
              width: "100%",
              boxSizing: "border-box",
              background: "rgba(12,12,14,0.82)",
              border: "8px solid #000",
              borderRadius: 30,
              padding: `26px 34px ${cardBottomPad}px`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 10,
            }}
          >
            {/* 🔴 그릇을 흐름(flow)에서 뺐다(2026-07-22 지시) — 전엔 카드 맨 위에서 자리를
                차지해서 글자를 아래로 밀고, 그만큼 카드 아래에 빈 공간이 남았다.
                이제 absolute라 레이아웃 높이에 안 잡히고, 순수 장식으로 얹힌다.
                ⚠️ translate/scale 숫자는 캔버스 드래그 값 그대로 — 손대지 말 것 */}
            <Img
              src={staticFile("bg/marat_bowl.png")}
              style={{
                position: "absolute",
                // 🔴 예전에 flex로 가운데 정렬됐을 때의 위치를 그대로 숫자로 옮겼다
                //    (content폭 916 기준 가운데 = left 370, padding-top 26 - marginTop 6 = top 28).
                //    %+translateX 조합은 scale(3.96)과 겹치면 계산이 꼬여서 픽셀로 고정했다.
                top: 28,
                left: 370,
                zIndex: -1,
                width: 260,
                translate: "25.2px 993.3px",
                scale: 3.96,
              }}
            />
            <div
              style={{
                fontFamily: JUA,
                fontSize: subtitleSize,
                color: "#C9C4B8",
                lineHeight: 1.02,
                whiteSpace: "nowrap",
                marginTop: -2,
              }}
            >
              셀프마라탕 두 종류, 같은 한 끼
            </div>
            <div
              style={{
                fontFamily: BLACK,
                fontSize: line1Size,
                color: "#fff",
                lineHeight: 1.05,
                whiteSpace: "nowrap",
              }}
            >
              6,000원 집이
            </div>
            <div
              style={{
                fontFamily: BLACK,
                fontSize: line2Size,
                color: C.yellow,
                lineHeight: 1.05,
                whiteSpace: "nowrap",
              }}
            >
              9,000원 집보다
            </div>
            <div
              style={{
                fontFamily: BLACK,
                fontSize: line3Size,
                color: "#fff",
                lineHeight: 1.05,
                whiteSpace: "nowrap",
              }}
            >
              비싸다?
            </div>
          </div>
          <div style={{ width: "100%", marginTop: badgeGapTop }}>
            <SeriesBadge fontSize={badgeFontSize} />
          </div>
        </div>
      )}
      {/* 🔴 훅(썸네일) 화면엔 브랜드볼 둘을 안 띄운다(2026-07-22 지시) — 그릇 일러스트만 크게 보여준다. */}
      {!p.hook &&
        cast.map(({ who, x }) => {
        const talking = who === L.who;
        const s = talking ? BIG * bounce * wobble : SMALL;
        return (
          <div
            key={who + x}
            style={{
              position: "absolute",
              // 🔴 조금 내렸다(2026-07-22 지시): 1130→1145. 말할 때 1.28배로 커지면
              //    발끝이 1145+512=1657까지 내려가서 안전영역(1660) 턱밑이다 — 더는 못 내린다.
              top: 1145,
              left: `calc(50% + ${x}px)`,
              transform: "translateX(-50%)",
              transformOrigin: "50% 100%",
              zIndex: talking ? 2 : 1,
            }}
          >
            <div
              style={{ transform: `scale(${s})`, transformOrigin: "50% 100%" }}
            >
              <BrandBall
                brand={who}
                face={talking ? p.face : p.of || "시치미"}
                scale={1.0}
                mouth={
                  talking && !silent
                    ? mouthAt(voices[li], L.head + inLine)
                    : null
                }
              />
            </div>
          </div>
        );
      })}
      {!silent && !p.noBubble && bubbleVisible && (
        // 🔴 y를 760→820으로 내렸다(2026-07-22 지시, 모자 내린 것과 같이 아래로).
        <Bubble y={820} pop={bubblePop} side={L.who === "올마" ? "left" : "right"}>
          {bubbleText}
        </Bubble>
      )}
      {/* 목소리 — head만큼 건너뛰고 발화 길이만. 끝 0.12초 페이드아웃 */}
      {LINES.map((l, i) => {
        const n = Math.round(l.sec * fps);
        const out = Math.round(0.12 * fps);
        return (
          <Sequence
            key={i}
            from={Math.round(LINE_AT[i] * fps)}
            durationInFrames={n}
            name={`${i + 1} ${l.who}`}
          >
            <Audio
              src={staticFile(`voice/${String(i + 1).padStart(2, "0")}.mp3`)}
              trimBefore={Math.round(l.head * fps)}
              trimAfter={Math.round((l.head + l.sec + 0.1) * fps)}
              volume={(x) =>
                interpolate(x, [0, 1, n - out, n], [0, 1, 1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              }
            />
          </Sequence>
        );
      })}
      {/* 효과음 — BGM 없음. 정적 구간(합계 뒤 0.7초)엔 아무것도 안 넣는다 */}
      <Hit t={0.15} src="paper.mp3" vol={0.5} dur={1.2} />
      {/* 소개 카드 등장 */}
      <Hit t={partAt(2, 0)} src="tick.mp3" vol={0.55} dur={0.5} />
      <Hit t={partAt(3, 0)} src="tick.mp3" vol={0.55} dur={0.5} />
      {/* B집 계산서 한 줄씩 */}
      <Hit t={partAt(6, 0)} src="tick.mp3" vol={0.6} dur={0.5} />
      <Hit t={partAt(6, 1)} src="tick.mp3" vol={0.6} dur={0.5} />
      <Hit t={partAt(6, 2)} src="tick.mp3" vol={0.6} dur={0.5} />
      {/* 합계 동전 — 대사(1.19초) 안에서 끝나야 한다. 정적을 침범하면 음향 사고 */}
      <Hit t={partAt(7, 0) + 0.1} src="coins.mp3" vol={0.65} dur={0.95} />
      {/* 마무리 차임 */}
      {/* 🔴 소리가 작다는 지적(2026-07-22) — 0.5→0.85→1.0(최대). 더 키우려면 원본 mp3 자체를 증폭해야 한다 */}
      <Hit t={partAt(11, 1)} src="chime.mp3" vol={1.0} dur={1.8} />
    </AbsoluteFill>
  );
};
