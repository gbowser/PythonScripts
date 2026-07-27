param(
    [switch]$DryRun,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$MTObjectsBatchScript = Join-Path $ForegroundDir "apply_optimised_mtobjects_all_galaxies.py"
$SEPBatchScript = Join-Path $ForegroundDir "batch_sep_all_galaxies.py"

$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$BatchRoot = Join-Path $Root "all galaxy batch scheduled run logs"
$MasterLog = Join-Path $BatchRoot ("run_all_missing_all_galaxy_batches_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

$MTObjectsSpikeBest = Join-Path $Root "mtobjects spike optimisation\20260719_175031\mtobjects_spike_optimisation_best.json"
$MTObjectsToyBest = Join-Path $Root "mtobjects toy optimisation\20260722_141659\mtobjects_parameter_optimisation_best.json"
$SEPSpikeBest = Join-Path $Root "sep spike optimisation\20260719_183144\sep_spike_optimisation_best.json"
$SEPToyBest = Join-Path $Root "sep toy optimisation\20260722_141659\sep_toy_object_optimisation_best.json"

$MTObjectsSpikeOut = Join-Path $Root "mtobjects all galaxy batch\mtobjects_spike_gate_20260722_103506"
$MTObjectsToyOut = Join-Path $Root "mtobjects all galaxy batch\mtobjects_toy_object_20260722_141659"
$SEPSpikeOut = Join-Path $Root "SEP all galaxy batch\sep_spike_gate_20260719_183144"
$SEPToyOut = Join-Path $Root "SEP all galaxy batch\sep_toy_object_20260722_141659"

$Failures = 0

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
        return
    }

    $exe = $Command[0]
    $args = @()
    if ($Command.Count -gt 1) {
        $args = $Command[1..($Command.Count - 1)]
    }
    & $exe @args 2>&1 | Tee-Object -FilePath $LogPath -Append
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-MasterLog "DONE $Name"
    }
    else {
        $script:Failures += 1
        Write-MasterLog "FAILED $Name exit_code=$exitCode"
    }
}

Write-MasterLog "All missing all-galaxy batch runner started."
Write-MasterLog "Master log: $MasterLog"

Run-Step `
    -Name "MTObjects Spike Gate resume" `
    -LogPath (Join-Path $MTObjectsSpikeOut "terminal_log_resume_20260723.txt") `
    -Command @(
        $Python,
        $MTObjectsBatchScript,
        "--best-json", $MTObjectsSpikeBest,
        "--source", "spike-gate",
        "--run-label", "MTObjects Spike Gate best 20260719_175031",
        "--resume-output-dir", $MTObjectsSpikeOut
    )

Run-Step `
    -Name "MTObjects Toy Object" `
    -LogPath (Join-Path $MTObjectsToyOut "terminal_log.txt") `
    -Command @(
        $Python,
        $MTObjectsBatchScript,
        "--best-json", $MTObjectsToyBest,
        "--source", "toy-object",
        "--run-label", "MTObjects Toy Object best 20260722_141659",
        "--output-dir", $MTObjectsToyOut
    )

Run-Step `
    -Name "SEP Spike Gate" `
    -LogPath (Join-Path $SEPSpikeOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatchScript,
        "--best-json", $SEPSpikeBest,
        "--source", "spike-gate",
        "--run-label", "SEP Spike Gate best 20260719_183144",
        "--output-dir", $SEPSpikeOut,
        "--require-best-json"
    )

Run-Step `
    -Name "SEP Toy Object" `
    -LogPath (Join-Path $SEPToyOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatchScript,
        "--best-json", $SEPToyBest,
        "--source", "toy-object",
        "--run-label", "SEP Toy Object best 20260722_141659",
        "--output-dir", $SEPToyOut,
        "--require-best-json"
    )

if ($Failures -eq 0) {
    Write-MasterLog "All requested all-galaxy batch jobs finished successfully."
    exit 0
}

Write-MasterLog "Finished with $Failures failed step(s)."
exit 1
