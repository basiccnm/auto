/* 앱 이름 한 번에 바꾸기 — 상표 확인이 끝나면 이 스크립트 하나로 끝낸다.
   이름을 바꿀 자리가 여섯 군데라 손으로 하면 반드시 한 곳을 빠뜨린다(그러면 스토어 심사에서 걸린다).

   쓰는 법:
     node scripts/rename-app.mjs "하교후"          ← 미리보기만(무엇이 바뀌는지 보여주고 끝)
     node scripts/rename-app.mjs "하교후" --write  ← 실제로 바꾼다

   ⚠ 바꾼 뒤 해야 할 것(이 스크립트가 못 하는 것):
     · npx cap sync android  →  gradlew assembleDebug  (앱 이름은 빌드해야 반영된다)
     · 앱 아이콘 교체(디자인 필요)
     · 워커 배포(공유 미리보기 문구가 워커에 있다)
     · 스토어 등록 정보 수정
   ⚠ 상표 확인이 먼저다 — 키프리스. 등록돼 있으면 다운로드 수와 무관하게 막힌다.
     지금까지 확인한 것은 docs/제안-보류.md 의 이름 표에 있다. */
import fs from "node:fs";

const NEW = process.argv[2];
const WRITE = process.argv.includes("--write");
if (!NEW) {
  console.error("이름을 넣어라:  node scripts/rename-app.mjs \"하교후\" [--write]");
  process.exit(1);
}

const OLD = "우리아이학교정보";
const OLD_SPACED = "우리아이 학교정보";      // 로그인 제목은 띄어쓰기가 있다

/* 어디를 바꾸나 — 파일마다 «무엇이 이름인지»가 다르다.
   앱 이름(설치 아이콘 밑)·브라우저 탭·화면 제목·공유 미리보기는 각각 다른 자리에 있다. */
const TARGETS = [
  { f: "app/capacitor.config.json", what: "앱 이름(설치 아이콘 밑 · 스토어)" },
  { f: "app/www/index.html",        what: "브라우저 탭 제목" },
  { f: "app/www/app.js",            what: "로그인 화면 제목" },
  { f: "workers/site-renderer/src/templates.js", what: "웹 <title> · og · 공유 미리보기" },
];

let total = 0;
for (const t of TARGETS) {
  if (!fs.existsSync(t.f)) { console.log(`  (없음) ${t.f}`); continue; }
  const src = fs.readFileSync(t.f, "utf8");
  const hits = (src.match(new RegExp(OLD, "g")) || []).length
             + (src.match(new RegExp(OLD_SPACED, "g")) || []).length;
  if (!hits) { console.log(`  (해당 없음) ${t.f}`); continue; }
  total += hits;
  console.log(`  ${String(hits).padStart(3)}곳  ${t.f}  — ${t.what}`);
  if (WRITE) {
    // 띄어쓴 것을 먼저 바꾼다 — 나중에 하면 이미 바뀐 앞부분과 안 맞는다
    fs.writeFileSync(t.f, src.split(OLD_SPACED).join(NEW).split(OLD).join(NEW), "utf8");
  }
}

console.log(`\n${OLD} → ${NEW} · 모두 ${total}곳`);
if (!WRITE) {
  console.log("미리보기만 했다. 실제로 바꾸려면 --write 를 붙여라.");
} else {
  console.log("바꿨다. 이제 해야 할 것:");
  console.log("  1) cd app && npx cap sync android && cd android && ./gradlew assembleDebug");
  console.log("  2) 워커 배포(공유 미리보기 문구) — 대표님 「배포해」 승인 필요");
  console.log("  3) 앱 아이콘 교체 · 스토어 등록 정보 수정");
  console.log("  4) index.html 의 ?v= 해시를 다시 뽑을 것(앱이 옛 파일을 물고 있으면 이름이 안 바뀐다)");
}
