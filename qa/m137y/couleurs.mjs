// M137-Y — captures île, deux thèmes : ZFANG (renforcée bleu roi / standard sable) et
// FRR (totalité émeraude / en partie améthyste), 4 états identifiables sans survol.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 130)) } };
const openCouches = async () => { if (await page.locator('[data-layer="parcelles"]').isVisible().catch(() => false)) return; const t = page.locator('[data-couches-toggle]').first(); if (await t.count()) { await t.click(); await page.waitForTimeout(500); } };
const on = async (k) => { if (!(await page.locator(`[data-layer="${k}"] span.bg-mint`).count())) { await page.locator(`[data-layer="${k}"]`).click(); await page.waitForTimeout(1200); } };
const off = async (k) => { if (await page.locator(`[data-layer="${k}"] span.bg-mint`).count()) { await page.locator(`[data-layer="${k}"]`).click(); await page.waitForTimeout(800); } };
const setTheme = async (label) => { await page.locator('[title="Fond de plan"]').click(); await page.waitForTimeout(400); await page.getByRole('button', { name: label, exact: true }).click(); await page.waitForTimeout(1800); };

await page.goto('http://localhost:5173/socle/', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);
await openCouches();

// ── SOMBRE ──
await soft(() => on('zfang'), 'zfang'); await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/A_zfang_sombre.png`, fullPage: false });
await soft(() => off('zfang'), 'zfang off'); await soft(() => on('frr'), 'frr'); await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/B_frr_sombre.png`, fullPage: false });

// ── CLAIR (vérif contraste sable foncé) ──
await soft(() => setTheme('Clair'), 'clair');
await page.screenshot({ path: `${OUT}/C_frr_clair.png`, fullPage: false });
await soft(() => off('frr'), 'frr off'); await soft(() => on('zfang'), 'zfang'); await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/D_zfang_clair.png`, fullPage: false });

const ok = ['zfang-renforce', 'zfang-standard'].every; // sanity noop
for (const e of ['zfang-renforce', 'zfang-standard', 'frr-totalite', 'frr-partie'])
  console.log(`légende ${e}:`, await page.locator(`[data-legend-${e}]`).count());
await b.close();
console.log('captures dans', OUT);
