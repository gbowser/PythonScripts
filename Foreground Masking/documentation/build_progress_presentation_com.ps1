$ErrorActionPreference = 'Stop'

$outDir = Join-Path $PSScriptRoot 'presentation_progress_20260829'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$cropDir = Join-Path $outDir 'image_crops'
New-Item -ItemType Directory -Force -Path $cropDir | Out-Null
$outFile = Join-Path $outDir 'Optimisation of Foreground Object Masking - Progress Presentation.pptx'

$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\final20_toy_optimisation\all182_application'
$clean = @('NGC0298','NGC0986','NGC1255','NGC1341','NGC1367','NGC3486','NGC3681','NGC4405','NGC4579','NGC4765','NGC1347','NGC2681','IC1954','NGC7531','NGC7418','NGC1559','PGC042160','NGC3726','NGC4102','NGC0918')

$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = -1
$deck = $pp.Presentations.Add()
$deck.PageSetup.SlideWidth = 960
$deck.PageSetup.SlideHeight = 540

$black = 0x171717; $gray = 0x666666; $light = 0xF2F3F5; $blue = 0xE67E22; $green = 0x2E8B57; $red = 0xD64541

function Add-Text($slide,$text,$x,$y,$w,$h,$size=20,$bold=$false,$color=$black,$align=1) {
  $s=$slide.Shapes.AddTextbox(1,$x,$y,$w,$h); $s.TextFrame.TextRange.Text=[string]$text
  $s.TextFrame.TextRange.Font.Name='Arial'; $s.TextFrame.TextRange.Font.Size=$size
  $s.TextFrame.TextRange.Font.Bold=[int]$bold; $s.TextFrame.TextRange.Font.Color.RGB=$color
  $s.TextFrame.TextRange.ParagraphFormat.Alignment=$align; $s.TextFrame.MarginLeft=0; $s.TextFrame.MarginRight=0
  return $s
}
function Add-Rect($slide,$x,$y,$w,$h,$fill=$light,$line=0xDDDDDD) {
  $s=$slide.Shapes.AddShape(1,$x,$y,$w,$h); $s.Fill.ForeColor.RGB=$fill; $s.Line.ForeColor.RGB=$line; return $s
}
function Add-Line($slide,$x1,$y1,$x2,$y2,$color=$black,$weight=1.5) {
  $s=$slide.Shapes.AddLine($x1,$y1,$x2,$y2); $s.Line.ForeColor.RGB=$color; $s.Line.Weight=[single]$weight; return $s
}
function Add-Arrow($slide,$x1,$y1,$x2,$y2,$color=$blue,$weight=2.5) {
  $s=Add-Line $slide $x1 $y1 $x2 $y2 $color $weight; $s.Line.EndArrowheadStyle=3; return $s
}
function Add-Title($slide,$title,$kicker='PROGRESS UPDATE') {
  Add-Text $slide $kicker 48 25 420 20 9 $true $blue | Out-Null
  Add-Text $slide $title 48 49 855 48 28 $true | Out-Null
  Add-Line $slide 48 104 912 104 0xD8D8D8 1 | Out-Null
}
function Add-Footer($slide,$n,$source='') {
  if($source){Add-Text $slide $source 48 510 800 16 7 $false 0x777777 | Out-Null}
  Add-Text $slide ([string]$n) 890 510 22 16 8 $false 0x777777 3 | Out-Null
}
function Add-PictureContain($slide,$path,$x,$y,$w,$h) {
  if(-not (Test-Path -LiteralPath $path)){return $null}
  $p=$slide.Shapes.AddPicture($path,0,-1,$x,$y,-1,-1)
  $scale=[Math]::Min($w/$p.Width,$h/$p.Height); $p.Width=[single]($p.Width*$scale); $p.Height=[single]($p.Height*$scale)
  $p.Left=[single]($x+($w-$p.Width)/2); $p.Top=[single]($y+($h-$p.Height)/2); return $p
}
function Add-PictureFill($slide,$path,$x,$y,$w,$h) {
  if(-not (Test-Path -LiteralPath $path)){return $null}
  if($null -eq $slide){throw "Add-PictureFill received a null slide for $path"}
  return $slide.Shapes.AddPicture($path,0,-1,$x,$y,$w,$h)
}
function Add-Notes($slide,$text) {
  try { $slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text=$text } catch {}
}
function New-TopCrop($source,$destination,$fraction) {
  Add-Type -AssemblyName System.Drawing
  $src=[System.Drawing.Bitmap]::FromFile($source)
  try {
    $height=[Math]::Max(1,[int]($src.Height*$fraction))
    $rect=New-Object System.Drawing.Rectangle(0,0,$src.Width,$height)
    $dst=$src.Clone($rect,$src.PixelFormat)
    try { $dst.Save($destination,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $dst.Dispose() }
  } finally { $src.Dispose() }
  return $destination
}
function New-RegionCrop($source,$destination,$xFraction,$yFraction,$widthFraction,$heightFraction) {
  Add-Type -AssemblyName System.Drawing
  $src=[System.Drawing.Bitmap]::FromFile($source)
  try {
    $rect=New-Object System.Drawing.Rectangle([int]($src.Width*$xFraction),[int]($src.Height*$yFraction),[int]($src.Width*$widthFraction),[int]($src.Height*$heightFraction))
    $dst=$src.Clone($rect,$src.PixelFormat)
    try { $dst.Save($destination,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $dst.Dispose() }
  } finally { $src.Dispose() }
  return $destination
}
function New-Slide { return $deck.Slides.Add($deck.Slides.Count+1,12) }

# 1
$s=New-Slide; Add-Text $s 'MSc RESEARCH | PROGRESS PRESENTATION' 48 38 620 24 11 $true $blue | Out-Null
Add-Text $s 'Optimisation of Foreground Object Masking' 48 126 610 116 38 $true | Out-Null
Add-Text $s 'A controlled comparison of SEP and MTObjects using synthetic contaminants' 48 255 590 62 19 $false $gray | Out-Null
Add-Rect $s 710 80 202 350 0x171717 0x171717 | Out-Null
Add-Text $s '182' 740 135 142 68 48 $true 0xFFFFFF 2 | Out-Null; Add-Text $s 'galaxy images' 740 205 142 30 14 $false 0xDDDDDD 2 | Out-Null
Add-Text $s '20' 740 278 142 58 42 $true $blue 2 | Out-Null; Add-Text $s 'clean calibration galaxies' 735 335 152 48 13 $false 0xDDDDDD 2 | Out-Null
Add-Footer $s 1; Add-Notes $s "Timing: 0:40. Frame the task: remove foreground structure while preserving the galaxy."

# 2
$s=New-Slide; Add-Title $s 'The masking problem is a balance, not a detection contest'
Add-Text $s 'Foreground stars and compact sources distort bar profiles and isophotes.' 48 127 410 68 22 $true | Out-Null
Add-Text $s 'An aggressive mask removes contaminants, but can also erase real galaxy structure. A useful method must maximise recovery while limiting collateral masking.' 48 211 410 110 17 $false $gray | Out-Null
Add-Rect $s 500 130 180 250 0xE8F4EC 0xB9D8C4 | Out-Null; Add-Text $s 'RECOVER' 525 159 130 24 11 $true $green 2 | Out-Null; Add-Text $s 'toy signal' 520 207 140 42 25 $true $green 2 | Out-Null; Add-Text $s 'higher is better' 525 271 130 24 12 $false $gray 2 | Out-Null
Add-Rect $s 704 130 180 250 0xFBEDEC 0xE5C1BE | Out-Null; Add-Text $s 'PRESERVE' 729 159 130 24 11 $true $red 2 | Out-Null; Add-Text $s 'galaxy area' 724 207 140 42 25 $true $red 2 | Out-Null; Add-Text $s 'less masking is better' 719 271 150 24 12 $false $gray 2 | Out-Null
Add-Text $s 'Optimisation target' 500 409 384 24 11 $true $blue 2 | Out-Null; Add-Text $s 'best scientific trade-off' 500 438 384 30 20 $true $black 2 | Out-Null
Add-Footer $s 2 'Project rationale; objective structure informed by Haigh et al. (2021).'; Add-Notes $s 'Timing: 0:55. Emphasise why segmentation metrics alone are insufficient.'

# 3
$s=New-Slide; Add-Title $s 'Two complementary segmentation approaches'
$cards=@(@('SEP','Threshold + connected pixels','Fast; explicit background estimation and deblending','Bertin & Arnouts 1996; Barbary 2016'),@('MTObjects','Max-tree attribute filtering','Hierarchical regions; sensitive to faint extended structure','Teeninga et al. 2015; Haigh et al. 2021'))
for($i=0;$i -lt 2;$i++){ $x=48+$i*438; Add-Rect $s $x 135 414 300 0xF5F5F5 0xDADADA | Out-Null; Add-Text $s $cards[$i][0] ($x+24) 160 160 42 30 $true ($(if($i-eq0){$blue}else{$green})) | Out-Null; Add-Text $s $cards[$i][1] ($x+24) 218 360 42 19 $true | Out-Null; Add-Text $s $cards[$i][2] ($x+24) 278 360 72 16 $false $gray | Out-Null; Add-Text $s $cards[$i][3] ($x+24) 390 360 24 9 $false 0x777777 | Out-Null }
Add-Footer $s 3 'Sources: Bertin & Arnouts (1996); Barbary (2016); Teeninga et al. (2015); Haigh et al. (2021).'; Add-Notes $s 'Timing: 1:00. SEP is the Python library implementation of Source Extractor.'

# 4
$s=New-Slide; Add-Title $s 'A clean calibration set had to be established first'
$steps=@(@('1','Catalogue screen','Gaia + 2MASS candidates'),@('2','2-D residual screen','original minus Gaussian blur'),@('3','Blind visual review','clean / ambiguous / polluted'),@('4','Severity adjudication','resolve borderline cases'))
for($i=0;$i-lt4;$i++){ $x=48+$i*216; Add-Text $s $steps[$i][0] $x 145 34 34 18 $true 0xFFFFFF 2 | Out-Null; $c=$s.Shapes.AddShape(9,$x,141,34,34);$c.Fill.ForeColor.RGB=$blue;$c.Line.Visible=0;$c.ZOrder(1); Add-Text $s $steps[$i][1] $x 196 186 44 16 $true | Out-Null; Add-Text $s $steps[$i][2] $x 247 186 62 13 $false $gray | Out-Null; if($i-lt3){Add-Arrow $s ($x+46) 158 ($x+196) 158 0x999999 2 | Out-Null}}
Add-Rect $s 48 356 846 87 0x171717 0x171717 | Out-Null; Add-Text $s '40  >  11  >  20' 78 375 270 46 28 $true 0xFFFFFF | Out-Null; Add-Text $s 'Successive sets exposed ranking bias and improved the final calibration sample.' 365 377 490 44 16 $false 0xE6E6E6 | Out-Null
Add-Footer $s 4 'Project selection workflow and reviewer records, August 2026.'; Add-Notes $s 'Timing: 1:10. Explain that bright structures within the galaxy were down-weighted, but not ignored.'

# 5-6 clean grids
for($page=0;$page-lt2;$page++){ $s=New-Slide; Add-Title $s ("Final clean calibration sample | {0}/2" -f ($page+1)); for($i=0;$i-lt10;$i++){ $idx=$page*10+$i; $col=$i%5;$row=[Math]::Floor($i/5);$x=48+$col*174;$y=132+$row*169; Add-Rect $s $x $y 154 145 0xF5F5F5 0xDADADA|Out-Null; Add-Text $s $clean[$idx] ($x+8) ($y+119) 138 20 12 $true $black 2|Out-Null; $img=Join-Path "$root\SEP" ("{0}_sep_*_clean.png" -f $clean[$idx]); $hit=Get-ChildItem -Path $img -ErrorAction SilentlyContinue|Select-Object -First 1; if($hit){$thumb=New-RegionCrop $hit.FullName (Join-Path $cropDir ($clean[$idx]+'_thumb.png')) 0.105 0.07 0.30 0.205; Add-PictureFill $s $thumb ($x+5) ($y+5) 144 108|Out-Null} }; Add-Footer $s ($page+5) 'Final 20 selected by blind visual contamination severity with documented tie-breaks.'; Add-Notes $s 'Timing: 0:40. These are calibration images, not claims that the fields contain literally zero foreground signal.' }

# 7
$s=New-Slide; Add-Title $s 'Toy objects inserted into clean galaxy images'
$toySource=Get-ChildItem -LiteralPath "$root\SEP" -Filter 'NGC0986*clean.png'|Select-Object -First 1
$toyDefs=@(@('Star-like','compact PSF',0.70,0.075,0.13,0.13),@('Cluster-like','broader compact source',0.78,0.16,0.15,0.15),@('Small galaxy','extended / elliptical',0.60,0.08,0.17,0.17))
for($i=0;$i-lt3;$i++){ $x=48+$i*282; Add-Rect $s $x 139 254 282 0xF4F4F4 0xD9D9D9|Out-Null; if($toySource){$toyCrop=New-RegionCrop $toySource.FullName (Join-Path $cropDir ('toy_'+$i+'.png')) $toyDefs[$i][2] $toyDefs[$i][3] $toyDefs[$i][4] $toyDefs[$i][5]; Add-PictureFill $s $toyCrop ($x+9) 148 236 205|Out-Null}; Add-Text $s $toyDefs[$i][0] ($x+12) 363 230 23 15 $true $black 2|Out-Null; Add-Text $s $toyDefs[$i][1] ($x+12) 390 230 18 10 $false $gray 2|Out-Null }
Add-Text $s 'Green outlines mark the injected toy boundaries. Toys span 6-30 sigma and are deliberately bright enough to assess recovery.' 48 444 818 34 11 $false $gray | Out-Null
Add-Footer $s 7 'Project paired-toy injection manifest and optimisation configuration.'; Add-Notes $s 'Timing: 1:00. Explain why the same injected objects are used for both methods.'

# 8
$s=New-Slide; Add-Title $s 'Objective: reward recovery, penalise collateral masking'
Add-Rect $s 48 140 864 96 0x171717 0x171717|Out-Null; Add-Text $s 'score  =  recovery quality  -  false-mask penalty  -  cap penalty' 78 171 804 42 25 $true 0xFFFFFF 2|Out-Null
$obj=@(@('Toy recall','fraction of injected pixels recovered'),@('Detection rate','fraction of toys meaningfully detected'),@('Masked fraction','total image area removed'),@('15% cap','reject pathological over-masking'))
for($i=0;$i-lt4;$i++){ $x=48+($i%2)*438;$y=276+[Math]::Floor($i/2)*92; Add-Text $s $obj[$i][0] $x $y 180 24 15 $true $blue|Out-Null; Add-Text $s $obj[$i][1] ($x+180) $y 230 46 13 $false $gray|Out-Null }
Add-Footer $s 8 'Project paired-toy objective, metric version paired-toy-metrics-v1.'; Add-Notes $s 'Timing: 1:00. Precision is low because the underlying image can still contain real uncatalogued sources; the paired toy metrics are the primary signal.'

# 9
$s=New-Slide; Add-Title $s 'Optuna searches the parameter space efficiently'
Add-Text $s 'Each trial proposes a parameter combination, runs the segmentation, evaluates the paired toys, and learns where to sample next.' 48 130 820 56 18 $false $gray|Out-Null
$labs=@('sample parameters','run SEP / MTObjects','measure objective','update search')
for($i=0;$i-lt4;$i++){ $x=48+$i*216; Add-Rect $s $x 238 170 100 ($(if($i-eq2){0xFFF0E3}else{0xF2F3F5})) 0xD5D5D5|Out-Null; Add-Text $s ($i+1) ($x+12) 252 24 20 11 $true $blue 2|Out-Null; Add-Text $s $labs[$i] ($x+18) 285 134 34 14 $true $black 2|Out-Null; if($i-lt3){Add-Arrow $s ($x+174) 288 ($x+210) 288 $blue 2.5|Out-Null}}
Add-Text $s '40 trials per fold x 20 folds x 2 methods' 48 405 820 36 23 $true | Out-Null
Add-Footer $s 9 'Optuna: Akiba et al. (2019); project cross-validation configuration.'; Add-Notes $s 'Timing: 0:55. Optuna concentrates evaluation on promising regions instead of a full grid.'

# 10
$s=New-Slide; Add-Title $s 'Leave-one-galaxy-out validation tests generalisation'
$thumbPaths=@(); foreach($name in $clean){$p=Join-Path $cropDir ($name+'_thumb.png'); if(Test-Path -LiteralPath $p){$thumbPaths+=$p}}
for($row=0;$row-lt5;$row++){ $y=131+$row*69; Add-Text $s ("Fold {0}" -f ($row+1)) 48 ($y+13) 52 18 9 $true $gray|Out-Null; for($col=0;$col-lt20;$col++){ $x=105+$col*39; Add-Rect $s $x $y 32 45 0xF2F3F5 0xD0D0D0|Out-Null; if($thumbPaths.Count-gt$col){Add-PictureFill $s $thumbPaths[$col] ($x+1) ($y+1) 30 43|Out-Null} }; $held=19-$row; $hx=105+$held*39; Add-Line $s ($hx+2) ($y+2) ($hx+30) ($y+43) 0x0000FF 3|Out-Null; Add-Line $s ($hx+30) ($y+2) ($hx+2) ($y+43) 0x0000FF 3|Out-Null }
Add-Text $s 'Red X = held-out galaxy; the other 19 train the fold. The omitted galaxy moves left one place in each row.' 105 482 780 20 11 $false $gray 2|Out-Null
Add-Footer $s 10 'Project final-20 cross-validation design.'; Add-Notes $s 'Timing: 1:05. Held out means the galaxy did not influence the parameter fit for that fold.'

# 11 results
$s=New-Slide; Add-Title $s 'Final-20 optimisation exposes a clear method trade-off'
$headers=@('Metric','SEP','MTObjects');$headerX=@(48,390,620);$headerW=@(330,210,210);$rows=@(@('Mean toy recall','51.2%','61.3%'),@('Toy detection rate','52.1%','62.6%'),@('Mean image masked','2.8%','10.7%'),@('Maximum image masked','6.1%','14.0%'),@('Composite score','0.475','0.280'))
for($c=0;$c-lt3;$c++){Add-Text $s $headers[$c] $headerX[$c] 136 $headerW[$c] 28 12 $true ($(if($c-eq0){$gray}elseif($c-eq1){$blue}else{$green}))|Out-Null}
for($r=0;$r-lt5;$r++){ $y=178+$r*56; if($r%2-eq0){Add-Rect $s 48 ($y-8) 822 46 0xF5F5F5 0xF5F5F5|Out-Null}; Add-Text $s $rows[$r][0] 62 $y 300 24 14 $true|Out-Null; Add-Text $s $rows[$r][1] 428 $y 150 24 16 $true $blue 2|Out-Null; Add-Text $s $rows[$r][2] 658 $y 150 24 16 $true $green 2|Out-Null }
Add-Text $s 'Interpretation: MTObjects recovers more injected structure; SEP preserves more of the galaxy image.' 48 468 822 28 16 $true|Out-Null
Add-Footer $s 11 'Final-20 winner JSON files; independent selection-set metrics, 29 August 2026.'; Add-Notes $s 'Timing: 1:20. Do not declare an absolute winner yet; the scientific preference depends on the acceptable masking budget.'

# 12-13 large method composites
foreach($example in @(@('NGC0986',12),@('NGC3486',13))){
  $gal=$example[0]; $slideNo=$example[1]; $s=New-Slide; Add-Title $s ("Large-format recovery comparison | "+$gal)
  $sep=Get-ChildItem -LiteralPath "$root\SEP" -Filter ($gal+'*clean.png')|Select-Object -First 1
  $mto=Get-ChildItem -LiteralPath "$root\MTObjects" -Filter ($gal+'*clean.png')|Select-Object -First 1
  if(-not $sep){$sep=Get-ChildItem -LiteralPath "$root\SEP" -Filter ($gal+'*.png')|Select-Object -First 1}; if(-not $mto){$mto=Get-ChildItem -LiteralPath "$root\MTObjects" -Filter ($gal+'*.png')|Select-Object -First 1}
  $rowDefs=@(@('As inserted',$sep,0.105,0.07,0.31,0.205,$sep,0.59,0.07,0.31,0.205),@('SEP result',$sep,0.105,0.30,0.31,0.205,$sep,0.59,0.30,0.31,0.205),@('MTObjects result',$mto,0.105,0.30,0.31,0.205,$mto,0.59,0.30,0.31,0.205))
  for($r=0;$r-lt3;$r++){ $y=126+$r*123; Add-Text $s $rowDefs[$r][0] 48 ($y+38) 120 30 13 $true ($(if($r-eq0){$gray}elseif($r-eq1){$blue}else{$green})) 3|Out-Null; for($c=0;$c-lt2;$c++){ $src=$rowDefs[$r][1+$c*5]; if($src){$crop=New-RegionCrop $src.FullName (Join-Path $cropDir ($gal+'_r'+$r+'_c'+$c+'.png')) $rowDefs[$r][2+$c*5] $rowDefs[$r][3+$c*5] $rowDefs[$r][4+$c*5] $rowDefs[$r][5+$c*5]; Add-PictureFill $s $crop (185+$c*352) $y 320 112|Out-Null} }; Add-Text $s ($(if($r-eq0){'Galaxy-centred original'}else{'Mask'})) 185 ($y+112) 320 14 8 $false $gray 2|Out-Null; Add-Text $s ($(if($r-eq0){'Original + toys'}else{'Recovered image'})) 537 ($y+112) 320 14 8 $false $gray 2|Out-Null }
  Add-Footer $s $slideNo ("Project paired-toy diagnostic reports: "+$gal+". Green = recovered toy boundary; red = incorrect mask."); Add-Notes $s 'Timing: 0:55. Compare the mask footprint and recovered image row by row.'
}

# 14
$s=New-Slide; Add-Title $s 'Progress, limitations and next decisions'
$items=@(@('DONE','20-fold SEP and MTObjects optimisation','20 clean galaxies x 10 toys'),@('IN PROGRESS','Apply winners to the full sample','180/182 currently complete for both'),@('RESOLVE','Constrained toy placement','fallback to 8 original-size toys'),@('DECIDE','Scientific operating point','recovery versus masked area'))
for($i=0;$i-lt4;$i++){ $y=132+$i*87; Add-Text $s $items[$i][0] 48 $y 110 20 9 $true ($(if($i-eq0){$green}elseif($i-eq1){$blue}else{$red}))|Out-Null; Add-Text $s $items[$i][1] 170 ($y-5) 330 30 16 $true|Out-Null; Add-Text $s $items[$i][2] 520 ($y-5) 350 36 14 $false $gray|Out-Null; Add-Line $s 48 ($y+48) 870 ($y+48) 0xDDDDDD 1|Out-Null }
Add-Text $s 'Current conclusion' 48 475 150 20 10 $true $blue|Out-Null; Add-Text $s 'The final-20 design is methodologically stronger; the best algorithm still depends on an explicit masking budget.' 204 469 666 36 15 $true|Out-Null
Add-Footer $s 14 'Project status at 29 August 2026.'; Add-Notes $s 'Timing: 1:00. Mention that final all-182 summary and comparison with earlier 11/40 samples will close the study.'

# 15 refs
$s=New-Slide; Add-Title $s 'References and project sources' 'REFERENCES'
$refs=@(
'Haigh, C. et al. (2021). Optimising and comparing source-extraction tools using objective segmentation quality criteria. Astronomy and Astrophysics 645, A107. doi:10.1051/0004-6361/202036561',
'Bertin, E. and Arnouts, S. (1996). SExtractor: Software for source extraction. Astronomy and Astrophysics Supplement 117, 393-404. doi:10.1051/aas:1996164',
'Barbary, K. (2016). SEP: Source Extractor as a library. Journal of Open Source Software 1(6), 58. doi:10.21105/joss.00058',
'Teeninga, P. et al. (2015). Improved detection of faint extended astronomical objects through statistical attribute filtering. ISMM, 157-168.',
'Haigh, C. MTObjects development implementation: github.com/CarolineHaigh/mtobjects',
'Akiba, T. et al. (2019). Optuna: A next-generation hyperparameter optimization framework. KDD 2019.',
'Project artefacts: final-20 selection records, paired-toy manifest, cross-validation winner JSON files and all-182 diagnostic reports (August 2026).')
for($i=0;$i-lt$refs.Count;$i++){Add-Text $s ('- '+$refs[$i]) 52 (124+$i*53) 820 46 11 $false $black|Out-Null}
Add-Footer $s 15; Add-Notes $s 'Timing: 0:30. Questions.'

$deck.SaveAs($outFile,24)
$deck.Close(); $pp.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($deck)|Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp)|Out-Null
Write-Output $outFile
