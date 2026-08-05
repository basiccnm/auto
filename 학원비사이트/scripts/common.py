import hashlib
import re

OFFICE_CODES = {
    "B10": "서울", "C10": "부산", "D10": "대구", "E10": "인천", "F10": "광주",
    "G10": "대전", "H10": "울산", "I10": "세종", "J10": "경기", "K10": "강원",
    "M10": "충북", "N10": "충남", "P10": "전북", "Q10": "전남", "R10": "경북",
    "S10": "경남", "T10": "제주",
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
DEFAULT_CATEGORY = ("기타학원", "gita")


def slugify_name(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r"[^\w가-힣]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "academy"


# 과정명 끝에 붙은 스케줄 괄호(예: "(주3회, 회130분)") 제거용. 괄호 안에 주/회/분이 있고 문자열 끝에 오는 경우만.
FEE_SCHEDULE_PAREN = re.compile(r"\((?=[^()]*[주회분])[^()]*\)\s*$")


def parse_fee(raw):
    if not raw or not raw.strip():
        return None
    items = []
    # 레코드 구분자는 "가격(숫자) 뒤에 오는 콤마"만. 괄호 안 스케줄 콤마(회/분 앞)와 구분해서
    # "수학고등(주3회, 회130분):360000" 같은 항목이 잘리지 않게 함.
    for part in re.split(r"(?<=\d),\s*", raw):
        part = part.strip()
        if not part or ":" not in part:
            continue
        course, price = part.rsplit(":", 1)
        price = price.strip()
        if not price.isdigit():
            continue
        course = FEE_SCHEDULE_PAREN.sub("", course.strip()).strip()
        items.append({"course": course, "price": int(price)})
    return items or None


def content_hash(row: dict) -> str:
    keys = [
        "ACA_NM", "REG_STTUS_NM", "PSNBY_THCC_CNTNT", "FA_RDNMA", "FA_RDNDA",
        "FA_TELNO", "TOFOR_SMTOT", "DTM_RCPTN_ABLTY_NMPR_SMTOT", "REALM_SC_NM",
        "LE_CRSE_NM",
    ]
    blob = "|".join(str(row.get(k, "")) for k in keys)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def normalize_row(row: dict, office_sido: str) -> dict:
    aca_asnum = row.get("ACA_ASNUM")
    name = (row.get("ACA_NM") or "").strip()
    sigungu = (row.get("ADMST_ZONE_NM") or "").strip() or "미상"
    realm = row.get("REALM_SC_NM")
    category_name, category_slug = REALM_TO_CATEGORY.get(realm, DEFAULT_CATEGORY)
    fee_raw = row.get("PSNBY_THCC_CNTNT")
    fee_raw = fee_raw.strip() if fee_raw else None
    fee_parsed = parse_fee(fee_raw)

    phone = row.get("FA_TELNO")
    if phone in (None, "null", ""):
        phone = None

    return {
        "aca_asnum": aca_asnum,
        "office_code": row.get("ATPT_OFCDC_SC_CODE"),
        "office_name": row.get("ATPT_OFCDC_SC_NM"),
        "sido": office_sido,
        "sigungu": sigungu,
        "inst_type": row.get("ACA_INSTI_SC_NM"),
        "name": name,
        "status": row.get("REG_STTUS_NM"),
        "realm_raw": realm,
        "category_name": category_name,
        "category_slug": category_slug,
        "course_name": row.get("LE_CRSE_NM"),
        "course_list_raw": row.get("LE_CRSE_LIST_NM"),
        "fee_raw": fee_raw,
        "fee_parsed": fee_parsed,
        "has_fee_data": bool(fee_parsed),
        "capacity_total": row.get("TOFOR_SMTOT"),
        "capacity_hourly": row.get("DTM_RCPTN_ABLTY_NMPR_SMTOT"),
        "address_road": (row.get("FA_RDNMA") or "").strip(),
        "address_detail": (row.get("FA_RDNDA") or "").strip(),
        "zipcode": row.get("FA_RDNZC"),
        "phone": phone,
        "reg_date": row.get("REG_YMD"),
        "slug": f"{slugify_name(name)}-{aca_asnum}",
        "content_hash": content_hash(row),
    }
