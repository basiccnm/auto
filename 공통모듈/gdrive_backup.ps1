# 구글드라이브 자동 백업 (작업 스케줄러 "GDrive프로젝트백업"이 매일 21:00 실행)
# 대상: 블로그수입관련 전체 + 로블록스-학교펫게임 → G:\내 드라이브\프로젝트백업\
# 제외: node_modules, .wrangler, __pycache__, dist, .git, _preview, naver_browser_profile (재생성 가능한 캐시/대용량)
#       uploader_profile = 쇼츠 업로더의 로그인 세션. 재생성 가능하지만 **캐시라서가 아니라 보안 때문에** 제외한다
#       (유튜브·틱톡·인스타·네이버 로그인 쿠키 = 계정 그 자체. 클라우드에 올리지 않는다)
# /MIR = 완전 미러(원본에서 지운 파일은 백업에서도 지워짐)
# 경로는 전부 하드코딩 — 스케줄러 실행 환경에서 환경변수가 비어 첫 실행이 조용히 죽은 사고(2026-07-17) 재발 방지

$log = "C:\Users\hardb\AppData\Local\gdrive_backup.log"
$errLog = "C:\Users\hardb\AppData\Local\gdrive_backup_error.log"

try {
    "===== backup start $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" | Out-File $log -Encoding utf8 -ErrorAction Stop

    if (-not (Test-Path "G:\내 드라이브")) {
        throw "G: 드라이브(구글드라이브) 없음 — Drive for Desktop이 안 떠 있거나 로그인 풀림"
    }

    $pairs = @(
        @{ src = "C:\Users\hardb\Desktop\블로그수입관련";     dst = "G:\내 드라이브\프로젝트백업\블로그수입관련" },
        @{ src = "C:\Users\hardb\Desktop\로블록스-학교펫게임"; dst = "G:\내 드라이브\프로젝트백업\로블록스-학교펫게임" }
    )
    # _site = Eleventy 빌드 결과물(학원비사이트, 8만개). 소스에서 재생성되므로 dist와 같은 취급.
    $excludeDirs = "node_modules", ".wrangler", "__pycache__", "dist", ".git", "_preview", "naver_browser_profile", "_site", "uploader_profile"

    foreach ($p in $pairs) {
        if (-not (Test-Path $p.src)) { "SKIP (없음): $($p.src)" | Out-File $log -Append -Encoding utf8; continue }
        & "C:\Windows\System32\Robocopy.exe" $p.src $p.dst /MIR /XD $excludeDirs /R:2 /W:5 /NP /NFL /NDL /LOG+:$log
        "robocopy 종료코드: $LASTEXITCODE ($($p.src))" | Out-File $log -Append -Encoding utf8   # 0~7=정상, 8+=오류
    }

    "===== backup end $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" | Out-File $log -Append -Encoding utf8
}
catch {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 백업 실패: $($_.Exception.Message)" | Out-File $errLog -Append -Encoding utf8
    exit 1
}
