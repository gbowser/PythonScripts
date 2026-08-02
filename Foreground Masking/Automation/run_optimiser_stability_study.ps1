param(
    [string]$AdoptProcessIdsCsv = ""
)

$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$LogRoot = Join-Path $ForegroundDir "run_logs\stability_20260727"
$Python = (Get-Command python).Source
$StatusCsv = Join-Path $LogRoot "run_status.csv"
$MasterLog = Join-Path $LogRoot "stability_queue.log"

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $StatusCsv)) {
    "stage,name,seed,exit_code,finished_at" | Set-Content -LiteralPath $StatusCsv -Encoding utf8
}

function Write-MasterLog([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -LiteralPath $MasterLog -Value $line -Encoding utf8
}

function Record-Status([string]$Stage, [string]$Name, [string]$Seed, [int]$ExitCode) {
    $line = "$Stage,$Name,$Seed,$ExitCode,$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Add-Content -LiteralPath $StatusCsv -Value $line -Encoding utf8
    Write-MasterLog "$Stage $Name seed=$Seed exit=$ExitCode"
}

function Start-PythonRun([string]$Name, [string]$ScriptName, [string[]]$Arguments, [string]$LogTag) {
    $script = Join-Path $ForegroundDir $ScriptName
    $stdout = Join-Path $LogRoot "$LogTag.out.log"
    $stderr = Join-Path $LogRoot "$LogTag.err.log"
    $argumentList = @("`"$script`"") + $Arguments
    $process = Start-Process -FilePath $Python -ArgumentList $argumentList `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
        -WindowStyle Hidden -PassThru
    return [pscustomobject]@{Name=$Name; Process=$process}
}

$AdoptProcessIds = @($AdoptProcessIdsCsv.Split(',', [StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { [int]$_ })
if ($AdoptProcessIds.Count -gt 0) {
    Write-MasterLog "Adopting wave-1 process IDs: $($AdoptProcessIds -join ', ')"
    foreach ($processId in $AdoptProcessIds) {
        try {
            Wait-Process -Id $processId -ErrorAction Stop
            Record-Status "optimiser-adopted" "pid-$processId" "202607281" 0
        }
        catch {
            Record-Status "optimiser-adopted" "pid-$processId" "202607281" 1
        }
    }
}

$optimisers = @(
    @{Name="spike_gate_SEP"; Script="Optimisation\optimise_spike_gate_SEP.py"},
    @{Name="toy_objects_SEP"; Script="Optimisation\optimise_toy_objects_SEP.py"},
    @{Name="spike_gate_MTObjects"; Script="Optimisation\optimise_spike_gate_MTObjects.py"},
    @{Name="toy_objects_MTObjects"; Script="Optimisation\optimise_toy_objects_MTObjects.py"}
)

foreach ($seed in @(202607282, 202607283)) {
    Write-MasterLog "Starting optimiser wave seed=$seed"
    $wave = @()
    foreach ($spec in $optimisers) {
        $tag = "$($spec.Name)_seed_$seed"
        $wave += Start-PythonRun $spec.Name $spec.Script @("--max-images", "20", "--seed", "$seed") $tag
    }
    foreach ($item in $wave) {
        $item.Process.WaitForExit()
        Record-Status "optimiser" $item.Name "$seed" $item.Process.ExitCode
    }
}

Write-MasterLog "All optimiser waves finished; starting all-galaxy batches sequentially."
$batches = @(
    @{Name="spike_gate_SEP"; Script="Batch tools\batch_spike_gate_SEP.py"},
    @{Name="toy_objects_SEP"; Script="Batch tools\batch_toy_objects_SEP.py"},
    @{Name="spike_gate_MTObjects"; Script="Batch tools\batch_spike_gate_MTObjects.py"},
    @{Name="toy_objects_MTObjects"; Script="Batch tools\batch_toy_objects_MTObjects.py"}
)

foreach ($spec in $batches) {
    $tag = "batch_$($spec.Name)"
    $item = Start-PythonRun $spec.Name $spec.Script @() $tag
    $item.Process.WaitForExit()
    Record-Status "batch" $spec.Name "" $item.Process.ExitCode
}

Write-MasterLog "Stability optimiser and batch queue completed."
