# ══════════════════════════════════════════════════════════════
# daily.ps1 — 하루 한 번 도는 갱신. 작업 스케줄러가 실행한다.
#
# 🔴 왜 깃허브 액션이 아니라 «이 PC» 인가 (2026-08-02 실측)
#    KAMIS 는 **해외 IP 를 막는다.** 깃허브 러너(미국 Azure, Cheyenne)에서 부르면
#    헤더를 어떻게 맞춰도 **HTTP 406 Not Acceptable** 이 돌아온다. 4가지 조합 전부 실패.
#    → 시세 수집은 **한국 IP 인 이 PC 에서만** 된다. 깃허브는 저장·배포만 맡는다.
#    ⚠️ 공공데이터 API 는 대체로 같은 정책이다. 다른 프로젝트를 액션으로 옮길 때도 같은 벽을 만난다.
#
# 하는 일
#   ① build.py   시세 수집 → 폭등 선별 → 대체재 → site/ 갱신
#   ② review.py  검수. **불합격이면 여기서 멈춘다. 올리지 않는다**
#   ③ git push   통과했고 바뀐 게 있을 때만
# ══════════════════════════════════════════════════════════════

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LOG  = Join-Path $ROOT '.build\daily.log'
New-Item -ItemType Directory -Force (Split-Path $LOG) | Out-Null
function Log($m) { "$(Get-Date -Format 'MM-dd HH:mm:ss')  $m" | Out-File $LOG -Append -Encoding utf8 }

$env:PYTHONIOENCODING = 'utf-8'
# ⚠ 이걸 안 하면 파이썬이 뱉은 한글을 파워셸이 콘솔 코드페이지(949)로 읽어 로그가 깨진다.
#   ⚠ 이 .ps1 파일 자체도 **UTF-8 BOM** 으로 저장해야 한다. BOM 이 없으면 5.1 이 ANSI 로 읽어
#     한글이 깨지고 «문자열에 " 종결자가 없습니다» 같은 엉뚱한 문법 오류가 난다(2026-08-02).
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location $ROOT

# ── ① 굽기 ──
# ⚠ native exe 의 stderr 를 2>&1 로 합치지 말 것. ErrorActionPreference=Stop 이라 예외가 된다
#   (문지기에서 똑같은 걸로 회수가 통째로 멈춰 있었다, 2026-08-02).
$prev = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$build = & python scripts\build.py | Out-String
$ErrorActionPreference = $prev
Log "build: $($build.Trim())"

# ── ② 검수 ──
$ErrorActionPreference = 'Continue'
$review = & python scripts\review.py | Out-String
$rc = $LASTEXITCODE
$ErrorActionPreference = $prev

if ($rc -ne 0) {
    Log "검수 불합격 — 올리지 않는다"
    Log $review.Trim()
    exit 1
}
Log '검수 통과'

# ── ③ 올리기 ──
$changed = & git status --porcelain site
if (-not $changed) { Log '바뀐 게 없다'; exit 0 }

& git add site
& git commit -q -m "시세 갱신 $(Get-Date -Format 'yyyy-MM-dd')"
& git push -q origin main
Log '올림 완료'
