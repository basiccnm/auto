// 올마 캐릭터 SVG — 2026-07-21 (움직이는 버전)
//
// 왜 SVG인가: ChatGPT·Flow로 표정을 뽑으면 매번 입이 비뚤어지고 한 장에 여러 개가 나온다.
//   4장 얻으려고 10장 넘게 뽑았다. 좌표를 쥐면 그런 일이 없다.
//
// 🔴 정적 이미지로 만들면 안 된다(2026-07-21 "너무 허접한데"). 부위마다 class를 달아
//   CSS로 **부드럽게 전환**시킨다. 팔이 스르륵 올라가고, 몸이 통통 뛰고, 고개가 갸웃한다.
//   포즈를 바꿔 끼우는 게 아니라 **같은 몸이 움직이는** 것이 핵심.

const OLMA = { head:"#F7EFA8", body:"#A9D3EF", line:"#000", lw:7 };

// 팔 각도 (어깨 기준 회전) — CSS transition이 사이를 메운다
const POSES = {
  기본:   { L:0,   R:0    },
  가리킴: { L:6,   R:-95  },
  으쓱:   { L:38,  R:-38  },
  만세:   { L:150, R:-150 },
  깜짝:   { L:60,  R:-60  },
};

function olmaSVG({ id = "olma", scale = 1 } = {}) {
  const C = OLMA;
  const arm = (side) => {
    const x = side === "L" ? 152 : 248, d = side === "L" ? -1 : 1;
    return `<g class="arm arm-${side}">
      <path d="M${x} 268 q${d*22} 55 ${d*14} 96" fill="none"
            stroke="${C.line}" stroke-width="${C.lw}" stroke-linecap="round"/>
      <ellipse cx="${x + d*15}" cy="374" rx="15" ry="19" fill="${C.body}"
               stroke="${C.line}" stroke-width="${C.lw}"/></g>`;
  };
  return `<svg id="${id}" class="olma" viewBox="0 0 400 560"
     width="${400*scale}" height="${560*scale}" xmlns="http://www.w3.org/2000/svg">
  <g class="whole">
    <g class="legs">
      <path d="M186 400 v100" stroke="${C.line}" stroke-width="${C.lw}" stroke-linecap="round"/>
      <path d="M214 400 v100" stroke="${C.line}" stroke-width="${C.lw}" stroke-linecap="round"/>
      <path d="M172 500 a20 14 0 0 1 28 0 z" fill="${C.body}" stroke="${C.line}" stroke-width="${C.lw}" stroke-linejoin="round"/>
      <path d="M200 500 a20 14 0 0 1 28 0 z" fill="${C.body}" stroke="${C.line}" stroke-width="${C.lw}" stroke-linejoin="round"/>
    </g>
    <rect class="torso" x="152" y="252" width="96" height="150" rx="26"
          fill="${C.body}" stroke="${C.line}" stroke-width="${C.lw}"/>
    <!-- 🔴 팔은 몸통 **뒤에** 그리면 들어올릴 때 몸에 가려 사라진다(2026-07-21 렌더에서 발견) -->
    ${arm("L")}${arm("R")}
    <g class="head">
      <circle cx="200" cy="163" r="98" fill="${C.head}" stroke="${C.line}" stroke-width="${C.lw}"/>
      <ellipse class="eye eye-L" cx="168" cy="150" rx="9" ry="9" fill="${C.line}"/>
      <ellipse class="eye eye-R" cx="232" cy="150" rx="9" ry="9" fill="${C.line}"/>
      <path class="mouth" d="M180 196 h40" fill="none"
            stroke="${C.line}" stroke-width="6" stroke-linecap="round"/>
    </g>
  </g></svg>`;
}

// 표정 — 입 path와 눈 크기를 갈아끼운다 (CSS가 부드럽게 이어줌)
const MOUTHS = {
  무표정: "M180 196 h40",
  놀람:   "M200 196 m-12 0 a12 12 0 1 0 24 0 a12 12 0 1 0 -24 0",
  갸웃:   "M182 196 q9 -7 18 0 t18 0",
  씩:     "M180 190 q20 18 40 0",
  헉:     "M200 200 m-22 0 a22 26 0 1 0 44 0 a22 26 0 1 0 -44 0",   // 입 쩍
  삐뚤:   "M176 198 q22 -14 44 4",
  일자:   "M186 196 h28",
};

// 포즈 추가 — 개그용
POSES["털썩"]   = { L:110, R:-110 };
POSES["뒷목"]   = { L:-140, R:-150 };
POSES["가리킴위"]= { L:6,  R:-100 };

function setFace(el, face) {
  const m = el.querySelector(".mouth");
  m.setAttribute("d", MOUTHS[face] || MOUTHS["무표정"]);
  const big = face === "놀람";
  el.querySelectorAll(".eye").forEach(e => e.setAttribute("rx", big ? 13 : 9));
  el.dataset.face = face;
}

function setPose(el, pose) {
  const p = POSES[pose] || POSES["기본"];
  el.querySelector(".arm-L").style.transform = `rotate(${p.L}deg)`;
  el.querySelector(".arm-R").style.transform = `rotate(${p.R}deg)`;
  el.dataset.pose = pose;
}

if (typeof module !== "undefined") module.exports = { olmaSVG, setFace, setPose, POSES, MOUTHS };
