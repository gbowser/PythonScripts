import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=new URL('.',import.meta.url);
const data=JSON.parse(await fs.readFile(new URL('population.json',out),'utf8'));
const wb=Workbook.create();
const s=wb.worksheets.add('Galaxies');
const n=wb.worksheets.add('Sources and method');
const count=data.rows.length,end=count+4;
s.showGridLines=false;n.showGridLines=false;
s.getRange('A1').values=[['Galaxy research population']];
s.getRange('A2').values=[['182 galaxies; latest categorical review; ICRS sky coordinates of adopted image centres']];
const headers=['Galaxy','Status','Centre RA (deg)','Centre Dec (deg)','RA (hh:mm:ss)','Dec (dd:mm:ss)','Hemisphere','Fornax separation (deg)','Reviewed at','Review notes','Status source','Coordinate source','Status in interactive tool'];
s.getRange('A4:M4').values=[headers];
s.getRange(`A5:M${end}`).values=data.rows.map(r=>[r.name,r.status,r.ra,r.dec,r.ra_sex,r.dec_sex,null,null,r.reviewed_at,r.notes,r.status_source,r.coordinate_source,r.gui_status]);
s.getRange(`G5:G${end}`).formulas=data.rows.map((r,i)=>[`=IF(D${i+5}>0,"North",IF(D${i+5}<0,"South","Equator"))`]);
s.getRange(`H5:H${end}`).formulas=data.rows.map((r,i)=>[`=DEGREES(ACOS(MAX(-1,MIN(1,SIN(RADIANS(D${i+5}))*SIN(RADIANS('Sources and method'!$B$5))+COS(RADIANS(D${i+5}))*COS(RADIANS('Sources and method'!$B$5))*COS(RADIANS(C${i+5}-'Sources and method'!$B$4))))))`]);
n.getRange('A1').values=[['Sources and method']];
n.getRange('A3:C6').values=[['Reference','Value','Source URL'],['Fornax centre RA (deg)',data.fornax_ra,'https://simbad.cds.unistra.fr/simbad/sim-id?Ident=NGC+1399'],['Fornax centre Dec (deg)',data.fornax_dec,'https://simbad.cds.unistra.fr/simbad/sim-id?Ident=NGC+1399'],['Adopted Fornax centre','NGC 1399','https://almascience.eso.org/alma-data/science-verification/sv-noticeboard-subpages/science-verification-fornax-cluster']];
n.getRange('A8:B19').values=[
 ['Item','Definition'],
 ['Population','All 182 unique galaxies in s4g_image_geometry_manifest.csv, the default manifest used by the interactive tool.'],
 ['Status','Latest dated categorical decision for each galaxy across catalogue and blind reviews. Severity scores are independent and are not converted into categorical labels.'],
 ['Unreviewed','No categorical decision found. Missing decisions are not treated as Clean.'],
 ['Centre coordinates','Adopted centre_x_pix / centre_y_pix from the manifest, in 1-based FITS pixels, transformed using each original FITS header: CD matrix, forward SIP terms where present, and inverse TAN projection.'],
 ['Coordinate frame','ICRS; FITS headers record EQUINOX 2000. RA and Dec are decimal degrees, with sexagesimal copies for readability.'],
 ['Hemisphere','North when declination > 0; South when declination < 0; Equator when declination = 0. This is celestial hemisphere.'],
 ['Fornax separation','Great-circle angular separation from NGC 1399, not a projected physical distance or a cluster-membership determination.'],
 ['Fornax reference position','03:38:29.083, -35:27:02.67 (ICRS), from SIMBAD. Reference degrees above are editable and separation formulas update.'],
 ['Interactive-tool status','The tool reads only candidate_union_rereview_decisions.csv. This column preserves that display label; Status also includes later/other recorded categorical reviews.'],
 ['Review timestamp','Recorded source timestamp, retained as text to preserve the original local time; source files do not specify a timezone.'],
 ['Workbook date','2026-10-11']
];
n.getRange('A21:B26').values=[['Classification','Count'],...['Clean','Ambiguous','Polluted','Unreviewed'].map(x=>[x,null]),['Total galaxies',null]];
n.getRange('B22:B25').formulas=['Clean','Ambiguous','Polluted','Unreviewed'].map((x,i)=>[`=COUNTIF('Galaxies'!$B$5:$B$${end},A${i+22})`]);
n.getRange('B26').formulas=[['=SUM(B22:B25)']];
n.getRange('A28:B32').values=[['Review sources','Use'],['all182_cleanliness_decisions.csv','Latest categorical reviews of the wider population'],['candidate_union_rereview_decisions.csv','Catalogue candidate reviews; labels displayed by the interactive tool'],['blind_audit_decisions.csv','Earlier blind categorical review, used when not superseded'],['blind_remaining_decisions.csv','Blind review of remaining galaxies, used when not superseded']];
for(const sh of [s,n]){
 sh.getUsedRange().format.font={name:'Arial',size:11,color:'#243247'};
 sh.getUsedRange().format.rowHeight=22;
 sh.getRange('A1').format.font={name:'Arial',size:17,bold:true,color:'#243247'};
}
s.getRange('A2').format.font={italic:true,color:'#596579'};
s.getRange(`A4:M${end}`).format.columnWidth=21;
s.getRange('A:A').format.columnWidth=16;s.getRange('B:B').format.columnWidth=15;
s.getRange('C:D').format.columnWidth=20;s.getRange('E:F').format.columnWidth=19;
s.getRange('G:G').format.columnWidth=15;s.getRange('H:H').format.columnWidth=23;
s.getRange('I:I').format.columnWidth=25;s.getRange('J:J').format.columnWidth=38;
s.getRange('K:L').format.columnWidth=42;s.getRange('M:M').format.columnWidth=28;
s.getRange('A4:M4').format={fill:'#263B55',font:{bold:true,color:'#FFFFFF'},rowHeight:36,wrapText:true};
s.getRange(`C5:D${end}`).setNumberFormat('0.000000');
s.getRange(`H5:H${end}`).setNumberFormat('0.000');
s.getRange(`J5:M${end}`).format.wrapText=true;
s.getRange(`A5:M${end}`).format.autofitRows();
const table=s.tables.add(`A4:M${end}`,true,'GalaxyPopulation');table.showFilterButton=true;
s.freezePanes.freezeRows(4);s.freezePanes.freezeColumns(1);
for(const [status,color] of [['Clean','#E2F0E5'],['Ambiguous','#FFF0CE'],['Polluted','#F7DEDE'],['Unreviewed','#E8EBEF']])
 s.getRange(`B5:B${end}`).conditionalFormats.addCustom(`B5="${status}"`,{fill:color});
n.getRange('A:A').format.columnWidth=29;n.getRange('B:B').format.columnWidth=95;n.getRange('C:C').format.columnWidth=80;
n.getRange('C4:C6').format.wrapText=true;n.getRange('A6:C6').format.rowHeight=44;
n.getRange('A8:B19').format.wrapText=true;n.getRange('A28:B32').format.wrapText=true;
n.getRange('A8:B19').format.autofitRows();n.getRange('A28:B32').format.autofitRows();
n.getRange('B4:B5').setNumberFormat('0.000000');
for(const r of ['A3:C3','A8:B8','A21:B21','A28:B28'])n.getRange(r).format={fill:'#263B55',font:{bold:true,color:'#FFFFFF'},rowHeight:25};
console.log((await wb.inspect({kind:'table',range:'Galaxies!A4:H9',include:'values,formulas',tableMaxRows:6,tableMaxCols:8,maxChars:2500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:1500})).ndjson);
const computed=s.getRange(`H5:H${end}`).values.flat();
for(let i=0;i<count;i++){
 if(typeof computed[i]!=='number'||Math.abs(computed[i]-data.rows[i].separation)>1e-7)throw Error(`Separation mismatch ${data.rows[i].name}: ${computed[i]}`);
}
if(n.getRange('B26').values[0][0]!==182)throw Error('Population count mismatch');
for(const [sheetName,range,name] of [['Galaxies','A1:H12','galaxies-preview.png'],['Sources and method','A1:C19','sources-preview.png']]){
 const preview=await wb.render({sheetName,range,scale:1,format:'png'});
 await fs.writeFile(new URL(name,out),new Uint8Array(await preview.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(new URL('galaxy_population.xlsx',out).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
console.log('Exported 182 galaxies; all separation formulas checked against independent haversine calculations.');
