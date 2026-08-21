// M128-6-§1.3 — capture : le scoreur ne rend AUCUN verdict au tiers. Un prix saisi produit un
// CONSTAT chiffré nu (prix probable du foncier + écart, marge à ce prix issue de la méthode
// DOCUMENTS). Aucun badge « dans le marché », aucune « synthèse », aucun « rentable ».
// (Remplace l'ancien harnais M137-S des « deux verdicts réconciliés », supprimés en M128-6.)
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 160)) } };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);

await soft(async () => { await page.getByRole('button', { name: 'Outils' }).first().click(); await page.waitForTimeout(700); }, 'outils');
await soft(async () => { await page.locator('[data-outil="scoreur-adresse"]').click(); await page.waitForTimeout(1000); }, 'scoreur');

const input = page.locator('[data-scoreur-panel] input[role="combobox"]');
await soft(async () => { await input.click(); await input.type('1 Rue Edf', { delay: 40 }); }, 'saisie');
await page.waitForTimeout(1200);
await soft(async () => { await page.locator('[role="option"]').first().click(); await page.waitForTimeout(1200); }, 'pick');

await soft(async () => { await page.locator('[data-scoreur-prix]').fill('125000'); }, 'prix');
await soft(async () => { await page.getByRole('button', { name: /Scorer cette adresse/ }).click(); }, 'scorer');
await page.waitForSelector('[data-scoreur-prix-constat]', { timeout: 20000 }).catch(() => console.log('WARN constat absent'));
await page.waitForTimeout(800);

const bloc = await page.locator('[data-scoreur-resultat]').innerText().catch(() => '');
console.log('constat chiffré présent:', /Prix probable du foncier|Marge à ce prix/.test(bloc));
// GARDE-FOU M128-6-§1.3 : AUCUN mot de verdict rendu au tiers.
const verdictMots = /(dans le marché|au-dessus du marché|en dessous du marché|rentable|bonne affaire|validé|opportunité)/i;
const sansVerdict = !verdictMots.test(bloc);
console.log('sans verdict:', sansVerdict);
await page.screenshot({ path: `${OUT}/scoreur_constat_chiffre_nu.png`, fullPage: true });

await b.close();
console.log(sansVerdict && /Marge à ce prix|Prix probable du foncier/.test(bloc)
  ? 'OK — constat chiffré nu, aucun verdict' : 'À VÉRIFIER (voir WARN)');
