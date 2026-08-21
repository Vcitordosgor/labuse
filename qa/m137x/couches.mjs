// M137-X — captures : pôles d'échange sur « Axes structurants » (magenta) ; ZFANG/FRR 4 états
// distincts (aplat vs hachures).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 140)) } };
const openCouches = async () => { if (await page.locator('[data-layer="parcelles"]').isVisible().catch(() => false)) return; const t = page.locator('[data-couches-toggle]').first(); if (await t.count()) { await t.click(); await page.waitForTimeout(500); } };
const toggle = async (k) => { await page.locator(`[data-layer="${k}"]`).click(); await page.waitForTimeout(1500); };

await page.goto('http://localhost:5173/socle/', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);
await openCouches();

// ── A) Axes structurants + pôles (vue île) ──
await soft(() => toggle('axes'), 'axes');
await page.waitForTimeout(1500);
console.log('A · légende axes:', await page.locator('[data-legend-axes]').count(),
            '· pôle mentionné:', await page.locator('[data-legend-axes]').getByText('pôle', { exact: false }).count() > 0,
            '· pôle absent de transport-legend au repos:', await page.locator('[data-legend-transport]').count());
await page.screenshot({ path: `${OUT}/A_poles_sur_axes.png`, fullPage: false });
await soft(() => toggle('axes'), 'axes off');

// ── B) ZFANG + FRR : 4 états distincts (aplat vs hachures) — vue île ──
await soft(() => toggle('zfang'), 'zfang');
await soft(() => toggle('frr'), 'frr');
await page.waitForTimeout(1500);
const entries = ['zfang-renforce', 'zfang-standard', 'frr-totalite', 'frr-partie'];
for (const e of entries) console.log(`B · légende ${e}:`, await page.locator(`[data-legend-${e}]`).count() > 0);
await page.screenshot({ path: `${OUT}/B_zfang_frr_4_etats.png`, fullPage: false });

await b.close();
console.log('captures dans', OUT);
