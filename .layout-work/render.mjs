import {mkdir, writeFile} from 'node:fs/promises';
import {resolve, join} from 'node:path';
import {pathToFileURL} from 'node:url';

const target = resolve(process.argv[2] || 'technicalhub_srm_proposal_doc.html');
const out = resolve(process.argv[3] || '.layout-work/previews');
const selected = process.argv[4] ? process.argv[4].split(',').map(Number) : null;
const tabs = await (await fetch('http://127.0.0.1:9417/json/list')).json();
const tab = tabs.find(t => t.type === 'page');
if (!tab) throw new Error('No headless page target');
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((ok, fail) => {ws.addEventListener('open',ok,{once:true});ws.addEventListener('error',fail,{once:true});});
let serial=0;
const pending=new Map();
ws.addEventListener('message',e=>{
  const msg=JSON.parse(e.data);
  if(!msg.id) return;
  const item=pending.get(msg.id);
  if(!item) return;
  clearTimeout(item.timer); pending.delete(msg.id);
  if(msg.error) item.fail(new Error(JSON.stringify(msg.error))); else item.ok(msg.result);
});
function call(method,params={}){
  return new Promise((ok,fail)=>{
    const id=++serial;
    const timer=setTimeout(()=>{pending.delete(id);fail(new Error('Timeout: '+method));},45000);
    pending.set(id,{ok,fail,timer});
    ws.send(JSON.stringify({id,method,params}));
  });
}
async function evaluate(expression){
  const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}
try{
  await call('Page.enable');
  await call('Runtime.enable');
  await call('Emulation.setEmulatedMedia',{media:'screen'});
  await call('Emulation.setDeviceMetricsOverride',{width:1120,height:1300,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:pathToFileURL(target).href});
  for(let i=0;i<60;i++){
    const ready=await evaluate(`document.readyState === 'complete' && [...document.images].every(i=>i.complete)`);
    if(ready) break;
    await new Promise(r=>setTimeout(r,100));
  }
  const assetLoads=await evaluate(`(async()=>{await document.fonts.ready;const refs=[...document.querySelectorAll('svg image')].map(i=>i.getAttribute('href'));const loaded=await Promise.all(refs.map(src=>new Promise(ok=>{const i=new Image();i.onload=()=>ok({src,ok:!!i.naturalWidth});i.onerror=()=>ok({src,ok:false});i.src=src;})));await new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)));return loaded;})()`);
  const metrics=await evaluate(`(()=>{
    const box=e=>{const r=e.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,bottom:r.bottom+scrollY,right:r.right+scrollX};};
    return {textOverflow:[...document.querySelectorAll('.learning-list li,.program-intro,.credential-notes')].filter(e=>e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2).map(e=>({class:e.className,text:e.textContent.trim(),scrollHeight:e.scrollHeight,clientHeight:e.clientHeight})),images:[...document.images].map(i=>({src:i.getAttribute('src'),complete:i.complete,ok:!!i.naturalWidth})),pages:[...document.querySelectorAll('section.page')].map((p,i)=>{
      const b=box(p),f=p.querySelector('.footer,.page-footer'),fb=f?box(f):null,c=p.querySelector('.program-content');
      const items=[...p.querySelectorAll('img,.brand-mark,.badge-mark,.outcome,.cohort-gallery,.vendor-pathway-strip')].map(e=>({tag:e.tagName,class:e.className.baseVal??e.className,src:e.getAttribute('src')||e.getAttribute('aria-label'),...box(e)}));
      const parts=c?[...c.children].map(e=>({class:e.className.baseVal??e.className,...box(e)})):[];
      return {number:i+1,heading:p.querySelector('h2,h1')?.textContent.trim(),...b,scrollHeight:p.scrollHeight,clientHeight:p.clientHeight,footer:fb,content:c?box(c):null,parts,items};
    })};
  })()`);
  metrics.assetLoads=assetLoads;
  await mkdir(out,{recursive:true});
  await writeFile(join(out,'metrics.json'),JSON.stringify(metrics,null,2));
  for(const p of metrics.pages){
    if(selected && !selected.includes(p.number)) continue;
    const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:p.x,y:p.y,width:p.width,height:p.height,scale:1}});
    await writeFile(join(out,'page-'+String(p.number).padStart(2,'0')+'.png'),Buffer.from(shot.data,'base64'));
  }
  await call('Emulation.setEmulatedMedia',{media:'print'});
  const pdf=await call('Page.printToPDF',{printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,scale:1,marginTop:0,marginBottom:0,marginLeft:0,marginRight:0});
  const pdfBytes=Buffer.from(pdf.data,'base64');
  await writeFile(join(out,'proposal-layout-preview.pdf'),pdfBytes);
  const pdfPages=[...pdfBytes.toString('latin1').matchAll(/\/Type\s*\/Page\b/g)].length;
  await call('Emulation.setEmulatedMedia',{media:''});
  const issues=metrics.pages.flatMap(p=>p.items.filter(i=>i.right>p.right+1 || i.x<p.x-1 || (p.footer&&i.bottom>p.footer.y-3)).map(i=>({page:p.number,item:i.class,src:i.src,bottom:i.bottom,footer:p.footer?.y})));
  console.log(JSON.stringify({pages:metrics.pages.length,pdfPages,brokenImages:[...metrics.images,...assetLoads].filter(i=>!i.ok),textOverflow:metrics.textOverflow,issues,output:out},null,2));
}finally{ws.close();}
