import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = process.argv[2] || '97414000EN0451';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0,140)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
await soft(async () => { const box=page.locator('[data-omnibox]'); await box.click(); await box.fill(IDU); await page.waitForTimeout(700); await box.press('Enter'); await page.waitForTimeout(3800); }, 'recherche');
await page.waitForSelector('[data-fiche-idu]', { timeout: 15000 }).catch(()=>{});
await page.waitForFunction(() => !document.body.innerText.includes('Chargement de la fiche'), { timeout: 20000 }).catch(()=>{});
await page.waitForTimeout(1500);
// commune servie (header)
const commune = await page.evaluate(() => { const e = document.querySelector('.eyebrow'); return e ? e.textContent.replace('PARCELLE ·','').trim() : null; });
console.log('commune servie (header):', commune);
// ouvrir le tiroir Marché
await soft(async () => { const d = page.locator('[data-drawer="marche"] button.tiroir'); await d.scrollIntoViewIfNeeded(); await d.click(); await page.waitForTimeout(1000); }, 'ouvrir tiroir marché');
// le bouton
const btn = page.locator('[data-porte="marche"]');
await soft(async () => { await btn.scrollIntoViewIfNeeded(); await page.waitForTimeout(500); }, 'scroll bouton');
const btnText = await btn.innerText().catch(()=>'(absent)');
console.log('texte bouton:', btnText.replace(/\s+/g,' ').trim());
await page.screenshot({ path: `${OUT}/marche_bouton_fiche.png` });
await soft(async () => { const bx = await page.locator('aside').filter({ has: page.locator('[data-fiche-idu]') }).first().boundingBox(); if (bx) await page.screenshot({ path: `${OUT}/marche_bouton_zoom.png`, clip: { x: bx.x, y: Math.max(0,bx.y), width: Math.min(bx.width,640), height: Math.min(bx.height,1024) } }); }, 'crop fiche');
// cliquer → ouvre l'outil Marché
await soft(async () => { await btn.click(); await page.waitForTimeout(2500); }, 'clic bouton');
const toolCommune = await page.locator('[data-marche-commune]').inputValue().catch(()=>'(pas de dropdown)');
console.log('commune de l\'outil Marché après clic:', toolCommune);
await page.screenshot({ path: `${OUT}/marche_outil_ouvert.png` });
await b.close();
const ok = /Voir le marché de/.test(btnText) && commune && toolCommune && commune.toUpperCase().includes(toolCommune.toUpperCase());
console.log(ok ? 'OK — bouton présent + outil ouvert sur la bonne commune' : 'À VÉRIFIER');
