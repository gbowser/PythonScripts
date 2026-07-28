$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$LogRoot = Join-Path $ForegroundDir "run_logs\stability_20260727"
$ControlLog = Join-Path $LogRoot "resume_missing_runs.log"
$BatchControlLog = Join-Path $LogRoot "stop_and_visible_batches.log"
$Python = (Get-Command python).Source
$Workbook = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation\Foreground Masking Optimisation Results.xlsx"

function Write-ControlLog([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -LiteralPath $ControlLog -Value $line -Encoding utf8
}

function Wait-ForCurrentBatches {
    Write-ControlLog "Waiting for the current visible all-galaxy batch sequence to finish."
    while ($true) {
        if (Test-Path -LiteralPath $BatchControlLog) {
            $content = Get-Content -Raw -LiteralPath $BatchControlLog
            if ($content -match 'All visible batch jobs finished') { break }
        }
        Start-Sleep -Seconds 15
    }
    Write-ControlLog "Current all-galaxy batches are complete."
}

function Start-VisibleOptimiser([string]$Name, [string]$ScriptName, [int]$Seed) {
    $script = Join-Path $ForegroundDir $ScriptName
    $title = "$Name - seed $Seed"
    $command = "`$Host.UI.RawUI.WindowTitle='$title'; & '$Python' '$script' --max-images 20 --seed $Seed; exit `$LASTEXITCODE"
    $process = Start-Process -FilePath (Get-Command pwsh).Source `
        -ArgumentList @('-NoProfile', '-Command', "`"$command`"") -PassThru
    Write-ControlLog "Started $Name seed=$Seed in visible PowerShell PID $($process.Id)."
    return [pscustomobject]@{Name=$Name; Seed=$Seed; Process=$process}
}

function Populate-ResultsWorkbook {
    Write-ControlLog "Backfilling all stability-study runs into $Workbook"
    $helper = Join-Path $ForegroundDir "Shared\append_optimisation_run_to_workbook.py"
    $specs = @(
        @{Folder='sep spike optimisation'; Algorithm='SEP'; Method='Spike Gate'; Prefix='sep_spike_optimisation'},
        @{Folder='sep toy optimisation'; Algorithm='SEP'; Method='Toy Object'; Prefix='sep_toy_object_optimisation'},
        @{Folder='mtobjects spike optimisation'; Algorithm='MTObjects'; Method='Spike Gate'; Prefix='mtobjects_spike_optimisation'},
        @{Folder='mtobjects toy optimisation'; Algorithm='MTObjects'; Method='Toy Object'; Prefix='mtobjects_parameter_optimisation'}
    )
    $dataRoot = "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
    foreach ($spec in $specs) {
        $parent = Join-Path $dataRoot $spec.Folder
        if (-not (Test-Path -LiteralPath $parent)) { continue }
        foreach ($runDir in Get-ChildItem -LiteralPath $parent -Directory) {
            $config = Get-ChildItem -LiteralPath $runDir.FullName -File -Filter '*optimisation_config.json' | Select-Object -First 1
            if ($null -eq $config) { continue }
            try { $seed = (Get-Content -Raw -LiteralPath $config.FullName | ConvertFrom-Json).seed } catch { continue }
            if ($seed -notin @(202607281, 202607282, 202607283)) { continue }
            & $Python $helper --algorithm $spec.Algorithm --method $spec.Method `
                --run-dir $runDir.FullName --prefix $spec.Prefix --workbook $Workbook
            Write-ControlLog "Workbook append $($spec.Algorithm) $($spec.Method) seed=$seed exit=$LASTEXITCODE"
        }
    }
}

Wait-ForCurrentBatches

$optimisers = @(
    @{Name='SEP Spike Gate'; Script='optimise_spike_gate_SEP.py'},
    @{Name='SEP Toy Objects'; Script='optimise_toy_objects_SEP.py'},
    @{Name='MTObjects Spike Gate'; Script='optimise_spike_gate_MTObjects.py'},
    @{Name='MTObjects Toy Objects'; Script='optimise_toy_objects_MTObjects.py'}
)

foreach ($seed in @(202607282, 202607283)) {
    Write-ControlLog "Starting missing optimisation wave seed=$seed."
    $wave = @()
    foreach ($spec in $optimisers) {
        $wave += Start-VisibleOptimiser $spec.Name $spec.Script $seed
    }
    foreach ($item in $wave) {
        $item.Process.WaitForExit()
        Write-ControlLog "$($item.Name) seed=$($item.Seed) finished with exit code $($item.Process.ExitCode)."
    }
}

Populate-ResultsWorkbook
Write-ControlLog "Missing optimisation runs completed and results workbook populated."
Write-Host "Press Enter to close this window."
Read-Host
