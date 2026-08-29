$ErrorActionPreference = 'Stop'
$source = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation\Revised 22 Galaxy Toy Object Optimisation - Data and Program Flow.docx'
$pdf = 'C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\qa_clean22_flow\clean22_flow_qa.pdf'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($source, $false, $true)
    $doc.ExportAsFixedFormat($pdf, 17)
    $doc.Close(0)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
    Write-Output $pdf
}
finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
