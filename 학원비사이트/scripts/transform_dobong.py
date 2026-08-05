import json
import io
import hashlib
import re
import sys

SRC = r"C:\Users\hardb\AppData\Local\Temp\claude\C--Users-hardb-Desktop--------------API\3fa96bba-ba14-4a1d-85fd-c83aa1dc5dc9\scratchpad\neis\dobong_1.json"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\src\_data\academies.json"

OFFICE_TO_SIDO = {
    "서울특별시교육청": "서울",
    "경기도교육청": "경기",
}

REALM_TO_CATEGORY = {
    "입시.검정 및 보습": ("보습학원", "bosup"),
    "예능(대)": ("예능학원", "yeeneung"),
    "국제화": ("어학원", "eohak"),
    "기타(대)": ("기타학원", "gita"),
    "직업기술": ("직업기술학원", "jikeop"),
    "독서실": ("독서실", "doksuil"),
    "종합(대)": ("종합학원", "jonghap"),
    "기예(대)": ("기예학원", "giye"),
    "인문사회(대)": ("인문사회학원", "inmun"),
}


def slugify_name(name: str) -> str:
    s = name.strip()
    s = re.sub(r"[^\w가-힣]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def parse_fee(raw: str):
    if not raw or not raw.strip():
        return None
    items = []
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        course, price = part.rsplit(":", 1)
        price = price.strip()
        if not price.isdigit():
            continue
        items.append({"course": course.strip(), "price": int(price)})
    return items or None


def content_hash(row: dict) -> str:
    keys = [
        "ACA_NM", "REG_STTUS_NM", "PSNBY_THCC_CNTNT", "FA_RDNMA", "FA_RDNDA",
        "FA_TELNO", "TOFOR_SMTOT", "DTM_RCPTN_ABLTY_NMPR_SMTOT",
    ]
    blob = "|".join(str(row.get(k, "")) for k in keys)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def main():
    with io.open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    rows = data["acaInsTiInfo"][1]["row"]

    out = []
    for r in rows:
        aca_asnum = r.get("ACA_ASNUM")
        name = (r.get("ACA_NM") or "").strip()
        sido = OFFICE_TO_SIDO.get(r.get("ATPT_OFCDC_SC_NM"), r.get("ATPT_OFCDC_SC_NM"))
        sigungu = r.get("ADMST_ZONE_NM")
        realm = r.get("REALM_SC_NM")
        category_name, category_slug = REALM_TO_CATEGORY.get(realm, ("기타학원", "gita"))
        fee_raw = r.get("PSNBY_THCC_CNTNT")
        fee_parsed = parse_fee(fee_raw)
        has_fee_data = bool(fee_parsed)

        addr_road = r.get("FA_RDNMA") or ""
        addr_detail = (r.get("FA_RDNDA") or "").strip()
        phone = r.get("FA_TELNO")
        if phone in (None, "null", ""):
            phone = None

        slug = f"{slugify_name(name)}-{aca_asnum}"

        out.append({
            "aca_asnum": aca_asnum,
            "name": name,
            "inst_type": r.get("ACA_INSTI_SC_NM"),
            "sido": sido,
            "sigungu": sigungu,
            "status": r.get("REG_STTUS_NM"),
            "category_name": category_name,
            "category_slug": category_slug,
            "realm_raw": realm,
            "course_name": r.get("LE_CRSE_NM"),
            "course_list_raw": r.get("LE_CRSE_LIST_NM"),
            "fee_raw": fee_raw.strip() if fee_raw else None,
            "fee_parsed": fee_parsed,
            "has_fee_data": has_fee_data,
            "capacity_total": r.get("TOFOR_SMTOT"),
            "capacity_hourly": r.get("DTM_RCPTN_ABLTY_NMPR_SMTOT"),
            "address_road": addr_road.strip(),
            "address_detail": addr_detail,
            "zipcode": r.get("FA_RDNZC"),
            "phone": phone,
            "reg_date": r.get("REG_YMD"),
            "slug": slug,
            "content_hash": content_hash(r),
        })

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    fee_count = sum(1 for a in out if a["has_fee_data"])
    print(f"total={len(out)} fee_filled={fee_count} ({fee_count/len(out)*100:.1f}%)")


if __name__ == "__main__":
    main()
