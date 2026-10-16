import { ouvrir, aller, shot, lien } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
// Use a parcel NOT already in CRM — pick RNU/BD0967
await aller(page, lien.fiche('97417000BD0967'));
await page.waitForTimeout(3500);
// find the "Ajouter au CRM / + CRM" control
const ctrl = await page.evaluate(() => {
  const all=[...document.querySelectorAll('button,a,[role="button"]')];
  const b=all.find(x=>/ajouter au CRM|\+ ?CRM|au CRM/i.test((x.innerText||'')+(x.getAttribute('aria-label')||'')));
  return b?{t:(b.innerText||'').trim().slice(0,30),aria:b.getAttribute('aria-label')||''}:null;
});
console.log('CRM control on fiche:', JSON.stringify(ctrl));
await shot(page, F, 'C_fiche_crm_bouton', { full: false });

// click it
const clicked = await page.evaluate(() => {
  const all=[...document.querySelectorAll('button,a,[role="button"]')];
  const b=all.find(x=>/ajouter au CRM|\+ ?CRM/i.test((x.innerText||'')+(x.getAttribute('aria-label')||'')));
  if(b){b.click();return true;}return false;
});
console.log('clicked add-to-CRM:', clicked);
await page.waitForTimeout(2000);
// a menu of columns may appear; pick first / confirm
await shot(page, F, 'C_fiche_crm_menu', { full: false });
const afterState = await page.evaluate(() => {
  const all=[...document.querySelectorAll('button,a')];
  const inpipe=all.find(x=>/retirer du CRM|dans le CRM|au pipeline|Déplacer vers/i.test(x.innerText||''));
  const menu=all.map(x=>x.innerText.trim()).filter(t=>/Repérée|Propriétaire à identifier|Contact à préparer/.test(t)).slice(0,3);
  return { inpipe: inpipe?inpipe.innerText.trim().slice(0,30):null, menu };
});
console.log('after state:', JSON.stringify(afterState));
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
