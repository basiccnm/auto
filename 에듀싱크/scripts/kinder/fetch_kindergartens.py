"""유치원알리미 basicInfo2로 유치원 기관정보 수집. sido_code+sgg_code 단위.

사용 예:
    python fetch_kindergartens.py 11 11320    # 서울 도봉구
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, kinder_get, now_iso, slugify, load_config


def to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def upsert_kindergarten(conn, row):
    conn.execute(
        """
        INSERT INTO kindergartens (
            kinder_code, office_edu, suboffice_edu, name, establish_type,
            address, phone, fax, homepage, operating_hours,
            class_count_age3, class_count_age4, class_count_age5,
            class_count_mixed, class_count_special,
            pupil_count_age3, pupil_count_age4, pupil_count_age5,
            pupil_count_mixed, pupil_count_special,
            director_name, lat, lng, disclosure_round, slug, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (kinder_code) DO UPDATE SET
            office_edu=excluded.office_edu, suboffice_edu=excluded.suboffice_edu,
            name=excluded.name, establish_type=excluded.establish_type,
            address=excluded.address, phone=excluded.phone, fax=excluded.fax,
            homepage=excluded.homepage, operating_hours=excluded.operating_hours,
            class_count_age3=excluded.class_count_age3, class_count_age4=excluded.class_count_age4,
            class_count_age5=excluded.class_count_age5, class_count_mixed=excluded.class_count_mixed,
            class_count_special=excluded.class_count_special,
            pupil_count_age3=excluded.pupil_count_age3, pupil_count_age4=excluded.pupil_count_age4,
            pupil_count_age5=excluded.pupil_count_age5, pupil_count_mixed=excluded.pupil_count_mixed,
            pupil_count_special=excluded.pupil_count_special,
            director_name=excluded.director_name, lat=excluded.lat, lng=excluded.lng,
            disclosure_round=excluded.disclosure_round, last_synced_at=excluded.last_synced_at
        """,
        (
            row["kindercode"],
            row["officeedu"],
            row.get("subofficeedu"),
            row["kindername"],
            row["establish"],
            row.get("addr"),
            row.get("telno"),
            row.get("faxno"),
            row.get("hpaddr"),
            row.get("opertime"),
            to_int(row.get("clcnt3")),
            to_int(row.get("clcnt4")),
            to_int(row.get("clcnt5")),
            to_int(row.get("mixclcnt")),
            to_int(row.get("shclcnt")),
            to_int(row.get("ppcnt3")),
            to_int(row.get("ppcnt4")),
            to_int(row.get("ppcnt5")),
            to_int(row.get("mixppcnt")),
            to_int(row.get("shppcnt")),
            row.get("ldgrname"),
            to_float(row.get("lttdcdnt")),
            to_float(row.get("lngtcdnt")),
            row["pbnttmng"],
            slugify(row["kindername"], row["kindercode"]),
            now_iso(),
        ),
    )


def main(sido_code, sgg_code):
    config = load_config()
    key = config["kindergarten_api_key"]
    conn = get_db()

    rows = kinder_get("basicInfo2", key, sido_code, sgg_code)
    for row in rows:
        upsert_kindergarten(conn, row)
    conn.commit()

    print(f"완료: {len(rows)}개 유치원 적재 (sido={sido_code}, sgg={sgg_code})")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python fetch_kindergartens.py <시도코드> <시군구코드>")
        print("예: python fetch_kindergartens.py 11 11320  (서울 도봉구)")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
