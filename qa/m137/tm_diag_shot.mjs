import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = process.argv[2] || '97414000EN0451';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0,120)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
await soft(async () => { const box=page.locator('[data-omnibox]'); await box.click(); await box.fill(IDU); await page.waitForTimeout(700); await box.press('Enter'); await page.waitForTimeout(3800); }, 'recherche');
await page.waitForSelector('[data-fiche-idu]', { timeout: 15000 }).catch(()=>{});
await page.waitForFunction(() => !document.body.innerText.includes('Chargement de la fiche'), { timeout: 20000 }).catch(()=>{});
await soft(async () => { const t=page.locator('button[title*="1950"]').first(); await t.scrollIntoViewIfNeeded(); await t.click(); }, 'temps');
await page.waitForFunction(() => !!window.__labuse_tm, { timeout: 15000 }).catch(()=>{});
await page.waitForTimeout(6000); // laisse les tuiles peindre
await page.screenshot({ path: `${OUT}/tm_diag_shot.png` });
await b.close();
console.log('shot done');
