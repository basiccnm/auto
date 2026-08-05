# -*- coding: utf-8 -*-
"""
[올마나마] 단일 간장 키(cg_soy_sauce 등) -> 진간장/국간장/양조간장 정밀 분리 마이그레이션 스크립트

사용법:
  python scripts/ganjang_split_migrate.py --dry      # 모의 실행 (DB 변경 없음, 분석 및 디버그 로그 생성)
  python scripts/ganjang_split_migrate.py --apply    # 실제 DB 반영 및 백업 생성

디버그 로그:
  logs/ganjang_split_YYYYMMDD_HHMMSS.log
"""

import os
import sys
import io
import shutil
import sqlite3
import logging
from datetime import datetime

# 한글 출력 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "eolmanama.db")
LOG_DIR = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# 로깅 설정 (상세 디버그 로그 파일 및 콘솔 출력)
# -------------------------------------------------------------------
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(LOG_DIR, f"ganjang_split_{timestamp}.log")

logger = logging.getLogger("ganjang_split")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# -------------------------------------------------------------------
# 간장 분류 키 및 매칭 규칙
# -------------------------------------------------------------------
KEY_JIN = "cg_soy_sauce_jin"       # 진간장 (조림, 볶음, 찜, 불고기 등)
KEY_GUK = "soy_sauce_guk"          # 국간장/조선간장 (국, 찌개, 탕, 나물 등)
KEY_YANGJO = "cg_soy_sauce_yangjo" # 양조간장 (양념장, 회, 드레싱, 무침 등)

GUK_KEYWORDS = ["국", "찌개", "탕", "나물", "전골", "미역국", "콩나물", "무국", "된장국", "수제비"]
YANGJO_KEYWORDS = ["양념장", "드레싱", "소스", "무침", "겉절이", "비빔", "딥", "퐁당"]

def classify_soy_sauce(dish_name, category_name, recipe_text):
    """
    요리 이름, 카테고리, 레시피 텍스트 문맥을 분석하여 적절한 간장 키 반환
    """
    text_combined = f"{dish_name} {category_name} {recipe_text}".lower()
    
    # 1. 국간장 키워드 우선 검사
    for kw in GUK_KEYWORDS:
        if kw in text_combined:
            return KEY_GUK, f"국/나물 키워드 감지 ('{kw}')"
            
    # 2. 양조간장 키워드 검사
    for kw in YANGJO_KEYWORDS:
        if kw in text_combined:
            return KEY_YANGJO, f"양념장/드레싱 키워드 감지 ('{kw}')"
            
    # 3. 기본값: 진간장 (조림, 볶음, 기본 한식 조리용)
    return KEY_JIN, "기본 조림/볶음용 (진간장 지정)"


def backup_database():
    """DB 백업 수행"""
    if not os.path.exists(DB_PATH):
        logger.error(f"❌ DB 파일을 찾을 수 없습니다: {DB_PATH}")
        sys.exit(1)
        
    bak_name = os.path.join(BASE, "data", f"eolmanama.db.bak_{datetime.now().strftime('%Y%m%d')}_ganjang")
    shutil.copy2(DB_PATH, bak_name)
    logger.info(f"✅ DB 사전 백업 완료: {bak_name}")
    return bak_name


def run_migration(apply=False):
    logger.info("=" * 60)
    logger.info(f"🚀 간장 키 분리 마이그레이션 시작 (적용 모드: {'APPLY (실제 DB 수정)' if apply else 'DRY-RUN (모의 실행)'})")
    logger.info(f"📝 디버그 로그 파일: {log_filename}")
    logger.info("=" * 60)
    
    if apply:
        backup_database()
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # SQL 1: 대상 재료 조회 (cg_soy_sauce / ganjang)
        query_select = """
            SELECT mi.id as row_id, mi.menu_id, mi.ingredient_key,
                   m.name as menu_name, m.category as menu_cat, m.recipe_steps
            FROM menu_ingredients mi
            JOIN menus m ON mi.menu_id = m.id
            WHERE mi.ingredient_key IN ('cg_soy_sauce', 'ganjang', 'soy_sauce');
        """
        logger.debug(f"[SQL EXECUTE] {query_select.strip()}")
        cur.execute(query_select)
        rows = cur.fetchall()
        
        logger.info(f"📊 대상 간장 매칭 항목 총 {len(rows)}건 발견")
        
        counts = {KEY_JIN: 0, KEY_GUK: 0, KEY_YANGJO: 0}
        updates = []
        
        for r in rows:
            row_id = r["row_id"]
            menu_id = r["menu_id"]
            menu_name = r["menu_name"] or ""
            menu_cat = r["menu_cat"] or ""
            recipe_steps = r["recipe_steps"] or ""
            old_key = r["ingredient_key"]
            
            new_key, reason = classify_soy_sauce(menu_name, menu_cat, recipe_steps)
            counts[new_key] += 1
            
            logger.debug(f"[분류] ID:{row_id} | 메뉴: '{menu_name}' ({menu_cat}) -> {old_key} ==> {new_key} (사유: {reason})")
            
            updates.append((new_key, row_id))
            
        logger.info("-" * 60)
        logger.info(f"📈 분류 집계 결과:")
        logger.info(f"  - 진간장 ({KEY_JIN}): {counts[KEY_JIN]}건")
        logger.info(f"  - 국간장 ({KEY_GUK}): {counts[KEY_GUK]}건")
        logger.info(f"  - 양조간장 ({KEY_YANGJO}): {counts[KEY_YANGJO]}건")
        logger.info("-" * 60)
        
        if apply:
            query_update = """
                UPDATE menu_ingredients
                SET ingredient_key = ?, updated_at = datetime('now')
                WHERE id = ?;
            """
            logger.debug(f"[SQL EXECUTE BATCH] {query_update.strip()}")
            cur.executemany(query_update, updates)
            conn.commit()
            logger.info(f"✅ DB 마이그레이션 성공적으로 완료되었습니다! ({len(updates)}개 행 수정)")
        else:
            logger.info("ℹ️ DRY-RUN 모드입니다. DB에 실제 변경 사항은 적용되지 않았습니다.")
            logger.info("실제 반영을 하려면 '--apply' 옵션을 붙여 실행하세요.")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 마이그레이션 중 오류 발생! 트랜잭션 롤백됨: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    is_apply = "--apply" in sys.argv
    run_migration(apply=is_apply)
