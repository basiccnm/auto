#!/usr/bin/env node
/* 템플릿 문자열 «본문»에 들어간 /* * / 주석을 찾는다.
   백틱 안에서는 그게 주석이 아니라 **화면에 그대로 찍히는 글자**다.
   2026-08-10 폰 실측에서 설정 화면에 주석 한 문단이 통째로 노출됐다. */
import { readFileSync } from "node:fs";
const file = process.argv[2] || "app/www/app.js";
const src = readFileSync(file, "utf8");
let i = 0, line = 1;
const stack = [];            // "tpl" = 템플릿 본문 / "expr" = ${ } 안
const hits = [];
const inTpl = () => stack.length && stack[stack.length - 1] === "tpl";
while (i < src.length) {
  const c = src[i], n = src[i + 1];
  if (c === "\n") { line++; i++; continue; }
  if (inTpl()) {
    if (c === "\\") { i += 2; continue; }
    if (c === "`") { stack.pop(); i++; continue; }
    if (c === "$" && n === "{") { stack.push("expr"); i += 2; continue; }
    if (c === "/" && n === "*") { hits.push(`${line}: ${src.slice(i, i + 60).split("\n")[0]}`); i += 2; continue; }
    i++; continue;
  }
  // 템플릿 본문 밖 — 주석·문자열은 건너뛴다
  if (c === "/" && n === "*") { const e = src.indexOf("*/", i + 2); line += (src.slice(i, e < 0 ? src.length : e).match(/\n/g) || []).length; i = e < 0 ? src.length : e + 2; continue; }
  if (c === "/" && n === "/") { const e = src.indexOf("\n", i); i = e < 0 ? src.length : e; continue; }
  if (c === '"' || c === "'") { let j = i + 1; while (j < src.length && src[j] !== c) { if (src[j] === "\\") j++; j++; } i = j + 1; continue; }
  if (c === "`") { stack.push("tpl"); i++; continue; }
  if (c === "{" && stack.length) { stack.push("brace"); i++; continue; }
  if (c === "}" && stack.length) { stack.pop(); i++; continue; }
  i++;
}
if (hits.length) { console.log("❌ 템플릿 안 /* */ 주석 " + hits.length + "곳 — 화면에 그대로 찍힌다"); hits.forEach(h => console.log("   " + h)); process.exit(1); }
console.log("✅ 템플릿 안에 새는 주석 없음");
