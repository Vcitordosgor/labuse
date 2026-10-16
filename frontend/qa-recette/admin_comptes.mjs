import { ouvrir, aller, shot, lien, debordements } from './harness.mjs';
const FAM = '09-admin';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.admin());
await sleep(1500);
await page.locator('[data-admin-section="licences"]').first().click();
await sleep(2500);

// segments disponibles
const segs = await page.$$eval('button', (els)=>els.map(e=>(e.textContent||'').trim()).filter(t=>/toucher|Actif|Essai|Invit|Suspend|Tous/i.test(t)&&t.length<30));
console.log('SEGMENTS:', JSON.stringify([...new Set(segs)]));

// cliquer « Tous » pour voir toute la liste
const tous = page.locator('button').filter({ hasText: /^Tous/ }).first();
if (await tous.count()) { await tous.click(); await sleep(1800); }
await shot(page, FAM, 'comptes_liste_tous', { full: true });

// compter les lignes de compte (chaque ligne a un bouton d'ouverture). On cherche initiales + MRR
const body = await page.locator('body').innerText();
console.log('colonnes/mots-clés:', (body.match(/MRR|visite|plan|à faire|Stripe|rapprochement|à toucher/gi)||[]).slice(0,10));

// ouvrir une VRAIE fiche compte : cliquer la 1re ligne client (pas un bouton d'action)
// les lignes sont des boutons avec initiales. On prend un bouton contenant « il y a » ou « jamais » (dernière visite) ou un @.
const ligne = page.locator('button').filter({ hasText: /jamais|il y a|aujourd'hui|hier|@ex\.test/i }).first();
let opened = false;
if (await ligne.count()) { await ligne.click().catch(()=>{}); await sleep(1800); opened = true; }
const body2 = await page.locator('body').innerText();
const fiche = /← Comptes|Aperçu|Activité|Facturation/i.test(body2);
console.log('fiche ouverte?', opened, 'onglets présents?', fiche);
console.log('onglets:', (body2.match(/Aperçu|Activité|Facturation|IA\b/gi)||[]).slice(0,6));
await shot(page, FAM, 'comptes_fiche', { full: true });

// boutons d'action présents sur la fiche (mutants à répertorier, NON cliqués)
const actions = await page.$$eval('button', (els)=>[...new Set(els.map(e=>(e.textContent||'').trim()).filter(t=>t&&t.length<40&&/Convertir|Suspendre|Rétablir|Prolonger|Déconnecter|envoyer|Créer|invitation|relancer|mail/i.test(t)))]);
console.log('ACTIONS MUTANTES fiche:', JSON.stringify(actions));

const deb = await debordements(page);
console.log('deb', deb.length, JSON.stringify(deb.slice(0,3)));
console.log('badTokens?', /NaN|undefined/.test(body2));
console.log('JOURNAL', journal.consoleErrors.length, journal.httpErrors.length, journal.pageErrors.length);
if (journal.httpErrors.length) console.log(journal.httpErrors);
await browser.close();
