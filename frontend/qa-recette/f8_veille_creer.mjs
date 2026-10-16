import { ouvrir, aller, shot, lien } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.fiche('97411000AT0427'));
await page.waitForTimeout(3000);

// find a "suivre / surveiller / cloche" control on the fiche
const found = await page.evaluate(() => {
  const all = [...document.querySelectorAll('button,[role="button"],a')];
  return all.map(b => ({ t: (b.innerText||'').trim().slice(0,30), aria: b.getAttribute('aria-label')||'', title: b.getAttribute('title')||'' }))
    .filter(x => /suivr|surveil|cloche|veille|alerte/i.test(x.t+x.aria+x.title));
});
console.log('veille controls on fiche:', JSON.stringify(found));
await shot(page, F, 'B_fiche_boutons', { full: false });

// click the suivre button
const clicked = await page.evaluate(() => {
  const all = [...document.querySelectorAll('button,[role="button"],a')];
  const b = all.find(x => /suivr|surveil/i.test((x.innerText||'')+(x.getAttribute('aria-label')||'')+(x.getAttribute('title')||'')));
  if (b) { b.click(); return (b.innerText||b.getAttribute('aria-label')||'').trim(); }
  return null;
});
console.log('clicked:', JSON.stringify(clicked));
await page.waitForTimeout(2500);
const after = await page.evaluate(() => {
  const all = [...document.querySelectorAll('button,[role="button"],a')];
  const b = all.find(x => /suivi|surveil|ne plus|retirer/i.test((x.innerText||'')+(x.getAttribute('aria-label')||'')+(x.getAttribute('title')||'')));
  return b ? (b.innerText||b.getAttribute('aria-label')||'').trim() : null;
});
console.log('after click (state toggled?):', JSON.stringify(after));
await shot(page, F, 'B_fiche_apres_suivre', { full: false });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
