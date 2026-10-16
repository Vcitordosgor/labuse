import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/99\+/.test((x.innerText||'').trim())); b&&b.click(); });
await page.waitForTimeout(2000);

// Try clicking an individual parcelle event "▲ XX#### : ..." which should open a fiche
const clicked = await page.evaluate(() => {
  const b = [...document.querySelectorAll('button,a,[role="button"]')].find(x => /▲ [A-Z]{1,2}\d+\s*:/.test(x.innerText));
  if (b) { const l=b.innerText.trim().slice(0,50); b.click(); return l; }
  return null;
});
await page.waitForTimeout(3000);
const afterHash = await page.evaluate(()=>location.hash);
const sel = await page.evaluate(() => {
  // is a fiche open? check for parcelle panel title
  const t = document.body.innerText;
  return { idu: (t.match(/\b974\d{11}\b/)||[])[0], hasFiche: /LE BIEN|Identité|SURFACE/.test(t) };
});
console.log('parcelle notif clicked:', JSON.stringify(clicked), 'hash:', afterHash, 'state:', JSON.stringify(sel));
await shot(page, F, 'B_notif_parcelle_navigue', { full: false });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)), 'ERR', journal.consoleErrors.length);
await browser.close();
