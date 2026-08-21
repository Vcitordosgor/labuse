// M137-S — capture : les deux verdicts du scoreur sont NOMMÉS et réconciliés.
// Prix au niveau du marché (≈ prix probable) → badge « Prix du terrain : dans le marché »
// + « Pour une opération de promotion : marge −99 k€ » + synthèse qui réconcilie les deux.
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

// prix au niveau du prix probable du foncier (≈ 125 000 €) → « dans le marché » + marge négative
await soft(async () => { await page.locator('[data-scoreur-prix]').fill('125000'); }, 'prix');
await soft(async () => { await page.getByRole('button', { name: /Scorer cette adresse/ }).click(); }, 'scorer');
await page.waitForSelector('[data-scoreur-prix-verdict]', { timeout: 20000 }).catch(() => console.log('WARN verdict absent'));
await page.waitForTimeout(800);

const badge = await page.locator('[data-scoreur-prix-verdict]').textContent().catch(() => '?');
const synthese = await page.locator('[data-scoreur-synthese]').textContent().catch(() => '(absente)');
const bloc = await page.locator('[data-scoreur-resultat]').innerText().catch(() => '');
console.log('badge:', (badge || '').trim());
console.log('synthèse présente:', /se vend à son prix/.test(synthese || ''));
console.log('marge opération nommée:', /opération de promotion/.test(bloc));
await page.screenshot({ path: `${OUT}/scoreur_deux_verdicts_reconcilies.png`, fullPage: true });

await b.close();
const ok = /dans le marché/i.test(badge || '') && /se vend à son prix/.test(synthese || '') && /opération de promotion/.test(bloc);
console.log(ok ? 'OK — badge marché + marge opération + synthèse réconciliée' : 'À VÉRIFIER (voir WARN)');
