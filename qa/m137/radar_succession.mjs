import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0,140)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
// ouvrir Outils → Radar des ventes (scoring-v2)
await soft(async () => { await page.locator('button[title="Outils"]').click(); await page.waitForTimeout(800); }, 'rail outils');
await soft(async () => { await page.locator('[data-outil="scoring-v2"]').click(); await page.waitForTimeout(3000); }, 'radar');
// attendre le chargement (Priorité = brulantes par défaut)
await page.waitForFunction(() => /succession en cours/.test(document.body.innerText), { timeout: 15000 }).catch(()=>console.log('WARN badge succession absent'));
const nBadge = await page.locator('text=succession en cours').count();
console.log('badges « succession en cours » visibles:', nBadge);
// scroller jusqu'au 1er badge et le cadrer
await soft(async () => { await page.locator('text=succession en cours').first().scrollIntoViewIfNeeded(); await page.waitForTimeout(600); }, 'scroll badge');
await page.screenshot({ path: `${OUT}/radar_succession.png` });
// crop panneau gauche
await page.screenshot({ path: `${OUT}/radar_succession_zoom.png`, clip: { x: 0, y: 0, width: 430, height: 1024 } });
await b.close();
console.log(nBadge > 0 ? 'OK — badge « succession en cours » affiché' : 'À VÉRIFIER');
