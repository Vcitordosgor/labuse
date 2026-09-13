// SOURCES-AUDIT-1 — capture navigateur RÉELLE des surfaces client (ports :8032/:5200).
// Rejouable :  BASE=http://localhost:5200 node docs/audit-2026-09/SOURCES/scripts/clictest_capture.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '');
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/SOURCES/captures';
mkdirSync(OUT, { recursive: true });
const IDU = process.env.IDU || '97412000AV0522';
const b = await chromium.launch({ executablePath: EXE });
const p = await b.newPage({ viewport: { width: 1440, height: 950 } });
p.setDefaultTimeout(15000);
p.on('pageerror', e => console.log('  PAGEERR', String(e).slice(0,120)));
const out = {};
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g,' ');
const shot = async n => { await p.waitForTimeout(500); await p.screenshot({ path: `${OUT}/${n}.png` }); console.log('  📸', n); };

await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2500);
await shot('01-accueil');

// ── COUCHES (panneau des couches carte) ──
try {
  await p.locator('text=/COUCHES/i').first().click(); await p.waitForTimeout(1200);
  out.couches = await txt(); await shot('02-couches');
} catch(e){ console.log('couches KO', e.message); }

// ── OUTILS ──
try {
  await p.goto(`${BASE}/socle/`, { waitUntil:'networkidle' }); await p.waitForTimeout(1000);
  await p.locator('text=/Ouvrir un outil|Outils/i').first().click(); await p.waitForTimeout(1200);
  out.outils = await txt(); await shot('03-outils');
} catch(e){ console.log('outils KO', e.message); }

// ── SOURCES (catalogue client) ──
try {
  await p.goto(`${BASE}/socle/`, { waitUntil:'networkidle' }); await p.waitForTimeout(800);
  await p.locator('nav >> text=/^Sources$/').first().click({timeout:5000}).catch(async()=>{ await p.locator('text=/^Sources$/').first().click(); });
  await p.waitForTimeout(1500);
  out.sources_page = await txt(); await shot('04-sources-page');
} catch(e){ console.log('sources KO', e.message); }

// ── FICHE PARCELLE (sélection via __labuse.select) ──
try {
  await p.goto(`${BASE}/socle/`, { waitUntil:'networkidle' }); await p.waitForTimeout(1500);
  await p.evaluate((idu)=> window.__labuse.select(idu), IDU); await p.waitForTimeout(3000);
  out.fiche = await txt(); await shot('05-fiche-parcelle');
  // scroll pour capturer le bas
  await p.evaluate(()=> { const el=document.querySelector('[class*=fiche],[class*=panel],aside'); if(el) el.scrollTop=el.scrollHeight; window.scrollTo(0, document.body.scrollHeight); });
  await p.waitForTimeout(1200); await shot('06-fiche-bas'); out.fiche += ' ' + await txt();
} catch(e){ console.log('fiche KO', e.message); }

writeFileSync(OUT+'/_surfaces.json', JSON.stringify(out, null, 1));
console.log('LENGTHS', Object.fromEntries(Object.entries(out).map(([k,v])=>[k,(v||'').length])));
await b.close();
