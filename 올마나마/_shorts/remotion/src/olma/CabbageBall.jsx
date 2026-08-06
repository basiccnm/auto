// 배추 캐릭터 — 진짜 관절이 움직이는 리깅 캐릭터 (2026-08-04)
//
// 🔴 왜 BrandBall과 다른가: BrandBall은 원 하나에 표정만 갈아끼우는 방식이라
//    팔다리가 없다. 이 캐릭터는 대표가 Gemini로 만든 **관절 스프라이트 시트**
//    (드라이브 `Gemini_Generated_Image_fo4h4nfo4h4nfo4h.png`)를 21개 부위로
//    잘라서 머리-몸통-엉덩이-팔(윗팔·아래팔·손)-다리(허벅지·정강이·발)를
//    각 관절 지점에서 회전시키는 **진짜 순운동학(forward kinematics) 리그**다.
//
// 🔴 부위 잘라내기 — 스크래치패드에서 1회성으로 처리했다. connected-component
//    분석으로 색(초록=그림/검정=텍스트)을 구분해 라벨 텍스트를 전부 제거하고
//    그림만 남겼다. 원본은 `public/cabbage/*.png`.
//    ⚠️ 팔다리는 **한쪽만 잘랐다** — 반대쪽은 `scaleX(-1)`로 거울 반전해서 쓴다.
//
// 🔴 ATTACH 좌표는 **각 부위 PNG에 좌표 격자를 씌워 눈으로 읽어** 잡았다
//    (2026-08-04, 1차 렌더에서 팔다리가 완전히 어긋난 뒤 다시 잡음).
//    부위 하나의 "자기 박스 안에서 다음 부위가 붙는 자리"가 숫자의 의미다.
import React from "react";
import { Img, staticFile } from "remotion";

const cabbage = (n) => staticFile(`cabbage/${n}.png`);

// 부위 원본 픽셀 크기 (스프라이트에서 자른 그대로, 스케일 전)
const SIZE = {
  head: [623, 658], torso: [577, 359], hip: [416, 205],
  thigh: [171, 242], shin: [139, 186],
  upperarm: [200, 241], forearm: [224, 178], hand: [174, 179],
  foot: [192, 198],
};

// 부착점 — "이 부위 자신의 박스 안에서" 관절이 있는 자리 [x,y]px.
// 격자 이미지로 실측(2026-08-04). 왼쪽 기준으로만 잡고 오른쪽은 거울 반전으로 재사용한다.
const ATTACH = {
  headNeck: [310, 625],        // head 안에서 목(torso와 겹치는 자리)
  torsoNeck: [288, 20],        // torso 안에서 머리가 얹히는 자리
  torsoShoulderL: [70, 90],    // torso 안에서 왼쪽 어깨
  torsoHip: [290, 335],        // torso 안에서 엉덩이가 붙는 자리
  hipTorso: [208, 15],         // hip 안에서 torso와 만나는 자리(윗변 중앙)
  hipLegL: [100, 175],         // hip 안에서 왼쪽 다리 소켓
  upperarmShoulder: [95, 15],  // upperarm 자신 안에서 어깨쪽(회전축)
  upperarmElbow: [55, 225],    // upperarm 자신 안에서 팔꿈치쪽(forearm 연결점)
  forearmElbow: [55, 15],      // forearm 자신 안에서 팔꿈치쪽(회전축)
  forearmWrist: [180, 110],    // forearm 자신 안에서 손목쪽(hand 연결점)
  handWrist: [105, 155],       // hand 자신 안에서 손목쪽(회전축)
  thighHip: [75, 15],          // thigh 자신 안에서 엉덩이쪽(회전축)
  thighKnee: [85, 225],        // thigh 자신 안에서 무릎쪽(shin 연결점)
  shinKnee: [70, 15],          // shin 자신 안에서 무릎쪽(회전축)
  shinAnkle: [70, 170],        // shin 자신 안에서 발목쪽(foot 연결점)
  footAnkle: [95, 20],         // foot 자신 안에서 발목쪽(회전축)
};

const EYE = { 기본: "eye_basic", 활짝: "eye_wide", 화남: "eye_angry", 슬픔: "eye_sad", 놀람: "eye_surprised", 질끈: "eye_tightclosed" };
const MOUTH = { 닫음: "mouth_closed", 미소: "mouth_smile", 아: "mouth_ah", 오: "mouth_oh", 이: "mouth_ee", 삐죽: "mouth_pouty" };

// 관절 하나 — 부모 좌표계의 parentAt 지점에, 자기 own 부착점(at)을 회전축으로 놓는다.
// children 은 이 관절 자신의 좌표계 위에서 다시 배치된다(팔꿈치→손목처럼 회전이 자연히 이어받아진다).
const Joint = ({ img, size, at, parentAt, angle = 0, flip = false, children }) => {
  const [w, h] = size;
  const [ax, ay] = at;
  const [px, py] = parentAt;
  return (
    <div style={{
      position: "absolute", left: px - ax, top: py - ay, width: w, height: h,
      transform: `rotate(${angle}deg)`, transformOrigin: `${ax}px ${ay}px`,
    }}>
      <div style={{ width: w, height: h, transform: flip ? "scaleX(-1)" : "none" }}>
        <Img src={cabbage(img)} style={{ width: w, height: h, display: "block" }} />
      </div>
      {children}
    </div>
  );
};

// 팔 하나(윗팔→아래팔→손). side="R" 이면 upperarmShoulder.x 를 부모 폭 기준으로 반전한다.
const Arm = ({ side, shoulder, angle, elbowAngle, wristAngle = 0 }) => {
  const flip = side === "R";
  return (
    <Joint img="upperarm" size={SIZE.upperarm} at={ATTACH.upperarmShoulder}
      parentAt={shoulder} angle={angle} flip={flip}>
      <Joint img="forearm" size={SIZE.forearm} at={ATTACH.forearmElbow}
        parentAt={ATTACH.upperarmElbow} angle={elbowAngle} flip={flip}>
        <Joint img="hand" size={SIZE.hand} at={ATTACH.handWrist}
          parentAt={ATTACH.forearmWrist} angle={wristAngle} flip={flip} />
      </Joint>
    </Joint>
  );
};

// 다리 하나(허벅지→정강이→발)
const Leg = ({ side, hip, angle, kneeAngle, ankleAngle = 0 }) => {
  const flip = side === "R";
  return (
    <Joint img="thigh" size={SIZE.thigh} at={ATTACH.thighHip}
      parentAt={hip} angle={angle} flip={flip}>
      <Joint img="shin" size={SIZE.shin} at={ATTACH.shinKnee}
        parentAt={ATTACH.thighKnee} angle={kneeAngle} flip={flip}>
        <Joint img="foot" size={SIZE.foot} at={ATTACH.footAnkle}
          parentAt={ATTACH.shinAnkle} angle={ankleAngle} flip={flip} />
      </Joint>
    </Joint>
  );
};

// ╔══════════════════════════════════════════════════════════╗
// ║  CabbageBall — 쓰는 쪽에서 각도만 넘기면 포즈가 바뀐다      ║
// ╚══════════════════════════════════════════════════════════╝
//   armL/armR      = 어깨 각도(0 = 아래로 늘어뜨림, 음수 = 앞으로 든다)
//   elbowL/elbowR  = 팔꿈치 각도(부모 각도에 더해짐)
//   legL/legR      = 다리 벌림 각도 · kneeL/kneeR = 무릎 각도
//   headTilt       = 목 각도(고개 갸웃)
//   eye / mouth    = 위 EYE/MOUTH 키 중 하나
export const CabbageBall = ({
  scale = 1,
  eye = "기본", mouth = "미소",
  headTilt = 0,
  armL = 25, elbowL = 10, armR = -25, elbowR = -10,
  legL = 12, kneeL = 0, legR = -12, kneeR = 0,
}) => {
  const hipLegR = [SIZE.hip[0] - ATTACH.hipLegL[0], ATTACH.hipLegL[1]];
  const torsoShoulderR = [SIZE.torso[0] - ATTACH.torsoShoulderL[0], ATTACH.torsoShoulderL[1]];

  // 몸통을 원점(0,0)에 두고, 머리·엉덩이는 몸통의 자식으로 이어 붙인다.
  // 팔다리가 옆으로 뻗을 여유를 두려고 바깥 래퍼에 여백을 준다.
  const PAD_X = 260, PAD_TOP = 640, PAD_BOTTOM = 480;
  const W = SIZE.torso[0] + PAD_X * 2;
  const H = SIZE.torso[1] + PAD_TOP + PAD_BOTTOM;

  return (
    <div style={{ position: "relative", width: W, height: H, transform: `scale(${scale})`, transformOrigin: "top left" }}>
      <div style={{ position: "absolute", left: PAD_X, top: PAD_TOP, width: SIZE.torso[0], height: SIZE.torso[1] }}>
        <Img src={cabbage("torso")} style={{ width: SIZE.torso[0], height: SIZE.torso[1], display: "block" }} />

        {/* 머리 — 목 지점에서 살짝 갸웃할 수 있게 관절로 얹는다 */}
        <Joint img="head" size={SIZE.head} at={ATTACH.headNeck} parentAt={ATTACH.torsoNeck} angle={headTilt}>
          <Img src={cabbage(EYE[eye] || EYE.기본)} style={{ position: "absolute", left: "26%", top: "46%", width: "48%", height: "auto" }} />
          <Img src={cabbage(MOUTH[mouth] || MOUTH.미소)} style={{ position: "absolute", left: "38%", top: "64%", width: "24%", height: "auto" }} />
        </Joint>

        {/* 엉덩이 + 다리 — 몸통 뒤에 깔리도록 zIndex를 낮춘다 */}
        <div style={{ position: "absolute", left: ATTACH.torsoHip[0] - ATTACH.hipTorso[0], top: ATTACH.torsoHip[1] - ATTACH.hipTorso[1], width: SIZE.hip[0], height: SIZE.hip[1], zIndex: -1 }}>
          <Img src={cabbage("hip")} style={{ width: SIZE.hip[0], height: SIZE.hip[1], display: "block" }} />
          <Leg side="L" hip={ATTACH.hipLegL} angle={legL} kneeAngle={kneeL} />
          <Leg side="R" hip={hipLegR} angle={legR} kneeAngle={kneeR} />
        </div>

        {/* 팔 */}
        <Arm side="L" shoulder={ATTACH.torsoShoulderL} angle={armL} elbowAngle={elbowL} />
        <Arm side="R" shoulder={torsoShoulderR} angle={armR} elbowAngle={elbowR} />
      </div>
    </div>
  );
};
