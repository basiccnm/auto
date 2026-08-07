/* 별이 아이콘 → 안드로이드 mipmap 전 세트 + 스토어 512.
   크롬 headless 로 SVG를 각 크기 PNG로 굽는다(투명 배경은 --default-background-color=00000000). */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const DIR = process.cwd();
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const RES = "C:\\Users\\hardb\\Desktop\\블로그수입관련\\에듀싱크\\app\\android\\app\\src\\main\\res";

const ART = `
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#4A7BD4"/><stop offset="1" stop-color="#1B3F7E"/>
    </linearGradient>
    <radialGradient id="star" cx="0.35" cy="0.28" r="1">
      <stop offset="0" stop-color="#FFE58A"/><stop offset="0.55" stop-color="#FFC531"/><stop offset="1" stop-color="#E89B00"/>
    </radialGradient>
  </defs>
  <rect width="512" height="512" fill="url(#bg)"/>
  <circle cx="120" cy="100" r="7" fill="rgba(255,255,255,.7)"/>
  <circle cx="420" cy="150" r="5" fill="rgba(255,255,255,.55)"/>
  <circle cx="380" cy="80" r="9" fill="rgba(255,255,255,.4)"/>
  <circle cx="90" cy="330" r="5" fill="rgba(255,255,255,.4)"/>
  <circle cx="430" cy="380" r="6" fill="rgba(255,255,255,.35)"/>
  <g id="starface">
    <path d="M256 78 l52 106 117 17 -85 83 20 117 -104 -55 -104 55 20 -117 -85 -83 117 -17 z" fill="url(#star)"/>
    <path d="M256 100 l44 90 99 14 -20 20 c-60 -34 -150 -40 -196 -10 l-25 -24 98 -14 z" fill="rgba(255,255,255,.35)"/>
    <circle cx="222" cy="252" r="15" fill="#3A2A00"/>
    <circle cx="290" cy="252" r="15" fill="#3A2A00"/>
    <circle cx="227" cy="246" r="5" fill="#FFF"/>
    <circle cx="295" cy="246" r="5" fill="#FFF"/>
    <path d="M226 296 q30 26 60 0" fill="none" stroke="#3A2A00" stroke-width="12" stroke-linecap="round"/>
    <circle cx="196" cy="284" r="12" fill="rgba(255,120,90,.45)"/>
    <circle cx="316" cy="284" r="12" fill="rgba(255,120,90,.45)"/>
  </g>`;

// 전경(어댑티브) — 배경 없이 별만, 안전영역(가운데 66%)에 맞춰 축소
const FG = `
  <defs>
    <radialGradient id="star" cx="0.35" cy="0.28" r="1">
      <stop offset="0" stop-color="#FFE58A"/><stop offset="0.55" stop-color="#FFC531"/><stop offset="1" stop-color="#E89B00"/>
    </radialGradient>
  </defs>
  <g transform="translate(256 256) scale(0.62) translate(-256 -239.5)">
    <path d="M256 78 l52 106 117 17 -85 83 20 117 -104 -55 -104 55 20 -117 -85 -83 117 -17 z" fill="url(#star)"/>
    <path d="M256 100 l44 90 99 14 -20 20 c-60 -34 -150 -40 -196 -10 l-25 -24 98 -14 z" fill="rgba(255,255,255,.35)"/>
    <circle cx="222" cy="252" r="15" fill="#3A2A00"/>
    <circle cx="290" cy="252" r="15" fill="#3A2A00"/>
    <circle cx="227" cy="246" r="5" fill="#FFF"/>
    <circle cx="295" cy="246" r="5" fill="#FFF"/>
    <path d="M226 296 q30 26 60 0" fill="none" stroke="#3A2A00" stroke-width="12" stroke-linecap="round"/>
    <circle cx="196" cy="284" r="12" fill="rgba(255,120,90,.45)"/>
    <circle cx="316" cy="284" r="12" fill="rgba(255,120,90,.45)"/>
  </g>`;

const page = (inner, clip) => `<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden}svg{display:block}</style>
<svg viewBox="0 0 512 512" width="512" height="512" xmlns="http://www.w3.org/2000/svg">${clip ? `<clipPath id="m">${clip}</clipPath><g clip-path="url(#m)">${inner}</g>` : inner}</svg>`;

fs.writeFileSync("ic-square.html", page(ART, null), "utf8");                                    // 스토어 512(불투명)
fs.writeFileSync("ic-legacy.html", page(ART, `<rect width="512" height="512" rx="96"/>`), "utf8");   // 구형 런처(둥근 사각)
fs.writeFileSync("ic-round.html", page(ART, `<circle cx="256" cy="256" r="256"/>`), "utf8");    // 원형
fs.writeFileSync("ic-fg.html", page(FG, null), "utf8");                                         // 어댑티브 전경(투명)

const shoot = (html, out, size) => {
  execFileSync(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--hide-scrollbars", "--force-device-scale-factor=1",
    "--default-background-color=00000000",
    `--window-size=${size},${size}`, `--screenshot=${path.join(DIR, out)}`, path.join(DIR, html)], { stdio: "ignore" });
};

const DENS = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
const FGD = { mdpi: 108, hdpi: 162, xhdpi: 216, xxhdpi: 324, xxxhdpi: 432 };

shoot("ic-square.html", "store-512.png", 512);
shoot("ic-legacy.html", "base-legacy.png", 512);
shoot("ic-round.html", "base-round.png", 512);
shoot("ic-fg.html", "base-fg.png", 512);
const shrink = (src, out, size) => {
  fs.writeFileSync("_shrink.html", `<!doctype html><style>html,body{margin:0;background:transparent}img{display:block;width:${size}px;height:${size}px}</style><img src="${src}">`, "utf8");
  execFileSync(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
    "--default-background-color=00000000",
    `--window-size=${size},${size}`, `--screenshot=${path.join(DIR, out)}`, path.join(DIR, "_shrink.html")], { stdio: "ignore" });
};
for (const [d, s] of Object.entries(DENS)) {
  shrink("base-legacy.png", `ic_launcher-${d}.png`, s);
  shrink("base-round.png", `ic_launcher_round-${d}.png`, s);
}
for (const [d, s] of Object.entries(FGD)) shrink("base-fg.png", `ic_fg-${d}.png`, s);

// res 에 배치
for (const d of Object.keys(DENS)) {
  fs.copyFileSync(`ic_launcher-${d}.png`, path.join(RES, `mipmap-${d}`, "ic_launcher.png"));
  fs.copyFileSync(`ic_launcher_round-${d}.png`, path.join(RES, `mipmap-${d}`, "ic_launcher_round.png"));
  fs.copyFileSync(`ic_fg-${d}.png`, path.join(RES, `mipmap-${d}`, "ic_launcher_foreground.png"));
}
console.log("mipmap 5벌 + store-512.png 완료");
