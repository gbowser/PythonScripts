param(
    [switch]$DryRun,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$BatchScript = Join-Path $ForegroundDir "apply_optimised_mtobjects_all_galaxies.py"

$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$RunName = "20260723_195742"
$BestJson = Join-Path $Root "mtobjects toy optimisation\$RunName\mtobjects_parameter_optimisation_best.json"
$BatchOut = Join-Path $Root "mtobjects all galaxy batch\mtobjects_toy_object_$RunName"
$BatchLog = Join-Path $BatchOut "terminal_log.txt"
$MasterLog = Join-Path $ForegroundDir ("run_logs\corrected_mtobjects_toy_batch_only_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-MasterLog {
    param([string]$Message)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $MasterLog) | Out-Null
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line
}

Write-MasterLog "Corrected MTObjects toy-object batch-only runner started."
Write-MasterLog "Best JSON: $BestJson"
Write-MasterLog "Output: $BatchOut"

if ($DryRun) {
    Write-MasterLog "Dry run requested; no batch launched."
    exit 0
}

if (-not (Test-Path $BestJson)) {
    Write-MasterLog "Missing best JSON."
    exit 1
}

New-Item -ItemType Directory -Force -Path $BatchOut | Out-Null
& $Python $BatchScript `
    --best-json $BestJson `
    --source toy-object `
    --run-label "MTObjects Toy Object capped 15pct $RunName" `
    --output-dir $BatchOut 2>&1 | Tee-Object -FilePath $BatchLog -Append

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-MasterLog "Corrected MTObjects toy-object batch finished successfully."
}
else {
    Write-MasterLog "Corrected MTObjects toy-object batch failed exit_code=$exitCode."
}
exit $exitCode
