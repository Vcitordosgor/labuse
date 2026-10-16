import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);

// 1) open a "+ Note" editor (without saving)
const noteOpen = await page.evaluate(() => {
  const b = document.querySelector('[data-crm-note-add]');
  if (b) { b.click(); return true; } return false;
});
await page.waitForTimeout(1000);
const hasEditor = await page.$('[data-crm-note]');
console.log('+ Note add button opens editor:', noteOpen, 'editor present:', !!hasEditor);
await shot(page, F, 'C_crm_note_editor', { full: false });
// close without saving (Escape / click elsewhere)
await page.keyboard.press('Escape');
await page.waitForTimeout(500);

// 2) click card body -> edit screen
const editOpened = await page.evaluate(() => {
  // card body (not the idu button, not note, not select)
  const card = document.querySelector('[data-pipeline-card], [data-crm-card]') || [...document.querySelectorAll('div')].find(d=>/408 m²/.test(d.innerText)&&/Déplacer vers/.test(d.innerText));
  return card ? card.className.slice(0,40) : 'no-card-selector';
});
console.log('card selector:', editOpened);

// 3) Check an empty column shows empty-state text
const emptyCols = await page.evaluate(() => {
  const states = [...document.querySelectorAll('*')].filter(e=>/Aucune|vide|Rien|Glissez|glisser une carte ici/i.test(e.textContent||'') && e.children.length<=2);
  return states.map(s=>s.textContent.trim().slice(0,60)).slice(0,6);
});
console.log('empty-state texts:', JSON.stringify(emptyCols));
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
