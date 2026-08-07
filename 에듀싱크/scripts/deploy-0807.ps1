# 보상 시스템 배포 (지시서 0807) — Windows PowerShell 용
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-0807.ps1           미리보기
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-0807.ps1 -Apply    실제 적용
#
# 순서 A(DB) -> B(워커) 는 바꾸지 말 것.
# 워커가 먼저 나가면 아직 없는 표를 찾아 500 이 난다.
#
# -Force : A 가 «이미 들어가 있어서» 실패한 경우에만 쓴다(두 번째 실행).
#          ALTER 에는 IF NOT EXISTS 가 없어 재실행이면 «duplicate column» 으로 멈추는데,
#          그건 실패가 아니라 «이미 됐다» 는 뜻이라 B 로 넘어가야 한다.
param([switch]$Apply, [switch]$Force)

$ErrorActionPreference = "Stop"
# 이 스크립트가 있는 폴더의 부모 = 에듀싱크 (어디서 실행하든 같은 곳을 본다)
Set-Location (Split-Path $PSScriptRoot -Parent)

$CFG    = "workers/site-renderer/wrangler.toml"
$DB     = "eduthink-db"
$WORKER = "eduthink-site-renderer"   # 배포 대상. olmanama 이 아니다 (07-21 오배포 사고)
$TABLES = "'store_items','reward_orders','child_mode_config','reactions','mission_verifications','parent_mission_templates'"

function Say($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function D1 { npx wrangler d1 execute $DB --remote --config $CFG @args }

# ⚠ $ErrorActionPreference 는 **외부 프로그램(npx·wrangler)의 실패를 못 잡는다.**
#   PowerShell 은 exe 가 0 이 아닌 코드로 죽어도 그냥 다음 줄로 간다.
#   이걸 안 보면 A(DB) 가 통째로 실패해도 B(워커) 가 나가서, 이 스크립트가 맨 위에서
#   «바꾸지 말 것» 이라고 적어 둔 바로 그 사고(표 없는데 워커 먼저)가 그대로 난다.
function MustSucceed($what) {
  if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] $what 가 실패했습니다 (종료코드 $LASTEXITCODE). 워커는 올리지 않고 멈춥니다." -ForegroundColor Red
    Write-Host @"
    위 오류가 «duplicate column name» 이면 **이미 적용된 것**입니다 - 실패가 아닙니다.
    그때는 이렇게 다시 부르면 A 를 건너뛰고 B 로 갑니다:
        powershell -ExecutionPolicy Bypass -File scripts\deploy-0807.ps1 -Apply -Force
    그 밖의 오류(로그인·권한·이름)는 고친 뒤 다시 -Apply 로 처음부터.
"@ -ForegroundColor Yellow
    exit 1
  }
}

Say "0. 지금 상태 (아직 안 올렸으면 비어 있는 게 정상)"
D1 --command "SELECT name FROM sqlite_master WHERE type='table' AND name IN ($TABLES)"
# «비어 있음» 과 «못 물어봤음» 은 화면에 똑같이 아무것도 안 나온다 - 구분해서 말해 준다
$probeCode = $LASTEXITCODE
if ($probeCode -ne 0) {
  Write-Host "`n[!] DB 에 물어보지 못했습니다 (종료코드 $probeCode)." -ForegroundColor Red
  Write-Host "    위가 «비어 있다» 는 뜻이 아닙니다. 로그인(npx wrangler login)·DB 이름($DB)을 먼저 확인하세요." -ForegroundColor Yellow
  exit 1
}

if (-not $Apply) {
  Write-Host @"

미리보기만 했습니다. 실제로 적용하려면 뒤에 -Apply 를 붙이세요:
    powershell -ExecutionPolicy Bypass -File scripts\deploy-0807.ps1 -Apply

적용될 것
  A. DB   migrate_reward_2026-08-07.sql  (표 6 · 인덱스 7 · orders 확장 2)
          migrate_pin_2026-08-07.sql     (PIN 시도제한 2컬럼)
  B. 워커  eduthink-site-renderer        (보상 13 + PIN 3 + 리롤 1 라우트)
  C. APK  는 따로 - 아래 안내대로
"@ -ForegroundColor Yellow
  exit 0
}

if ($Force) { Say "(-Force) A 의 실패를 «이미 적용됨» 으로 보고 넘어갑니다" }

Say "A-1. 표·인덱스 (추가만 한다)"
D1 --file scripts/migrate_reward_2026-08-07.sql
if (-not $Force) { MustSucceed "A-1 (표·인덱스)" }

Say "A-2. PIN 시도 제한 (A-1 이 child_mode_config 를 만든 뒤라야 한다)"
D1 --file scripts/migrate_pin_2026-08-07.sql
if (-not $Force) { MustSucceed "A-2 (PIN 시도 제한)" }

Say "A-3. 확인 - 표 6개가 다 있을 때만 B 로 간다"
# 사람이 눈으로 6 을 읽는 것에 맡기면, 못 보고 지나쳐도 워커가 그냥 나간다 → 스크립트가 센다
$raw = (D1 --json --command "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name IN ($TABLES)") -join "`n"
Write-Host $raw
$n = $null
try { $n = [int]((ConvertFrom-Json $raw)[0].results[0].n) } catch { }
if ($null -eq $n) {
  # 형식이 달라 «못 읽은» 것이지 «없다» 가 아니다 - 숫자만 다시 훑는다
  $m = [regex]::Match($raw, '"n"\s*:\s*(\d+)')
  if ($m.Success) { $n = [int]$m.Groups[1].Value }
}
if ($n -ne 6) {
  $shownN = if ($null -eq $n) { "못 읽음" } else { $n }
  Write-Host "`n[!] 표가 6개가 아닙니다 (읽은 값: $shownN). 표 없이 워커가 나가면 500 입니다." -ForegroundColor Red
  if (-not $Force) {
    Write-Host "    A 를 먼저 끝내세요. 눈으로 6 을 확인했는데 못 읽은 것뿐이라면 -Force 로 B 만 갑니다." -ForegroundColor Yellow
    exit 1
  }
  Write-Host "    (-Force) 확인을 건너뛰고 B 로 갑니다." -ForegroundColor Yellow
}

Say "B. 워커 배포"
# --config 를 빼면 엉뚱한 워커로 나간다 (올마나마에서 실제로 났던 사고)
# ⚠ 2>&1 로 받는 순간 wrangler 가 stderr 에 찍는 «평범한 안내문»까지 오류 기록이 된다.
#   EAP=Stop 인 채로 두면 배포되기도 전에 그 안내문 한 줄에 스크립트가 죽는다 → 이 구간만 푼다.
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$out = npx wrangler deploy --config $CFG 2>&1
$deployCode = $LASTEXITCODE
$ErrorActionPreference = $prevEAP
$out | ForEach-Object { Write-Host $_ }
if ($deployCode -ne 0) {
  Write-Host "`n[!] 워커 배포가 실패했습니다 (종료코드 $deployCode). DB(A)는 이미 적용된 상태입니다." -ForegroundColor Red
  Write-Host "    고친 뒤 -Apply -Force 로 다시 부르면 A 를 건너뛰고 B 만 갑니다." -ForegroundColor Yellow
  exit 1
}
if (($out -join "`n") -notmatch [regex]::Escape($WORKER)) {
  Write-Host "`n[!] 출력에 '$WORKER' 가 없습니다 - 엉뚱한 워커로 나갔을 수 있습니다. 확인하세요." -ForegroundColor Red
  exit 1
}

Say "B-2. 라우트 확인 (AUTH_REQUIRED 가 나오면 정상 · 404 면 화이트리스트를 볼 것)"
$url = ([regex]::Match(($out -join "`n"), 'https://[a-z0-9.-]*workers\.dev')).Value
if ($url) { try { (Invoke-WebRequest "$url/api/v1/child-mode/pin" -UseBasicParsing).Content } catch { $_.ErrorDetails.Message } }
else { Write-Host "(주소를 못 읽었습니다 - 손으로 확인)" }

Write-Host @"


[OK] A·B 끝. 다음은 C(APK) - 화면은 APK 안에 들어 있어서 이걸 해야 새 화면이 나옵니다.

    `$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
    cd app\android
    .\gradlew.bat assembleDebug
    adb install -r "`$env:LOCALAPPDATA\eduthink-build\android\app\outputs\apk\debug\app-debug.apk"

그다음 실기기 8항목 - docs\배포점검-0807-보상시스템.md 맨 아래.
6·7 은 «되는지»가 아니라 «막히는지»를 봅니다 (리롤 2회차 · PIN 5회 잠금).
"@ -ForegroundColor Green
