import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);

// find the bell: button containing "99+" or an svg bell in header
const bellInfo = await page.evaluate(() => {
  const cands = [...document.querySelectorAll('button')];
  const b = cands.find(x => /99\+|^\d+$/.test((x.innerText||'').trim()) || x.getAttribute('aria-label')?.match(/notif|cloche|alerte/i));
  return b ? { txt: b.innerText.trim(), aria: b.getAttribute('aria-label') } : null;
});
console.log('bell candidate:', JSON.stringify(bellInfo));

// Click the element showing "99+"
const clicked = await page.evaluate(() => {
  const cands = [...document.querySelectorAll('button')];
  const b = cands.find(x => /99\+/.test((x.innerText||'').trim()));
  if (b) { b.click(); return true; }
  return false;
});
console.log('clicked 99+:', clicked);
await page.waitForTimeout(2500);
await shot(page, F, 'B_cloche_ouverte', { full: true });
const body = await page.evaluate(() => {
  // dropdown likely a fixed panel
  const panels = [...document.querySelectorAll('[role="dialog"],[class*="dropdown"],[class*="notif"],[class*="popover"]')];
  const txt = panels.map(p=>p.innerText).join('\n---\n');
  return txt.slice(0,1800) || document.body.innerText.slice(0,1800);
});
console.log('--- CLOCHE PANEL ---\n', body);
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
