$ErrorActionPreference='Stop'
$w=New-Object -ComObject Word.Application
$w.Visible=$false
$w.DisplayAlerts=0
$d=$w.Documents.Add()
$d.Content.Text='COM save test'
$p='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\phase2_com_qa\com_save_test.docx'
$d.SaveAs2($p,16)
$d.Close(0)
$w.Quit()
Write-Output (Test-Path -LiteralPath $p)
