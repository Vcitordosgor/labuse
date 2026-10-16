import { ouvrir, aller, shot, lien, debordements, API } from './harness.mjs';
const FAM = '09-admin';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.admin());
await sleep(1500);

// --- Fiche compte : parcourir les onglets (lecture seule) ---
await page.locator('[data-admin-section="licences"]').first().click();
await sleep(2000);
await page.locator('button').filter({ hasText: /^Tous/ }).first().click().catch(()=>{});
await sleep(1200);
await page.locator('button').filter({ hasText: /jamais|il y a|aujourd'hui|hier|@ex\.test/i }).first().click().catch(()=>{});
await sleep(1500);
for (const onglet of ['Activité', 'Facturation', 'IA']) {
  const t = page.locator('button, [role="tab"]').filter({ hasText: new RegExp('^'+onglet+'$','i') }).first();
  if (await t.count()) { await t.click().catch(()=>{}); await sleep(1200); await shot(page, FAM, 'fiche_onglet_'+onglet);
    const b = await page.locator('body').innerText();
    console.log(onglet, 'bad?', /NaN|undefined/.test(b), '| snip:', (b.match(/Stripe|abonnement|MRR|past_due|€|quota|plafond|coût/gi)||[]).slice(0,6));
  } else console.log(onglet, 'ONGLET ABSENT');
}

// --- IA section : comparer chiffres UI vs API ---
await page.locator('[data-admin-section="ia"]').first().click();
await sleep(2200);
const body = await page.locator('body').innerText();
console.log('\n=== IA SECTION ===');
console.log((body.replace(/\s+/g,' ').match(/Coût du mois[\s\S]{0,60}|provider|anthropic|haiku|sonnet|doctrine[\s\S]{0,80}|projection[\s\S]{0,40}/gi)||[]).slice(0,8));
// chiffres clés
const api = await (await fetch(API+'/admin/ia')).json();
console.log('API mois.cout_eur', api.mois.cout_eur, '| projection', api.projection_fin_mois_eur, '| modeles', api.blocs ? '' : '', '| budget', api.budget_defaut_eur);
console.log('UI affiche 0,51 ?', body.includes('0,51'), '| 1,05 ?', body.includes('1,05'), '| haiku ?', /haiku/i.test(body), '| sonnet ?', /sonnet/i.test(body), '| doctrine ?', /doctrine|ne calcule ni/i.test(body));
// quotas par compte
console.log('quotas/par licence présents?', /quota|par licence|plafond|Vous \(admin/i.test(body));
await shot(page, FAM, 'ia_full', { full: true });
const deb = await debordements(page);
console.log('deb', deb.length, JSON.stringify(deb.slice(0,3)));

console.log('\nJOURNAL', journal.consoleErrors.length, journal.httpErrors.length, journal.pageErrors.length);
if (journal.httpErrors.length) console.log(journal.httpErrors);
await browser.close();
