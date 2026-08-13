# eolmanama daily refresh + deploy (2026-07-19, logging fix 2026-07-20)
# Task Scheduler task (eolmanama daily refresh) runs this at 07:00 daily.
# NOTE: keep this file ASCII-only in code paths — PS5.1 reads BOM-less UTF-8 as ANSI and
#       non-ASCII inside strings breaks parsing (happened 2026-07-19).
#
# 2026-07-20 fix — why the 07:00 run died silently:
#   PS5.1 wraps native-exe stderr into ErrorRecords when redirected with *>>.
#   With $ErrorActionPreference="Stop" that becomes a TERMINATING error, so the
#   script died before writing its FAIL line (log ended mid-step, cause unknown).
#   Fix: route each step through cmd.exe so redirection happens outside PowerShell.
#   Also: on failure, drop a marker file on the Desktop so the user actually notices.
#
# Pipeline: collect prices -> recompute -> regenerate all
#           -> healthcheck (GATE: if it fails, DO NOT deploy) -> wrangler deploy
# Log: logs\refresh_YYYY-MM-DD.log
$ErrorActionPreference = "Continue"
$BASE = Split-Path -Parent $PSScriptRoot
$LOGDIR = Join-Path $BASE "logs"
if (-not (Test-Path $LOGDIR)) { New-Item -ItemType Directory -Path $LOGDIR | Out-Null }
$STAMP = Get-Date -Format "yyyy-MM-dd"
$LOG = Join-Path $LOGDIR ("refresh_" + $STAMP + ".log")
$env:PYTHONIOENCODING = "utf-8"
Set-Location $BASE

function Fail-Notify($name) {
    Add-Content $LOG ("FAIL: " + $name + " (exit " + $LASTEXITCODE + ") - aborting, NOT deploying")
    $desktop = [Environment]::GetFolderPath("Desktop")
    $marker = Join-Path $desktop ("eolmanama_REFRESH_FAILED_" + $STAMP + ".txt")
    $tail = Get-Content $LOG -Tail 40
    Set-Content -Path $marker -Value (@("Refresh FAILED at step: " + $name, "Log: " + $LOG, "", "--- last 40 log lines ---") + $tail) -Encoding UTF8
    exit 1
}

function Step($name, $cmdline) {
    Add-Content $LOG ("=== " + $name + " (" + (Get-Date -Format "HH:mm:ss") + ") ===")
    # cmd.exe does the redirection -> PS never sees native stderr, no ErrorRecord wrapping.
    & cmd /c ($cmdline + " >> """ + $LOG + """ 2>&1")
    if ($LASTEXITCODE -ne 0) { Fail-Notify $name }
}

Step "collect_prices (KAMIS/ekape)" "python scripts\collect_prices.py"
Step "collect_chamga (weekly)"      "python scripts\collect_chamga.py"
Step "collect_ekape (livestock)"    "python scripts\collect_ekape.py"
Step "collect_kamis_all (KAMIS)"    "python scripts\collect_kamis_all.py"
Step "collect_at_auction (auction)" "python scripts\collect_at_auction.py"
Step "collect_customs_meat (import)" "python scripts\collect_customs_meat.py"
Step "compute_line_costs"           "python scripts\compute_line_costs.py"
Step "gen_preview_html"             "python scripts\gen_preview_html.py"
Step "gen_dishes"                   "python scripts\gen_dishes.py"
Step "gen_prices_page"              "python scripts\gen_prices_page.py"
Step "gen_sitemap"                  "python scripts\gen_sitemap.py"
Step "build_dist"                   "python scripts\build_dist.py"
Step "healthcheck (deploy gate)"    "python scripts\healthcheck.py"

# 2026-08-14 fix: deploy via scripts\deploy.py (file-count guard + --config + live check).
# Bare "npx wrangler deploy" picked the ROOT wrangler.jsonc even when run from
# workers\site-renderer (verified 2026-07-24) -> deployed to a domainless worker.
Step "deploy (guarded)" "python scripts\deploy.py"
Add-Content $LOG ("OK: refresh + deploy done " + (Get-Date -Format "HH:mm:ss"))
# success: remove any stale failure marker from today
$desktop = [Environment]::GetFolderPath("Desktop")
$marker = Join-Path $desktop ("eolmanama_REFRESH_FAILED_" + $STAMP + ".txt")
if (Test-Path $marker) { Remove-Item $marker -Force }
