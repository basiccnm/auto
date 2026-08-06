// 사장픽 조합 쇼츠 — 공통 화면 (2026-07-27)
//
// 🔴 편이 바뀌어도 이 파일은 그대로 쓴다. 편별 파일(combo_*.js)이 데이터만 바꾼다.
// 🔴 **올마가 나온다**(2026-07-27 방침 변경). 원가편과 같은 채널에 올리니 톤도 같아야 한다.
//    단, 작게 오른쪽 아래 구석에만. 사장님은 안 나온다.
//
// 장면 구성 (총 15초 · 450프레임 @30fps)
//   0.0~2.5  훅        "집에서 집코바"
//   2.5~7.5  살 것     3개가 하나씩 튀어 들어온다 + 합계
//   7.5~12.5 만드는 법 3단계
//   12.5~15  마무리    완성 요리 + 링크 안내
import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

import { BLACK, JUA, NOTO } from "../shorts/fonts";
import { TONE } from "../cards/tone";
import { GridBg, Ribbon } from "../cards/SoftKit";
import { ICON } from "../cards/props";
import { useAudioData } from "@remotion/media-utils";

import { BrandBall } from "../olma/BrandBall";
import { mouthAt } from "../shorts/talk_engine";

const won = (n) => n.toLocaleString("ko-KR");

// 🔴 정지 그림만 나열하면 밋밋하다(2026-07-27 지적). 아래 세 가지로 움직임을 준다.
//    ① Float — 위아래로 천천히 떠다닌다 (완성 요리·재료)
//    ② Shake — 좌우로 흔들린다 (쉐키쉐키·지글지글)
//    ③ Steam — 김이 모락모락 올라간다

const Float = ({ amp = 14, speed = 1, children, style }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ ...style, transform: `translateY(${Math.sin((f / 30) * speed * Math.PI) * amp}px)` }}>
      {children}
    </div>
  );
};

const Shake = ({ amp = 10, speed = 6, rot = 3, children, style }) => {
  const f = useCurrentFrame();
  const t = (f / 30) * speed * Math.PI;
  return (
    <div style={{ ...style, transform: `translateX(${Math.sin(t) * amp}px) rotate(${Math.sin(t) * rot}deg)` }}>
      {children}
    </div>
  );
};

// 김 — 세 줄기가 시차를 두고 올라가며 흐려진다
const Steam = ({ left = 0, top = 0 }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ position: "absolute", left, top, pointerEvents: "none" }}>
      {[0, 1, 2].map((i) => {
        const p = ((f + i * 22) % 66) / 66;
        return (
          <div key={i} style={{
            position: "absolute", left: i * 46, bottom: p * 150,
            width: 26, height: 26, borderRadius: "50%",
            background: "rgba(255,255,255,.85)", opacity: (1 - p) * 0.9,
            transform: `scale(${0.6 + p * 1.1})`,
          }} />
        );
      })}
    </div>
  );
};

// 아래에서 튀어오르며 등장. 편마다 같은 리듬이라 여기 하나로 둔다
// 🔴 style 에 transform 을 같이 주면 **여기서 덮어써진다**(2026-07-27 카드가 오른쪽으로 밀림).
//    가운데 정렬은 transform 말고 left 좌표로 잡을 것.
const Pop = ({ delay = 0, children, style }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: f - delay, fps, config: { damping: 14, mass: 0.5 } });
  return (
    <div style={{ ...style, opacity: Math.min(s * 2, 1), transform: `translateY(${(1 - s) * 40}px) scale(${0.86 + s * 0.14})` }}>
      {children}
    </div>
  );
};

// ── 올마 — 레시피편에도 캐릭터를 넣는다 (2026-07-27 지시)
//
// 🔴 **사장님은 안 나온다.** 원가편에서 변명하는 역할이라 레시피편엔 자리가 없다.
//    올마 혼자 시청자한테 말하는 톤이다. 목소리도 SunHi 하나뿐(voiceR1).
// 🔴 **작게 넣는다.** 캐릭터를 키우면 상품 카드를 줄여야 하는데,
//    "애들을 줄이면 되지"(2026-07-27) — 카드가 우선이다.
// 🔴 그래서 자리는 **오른쪽 아래 구석 고정.** 판 내용은 전부 그 위쪽에 있다.
const OLMA = { scale: 0.62, left: 782, top: 1548 };

// 🔴 입은 **실제 목소리 파형**에서 뽑는다(2026-07-27 지적 "입모양 안 맞어").
//    sin 파로 흔들면 소리가 없을 때도 입이 움직여 바로 티가 난다.
//    장면마다 그 장면의 mp3 를 읽고, 장면 시작 + LEAD 만큼 지난 지점을 본다.
// 🔴 `건너뜀` 은 이 장면이 그 음성의 **몇 프레임째부터** 나오는지다.
//    조리 3단계는 음성 03 하나를 셋이 나눠 쓰므로, 2·3단계는 그만큼 뒤를 봐야 입이 맞는다.
// 🔴 `손` 은 올마가 **들고 있는 물건**(2026-07-27 지시).
//    볼은 400x400 이고 scale 이 걸리므로, 손 위치도 같은 배율로 따라가야 어긋나지 않는다.
const Olma = ({ face = "웃음", voice, 건너뜀 = 0, 손 = null }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const data = useAudioData(staticFile(voice));
  const mouth = mouthAt(data, (f + 건너뜀 - LEAD) / fps);
  return (
    <Float amp={7} speed={0.8} style={{ position: "absolute", left: OLMA.left, top: OLMA.top, zIndex: 9 }}>
      <div style={{ position: "relative" }}>
        <BrandBall brand="올마" face={face} scale={OLMA.scale} mouth={mouth} />
        {손 && (
          <Img
            src={staticFile(손)}
            style={{
              position: "absolute",
              // 볼 왼쪽 팔 근처. 400 기준 좌표에 배율을 곱해 볼과 같이 커지고 작아진다
              left: -58 * OLMA.scale, top: 196 * OLMA.scale,
              width: 176 * OLMA.scale, height: 176 * OLMA.scale, objectFit: "contain",
              transform: "rotate(-8deg)",
              filter: "drop-shadow(0 8px 16px rgba(180,120,90,.24))",
            }}
          />
        )}
      </div>
    </Float>
  );
};


// ── 자막 (2026-07-28) ────────────────────────────────
//
// 🔴 조리 구간을 음성 길이에 맞춰 줄였더니 화면이 정신없이 넘어갔다.
//    **구간은 5초로 두고 자막을 넣는다** — 소리를 끄고 보는 사람이 대부분이라
//    자막이 있으면 타이밍이 조금 어긋나도 내용이 전달된다.
// 🔴 자막은 **올마를 가리지 않게** 왼쪽 아래. 올마는 오른쪽 아래 구석에 있다.
const Sub = ({ text }) => {
  if (!text) return null;
  return (
    <div style={{
      position: "absolute", left: 60, right: 300, bottom: 96,
      fontFamily: NOTO, fontWeight: 800, fontSize: 42, lineHeight: 1.35,
      color: "#fff", background: "rgba(40,28,22,.78)", borderRadius: 18,
      padding: "14px 22px", zIndex: 8, wordBreak: "keep-all",
    }}>
      {text}
    </div>
  );
};

// ── ① 훅 = **썸네일 그대로** (2026-07-27)
//
// 🔴 썸네일을 따로 만들지 않는다. 첫 장면이 곧 썸네일이다.
//    원가편이 ThumbCard 를 첫 장면으로 쓰는 것과 같은 방식 —
//    두 번 만들 일이 없고, 썸네일과 영상 첫 프레임이 어긋날 수도 없다.
//    편별 파일에서 renderHook 으로 넘긴다.

// ── ② 살 것 — 그림 + 이름 + 값. 하나씩 들어온다
// 🔴 상품 개수에 맞춰 간격을 좁힌다(2026-07-28). 3개 기준으로 380+i*300 을 박아뒀더니
//    지코바 편(4개)에서 마지막 카드가 «다 합쳐» 와 겹쳤다. 개수가 늘 3개라는 보장이 없다.
const buyRow = (n) => (n >= 4 ? { top: 350, gap: 238 } : { top: 380, gap: 300 });

export const Buy = ({ ITEMS, total, checkedAt, voice, 손, 자막 }) => (
  <AbsoluteFill>
    <Olma face="웃음" voice={voice} 손={손} />
    <Sub text={자막} />
    <div style={{ position: "absolute", top: 190, width: "100%", textAlign: "center",
                  fontFamily: BLACK, fontSize: 96, color: TONE.ink }}>
      이것만 사면 돼요
    </div>
    {ITEMS.map((it, i) => (
      <Pop key={i} delay={i * 14}
        style={{ position: "absolute", top: buyRow(ITEMS.length).top + i * buyRow(ITEMS.length).gap, left: 60,
                 width: 960, boxSizing: "border-box", display: "flex", alignItems: "center", gap: 22,
                 background: TONE.card, borderRadius: 36, padding: "22px 30px", boxShadow: TONE.shadow }}>
        <Img src={staticFile(it.그림)} style={{ width: ITEMS.length >= 4 ? 140 : 170, height: ITEMS.length >= 4 ? 140 : 170, objectFit: "contain", flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* 🔴 카드를 꽉 채우게 크게(2026-07-27 지시). 선택 재료는 배지로 표시한다 */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontFamily: BLACK, fontSize: ITEMS.length >= 4 ? 54 : 64, color: TONE.ink, lineHeight: 1.1 }}>{it.이름}</span>
            {it.선택 && (
              <span style={{ fontFamily: BLACK, fontSize: 42, color: "#fff", background: TONE.point,
                             borderRadius: 999, padding: "8px 24px", whiteSpace: "nowrap" }}>
                선택
              </span>
            )}
          </div>
          <div style={{ fontFamily: JUA, fontSize: 38, color: "#8A7B72", marginTop: 4 }}>{it.메모}</div>
        </div>
        <div style={{ fontFamily: BLACK, fontSize: 72, color: TONE.point, whiteSpace: "nowrap", flexShrink: 0 }}>
          {won(it.값)}
        </div>
      </Pop>
    ))}
    <Pop delay={54} style={{ position: "absolute", top: 1300, width: "100%", textAlign: "center" }}>
      <div style={{ fontFamily: BLACK, fontSize: 112, color: TONE.ink }}>
        다 합쳐 <span style={{ color: TONE.point }}>{won(total)}원</span>
      </div>
      <div style={{ fontFamily: JUA, fontSize: 34, color: "#8A7B72", marginTop: 14 }}>
        · 선택 재료는 뺀 값 · 가격은 {checkedAt} 기준이라 날마다 달라져요 ·
      </div>
    </Pop>
  </AbsoluteFill>
);

// ── ③ 만드는 법 — 단계 하나씩
export const Step = ({ s, i, voice, 건너뜀 = 0, 자막 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <Sub text={자막} />
    {/* 단계마다 표정을 바꿔 같은 그림이 반복되는 느낌을 줄인다 */}
    <Olma face={["놀람", "웃음", "뿌듯"][i % 3]} voice={voice} 건너뜀={건너뜀} 손={s.손} />
    <Img src={staticFile(s.번호)} style={{ position: "absolute", top: 300, width: 200 }} />
    {s.흔들 ? (
      <Shake amp={16} speed={7} rot={4} style={{ position: "absolute", top: 540, width: "100%", display: "flex", justifyContent: "center" }}>
        <Img src={staticFile(s.그림)} style={{ width: 700, filter: "drop-shadow(0 14px 30px rgba(180,120,90,.22))" }} />
      </Shake>
    ) : (
      <Float amp={10} speed={0.9} style={{ position: "absolute", top: 540, width: "100%", display: "flex", justifyContent: "center" }}>
        <Img src={staticFile(s.그림)} style={{ width: 700, filter: "drop-shadow(0 14px 30px rgba(180,120,90,.22))" }} />
      </Float>
    )}
    <div style={{ position: "absolute", top: 1250, width: "100%", textAlign: "center",
                  fontFamily: BLACK, fontSize: 100, color: TONE.ink }}>
      {s.글}
    </div>
    <div style={{ position: "absolute", top: 1440, width: "100%", display: "flex",
                  justifyContent: "center", gap: 30 }}>
      {s.불 && <Img src={staticFile(s.불)} style={{ width: 130 }} />}
      {s.시간 && <Img src={staticFile(s.시간)} style={{ width: 130 }} />}
      {s.끝 && <Img src={staticFile(s.끝)} style={{ width: 130 }} />}
    </div>
  </AbsoluteFill>
);

// ── ④ 마무리 — 링크는 영상에 안 넣는다. 댓글로 보낸다
// 🔴 `주의` 는 **꼭 화면에 보여야 하는 한 줄**이다(2026-07-28).
//    지코바 편의 "지코바 스타일이지 지코바 맛은 아닙니다" 처럼,
//    빼면 사실과 달라지는 문구를 편별 파일에서 넘긴다.
export const End = ({ done, next, voice, 손, 주의 }) => (
  <AbsoluteFill style={{ alignItems: "center" }}>
    <Olma face="뿌듯" voice={voice} 손={손} />
    <Float amp={14} speed={0.6} style={{ position: "absolute", top: 330, width: "100%", display: "flex", justifyContent: "center" }}>
      <Img src={staticFile(done)} style={{ width: 780, filter: "drop-shadow(0 16px 34px rgba(180,120,90,.26))" }} />
    </Float>
    <Steam left={480} top={420} />
    <div style={{ position: "absolute", top: 1010, width: 940, left: "50%", transform: "translateX(-50%)",
                  background: TONE.card, borderRadius: 40, padding: "40px 30px", boxShadow: TONE.shadow,
                  textAlign: "center" }}>
      {/* 🔴 **세 줄까지만.** 다섯 줄로 쌓았더니 뭘 보라는 건지 알 수 없었다
          (2026-07-27 "5줄인데 너무 이상해"). "끝" 은 지웠다 — 영상이 끝나는 건 보면 안다.
          🔴 크고 굵게 검정. 40~46px Jua 회갈색은 폰에서 안 읽힌다("잘 보이지도 않아"). */}
      {/* 🔴 폰트는 **Noto Sans KR 900**(2026-07-27 "폰트를 바꾸라고").
          Black Han Sans 는 굵지만 자간이 좁고 각져서 이 판처럼 글이 여러 줄이면 뭉개진다.
          숫자·훅에는 계속 쓰되, **읽어야 하는 문장**은 Noto 로 간다. */}
      <div style={{ fontFamily: NOTO, fontWeight: 900, fontSize: 76, color: TONE.ink, letterSpacing: -1 }}>
        구매는 댓글에
      </div>
      {주의 && (
        <div style={{ fontFamily: NOTO, fontWeight: 700, fontSize: 36, color: "#8A7B72", marginTop: 12 }}>
          {주의}
        </div>
      )}
      {next && (
        <div style={{ fontFamily: NOTO, fontWeight: 800, fontSize: 64, color: "#4A3A32", marginTop: 24 }}>
          {/* 🔴 메뉴명만 색을 달리한다 — 다음 편에 뭐가 나오는지가 이 줄의 알맹이다 */}
          NEXT. <span style={{ color: TONE.point }}>{next}</span>
        </div>
      )}
      {/* 🔴 구독 줄은 **색이 아니라 모양**으로 구분한다(2026-07-27 "밑에 색상이랑 똑같잖아").
          예고 메뉴명이 코럴이라 글씨색으로는 겹친다 → 코럴을 배경으로 깔고 글씨는 흰색.
          버튼처럼 보여서 누르라는 뜻도 같이 전달된다. */}
      <div style={{ display: "inline-block", background: "#E03131", borderRadius: 999,
                    padding: "14px 46px", marginTop: 24 }}>
        <div style={{ fontFamily: NOTO, fontWeight: 900, fontSize: 60, color: "#fff", letterSpacing: -1 }}>
          구독하기
        </div>
      </div>
    </div>
  </AbsoluteFill>
);

// ── 전체 조립
//
// 🔴 음성은 **4줄만** 넣는다(2026-07-27). 판이 6장인데 다 읽으면 늘어진다.
//    voiceS1/01~04.mp3 — 훅 · 살 것 · 조리 · 마무리
//    장면 시작보다 살짝 늦게(LEAD) 넣어야 화면이 먼저 뜨고 말이 따라온다.
const LEAD = 6; // 프레임

// 🔴 조리 3단계를 **150프레임(5초)에 고정**해뒀더니, 음성이 3.9초로 짧은 편에서
//    마지막 1.1초가 소리 없이 떠 있었다(2026-07-28 "너무 느려").
//    그리고 대사가 2단계를 말하는 중에 화면은 이미 3단계로 넘어갔다.
//    → **음성 길이에 맞춰 나눈다.** 편별 파일이 `EP.조리초` 로 실측값을 준다.
//    남는 시간은 마무리 판이 가져간다 — 마무리는 길어도 어색하지 않다.
export const ShopCombo = ({ EP, ITEMS, total, STEPS, DONE, 손, renderHook, voiceDir = "voiceS1" }) => {
  const 조리 = Math.round((5 * 30) / STEPS.length);   // 단계 하나당 프레임 (5초 고정)
  const 조리끝 = 225 + 조리 * STEPS.length;
  return (
  <GridBg base={TONE.bg} line={TONE.grid}>
    <Sequence durationInFrames={75}>{renderHook()}</Sequence>
    <Sequence from={75} durationInFrames={150}>
      <Buy ITEMS={ITEMS} total={total} checkedAt={EP.checkedAt} voice={`${voiceDir}/02.mp3`} 손={손?.살것} 자막={EP.자막?.[1]} />
    </Sequence>
    {STEPS.map((s, i) => (
      <Sequence key={i} from={225 + i * 조리} durationInFrames={조리}>
        <Step s={s} i={i} voice={`${voiceDir}/03.mp3`} 건너뜀={i * 조리} 자막={EP.자막?.[2]} />
      </Sequence>
    ))}
    <Sequence from={조리끝} durationInFrames={450 - 조리끝}><End done={DONE} next={EP.next} voice={`${voiceDir}/04.mp3`} 손={손?.마무리} 주의={EP.주의} /></Sequence>

    {/* 음성 — 장면 머리에 맞춰 깐다 */}
    <Sequence from={LEAD}><Audio src={staticFile(`${voiceDir}/01.mp3`)} /></Sequence>
    <Sequence from={75 + LEAD}><Audio src={staticFile(`${voiceDir}/02.mp3`)} /></Sequence>
    <Sequence from={225 + LEAD}><Audio src={staticFile(`${voiceDir}/03.mp3`)} /></Sequence>
    <Sequence from={조리끝 + LEAD}><Audio src={staticFile(`${voiceDir}/04.mp3`)} /></Sequence>

    {/* 🔴 효과음 — 그림만으론 감각이 안 산다. 카드 등장·조리·완성에 하나씩 */}
    {/* 🔴 카드가 들어올 때 **종이 넘기는 소리**(2026-07-27 지시). pop_in 은 장난스러워서 뺐다 */}
    <Sequence from={78} durationInFrames={22}><Audio src={staticFile("sfx/paper.mp3")} volume={0.55} /></Sequence>
    <Sequence from={92} durationInFrames={22}><Audio src={staticFile("sfx/paper.mp3")} volume={0.55} /></Sequence>
    <Sequence from={106} durationInFrames={22}><Audio src={staticFile("sfx/paper.mp3")} volume={0.55} /></Sequence>
    <Sequence from={132} durationInFrames={40}><Audio src={staticFile("sfx/chime.mp3")} volume={0.5} /></Sequence>
    {STEPS.map((_, i) => (
      <Sequence key={`s${i}`} from={225 + i * 조리} durationInFrames={24}>
        <Audio src={staticFile("sfx/click.mp3")} volume={0.45} />
      </Sequence>
    ))}
    <Sequence from={조리끝} durationInFrames={50}><Audio src={staticFile("sfx/chime.mp3")} volume={0.7} /></Sequence>
  </GridBg>
  );
};
