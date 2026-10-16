// RECETTE-GENERALE-1 — captures « après » des correctifs UI.
// Pilote le Chrome système (macOS 13). DESKTOP uniquement. LECTURE SEULE côté code.
// Deep-links via le hash RÉEL (#idu=…&m=… / #surveillance=…) = le chemin exact que les
// correctifs amorcent (App.tsx boot-hash). Le « # » est OBLIGATOIRE. Chaque capture tourne
// dans un CONTEXTE NEUF : enchaîner les page.goto(#deep-link) dans une même session fait
// avorter l'effet boot-hash des navigations suivantes (timing React/vite dev).
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = 'http://localhost:5999/socle/';
const OUT = '/Users/openclaw/Desktop/labuse-fix-recette/docs/audit-2026-10/recette-generale-1/apres';
mkdirSync(OUT, { recursive: true });

const BRUIT = [/\/moi\/prefs-carte/, /favicon/];
const estBruit = (u) => BRUIT.some((re) => re.test(u));

const browser = await chromium.launch({ channel: 'chrome' });

// Un contexte neuf + journal console/http par capture.
async function fresh() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 980 } });
  const page = await context.newPage();
  const journal = [];
  page.on('console', (m) => {
    const t = m.text();
    if ((m.type() === 'error' || m.type() === 'warning') && !/Failed to load resource/i.test(t) && !estBruit(t))
      journal.push(`[${m.type()}] ${t}`);
  });
  page.on('pageerror', (e) => journal.push(`[pageerror] ${String(e)}`));
  page.on('response', (r) => { if (r.status() >= 400 && !estBruit(r.url())) journal.push(`[http] ${r.status()} ${r.request().method()} ${r.url()}`); });
  return { context, page, journal };
}
async function boot(page, hash = '') {
  await page.goto(BASE + hash, { waitUntil: 'domcontentloaded', timeout: 45000 });
  try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
  await page.waitForTimeout(1500);
}
const shot = (page, name) => page.screenshot({ path: `${OUT}/${name}` });
const report = {};

// ─────────────────────────────────────────────────────────────────────────
// A-02-1 — fiche RNU Saint-Philippe : tuile « Zone » = « Non publié au GPU » ENTIER
{
  const { context, page } = await fresh();
  try {
    await boot(page, '#idu=97417000BD0967');
    await page.waitForTimeout(8000);
    const zone = await page.evaluate(() => {
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walk.nextNode())) {
        if (/Non publié au GPU/.test(n.nodeValue || '')) {
          const el = n.parentElement;
          return { trouve: true, texte: n.nodeValue.trim(),
                   scrollW: el.scrollWidth, clientW: el.clientWidth,
                   tronque: el.scrollWidth > el.clientWidth + 1 };
        }
      }
      return { trouve: false };
    });
    report['A-02-1'] = zone;
    await shot(page, 'A-02-1_apres_fiche_rnu.png');
  } catch (e) { report['A-02-1'] = { error: String(e) }; }
  await context.close();
}

// ─────────────────────────────────────────────────────────────────────────
// A-01-1 — recherche absurde → dropdown « Aucun résultat »
{
  const { context, page } = await fresh();
  try {
    await boot(page);
    const input = await page.$('[data-omnibox], [data-suggest-input]');
    if (!input) throw new Error('barre de recherche introuvable');
    await input.click();
    await input.fill('zzzqwerty');
    await page.waitForTimeout(2800);
    const vide = await page.evaluate(() => {
      const el = document.querySelector('[data-suggest-vide]');
      return el ? (el.innerText || '').trim() : null;
    });
    report['A-01-1'] = { dropdownVide: vide, visible: !!vide };
    await shot(page, 'A-01-1_apres_recherche.png');
  } catch (e) { report['A-01-1'] = { error: String(e) }; }
  await context.close();
}

// ─────────────────────────────────────────────────────────────────────────
// A-05-2 — Bilan en anonyme : « générer » → invite à se connecter (plus « Génération impossible. »)
{
  const { context, page } = await fresh();
  try {
    await boot(page, '#idu=97422000BX1106');
    await page.waitForTimeout(10000);
    const btn = await page.$('[data-banquier-btn]');
    if (!btn) throw new Error('bouton Financier/Bilan introuvable');
    await btn.scrollIntoViewIfNeeded().catch(() => {});
    await btn.click();
    await page.waitForTimeout(2500);
    const clicked = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find((x) => /générer le bilan/i.test(x.innerText || ''));
      if (b) { b.click(); return true; }
      return false;
    });
    await page.waitForTimeout(4000);
    const msg = await page.evaluate(() => document.body.innerText);
    report['A-05-2'] = {
      clickGenerer: clicked,
      inviteConnexion: /connectez-vous à votre compte/i.test(msg),
      messageImpossibleMuet: /génération impossible\./i.test(msg),
    };
    await shot(page, 'A-05-2_apres_bilan.png');
  } catch (e) { report['A-05-2'] = { error: String(e) }; }
  await context.close();
}

// ─────────────────────────────────────────────────────────────────────────
// A-08-1 — deep-link courrier : parcelle société pré-remplie comme destinataire
{
  const { context, page } = await fresh();
  try {
    await boot(page, '#idu=97416000EW0446&m=courriers');
    await page.waitForTimeout(10000);
    const info = await page.evaluate(() => {
      const txt = document.body.innerText;
      return {
        courrierOuvert: /Courrier propriétaire|1 · Destinataires/i.test(txt),
        nbDestinataire: (txt.match(/(\d+) destinataire/) || [])[1] || null,
        refPrefillVisible: /EW ?0446/i.test(txt),
        societeVisible: /DECORASUD/i.test(txt),
      };
    });
    report['A-08-1'] = info;
    await shot(page, 'A-08-1_apres_courrier_prefill.png');
  } catch (e) { report['A-08-1'] = { error: String(e) }; }
  await context.close();
}

// ─────────────────────────────────────────────────────────────────────────
// A-03-1 — fiche commune : console 0 warning « duplicate / same key »
{
  const { context, page, journal } = await fresh();
  try {
    await boot(page);
    journal.length = 0;
    await page.evaluate(() => { window.__labuse.setContexteCommune('Saint-Denis'); });
    try { await page.waitForSelector('[data-contexte-panel]', { timeout: 14000 }); } catch {}
    try { await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 }); } catch {}
    await page.waitForTimeout(3000);
    const ids = await page.$$eval('[data-acc]', (els) => els.map((e) => e.getAttribute('data-acc')).slice(0, 12));
    for (const id of ids) {
      const s = await page.$(`[data-ligne-carte="${id}"]`);
      if (s) { await s.click({ timeout: 1500 }).catch(() => {}); await page.waitForTimeout(250); }
    }
    await page.waitForTimeout(1000);
    const j = [...journal];
    const dupKeys = j.filter((l) => /same key|duplicate key|two children with the same key|unique "key"/i.test(l));
    report['A-03-1'] = { totalConsole: j.length, duplicateKey: dupKeys.length, dupLines: dupKeys };
    await shot(page, 'A-03-1_apres_commune.png');
    writeFileSync(`${OUT}/A-03-1_apres_commune_console.txt`,
      `A-03-1 — console de la fiche commune Saint-Denis (après correctif)\n` +
      `Date: ${new Date().toISOString()}\n` +
      `Geste : ouverture ContextePanel Saint-Denis + dépliage de ${ids.length} cartes.\n\n` +
      `Warnings « duplicate / same key » : ${dupKeys.length} (attendu : 0)\n` +
      (dupKeys.length ? dupKeys.map((l) => '  ' + l).join('\n') + '\n' : '  (aucun)\n') +
      `\n--- Toutes les lignes console/http retenues (bruit connu /moi/prefs-carte + favicon filtré) : ${j.length} ---\n` +
      (j.length ? j.map((l) => '  ' + l).join('\n') : '  (console vide)') + '\n');
  } catch (e) { report['A-03-1'] = { error: String(e) }; }
  await context.close();
}

// ─────────────────────────────────────────────────────────────────────────
// A-08-3 — deep-link mort #surveillance=secteurs → ouvre proprement le volet « parcelles »
{
  const { context, page, journal } = await fresh();
  try {
    await boot(page, '#surveillance=secteurs');
    await page.waitForTimeout(8000);
    const info = await page.evaluate(() => {
      const txt = document.body.innerText;
      return {
        hash: location.hash,
        voletFoncierParcelles: /VEILLE · LE FONCIER|Vos parcelles suivies/i.test(txt),
        mentionneParcelles: /parcelle/i.test(txt),
        slice: txt.slice(0, 420).replace(/\n/g, ' / '),
      };
    });
    report['A-08-3'] = { ...info, console: [...journal] };
    await shot(page, 'A-08-3_apres.png');
  } catch (e) { report['A-08-3'] = { error: String(e) }; }
  await context.close();
}

console.log(JSON.stringify(report, null, 2));
await browser.close();
