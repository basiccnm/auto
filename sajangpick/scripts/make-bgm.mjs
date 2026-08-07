// BGM 합성기 — public/bgm.wav 를 만든다. (회신04 §B.3)
//
// 왜 직접 만드나: 저작권 프리 음원을 "다운로드"하는 순간 출처·라이선스 검증 문제가 생긴다.
// 우리가 수학으로 만든 소리는 원천적으로 우리 것이다.
// 더 좋은 CC0 트랙이 생기면 public/bgm.wav 만 갈아끼우면 된다 (코드는 그대로).
//
// 소리: C → Am → F → G 4코드 패드, 코드당 4초, 총 16초 루프.
// 사인파 3화음 + 옥타브 아래 루트 + 느린 볼륨 물결. 부드럽고 존재감 낮은 배경음.
//
// 실행: node scripts/make-bgm.mjs

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'public', 'bgm.wav');

const SR = 44100;
const CHORD_SEC = 4;
const CHORDS = [
  [261.63, 329.63, 392.0], // C
  [220.0, 261.63, 329.63], // Am
  [174.61, 220.0, 261.63], // F
  [196.0, 246.94, 293.66], // G
];

const totalSamples = SR * CHORD_SEC * CHORDS.length;
const data = new Float64Array(totalSamples);

CHORDS.forEach((freqs, ci) => {
  const start = ci * CHORD_SEC * SR;
  const n = CHORD_SEC * SR;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    // 코드 경계에서 뚝 끊기지 않게 앞뒤로 부드러운 봉투를 씌운다
    const env = Math.min(t / 0.25, 1) * Math.min((CHORD_SEC - t) / 0.35, 1);
    // 아주 느린 볼륨 물결 (호흡감)
    const breathe = 0.85 + 0.15 * Math.sin(2 * Math.PI * 0.2 * (start / SR + t));
    let s = 0;
    for (const f of freqs) {
      s += 0.22 * Math.sin(2 * Math.PI * f * t);
      s += 0.05 * Math.sin(2 * Math.PI * f * 2 * t); // 옅은 배음
    }
    s += 0.14 * Math.sin(2 * Math.PI * (freqs[0] / 2) * t); // 옥타브 아래 루트
    data[start + i] = s * env * breathe;
  }
});

// 정규화 후 16bit PCM 스테레오 WAV로
let peak = 0;
for (const v of data) peak = Math.max(peak, Math.abs(v));
const gain = 0.85 / peak;

const bytesPerSample = 2;
const channels = 2;
const dataSize = totalSamples * bytesPerSample * channels;
const buf = Buffer.alloc(44 + dataSize);

buf.write('RIFF', 0);
buf.writeUInt32LE(36 + dataSize, 4);
buf.write('WAVE', 8);
buf.write('fmt ', 12);
buf.writeUInt32LE(16, 16);
buf.writeUInt16LE(1, 20); // PCM
buf.writeUInt16LE(channels, 22);
buf.writeUInt32LE(SR, 24);
buf.writeUInt32LE(SR * channels * bytesPerSample, 28);
buf.writeUInt16LE(channels * bytesPerSample, 32);
buf.writeUInt16LE(16, 34);
buf.write('data', 36);
buf.writeUInt32LE(dataSize, 40);

for (let i = 0; i < totalSamples; i++) {
  const v = Math.max(-1, Math.min(1, data[i] * gain));
  const int16 = Math.round(v * 32767);
  buf.writeInt16LE(int16, 44 + i * 4);     // L
  buf.writeInt16LE(int16, 44 + i * 4 + 2); // R
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, buf);
console.log(`bgm.wav 생성: ${(buf.length / 1024 / 1024).toFixed(1)}MB, ${CHORD_SEC * CHORDS.length}초 루프`);
