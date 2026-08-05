# -*- coding: utf-8 -*-
"""네이버 블로그 반자동 발행용 변환 모듈.

네이버는 2020년 5월에 블로그 글쓰기 API를 종료했기 때문에 완전 자동 발행은 불가능하다.
대신 이 모듈이 Blogspot 글을 네이버 스마트에디터에 붙여넣기 좋은 형태로 변환해주고,
사용자는 (1) 변환된 HTML을 브라우저로 열어 전체복사 → (2) 스마트에디터에 붙여넣기 →
(3) meta.txt의 제목/태그 붙여넣기 → (4) 발행 버튼만 누르면 된다.

글 하나당 naver_export/<슬러그>/ 폴더가 생성된다:
    naver.html  — 붙여넣기용 정리된 본문 (브라우저로 열어서 Ctrl+A, Ctrl+C)
    meta.txt    — 제목, 태그(#형식), 원본 URL
    images/     — 본문 이미지 사본 (붙여넣기로 이미지가 안 따라올 경우 드래그로 삽입)
"""

import os
import re
import ctypes
import requests
from ctypes import wintypes

NAVER_EXPORT_FOLDER = "naver_export"

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_STYLE_ATTR_RE = re.compile(r'\s+style="[^"]*"', re.IGNORECASE)
_DIV_TAG_RE = re.compile(r"</?div[^>]*>", re.IGNORECASE)
_SPAN_TAG_RE = re.compile(r"</?span[^>]*>", re.IGNORECASE)
_IMG_SRC_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)
_EMPTY_P_RE = re.compile(r"<p[^>]*>\s*(?:&nbsp;)?\s*</p>", re.IGNORECASE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def _slug_from_url(url):
    return os.path.splitext(url.rstrip("/").split("/")[-1])[0]


def copy_html_to_clipboard(fragment_html):
    """HTML을 서식 포함(CF_HTML) 형태로 윈도우 클립보드에 넣는다.

    네이버 스마트에디터에 Ctrl+V 하면 제목/문단/이미지가 서식 그대로 붙는다.
    주의: PowerShell의 Set-Clipboard -AsHtml은 CF_HTML 바이트 오프셋을 UTF-8로
    계산하지 않아 한글이 깨진다 (2026-07-09 실측). 그래서 규격을 직접 만든다.
    """
    pre = "<html><body><!--StartFragment-->"
    post = "<!--EndFragment--></body></html>"
    header_tpl = ("Version:0.9\r\nStartHTML:{:010d}\r\nEndHTML:{:010d}\r\n"
                  "StartFragment:{:010d}\r\nEndFragment:{:010d}\r\n")

    header_len = len(header_tpl.format(0, 0, 0, 0).encode("utf-8"))
    pre_len = len(pre.encode("utf-8"))
    frag_len = len(fragment_html.encode("utf-8"))
    post_len = len(post.encode("utf-8"))

    start_html = header_len
    start_frag = header_len + pre_len
    end_frag = start_frag + frag_len
    end_html = end_frag + post_len

    payload = (header_tpl.format(start_html, end_html, start_frag, end_frag)
               + pre + fragment_html + post).encode("utf-8") + b"\x00"

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE

    cf_html = user32.RegisterClipboardFormatW("HTML Format")
    GMEM_MOVEABLE = 0x0002
    if not user32.OpenClipboard(0):
        raise RuntimeError("클립보드를 열 수 없습니다 (다른 프로그램이 사용 중)")
    try:
        user32.EmptyClipboard()
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
        ptr = kernel32.GlobalLock(h)
        ctypes.memmove(ptr, payload, len(payload))
        kernel32.GlobalUnlock(h)
        if not user32.SetClipboardData(cf_html, h):
            raise RuntimeError("클립보드 데이터 설정 실패")
    finally:
        user32.CloseClipboard()


def convert_content_for_naver(content):
    """Blogspot 본문 HTML을 네이버 붙여넣기용으로 정리한다.

    - HTML 주석 제거 (숨겨둔 쿠팡 카드/링크/고지문구도 주석이므로 함께 사라짐 —
      네이버는 외부 상업 링크에 더 민감하므로 의도된 동작)
    - <style> 블록, style 속성, div/span 래퍼 제거 (스마트에디터가 자체 서식 적용)
    - h2 -> h3 재매핑 (스마트에디터 소제목 스타일과 매칭이 더 좋음)
    - 제목/문단/목록/굵게/이미지는 유지
    """
    html = content
    html = _COMMENT_RE.sub("", html)
    html = _STYLE_BLOCK_RE.sub("", html)
    html = _DIV_TAG_RE.sub("", html)
    html = _SPAN_TAG_RE.sub("", html)
    html = _STYLE_ATTR_RE.sub("", html)
    html = re.sub(r"<(/?)h2(\s[^>]*)?>", r"<\1h3>", html, flags=re.IGNORECASE)
    html = _EMPTY_P_RE.sub("", html)
    html = _MULTI_BLANK_RE.sub("\n\n", html)
    return html.strip()


def extract_image_urls(content):
    return _IMG_SRC_RE.findall(content)


def text_to_naver_html(text):
    """일반 텍스트(재미나이 웹에서 통으로 받은 완성글)를 네이버 붙여넣기용 HTML로 바꾼다.

    - 빈 줄 기준으로 문단을 나누고, 문단 사이에 빈 줄(<p><br></p>)을 넣어 가독성 확보
    - SEO 서식 마커 변환 (방침 1-6): "[소제목] 텍스트" -> <h3>, "[인용구] 텍스트" -> <blockquote>
      (에디터에 HTML로 붙여넣으면 네이버 소제목/인용구 스타일로 매핑됨)
    - 이미 HTML(<p 태그 포함)이면 문단 사이 간격만 보강
    """
    if "<p" in text:  # 이미 HTML인 경우: 문단 사이 간격만 추가
        return add_paragraph_spacing(text)

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    html_parts = []
    for para in paragraphs:
        m = re.match(r"^\[\s*소제목\s*\]\s*(.+)$", para, re.DOTALL)
        if m:
            html_parts.append("<h3>" + m.group(1).strip().replace("\n", " ") + "</h3>")
            continue
        m = re.match(r"^\[\s*인용구?\s*\]\s*(.+)$", para, re.DOTALL)
        if m:
            html_parts.append("<blockquote>" + m.group(1).strip().replace("\n", "<br>") + "</blockquote>")
            continue
        # 문단 중간에 마커가 섞인 경우도 처리 (줄 단위)
        if re.search(r"^\[\s*(소제목|인용구?)\s*\]", para, re.MULTILINE):
            lines_out = []
            for line in para.split("\n"):
                lm = re.match(r"^\[\s*소제목\s*\]\s*(.+)$", line.strip())
                if lm:
                    lines_out.append("<h3>" + lm.group(1).strip() + "</h3>")
                    continue
                lm = re.match(r"^\[\s*인용구?\s*\]\s*(.+)$", line.strip())
                if lm:
                    lines_out.append("<blockquote>" + lm.group(1).strip() + "</blockquote>")
                    continue
                if line.strip():
                    lines_out.append("<p>" + line.strip() + "</p>")
            html_parts.append("\n".join(lines_out))
            continue
        # 일반 문단: 내부 단일 줄바꿈은 <br>로
        html_parts.append("<p>" + para.replace("\n", "<br>") + "</p>")
    return "\n<p><br></p>\n".join(html_parts)


def add_paragraph_spacing(html):
    """연속된 문단(<p>...</p><p>...) 사이에 빈 줄을 넣어 네이버에서 보기 편하게 만든다."""
    if "<p><br></p>" in html:  # 이미 간격 있음 (재실행 안전)
        return html
    return re.sub(r"</p>\s*<p", "</p>\n<p><br></p>\n<p", html)


def insert_images_into_body(body_html, image_urls):
    """이미지 URL들을 본문에 고르게 배치한다 (첫 번째=썸네일은 맨 위, 나머지는 문단 사이).

    이미지는 GitHub 등 외부 URL이어야 하며, 네이버 에디터에 붙여넣으면
    네이버 서버로 자동 업로드된다 (2026-07-09 실측 검증된 방식).
    """
    if not image_urls:
        return body_html

    def img_tag(url):
        return f'<p><img src="{url}" style="max-width:100%;"></p>'

    result = body_html
    thumbnail, rest = image_urls[0], list(image_urls[1:])

    # 본문 이미지(body_1~5): 문단 블록 사이에 고르게 분산
    if rest:
        # 빈 줄 간격(<p><br></p>) 기준으로 문단 블록을 나눈다
        blocks = re.split(r"\n?<p><br></p>\n?", result)
        if len(blocks) >= 2:
            step = max(1, len(blocks) // (len(rest) + 1))
            out, img_i = [], 0
            for i, block in enumerate(blocks):
                out.append(block)
                if img_i < len(rest) and (i + 1) % step == 0 and i < len(blocks) - 1:
                    out.append(img_tag(rest[img_i]))
                    img_i += 1
            # 못 넣은 이미지는 마지막 블록 앞에
            while img_i < len(rest):
                out.insert(-1, img_tag(rest[img_i]))
                img_i += 1
            result = "\n<p><br></p>\n".join(out)
        else:
            result = result + "\n<p><br></p>\n" + "\n<p><br></p>\n".join(img_tag(u) for u in rest)

    # 썸네일은 본문 맨 위에
    result = img_tag(thumbnail) + "\n<p><br></p>\n" + result
    return result


def export_post_for_naver(post, output_root=NAVER_EXPORT_FOLDER, download_images=True, log=print):
    """Blogger 글 dict(title/content/labels/url)를 네이버 발행 준비 폴더로 내보낸다.

    반환값: 생성된 폴더 경로
    """
    slug = _slug_from_url(post.get("url", "")) or "post"
    out_dir = os.path.join(output_root, slug)
    os.makedirs(out_dir, exist_ok=True)

    cleaned = convert_content_for_naver(post["content"])

    # 브라우저로 열었을 때 복사하기 좋게 최소한의 보기용 스타일만 감싼다
    # (이 스타일은 문서 레벨이라 복사-붙여넣기에는 섞여 들어가지 않음)
    page = (
        "<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{post['title']}</title>\n"
        "<style>body{max-width:800px;margin:40px auto;font-family:'Malgun Gothic',sans-serif;"
        "line-height:1.8;padding:0 20px;} img{max-width:100%;}</style>\n"
        "</head>\n<body>\n"
        f"{cleaned}\n"
        "</body>\n</html>\n"
    )
    html_path = os.path.join(out_dir, "naver.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(page)

    labels = post.get("labels", [])
    tags = " ".join("#" + l.replace(" ", "") for l in labels)
    meta = (
        f"제목: {post['title']}\n"
        f"태그: {tags}\n"
        f"원본: {post.get('url', '')}\n"
        "\n"
        "발행 순서:\n"
        "1. naver.html을 브라우저로 열고 Ctrl+A, Ctrl+C\n"
        "2. 네이버 스마트에디터 본문에 Ctrl+V\n"
        "3. 위의 제목/태그를 복사해서 입력\n"
        "4. 이미지가 안 따라왔으면 images/ 폴더에서 드래그로 삽입\n"
        "5. 발행\n"
    )
    with open(os.path.join(out_dir, "meta.txt"), "w", encoding="utf-8") as f:
        f.write(meta)

    if download_images:
        img_urls = extract_image_urls(cleaned)
        if img_urls:
            img_dir = os.path.join(out_dir, "images")
            os.makedirs(img_dir, exist_ok=True)
            for i, url in enumerate(img_urls, 1):
                try:
                    res = requests.get(url, timeout=20)
                    if res.status_code != 200 or not res.content:
                        raise RuntimeError(f"HTTP {res.status_code}")
                    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
                    with open(os.path.join(img_dir, f"{i:02d}{ext}"), "wb") as f:
                        f.write(res.content)
                except Exception as e:
                    log(f"  이미지 다운로드 실패 ({url}): {e}")

    return out_dir
