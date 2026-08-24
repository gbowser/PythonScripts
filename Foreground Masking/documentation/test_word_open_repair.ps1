$ErrorActionPreference='Stop'
$path='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\toy_comparison_doc_qa\Toy Objects SEP and MTObjects Methodology.docx'
$m=[Type]::Missing
$w=New-Object -ComObject Word.Application; $w.Visible=$false; $w.DisplayAlerts=0
try {
  $d=$w.Documents.Open($path,$false,$true,$false,$m,$m,$false,$m,$m,$m,$m,$false,$true,$m,$true,$m)
  Write-Output 'OPENED_REPAIR'
  $d.Close(0)
} finally {$w.Quit()}
