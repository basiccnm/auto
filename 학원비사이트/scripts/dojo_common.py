from __future__ import annotations

import hashlib
import re

SIDO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남", "전라북도": "전북", "전북특별자치도": "전북",
    "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}

CATEGORY_SLUG = {
    "태권도": "taekwondo", "권투": "boxing", "유도": "judo", "합기도": "hapkido",
    "레슬링": "wrestling", "검도": "kumdo", "우슈": "wushu",
}
DEFAULT_CATEGORY_SLUG = "gita"

# 종목 필드(BZSTAT_SE_NM)가 비어있을 때 사업장명 키워드로 보완 분류
NAME_KEYWORD_SPORT = [
    ("태권도", "태권도"), ("검도", "검도"), ("유도", "유도"), ("합기도", "합기도"),
    ("복싱", "권투"), ("킥복싱", "권투"), ("권투", "권투"), ("레슬링", "레슬링"),
    ("우슈", "우슈"),
]


def infer_sport_from_name(name: str) -> str:
    for keyword, sport in NAME_KEYWORD_SPORT:
        if keyword in name:
            return sport
    return ""


def slugify_name(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r"[^\w가-힣]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "dojo"


def parse_address(addr: str):
    if not addr or not addr.strip():
        return None, None
    parts = addr.strip().split()
    if len(parts) < 2:
        return None, None
    sido_raw, sigungu = parts[0], parts[1]
    sido = SIDO_MAP.get(sido_raw, sido_raw)
    return sido, sigungu


def content_hash(item: dict) -> str:
    keys = [
        "BPLC_NM", "SALS_STTS_NM", "DTL_SALS_STTS_NM", "ROAD_NM_ADDR", "LOTNO_ADDR",
        "TELNO", "LDER_CNT", "MBR_RCRT_TOTAL_PERNE", "BZSTAT_SE_NM", "CLSBIZ_YMD",
    ]
    blob = "|".join(str(item.get(k, "")) for k in keys)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def normalize_item(item: dict) -> dict | None:
    name = (item.get("BPLC_NM") or "").strip()
    addr_road = (item.get("ROAD_NM_ADDR") or "").strip()
    addr_lot = (item.get("LOTNO_ADDR") or "").strip()
    sido, sigungu = parse_address(addr_road or addr_lot)
    if not sido or not sigungu:
        return None

    sport = (item.get("BZSTAT_SE_NM") or "").strip()
    sport_inferred = False
    if not sport:
        inferred = infer_sport_from_name(name)
        if inferred:
            sport = inferred
            sport_inferred = True
    category_slug = CATEGORY_SLUG.get(sport, DEFAULT_CATEGORY_SLUG)
    category_name = f"{sport}장" if sport else "체육도장"

    status_name = item.get("SALS_STTS_NM")
    is_open = status_name == "영업/정상"

    phone = item.get("TELNO") or None
    mng_no = item.get("MNG_NO")
    grp_cd = item.get("OPN_ATMY_GRP_CD")

    return {
        "mng_no": mng_no,
        "opn_atmy_grp_cd": grp_cd,
        "name": name,
        "sport_name": sport,
        "sido": sido,
        "sigungu": sigungu,
        "status_code": item.get("SALS_STTS_CD"),
        "status_name": status_name,
        "detail_status_name": item.get("DTL_SALS_STTS_NM"),
        "is_open": is_open,
        "license_ymd": item.get("LCPMT_YMD"),
        "closed_ymd": item.get("CLSBIZ_YMD") or None,
        "address_road": addr_road,
        "address_lot": addr_lot,
        "zipcode": item.get("ROAD_NM_ZIP"),
        "phone": phone,
        "leader_count": item.get("LDER_CNT") or None,
        "member_capacity": item.get("MBR_RCRT_TOTAL_PERNE"),
        "category_name": category_name,
        "category_slug": category_slug,
        "slug": f"{slugify_name(name)}-{mng_no}",
        "content_hash": content_hash(item),
    }
