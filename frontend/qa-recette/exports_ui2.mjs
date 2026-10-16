// Famille 5 (suite) — Bilan (écran d'hypothèses), Comparatif, Étude de zone via l'UI.
import { ouvrir, aller, shot } from './harness.mjs';
const FAM = '05-exports';
const A = '97422000BX1106', B = '97411000AT0427';
const { browser, page, journal } = await ouvrir({});
const log = (...a) => console.log(...a);

await aller(page, `#idu=${A}`);
await page.waitForTimeout(1200);
await page.click('[data-rail="documents"]');
await page.waitForTimeout(1000);

// ── BILAN : ouvre l'écran d'hypothèses ──
log('\n--- Bilan ---');
await page.locator('button:has-text("Bilan")').first().click();
await page.waitForTimeout(600);
const input = page.locator('.fixed input').first();
await input.fill(A); await page.keyboard.press('Enter'); await page.waitForTimeout(1000);
const cand = page.locator('.fixed [data-parcelinput-candidat]');
if (await cand.count()) { await cand.first().click(); await page.waitForTimeout(500); }
// clique « Générer le bilan » (ouvre BilanEcran)
const cta = page.locator('.fixed button:has-text("Générer le bilan")').first();
log('  CTA Bilan activable =', await cta.isEnabled().catch(() => false));
await cta.click();
await page.waitForTimeout(2500);
await shot(page, FAM, 'bilan_ecran_hypotheses');
// l'écran bilan a son propre bouton « Générer le bilan » (génère le PDF)
const genBilan = page.locator('button:has-text("Générer le bilan")');
log('  boutons Générer le bilan présents =', await genBilan.count());
await page.keyboard.press('Escape'); await page.waitForTimeout(500);
await page.keyboard.press('Escape'); await page.waitForTimeout(500);

// ── COMPARATIF ──
log('\n--- Comparatif ---');
await page.locator('button:has-text("Comparatif")').first().click();
await page.waitForTimeout(600);
const ins = page.locator('.fixed input');
await ins.nth(0).fill(A); await ins.nth(0).press('Enter'); await page.waitForTimeout(900);
let c = page.locator('.fixed [data-parcelinput-candidat]'); if (await c.count()) { await c.first().click(); await page.waitForTimeout(400); }
await ins.nth(1).fill(B); await ins.nth(1).press('Enter'); await page.waitForTimeout(900);
c = page.locator('.fixed [data-parcelinput-candidat]'); if (await c.count()) { await c.first().click(); await page.waitForTimeout(400); }
await shot(page, FAM, 'porte_Comparatif');
const popC = page.context().waitForEvent('page', { timeout: 6000 }).catch(() => null);
const ctaC = page.locator('.fixed button:has-text("Générer le comparatif")').first();
log('  CTA Comparatif activable =', await ctaC.isEnabled().catch(() => false));
if (await ctaC.isEnabled().catch(() => false)) { await ctaC.click(); await page.waitForTimeout(2500); const p = await popC; log('  PDF ouvert =', !!p); if (p) await p.close().catch(() => {}); }
await page.keyboard.press('Escape'); await page.waitForTimeout(500);

// ── ÉTUDE DE ZONE ──
log('\n--- Étude de zone ---');
await page.locator('button:has-text("Étude de zone")').first().click();
await page.waitForTimeout(600);
const insZ = page.locator('.fixed input').first();
await insZ.fill(A); await insZ.press('Enter'); await page.waitForTimeout(900);
let cz = page.locator('.fixed [data-parcelinput-candidat]'); if (await cz.count()) { await cz.first().click(); await page.waitForTimeout(400); }
await shot(page, FAM, 'porte_EtudeZone');
const popZ = page.context().waitForEvent('page', { timeout: 8000 }).catch(() => null);
const ctaZ = page.locator('.fixed button:has-text("Générer l’étude de zone")').first();
log('  CTA Étude activable =', await ctaZ.isEnabled().catch(() => false));
if (await ctaZ.isEnabled().catch(() => false)) { await ctaZ.click(); await page.waitForTimeout(3500); const p = await popZ; log('  PDF ouvert =', !!p); if (p) await p.close().catch(() => {}); }

log('\n=== JOURNAL ===');
log('consoleErrors', journal.consoleErrors.length, JSON.stringify(journal.consoleErrors.slice(0, 5)));
log('httpErrors', journal.httpErrors.length, JSON.stringify(journal.httpErrors.slice(0, 10)));
log('pageErrors', journal.pageErrors.length);
await browser.close();
