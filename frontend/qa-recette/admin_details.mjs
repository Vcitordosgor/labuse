import { ouvrir, aller, shot, lien, debordements } from './harness.mjs';
const FAM = '09-admin';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.admin());
await sleep(2000);

async function go(key) {
  await page.locator(`[data-admin-section="${key}"]`).first().click();
  try { await page.waitForLoadState('networkidle', { timeout: 10000 }); } catch {}
  await sleep(2000);
}

// ---- COMPTES ----
await go('licences');
let body = await page.locator('body').innerText();
console.log('=== COMPTES ===');
// statuts, MRR, à toucher, stripe
console.log('MRR/CA snip:', (body.match(/MRR|Chiffre|à toucher|Stripe|rapprochement/gi)||[]).slice(0,8));
const rows = await page.$$eval('table tr, [data-compte], [role="row"]', (els)=>els.length);
console.log('rows-ish:', rows);
// ouvrir une fiche compte en lecture : cliquer la 1re ligne/compte
const compteBtn = page.locator('button, a, tr').filter({ hasText: /Recette|@|actif|essai|invit/i }).first();
if (await compteBtn.count()) { await compteBtn.click().catch(()=>{}); await sleep(1500); }
await shot(page, FAM, 'comptes_detail', { full: true });
let deb = await debordements(page); console.log('COMPTES deb', deb.length, JSON.stringify(deb.slice(0,3)));
// répertorier boutons d'action (mutants)
let btns = await page.$$eval('button', (els)=>[...new Set(els.map(e=>(e.textContent||'').trim()).filter(t=>t&&t.length<40))]);
console.log('COMPTES boutons:', JSON.stringify(btns));

// ---- DONNEES / CIRCUIT ----
await go('donnees');
body = await page.locator('body').innerText();
console.log('\n=== DONNEES/CIRCUIT ===');
console.log('run/q_v snip:', (body.match(/q_v\d+|réservoir|robinet|verrou|run servi/gi)||[]).slice(0,10));
// ouvrir un réservoir (clic sur un item réservoir)
const reser = page.locator('button, a, [data-reservoir], li').filter({ hasText: /BD TOPO|DVF|cadastre|PPR|RNB|réservoir/i }).first();
if (await reser.count()) { await reser.click().catch(()=>{}); await sleep(1500); await shot(page, FAM, 'circuit_reservoir'); }
deb = await debordements(page); console.log('DONNEES deb', deb.length, JSON.stringify(deb.slice(0,5)));
btns = await page.$$eval('button', (els)=>[...new Set(els.map(e=>(e.textContent||'').trim()).filter(t=>t&&t.length<40))]);
console.log('DONNEES boutons:', JSON.stringify(btns));

// ---- IA ----
await go('ia');
body = await page.locator('body').innerText();
console.log('\n=== IA ===');
console.log('IA snip:', (body.match(/anthropic|haiku|sonnet|doctrine|quota|coût|€|provider/gi)||[]).slice(0,12));
console.log('IA badTokens?', /NaN|undefined/.test(body));
await shot(page, FAM, 'ia_detail', { full: true });
deb = await debordements(page); console.log('IA deb', deb.length, JSON.stringify(deb.slice(0,3)));
btns = await page.$$eval('button', (els)=>[...new Set(els.map(e=>(e.textContent||'').trim()).filter(t=>t&&t.length<40))]);
console.log('IA boutons:', JSON.stringify(btns));

// ---- PRODUIT (overflow) ----
await go('produit');
deb = await debordements(page); console.log('\n=== PRODUIT deb', deb.length, JSON.stringify(deb));
await shot(page, FAM, 'produit_detail', { full: true });

console.log('\nJOURNAL err/http/perr', journal.consoleErrors.length, journal.httpErrors.length, journal.pageErrors.length);
if (journal.httpErrors.length) console.log('HTTP:', journal.httpErrors);
if (journal.consoleErrors.length) console.log('ERR:', journal.consoleErrors);
await browser.close();
