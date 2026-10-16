import { ouvrir, aller, shot, lien } from './harness.mjs';

const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});

await aller(page, lien.outil('courriers'));
await page.waitForTimeout(2500);

// Step 1: type IDU in ParcelInput
const input = await page.$('[data-courrier-idu] input, input[placeholder*="IDU"], input[placeholder*="Adresse"]');
console.log('input found:', !!input);
if (input) {
  await input.fill('97416000EW0446');
  await page.waitForTimeout(1800);
  // try pressing Enter or clicking a suggestion
  await input.press('Enter');
  await page.waitForTimeout(2500);
}
let dests = await page.$$eval('[data-courrier-dest]', els => els.map(e => e.innerText.trim()));
console.log('destinataires after add:', JSON.stringify(dests));
await shot(page, F, 'A_step1_destinataire_ajoute', { full: true });

// Go to Rédaction (step 2)
const red = await page.$$('button');
let clicked = false;
for (const b of red) {
  const t = (await b.innerText()).trim();
  if (/Rédiger|Rédaction|^2 /.test(t)) { await b.click(); clicked = true; break; }
}
console.log('clicked redaction:', clicked);
await page.waitForTimeout(3000);
let body2 = await page.evaluate(() => document.body.innerText.slice(0, 2500));
console.log('--- STEP2 RÉDACTION ---\n', body2);
await shot(page, F, 'A_step2_apercu', { full: true });

// Go to Envoi (step 3)
const btns3 = await page.$$('button');
for (const b of btns3) {
  const t = (await b.innerText()).trim();
  if (/^3 |Envoi|Demander/.test(t)) { await b.click(); break; }
}
await page.waitForTimeout(3000);
let body3 = await page.evaluate(() => document.body.innerText.slice(0, 2500));
console.log('--- STEP3 ENVOI ---\n', body3);
await shot(page, F, 'A_step3_envoi', { full: true });

console.log('ERR', journal.consoleErrors.length, 'HTTP', JSON.stringify(journal.httpErrors), 'PE', journal.pageErrors.length);
await browser.close();
