param(
    [switch]$DryRun,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$SEPBatch = Join-Path $ForegroundDir "Batch tools\batch_sep_all_galaxies.py"
$Compositor = Join-Path $ForegroundDir "Utilities\make_all_method_galaxy_comparison_pngs.py"

$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$LogRoot = Join-Path $ForegroundDir "run_logs"
$MasterLog = Join-Path $LogRoot ("wrapped_sep_batches_and_comparison_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

$SpikeRun = "20260724_164739"
$ToyRun = "20260724_163302"
$SpikeBest = Join-Path $Root "sep spike optimisation\$SpikeRun\sep_spike_optimisation_best.json"
$ToyBest = Join-Path $Root "sep toy optimisation\$ToyRun\sep_toy_object_optimisation_best.json"

$SEPSpikeOut = Join-Path $Root ("SEP all galaxy batch\sep_spike_gate_capped_wrapped_nofits_$SpikeRun")
$SEPToyOut = Join-Path $Root ("SEP all galaxy batch\sep_toy_object_capped_wrapped_nofits_$ToyRun")
$ComparisonOut = Join-Path $Root ("all method galaxy comparison panels\all_method_comparison_capped_sep_spike_wrapped_nofits_$SpikeRun")

$MTObjectsSpikeSummary = Join-Path $Root "mtobjects all galaxy batch\mtobjects_spike_gate_20260722_103506\mtobjects_optimised_apply_summary.csv"
$MTObjectsToySummary = Join-Path $Root "mtobjects all galaxy batch\mtobjects_toy_object_20260723_195742\mtobjects_optimised_apply_summary.csv"
$SEPSpikeSummary = Join-Path $SEPSpikeOut "sep_optimised_apply_summary.csv"
$SEPToySummary = Join-Path $SEPToyOut "sep_optimised_apply_summary.csv"

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

Write-MasterLog "Wrapped SEP report rerun and comparison started."
Write-MasterLog "SEP Spike best JSON: $SpikeBest"
Write-MasterLog "SEP Toy best JSON: $ToyBest"

foreach ($path in @($SpikeBest, $ToyBest, $MTObjectsSpikeSummary, $MTObjectsToySummary)) {
    if (-not (Test-Path $path)) {
        Write-MasterLog "Missing required input: $path"
        exit 1
    }
}

$failures = 0

$spikeExit = Run-Step `
    -Name "Wrapped SEP Spike Gate all-galaxy batch" `
    -LogPath (Join-Path $SEPSpikeOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatch,
        "--best-json", $SpikeBest,
        "--source", "spike-gate",
        "--run-label", "Wrapped capped SEP Spike Gate $SpikeRun",
        "--output-dir", $SEPSpikeOut,
        "--require-best-json"
    )
if ($spikeExit -ne 0) { $failures += 1 }

$toyExit = Run-Step `
    -Name "Wrapped SEP Toy Object all-galaxy batch" `
    -LogPath (Join-Path $SEPToyOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatch,
        "--best-json", $ToyBest,
        "--source", "toy-object",
        "--run-label", "Wrapped SEP Toy Object $ToyRun",
        "--output-dir", $SEPToyOut,
        "--require-best-json"
    )
if ($toyExit -ne 0) { $failures += 1 }

if ($DryRun) {
    Write-MasterLog "Dry run complete."
    exit 0
}

if ($failures -gt 0) {
    Write-MasterLog "Skipping comparison because $failures SEP batch step(s) failed."
    exit 1
}

foreach ($path in @($SEPSpikeSummary, $SEPToySummary)) {
    if (-not (Test-Path $path)) {
        Write-MasterLog "Missing required SEP summary: $path"
        exit 1
    }
}

$comparisonExit = Run-Step `
    -Name "Wrapped all-method comparison panels" `
    -LogPath (Join-Path $ComparisonOut "terminal_log.txt") `
    -Command @(
        $Python,
        $Compositor,
        "--mtobjects-spike-summary", $MTObjectsSpikeSummary,
        "--mtobjects-toy-summary", $MTObjectsToySummary,
        "--sep-spike-summary", $SEPSpikeSummary,
        "--sep-toy-summary", $SEPToySummary,
        "--output-dir", $ComparisonOut,
        "--require-all"
    )
if ($comparisonExit -ne 0) {
    Write-MasterLog "Wrapped all-method comparison failed."
    exit $comparisonExit
}

Write-MasterLog "Wrapped SEP report rerun and comparison finished successfully."
