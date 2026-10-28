from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8')
# New-round context and prior assessment are read-only references.
s=s.replace("$('galaxyTitle').textContent=`Galaxy ${id}`;", "$('galaxyTitle').textContent=`Galaxy ${id}`;\n $('previousReviewPanel').hidden=!g.previous_review;$('previousReviewText').textContent=g.previous_review?`Previous review: disc ${g.previous_review.disc_decision}; bar ${g.previous_review.bar_decision}; centre ${g.previous_review.centre_decision}; rule ${g.previous_review.rule_action}. Notes: ${g.previous_review.notes||'(no note)'}`:'';\n $('diagnosticLink').hidden=!g.refit?.job_id||!g.diagnostic_available;if(g.refit?.job_id)$('diagnosticLink').href='/api/refit/diagnostic?job='+g.refit.job_id;",1)
s=s.replace("(g.refit?'MANUAL CENTRE REFIT · ':'')", "(g.refit?'CENTRE-CONSTRAINED TRIAL · ':'')",1)
s=s.replace(" const base=g.pipeline_original??g.original;const rows=", " $('previousReviewHeader').hidden=!g.campaign_case;const base=g.pipeline_original??g.original;const rows=",1)
s=s.replace('<td>${deg(a)}</td><td>${deg(b)}', '<td>${deg(a)}</td>${g.campaign_case?`<td>${deg(g.previous_review?.calculation?.[name===\'Disc PA\'?\'disc_pa\':name===\'Bar PA\'?\'bar_pa\':\'inclination\'])}</td>`:\'\'}<td>${deg(b)}',1)
s=s.replace("$('outputPath').textContent='Saved locally in: '+S.boot.output;", "$('outputPath').textContent='Saved locally in: '+S.boot.output;$('campaignBanner').hidden=!S.boot.campaign;$('campaignBanner').textContent=S.boot.campaign?`${S.boot.campaign.title}: ${S.boot.sample.length} examples. New trials are provisional. Previous reviews and notes are preserved; save a new assessment for this round. Centre limits are pilot settings requiring review.`:'';",1)
# Always include centre evidence for centre-review comparisons, even if a fixed-centre trial has zero drift.
a=s.index(" if((c.centre_rejected_disc?.length??0)");b=s.index('\n if(!settings.noBar',a)
s=s[:a]+''' if(g.centre_reference){const raw=[...new Set([...selected(numericalPool(g,settings),'disc'),...selected(numericalPool(g,settings),'bar')])],rejected=[...new Set([...(c.centre_rejected_disc??[]),...(c.centre_rejected_bar??[])])];add('centre','Ellipse centre consistency',`${c.centre_rejected_disc?.length??0} disc and ${c.centre_rejected_bar?.length??0} bar samples in the selected intervals excluded. Reference: ${g.centre_reference.provenance}. Pilot cap ${fmt(r.centre_cap_native??3)} native px, fractional limit ${fmt((r.centre_fraction??.05)*100,1)}%, floor ${fmt(r.centre_floor_native??1)} native px. The displacement plot compares centres with the tolerance curve. ${g.refit?.lock_centre?'These ellipse centres are fixed by constraint; zero drift does not independently validate the supplied centre or fitted shape.':''}`,rejected.length?rejected:raw,rejected.length>0,r.centre_enabled===false?'Screen disabled':null);}
''' +s[b:]
s=s.replace("failed:'failed'}[example?.category]", "failed:'failed',centre_priority:'centre',centre_control:'centre',centre_validation:'centre'}[example?.category]")
s=s.replace("for(const [id,field,maxY,title] of [['epsPlot'", "const centreAxis=radiusAxis(Math.max(4,...S.g.profile.filter(p=>p.sma_arcsec<=xmax).map(p=>centrePointStatus(p)).filter(z=>z.available).map(z=>z.offset)));\n for(const [id,field,maxY,title] of [['epsPlot'",1)
s=s.replace("['paPlot','pa_sky_deg',180,", "['centrePlot','centre_offset',centreAxis.max,'Ellipse centre displacement (native pixels); dashed = limit'],['paPlot','pa_sky_deg',180,",1)
s=s.replace("const isPA=field==='pa_sky_deg',isInc=field==='inclination'", "const isPA=field==='pa_sky_deg',isInc=field==='inclination',isCentre=field==='centre_offset'",1)
s=s.replace("isInc?[0,15,30,45,60,75,90]:[0,.25,.5,.75,1]", "isInc?[0,15,30,45,60,75,90]:isCentre?centreAxis.ticks:[0,.25,.5,.75,1]",1)
s=s.replace("isInc?(inDisc(p)?ellipseInclination(p):null):p[field]", "isInc?(inDisc(p)?ellipseInclination(p):null):isCentre?(centrePointStatus(p).available?centrePointStatus(p).offset:null):p[field]",1)
s=s.replace("isInc?Math.round(vy):vy.toFixed(2)", "isInc?Math.round(vy):isCentre?vy.toFixed(centreAxis.decimals):vy.toFixed(2)",1)
needle=" let segments=[],current=[],previous=null;"
s=s.replace(needle," if(isCentre&&S.g.centre_reference){const path=[];for(let i=0;i<=80;i++){const radius=Math.max(.0001,xmax*i/80),ref=S.g.centre_reference,status=centrePointStatus({sma_arcsec:radius,x_original_pix:ref.x,y_original_pix:ref.y});if(status.available)path.push(`${x(radius)},${y(status.limit)}`);}html+=`<polyline class=\"centre-tolerance\" points=\"${path.join(' ')}\" fill=\"none\" stroke=\"#cf3434\" stroke-width=\"1.6\" stroke-dasharray=\"5 4\"><title>Centre tolerance in native pixels; samples above this curve are excluded while the centre screen is enabled.</title></polyline>`;}\n"+needle,1)
s=s.replace("$(id).innerHTML=html;$(id).dataset.xmax=xmax;", "$(id).innerHTML=html;$(id).dataset.xmax=xmax;if(id==='centrePlot')$(id).hidden=!(highlight&&warnings.some(w=>w.code==='centre'));",1)
s=s.replace("for(const id of ['epsPlot','incPlot','paPlot'])", "for(const id of ['epsPlot','incPlot','centrePlot','paPlot'])",1)
s=s.replace("const xmax=plotMax()", "const xmax=plotMax()")
# Failed fits still expose rejected measurements for diagnosis.
s=s.replace("const accepted=pool(),bounds=", "const accepted=S.g.original.status==='fit_failed'?S.g.profile.filter(p=>finite(p.sma_arcsec)):pool(),bounds=",1)
# Store rejection provenance compactly with a review.
s=s.replace("delete calculation.disc;delete calculation.bar;", "delete calculation.disc;delete calculation.bar;for(const key of ['centre_rejected_disc','centre_rejected_bar'])calculation[key]=(calculation[key]??[]).map(p=>({radius_arcsec:p.sma_arcsec,...centrePointStatus(p)}));",1)
# Small centre marks on displayed ellipses reveal the per-isophote centres.
s=s.replace("ctx.lineWidth=dashed?1.3:1.1;ctx.stroke();};", "ctx.lineWidth=dashed?1.3:1.1;ctx.stroke();if(S.settings.display.centres){const cx=t.x(p.x_original_pix),cy=t.y(p.y_original_pix);ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(cx-2,cy);ctx.lineTo(cx+2,cy);ctx.moveTo(cx,cy-2);ctx.lineTo(cx,cy+2);ctx.stroke();}};",1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/index.html');s=p.read_text(encoding='utf8');s=s.replace('<main>','<main>\n <p id="campaignBanner" class="campaign-banner" hidden></p>',1);s=s.replace('<p id="originalFlags" class="flagline"></p>','<p id="originalFlags" class="flagline"></p><details id="previousReviewPanel" class="panel" hidden><summary>Previous assessment (preserved)</summary><p id="previousReviewText" class="small"></p></details>',1)
s=s.replace('<svg id="paPlot"', '<svg id="centrePlot" viewBox="0 0 660 215" aria-label="Ellipse centre displacement profile" hidden></svg><svg id="paPlot"',1)
s=s.replace('<th title="Recalculated from the displayed fit', '<th id="previousReviewHeader" hidden>Previous reviewed selection</th><th title="Recalculated from the displayed fit',1)
s=s.replace('<div id="imageLoading"', '<div id="imageLoading"')
s=s.replace('   <details id="centrePanel">', '   <p><a id="diagnosticLink" class="button secondary" href="#" target="_blank" rel="noopener" hidden>Open science / model / residual diagnostic</a></p>\n   <details id="centrePanel">',1)
s=s.replace('Your assessment</h2>', 'Your assessment for this round</h2>',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/style.css');s=p.read_text(encoding='utf8');s+='\n.campaign-banner{padding:10px 12px;border-left:4px solid #176481;background:#e6f1f7;font-size:13px}.criteria-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}.results>div:first-child{overflow-x:auto}\n';p.write_text(s,encoding='utf8')
# Safe diagnostic route derives the PNG from an opaque validated refit identifier.
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('previous_review=(self.campaign or {}).get', 'diagnostic_available=bool(refit_id and (self.output/"refits"/refit_id/"diagnostics"/f"Euclid_{oid}_MER_VIS_model_residual.png").is_file()),\n                          previous_review=(self.campaign or {}).get',1)
needle='            if route == "/api/refit/export":'
s=s.replace(needle,'''            if route == "/api/refit/diagnostic":
                job=params.get("job",[""])[0]; status=self.server.store.refit_status(job)
                path=self.server.store.output/'refits'/job/'diagnostics'/f'Euclid_{status["object_id"]}_MER_VIS_model_residual.png'
                if not path.is_file():raise ValueError('No model diagnostic is available for this trial')
                return self.send(path.read_bytes(),'image/png')
''' +needle,1);p.write_text(s,encoding='utf8')
