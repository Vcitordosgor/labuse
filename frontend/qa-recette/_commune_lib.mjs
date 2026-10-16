import { shot, debordements, BASE } from './harness.mjs';

// Ouvre la fiche commune. NB : le deep-link #c=<nom> ne pose QUE le filtre commune
// (setCommune), il N'OUVRE PAS la fiche (ContextePanel = setContexteCommune). Le vrai geste :
// bouton selecteur commune (data-commune-select) -> bouton "voir la fiche ->" (data-fiche-commune).
// On tente le vrai geste UI ; repli robuste via window.__labuse.setContexteCommune.
export async function allerCommune(page, nom, { gesteReel = false } = {}) {
  const t0 = Date.now();
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 45000 });
  try { await page.waitForLoadState('networkidle', { timeout: 14000 }); } catch {}
  await page.waitForTimeout(800);
  let via = 'none';
  if (gesteReel) {
    // vrai geste : ouvrir le menu commune et cliquer "voir la fiche ->" de la bonne ligne
    try {
      const sel = await page.$('[data-commune-select]');
      if (sel) {
        await sel.click({ timeout: 2500 });
        await page.waitForTimeout(500);
        // trouver la ligne contenant le nom, cliquer son data-fiche-commune
        const clicked = await page.evaluate((n) => {
          const rows = [...document.querySelectorAll('[data-fiche-commune]')];
          for (const b of rows) {
            const row = b.closest('div');
            if (row && (row.innerText || '').includes(n)) { b.click(); return true; }
          }
          return false;
        }, nom);
        if (clicked) via = 'geste';
      }
    } catch {}
  }
  if (via !== 'geste') {
    // repli : pilotage direct
    await page.evaluate((n) => { const l = window.__labuse; if (l && l.setContexteCommune) l.setContexteCommune(n); }, nom);
    via = via === 'none' ? 'pilote' : via;
  }
  try { await page.waitForSelector('[data-contexte-panel]', { timeout: 12000 }); } catch {}
  // la donnee (bandeau) arrive apres le chargement du chunk lazy + fetch : on l'attend vraiment.
  try { await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 }); } catch {}
  await page.waitForTimeout(800);
  page.__via = via;
  return Date.now() - t0;
}

export async function panneauPresent(page) {
  return page.$('[data-contexte-panel]').then(x => !!x);
}

// Lit le bandeau 6 chiffres.
export async function bandeau(page) {
  return page.$eval('[data-bandeau-chiffres]', el => {
    const cells = [...el.querySelectorAll(':scope > div')].map(c => {
      const ps = [...c.querySelectorAll('p')].map(p => (p.innerText || '').trim());
      return { v: ps[0] || '', n: ps[1] || '', s: ps[2] || '' };
    });
    return cells;
  }).catch(() => []);
}

// Déplie toutes les cartes (details[data-acc]) et renvoie, par carte, le texte + détection vide muet.
export async function parcourirCartes(page) {
  const ids = await page.$$eval('[data-acc]', els => els.map(e => e.getAttribute('data-acc')));
  const result = {};
  for (const id of ids) {
    // valeur sur la ligne fermée (droite)
    let headVal = '';
    try { headVal = await page.$eval(`[data-acc="${id}"] summary`, s => (s.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120)); } catch {}
    // ACCORDEON : une seule carte ouverte a la fois (acc.openId). On CLIQUE le summary pour
    // ouvrir CETTE carte (ferme les autres), puis on lit le <div> de contenu (apres le summary).
    const dejaOuvert = await page.$eval(`[data-acc="${id}"]`, e => !!e.open).catch(() => false);
    if (!dejaOuvert) {
      const summary = await page.$(`[data-ligne-carte="${id}"]`);
      if (summary) { await summary.click({ timeout: 1500 }).catch(() => {}); await page.waitForTimeout(260); }
    }
    const content = await page.$eval(`[data-acc="${id}"]`, e => {
      // le corps = dernier enfant direct (div de contenu) ; sinon innerText moins summary
      const body = e.querySelector(':scope > div');
      if (body) return (body.innerText || '').trim();
      const sum = e.querySelector('summary');
      const full = (e.innerText || ''); const sumT = sum ? (sum.innerText || '') : '';
      return full.startsWith(sumT) ? full.slice(sumT.length).trim() : full.trim();
    }).catch(() => '');
    const t = content.toLowerCase();
    const honest = /non renseign|non mesur|non calcul|analyse incompl|sans objet|absent|aucun|pas d|non disponible|inconnu|non identifi|hors fichier|à vérifier|non résolu|estim|non rattach|règlement national|rnu|non recens|pas de p, reste|reste à/.test(t);
    const bad = /\bnan\b|undefined|null(?![a-z])|\[object/i.test(content);
    const vide = content.replace(/\s/g, '').length < 2;
    result[id] = {
      headVal,
      len: content.length,
      content: content.slice(0, 1500),
      bad,
      videMuet: (vide && !honest) || (content.length > 0 && content.replace(/—|\s/g, '').length < 3 && !honest),
    };
  }
  return result;
}

// Compte les tuiles "Étudier cette commune" et vérifie qu'elles sont cliquables.
export async function tuiles(page) {
  return page.evaluate(() => {
    const zone = document.querySelector('[data-etudier-commune]');
    if (!zone) return { present: false, n: 0 };
    const btns = [...zone.querySelectorAll('button')];
    return { present: true, n: btns.length, labels: btns.map(b => (b.innerText || '').trim()) };
  });
}

export { shot, debordements };
