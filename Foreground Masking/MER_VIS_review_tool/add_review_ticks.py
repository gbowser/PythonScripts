from pathlib import Path
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8');s=s.replace('function queue(){','const isReviewed = review => !!review && review.reviewed!==false;\nfunction queue(){',1)
s=s.replace('!S.boot.reviews[r.object_id]','!isReviewed(S.boot.reviews[r.object_id])').replace('filter(r=>S.boot.reviews[r.object_id])','filter(r=>isReviewed(S.boot.reviews[r.object_id]))').replace('.map(r=>S.boot.reviews[r.object_id]).filter(Boolean)','.map(r=>S.boot.reviews[r.object_id]).filter(isReviewed)')
a=s.index("html+=`<button class=\"queue-item");b=s.index(';}',a)
s=s[:a]+'''html+=`<div class="queue-row ${S.id===row.object_id?'active':''}"><button class="queue-item" data-id="${esc(row.object_id)}">${esc(row.object_id)}${name?`<span class="name">${esc(name)}</span>`:''}</button><input class="review-tick" type="checkbox" data-review-id="${esc(row.object_id)}" aria-label="Reviewed galaxy ${esc(row.object_id)}" title="Mark reviewed; untick to undo review status (notes are retained)" ${isReviewed(S.boot.reviews[row.object_id])?'checked':''}></div>`''' +s[b:]
needle=" $('queue').querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>loadGalaxy(b.dataset.id));"
s=s.replace(needle,needle+"\n $('queue').querySelectorAll('[data-review-id]').forEach(b=>b.onchange=()=>setReviewed(b.dataset.reviewId,b.checked,b));")
s=s.replace("$('saveStatus').textContent=saved?`Saved assessment:","$('saveStatus').textContent=isReviewed(saved)?`Saved assessment:")
s=s.replace("'Exploration is not marked as reviewed until you save.'","'Not marked reviewed. Save an assessment or tick the galaxy in the left list.'")
pos=s.index('async function saveReview(')
s=s[:pos]+'''async function setReviewed(id,reviewed,box){box.disabled=true;clearError();try{
 const result=await api('/api/review-status',{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':S.token},body:JSON.stringify({object_id:id,reviewed})});
 S.boot.reviews[id]=result.review;queue();if(S.id===id){S.g.review=result.review;$('saveStatus').textContent=reviewed?'Marked reviewed; use Save assessment to save any form changes.':'Review status undone; saved notes and current edits are retained.';}
 toast(result.warning??(reviewed?'Marked reviewed':'Marked unreviewed; notes retained'));
 }catch(e){box.checked=!reviewed;showError(e);}finally{box.disabled=false;}}
''' +s[pos:];p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/style.css');s=p.read_text(encoding='utf8');s+='''
.queue-row{display:flex;align-items:center;border-left:3px solid transparent}.queue-row.active{border-left-color:var(--blue);background:white}.queue-row .queue-item{flex:1;min-width:0;width:auto;border-left:0;overflow-wrap:anywhere}.review-tick{flex:0 0 auto;width:16px;height:16px;margin:0 8px 0 3px;cursor:pointer}.queue-row:hover{background:#f6fafc}
''';p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('record.update(object_id=oid,','record.update(reviewed=True, object_id=oid,',1)
pos=s.index('    def export_csv(self):');s=s[:pos]+'''    def set_reviewed(self, payload):
        oid = str(payload.get("object_id", ""))
        if oid not in self.byid or type(payload.get("reviewed")) is not bool:
            raise ValueError("A known galaxy and boolean reviewed status are required")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.lock:
            record = dict(self.reviews.get(oid) or dict(
                object_id=oid, catalogue_name=self.byid[oid].get("catalogue_name", ""),
                category=next((r["category"] for r in self.sample if r["object_id"]==oid), "extra"),
                disc_decision="not_assessed", bar_decision="not_assessed", centre_decision="not_assessed",
                rule_action="unsure", notes="", settings={}, calculation={}, source_manifest_sha256=self.digest))
            record.update(reviewed=payload["reviewed"], review_status_changed_utc=now)
            if payload["reviewed"]: record["reviewed_utc"] = now
            updated = dict(self.reviews); updated[oid] = record
            atomic_json(self.review_path, updated); self.reviews = updated
            warning = None
            try: (self.output / "MER_VIS_saved_reviews.csv").write_bytes(self.export_csv())
            except PermissionError: warning = "Status saved in JSON. Close the CSV in Excel to refresh the CSV copy."
        return dict(saved=True, review=record, warning=warning)

''' +s[pos:]
s=s.replace('fields = ["object_id","catalogue_name"','fields = ["object_id","reviewed","catalogue_name"',1);s=s.replace('result = {k:r.get(k,"") for k in fields}','result = {k:r.get(k,"") for k in fields}\n                result["reviewed"] = r.get("reviewed", True)',1)
s=s.replace('if self.path == "/api/review":','if self.path == "/api/review-status": return self.send(self.server.store.set_reviewed(payload))\n            if self.path == "/api/review":',1)
p.write_text(s,encoding='utf8')
