import { ouvrir, shot, lien } from './harness.mjs';
import { FAM, attendreOutil, etatOutil, allerOutil as aller } from './_outils_lib.mjs';

// Usage: node outils_lot.mjs <lotName> key:parcelle:caslimite  key2:parcelle:caslimite ...
// chaque arg = "key" ou "key:IDUnormale:IDUlimite"
const args = process.argv.slice(2);
const lotName = args[0];
const specs = args.slice(1).map(s => {
  const [key, normale, limite] = s.split(':');
  return { key, normale, limite };
});

const { browser, page, journal } = await ouvrir({});

function snapJournal() {
  return {
    err: journal.consoleErrors.length,
    http: journal.httpErrors.length,
    page: journal.pageErrors.length,
    httpList: [...journal.httpErrors],
    errList: [...journal.consoleErrors],
    pageList: [...journal.pageErrors],
  };
}
let base = snapJournal();
function delta() {
  const cur = snapJournal();
  const d = {
    err: cur.err - base.err, http: cur.http - base.http, page: cur.page - base.page,
    httpList: cur.httpList.slice(base.http), errList: cur.errList.slice(base.err), pageList: cur.pageList.slice(base.page),
  };
  base = cur;
  return d;
}

for (const { key, normale, limite } of specs) {
  console.log('\n===== OUTIL', key, '=====');

  // 1) standalone
  let t0 = Date.now();
  let ms = await aller(page, lien.outil(key));
  await attendreOutil(page, { timeout: 60000 });
  await page.waitForTimeout(800);
  let et = await etatOutil(page);
  let jd = delta();
  console.log(`[${key}] SEUL loadMs=${ms} totMs=${Date.now()-t0} len=${et.len} spinners=${et.spinners} vide=${et.vide} NaN=${et.hasNaN} err=${jd.err} http=${jd.http} page=${jd.page}`);
  console.log(`[${key}] boutons=${JSON.stringify(et.boutons)}`);
  console.log(`[${key}] extrait="${et.extrait.slice(0,300)}"`);
  if (jd.httpList.length) console.log(`[${key}] HTTP`, jd.httpList.slice(0,6));
  if (jd.errList.length) console.log(`[${key}] CONSOLE`, jd.errList.slice(0,4));
  if (jd.pageList.length) console.log(`[${key}] PAGE`, jd.pageList.slice(0,3));
  await shot(page, FAM, `${key}-seul`, { full: true });

  // 2) sur parcelle normale
  if (normale) {
    t0 = Date.now();
    ms = await aller(page, lien.outilSurParcelle(key, normale));
    await attendreOutil(page, { timeout: 60000 });
    await page.waitForTimeout(1000);
    et = await etatOutil(page);
    jd = delta();
    console.log(`[${key}] NORMALE ${normale} loadMs=${ms} totMs=${Date.now()-t0} len=${et.len} spinners=${et.spinners} vide=${et.vide} NaN=${et.hasNaN} err=${jd.err} http=${jd.http} page=${jd.page}`);
    console.log(`[${key}] extrait="${et.extrait.slice(0,400)}"`);
    if (jd.httpList.length) console.log(`[${key}] HTTP`, jd.httpList.slice(0,6));
    if (jd.errList.length) console.log(`[${key}] CONSOLE`, jd.errList.slice(0,4));
    if (jd.pageList.length) console.log(`[${key}] PAGE`, jd.pageList.slice(0,3));
    await shot(page, FAM, `${key}-normale`, { full: true });
  }

  // 3) cas limite
  if (limite) {
    t0 = Date.now();
    ms = await aller(page, lien.outilSurParcelle(key, limite));
    await attendreOutil(page, { timeout: 60000 });
    await page.waitForTimeout(1000);
    et = await etatOutil(page);
    jd = delta();
    console.log(`[${key}] LIMITE ${limite} loadMs=${ms} totMs=${Date.now()-t0} len=${et.len} spinners=${et.spinners} vide=${et.vide} NaN=${et.hasNaN} err=${jd.err} http=${jd.http} page=${jd.page}`);
    console.log(`[${key}] extrait="${et.extrait.slice(0,400)}"`);
    if (jd.httpList.length) console.log(`[${key}] HTTP`, jd.httpList.slice(0,6));
    if (jd.errList.length) console.log(`[${key}] CONSOLE`, jd.errList.slice(0,4));
    if (jd.pageList.length) console.log(`[${key}] PAGE`, jd.pageList.slice(0,3));
    await shot(page, FAM, `${key}-limite`, { full: true });
  }
}

console.log('\n===== FIN LOT', lotName, '=====');
await browser.close();
