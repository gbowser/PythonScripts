$ErrorActionPreference='Stop'
$out='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\toy_comparison_doc_qa\word_com_save_test.docx'
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
  $doc=$word.Documents.Add()
  $word.Selection.TypeText('Word COM save test')
  Write-Output 'BEFORE_SAVE'
  $doc.SaveAs2($out,16)
  Write-Output 'AFTER_SAVE'
  $doc.Close(0)
} finally {
  $word.Quit()
}
