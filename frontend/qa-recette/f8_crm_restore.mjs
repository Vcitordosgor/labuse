import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);
// The BA0005 card (entry 93) is now in "Contacté". Find the select in the card showing BA0005 and move back to "Repérée".
const done = await page.evaluate(() => {
  const selects = [...document.querySelectorAll('select')];
  for (const s of selects) {
    const card = s.closest('div');
    // climb to a card-ish container that mentions BA0005
    let c = s; for (let i=0;i<8 && c;i++){ if(/97404000BA0005/.test(c.innerText||'')) break; c=c.parentElement; }
    if (c && /97404000BA0005/.test(c.innerText||'') && [...s.options].some(o=>o.textContent.trim()==='Repérée')) {
      const opt=[...s.options].find(o=>o.textContent.trim()==='Repérée');
      s.value=opt.value; s.dispatchEvent(new Event('change',{bubbles:true}));
      return 'restored';
    }
  }
  return 'card-not-found';
});
console.log('restore:', done);
await page.waitForTimeout(2500);
await shot(page, F, 'C_crm_restore', { full: false });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)));
await browser.close();
