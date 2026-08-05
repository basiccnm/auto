import re

MOBILE_CSS_MARKER = "<!-- MOBILE_FONT_CSS_V1 -->"

H2_STYLE = "border-left: 5px solid #007bff; padding-left: 10px; margin-top: 40px; margin-bottom: 20px; font-size: 22px; color: #111;"
H3_STYLE = "margin-top: 30px; margin-bottom: 15px; font-size: 18px; color: #222;"
P_MARGIN = "margin-bottom: 20px;"
WRAP_OPEN = '<div style="font-size: 16px; line-height: 1.8; color: #333;">'
WRAP_CLOSE = "</div>"

EMPTY_HEADER_RE = re.compile(
    r'<h[34][^>]*>\s*(?:<b[^>]*>)?\s*(?:<br\s*/?>)?\s*(?:</b>)?\s*</h[34]>',
    re.IGNORECASE
)


def restyle_content(html):
    prefix = ""
    body = html
    if body.startswith(MOBILE_CSS_MARKER):
        idx = body.find("</style>")
        if idx != -1:
            idx_end = idx + len("</style>")
            prefix = body[:idx_end]
            body = body[idx_end:]

    body = EMPTY_HEADER_RE.sub("", body)

    body = re.sub(r'<h3[^>]*>', f'<h2 style="{H2_STYLE}">', body, flags=re.IGNORECASE)
    body = re.sub(r'</h3>', '</h2>', body, flags=re.IGNORECASE)

    body = re.sub(r'<h4[^>]*>', f'<h3 style="{H3_STYLE}">', body, flags=re.IGNORECASE)
    body = re.sub(r'</h4>', '</h3>', body, flags=re.IGNORECASE)

    def p_repl(m):
        tag = m.group(0)
        if "style=" in tag.lower():
            return tag
        return tag[:-1] + f' style="{P_MARGIN}">'

    body = re.sub(r'<p(?:\s+[^>]*)?>', p_repl, body, flags=re.IGNORECASE)

    return prefix + WRAP_OPEN + body + WRAP_CLOSE
