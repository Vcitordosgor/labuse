import { ouvrir, aller } from './harness.mjs';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);

// locate card BA0005: it should be in the Contacté column now. Navigate columns via the "›" pager until visible.
// Simpler: use native select interaction via Playwright. Find the select whose ancestor card text has BA0005.
const handles = await page.$$('select');
let target=null;
for (const h of handles) {
  const txt = await h.evaluate(s => { let c=s; for(let i=0;i<8&&c;i++){ if(/97404000BA0005/.test(c.innerText||'')) return c.innerText.slice(0,60); c=c.parentElement;} return ''; });
  if (txt) { target=h; console.log('found card select, ctx:', txt); break; }
}
if (target) {
  await target.selectOption({ label: 'Repérée' });
  await page.waitForTimeout(2800);
  console.log('selectOption done');
} else {
  console.log('BA0005 select not on current page view; paging...');
  // page right to find it
  for (let p=0;p<8 && !target;p++){
    await page.evaluate(()=>{ const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='›'); b&&b.click(); });
    await page.waitForTimeout(1200);
    const hs = await page.$$('select');
    for (const h of hs){ const txt=await h.evaluate(s=>{let c=s;for(let i=0;i<8&&c;i++){if(/97404000BA0005/.test(c.innerText||''))return 'Y';c=c.parentElement;}return '';}); if(txt){target=h;break;} }
  }
  if (target){ await target.selectOption({label:'Repérée'}); await page.waitForTimeout(2800); console.log('restored after paging'); }
  else console.log('still not found');
}
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)));
await browser.close();
