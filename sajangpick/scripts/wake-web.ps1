# Wake-web macro (회신03 §1).
# Finds the Claude web window, pastes "확인" and presses Enter — one-key wake for the web brain.
#
# Guard: does nothing unless WAKE.md says WEB_NEEDED (prevents pointless wakes).
# Korean text is sent via clipboard+Ctrl+V because SendKeys cannot type Hangul reliably.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$wake = Join-Path $root 'WAKE.md'

# 1) Guard — only fire when the web actually needs waking.
#    --force skips the guard (testing, or waking before the 20-min timer).
$force = $args -contains '--force'
if (-not (Test-Path $wake)) { Write-Host 'WAKE.md 없음 — 종료'; exit 0 }
$webNeeded = (Select-String -Path $wake -Pattern '^WEB_NEEDED:\s*(.+)$').Matches.Groups[1].Value.Trim()
if ((-not $webNeeded -or $webNeeded -eq '-') -and -not $force) {
    Write-Host '깨울 것 없음 (WEB_NEEDED: -)'; exit 0
}
if (-not $webNeeded -or $webNeeded -eq '-') { $webNeeded = '04' }

# 2) Find a Claude window (browser tab title or desktop app)
Add-Type -AssemblyName Microsoft.VisualBasic
Add-Type -AssemblyName System.Windows.Forms

$target = Get-Process | Where-Object { $_.MainWindowTitle -match 'Claude' } | Select-Object -First 1
if (-not $target) {
    Write-Host 'Claude 창을 찾지 못함 — 브라우저에서 claude.ai 탭을 연 뒤 다시 실행'
    exit 1
}

# 3) Focus it, paste the wake message, press Enter
Set-Clipboard -Value ("진행상황 봐줘 (요청" + $webNeeded + " 대기중)")
[Microsoft.VisualBasic.Interaction]::AppActivate($target.Id)
Start-Sleep -Milliseconds 600
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
Write-Host ("깨움 전송 완료 → " + $target.MainWindowTitle)
