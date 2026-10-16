import { shot, debordements, BASE } from './harness.mjs';

export async function allerFiche(page, idu){
  const t0=Date.now();
  await page.goto(BASE + `#idu=${idu}`, { waitUntil:'domcontentloaded', timeout:45000 });
  await page.reload({ waitUntil:'domcontentloaded' });
  try { await page.waitForLoadState('networkidle',{timeout:14000}); } catch {}
  await page.waitForTimeout(2200);
  return Date.now()-t0;
}

// Open each drawer one by one (accordion), capture its .t-open content.
export async function parcourirTiroirs(page){
  const ids = await page.$$eval('[data-drawer]', els => els.map(e=>e.getAttribute('data-drawer')));
  const result={};
  for (const id of ids){
    const btn = await page.$(`[data-drawer="${id}"] button.tiroir`);
    if(!btn){ result[id]={clickable:false}; continue; }
    const hasChild = await page.$(`[data-drawer="${id}"] .t-open`).then(x=>!!x).catch(()=>false);
    await btn.click({timeout:1500}).catch(()=>{});
    await page.waitForTimeout(350);
    const content = await page.$eval(`[data-drawer="${id}"]`, e=>{
      const o=e.querySelector('.t-open');
      return o ? (o.innerText||'') : '';
    }).catch(()=>'');
    // header value (right side)
    const hv = await page.$eval(`[data-drawer="${id}"] .t-right`, e=>(e.innerText||'').trim()).catch(()=>'');
    result[id]={clickable:true, opened: content.length>0, headVal:hv, content};
    // vide sans explication?
    const t=content.toLowerCase();
    const honest = /non renseigné|non mesuré|non calcul|analyse incomplète|sans objet|absent|aucun|pas de|non disponible|inconnu|non identifié|hors fichier|à vérifier|non résolue|estimé|non rattachée/.test(t);
    result[id].videSansExpl = content.length>0 && content.trim().split('\n').filter(l=>l.trim()).length<2 && !honest;
  }
  return result;
}

export async function entete(page){
  return page.evaluate(()=>{
    let f=null;
    for (const el of document.querySelectorAll('div')){
      if (/Demander à LABUSE/.test(el.innerText||'') && el.scrollHeight>el.clientHeight+20){
        if(!f || el.scrollHeight<f.scrollHeight) f=el;
      }
    }
    const t=(f?f.innerText:document.body.innerText)||'';
    // first block up to the CTAs
    const idx=t.indexOf('Demander à LABUSE');
    return (idx>0?t.slice(0,idx):t.slice(0,500));
  });
}

export async function clicBouton(page, labelRe){
  const btns=await page.$$('button,a[role=button],a');
  for(const b of btns){
    let t=''; try{t=((await b.innerText())||'').trim();}catch{continue;}
    if(labelRe.test(t)){
      const before=page.url();
      const vis = await b.isVisible().catch(()=>false);
      if(!vis) continue;
      await b.click({timeout:2500}).catch(()=>{});
      await page.waitForTimeout(1000);
      return {found:true,label:t.split('\n')[0].slice(0,40),urlBefore:before,urlAfter:page.url()};
    }
  }
  return {found:false};
}
export { shot, debordements };
