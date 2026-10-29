/* Browser-independent interaction tests. Canvas rendering needs a visual check. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const pixel = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1cAAAAASUVORK5CYII=';
const drawCalls=[];
class Element {
  constructor(tag='div'){this.tagName=tag;this.value='';this.children=[];this.options=[];this.style={};this.dataset={};this.hidden=false;this.checked=false;this.disabled=false;this.clientWidth=400;this.width=400;this.height=400;this.classList={toggle(){}};}
  append(...nodes){this.children.push(...nodes);if(this.tagName==='select')for(const n of nodes){this.options.push(n);if(!this.value)this.value=n.value;}}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  addEventListener(name,fn){this['event_'+name]=fn;}
  getBoundingClientRect(){return {left:0,top:0,width:400,height:400};}
  setPointerCapture(){}
  scrollIntoView(){this.scrolled=true;}
  getContext(){return {fillRect(){},drawImage(...args){drawCalls.push(args);},beginPath(){},moveTo(){},lineTo(){},stroke(){},putImageData(){},createImageData(w,h){return {data:new Uint8ClampedArray(w*h*4)};}};}
  toDataURL(){return pixel;}
}
const elements={};
const doc={getElementById(id){return elements[id]??=new Element(id==='galaxy'?'select':'div');},createElement(tag){return new Element(tag);},createTextNode(text){return {textContent:text};}};
const defaults={move_factor:.5,dilation:2,minarea:5,alpha:1e-6,min_distance:0,gaussian_fwhm:1,bg_mean:null,bg_variance:null,gain:1,soft_bias:0};
const geometry={x:2,y:2,a:1,q:.7,theta:0,scale:.1,bar_min:.1,bar_max:.2,disc_min:.3,disc_max:.5};
geometry.outer_disc={x:2,y:2,a:5,q:.6,theta:.2,sma_arcsec:.5,source:'automatic_outer_disc'};
const processing_bounds={x0:0,x1:5,y0:0,y1:5};
const detection={object_id:'test',processing_policy:'fit_galaxy_crop_v1',processing_bounds,run_id:'a'.repeat(32),shape:[5,5],params:defaults,geometry,target:1,background:{sigma:.01},objects:[{label:1,target:true,pixels:3,mask:false,intersects_aoi:true},{label:2,target:false,pixels:6,mask:true,intersects_aoi:true}]};
const labelArray=new Uint32Array(25);labelArray[12]=1;labelArray[6]=2;
const posts=[];
const context={document:doc,devicePixelRatio:1,Image:class {async decode(){}},Uint32Array,Float32Array,Uint8ClampedArray,Set,Math,Number,Error,console,setTimeout,clearTimeout,
  window:{confirm:()=>true,addEventListener(){}},confirm:()=>true,
  fetch:async(url,opts)=>{const body=opts?.body?JSON.parse(opts.body):null;if(body)posts.push({url,body});let value;
    if(url==='/api/config')value={defaults,targets:[{object_id:'test',status:'reviewed_supported'}],output:'test-output'};
    else if(url.startsWith('/api/galaxy'))value={object_id:'test',shape:[5,5],geometry,processing_bounds,latest:null};
    else if(url.startsWith('/api/display'))return {ok:true,headers:{get:()=>JSON.stringify({width:5,height:5,factor:1,stats:{minimum:0,maximum:1,median:.1,robust_sigma:.01}})},arrayBuffer:async()=>new Float32Array(25).fill(.1).buffer};
    else if(url.includes('labels.bin'))return {arrayBuffer:async()=>labelArray.buffer};
    else if(url==='/api/mask')value={png:pixel.split(',')[1],masked_fraction:.2,aoi_masked_fraction:.1};
    else if(url==='/api/save')value={...body,review_id:'b'.repeat(32),object_id:'test'};
    else throw Error('Unexpected endpoint '+url);
    return {ok:true,json:async()=>value};}};
vm.createContext(context);
const source=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');vm.runInContext(source,context);
const run=code=>vm.runInContext(code,context);
(async()=>{
  await new Promise(resolve=>setTimeout(resolve,10));
  if(!run('galaxy'))throw Error('Startup failed: '+elements.status?.textContent);
  assert.equal(run('galaxy.object_id'),'test');
  assert.equal(elements.stretch.value,'autostf');assert.equal(elements.showEllipses.value,'off');
  assert.equal(run('view.span'),5);assert.equal(elements.showAOI,undefined);
  assert.equal(run('visibleEllipses().length'),0);
  assert.ok(Math.abs(run('autoSTFValue(.1,autoSTFParameters({minimum:0,maximum:1,median:.1,robust_sigma:.01}))')-.25)<1e-12);
  run('proposedEllipses=[{x:2,y:2,a:4,q:.6,theta:0,sma_arcsec:.4},{x:2,y:2,a:1.5,q:.5,theta:.5,sma_arcsec:.15}]');
  elements.showEllipses.value='both';assert.equal(run('visibleEllipses().length'),2);
  elements.showEllipses.value='disc';assert.equal(run('visibleEllipses()[0].kind'),'disc');
  elements.showEllipses.value='off';
  const raw=run('displayPixels.slice()');elements.gamma.value=2;run('stretchDisplay()');
  assert.equal(elements.gammaValue.value,'2.00');assert.deepEqual(Array.from(run('displayPixels')),Array.from(raw));
  context.fixture=detection;await run('useResult(fixture)');
  assert.equal(run('selected.has(2)'),true);
  await run('toggle(1)');assert.equal(run('selected.has(1)'),true);
  await run('toggle(1)');assert.equal(run('selected.has(1)'),false);
  await run('toggle(2)');assert.equal(run('selected.has(2)'),false);
  await elements.undo.onclick();assert.equal(run('selected.has(2)'),true);
  elements.confirm.checked=true;elements.confirm.onchange();
  assert.equal(elements.save.disabled,false);
  await elements.save.onclick();assert.equal(run('accepted.review_id'),'b'.repeat(32));
  elements.minarea.value=6;elements.minarea.oninput();assert.equal(elements.save.disabled,true);assert.equal(elements.refit.disabled,true);
  await elements.save.onclick();assert.equal(posts.filter(p=>p.url==='/api/save').length,1);
  assert.match(elements.status.textContent,/changed controls/);
  run('setParams(fixture.params)');await run('useResult(fixture)');
  elements.pin.onclick();assert.equal(elements.referenceSection.hidden,false);
  const pinned=run('reference.overlay');await run('toggle(2)');assert.equal(run('reference.overlay'),pinned);
  await run('showSweep([fixture])');assert.equal(elements.sweepResults.children.length,1);
  assert.equal(elements.sweepSection.scrolled,true);assert.match(elements.sweepProgress.textContent,/1 comparison results ready/);
  assert.match(elements.sweepProgress.textContent,/Detection: Original image/);
  run('view.span=100');
  await run('showSweep([fixture,fixture,fixture,fixture,fixture])');
  const before=drawCalls.slice(-10).map(call=>call.slice(1));
  const requestsBeforeZoom=posts.length;
  elements.zoomIn.onclick();
  const zoomed=drawCalls.slice(-10).map(call=>call.slice(1));
  for(let i=0;i<10;i++)assert.ok(zoomed[i][2]>before[i][2]);
  elements.zoomOut.onclick();
  const restored=drawCalls.slice(-10).map(call=>call.slice(1));
  for(let i=0;i<10;i++)assert.ok(Math.abs(restored[i][2]-before[i][2])<1e-10);
  run('view.x+=3;render()');
  const panned=drawCalls.slice(-10).map(call=>call.slice(1));
  for(let i=0;i<10;i++)assert.notEqual(panned[i][0],restored[i][0]);
  assert.equal(posts.length,requestsBeforeZoom);
  elements.projectedPreset.onclick();assert.equal(elements.detect_on.value,'original+residual');
  assert.equal(Number(elements.residual_max_area.value),100);assert.equal(Number(elements.moveNumber.value),.9);
  console.log('PASS: load, centre-label masking, toggle/undo, save, dirty-parameter guards, frozen reference, comparison');
})().catch(error=>{console.error(error);process.exitCode=1;});
