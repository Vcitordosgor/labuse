// Helpers pour la Famille 4 — Outils
export const FAM = '04-outils';
import { BASE } from './harness.mjs';

// L'app ne lit le hash QU'AU MONTAGE (App.tsx useEffect []), aucun listener hashchange.
// Un page.goto qui ne change que le fragment ne recharge pas → tous les outils
// montreraient le PREMIER ouvert. On force un vrai reload via un query param busting,
// placé AVANT le hash (…/socle/?r=N#m=key). Renvoie le temps (ms).
let _r = 0;
export async function allerOutil(page, hash, { timeout = 40000 } = {}) {
  const t0 = Date.now();
  const url = BASE.replace(/\/$/, '/') + `?r=${++_r}` + hash;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
  try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
  return Date.now() - t0;
}

// Parcelles témoins
export const P = {
  saine: '97422000BX1106',       // Le Tampon R+6
  saineSD: '97411000AT0427',     // Saint-Denis
  rnu: '97417000BD0967',         // Saint-Philippe (RNU)
  disparue: '97416000IE0438',    // Saint-Pierre (disparue cadastre)
  empriseSat: '97411000AY0015',  // Saint-Denis (emprise saturée)
  grand2ha: '97411000IO0059',    // Saint-Denis (>2ha)
  nonCalibre: '97410000AE0144',  // Saint-Benoit (non calibré)
  horsClass: '97415000CH0065',   // Saint-Paul (hors classement)
  societe: '97416000EW0446',     // Saint-Pierre (PM)
};

// Attend la disparition d'un spinner + un peu de contenu dans le panneau outil
export async function attendreOutil(page, { timeout = 60000 } = {}) {
  const t0 = Date.now();
  // networkidle déjà fait par aller(); on laisse le contenu s'installer
  try {
    await page.waitForFunction(() => {
      const t = document.body.innerText || '';
      return t.length > 200;
    }, { timeout });
  } catch {}
  return Date.now() - t0;
}

// Résumé de l'état d'un panneau outil : texte visible, présence spinner, boutons
export async function etatOutil(page) {
  return page.evaluate(() => {
    const spinners = document.querySelectorAll('[class*="anim"],[class*="spin"],[class*="loader"],[class*="Loader"]').length;
    const boutons = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null).map(b => (b.innerText||'').trim().slice(0,30)).filter(Boolean);
    const txt = (document.body.innerText || '').replace(/\s+/g,' ').trim();
    const hasNaN = /NaN|undefined|\[object Object\]/.test(txt);
    const vide = txt.length < 120;
    return { len: txt.length, spinners, boutons: boutons.slice(0,25), hasNaN, vide, extrait: txt.slice(0, 600) };
  });
}
