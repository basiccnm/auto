# 보상 시스템 배포 (지시서 0807) — Windows PowerShell 용
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-0807.ps1           미리보기
#   powershell -ExecutionPolicy Bypass -File scripts\deploy-0807.ps1 -Apply    실제 적용
#
# 순서 A(DB) -> B(워커) 는 바꾸지 말 것.
# 워커가 먼저 나가면 아직 없는 표를 찾아 500 이 난다.
param([switch]$Apply)

$ErrorActionPreference = "Stop"
# 이 스크립트가 있는 폴더의 부모 = 에듀싱크 (어디서 실행하든 같은 곳을 본다)
Set-Location (Split-Path $PSScriptRoot -Parent)

$CFG    = "workers/site-renderer/wrangler.toml"
$DB     = "eduthink-db"
$WORKER = "eduthink-site-renderer"   # 배포 대상. olmanama 이 아니다 (07-21 오배포 사고)
$TABLES = "'store_items','reward_orders','child_mode_config','reactions','mission_verifications','parent_mission_templates'"

function Say($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function D1 { npx wrangler d1 execute $DB --remote --config $CFG @args }

Say "0. 지금 상태 (아직 안 올렸으면 비어 있는 게 정상)"
D1 --command "SELECT name FROM sqlite_master WHERE type='table' AND name IN ($TABLES)"

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

Say "A-1. 표·인덱스 (추가만 한다)"
D1 --file scripts/migrate_reward_2026-08-07.sql

Say "A-2. PIN 시도 제한 (A-1 이 child_mode_config 를 만든 뒤라야 한다)"
D1 --file scripts/migrate_pin_2026-08-07.sql

Say "A-3. 확인 - 6 이 나와야 한다"
D1 --command "SELECT COUNT(*) AS tables FROM sqlite_master WHERE type='table' AND name IN ($TABLES)"

Say "B. 워커 배포"
# --config 를 빼면 엉뚱한 워커로 나간다 (올마나마에서 실제로 났던 사고)
$out = npx wrangler deploy --config $CFG 2>&1 | Tee-Object -Variable shown
$shown | ForEach-Object { Write-Host $_ }
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
