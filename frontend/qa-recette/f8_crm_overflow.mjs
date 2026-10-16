import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);
// find the element containing the long A string and measure
const info = await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter(e => /AAAAAAAAAAAAAAAAAAAA/.test(e.textContent||'') && e.children.length===0);
  if (!els.length) return 'not-found';
  const e = els[0];
  const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  // does it overflow the viewport or its column?
  return { tag:e.tagName, cls:String(e.className), scrollW:e.scrollWidth, clientW:e.clientW||e.clientWidth,
           rectW:Math.round(r.width), rectRight:Math.round(r.right), viewportW:window.innerWidth,
           wordBreak:cs.wordBreak, overflowWrap:cs.overflowWrap, whiteSpace:cs.whiteSpace, overflow:cs.overflow };
});
console.log('LONG-NOTE ELEMENT:', JSON.stringify(info, null, 1));
// check page-level horizontal scroll
const pageScroll = await page.evaluate(() => ({ docScrollW: document.documentElement.scrollWidth, winW: window.innerWidth, overflowsPage: document.documentElement.scrollWidth > window.innerWidth + 2 }));
console.log('PAGE SCROLL:', JSON.stringify(pageScroll));
await shot(page, F, 'C_crm_note_overflow', { full: false });
await browser.close();
