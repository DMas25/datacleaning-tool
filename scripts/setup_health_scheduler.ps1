# Registers health_check_local.py as a Windows Task Scheduler job.
# Runs every 15 minutes while you are logged in.
# Run this script once from an elevated (Admin) PowerShell prompt.

$TaskName   = "ColtraDataAi - Local Health Check"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot    = Split-Path -Parent $ScriptDir
$PythonExe  = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $PythonExe) {
    Write-Error "Python not found on PATH. Install Python and re-run."
    exit 1
}

$Script     = Join-Path $ScriptDir "health_check_local.py"
$LogDir     = Join-Path $AppRoot "logs"
$LogFile    = Join-Path $LogDir "health_scheduler.log"

# Remove existing task with the same name if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action  = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$Script`"" `
    -WorkingDirectory $AppRoot

# Every 15 minutes, indefinitely
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Checks localhost:8501 every 15 minutes and logs to $LogFile" `
    -Force | Out-Null

Write-Host "Task '$TaskName' registered successfully."
Write-Host "Python:  $PythonExe"
Write-Host "Script:  $Script"
Write-Host "Log dir: $LogDir"
Write-Host ""
Write-Host "To view results: Get-Content '$LogDir\health_local.log' -Tail 20"
Write-Host "To remove task:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
