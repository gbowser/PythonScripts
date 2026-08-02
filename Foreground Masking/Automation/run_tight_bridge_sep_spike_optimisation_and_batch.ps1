param(
    [switch]$DryRun,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$Optimiser = Join-Path $ForegroundDir "Optimisation\optimise_spike_gate_SEP.py"
$Batch = Join-Path $ForegroundDir "Batch tools\batch_sep_all_galaxies.py"

$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$LogRoot = Join-Path $ForegroundDir "run_logs"
$MasterLog = Join-Path $LogRoot ("tight_bridge_sep_spike_optimisation_and_batch_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

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

Write-MasterLog "Tight-bridge SEP Spike Gate optimisation and full-galaxy batch started."
Write-MasterLog "Recipe: global SEP parameters, bridge-span cap, lower max-area search, no cleaned FITS."

$optimiseLog = Join-Path $LogRoot ("tight_bridge_sep_spike_optimisation_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$optimiseExit = Run-Step `
    -Name "Tight-bridge SEP Spike Gate optimisation" `
    -LogPath $optimiseLog `
    -Command @(
        $Python,
        $Optimiser,
        "--pc", $PC,
        "--max-images", "20",
        "--initial-points", "12",
        "--max-iter", "48",
        "--detect-on", "residual",
        "--max-masked-fraction", "0.08",
        "--data-loss-penalty", "8.0",
        "--profile-loss-penalty", "22.0",
        "--mean-spike-coverage-weight", "22.0",
        "--min-spike-coverage-weight", "2.0",
        "--max-profile-affected-fraction", "0.16",
        "--max-non-spike-profile-fraction", "0.08",
        "--max-bridge-span-arcsec", "13.0",
        "--bridge-span-penalty", "0.08",
        "--max-area-search", "250",
        "--progress-galaxies"
    )

if ($optimiseExit -ne 0) {
    Write-MasterLog "Stopping because tight-bridge SEP Spike Gate optimisation failed."
    exit $optimiseExit
}

if ($DryRun) {
    Write-MasterLog "Dry run complete."
    exit 0
}

$runDir = Latest-RunDir -Parent (Join-Path $Root "sep spike optimisation") -BestName "sep_spike_optimisation_best.json"
if (-not $runDir) {
    Write-MasterLog "Could not find tight-bridge SEP Spike Gate best JSON."
    exit 1
}

$bestJson = Join-Path $runDir.FullName "sep_spike_optimisation_best.json"
$batchOut = Join-Path $Root ("SEP all galaxy batch\sep_spike_gate_tight_bridge_{0}" -f $runDir.Name)
Write-MasterLog "Using tight-bridge SEP Spike Gate best JSON: $bestJson"
Write-MasterLog "Batch output: $batchOut"

$batchExit = Run-Step `
    -Name "Tight-bridge SEP Spike Gate all-galaxy batch" `
    -LogPath (Join-Path $batchOut "terminal_log.txt") `
    -Command @(
        $Python,
        $Batch,
        "--pc", $PC,
        "--best-json", $bestJson,
        "--source", "spike-gate",
        "--run-label", ("Tight-bridge SEP Spike Gate {0}" -f $runDir.Name),
        "--output-dir", $batchOut,
        "--require-best-json",
        "--replace-summary"
    )

if ($batchExit -ne 0) {
    Write-MasterLog "Tight-bridge SEP Spike Gate batch failed."
    exit $batchExit
}

Write-MasterLog "Tight-bridge SEP Spike Gate optimisation and batch finished successfully."

