import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=criteres');
await page.waitForTimeout(3000);

// The newest Cilaos alerte (surface 500) should be at the top. Click its "Mettre en pause".
const paused = await page.evaluate(() => {
  // find a card mentioning Cilaos with "Mettre en pause"
  const cards = [...document.querySelectorAll('[data-veille-alerte], article, li, div')].filter(c => /Cilaos/.test(c.innerText) && /Mettre en pause/.test(c.innerText));
  if (!cards.length) return 'no-card';
  const b = [...cards[0].querySelectorAll('button')].find(x=>/Mettre en pause/.test(x.innerText));
  if (b) { b.click(); return 'paused'; }
  return 'no-btn';
});
console.log('pause:', paused);
await page.waitForTimeout(2000);
await shot(page, F, 'B_alerte_en_pause', { full: true });
console.log('HTTP1', JSON.stringify(journal.httpErrors.slice(0,5)));
await browser.close();
