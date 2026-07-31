$ErrorActionPreference = 'SilentlyContinue'

$runLog = 'C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\run_logs\four_batches_then_compositor_20260730_192147.log'
$toyOutput = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects optimised foreground removal\toy-object\20260730_215831'

while ($true) {
    Clear-Host
    Write-Host (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    Write-Host ''
    Write-Host 'Azure VM: deallocated (results already downloaded; no compute charge accruing)'
    Write-Host ''
    Write-Host 'Desktop all-galaxy pipeline:'

    $runner = Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -like '*run_four_batches_then_compositor_visible.ps1*' -and
        $_.CommandLine -notlike '*watch_four_batches_progress.ps1*'
    }
    if ($runner) {
        Write-Host "  Pipeline process: running (PID $($runner[0].ProcessId))"
    } else {
        Write-Host '  Pipeline process: not running'
    }

    if (Test-Path -LiteralPath $toyOutput) {
        $completed = (Get-ChildItem -LiteralPath $toyOutput -Filter '*.png' -File).Count
        Write-Host "  MTObjects toy-object galaxies: $completed / 182"
    } else {
        Write-Host '  MTObjects toy-object output folder not created yet'
    }

    Write-Host ''
    Write-Host 'Latest pipeline messages:'
    if (Test-Path -LiteralPath $runLog) {
        Get-Content -LiteralPath $runLog -Tail 14
    }

    Write-Host ''
    Write-Host 'This display refreshes every 10 seconds. Close it whenever you wish.'
    Start-Sleep -Seconds 10
}
