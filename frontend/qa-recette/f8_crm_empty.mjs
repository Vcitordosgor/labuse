import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);
// page right through columns to find an empty one showing "Aucune parcelle"
let found=null;
for (let p=0;p<8;p++){
  const txt = await page.evaluate(()=> {
    const e=[...document.querySelectorAll('.empty, [class*="empty"]')].find(x=>/Aucune parcelle/.test(x.textContent||''));
    return e?e.textContent.trim():null;
  });
  if (txt){ found=txt; await shot(page, F, 'C_crm_colonne_vide', {full:true}); break; }
  await page.evaluate(()=>{ const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='›'); b&&b.click(); });
  await page.waitForTimeout(1200);
}
console.log('empty column state:', JSON.stringify(found));
// archived empty-state
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/Archivées/.test(x.innerText)); b&&b.click(); });
await page.waitForTimeout(1800);
const arch = await page.evaluate(()=> {
  const t=document.body.innerText;
  return (t.match(/Aucune carte archivée|\d+ carte/)||['?'])[0];
});
console.log('archived view:', JSON.stringify(arch));
await shot(page, F, 'C_crm_archivees_view', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
