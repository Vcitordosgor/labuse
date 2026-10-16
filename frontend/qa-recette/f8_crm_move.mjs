import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);

// Use the "Déplacer vers…" select on the first card (BA0005 in Repérée) -> move to "Contacté"
// It's a <select>; find one near BA0005
const moved = await page.evaluate(() => {
  const selects = [...document.querySelectorAll('select')];
  for (const s of selects) {
    const opts = [...s.options].map(o=>o.textContent.trim());
    if (opts.includes('Déplacer vers…') && opts.includes('Contacté')) {
      // locate card idu near it
      const card = s.closest('[data-pipeline-card],div');
      return { optCount: opts.length, hasContacte: true };
    }
  }
  return null;
});
console.log('move-select found:', JSON.stringify(moved));
// Do the move on the FIRST such select
await page.evaluate(() => {
  const s = [...document.querySelectorAll('select')].find(x => [...x.options].some(o=>o.textContent.trim()==='Déplacer vers…'));
  if (s) {
    s.value = [...s.options].find(o=>o.textContent.trim()==='Contacté').value;
    s.dispatchEvent(new Event('change', { bubbles: true }));
  }
});
await page.waitForTimeout(2800);
await shot(page, F, 'C_crm_apres_move', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,8)), 'ERR', journal.consoleErrors.length);
await browser.close();
