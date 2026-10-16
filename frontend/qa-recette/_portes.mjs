import { ouvrir } from './harness.mjs';
import { allerCommune, shot } from './_commune_lib.mjs';
const { browser, page, journal } = await ouvrir({});
const NOM = process.env.NOM || 'Saint-Denis';
const tuiles = ['data-tuile-plu', 'data-tuile-permis', 'data-tuile-etude-zone', 'data-tuile-communes'];
for (const t of tuiles) {
  await allerCommune(page, NOM, { gesteReel: true });
  const before = page.url();
  const sel = `[data-etudier-commune] button`; // les OutilCase
  // trouver le bouton par son data-attr (OutilCase le pose)
  const btn = await page.$(`[${t}]`) || await page.$(`[data-etudier-commune] [${t}]`);
  let clicked = false, after = before, moduleAfter = null;
  if (btn) {
    await btn.click({ timeout: 2500 }).catch(() => {});
    await page.waitForTimeout(1500);
    after = page.url();
    moduleAfter = await page.evaluate(() => {
      const m = new URLSearchParams(location.hash.replace(/^#/, '')).get('m');
      return m;
    });
    clicked = true;
  }
  console.log(JSON.stringify({ tuile: t, found: !!btn, changed: after !== before, moduleAfter }));
  await shot(page, '03-commune', `${NOM.replace(/[^a-zA-Z0-9]/g, '_')}_porte_${t}`);
}
console.log('http', journal.httpErrors.length, 'cons', journal.consoleErrors.length);
await browser.close();
