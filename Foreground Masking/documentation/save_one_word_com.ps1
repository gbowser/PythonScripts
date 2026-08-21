param([Parameter(Mandatory=$true)][string]$InputTxt,[Parameter(Mandatory=$true)][string]$LocalDocx,[Parameter(Mandatory=$true)][string]$FinalDocx,[Parameter(Mandatory=$true)][string]$Pdf)
$ErrorActionPreference='Stop'
$w=$null
try{
 $text=[IO.File]::ReadAllText($InputTxt)
 $w=New-Object -ComObject Word.Application;$w.Visible=$false;$w.DisplayAlerts=0
 $d=$w.Documents.Add();$d.Content.Text=$text;$d.Content.Font.Name='Calibri';$d.Content.Font.Size=11
 $d.Content.ParagraphFormat.SpaceAfter=6;$d.Content.ParagraphFormat.LineSpacingRule=5;$d.Content.ParagraphFormat.LineSpacing=13.2
 $d.Paragraphs.Item(1).Range.Font.Size=24;$d.Paragraphs.Item(1).Range.Font.Bold=$true;$d.Paragraphs.Item(1).Range.Font.Color=0x45250B
 $d.Paragraphs.Item(2).Range.Font.Size=13;$d.Paragraphs.Item(2).Range.Font.Color=0x555555
 foreach($s in $d.Sections){$s.PageSetup.TopMargin=72;$s.PageSetup.BottomMargin=72;$s.PageSetup.LeftMargin=72;$s.PageSetup.RightMargin=72}
 $d.SaveAs2($LocalDocx,16);$d.ExportAsFixedFormat($Pdf,17);$d.Close(0);$w.Quit();[Runtime.InteropServices.Marshal]::FinalReleaseComObject($w)|Out-Null;$w=$null
 Copy-Item -LiteralPath $LocalDocx -Destination $FinalDocx -Force
 Write-Output $FinalDocx
}finally{if($w){try{$w.Quit()}catch{}}}
