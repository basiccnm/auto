// 만담 조립 엔진 — 편이 바뀌어도 그대로 쓴다 (2026-07-23 분리)
//
// 🔴 왜 뺐나: 1편(Talk.jsx)에서 조립 로직·말풍선·효과음 처리를 그대로 복사해 2편을 만들면
//    같은 코드가 두 벌이 된다. 편은 계속 늘어나므로 엔진을 공통으로 두고
//    **편별 파일은 카드(화면)만 정의**하게 했다.
//
//    쓰는 쪽(예: Talk2.jsx):
//      <TalkEngine lines={LINES} lead={LEAD} voiceDir="voice2"
//                  renderCards={(p, ctx) => ...} renderHook={() => ...}
//                  sfx={(at) => [{ t: at(2,0), src: "tick.mp3" }]} />
//
// 🔴 1편(Talk.jsx)은 아직 이 엔진을 안 쓴다. 이미 렌더·업로드가 끝난 편이라
//    건드려서 깨질 위험을 피했다. 3편부터는 이 엔진만 쓴다.
import React from "react";
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
import { BLACK, JUA } from "./fonts";

export const won = (n) => n.toLocaleString() + "원";

// ── 배치 상수 ────────────────────────────────────────────────
// 🔴 안전 영역(3편에서 데임): 카드는 top 200부터, 캐릭터 발끝 1660 이내.
//    캐릭터 top 1145 + 말할 때 1.28배 = 발끝 1657. 더 내리면 하단 UI에 먹힌다.
// 🔴 여성향 톤 배경(2026-07-25) — bg:"soft" 일 때 쓴다
const SOFT_BG = "#F7E2D8";
const SOFT_GRID = "rgba(175,120,95,.34)"; // 🔴 .15는 화면에서 안 보였다(2026-07-25)

export const LEFT = -225;
export const RIGHT = 225;
export const BIG = 1.28;
export const SMALL = 1.0;
export const BALL_TOP = 1145;

// ── 카드 공통 ────────────────────────────────────────────────
// 🔴 pop을 주면 카드가 **아래에서 튀어오르며 등장**한다(2026-07-23 이펙트 요청).
//    안 주면 그냥 뜬다(장면 내내 떠 있는 카드는 매번 튀면 정신없다).
// 🔴 soft=true 면 **흰 카드 + 그림자**(여성향 톤). 안 주면 예전 검정 판 그대로다 —
//    마라탕·피자편이 그 판을 쓰고 있어서 기본값은 바꾸지 않는다(2026-07-25).
export const Card = ({ children, wide = false, top = 200, pop, soft = false }) => {
  const enter = pop == null ? 1 : pop;
  return (
    <div
      style={{
        position: "absolute",
        top,
        left: "50%",
        transform: `translateX(-50%) translateY(${(1 - enter) * 70}px) scale(${0.9 + enter * 0.1})`,
        transformOrigin: "50% 0%",
        opacity: Math.min(enter * 2, 1),
        width: wide ? 1000 : 880,
        boxSizing: "border-box",
        background: soft ? "#FFFFFF" : "rgba(12,12,14,0.82)",
        border: soft ? "none" : "8px solid #000",
        boxShadow: soft ? "0 14px 40px rgba(170,140,120,.16)" : "none",
        borderRadius: soft ? 38 : 30,
        padding: "26px 34px 22px",
      }}
    >
      {children}
    </div>
  );
};

// 🔴 pop을 주면 방금 뜬 줄이 **왼쪽에서 슥 들어오며 한 번 튕긴다**(2026-07-23 이펙트 요청).
//    숫자가 그냥 나타나면 눈이 안 따라온다. 움직임이 있어야 시선이 꽂힌다.
export const Row = ({ name, val, hi, big, dim, size, pop }) => {
  const enter = pop == null ? 1 : pop;
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        gap: 16,
        fontFamily: big ? BLACK : JUA,
        fontSize: size || (big ? 84 : hi ? 60 : 50),
        color: big || hi ? C.yellow : dim ? "#B9B4A8" : "#fff",
        marginTop: big ? 10 : 8,
        opacity: Math.min(enter * 1.8, 1),
        transform: `translateX(${(1 - enter) * -60}px) scale(${0.94 + enter * 0.06})`,
        transformOrigin: "0% 50%",
      }}
    >
      <span style={{ whiteSpace: "nowrap" }}>{name}</span>
      {val != null && (
        <span style={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
          {val}
        </span>
      )}
    </div>
  );
};

export const Title = ({ children, color = C.yellow }) => (
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

// 시리즈 배지 — 제목엔 못 박으니 썸네일(훅 카드) 밑에 카드 너비만큼 깔린다
export const SeriesBadge = ({ label, fontSize = 62 }) => (
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
    {label}
  </div>
);

// 마무리 판 — **구독 유도 + 다음 편 예고** (2026-07-27 전면 교체)
//
// 🔴 왜 바꿨나: 완주율은 높은데(뿌링클 96%) 구독이 안 붙었다. 5,400회에 구독 1명.
//    끝까지 본 사람한테 **구독하라는 말을 한 번도 안 했기 때문**이다.
//    그 자리를 사이트 주소(olmanama.com)가 차지하고 있었는데,
//    쇼츠에서 외부 링크는 전환이 거의 없다 → 사이트 유도는 **고정 댓글로만** 한다.
//
// 🔴 다음 편 메뉴를 예고하면 구독할 **이유**가 생긴다(시리즈로 이어보게 만든다).
//    편별 파일에서 next="도미노 포테이토 피자" 처럼 넘긴다. 안 넘기면 두루뭉술한 문구로 대체.
//
// 🔴 기존 편(마라탕·피자)은 soft 를 안 줘서 **옛 검정 판 그대로** 나온다. 안 건드린다.
export const Site = ({
  pop, site, disc, soft = false, next = "",
  ask = "마라탕 궁금한 거 있으면\n쇼츠로 알려드려요!",
}) => (
  <Card wide soft={soft}>
    {soft ? (
      <>
        <div
          style={{
            textAlign: "center", fontFamily: JUA, fontSize: 52,
            color: "#6E5A4E", opacity: pop,
          }}
        >
          {next ? "다음은" : "다음도"}
        </div>
        <div
          style={{
            textAlign: "center", fontFamily: BLACK, fontSize: next ? 96 : 84,
            color: "#111111", lineHeight: 1.1, marginTop: 6,
            whiteSpace: next.length > 9 ? "normal" : "nowrap",
          }}
        >
          {next || "원가 깝니다"}
        </div>
        <div style={{ borderTop: "4px solid #F3EAE3", margin: "20px 0 16px" }} />
        <div
          style={{
            textAlign: "center", fontFamily: BLACK, fontSize: 76,
            color: "#E05575", lineHeight: 1.2,
          }}
        >
          구독하면 안 놓쳐요
        </div>
        <div
          style={{
            textAlign: "center", fontFamily: JUA, fontSize: 38,
            color: "#8A7B72", marginTop: 14,
          }}
        >
          궁금한 메뉴는 댓글로
        </div>
      </>
    ) : (
      <>
        <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 100, color: "#fff", opacity: pop }}>
          {site}
        </div>
        <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 46, color: "#B9B4A8", marginTop: 8 }}>
          음식 원가, 여기 다 있습니다
        </div>
        <div style={{ borderTop: "6px solid #4A4A4A", margin: "22px 0 18px" }} />
        <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 64, color: C.yellow, lineHeight: 1.25 }}>
          {ask.split("\n").map((x) => (
            <div key={x}>{x}</div>
          ))}
        </div>
        <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 72, color: "#fff", marginTop: 10, lineHeight: 1.15 }}>
          댓글 남겨주세요!!!!
        </div>
        {disc && (
          <>
            <div style={{ borderTop: "4px solid #4A4A4A", margin: "20px 0 0" }} />
            <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 34, color: "#9C978C", marginTop: 12, lineHeight: 1.35 }}>
              {disc.split("\n").map((x) => (
                <div key={x}>{x}</div>
              ))}
            </div>
          </>
        )}
      </>
    )}
  </Card>
);

// ── 말풍선 ────────────────────────────────────────────────────
// 🔴 항상 1줄로만 나온다(2026-07-22 지시) — 2줄로 접히면 높이가 그때그때 달라져
//    자리가 안 잡힌 것처럼 보인다. 길면 글자를 줄이고, 아주 길면 둘로 쪼개 순서대로 보여준다.
// 🔴 2026-07-24 전면 교체 — 글자를 줄이지 않고 **문장을 더 잘게 쪼개 순서대로** 보여준다.
//    (대표님 지적: "글씨가 작아지는 거 있잖아, 앞 문장 나오고 그다음 문장 나오게 해서 크기 맞춰라")
//    옛 방식: 16자 넘으면 폰트를 최소 44까지 줄이고, 20자 넘으면 딱 2조각으로만 쪼갬
//             → 긴 대사는 2조각이어도 한 조각이 23자씩이라 결국 글씨가 작아졌다.
//    새 방식: 한 조각이 16자를 넘지 않게 **필요한 만큼** 쪼갠다. 그래서 폰트는 거의 항상 72.
const BASE_FONT = 72;
const MAX_CHARS_AT_BASE = 16;
const MIN_FONT = 58; // 44 → 58. 이 밑으로는 안 줄인다 — 줄이는 대신 쪼갠다
export const bubbleFontSize = (text) => {
  const n = (text || "").length;
  if (n <= MAX_CHARS_AT_BASE) return BASE_FONT;
  return Math.max(MIN_FONT, Math.round((BASE_FONT * MAX_CHARS_AT_BASE) / n));
};

const SPLIT_GAP_SEC = 0.1; // 조각 사이 깜빡임 — 넘어간 게 보여야 한다
const MIN_CHUNK_SEC = 0.55; // 조각 하나가 이보다 짧으면 못 읽는다
const HARD_MAX_CHARS = 34; // 여기까지 늘려도 시간이 안 나오면 그냥 글자를 줄인다

// 🔴 자르는 자리에 우선순위를 둔다 — 문장 끝 > 쉼표 > 그냥 띄어쓰기.
//    안 그러면 "15,900원. 할인 적은 / 집이 1,000원 더 쌉니다"처럼 문장 중간이 끊겨 읽기 나쁘다.
//    ⚠️ 쉼표는 **뒤에 공백이 있는 것만** 경계로 본다. "13,900"의 쉼표에서 잘리면 안 되니까.
const BREAKS = [/[.?!]\s/g, /,\s/g, /\s/g];

const packWords = (text, max) => {
  const s = (text || "").trim();
  if (s.length <= max) return [s];
  for (const re of BREAKS) {
    const idxs = [...s.matchAll(re)].map((m) => m.index + m[0].length);
    if (!idxs.length) continue;
    // 가운데에 제일 가까운 경계에서 자르고, 양쪽을 다시 같은 규칙으로 처리한다
    const mid = s.length / 2;
    const cut = idxs.reduce((a, b) => (Math.abs(b - mid) < Math.abs(a - mid) ? b : a));
    return [...packWords(s.slice(0, cut), max), ...packWords(s.slice(cut), max)];
  }
  return [s];
};

// 조각이 너무 많아 하나가 0.55초도 못 받으면, 상한을 늘려 조각 수를 줄인다
export const splitBubbleText = (text, sec = 99) => {
  if (!text) return [text];
  let max = MAX_CHARS_AT_BASE;
  let chunks = packWords(text, max);
  while (chunks.length > 1 && sec / chunks.length < MIN_CHUNK_SEC && max < HARD_MAX_CHARS) {
    max += 4;
    chunks = packWords(text, max);
  }
  return chunks;
};

export const Bubble = ({ children, y, pop, side }) => {
  const tail = side === "left" ? "24%" : "76%";
  const fontSize = bubbleFontSize(children);
  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: "50%",
        // 🔴 캐릭터(zIndex 1~2)보다 위여야 한다. zIndex:auto면 항상 아래로 깔린다
        zIndex: 5,
        transform: `translateX(-50%) scale(${pop})`,
        // 🔴 꼬리 위치를 기준으로 팝업하면 대사마다 좌우로 튄다. 가운데 고정
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

// ── 감정 텍스트 (2026-07-23 추가) ──────────────────────────────
// 🔴 표정 9종만으로는 "꺼드럭꺼드럭" 같은 미묘한 감정이 안 나온다(2026-07-23 지시).
//    폴란드볼 문법대로 **캐릭터 옆에 작은 글자를 붙여** 감정을 푼다.
//    예: 꺼드럭꺼드럭 · 부들부들 · 씨익 · 헉 · 발끈 · 주르륵
//    lines의 part에 `emo: { who: "올마", text: "꺼드럭꺼드럭" }` 로 넣는다.
export const EmoText = ({ text, side, pop = 1 }) => {
  // 말하는 쪽 위에 살짝 기울여 붙는다. 좌우는 캐릭터 위치를 따라간다
  const x = side === "left" ? LEFT : RIGHT;
  const tilt = side === "left" ? -8 : 8;
  // 🔴 2026-07-24 위치 교정 — 원래 BALL_TOP-90 / ±150 이라 모자 라벨("사장님")과 겹쳤다.
  //    1차로 ±190까지 벌렸더니 이번엔 오른쪽 글자가 **화면 밖으로 잘렸다**
  //    ("당연하지"·"부들부들"·"히힣" 끝이 날아감). 최종: 위로 165, 좌우 ±140.
  return (
    <div
      style={{
        position: "absolute",
        top: BALL_TOP - 165,
        left: `calc(50% + ${x + (side === "left" ? -140 : 140)}px)`,
        transform: `translateX(-50%) rotate(${tilt}deg) scale(${0.6 + pop * 0.4})`,
        opacity: Math.min(pop * 2, 1),
        zIndex: 4,
        fontFamily: BLACK,
        fontSize: 46,
        color: "#fff",
        WebkitTextStroke: "9px #000",
        paintOrder: "stroke fill",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
};

// ── 효과음 ────────────────────────────────────────────────────
// 🔴 끝을 그냥 자르면 "뚝" 하고 사고처럼 들린다. 0.35초 페이드아웃 필수
export const Hit = ({ t, src, vol = 0.7, dur = 1.2 }) => {
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

// 목소리 파형 → 입 벌림(0~1)
export const mouthAt = (data, sec) => {
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

// ── 길이 계산 헬퍼 (Root.jsx에서 durationInFrames 구할 때 쓴다) ──
export const talkSec = (lines, lead) =>
  lead + lines.reduce((a, l) => a + l.sec + (l.gap || 0), 0);

// ── 엔진 본체 ──────────────────────────────────────────────────
export const TalkEngine = ({
  lines,
  lead = 0.2,
  voiceDir = "voice",
  bubbleY = 820,
  defaultBg = "marat03",
  renderCards, // (p, ctx) => JSX   ctx = { bigIn, L, li }
  renderHook, // (p, ctx) => JSX   훅(썸네일) 화면 — 캐릭터는 자동으로 숨는다
  sfx, // (at) => [{ t, src, vol, dur }]   at(lineIdx, partIdx) = 그 화면 시작 초
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;

  // 🔴 훅 규칙상 개수가 고정이어야 한다. lines는 편마다 고정이라 안전하다
  const voices = lines.map((_, i) =>
    useAudioData(staticFile(`${voiceDir}/${String(i + 1).padStart(2, "0")}.mp3`)),
  );

  const LINE_AT = lines.reduce((acc, l, i) => {
    acc.push(i === 0 ? lead : acc[i - 1] + lines[i - 1].sec + (lines[i - 1].gap || 0));
    return acc;
  }, []);
  const at = (li, pi) =>
    LINE_AT[li] + lines[li].parts.slice(0, pi).reduce((a, p) => a + p.sec, 0);

  let li = 0;
  for (let i = 0; i < lines.length; i++) {
    if (t >= LINE_AT[i]) li = i;
  }
  const L = lines[li];
  const inLine = t - LINE_AT[li];
  const silent = inLine > L.sec;

  // 🔴 gap(숨) 구간 버그 수정(2026-07-23) — 대사가 끝나고 숨으로 넘어가면
  //    pStart가 대사 끝으로 밀려서 inPart가 0으로 리셋됐다. 그래서 스프링이 다시 돌고
  //    **같은 순위가 한 번 더 쿵 떨어지는** 현상이 났다("전 순위가 다시 떨어짐").
  //    이제 마지막 part의 시작점을 그대로 유지한다.
  let acc = 0;
  let p = L.parts[0];
  let pStart = 0;
  for (const q of L.parts) {
    if (inLine < acc + q.sec) {
      p = q;
      pStart = acc;
      break;
    }
    p = q; // 숨 구간이면 마지막 part를 그대로 들고 간다
    pStart = acc; // ← acc를 더하기 **전** 값이라야 그 part의 시작점이다
    acc += q.sec;
  }
  const inPart = (inLine - pStart) * fps;

  // 긴 대사는 절반씩 나눠 순서대로. 캐릭터 튐은 part 기준, 말풍선 팝인만 조각 기준
  const inPartSec = inLine - pStart;
  // 🔴 2026-07-24 — 조각이 2개 고정이 아니라 **N개**다. 글자 수에 비례해 시간을 나눠 갖고
  //    조각 사이엔 아주 짧게 사라졌다 나타난다(넘어간 걸 눈이 알아채야 한다).
  const chunks = splitBubbleText(p.text, p.sec);
  let bubbleText = chunks[chunks.length - 1];
  let bubbleLocalSec = inPartSec;
  let bubbleVisible = true;
  if (chunks.length > 1) {
    const totalChars = chunks.reduce((a, c) => a + c.length, 0);
    const usable = Math.max(0.2, p.sec - SPLIT_GAP_SEC * (chunks.length - 1));
    let t0 = 0;
    for (let ci = 0; ci < chunks.length; ci++) {
      const d = usable * (chunks[ci].length / totalChars);
      if (inPartSec < t0 + d) {
        bubbleText = chunks[ci];
        bubbleLocalSec = inPartSec - t0;
        break;
      }
      if (inPartSec < t0 + d + SPLIT_GAP_SEC) {
        bubbleText = chunks[ci];
        bubbleVisible = false; // 조각 사이 깜빡임
        break;
      }
      t0 += d + SPLIT_GAP_SEC;
      // 마지막 조각을 지나면(숨 구간) 마지막 조각을 그대로 들고 있는다
      if (ci === chunks.length - 1) bubbleLocalSec = inPartSec - (t0 - d - SPLIT_GAP_SEC);
    }
  }

  const bubblePop = spring({
    fps,
    frame: bubbleLocalSec * fps,
    config: { damping: 11, stiffness: 220, mass: 0.6 },
  });
  const bounce = interpolate(
    spring({ fps, frame: inPart, config: { damping: 9, stiffness: 260, mass: 0.5 } }),
    [0, 1],
    [0.9, 1],
  );
  const wobble = silent ? 1 : 1 + Math.sin(inPart / 4.5) * 0.016;
  const bigIn = spring({ fps, frame: inPart - 2, config: { damping: 12, stiffness: 200 } });

  // 🔴 장면 전환 플래시(2026-07-23 이펙트 요청) — 배경이 바뀌는 대사 첫 0.2초에
  //    흰 막이 확 스쳤다 사라진다. 하드컷만 있으면 장면이 바뀐 줄 모르고 지나간다.
  const bgChanged = li > 0 && lines[li - 1].bg !== L.bg;
  const flash = bgChanged
    ? interpolate(inLine, [0, 0.06, 0.22], [0.55, 0.35, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  // 카드·줄 등장용 스프링 — part가 바뀔 때마다 0에서 다시 오른다
  const partPop = spring({
    fps,
    frame: inPart,
    config: { damping: 13, stiffness: 190, mass: 0.7 },
  });

  // 🔴 "쿵" 떨어지는 용 — damping을 낮추고 mass를 키워 무겁게 착지시킨다(2026-07-23).
  //    partPop보다 더 세게 튀어야 가격이 꽂히는 느낌이 난다.
  const dropPop = spring({
    fps,
    frame: inPart,
    config: { damping: 9, stiffness: 150, mass: 1.4 },
  });

  const cast = [
    { who: "올마", x: LEFT },
    { who: L.who === "올마" ? L.with : L.who, x: RIGHT },
  ];
  const ctx = { bigIn, partPop, dropPop, L, li, inLine, silent };

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* ① 배경 — 대사 시작에 맞춰 하드컷.
          🔴 bg가 "soft"면 **이미지 대신 파스텔 격자**를 깐다(2026-07-25 여성향 톤).
             아이소메트릭 매장 그림이 게임 문법이라 뺐다. 기존 편(marat·store·pizza)은 그대로 이미지. */}
      {(L.bg || defaultBg) === "soft" ? (
        <AbsoluteFill
          style={{
            background: SOFT_BG,
            backgroundImage: `linear-gradient(${SOFT_GRID} 1.5px, transparent 1.5px), linear-gradient(90deg, ${SOFT_GRID} 1.5px, transparent 1.5px)`,
            backgroundSize: "54px 54px",
          }}
        />
      ) : (
        <>
          <Img
            src={staticFile(`bg/${L.bg || defaultBg}.png`)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
          <AbsoluteFill
            style={{
              background:
                "linear-gradient(180deg, rgba(0,0,0,.5) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 44%, rgba(0,0,0,.62) 100%)",
            }}
          />
        </>
      )}

      {/* 장면 전환 플래시 — 배경이 바뀐 대사에서만 */}
      {flash > 0 && (
        <AbsoluteFill style={{ background: "#fff", opacity: flash }} />
      )}

      {/* ② 카드 */}
      {renderCards && renderCards(p, ctx)}
      {p.hook && renderHook && renderHook(p, ctx)}

      {/* ④⑤ 캐릭터 — 훅(썸네일)과 noBall 화면엔 안 띄운다.
          🔴 noBall은 전체 표처럼 화면을 꽉 채우는 카드용이다. 볼이 표를 가린다(2026-07-23) */}
      {!p.hook &&
        !p.noBall &&
        cast.map(({ who, x }) => {
          const talking = who === L.who;
          const s = talking ? BIG * bounce * wobble : SMALL;
          return (
            <div
              key={who + x}
              style={{
                position: "absolute",
                top: BALL_TOP,
                left: `calc(50% + ${x}px)`,
                transform: "translateX(-50%)",
                transformOrigin: "50% 100%",
                zIndex: talking ? 2 : 1,
              }}
            >
              <div style={{ transform: `scale(${s})`, transformOrigin: "50% 100%" }}>
                {/* 🔴 소품은 말하는 쪽에만 켠다(2026-07-23). p.prop = "magnifier" 같은 이름 하나만.
                    듣는 쪽 소품은 p.ofProp 으로 따로 준다. 한 캐릭터에 두 개 이상 켜지 말 것 */}
                <BrandBall
                  brand={who}
                  face={talking ? p.face : p.of || "시치미"}
                  scale={1.0}
                  mouth={talking && !silent ? mouthAt(voices[li], L.head + inLine) : null}
                  {...(talking && p.prop ? { [p.prop]: true } : {})}
                  {...(!talking && p.ofProp ? { [p.ofProp]: true } : {})}
                />
              </div>
            </div>
          );
        })}

      {/* 감정 텍스트 — 표정으로 안 되는 감정을 글자로 푼다 (꺼드럭꺼드럭 등) */}
      {!p.hook && !p.noBall && p.emo && (
        <EmoText
          text={p.emo.text}
          side={p.emo.who === "올마" ? "left" : "right"}
          pop={partPop}
        />
      )}

      {/* ③ 말풍선 */}
      {!silent && !p.noBubble && bubbleVisible && (
        <Bubble y={bubbleY} pop={bubblePop} side={L.who === "올마" ? "left" : "right"}>
          {bubbleText}
        </Bubble>
      )}

      {/* 목소리 — head만큼 건너뛰고 발화 길이만. 끝 0.12초 페이드아웃 */}
      {lines.map((l, i) => {
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
              src={staticFile(`${voiceDir}/${String(i + 1).padStart(2, "0")}.mp3`)}
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

      {/* ⑥ 효과음 — BGM 없음 */}
      {sfx &&
        sfx(at).map((s, i) => (
          <Hit key={i} t={s.t} src={s.src} vol={s.vol} dur={s.dur} />
        ))}
    </AbsoluteFill>
  );
};
