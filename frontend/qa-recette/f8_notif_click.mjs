import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
// open cloche
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/99\+/.test((x.innerText||'').trim())); b&&b.click(); });
await page.waitForTimeout(2000);
// click a "Voir les N →" grouped notif
const beforeHash = await page.evaluate(()=>location.hash);
const clicked = await page.evaluate(() => {
  const b = [...document.querySelectorAll('button,a')].find(x => /Voir les \d+ →|▲ [A-Z]{2}\d+/.test(x.innerText));
  if (b) { const label=b.innerText.trim().slice(0,40); b.click(); return label; }
  return null;
});
await page.waitForTimeout(2500);
const afterHash = await page.evaluate(()=>location.hash);
console.log('notif clicked:', JSON.stringify(clicked), 'hash', beforeHash, '->', afterHash);
await shot(page, F, 'B_notif_navigation', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)), 'ERR', journal.consoleErrors.length);

// now test mail digest toggle: open cloche -> préférences
await aller(page, '');
await page.waitForTimeout(2000);
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/99\+/.test((x.innerText||'').trim())); b&&b.click(); });
await page.waitForTimeout(1500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>/préférences/i.test(x.innerText)); b&&b.click(); });
await page.waitForTimeout(1800);
const prefsBody = await page.evaluate(() => {
  const p = [...document.querySelectorAll('[role="dialog"],[class*="notif"],[class*="popover"]')].map(x=>x.innerText).join('\n');
  return p.slice(0,1200) || document.body.innerText.slice(0,1200);
});
console.log('--- PREFS CLOCHE ---\n', prefsBody);
await shot(page, F, 'B_cloche_preferences', { full: true });
console.log('HTTP2', JSON.stringify(journal.httpErrors.slice(0,5)), 'ERR', journal.consoleErrors.length);
await browser.close();
