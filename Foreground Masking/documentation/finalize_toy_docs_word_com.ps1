$ErrorActionPreference='Stop'
$dir='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\toy_comparison_doc_qa'
$names=@('Toy Objects SEP and MTObjects Methodology','Toy Objects SEP versus MTObjects Results and Recommendations')
$word=New-Object -ComObject Word.Application
$word.Visible=$false; $word.DisplayAlerts=0
try {
  foreach($name in $names){
    $docx=Join-Path $dir ($name+'.docx'); $pdf=Join-Path $dir ($name+'.pdf')
    Write-Output ('OPEN='+$docx)
    $doc=$word.Documents.Open($docx,$false,$false)
    Write-Output ('OPENED='+$docx)
    $doc.ExportAsFixedFormat($pdf,17)
    Write-Output ('EXPORTED='+$pdf)
    $doc.Close(0)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
  }
} finally {
  $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
