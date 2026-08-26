// FOND-SOMBRE — vérifs annexes APRÈS nettoyage : millésime ortho ancien (1950) servi,
// comparateur swipe « Remonter le temps » (#m=temps) vivant, console propre.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/');
const OUT = new URL('./out/apres', import.meta.url).pathname;
const EXE = process.env.CHROMIUM
  || `${process.env.HOME}/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell`;

const consoleErrors = [];
const badResponses = [];
const browser = await chromium.launch({ executablePath: EXE });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
page.setDefaultTimeout(20000);
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
page.on('pageerror', (e) => consoleErrors.push('PAGEERROR ' + String(e).slice(0, 200)));
page.on('response', (r) => { if (r.status() >= 400) badResponses.push(`${r.status()} ${r.url().slice(0, 140)}`); });

// millésime ortho ancien via le sélecteur de fonds
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-omnibox]');
await page.waitForTimeout(4000);
await page.click('button[title="Fond de plan"]');
await page.locator('.floating button', { hasText: '1950-1965' }).click();
await page.mouse.click(700, 520);
await page.waitForTimeout(3500);
await page.screenshot({ path: `${OUT}/7-ortho-1950-2d.png` });

// comparateur swipe « Remonter le temps »
await page.goto(`${BASE}#m=temps`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(7000);                  // deux cartes + tuiles des deux fonds
await page.screenshot({ path: `${OUT}/8-temps-swipe.png` });

writeFileSync(`${OUT}/verifs_annexes.json`, JSON.stringify({ consoleErrors, badResponses }, null, 2));
console.log(`console errors: ${consoleErrors.length} · >=400: ${badResponses.length}`);
console.log(badResponses.slice(0, 8));
await browser.close();
