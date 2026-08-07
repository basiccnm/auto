# 로그온 백업 메움이 (2026-08-07)
# 시작프로그램(shell:startup)에서 불린다. 하는 일은 하나 — **오늘 백업이 아직 없으면 한 번 돌린다.**
#
# 왜 필요한가
#   정기 백업은 작업 스케줄러 "GDrive프로젝트백업"(매일 21:00)이 진다.
#   그런데 **21시에 PC 가 꺼져 있으면 그날은 그냥 걸러진다.**
#   실제로 2026-08-05·06 이 걸러져 8/4 상태로 3일을 보냈다(2026-08-07 확인).
#   그 작업은 관리자 소유라 트리거를 더할 수 없었다(Access denied) → 사용자 권한으로 도는 이 길을 둔다.
#
# ⚠ 정기 작업을 대신하지 않는다. **걸러진 날만 메운다.**
# ⚠ 오늘 이미 돌았으면 아무것도 안 한다 — 로그온마다 전체 미러를 돌리면 부팅이 느려진다.

$log     = "C:\Users\hardb\AppData\Local\gdrive_backup.log"
$backup  = "C:\Users\hardb\Desktop\블로그수입관련\공통모듈\gdrive_backup.ps1"
$stamp   = "C:\Users\hardb\AppData\Local\gdrive_backup_lastrun.txt"

Start-Sleep -Seconds 180      # 부팅 직후는 드라이브 마운트·네트워크가 아직이다. 3분 기다린다

try {
    $today = Get-Date -Format 'yyyy-MM-dd'

    # 오늘 이미 돌았나 — 도장 파일이 우선, 없으면 로그의 시작 줄로 판단
    $ranToday = $false
    if (Test-Path $stamp) {
        if ((Get-Content $stamp -ErrorAction SilentlyContinue | Select-Object -First 1) -eq $today) { $ranToday = $true }
    }
    if (-not $ranToday -and (Test-Path $log)) {
        $first = Get-Content $log -TotalCount 1 -ErrorAction SilentlyContinue
        if ($first -match $today) { $ranToday = $true }
    }
    if ($ranToday) { return }

    # G: 가 아직 안 떴으면 더 기다린다(최대 10분) — Drive for Desktop 이 늦게 뜨는 날이 있다
    $waited = 0
    while (-not (Test-Path "G:\내 드라이브") -and $waited -lt 600) {
        Start-Sleep -Seconds 30; $waited += 30
    }
    if (-not (Test-Path "G:\내 드라이브")) { return }   # 조용히 물러난다. 21시 정기분이 다시 시도한다

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $backup
    Set-Content $stamp $today -Encoding utf8
}
catch {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 로그온 메움 실패: $($_.Exception.Message)" |
        Out-File "C:\Users\hardb\AppData\Local\gdrive_backup_error.log" -Append -Encoding utf8
}
