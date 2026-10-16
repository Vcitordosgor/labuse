import { ouvrir } from './harness.mjs';
import { allerCommune, panneauPresent, bandeau, parcourirCartes, tuiles, debordements, shot } from './_commune_lib.mjs';
import { writeFileSync } from 'node:fs';

const LOT = JSON.parse(process.env.LOT);      // array of commune names
const CAP = process.env.CAP === '1';          // capture each
const { browser, page, journal } = await ouvrir({});

for (const nom of LOT) {
  const c0 = journal.consoleErrors.length, h0 = journal.httpErrors.length;
  const ms = await allerCommune(page, nom);
  const present = await panneauPresent(page);
  let band = [], cartes = {}, tui = { present: false, n: 0 }, deb = [];
  if (present) {
    band = await bandeau(page);
    cartes = await parcourirCartes(page);
    tui = await tuiles(page);
    deb = await debordements(page);
  }
  const newCons = journal.consoleErrors.length - c0;
  const newHttp = journal.httpErrors.length - h0;
  const bandBad = band.filter(c => /nan|undefined|null/i.test(c.v)).map(c => c.n);
  const cartesVideMuet = Object.entries(cartes).filter(([, v]) => v.videMuet).map(([k]) => k);
  const cartesBad = Object.entries(cartes).filter(([, v]) => v.bad).map(([k]) => k);
  if (CAP) await shot(page, '03-commune', nom.replace(/[^a-zA-Z0-9]/g, '_'));
  const summary = {
    nom, loadMs: ms, present, newCons, newHttp,
    nCartes: Object.keys(cartes).length,
    bandeau: band.map(c => `${c.n}=${c.v}`),
    bandBad, cartesVideMuet, cartesBad,
    tuiles: tui.n, deb: deb.length,
  };
  console.log('=====', nom, '=====');
  console.log(JSON.stringify(summary));
  if (newHttp > 0) console.log('HTTP:', journal.httpErrors.slice(h0));
  if (newCons > 0) console.log('CONS:', journal.consoleErrors.slice(c0).slice(0, 5));
  if (deb.length) console.log('DEB:', JSON.stringify(deb.slice(0, 5)));
  // dump
  let dump = `COMMUNE ${nom} loadMs=${ms} present=${present}\nBANDEAU: ${JSON.stringify(band)}\nTUILES: ${JSON.stringify(tui)}\n`;
  for (const [k, v] of Object.entries(cartes)) dump += `\n### ${k} [head="${v.headVal}"] videMuet=${v.videMuet} bad=${v.bad}\n${v.content || '(vide)'}\n`;
  writeFileSync(`/tmp/c_${nom.replace(/[^a-zA-Z0-9]/g, '_')}.txt`, dump);
}
await browser.close();
console.log('FIN LOT');
