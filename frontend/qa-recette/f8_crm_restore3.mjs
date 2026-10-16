import { ouvrir, aller } from './harness.mjs';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);

// Find the SMALLEST element whose text contains exactly the idu, then find the nearest following select
const res = await page.evaluate(() => {
  // find the idu text node's element
  const all = [...document.querySelectorAll('*')].filter(e => e.children.length<=2 && /97404000BA0005/.test(e.textContent||'') && (e.textContent||'').length < 400);
  if (!all.length) return 'no-idu-el';
  // the card = climb a few parents until we find exactly one select inside
  let card = all[0];
  for (let i=0;i<8;i++){ if (card.querySelectorAll('select').length===1) break; card=card.parentElement; if(!card) break; }
  if (!card) return 'no-card';
  const sel = card.querySelector('select');
  if (!sel) return 'no-select-in-card';
  // confirm current selection options include Repérée & it's the move dropdown
  const opt = [...sel.options].find(o=>o.textContent.trim()==='Repérée');
  if (!opt) return 'no-reperee-option';
  sel.value = opt.value;
  sel.dispatchEvent(new Event('change', { bubbles: true }));
  return 'moved-to-reperee idu-card-text=' + card.innerText.slice(0,50).replace(/\n/g,' ');
});
console.log('restore result:', res);
await page.waitForTimeout(2800);
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)));
await browser.close();
