# 스킬 라이브러리 — 설치 안내

검증 완료된 스킬만 모은 번들입니다 (2026-08-02 기준, 원본 GitHub 저장소에서 직접 클론).

## 폴더 구성

```
skills-library/
├── design/      ← 앱/웹 디자인 작업용
│   ├── frontend-design     (anthropics 공식) AI 티 나는 UI 방지, 미학 선확정
│   ├── canvas-design       (anthropics 공식) 포스터·카드·정적 이미지
│   ├── nothing-design      모노크롬·타이포 중심 Nothing 스타일 UI
│   ├── design-auditor      19개 규칙으로 디자인 점수화 감사
│   └── impeccable          디자인 품질 명령 23개 + 검출 규칙 44개
│                           (design-auditor와 역할 겹침 — 둘 다 넣어둠, 취향대로)
├── olmanama/    ← 얼마나마(olmanama.com)용
│   └── claude-seo/skills/  SEO 서브스킬 25개 (핵심: seo-programmatic,
│                           seo-schema, seo-geo, seo-audit, seo-technical)
└── shorts/      ← 쇼핑쇼츠 파이프라인용
    ├── remotion-*          (remotion-dev 공식) 렌더링 모범사례 11종
    │                       (핵심: remotion-best-practices, remotion-captions,
    │                        remotion-create, remotion-render)
    ├── video_toolkit       엔드투엔드 영상 파이프라인 참고 골격
    ├── watch (claude-video) 영상을 프레임+음성으로 분해해 Claude가 "보게" 함
    │                       → 클립 선별 단계 핵심 부품. FFmpeg·(음성은 Whisper) 필요
    ├── hook-generator      3초 후킹 문구 (PAS/AIDA/BAB/STAR/SLAY)
    ├── youtube-thumbnail   썸네일 프롬프트 생성
    └── reels-scripting     떡상 릴스 역설계 → 스크립트
```

## Claude Code에서 설치 (프로젝트별 격리)

스킬은 **프로젝트 폴더 안에 넣으면 그 프로젝트에서만** 뜹니다.

```
쇼츠 프로젝트 폴더\.claude\skills\   ← shorts/ 안의 폴더들 복사
얼마나마 프로젝트 폴더\.claude\skills\ ← olmanama/claude-seo/skills/ 안의 폴더들 복사
디자인 작업 폴더\.claude\skills\      ← design/ 안의 폴더들 복사
```

- 전역 설치(모든 프로젝트에서 사용)를 원하면: `C:\Users\hardb\.claude\skills\`
- 특정 스킬을 강제로 쓰게 하려면 대화에서 `/스킬이름` 으로 직접 호출

## GitHub 공용 창고로 쓰기 (코워크 + 코드탭 공용)

1. GitHub에 비공개 저장소 생성 (예: `my-skills`)
2. 이 폴더를 통째로 push
3. 코드탭: `git clone` 후 위 경로에 복사 (또는 프로젝트에서 직접 참조)
4. 코워크(웹 Claude): 세션에서 "내 my-skills 저장소 받아서 ○○ 스킬 적용해줘"

## 원본 저장소 (업데이트 받을 때)

- https://github.com/anthropics/skills (frontend-design, canvas-design)
- https://github.com/remotion-dev/skills (remotion 전체)
- https://github.com/digitalsamba/claude-code-video-toolkit (video_toolkit — 원본에 예제·템플릿 다수, 필요시 전체 클론)
- https://github.com/charlie947/social-media-skills (hook-generator 등)
- https://github.com/AgriciDaniel/claude-seo (스킬 25개 외에 서브에이전트 18개도 있음 — 필요시 원본의 install 스크립트 사용)
- https://github.com/dominikmartn/nothing-design-skill
- https://github.com/Ashutos1997/claude-design-auditor-skill

## design-extract (designlang) — 스킬이 아니라 CLI 도구

TOP 10 문서의 7위. GitHub 저장소(Manavarya09/design-extract)는 현재 접근 불가
(삭제 또는 비공개 전환된 듯)하지만, **npm 패키지 `designlang`은 살아있음** (v12.21.0 확인).
스킬처럼 복사하는 게 아니라 명령어로 쓰는 도구라 번들에는 미포함. 사용법:

```
npx designlang https://benchmark-site.com   # 사이트 디자인 시스템 추출
npx designlang grade <url>                  # 디자인 점수 리포트
```

## 주의

- reels-scripting은 Apify(유료)·Gemini API 키가 있어야 완전 동작. 키 없이는 프레임워크 부분만 참고용.
- hook-generator 등 charlie947 스킬은 영어 기반 → 한국어 산출물은 톤 보정 필요.
- claude-seo의 일부 서브스킬(seo-dataforseo 등)은 외부 유료 API 연동용 — 키 없으면 무시하면 됨.
