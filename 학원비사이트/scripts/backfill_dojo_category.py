import sqlite3
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from dojo_common import CATEGORY_SLUG, infer_sport_from_name

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, name FROM dojos WHERE sport_name IS NULL OR sport_name = ''"
    ).fetchall()

    fixed = 0
    for dojo_id, name in rows:
        inferred = infer_sport_from_name(name or "")
        if not inferred:
            continue
        category_slug = CATEGORY_SLUG.get(inferred, "gita")
        category_name = f"{inferred}장"
        conn.execute(
            "UPDATE dojos SET sport_name=?, category_name=?, category_slug=? WHERE id=?",
            (inferred, category_name, category_slug, dojo_id),
        )
        fixed += 1

    conn.commit()
    conn.close()
    print(f"blank sport rows: {len(rows)}, fixed by keyword match: {fixed}")


if __name__ == "__main__":
    main()
