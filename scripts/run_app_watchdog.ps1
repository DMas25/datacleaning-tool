# Keeps the Streamlit app alive: restarts it automatically if it crashes or is closed.
#
# Crash-loop intelligence:
#   - 3+ restarts within 5 minutes  -> fire an internal alert (notify_crash_loop.py)
#   - 5+ restarts within 5 minutes  -> also trip safe mode (writes the same flag
#                                       file core/safe_mode.py reads) so the app
#                                       comes back up in minimal mode instead of
#                                       re-running the code path that's crashing it
#   - restart delay backs off progressively (5s, 10s, 20s, 40s, capped at 60s)
#     instead of hammering a broken process every 5 seconds, and resets back to
#     5s once a run survives more than 60s (a real recovery, not a fluke)
$projectDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectDir ".venv\Scripts\python.exe"
$logDir = Join-Path $projectDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "streamlit_watchdog.log"
$notifyScript = Join-Path $PSScriptRoot "notify_crash_loop.py"
$safeModeFlag = Join-Path $logDir ".safe_mode.json"

Set-Location $projectDir

$crashLoopWindowSeconds = 300
$alertThreshold = 3
$safeModeThreshold = 5
$recentRestarts = New-Object System.Collections.Generic.List[datetime]

$backoffSeconds = 5
$maxBackoffSeconds = 60
$stableRunSeconds = 60   # a run lasting longer than this counts as "recovered"

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$timestamp] Starting Streamlit app..."

    $runStart = Get-Date
    & $python -m streamlit run app.py --server.port 8501 --server.headless true *>> $logFile
    $exitCode = $LASTEXITCODE
    $runDuration = (Get-Date) - $runStart
    $exitTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    $now = Get-Date
    $recentRestarts.Add($now)
    $recentRestarts.RemoveAll({ param($t) ($now - $t).TotalSeconds -gt $crashLoopWindowSeconds }) | Out-Null

    if ($runDuration.TotalSeconds -ge $stableRunSeconds) {
        $backoffSeconds = 5
    } else {
        $backoffSeconds = [Math]::Min($backoffSeconds * 2, $maxBackoffSeconds)
    }

    Add-Content -Path $logFile -Value "[$exitTimestamp] Streamlit exited (code $exitCode) after $([Math]::Round($runDuration.TotalSeconds, 1))s. Restarting in ${backoffSeconds}s..."

    if ($recentRestarts.Count -ge $alertThreshold) {
        Add-Content -Path $logFile -Value "[$exitTimestamp] Crash loop detected ($($recentRestarts.Count) restarts in ${crashLoopWindowSeconds}s) - sending alert."
        & $python $notifyScript $recentRestarts.Count *>> $logFile
    }

    if ($recentRestarts.Count -ge $safeModeThreshold) {
        Add-Content -Path $logFile -Value "[$exitTimestamp] $($recentRestarts.Count) restarts in ${crashLoopWindowSeconds}s - tripping safe mode."
        $safeModePayload = @{
            active       = $true
            activated_at = [double](Get-Date -UFormat %s)
            reason       = "watchdog: $($recentRestarts.Count) restarts in ${crashLoopWindowSeconds}s"
        }
        $safeModePayload | ConvertTo-Json | Set-Content -Path $safeModeFlag -Encoding utf8
    }

    Start-Sleep -Seconds $backoffSeconds
}
