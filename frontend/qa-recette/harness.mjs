// Harnais partagé de la RECETTE-GENERALE-1. Importé par chaque agent de famille.
// Pilote le Google Chrome du système (channel:'chrome') — macOS 13 n'a pas de
// binaire Playwright compatible. LECTURE SEULE : ne corrige rien, ne poste rien.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

export const BASE = process.env.RECETTE_BASE || 'http://localhost:5998/socle/';
export const API = process.env.RECETTE_API || 'http://127.0.0.1:8798';

// Bruit de fond CONNU en session anonyme (à ne PAS compter comme anomalie) :
export const BRUIT_CONNU = [
  /\/moi\/prefs-carte/,          // 401 : préférences carte d'un user non connecté
  /favicon/,
];

export function estBruit(url) {
  return BRUIT_CONNU.some((re) => re.test(url));
}

// Ouvre un navigateur. mobile=true → viewport téléphone 390px.
export async function ouvrir({ mobile = false } = {}) {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext(
    mobile
      ? { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
          userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1' }
      : { viewport: { width: 1440, height: 900 } }
  );
  const page = await context.newPage();
  const journal = { consoleErrors: [], httpErrors: [], pageErrors: [] };
  page.on('console', (m) => {
    const t = m.text();
    // « Failed to load resource » : écho sans URL d'une réponse HTTP — déjà traitée
    // (avec URL + filtre bruit) par le handler `response`. On ne la compte pas deux fois.
    if (m.type() === 'error' && !/Failed to load resource/i.test(t) && !estBruit(t)) {
      journal.consoleErrors.push(t);
    }
  });
  page.on('pageerror', (e) => journal.pageErrors.push(String(e)));
  page.on('response', (r) => {
    if (r.status() >= 400 && !estBruit(r.url())) journal.httpErrors.push(`${r.status()} ${r.request().method()} ${r.url()}`);
  });
  return { browser, context, page, journal };
}

// Navigue vers un hash et mesure le temps jusqu'à networkidle (ms).
export async function aller(page, hash = '', { timeout = 40000 } = {}) {
  const t0 = Date.now();
  await page.goto(BASE + hash, { waitUntil: 'domcontentloaded', timeout });
  try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
  return Date.now() - t0;
}

// Deep-links (voir App.tsx) :
export const lien = {
  fiche: (idu) => `#idu=${idu}`,
  commune: (nom) => `#c=${encodeURIComponent(nom)}`,
  outil: (key) => `#m=${key}`,
  outilSurParcelle: (key, idu) => `#idu=${idu}&m=${key}`,
  admin: () => `#admin=1`,
  radar: () => `#radar=1`,
  surveillance: (vue) => `#surveillance=${vue}`,
};

let _cpt = 0;
// Capture d'écran dans captures/<famille>/<nom>.png (chemin absolu renvoyé).
export async function shot(page, famille, nom, { full = false } = {}) {
  const dir = `/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/${famille}`;
  mkdirSync(dir, { recursive: true });
  const safe = String(nom).replace(/[^a-zA-Z0-9_-]/g, '_');
  const path = `${dir}/${String(++_cpt).padStart(3, '0')}_${safe}.png`;
  await page.screenshot({ path, fullPage: full });
  return path;
}

// Vrai si un élément déborde horizontalement de son conteneur (texte coupé / overflow).
export async function debordements(page) {
  return page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('*')) {
      if (el.scrollWidth > el.clientWidth + 4 && el.clientWidth > 0) {
        const txt = (el.textContent || '').trim().slice(0, 40);
        if (txt) out.push({ tag: el.tagName, cls: String(el.className).slice(0, 40), txt });
      }
    }
    return out.slice(0, 25);
  });
}
