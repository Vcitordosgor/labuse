#!/usr/bin/env node
// PARCOURS-FIX-1 (Lot 1.1) — TEST DE FUMÉE « le build servi s'ouvre ».
//
// Le smoke_test.sh vérifie que le serveur répond (healthz/readyz/DB) — mais un BUILD cassé rend une
// PAGE BLANCHE tout en répondant 200 (incident PARCOURS-CLIENT-1 BLOQUANT-1 : chunk `vendor`,
// `TypeError: t is not a function`). Ce test ouvre le build DANS UN VRAI NAVIGATEUR (chromium) et
// échoue si l'app ne MONTE pas (`window.__labuse` absent / root vide) ou si une erreur fatale de
// bundle apparaît en console. C'est le seul contrôle qui attrape une page blanche avant le client.
//
// Variables : LABUSE_BASE_URL (déf. http://127.0.0.1:8000), LABUSE_SMOKE_PASSWORD ou
//             LABUSE_AUTH_PASSWORD (mot de passe pilote, pour franchir /login si l'app le demande).
// Résout chromium depuis le playwright du dépôt (frontend/node_modules) ou PW_PKG.
// Sort 0 = build s'ouvre ; 1 = page blanche / erreur fatale ; 77 = SKIP (outil absent) — non bloquant.

import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE = (process.env.LABUSE_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const PASSWORD = process.env.LABUSE_SMOKE_PASSWORD || process.env.LABUSE_AUTH_PASSWORD || '';
// motifs d'ERREUR FATALE de bundle (la page blanche du mandat + classes voisines)
const FATALS = [/is not a function/i, /__commonjsmin/i, /cannot read propert/i,
                /unexpected token/i, /failed to fetch dynamically imported module/i];

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const candidats = [
    process.env.PW_PKG,
    resolve(__dirname, '../../frontend/node_modules/playwright/index.js'),
    `${process.env.HOME}/Desktop/labuse/frontend/node_modules/playwright/index.js`,
    'playwright',
  ].filter(Boolean);
  for (const c of candidats) {
    try { return require(c); } catch { /* suivant */ }
  }
  return null;
}

const pw = loadPlaywright();
if (!pw) {
  console.log('· smoke_build : playwright introuvable — SKIP (non bloquant).');
  process.exit(77);
}

// Le navigateur installé peut avoir une révision ≠ de celle attendue par le paquet playwright
// (cache partagé entre versions) : on résout un exécutable chromium présent plutôt que d'exiger
// `npx playwright install`. Env PLAYWRIGHT_CHROMIUM prime.
async function execPath() {
  if (process.env.PLAYWRIGHT_CHROMIUM) return process.env.PLAYWRIGHT_CHROMIUM;
  const { readdirSync, existsSync } = await import('node:fs');
  const root = `${process.env.HOME}/Library/Caches/ms-playwright`;
  if (!existsSync(root)) return undefined;
  const noms = ['chrome-headless-shell-mac-arm64/chrome-headless-shell',
                'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
                'chrome-headless-shell-linux/chrome-headless-shell',
                'chrome-linux/chrome'];
  for (const d of readdirSync(root).filter((n) => /chromium/i.test(n))) {
    for (const rel of noms) {
      const p = `${root}/${d}/${rel}`;
      if (existsSync(p)) return p;
    }
  }
  return undefined;
}
const executablePath = await execPath();
const browser = await pw.chromium.launch(executablePath ? { executablePath } : {});
const page = await browser.newPage();
const fatals = [];
page.on('console', (m) => {
  if (m.type() === 'error' && FATALS.some((re) => re.test(m.text()))) fatals.push(m.text());
});
page.on('pageerror', (e) => { if (FATALS.some((re) => re.test(String(e)))) fatals.push(String(e)); });

let code = 0;
try {
  await page.goto(`${BASE}/socle/`, { waitUntil: 'networkidle', timeout: 30000 });
  // Si l'app demande une connexion et qu'on a le mot de passe pilote, on la franchit.
  if (/\/login/.test(page.url()) && PASSWORD) {
    await page.fill('input[name=password], input[type=password]', PASSWORD);
    // pilote = identifiant vide ; on SOUMET par le bouton (le submit par Enter peut ne pas déclencher).
    await Promise.all([
      page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {}),
      page.click('button[type=submit]').catch(() => page.keyboard.press('Enter')),
    ]);
    await page.waitForTimeout(500);
    await page.goto(`${BASE}/socle/`, { waitUntil: 'networkidle', timeout: 30000 });
  }
  if (/\/login/.test(page.url())) {
    console.log('· smoke_build : /socle protégé et aucun mot de passe fourni — SKIP (non bloquant).');
    await browser.close();
    process.exit(77);
  }
  const monte = await page.evaluate(() => ({
    labuse: typeof window.__labuse,
    rootLen: (document.getElementById('root') || {}).innerHTML?.length || 0,
  }));
  const ok = monte.labuse === 'object' && monte.rootLen > 500 && fatals.length === 0;
  if (ok) {
    console.log(`  ✓ build servi s'ouvre (window.__labuse=${monte.labuse}, root=${monte.rootLen} car., 0 erreur fatale)`);
  } else {
    console.error(`  ✗ PAGE BLANCHE / build cassé : window.__labuse=${monte.labuse}, root=${monte.rootLen} car.`);
    if (fatals.length) console.error('    erreurs fatales : ' + fatals.join(' | '));
    code = 1;
  }
} catch (e) {
  console.error('  ✗ smoke_build : échec de chargement — ' + String(e));
  code = 1;
} finally {
  await browser.close();
}
process.exit(code);
