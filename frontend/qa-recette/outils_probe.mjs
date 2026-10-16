import { ouvrir, shot } from './harness.mjs';
import { FAM, attendreOutil, etatOutil, allerOutil as aller } from './_outils_lib.mjs';
import { lien } from './harness.mjs';

const key = process.argv[2];
const idu = process.argv[3];
const label = process.argv[4] || 'probe';
const wait = parseInt(process.argv[5] || '3000', 10);

const { browser, page, journal } = await ouvrir({});
const ms = await aller(page, lien.outilSurParcelle(key, idu));
await attendreOutil(page, { timeout: 70000 });
await page.waitForTimeout(wait);
const et = await etatOutil(page);
console.log(`[${key}/${idu}] loadMs=${ms} len=${et.len} spinners=${et.spinners} NaN=${et.hasNaN} err=${journal.consoleErrors.length} http=${journal.httpErrors.length} page=${journal.pageErrors.length}`);
console.log('FULL TEXT:\n', et.extrait);
// texte complet nettoyé plus long
const long = await page.evaluate(()=> (document.body.innerText||'').replace(/\s+/g,' ').trim().slice(0,2500));
console.log('\nLONG:\n', long);
if (journal.httpErrors.length) console.log('HTTP', journal.httpErrors.slice(0,8));
if (journal.consoleErrors.length) console.log('CONSOLE', journal.consoleErrors.slice(0,5));
if (journal.pageErrors.length) console.log('PAGE', journal.pageErrors.slice(0,3));
await shot(page, FAM, `probe-${key}-${label}`, { full: true });
await browser.close();
