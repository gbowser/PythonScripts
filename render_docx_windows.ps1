[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputPath,

    [Parameter(Position = 1)]
    [string]$OutputDirectory,

    [switch]$EmitPdf,
    [switch]$VerboseRenderer
)

$ErrorActionPreference = "Stop"
$repositoryRoot = $PSScriptRoot
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$sofficeCandidates = @(
    "C:\Program Files\LibreOffice\program\soffice.exe",
    "C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    (Join-Path $repositoryRoot ".tools\LibreOffice\program\soffice.exe"),
    (Join-Path $repositoryRoot ".tools\LibreOffice\soffice.exe")
)
$sofficePath = $sofficeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$rendererPath = "C:\Users\gordo\.codex\plugins\cache\openai-primary-runtime\documents\26.812.11052\skills\documents\render_docx.py"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Repository Python was not found: $pythonPath"
}
if (-not $sofficePath) {
    throw "LibreOffice soffice.exe was not found in the system or repository-local locations."
}
if (-not (Test-Path -LiteralPath $rendererPath)) {
    throw "Codex DOCX renderer was not found: $rendererPath"
}

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path (Split-Path $resolvedInput -Parent) (([IO.Path]::GetFileNameWithoutExtension($resolvedInput)) + "_render")
}
$resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null

$popplerRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
$pdftoppm = Get-ChildItem -LiteralPath $popplerRoot -Recurse -Filter "pdftoppm.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "oschwartz10612\.Poppler" } |
    Select-Object -First 1
if (-not $pdftoppm) {
    throw "Poppler pdftoppm.exe was not found under $popplerRoot. Install oschwartz10612.Poppler with winget."
}

$sofficeDirectory = Split-Path $sofficePath -Parent
$popplerDirectory = Split-Path $pdftoppm.FullName -Parent
$env:PATH = "$sofficeDirectory;$popplerDirectory;$env:PATH"
$env:TEMP = Join-Path $repositoryRoot ".docx-temp"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null

& $pythonPath -c "import pdf2image" | Out-Null

$arguments = @($rendererPath, $resolvedInput, "--output_dir", $resolvedOutput)
if ($EmitPdf) { $arguments += "--emit_pdf" }
if ($VerboseRenderer) { $arguments += "--verbose" }

& $pythonPath @arguments
if ($LASTEXITCODE -ne 0) {
    throw "DOCX rendering failed with exit code $LASTEXITCODE."
}

$pages = Get-ChildItem -LiteralPath $resolvedOutput -Filter "page-*.png" | Sort-Object Name
if (-not $pages) {
    throw "Rendering completed without creating page PNG files."
}

Write-Output "Rendered $($pages.Count) page(s) to $resolvedOutput"
$pages | Select-Object FullName, Length
