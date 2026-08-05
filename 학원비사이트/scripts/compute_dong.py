import re
import sqlite3

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"

PAREN_RE = re.compile(r"\(([^)]*)\)")
DONG_KOREAN_RE = re.compile(r"([가-힣]+동)(?!\d)")  # 순수 한글 + '동', 뒤에 숫자 안 이어짐 (예: 방학동 O, 502동 X)


def extract_dong_from_parens(text):
    """마지막 괄호 그룹 안에서 순수 한글 동명을 찾는다 (건물동수 오인식 방지)."""
    if not text:
        return None
    groups = PAREN_RE.findall(text)
    if not groups:
        return None
    last = groups[-1]
    m = DONG_KOREAN_RE.search(last)
    return m.group(1) if m else None


def extract_dong_from_plain_address(text):
    """'시도 시군구 동명 번지' 형태(괄호 없는 지번주소)에서 3번째 토큰만 검사."""
    if not text:
        return None
    parts = text.split()
    if len(parts) < 3:
        return None
    candidate = parts[2]
    if DONG_KOREAN_RE.fullmatch(candidate):
        return candidate
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    for stmt in ["ALTER TABLE academies ADD COLUMN dong TEXT", "ALTER TABLE dojos ADD COLUMN dong TEXT"]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass

    # 기존 값 전부 재계산 (오탐 제거 위해 NULL 여부 상관없이 재실행)
    a_rows = conn.execute("SELECT id, address_detail, address_road FROM academies").fetchall()
    a_fixed = 0
    a_cleared = 0
    for id_, detail, road in a_rows:
        dong = extract_dong_from_parens(detail) or extract_dong_from_parens(road)
        conn.execute("UPDATE academies SET dong = ? WHERE id = ?", (dong, id_))
        if dong:
            a_fixed += 1
        else:
            a_cleared += 1
    conn.commit()

    d_rows = conn.execute("SELECT id, address_road, address_lot FROM dojos").fetchall()
    d_fixed = 0
    d_cleared = 0
    for id_, road, lot in d_rows:
        dong = extract_dong_from_parens(road) or extract_dong_from_plain_address(lot)
        conn.execute("UPDATE dojos SET dong = ? WHERE id = ?", (dong, id_))
        if dong:
            d_fixed += 1
        else:
            d_cleared += 1
    conn.commit()

    print(f"academies: dong 있음 {a_fixed} / 없음 {a_cleared} (총 {len(a_rows)})")
    print(f"dojos: dong 있음 {d_fixed} / 없음 {d_cleared} (총 {len(d_rows)})")

    bad_a = conn.execute("SELECT COUNT(*) FROM academies WHERE dong GLOB '*[0-9]*'").fetchone()[0]
    bad_d = conn.execute("SELECT COUNT(*) FROM dojos WHERE dong GLOB '*[0-9]*'").fetchone()[0]
    print(f"검증: 숫자 포함 dong 잔존 - academies={bad_a}, dojos={bad_d} (0이어야 정상)")


if __name__ == "__main__":
    main()
