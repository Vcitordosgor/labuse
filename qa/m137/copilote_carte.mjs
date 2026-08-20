import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const Q = process.argv[2] || 'combien de parcelles en procédure collective à Saint-Paul';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0,160)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
// ouvrir le Copilote (rail « IA »)
await soft(async () => { await page.locator('button[title="IA"]').click(); await page.waitForTimeout(1200); }, 'ouvrir copilote');
// poser la question
await soft(async () => {
  const t = page.locator('[data-brief]').first();
  await t.click(); await t.fill(Q); await page.waitForTimeout(300);
  const env = page.locator('[data-accueil-envoyer]');
  if (await env.count()) await env.click(); else await t.press('Enter');
}, 'poser question');
// attendre la réponse avec le bouton carte
await page.waitForSelector('[data-reponse-carte]', { timeout: 45000 }).catch(() => console.log('WARN pas de bouton carte'));
const btnTxt = await page.locator('[data-reponse-carte]').innerText().catch(()=>'(absent)');
const reponseTxt = await page.locator('[data-reponse]').first().innerText().catch(()=>'');
console.log('bouton:', btnTxt.replace(/\s+/g,' ').trim());
const mCount = reponseTxt.match(/\b(\d{1,4})\s+parcelle/);
const annonce = mCount ? mCount[1] : '?';
console.log('compte annoncé par Copilote:', annonce);
await page.screenshot({ path: `${OUT}/copilote_reponse.png` });
// cliquer « Voir sur la carte »
await soft(async () => { await page.locator("[data-reponse-carte]").click(); await page.waitForTimeout(9000); }, 'clic carte');
// vérifier : listing ouvert + compte
const arrivee = await page.evaluate(() => {
  const panel = document.querySelector('[data-results-panel]');
  const bandeau = document.querySelector('[data-bandeau-chiffres]');
  return { listingVisible: !!(panel && panel.offsetParent !== null), text: (panel?.innerText || '') };
});
console.log('listing visible:', arrivee.listingVisible);
const txt = (arrivee.text || '').replace(/\s+/g, ' ');
// pied de liste en mode commune : « N affichée(s) / TOTAL »
const mFoot = txt.match(/(\d+)\s+affichée[s]?(?:\s*\/\s*(\d+))?/);
const totalListing = mFoot ? (mFoot[2] || mFoot[1]) : null;
console.log('pied de liste:', mFoot ? mFoot[0] : '(non trouvé)', '→ total =', totalListing);
console.log('tail listing:', txt.slice(-120));
const mArr = { 1: totalListing };
await page.screenshot({ path: `${OUT}/copilote_arrivee_carte.png` });
await b.close();
const ok = arrivee.listingVisible && totalListing === annonce;
console.log(ok ? `OK — listing ouvert, compte ${totalListing} = annoncé ${annonce}` : "À VÉRIFIER");
