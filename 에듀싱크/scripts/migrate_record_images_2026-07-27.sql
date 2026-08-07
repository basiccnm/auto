-- 한 기록에 사진 여러 장 (2026-07-27)
--
-- 왜: `records.image_key` 가 한 칸뿐이라 **사진 한 장이 곧 기록 하나**였다.
--     통지표 앞·뒤 2장을 넣으면 「통지표」 기록이 두 건으로 갈렸다(사장님 발견).
--     디자인(5a)의 「3장」 배지·페이지 막대도 이 구조에선 늘 1장이라 무의미했다.
--
-- 어떻게: 사진을 별도 표로 뺀다. records 는 «한 건»의 뜻만 갖는다.
--     image_key 컬럼은 **지우지 않는다** — 옛 코드가 아직 읽을 수 있고,
--     되돌려야 할 때 근거가 남아야 한다. 새 코드는 record_images 만 본다.
--     (대표 사진 = ord 가 가장 작은 것)

CREATE TABLE IF NOT EXISTS record_images (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id  INTEGER NOT NULL REFERENCES records(id),
  ord        INTEGER NOT NULL DEFAULT 0,     -- 0부터. 앞장·뒷장 순서가 곧 이 값
  image_key  TEXT NOT NULL UNIQUE,           -- R2 키. 썸네일은 같은 키 + "_t"
  bytes      INTEGER,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_record_images_rec ON record_images(record_id, ord);

-- 기존 기록을 그대로 옮긴다. 한 건에 한 장씩 들어간다(지금 구조가 그랬으므로).
-- 두 번 돌려도 안전하다 — image_key 가 UNIQUE 라 중복 INSERT 는 무시된다.
INSERT OR IGNORE INTO record_images (record_id, ord, image_key, bytes, created_at)
SELECT id, 0, image_key, bytes, created_at FROM records WHERE image_key IS NOT NULL;
