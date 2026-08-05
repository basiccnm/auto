# 올마나마 갱신 · 배포 (2026-07-22)
#  .bat에 한글을 넣으면 cmd가 goto 위치를 바이트로 세다 어긋나 깨진다 → 실제 작업은 여기서 한다.
#  루트의 갱신배포.bat 은 이 파일을 부르는 ASCII 런처일 뿐이다.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$ROOT = Split-Path $PSScriptRoot -Parent
Set-Location $ROOT

function Step($label, $script) {
    Write-Host "`n[$label] $script" -ForegroundColor Cyan
    & python "scripts\$script"
    if ($LASTEXITCODE -ne 0) { throw "$script 실패 (종료코드 $LASTEXITCODE)" }
}

Write-Host "============================================" -ForegroundColor DarkGray
Write-Host "  올마나마 갱신 · 배포        $(Get-Date -Format 'MM-dd HH:mm')"
Write-Host "============================================" -ForegroundColor DarkGray
Write-Host @"

  1  시세만 갱신         KAMIS 수집 + 원가 재계산
  2  화면만 다시 만들기   DB를 직접 고친 뒤
  3  검사만              healthcheck
  4  전체 + 배포         1~3 하고 olmanama.com 에 올림
  0  나가기
"@
$sel = Read-Host "`n번호 입력"
if ($sel -eq '0') { return }
if ($sel -notin '1', '2', '3', '4') { Write-Host "  잘못된 번호입니다." -ForegroundColor Red; return }

try {
    if ($sel -in '1', '4') {
        Step '수집' 'collect_kamis_all.py'
        Step '계산' 'compute_line_costs.py'
    }
    if ($sel -in '2', '4') {
        Step '화면' 'gen_dishes.py'
        Step '화면' 'gen_preview_html.py'
        Step '화면' 'gen_prices_page.py'
        Step '빌드' 'build_dist.py'
    }
    if ($sel -in '3', '4') {
        Write-Host "`n[검사] healthcheck.py" -ForegroundColor Cyan
        & python scripts\healthcheck.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "`n  검사에서 문제가 나왔습니다. 위 목록을 보세요. 배포하지 않고 멈춥니다." -ForegroundColor Red
            return
        }
    }
    if ($sel -eq '4') {
        Write-Host "`n--------------------------------------------" -ForegroundColor Yellow
        Write-Host "  실서비스 olmanama.com 에 올립니다." -ForegroundColor Yellow
        Write-Host "--------------------------------------------" -ForegroundColor Yellow
        if ((Read-Host "정말 배포할까요? (y 입력)") -notin 'y', 'Y') {
            Write-Host "  배포하지 않았습니다."; return
        }
        Push-Location "workers\site-renderer"
        try {
            & npx wrangler deploy
            if ($LASTEXITCODE -ne 0) { throw "wrangler deploy 실패" }
            Write-Host "`n  배포 완료 — https://olmanama.com" -ForegroundColor Green
        } finally { Pop-Location }
    }
    Write-Host "`n  끝났습니다." -ForegroundColor Green
} catch {
    Write-Host "`n  *** 중단되었습니다 ***" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
}
