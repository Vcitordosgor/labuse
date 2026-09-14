// SOURCES-4 lot 1 — captures RÉELLES des champs surfacés depuis `raw` (ports :8032/:5200).
// Rejouable :  BASE=http://localhost:5200 node docs/audit-2026-09/SOURCES/scripts/sources4_lot1_captures.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '');
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/SOURCES/captures-sources4';
mkdirSync(OUT, { recursive: true });
const IDU = process.env.IDU || '97411000BH0670';   // parcelle avec copropriété RNIC (syndic pro)
const b = await chromium.launch({ executablePath: EXE });
const p = await b.newPage({ viewport: { width: 1440, height: 1200 } });
p.setDefaultTimeout(20000);
p.on('pageerror', e => console.log('  PAGEERR', String(e).slice(0, 120)));
const out = {};
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ');
const shot = async n => { await p.waitForTimeout(500); await p.screenshot({ path: `${OUT}/${n}.png`, fullPage: true }); console.log('  📸', n); };

// ── CatNat détail (fiche commune → carte Risques) ──
try {
  await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
  await p.evaluate(() => window.__labuse.setContexteCommune('Saint-Denis')); await p.waitForTimeout(2500);
  // ouvrir la carte Risques
  await p.locator('text=/^Risques$/').first().click().catch(() => {}); await p.waitForTimeout(1200);
  out.commune_risques = await txt(); await shot('01-commune-risques-catnat-detail');
} catch (e) { console.log('commune KO', e.message); }

// ── Copropriété RNIC (fiche parcelle → bloc copropriété) ──
try {
  await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
  await p.evaluate(idu => window.__labuse.select(idu), IDU); await p.waitForTimeout(4000);
  // le bloc Copropriété est dans le tiroir « Propriétaire » (replié) — l'ouvrir
  await p.locator('text=/Propriétaire/').first().click().catch(() => {}); await p.waitForTimeout(1500);
  await p.locator('[data-coproprietes]').first().waitFor({ state: 'attached', timeout: 25000 }).catch(() => {});
  await p.waitForTimeout(1500);
  await p.evaluate(() => { const el = document.querySelector('[data-coproprietes]'); if (el) el.scrollIntoView({ block: 'center' }); });
  await p.waitForTimeout(1000); out.fiche = await txt(); await shot('02-fiche-copropriete-rnic');
} catch (e) { console.log('fiche KO', e.message); }

writeFileSync(OUT + '/_surfaces.json', JSON.stringify(out, null, 1));
console.log('CATNAT_DETAIL vu:', /INTE|IOME|Mouvement de Terrain|Coulées de Boue/.test(out.commune_risques || ''));
console.log('SIRET syndic vu:', /SIRET/.test(out.fiche || ''), '| stationnement vu:', /stationnement/.test(out.fiche || ''));
await b.close();
