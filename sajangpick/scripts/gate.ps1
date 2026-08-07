# ══════════════════════════════════════════════════════════════
# gate.ps1 — 3분마다 도는 "값싼 문지기" (작업 스케줄러가 실행)
#
# 설계 의도 (2026-08-01 사용자 지시: 3분 주기):
#   3분마다 Claude를 깨우면 하루 480번이라 사용량이 감당이 안 된다.
#   그래서 이 스크립트가 값싼 조건 검사만 하고,
#   **진짜 할 일이 있을 때만** claude -p 를 부른다.
#
# 하는 일 세 가지
#   ① WEB_NEEDED 가 떠 있으면 → 에뮬(LDPlayer) 제미나이에 "check" 찔러넣기
#      (판단이 필요 없는 정형 작업이라 AI 없이 직접 한다)
#   ② 드라이브 최상단에 새 회신 구글문서가 생겼으면 → claude -p 호출해 회수시킴
#      (.gdoc 은 클라우드 전용이라 스크립트로는 내용을 못 읽는다. 드라이브 API 필요)
#   ③ 아무 일 없으면 조용히 종료 (비용 0)
# ══════════════════════════════════════════════════════════════

$ErrorActionPreference = 'Stop'

$HERE_SCRIPTS = Split-Path -Parent $MyInvocation.MyCommand.Path
$ROOT   = Split-Path -Parent $HERE_SCRIPTS
$COMM   = 'G:\내 드라이브\sajangpick'
$DRIVE  = 'G:\내 드라이브'
$ADB    = 'C:\LDPlayer\LDPlayer14\adb.exe'
$DEV    = '127.0.0.1:5555'
$STATE  = Join-Path $ROOT '.build\gate-state.json'
$LOG    = Join-Path $ROOT '.build\gate.log'

# 같은 요청을 계속 찌르지 않도록 하는 간격. 제미나이가 답할 시간을 준다.
$POKE_COOLDOWN_MIN = 10

New-Item -ItemType Directory -Force (Split-Path $LOG) | Out-Null
function Log($m) { "$(Get-Date -Format 'MM-dd HH:mm:ss')  $m" | Out-File $LOG -Append -Encoding utf8 }

# ── 상태 (마지막으로 찌른 요청번호·시각, 이미 회수한 문서) ──
$st = @{ lastPoked = ''; lastPokeAt = ''; collected = @() }
if (Test-Path $STATE) {
    try {
        $j = Get-Content $STATE -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($j.lastPoked)  { $st.lastPoked  = $j.lastPoked }
        if ($j.lastPokeAt) { $st.lastPokeAt = $j.lastPokeAt }
        if ($j.collected)  { $st.collected  = @($j.collected) }
    } catch { }
}
function Save-State { ($st | ConvertTo-Json -Depth 3) | Out-File $STATE -Encoding utf8 }

# 드라이브가 안 붙어 있으면(구글드라이브 종료 등) 아무것도 못 한다
if (-not (Test-Path $COMM)) { Log '드라이브 없음 — 종료'; exit 0 }

$work = $false

# ── ① 웹을 깨워야 하나 ───────────────────────────────────────
$wakeFile = Join-Path $COMM 'WAKE.md'
$webNeeded = '-'
if (Test-Path $wakeFile) {
    $m = Select-String -Path $wakeFile -Pattern '^WEB_NEEDED:\s*(.+)$'
    if ($m) { $webNeeded = $m.Matches.Groups[1].Value.Trim() }
}

if ($webNeeded -and $webNeeded -ne '-') {
    # 같은 번호를 쿨다운 안에 또 찌르지 않는다
    $recent = $false
    if ($st.lastPoked -eq $webNeeded -and $st.lastPokeAt) {
        try { $recent = ((Get-Date) - [datetime]$st.lastPokeAt).TotalMinutes -lt $POKE_COOLDOWN_MIN } catch { }
    }

    if (-not $recent) {
        # 에뮬이 살아있을 때만. adb 는 자주 끊기므로 매번 connect 한다.
        & $ADB connect $DEV *> $null
        $alive = (& $ADB -s $DEV shell echo ok 2>$null) -match 'ok'

        if ($alive) {
            # 제미나이 앱을 앞으로 (이미 떠 있으면 그대로 살아난다)
            & $ADB -s $DEV shell am start -n 'com.google.android.apps.bard/com.google.android.apps.bard.shellapp.BardEntryPointActivity' *> $null
            Start-Sleep -Seconds 6

            # ⚠ adb 는 한글을 못 친다. 신호어는 영문 'check' 로 고정.
            #    "check" 가 무슨 뜻인지는 제미나이 대화에 미리 일러둔 상태여야 한다.
            & $ADB -s $DEV shell input tap 450 1494      # 입력창
            Start-Sleep -Seconds 2
            & $ADB -s $DEV shell input text "check%srequest%s$webNeeded"
            Start-Sleep -Seconds 2
            & $ADB -s $DEV shell input keyevent 66       # Enter

            $st.lastPoked = $webNeeded
            $st.lastPokeAt = (Get-Date).ToString('o')
            Save-State
            Log "제미나이 깨움 — 요청$webNeeded"
        } else {
            Log "WEB_NEEDED=$webNeeded 인데 에뮬 응답 없음 — 건너뜀"
        }
    }
}

# ── ② 회수할 회신 문서가 생겼나 ──────────────────────────────
# 제미나이는 폴더 지정·.md 생성을 못 해서 최상단에 구글문서로 답을 쓴다.
# ⚠ 이름은 한글(회신NN)·영문(REPLYNN) 둘 다 받는다.
#    adb 가 한글을 못 쳐서 제미나이에겐 영문 이름으로 시키기 때문(2026-08-01).
# ⚠ 이름에 번호가 없는 문서도 있다 — 앱의 「Docs로 내보내기」로 뽑으면 이름이 답변 첫 줄이 된다.
#    그건 여기서 못 거르므로, 최상단 구글문서가 하나라도 늘면 일단 회수기를 돌린다.
#    번호는 collect_reply.py 가 이름 → 본문 순으로 알아서 찾는다(2026-08-02).
$docs = Get-ChildItem $DRIVE -File -Filter '*.gdoc' -ErrorAction SilentlyContinue
foreach ($d in $docs) {
    if ($st.collected -contains $d.Name) { continue }
    $work = $true
    Log "회수 대상 발견 — $($d.Name)"
}

# ── ③ 할 일이 있을 때만 Claude 호출 ──────────────────────────
if ($work) {
    # 회수는 판단이 없는 단순 작업이라 **AI를 부르지 않는다.**
    # 예전엔 claude -p 를 불렀는데 헤드리스에서 로그인이 안 돼 막혔고(2026-08-01),
    # 사용량도 들었다. 파이썬이 드라이브 API로 직접 가져오면 비용 0에 로그인도 안 풀린다.
    Log 'collect_reply.py 실행'
    try {
        $py = Join-Path $HERE_SCRIPTS 'collect_reply.py'
        # ⚠⚠ 절대 `2>&1` 을 붙이지 말 것 (2026-08-02 실제로 이것 때문에 회수가 통째로 멈춰 있었다).
        #    파이썬 3.9 는 google-auth 를 부를 때마다 FutureWarning 을 stderr 로 쏟는데,
        #    파워셸에서 native exe 의 stderr 를 2>&1 로 합치면 각 줄이 **ErrorRecord** 가 된다.
        #    이 스크립트는 $ErrorActionPreference='Stop' 이라 그게 곧바로 예외로 터진다.
        #    → 경고를 걸러내려고 만든 아래 필터는 실행조차 못 하고 catch 로 떨어졌다.
        #    stderr 는 그냥 흘려보낸다(작업 스케줄러가 삼킨다). 성패는 파일 존재로 판정한다.
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $raw = & python $py | Out-String
        $ErrorActionPreference = $prev
        Log "회수 결과: $($raw.Trim())"

        # ── 처리 표시 ──
        # ⚠ 예전엔 «이름에서 번호를 뽑아 그 .md 가 생겼는지»로 판정했다. 이제 못 쓴다.
        #    대상이 최상단 구글문서 전부라 기획서·리서치 같은 무관한 문서가 섞이고,
        #    그것들은 영영 «회수 실패»로 남아 매 주기 재시도를 유발한다(무한 루프).
        #
        #    판정 기준을 바꾼다: **회수기가 정상 종료했는지**로 본다.
        #    회수기는 번호를 이름→본문 순으로 스스로 찾고, 이미 있는 건 건너뛴다.
        #    그러니 한 번 정상으로 돌았으면 그 시점의 문서들은 다 훑은 것이다.
        #    회수기가 죽으면(출력 없음/예외) 아무것도 표시하지 않아 다음 주기에 다시 온다.
        if ($LASTEXITCODE -eq 0 -and $raw.Trim()) {
            foreach ($d in $docs) {
                if ($st.collected -notcontains $d.Name) { $st.collected += $d.Name }
            }
            Save-State
        } else {
            Log "회수기 비정상 종료 — 표시하지 않음. 다음 주기에 다시 시도"
        }

        # 회수했으면 신호판을 갱신해 CODE_NEEDED 에 올린다
        Push-Location $ROOT
        & node watcher.mjs --once *> $null
        Pop-Location
    } catch {
        Log "회수 실패: $($_.Exception.Message)"
    }
} else {
    Log "할 일 없음 (WEB_NEEDED=$webNeeded)"
}
