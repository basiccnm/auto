// 글꼴 — 윈도우 기본 폰트(맑은 고딕)는 쇼츠에서 힘이 없다(2026-07-21 "글꼴이 마음에 안 들어").
//   BlackHanSans : 굵고 각져서 숫자·제목이 확 박힌다 (임팩트 담당)
//   Jua          : 둥글둥글해서 올마 그림체랑 결이 맞는다 (설명·배지 담당)
import { loadFont as loadBlack } from "@remotion/google-fonts/BlackHanSans";
import { loadFont as loadJua } from "@remotion/google-fonts/Jua";
import { loadFont as loadNoto } from "@remotion/google-fonts/NotoSansKR";

export const BLACK = loadBlack().fontFamily; // 제목·숫자
export const JUA = loadJua().fontFamily; // 배지·설명 (쇼츠용, 손글씨 결)

// 🔴 카드뉴스 본문용(2026-07-24) — Jua는 둥글어서 귀엽지만 긴 글이 잘 안 읽힌다.
//    카드뉴스는 **읽는 콘텐츠**라 가독성이 우선이다.
//    라이선스: Noto Sans KR · Black Han Sans · Jua 모두 SIL Open Font License —
//    상업 사용·영상 삽입 전부 무료. 별도 표기 의무 없음
export const NOTO = loadNoto().fontFamily;
