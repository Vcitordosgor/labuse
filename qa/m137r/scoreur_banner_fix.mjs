// M137-R — capture : le bandeau « Aucune adresse trouvée » ne s'affiche PLUS par-dessus un
// résultat valide (bug : la sélection recopiait le libellé → re-recherche 0 résultat → bandeau).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 160)) } };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);

// Outils → Scorer une adresse
await soft(async () => { await page.getByRole('button', { name: 'Outils' }).first().click(); await page.waitForTimeout(700); }, 'outils');
await soft(async () => { await page.locator('[data-outil="scoreur-adresse"]').click(); await page.waitForTimeout(1000); }, 'scoreur');

// saisir une adresse qui, en libellé COMPLET, ne se re-trouve pas (déclencheur du bug)
const input = page.locator('[data-scoreur-panel] input[role="combobox"]');
await soft(async () => { await input.click(); await input.type('1 Rue Edf', { delay: 40 }); }, 'saisie');
await page.waitForTimeout(1200);
// choisir la 1re suggestion
await soft(async () => { await page.locator('[role="option"]').first().click(); await page.waitForTimeout(1500); }, 'pick');

const bannerAfterPick = await page.getByText('Aucune adresse trouvée').count();
console.log('bandeau présent après sélection:', bannerAfterPick, '(attendu 0)');

// saisir un prix + scorer
await soft(async () => { await page.locator('[data-scoreur-prix]').fill('850000'); }, 'prix');
await soft(async () => { await page.getByRole('button', { name: /Scorer cette adresse/ }).click(); }, 'scorer');
await page.waitForSelector('[data-scoreur-resultat]', { timeout: 20000 }).catch(() => console.log('WARN résultat absent'));
await page.waitForTimeout(1000);

const bannerWithResult = await page.getByText('Aucune adresse trouvée').count();
const resultVisible = await page.locator('[data-scoreur-resultat]').count();
console.log('bandeau présent AVEC résultat:', bannerWithResult, '(attendu 0)');
console.log('résultat affiché:', resultVisible > 0);
await page.screenshot({ path: `${OUT}/scoreur_sans_bandeau_parasite.png`, fullPage: true });

await b.close();
console.log(bannerAfterPick === 0 && bannerWithResult === 0 && resultVisible > 0
  ? 'OK — plus de bandeau parasite, résultat affiché'
  : 'À VÉRIFIER (voir WARN)');
