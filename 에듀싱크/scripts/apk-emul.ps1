# APK 빌드 + 에뮬 설치 — 한 줄로 (지시서 0807 배포 C 단계)
#   powershell -ExecutionPolicy Bypass -File scripts\apk-emul.ps1
#
# 앞서 A(DB)·B(워커)가 끝나 있어야 한다. 안 그러면 화면은 새것인데 서버가 500 을 낸다.
param([switch]$SkipBuild)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Say($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Die($m) { Write-Host "`n[!] $m" -ForegroundColor Red; exit 1 }

# ── 0. 화면 파일이 APK 자산과 같은지 (이게 어긋나면 «옛 화면»이 나온다) ──
Say "0. 화면 파일 확인"
$pairs = @(
  @{ a = "app\www\app.js";    b = "app\android\app\src\main\assets\public\app.js" },
  @{ a = "app\www\style.css"; b = "app\android\app\src\main\assets\public\style.css" }
)
foreach ($p in $pairs) {
  if (-not (Test-Path $p.b)) { Die "$($p.b) 가 없습니다" }
  $h1 = (Get-FileHash $p.a).Hash; $h2 = (Get-FileHash $p.b).Hash
  if ($h1 -ne $h2) {
    Write-Host "  자산이 낡았습니다 - 복사합니다: $($p.b)" -ForegroundColor Yellow
    Copy-Item $p.a $p.b -Force
  } else { Write-Host "  OK  $(Split-Path $p.a -Leaf)" }
}
Copy-Item app\www\themes\* app\android\app\src\main\assets\public\themes\ -Force -ErrorAction SilentlyContinue
Copy-Item app\www\fonts\*  app\android\app\src\main\assets\public\fonts\  -Force -ErrorAction SilentlyContinue

# ── 1. 빌드 ──
if (-not $SkipBuild) {
  Say "1. APK 빌드"
  # 기본 Java 8 로는 실패한다 - Android Studio 가 들고 있는 JBR 을 쓴다
  $jbr = "C:\Program Files\Android\Android Studio\jbr"
  if (-not (Test-Path $jbr)) { Die "Android Studio JBR 을 못 찾았습니다: $jbr" }
  $env:JAVA_HOME = $jbr
  Push-Location app\android
  try { .\gradlew.bat assembleDebug } finally { Pop-Location }
}

# ── 2. APK 찾기 ──
# 프로젝트 안이 아니라 밖에 떨어진다 (android/build.gradle 29행이 buildDir 를 밖으로 뺐다)
Say "2. APK 찾기"
$apk = Get-ChildItem "$env:LOCALAPPDATA\eduthink-build" -Recurse -Filter "app-debug.apk" -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $apk) {
  $apk = Get-ChildItem "app\android" -Recurse -Filter "app-debug.apk" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if (-not $apk) { Die "app-debug.apk 를 못 찾았습니다. 빌드가 실패했는지 위 로그를 보세요." }
Write-Host "  $($apk.FullName)"
Write-Host "  빌드 시각 $($apk.LastWriteTime)  크기 $([math]::Round($apk.Length/1MB,1))MB"

# ── 3. 에뮬 ──
Say "3. 에뮬 확인"
# ⚠ 윈도우 adb.exe 는 줄끝이 CRLF 다. "`n" 으로만 자르면 각 줄 끝에 `r 이 남고,
#   정규식의 $ 는 `r 앞에서 안 맞는다 → 에뮬이 붙어 있어도 «기기 없음» 으로 읽힌다.
#   실제로 여기서 막히면 «에뮬 설정이 잘못됐나» 를 한참 뒤진다. 줄끝부터 털고 본다.
$devs = (adb devices) -split "\r?\n" | ForEach-Object { $_.TrimEnd() } |
        Where-Object { $_ -match "\tdevice$" }
if (-not $devs) {
  Write-Host @"
  기기가 안 보입니다. LDPlayer 에서:
    설정 - 기타설정 - «ADB 디버깅» 을 «로컬 연결 열기» 로
  그래도 안 보이면 포트로 직접:
    adb connect 127.0.0.1:5555      (LDPlayer 는 5555 / 5557 / 62001 중 하나)
"@ -ForegroundColor Yellow
  Die "에뮬 연결 후 다시 실행하세요 (빌드는 끝났으니 -SkipBuild 를 붙이면 빠릅니다)"
}
Write-Host "  $($devs -join ', ')"

Say "4. 설치"
adb install -r $apk.FullName
# 설치가 실패했는데 앱을 띄우면 «옛 화면» 이 그대로 뜬다 - 그걸 새 화면으로 착각하면
# 8항목 점검이 통째로 헛것이 된다. 여기서 끊는다.
if ($LASTEXITCODE -ne 0) {
  Write-Host @"
  설치 실패입니다. 흔한 원인:
    INSTALL_FAILED_UPDATE_INCOMPATIBLE  = 서명이 다른 판이 이미 깔려 있다
        adb uninstall com.eduthink.app   후 다시 실행 (⚠ 앱 데이터가 지워집니다)
    INSTALL_FAILED_VERSION_DOWNGRADE    = 기기에 더 새 판이 깔려 있다
"@ -ForegroundColor Yellow
  Die "설치가 안 됐으니 8항목 점검은 옛 화면을 보게 됩니다. 위를 먼저 해결하세요."
}
adb shell monkey -p com.eduthink.app -c android.intent.category.LAUNCHER 1 | Out-Null

Write-Host @"


[OK] 설치·실행 완료. 이제 8항목을 눈으로 봅니다 (docs\배포점검-0807-보상시스템.md 맨 아래)

  1 드로어 - 별도장 상점      빈 진열대 + «바꿀 것 올리기»
  2 보상 올리기               앱을 껐다 켜도 남는가 (= 서버에 갔다는 뜻)
  3 아이 화면 - 별의 길 - 상점  별 모자란 카드가 흐린가
  4 ★로 바꾸기                별이 줄고 티켓 «기다리는 중»
  5 부모 미션 화면            «티켓 바꿔주기» - [바꿔줬어요]
  6 리롤                      안 한 것만 바뀌고, **두 번째는 막히는가**
  7 아이 모드                 PIN 정하기 - 설정 안 보임 - **5번 틀리면 잠기는가**
  8 칭찬 스티커               눌리고 토스트

  6·7 은 «되는지»가 아니라 «막히는지»를 봅니다.
  화면 로그가 필요하면:  adb logcat -s chromium:I
"@ -ForegroundColor Green
