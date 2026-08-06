// ================= 자녀 데이터 · 삭제 연쇄 (단일 진입점) =================
// 정본 §8 "저장(스토리지)" 블록 · 계약 §5 · 회신19 §2-1
//
// 🔴 **자녀 데이터를 지우는 경로는 이 파일 하나뿐이다.**
//    사용자 단건 삭제 / 전체 삭제 / admin 삭제 / API DELETE — 전부 여기를 부른다.
//
// 왜 파일을 따로 뺐나: 블록5(api_records.js)가 순환 import를 피하려고 index.js의
// deleteChildCascade를 **복제**했었다. 두 벌이 되면 자녀에 딸린 테이블이 늘 때
// 한 곳을 빠뜨리게 되고, 그러면 **R2에 아이 사진이 영구히 남는다**(복구 불가).
// "언제든 원본까지 전부 삭제"가 사용자에게 한 약속이라 이건 안전 사고 지점이다.
// → 도메인 모듈로 승격해 단일 진입점을 복원했다(회신19 승인).

// 파생 키(썸네일 등)는 **원본 키에서 유도 가능하게** 이름 짓는다.
// "지울 목록을 몰라서 못 지우는" 상황을 구조로 차단하기 위함 — 파생을 늘릴 때
// 이 배열에만 추가하면 삭제가 자동으로 따라간다.
export const R2_DERIVED_SUFFIXES = ["_t"];

export function r2KeysOf(imageKey) {
  return [imageKey, ...R2_DERIVED_SUFFIXES.map((sfx) => imageKey + sfx)];
}

// 자녀 하나를 통째로 파기한다. 반환: { ok:true } | { ok:false, error }
//
// 순서가 전부다: **R2 먼저 → DB 나중.**
//   · DB를 먼저 지우면 image_key를 잃어 R2에 영구 고아 파일이 남는다(복구 불가).
//   · 반대로 R2 삭제 후 DB 삭제가 실패하면 "이미지 깨진 기록"이 남는데,
//     이건 사용자가 다시 삭제하면 정리된다.
//   → 실패하더라도 **복구 가능한 쪽으로** 실패시킨다.
export async function deleteChildCascade(db, env, childIdRaw) {
  // 🔴 반드시 정수로 바꾼다. D1의 bind()는 넘긴 타입을 그대로 보내서, 라우터 정규식이 준
  // 문자열 "38"을 그대로 쓰면 INTEGER 컬럼과 매칭되지 않는다 —
  // **삭제가 조용히 0건 처리되고 ok:true가 반환된다**(2026-07-24 실제로 당함).
  // API 경로는 DB에서 읽은 정수를 넘겨 우연히 동작했고, admin 경로만 실패했다.
  const childId = Number(childIdRaw);
  if (!Number.isFinite(childId)) return { ok: false, error: "invalid_child_id" };
  // 1) R2 원본 + 파생 먼저
  if (env && env.RECORDS) {
    /* 사진 여러 장(2026-07-27) — record_images 까지 훑는다.
       records.image_key 만 보면 2번째 장부터가 R2 에 고아로 남는다. */
    const { results } = await db.prepare(
      `SELECT image_key FROM records WHERE child_id = ? AND image_key IS NOT NULL
       UNION
       SELECT ri.image_key FROM record_images ri
         JOIN records r ON r.id = ri.record_id WHERE r.child_id = ?`
    ).bind(childId, childId).all();
    // 파생이 없는 기록이면 그 키는 그냥 없는 객체라 삭제가 무해하게 지나간다.
    const keys = results.flatMap((r) => (r.image_key ? r2KeysOf(r.image_key) : []));
    // R2 delete는 배열을 받는다. 한 번에 너무 많이 보내지 않도록 1,000개씩 끊는다(기록 상한과 동일).
    for (let i = 0; i < keys.length; i += 1000) {
      try {
        await env.RECORDS.delete(keys.slice(i, i + 1000));
      } catch (e) {
        // R2 삭제 실패 시 DB를 지우면 고아가 확정된다 → 중단하고 호출부에 알린다.
        // ⚠️ 에러를 반드시 남긴다 — 예전엔 삼켜서 "왜 삭제가 안 되는지" 추적이 불가능했다(2026-07-24).
        console.error("[deleteChildCascade] R2 삭제 실패 child=" + childId + ":", e && (e.message || e));
        return { ok: false, error: "r2_delete_failed" };
      }
    }
  }

  // 2) 자식 테이블 → 3) children 본체
  // ⚠️ 자녀에 딸린 테이블을 추가하면 **여기에만** 넣으면 된다. 이제 복사본이 없다.
  //
  // 판별 기준은 "개인 데이터로 보이는가"가 아니라 **child_id를 들고 있는가**다.
  // community_posts가 실제로 이 함수에서 빠져 있었다(2026-07-24 발견) — 학교 커뮤니티
  // "공개 글"이라 자녀 데이터로 안 보였지만 owner_token·작성 당시 학년·반을 함께 박제해
  // 보관한다. 자녀를 지워도 그게 남으면 "언제든 원본까지 전부 삭제" 약속이 깨진다.
  // → 새 테이블을 만들 때 child_id를 넣었다면 그 순간 이 배열도 같이 늘려야 한다.
  //
  // 🔴 `orders`는 지우지 않되 **연결은 끊어야 한다.** `orders.child_id`가 `children(id)`를
  //    참조하므로 그냥 두면 자녀 삭제가 **FOREIGN KEY 위반으로 500**이 난다 —
  //    즉 "이용권을 한 번이라도 산 자녀는 삭제가 안 되는" 상태였다(2026-07-24 검수에서 실제로 터짐.
  //    ①에서 주문 없는 자녀로만 시험해 안 드러났다).
  //    `child_id`는 nullable이라 NULL로 끊는다. 금액·기간·계정·상태는 그대로 남아 이력이 보존된다 —
  //    회신20 §3-3의 "계정 연결 끊고 익명 보존"을 자녀 단위에 그대로 적용한 것.
  await db.batch([
    db.prepare("UPDATE orders SET child_id = NULL WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM record_images WHERE record_id IN (SELECT id FROM records WHERE child_id = ?)").bind(childId),
    db.prepare("DELETE FROM records WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM activity_schedules WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM identifiers WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM personal_schedule WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM personal_events WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM schedule_settings WHERE child_id = ?").bind(childId),
    // ⚠️ 신고 기록이 **글보다 먼저** 지워져야 한다. `community_reports.post_id`가 NOT NULL로
    //    글을 참조해서, 순서를 바꾸면 FOREIGN KEY 위반으로 삭제 전체가 500이 난다
    //    (= 신고당한 글이 있는 자녀는 삭제 불가. orders FK와 똑같은 함정, 2026-07-24 실측).
    //    orders처럼 NULL로 끊을 수 없어서(NOT NULL) 지운다 — 글이 사라지면 그 글을 가리키던
    //    신고는 가리킬 대상이 없다. 회신20 §3-3의 "신고 이력 익명 보존"은 **계정 탈퇴** 얘기이고,
    //    거기서 끊을 연결은 owner_token(신고자)이지 post_id(대상)가 아니다.
    db.prepare("DELETE FROM community_reports WHERE post_id IN (SELECT id FROM community_posts WHERE child_id = ?)").bind(childId),
    db.prepare("DELETE FROM community_posts WHERE child_id = ?").bind(childId),
    // 2026-07-25 신설 — 판별 기준은 "개인정보처럼 보이는가"가 아니라 **child_id를 들고 있는가**(회신20).
    // 서류엔 주소·병명·상담 내용이, 대화엔 아이와 주고받은 말이 그대로 들어 있다.
    db.prepare("DELETE FROM documents WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM messages WHERE child_id = ?").bind(childId),
    db.prepare("DELETE FROM supplies WHERE child_id = ?").bind(childId),          // 2026-07-27 신설
    db.prepare("DELETE FROM children WHERE id = ?").bind(childId),
  ]);
  // 일부러 안 지우는 것: **orders**(위에서 child_id만 NULL로 끊었다). 결제 이력이라 보존이 원칙 —
  // 계약 §7.3-②가 payments를 "읽기 전용 이력으로 동결"한 것과 같은 이유다.
  return { ok: true };
}

// 기록 한 건 삭제 — 같은 원칙(R2 먼저 → DB 나중).
// 소유권 검증은 호출부 책임이다. 이 함수는 이미 확인된 record만 받는다.
export async function deleteRecordAssets(db, env, record) {
  /* 사진이 여러 장이 됐다(2026-07-27) — record_images 를 먼저 훑어 **전부** 지운다.
     image_key 한 장만 지우면 나머지 장이 R2 에 영원히 남는다(보이지 않는 고아). */
  const { results } = await db
    .prepare("SELECT image_key FROM record_images WHERE record_id = ? ORDER BY ord")
    .bind(record.id).all();
  const keys = (results || []).map((r) => r.image_key);
  if (record.image_key && !keys.includes(record.image_key)) keys.push(record.image_key);

  if (env && env.RECORDS && keys.length) {
    try {
      await env.RECORDS.delete(keys.flatMap((k) => r2KeysOf(k)));
    } catch (e) {
      // deleteChildCascade와 같은 이유로 삼키지 않는다 — 이 실패는 사용자에게 500으로만 보이고
      // 로그가 없으면 "왜 삭제가 안 되는지"를 못 쫓는다.
      console.error("[deleteRecordAssets] R2 삭제 실패 record=" + record.id + ":", e && (e.message || e));
      return { ok: false, error: "r2_delete_failed" };
    }
  }
  // 사진 행이 기록을 참조하므로 **먼저** 지운다
  await db.prepare("DELETE FROM record_images WHERE record_id = ?").bind(record.id).run();
  await db.prepare("DELETE FROM records WHERE id = ?").bind(record.id).run();
  return { ok: true };
}
