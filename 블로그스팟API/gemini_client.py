# -*- coding: utf-8 -*-
"""Gemini API 클라이언트 — 네이버용 페르소나 변환 담당.

Blogspot과 네이버에 같은 글을 올리면 검색엔진이 중복문서로 판정할 수 있어서,
네이버 발행본은 Gemini로 말투/문장 구조를 바꿔서 내용은 같되 문서로는 다르게 만든다.

- API 키: gemini_config.json (api_key, default_model)
- 페르소나: naver_persona.txt (없으면 기본 페르소나 자동 생성 — 파일 수정으로 말투 조절 가능)
- 무료 티어 특성상 429(쿼터)/503(혼잡)이 잦아서 모델 폴백 + 재시도를 내장한다.
"""

import os
import re
import json
import time
import requests

GEMINI_CONFIG_FILE = "gemini_config.json"
PERSONA_FILE = "naver_persona.txt"

# default_model 실패 시 순서대로 폴백 (2026-07 무료 티어 실측 기준)
FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]

DEFAULT_PERSONA = """당신은 네이버 블로그를 운영하는 친근한 건강 블로거입니다.

말투 규칙:
- 부드러운 '~해요'체를 기본으로 사용 (원문의 '~합니다'체를 바꿔주세요)
- 딱딱한 설명문 대신 이웃에게 이야기하듯 자연스럽게
- 가끔 공감 표현을 섞기 (예: "저도 그랬는데요", "다들 한 번쯤 고민해보셨을 거예요")
- 과장·확정적 효능 표현은 금지 (원문의 신중한 표현 수준 유지)
- 이모지는 원문에 있는 것만 유지, 새로 추가하지 않기
"""


def load_gemini_config():
    if not os.path.exists(GEMINI_CONFIG_FILE):
        raise FileNotFoundError(f"{GEMINI_CONFIG_FILE} 파일이 없습니다.")
    with open(GEMINI_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_persona():
    if not os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_PERSONA)
    with open(PERSONA_FILE, "r", encoding="utf-8") as f:
        return f.read()


def generate(prompt, log=print, max_retries=3):
    """Gemini에 프롬프트를 보내고 텍스트 응답을 받는다 (모델 폴백 + 재시도 내장)."""
    cfg = load_gemini_config()
    key = cfg["api_key"]
    models = [cfg.get("default_model", FALLBACK_MODELS[0])]
    models += [m for m in FALLBACK_MODELS if m not in models]

    last_error = None
    for model in models:
        for attempt in range(max_retries):
            try:
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=120,
                )
            except requests.RequestException as e:
                last_error = str(e)
                time.sleep(2 ** (attempt + 1))
                continue

            if res.status_code == 200:
                try:
                    return res.json()["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    last_error = f"{model}: 응답 구조 이상 {str(res.json())[:200]}"
                    break  # 같은 모델 재시도 무의미, 다음 모델로
            elif res.status_code == 503:  # 혼잡 — 잠시 후 같은 모델 재시도
                last_error = f"{model}: 503 혼잡"
                log(f"  {model} 혼잡, {2 ** (attempt + 1)}초 후 재시도")
                time.sleep(2 ** (attempt + 1))
            elif res.status_code == 429:  # 쿼터 소진 — 다음 모델로 즉시 폴백
                last_error = f"{model}: 429 쿼터 소진"
                log(f"  {model} 쿼터 소진, 다음 모델로 전환")
                break
            else:
                raise RuntimeError(f"Gemini 오류 ({res.status_code}): {res.text[:300]}")

    raise RuntimeError(f"모든 모델 실패. 마지막 오류: {last_error}")


IMAGE_MODEL = "gemini-2.5-flash-image"


def generate_image(prompt, out_path, log=print, max_retries=3):
    """Gemini 이미지 생성 (Nano Banana). 생성된 이미지를 out_path에 저장하고 경로를 반환한다."""
    import base64

    cfg = load_gemini_config()
    key = cfg["api_key"]

    last_error = None
    for attempt in range(max_retries):
        try:
            res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
                },
                timeout=180,
            )
        except requests.RequestException as e:
            last_error = str(e)
            time.sleep(2 ** (attempt + 1))
            continue

        if res.status_code == 200:
            parts = res.json()["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline:
                    img_bytes = base64.b64decode(inline["data"])
                    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    return out_path
            last_error = "응답에 이미지가 없음 (텍스트만 반환됨)"
            log(f"  {last_error}, 재시도 {attempt + 1}/{max_retries}")
        elif res.status_code in (429, 503):
            last_error = f"{res.status_code}"
            log(f"  이미지 생성 {res.status_code}, {2 ** (attempt + 1)}초 후 재시도")
            time.sleep(2 ** (attempt + 1))
        else:
            raise RuntimeError(f"이미지 생성 오류 ({res.status_code}): {res.text[:300]}")

    raise RuntimeError(f"이미지 생성 실패: {last_error}")


IMAGE_STYLE_SUFFIX = (
    "따뜻하고 부드러운 파스텔 톤의 플랫 일러스트, 텍스트나 글자 없이, "
    "깨끗한 단색 배경, 한국 건강 블로그용 이미지"
)


def build_image_prompts(topic, html_content=None, log=print):
    """글 내용을 분석해서 서로 다른 이미지 6개(썸네일 1 + 본문 보조 5)용 프롬프트를 만든다.

    본문이 주어지면 Gemini가 실제 소제목/섹션별로 각각 다른 장면을 뽑는다.
    (이미지 생성 API는 유료 전용이라, 프롬프트만 뽑아 사용자가 직접 생성하는 워크플로우)
    반환: [(파일명, 프롬프트), ...]
    """
    if html_content:
        try:
            return _build_image_prompts_from_content(topic, html_content, log=log)
        except Exception as e:
            log(f"  Gemini 프롬프트 생성 실패, 기본 템플릿 사용: {e}")

    # 폴백: 본문 없이 주제만으로 (섹션 정보가 없으므로 장면 다양화가 제한적)
    return [
        ("thumbnail", f"{topic} 주제의 블로그 대표 썸네일, 16:9 비율. {IMAGE_STYLE_SUFFIX}"),
        ("body_1", f"아침 식탁에서 영양제를 챙겨 먹는 사람의 일상. {IMAGE_STYLE_SUFFIX}"),
        ("body_2", f"{topic} 관련 영양소가 풍부한 자연 식품들의 구성. {IMAGE_STYLE_SUFFIX}"),
        ("body_3", f"활기차게 하루를 보내는 건강한 모습. {IMAGE_STYLE_SUFFIX}"),
        ("body_4", f"약국 선반에 진열된 다양한 영양제 병들. {IMAGE_STYLE_SUFFIX}"),
        ("body_5", f"돋보기로 성분표를 꼼꼼히 확인하는 손. {IMAGE_STYLE_SUFFIX}"),
    ]


def _build_image_prompts_from_content(title, html_content, log=print):
    """Gemini가 글 본문을 읽고 섹션별로 서로 다른 장면 프롬프트 6개를 뽑는다."""
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text).strip()[:3000]

    prompt = f"""아래 블로그 글을 읽고, 이 글에 넣을 삽화 6개의 이미지 생성 프롬프트를 만들어주세요.

규칙:
1. 첫 번째는 글 전체를 대표하는 썸네일 (16:9 비율 명시)
2. 나머지 5개는 글의 서로 다른 소제목/섹션 내용에 맞는 장면 — 반드시 6개가 전부 뚜렷하게 다른 장면이어야 함
   (예: 어떤 성분을 다루면 그 성분의 원료 식품, 그 고민을 겪는 사람의 구체적 상황 등)
3. 각 프롬프트는 구체적인 장면 묘사 1~2문장 (사물, 인물, 배경, 구도 포함)
4. 모든 프롬프트 끝에 다음 스타일 문구를 붙이기: "{IMAGE_STYLE_SUFFIX}"
5. 출력 형식: 한 줄에 하나씩, "번호|프롬프트" 형태로 정확히 6줄만 출력. 다른 텍스트 금지.

글 제목: {title}

글 내용:
{text}"""

    result = generate(prompt, log=log)
    lines = [l.strip() for l in result.strip().split("\n") if "|" in l]
    if len(lines) < 6:
        raise RuntimeError(f"프롬프트 6개를 못 뽑음 (파싱된 줄: {len(lines)})")

    names = ["thumbnail", "body_1", "body_2", "body_3", "body_4", "body_5"]
    specs = []
    for name, line in zip(names, lines[:6]):
        p = line.split("|", 1)[1].strip()
        if IMAGE_STYLE_SUFFIX not in p:
            p = f"{p} {IMAGE_STYLE_SUFFIX}"
        specs.append((name, p))
    return specs


def write_image_prompts_file(topic, out_dir, html_content=None, log=print):
    """이미지 프롬프트 6개를 out_dir/image_prompts.txt로 저장한다 (사용자 수동 생성용)."""
    specs = build_image_prompts(topic, html_content=html_content, log=log)
    lines = [
        f"[{topic}] 이미지 생성 프롬프트 (총 {len(specs)}개)",
        "",
        "사용법: 아래 프롬프트를 이미지 생성 도구(Google Flow, AI Studio 등)에 붙여넣어",
        "이미지를 만든 뒤, 이 폴더에 아래 파일명(png/jpg)으로 저장해주세요.",
        "(추후 관리자 화면에서 파일선택으로 바로 첨부할 수 있게 될 예정)",
        "",
    ]
    for name, prompt in specs:
        lines += [f"=== {name} ===", prompt, ""]
    path = os.path.join(out_dir, "image_prompts.txt")
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"  이미지 프롬프트 저장: {path}")
    return path


def generate_blog_images(topic, out_dir, html_content=None, log=print):
    """블로그 글용 이미지 6개를 Gemini API로 직접 생성한다.

    주의: 이미지 생성 모델은 무료 티어 한도가 0이라 결제 활성화된 키가 필요함
    (2026-07-09 확인). 결제 전에는 write_image_prompts_file()로 프롬프트만 뽑아서
    사용자가 직접 생성하는 방식을 쓴다.
    반환: 생성된 파일 경로 리스트 (실패한 것은 건너뜀)
    """
    results = []
    for name, prompt in build_image_prompts(topic, html_content=html_content, log=log):
        out_path = os.path.join(out_dir, f"{name}.png")
        try:
            log(f"  이미지 생성 중: {name}")
            generate_image(prompt, out_path, log=log)
            results.append(out_path)
        except Exception as e:
            log(f"  {name} 생성 실패: {e}")
    return results


def _strip_code_fence(text):
    """Gemini가 ```html ... ``` 로 감싸서 답하는 경우 벗겨낸다."""
    m = re.match(r"^\s*```(?:html)?\s*\n(.*?)\n\s*```\s*$", text, re.DOTALL)
    return m.group(1) if m else text.strip()


def write_bridge_post(title, facts_html, blogspot_url, log=print):
    """네이버용 브릿지 글을 독립적으로 새로 쓴다 (2026-07-09 확정 방식).

    Blogspot 글을 '변환'하는 게 아니라, 사실관계(성분/가격/효능 설명)만 가져와서
    주부 페르소나의 1인칭 이야기 글로 완전히 새로 작성한다.
    - 목차/비교표/번호 소제목 금지 (Blogspot 전용)
    - 쇼핑몰 링크 금지, 유일한 링크는 마지막 방구석 약국 연결 문구
    반환: (네이버용 제목, 본문 HTML)
    """
    persona = load_persona()

    facts_text = re.sub(r"<[^>]+>", " ", facts_html)
    facts_text = re.sub(r"\s+", " ", facts_text).strip()[:4000]

    prompt = f"""{persona}

아래 "참고 자료"의 사실관계(성분 이름, 효능 설명의 수준, 주의사항)만 활용해서,
네이버 블로그용 글을 처음부터 새로 써주세요. 참고 자료의 문장을 재사용하거나 구조를 따라하지 말고,
위 페르소나가 자기 이야기를 하듯 완전히 독립적인 글이어야 합니다.

절대 규칙:
1. 출력은 HTML: 문단은 <p>, 강조는 <strong>만 사용. 목차·표·번호 소제목 금지.
2. 분량: 문단 7~10개 (공백 제외 1000자 이상)
3. 도입은 개인적인 상황/고민에서 시작 (예: 가족 건강 걱정 에피소드)
4. 쇼핑몰/구매 링크 절대 금지. 특정 브랜드 제품명도 나열하지 않기 (성분 위주로).
5. 글 마지막 문단 다음에 정확히 이 한 줄을 넣기:
   <p>더 자세한 브랜드별 비교표와 최저가는 <a href="{blogspot_url}">[방구석 약국]</a> 링크에서 확인하세요.</p>
6. 첫 줄에 "TITLE: 제목" 형식으로 네이버 검색에 자연스러운 제목을 쓰고, 그 다음 줄부터 본문 HTML만 출력.
   제목도 개인 경험담 느낌으로 (예: "남편 영양제 알아보다가 정리해본 이야기")
7. 설명/인사말 등 다른 텍스트는 일절 출력 금지.

참고 자료 (사실관계 출처):
제목: {title}
내용: {facts_text}"""

    log(f"  네이버 브릿지 글 작성 중... (참고자료 {len(facts_text):,}자)")
    result = _strip_code_fence(generate(prompt, log=log))

    new_title = title
    body = result
    m = re.match(r"\s*TITLE:\s*(.+?)\s*\n(.*)", result, re.DOTALL)
    if m:
        new_title = m.group(1).strip()
        body = _strip_code_fence(m.group(2).strip())

    # 안전검증: 금지 요소 확인
    if re.search(r'link\.coupang\.com|iherb\.com', body, re.IGNORECASE):
        raise RuntimeError("브릿지 글에 쇼핑몰 링크가 포함됨 — 재생성 필요")
    if blogspot_url not in body:
        body += f'\n<p>더 자세한 브랜드별 비교표와 최저가는 <a href="{blogspot_url}">[방구석 약국]</a> 링크에서 확인하세요.</p>'

    return new_title, body


def rewrite_for_naver(title, html_content, log=print):
    """제목과 본문 HTML을 네이버용 페르소나로 다시 쓴다.

    반환: (새 제목, 새 본문 HTML)
    """
    persona = load_persona()

    prompt = f"""{persona}

아래 블로그 글을 위 페르소나의 말투로 다시 써주세요.

절대 규칙:
1. HTML 태그 구조(h2, p, strong, ul, li, br, img, a)는 그대로 유지하고, 태그 안의 텍스트만 바꾸세요.
2. <img> 태그는 속성 하나도 바꾸지 말고 그대로 두세요.
3. 정보(성분명, 수치, 효능 설명의 사실관계)는 절대 바꾸지 마세요. 표현만 바꾸는 겁니다.
4. 문장 순서를 자연스럽게 재배열하는 것은 좋지만, 내용 추가/삭제는 하지 마세요.
5. 원문과 문장이 그대로 겹치지 않게, 모든 문장을 새로 표현해주세요 (검색엔진 중복문서 방지 목적).
6. 첫 줄에 새 제목을 "TITLE: 제목" 형식으로 쓰고, 그 다음 줄부터 본문 HTML만 출력하세요.
   제목도 원문과 다르게, 네이버 검색에 잘 걸리는 자연스러운 제목으로 바꿔주세요.
7. 설명이나 인사말 등 다른 텍스트는 일절 출력하지 마세요.

원문 제목: {title}

원문 본문:
{html_content}"""

    log(f"  Gemini 변환 요청 중... (본문 {len(html_content):,}자)")
    result = generate(prompt, log=log)
    result = _strip_code_fence(result)

    new_title = title
    body = result
    m = re.match(r"\s*TITLE:\s*(.+?)\s*\n(.*)", result, re.DOTALL)
    if m:
        new_title = m.group(1).strip()
        body = m.group(2).strip()
    body = _strip_code_fence(body)

    # 안전검증: 이미지 태그가 사라지거나 변형되지 않았는지
    orig_imgs = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
    new_imgs = re.findall(r'<img[^>]+src="([^"]+)"', body)
    if orig_imgs != new_imgs:
        log("  경고: 변환 과정에서 이미지 태그가 달라져 원본 이미지로 복구합니다.")
        # 이미지가 유실된 경우: 본문 맨 앞에 원본 이미지들을 되살린다
        missing = [u for u in orig_imgs if u not in new_imgs]
        for url in reversed(missing):
            body = f'<img src="{url}">\n\n' + body

    return new_title, body
