param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$Optimiser = Join-Path $ForegroundDir "optimise_sep_spike_gate_parameters.py"
$Batch = Join-Path $ForegroundDir "batch_sep_all_galaxies.py"

$Root = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$LogRoot = Join-Path $ForegroundDir "run_logs"
$MasterLog = Join-Path $LogRoot ("balanced_bridge_sep_spike_optimisation_and_batch_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-MasterLog {
    param([string]$Message)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $MasterLog) | Out-Null
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line
}

function Run-Step {
    param(
        [string]$Name,
        [string]$LogPath,
        [string[]]$Command
    )
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null
    Write-MasterLog "START $Name"
    Write-MasterLog ("COMMAND " + ($Command -join " "))
    if ($DryRun) {
        Write-MasterLog "DRY RUN $Name"
        return 0
    }

    $exe = $Command[0]
    $args = @()
    if ($Command.Count -gt 1) {
        $args = $Command[1..($Command.Count - 1)]
    }

    & $exe @args 2>&1 | Tee-Object -FilePath $LogPath -Append | Out-Host
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-MasterLog "DONE $Name"
    }
    else {
        Write-MasterLog "FAILED $Name exit_code=$exitCode"
    }
    return $exitCode
}

function Latest-RunDir {
    param(
        [string]$Parent,
        [string]$BestName
    )
    Get-ChildItem -Path $Parent -Directory |
        Where-Object { $_.Name -notmatch "\.bad_" -and (Test-Path (Join-Path $_.FullName $BestName)) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

Write-MasterLog "Balanced-bridge SEP Spike Gate optimisation and full-galaxy batch started."
Write-MasterLog "Recipe: global SEP parameters, restored spike coverage pressure, moderate bridge-span control."

$optimiseLog = Join-Path $LogRoot ("balanced_bridge_sep_spike_optimisation_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$optimiseExit = Run-Step `
    -Name "Balanced-bridge SEP Spike Gate optimisation" `
    -LogPath $optimiseLog `
    -Command @(
        $Python,
        $Optimiser,
        "--max-images", "20",
        "--initial-points", "12",
        "--max-iter", "48",
        "--detect-on", "residual",
        "--max-masked-fraction", "0.08",
        "--data-loss-penalty", "7.0",
        "--profile-loss-penalty", "16.0",
        "--mean-spike-coverage-weight", "38.0",
        "--min-spike-coverage-weight", "6.0",
        "--max-profile-affected-fraction", "0.22",
        "--max-non-spike-profile-fraction", "0.12",
        "--max-bridge-span-arcsec", "18.0",
        "--bridge-span-penalty", "0.03",
        "--max-area-search", "600",
        "--progress-galaxies"
    )

if ($optimiseExit -ne 0) {
    Write-MasterLog "Stopping because balanced-bridge SEP Spike Gate optimisation failed."
    exit $optimiseExit
}

if ($DryRun) {
    Write-MasterLog "Dry run complete."
    exit 0
}

$runDir = Latest-RunDir -Parent (Join-Path $Root "sep spike optimisation") -BestName "sep_spike_optimisation_best.json"
if (-not $runDir) {
    Write-MasterLog "Could not find balanced-bridge SEP Spike Gate best JSON."
    exit 1
}

$bestJson = Join-Path $runDir.FullName "sep_spike_optimisation_best.json"
$batchOut = Join-Path $Root ("SEP all galaxy batch\sep_spike_gate_balanced_bridge_{0}" -f $runDir.Name)
Write-MasterLog "Using balanced-bridge SEP Spike Gate best JSON: $bestJson"
Write-MasterLog "Batch output: $batchOut"

$batchExit = Run-Step `
    -Name "Balanced-bridge SEP Spike Gate all-galaxy batch" `
    -LogPath (Join-Path $batchOut "terminal_log.txt") `
    -Command @(
        $Python,
        $Batch,
        "--best-json", $bestJson,
        "--source", "spike-gate",
        "--run-label", ("Balanced-bridge SEP Spike Gate {0}" -f $runDir.Name),
        "--output-dir", $batchOut,
        "--require-best-json",
        "--replace-summary"
    )

if ($batchExit -ne 0) {
    Write-MasterLog "Balanced-bridge SEP Spike Gate batch failed."
    exit $batchExit
}

Write-MasterLog "Balanced-bridge SEP Spike Gate optimisation and batch finished successfully."
