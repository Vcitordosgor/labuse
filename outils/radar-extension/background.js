// LABUSE Radar — service worker (orchestrateur MV3).
// Ouvre un onglet en arrière-plan sur la recherche Leboncoin, lit le
// __NEXT_DATA__ de la page "riche" et envoie le HTML brut au back LABUSE.
// Rythme humain, plafonds durs, arrêt net sur blocage.

const ALARM_NAME = "radar-soir";

// ---- Plafonds durs (doctrine) --------------------------------------------
const CAP_TOTAL_PAGES = 40; // jamais plus de 40 pages dans une soirée
const CAP_NOUVELLES = 15; // passe "nouvelles"
const CAP_RELECTURE = 20; // ~20 pages d'inventaire en rotation
const CAP_CONFIRMATION = 60; // liens de confirmation par soirée

// ---- Délais rythme humain (ms) -------------------------------------------
const NAV_MIN = 4000;
const NAV_MAX = 8000;
const CONF_MIN = 8000;
const CONF_MAX = 15000;

// ---- Bien'ici (RADAR-SOURCES-2) : capture par APPEL API, pas lecture de page ----------------
// Bien'ici est une SPA Angular : les annonces n'arrivent PAS dans le HTML mais par un appel JSON
// `realEstateAds.json`. L'extension fait ce fetch() MÊME-ORIGINE depuis la session réelle de Vic
// (doctrine §2 : vraie session, vrais en-têtes/cookies — jamais un robot serveur) et POSTE le JSON
// tel quel au serveur, exactement comme le HTML Leboncoin. Le serveur reconnaît le payload (clé
// `realEstateAds`) et le traduit (html_next.aplatir_bienici).
const BIENICI_SIZE = 24;                 // annonces par appel (= pagination du site)
const BIENICI_ZONE_REUNION = "-77601";   // identifiant de zone « La Réunion » (observé — à CONFIRMER par Vic)
// Base des filtres « VENTES, toute La Réunion » (à confirmer par Vic). L'extension y ajoute size/from/page.
const BIENICI_FILTERS = {
  filterType: "buy",
  propertyType: ["house", "flat", "terrain", "loft", "townhouse", "castle", "building", "parking", "premises"],
  sortBy: "relevance", sortOrder: "desc", onTheMarket: [true],
  zoneIdsByTypes: { zoneIds: [BIENICI_ZONE_REUNION] }
};
const BIENICI_CAP_NOUVELLES = 15;        // appels « nouvelles » (comme Leboncoin ; ~360 annonces max)
const BIENICI_CAP_RELECTURE = 20;        // appels « relecture » en rotation

// Les 24 communes de La Réunion (ordre du mandat).
const COMMUNES = [
  "Saint-Denis", "Sainte-Marie", "Sainte-Suzanne", "Saint-André",
  "Bras-Panon", "Salazie", "Saint-Benoît", "La Plaine-des-Palmistes",
  "Sainte-Rose", "Saint-Philippe", "Saint-Joseph", "Petite-Île",
  "Saint-Pierre", "Le Tampon", "Entre-Deux", "Cilaos",
  "Saint-Louis", "L'Étang-Salé", "Les Avirons", "Saint-Leu",
  "Trois-Bassins", "Saint-Paul", "La Possession", "Le Port"
];

// =========================================================================
// Utilitaires
// =========================================================================

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function jitter(min, max) {
  return Math.floor(min + Math.random() * (max - min));
}

function nowIso() {
  return new Date().toISOString();
}

async function getOpts() {
  const d = await chrome.storage.local.get({
    searchUrl: "",
    // RADAR-SOURCES-2 — page de recherche Bien'ici (VENTES, toute La Réunion). Sert à OUVRIR un onglet
    // bienici.com (session chaude) d'où partent les fetch() même-origine ; vide = Bien'ici désactivé.
    bieniciSearchUrl: "",
    bieniciRelectureCursor: 0,
    // RADAR-FIX-2 (Lot B) — PROD par défaut : l'extension nourrit https://app.labuse.immo. localhost ne sert
    // qu'en recette, en le tapant EXPLICITEMENT dans les Options.
    labuseUrl: "https://app.labuse.immo",
    token: "",
    hour: 21,
    jitterMaxMin: 180,
    relectureCursor: 0,
    lastRun: null,
    lastResult: null,
    // RADAR-FIX-2 (Lot A) — pilotage du déclenchement automatique du soir (heartbeat).
    autoRunDate: "",        // date locale (YYYY-MM-DD) de la dernière capture AUTO : une seule par soir
    todayTargetDate: "",    // jour pour lequel la minute-cible ci-dessous a été tirée
    todayTargetTs: 0,       // instant-cible (dans la fenêtre du soir) tiré une fois par jour
    running: false,         // un run est en cours (garde anti double-déclenchement entre réveils du worker)
    // RADAR-FIX-2 (Lot B) — hôte LABUSE de la dernière capture réussie : un changement = BASCULE → rattrapage.
    lastCaptureHost: ""
  });
  return d;
}

// RADAR-FIX-2 — hôte d'une URL (pour détecter la bascule localhost→prod).
function hostOf(url) {
  try { return new URL(url).host; } catch (_) { return ""; }
}

// RADAR-SOURCES-2 — reconnaissance du portail d'une URL (routage des passes et de la confirmation).
function isBienici(url) { return /(^|\.)bienici\.com$/i.test(hostOf(url)); }
function isLeboncoin(url) { return /(^|\.)leboncoin\.fr$/i.test(hostOf(url)); }

// L'id Bien'ici est le DERNIER segment de l'URL d'annonce (« …/immo-facile-61412190 ») — c'est lui qui
// résout l'annonce chez Bien'ici. On l'extrait pour interroger l'API d'une annonce seule (confirmation).
function bieniciIdFromUrl(url) {
  try {
    const p = new URL(url).pathname.replace(/\/+$/, "").split("/");
    return p[p.length - 1] || null;
  } catch (_) { return null; }
}

// RADAR-FIX-2 — date locale YYYY-MM-DD (le « soir » se juge en heure locale de la machine qui capture).
function localDateStr(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

async function setOpts(patch) {
  await chrome.storage.local.set(patch);
}

// Badge d'action : ✓ + heure au succès, ✗ au blocage/erreur.
async function setBadge(text, color) {
  try {
    await chrome.action.setBadgeText({ text });
    if (color) await chrome.action.setBadgeBackgroundColor({ color });
  } catch (_) { /* action indisponible : on ignore */ }
}

async function notify(message) {
  try {
    await chrome.notifications.create({
      type: "basic",
      iconUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
      title: "LABUSE Radar",
      message
    });
  } catch (_) { /* notifications indisponibles : on ignore */ }
}

// Erreur "blocage" : on arrête tout et on prévient.
class BlockError extends Error {}

// =========================================================================
// Génération des 24 URLs par commune
// =========================================================================
//
// ATTENTION — l'encodage exact du paramètre `locations` de Leboncoin n'est
// PAS connu ici (format type "Saint-Denis_97400" ou identifiant interne).
// À VALIDER en Lot 0.2 / recette avec Vic sur une vraie URL.
// Implémentation défensive : si `locations=` est présent et contient un
// libellé de commune reconnaissable, on le remplace commune par commune ;
// sinon on retombe sur l'URL île entière (une seule entrée).
function communeUrls(searchUrl) {
  if (!searchUrl) return [];
  let u;
  try {
    u = new URL(searchUrl);
  } catch (_) {
    return [searchUrl];
  }
  const loc = u.searchParams.get("locations");
  if (!loc) {
    // Pas de paramètre locations : on ne sait pas cibler une commune.
    return [searchUrl];
  }
  // On cherche si le token actuel ressemble à l'une des communes connues.
  const decoded = decodeURIComponent(loc);
  const matched = COMMUNES.find((c) =>
    decoded.toLowerCase().includes(c.toLowerCase())
  );
  if (!matched) {
    // Format inconnu : repli île entière (recette validera l'encodage).
    return [searchUrl];
  }
  // On produit une variante par commune en substituant le libellé reconnu.
  return COMMUNES.map((c) => {
    const v = new URL(searchUrl);
    const newLoc = decoded.replace(new RegExp(matched, "i"), c);
    v.searchParams.set("locations", newLoc);
    return v.toString();
  });
}

// =========================================================================
// Onglet de travail + injection
// =========================================================================

async function openWorkTab(url) {
  const tab = await chrome.tabs.create({ url, active: false });
  await waitTabComplete(tab.id);
  return tab.id;
}

function waitTabComplete(tabId, timeoutMs = 25000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    const check = async () => {
      let t;
      try {
        t = await chrome.tabs.get(tabId);
      } catch (_) {
        return reject(new Error("Onglet fermé"));
      }
      if (t.status === "complete") return resolve();
      if (Date.now() > deadline) return resolve(); // on tente quand même la lecture
      setTimeout(check, 500);
    };
    check();
  });
}

// Fonction injectée DANS la page vivante. Ne lit que le DOM live.
function inspectPage() {
  const out = {
    hasNext: false,
    nextData: null,
    hasAditemContainer: false,
    looksBlocked: false,
    outerHTML: "",
    bodyText: "",
    title: "",
    indexDates: []
  };
  try {
    out.outerHTML = document.documentElement.outerHTML;
    // RADAR-FIX-3 — on garde le TEXTE VISIBLE (innerText) à part : la reconnaissance « annonce
    // expirée » doit se faire sur ce que l'utilisateur voit, pas sur le HTML/JS complet (où « 404 »,
    // « expirée »… traînent dans les scripts et déclenchaient de fausses suppressions).
    out.bodyText = (document.body ? document.body.innerText : "");
    out.title = document.title || "";

    // Détection blocage / captcha / vérification.
    const bodyTxt = out.bodyText.toLowerCase();
    const hay = (bodyTxt + " " + document.title + " " + location.href).toLowerCase();
    const blockers = ["datadome", "captcha", "verification", "vérification", "challenge", "access denied"];
    if (blockers.some((b) => hay.includes(b))) out.looksBlocked = true;

    // __NEXT_DATA__ (page riche).
    const nd = document.querySelector("#__NEXT_DATA__");
    if (nd && nd.textContent) {
      try {
        out.nextData = JSON.parse(nd.textContent);
      } catch (_) { out.nextData = null; }
    }

    // Cartes DOM (page dégradée).
    out.hasAditemContainer = !!document.querySelector('[data-test-id="aditem_container"], [data-qa-id="aditem_container"], .aditem_container');

    // Dates d'annonces (max = index_date le plus récent).
    const ads = out.nextData
      && out.nextData.props
      && out.nextData.props.pageProps
      && out.nextData.props.pageProps.searchData
      && out.nextData.props.pageProps.searchData.ads;
    if (Array.isArray(ads)) {
      for (const a of ads) {
        const d = a && (a.index_date || a.first_publication_date);
        if (d) out.indexDates.push(String(d));
      }
    }

    // Présence d'un lien "page suivante" cliquable ?
    const nextEl = document.querySelector(
      'a[title="Page suivante"], [aria-label*="suivante" i], a[rel="next"], link[rel="next"]'
    );
    out.hasNext = !!nextEl;
  } catch (e) {
    // En cas d'erreur imprévue on renvoie ce qu'on a.
  }
  return out;
}

// Fonction injectée pour cliquer le "page suivante" du site (nav Next.js).
function clickNext() {
  const el = document.querySelector(
    'a[title="Page suivante"], [aria-label*="suivante" i], a[rel="next"]'
  );
  if (!el) return false;
  el.scrollIntoView();
  el.click();
  return true;
}

async function inject(tabId, fn) {
  const res = await chrome.scripting.executeScript({
    target: { tabId },
    func: fn
  });
  return res && res[0] ? res[0].result : null;
}

// =========================================================================
// Appels back LABUSE (chaque appel porte X-Radar-Token)
// =========================================================================

async function apiCapture(opts, passe, url, page, html, capturedAt, source) {
  const r = await fetch(opts.labuseUrl.replace(/\/$/, "") + "/admin/radar/capture", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Radar-Token": opts.token },
    // RADAR-FIX-2 (Lot A) — `source` grave le déclencheur (auto | manuel) côté back (journal + dashboard).
    body: JSON.stringify({ passe, url, page, html, captured_at: capturedAt, source: source || "auto" })
  });
  if (!r.ok) throw new Error("capture HTTP " + r.status);
  return r.json();
}

async function apiEtat(opts) {
  const r = await fetch(opts.labuseUrl.replace(/\/$/, "") + "/admin/radar/etat", {
    method: "GET",
    headers: { "X-Radar-Token": opts.token }
  });
  if (!r.ok) throw new Error("etat HTTP " + r.status);
  return r.json();
}

// RADAR-FIX-3 — toute la passe en UN envoi : c'est l'unité sur laquelle le serveur applique le
// garde-fou des 30 %. On ne poste plus lien par lien.
async function apiConfirmationBatch(opts, items) {
  const r = await fetch(opts.labuseUrl.replace(/\/$/, "") + "/admin/radar/confirmation-batch", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Radar-Token": opts.token },
    body: JSON.stringify({ items })
  });
  if (!r.ok) throw new Error("confirmation-batch HTTP " + r.status);
  return r.json();
}

// =========================================================================
// Lecture d'une page + garde-fous blocage
// =========================================================================

async function readPage(tabId) {
  const info = await inject(tabId, inspectPage);
  if (!info) throw new BlockError("Lecture impossible");
  if (info.looksBlocked) throw new BlockError("Page de vérification détectée");
  // Ni searchData ni cartes DOM = page inutilisable → blocage.
  const hasSearchData = !!(info.nextData
    && info.nextData.props
    && info.nextData.props.pageProps
    && info.nextData.props.pageProps.searchData);
  if (!hasSearchData && !info.hasAditemContainer) {
    throw new BlockError("Ni searchData ni cartes d'annonces");
  }
  return info;
}

function maxDate(dates) {
  let m = null;
  for (const d of dates) {
    const t = Date.parse(d);
    if (!isNaN(t) && (m === null || t > m)) m = t;
  }
  return m;
}

// =========================================================================
// Les trois passes
// =========================================================================

// Renvoie le nb de pages consommées (pour le plafond total).
// RADAR-FIX-2 (Lot B) — `rattrapage` (1ʳᵉ capture après bascule vers la prod) : on remonte PLUS LOIN que
// les 15 pages d'une soirée normale, jusqu'au plafond dur de 40 pages, pour rattraper depuis la dernière
// annonce connue en prod. La RÈGLE D'ARRÊT ne change pas : on s'arrête dès qu'une page ne porte plus
// d'annonce plus récente que le seuil (index_date). Le plafond 40 reste la garde dure.
async function passeNouvelles(opts, tabId, capturedAt, etat, budget, source, rattrapage) {
  const seuil = etat && etat.derniere_capture_at
    ? Date.parse(etat.derniere_capture_at) - 3600 * 1000 // −1 h
    : null;
  let page = 1;
  let used = 0;
  const plafond = rattrapage ? CAP_TOTAL_PAGES : CAP_NOUVELLES;
  const maxPages = Math.min(plafond, budget);
  while (page <= maxPages) {
    const info = await readPage(tabId);
    await apiCapture(opts, "nouvelles", opts.searchUrl, page, info.outerHTML, capturedAt, source);
    used++;
    // On continue tant que la page contient des annonces plus récentes que le seuil.
    const newest = maxDate(info.indexDates);
    if (seuil !== null && newest !== null && newest <= seuil) break;
    if (page >= maxPages || !info.hasNext) break;
    // Navigation via le "page suivante" du site (garde la page riche).
    await sleep(jitter(NAV_MIN, NAV_MAX));
    const ok = await inject(tabId, clickNext);
    if (!ok) break;
    await waitTabComplete(tabId);
    page++;
  }
  return used;
}

async function passeRelecture(opts, tabId, capturedAt, budget, source) {
  // Rotation : on reprend là où on s'était arrêté hier.
  let cursor = opts.relectureCursor || 0;
  const maxPages = Math.min(CAP_RELECTURE, budget);
  let used = 0;
  let page = 1;
  // On saute jusqu'au curseur puis on lit maxPages pages consécutives.
  // (La pagination du site est cliente ; on avance par "page suivante".)
  while (used < maxPages && page <= CAP_TOTAL_PAGES) {
    const info = await readPage(tabId);
    if (page > cursor) {
      await apiCapture(opts, "relecture", opts.searchUrl, page, info.outerHTML, capturedAt, source);
      used++;
    }
    if (!info.hasNext) {
      // Fin d'inventaire : on repart de zéro la prochaine soirée.
      cursor = 0;
      await setOpts({ relectureCursor: 0 });
      break;
    }
    await sleep(jitter(NAV_MIN, NAV_MAX));
    const ok = await inject(tabId, clickNext);
    if (!ok) break;
    await waitTabComplete(tabId);
    page++;
  }
  // On avance le curseur pour que l'inventaire complet passe en ≤7 jours.
  if (cursor !== 0) {
    await setOpts({ relectureCursor: cursor + used });
  }
  return used;
}

// RADAR-FIX-3 — SIGNATURES d'une annonce DISPARUE, lues sur le TEXTE VISIBLE (jamais le HTML/JS
// complet). Des PHRASES entières, pas des jetons « 404 »/« expirée » qui traînent partout dans le
// bundle et faisaient passer des pages en ligne pour supprimées (60/60 le 28/10).
const RE_ANNONCE_EXPIREE = /cette annonce n'est plus disponible|cette annonce a été supprimée|cette annonce (est|a été) désactivée|l'annonce que vous (recherchez|cherchez) n'est plus (disponible|en ligne)|annonce (expirée|supprimée|désactivée|n'existe plus)/i;
const RE_PAGE_404 = /la page que vous (recherchez|cherchez) (est introuvable|n'existe plus)|page introuvable|erreur 404|oups[^.]{0,40}introuvable/i;
const RE_PRIX_VISIBLE = /\d[\d  .]*€/;   // un prix affiché = signe fort d'une annonce bien présente

// Classe PUREMENT un lien vérifié, sans jamais faire confiance à un indice faible. Règle gravée :
// on ne retire QUE sur PREUVE POSITIVE (phrase d'expiration reconnue, ou page d'erreur 404 reconnue).
// Bloquée / vide / illisible / redirigée ailleurs = « inconnue » → non vérifiée (zéro retrait).
function classifierConfirmation(info, finalUrl, listId) {
  if (!info || !info.outerHTML) return { verdict: "inconnue", preuve: null, httpStatus: null };
  if (info.looksBlocked) return { verdict: "inconnue", preuve: null, httpStatus: null };

  const vis = ((info.bodyText || "") + "\n" + (info.title || ""));
  // Preuve POSITIVE d'abord (une page expirée peut aussi afficher des annonces « recommandées » avec
  // leurs prix — la PHRASE d'expiration tranche, pas la présence d'un prix).
  if (RE_ANNONCE_EXPIREE.test(vis)) return { verdict: "supprimee", preuve: "expiree", httpStatus: 410 };
  if (RE_PAGE_404.test(vis)) return { verdict: "supprimee", preuve: "http_404", httpStatus: 404 };

  // Toujours là : on est RESTÉ sur l'annonce (son list_id dans l'URL finale) ET on voit son contenu.
  const surLAnnonce = !!(finalUrl && listId && String(finalUrl).includes(String(listId)));
  const contenuAnnonce = !!(info.hasAditemContainer || RE_PRIX_VISIBLE.test(info.bodyText || ""));
  if (surLAnnonce && contenuAnnonce) return { verdict: "presente", preuve: null, httpStatus: 200 };

  // Redirigée (consentement/login/accueil), vide, ou contenu non reconnu → non vérifiée.
  return { verdict: "inconnue", preuve: null, httpStatus: null };
}

async function passeConfirmation(opts, tabId, items) {
  const liste = Array.isArray(items) ? items : [];
  const verdicts = [];
  let done = 0;
  for (const item of liste) {
    if (done >= CAP_CONFIRMATION) break;
    let res = { verdict: "inconnue", preuve: null, httpStatus: null };
    let bloque = false;
    try {
      await chrome.tabs.update(tabId, { url: item.url, active: false });
      await waitTabComplete(tabId);
      const t = await chrome.tabs.get(tabId);
      const finalUrl = t.url || "";
      const info = await inject(tabId, inspectPage);
      bloque = !!(info && info.looksBlocked);
      res = classifierConfirmation(info, finalUrl, item.list_id);
    } catch (e) {
      res = { verdict: "inconnue", preuve: null, httpStatus: null };
    }
    verdicts.push({ list_id: item.list_id, verdict: res.verdict, preuve: res.preuve,
                    url: item.url, http_status: res.httpStatus });
    done++;
    // Mur DataDome/captcha : on ARRÊTE la passe (on ne martèle pas) ; ces liens restent « non
    // vérifiés », donc aucun retrait. Le reste sera revu la prochaine fois.
    if (bloque) break;
    if (done < liste.length && done < CAP_CONFIRMATION) {
      await sleep(jitter(CONF_MIN, CONF_MAX));
    }
  }
  // La PASSE part en un seul envoi : le serveur y applique le garde-fou des 30 %.
  if (verdicts.length) await apiConfirmationBatch(opts, verdicts);
  return done;
}

// =========================================================================
// Bien'ici — capture par appel API (RADAR-SOURCES-2)
// =========================================================================

// Fonction INJECTÉE dans un onglet bienici.com : fetch() MÊME-ORIGINE (donc avec la session/cookies de
// Vic) de `realEstateAds.json` pour UNE page de filtres donnés. Retourne {status, body} — jamais ne lève.
async function biFetchResults(baseFilters, page, size) {
  const filters = Object.assign({}, baseFilters, { size, from: (page - 1) * size, page });
  const url = location.origin + "/realEstateAds.json?filters=" + encodeURIComponent(JSON.stringify(filters));
  try {
    const r = await fetch(url, { headers: { "x-requested-with": "XMLHttpRequest", "accept": "application/json" } });
    const body = await r.text();
    return { status: r.status, body };
  } catch (e) {
    return { status: 0, body: "", error: String(e) };
  }
}

// Fonction INJECTÉE : fetch() d'UNE annonce seule (confirmation). 404 = preuve POSITIVE de disparition ;
// 200 + status.onTheMarket=false = expirée ; 200 + onTheMarket = toujours présente.
async function biFetchAd(id) {
  const url = location.origin + "/realEstateAd.json?id=" + encodeURIComponent(id);
  try {
    const r = await fetch(url, { headers: { "x-requested-with": "XMLHttpRequest", "accept": "application/json" } });
    let onTheMarket = null, found = false;
    if (r.status === 200) {
      try { const j = JSON.parse(await r.text()); found = !!(j && j.id); onTheMarket = j && j.status ? !!j.status.onTheMarket : null; }
      catch (_) { found = false; }
    }
    return { status: r.status, found, onTheMarket };
  } catch (e) {
    return { status: 0, found: false, onTheMarket: null, error: String(e) };
  }
}

async function injectArgs(tabId, fn, args) {
  const res = await chrome.scripting.executeScript({ target: { tabId }, func: fn, args });
  return res && res[0] ? res[0].result : null;
}

// Lit une page de résultats Bien'ici et la poste. Retourne la liste des dates (modificationDate) des
// annonces de la page, pour la règle d'arrêt « plus rien de neuf » (comme index_date côté Leboncoin).
async function biCapturePage(opts, tabId, passe, page, capturedAt, source) {
  const res = await biFetchResults(BIENICI_FILTERS, page, BIENICI_SIZE);
  if (res.status === 429) throw new BlockError("Bien'ici 429 (trop vite) — on se calme");
  if (res.status !== 200 || !res.body) throw new BlockError("Bien'ici : réponse vide (HTTP " + res.status + ")");
  let ads = [];
  try { ads = (JSON.parse(res.body).realEstateAds) || []; } catch (_) { throw new BlockError("Bien'ici : JSON illisible"); }
  if (!ads.length) return { dates: [], empty: true };   // page au-delà du dernier résultat : fin propre
  // On poste le CORPS JSON brut (le serveur reconnaît `realEstateAds` et le traduit). Même route que LBC.
  await apiCapture(opts, passe, opts.bieniciSearchUrl, page, res.body, capturedAt, source);
  const dates = ads.map((a) => a && (a.modificationDate || a.publicationDate)).filter(Boolean).map(String);
  return { dates, empty: false };
}

async function passeNouvellesBienici(opts, tabId, capturedAt, etat, source) {
  const seuil = etat && etat.derniere_capture_at ? Date.parse(etat.derniere_capture_at) - 3600 * 1000 : null;
  let page = 1, used = 0;
  while (page <= BIENICI_CAP_NOUVELLES) {
    const { dates, empty } = await biCapturePage(opts, tabId, "nouvelles", page, capturedAt, source);
    used++;
    if (empty) break;
    const newest = maxDate(dates);
    if (seuil !== null && newest !== null && newest <= seuil) break;   // plus rien de plus récent
    await sleep(jitter(NAV_MIN, NAV_MAX));
    page++;
  }
  return used;
}

async function passeRelectureBienici(opts, tabId, capturedAt, source) {
  // Rotation : on reprend là où on s'était arrêté hier (curseur de page). Inventaire complet en ≤ quelques soirs.
  let cursor = opts.bieniciRelectureCursor || 0;
  let used = 0;
  while (used < BIENICI_CAP_RELECTURE) {
    const page = cursor + used + 1;
    const { empty } = await biCapturePage(opts, tabId, "relecture", page, capturedAt, source);
    used++;
    if (empty) { cursor = 0; break; }   // fin d'inventaire : on repart de la page 1 la prochaine fois
    await sleep(jitter(NAV_MIN, NAV_MAX));
  }
  await setOpts({ bieniciRelectureCursor: cursor === 0 ? 0 : cursor + used });
  return used;
}

// Classification PURE d'une annonce Bien'ici vérifiée (testable hors navigateur). Même doctrine
// RADAR-FIX-3 : on ne retire QUE sur preuve positive (404, ou off-market déclaré). Tout le reste = inconnue.
function classifierConfirmationBienici(ad) {
  if (!ad || ad.status === 0) return { verdict: "inconnue", preuve: null, httpStatus: null };
  if (ad.status === 404) return { verdict: "supprimee", preuve: "http_404", httpStatus: 404 };
  if (ad.status === 200 && ad.onTheMarket === false) return { verdict: "supprimee", preuve: "expiree", httpStatus: 410 };
  if (ad.status === 200 && ad.found) return { verdict: "presente", preuve: null, httpStatus: 200 };
  return { verdict: "inconnue", preuve: null, httpStatus: null };
}

async function passeConfirmationBienici(opts, tabId, items) {
  const liste = Array.isArray(items) ? items : [];
  const verdicts = [];
  let done = 0;
  for (const item of liste) {
    if (done >= CAP_CONFIRMATION) break;
    const id = bieniciIdFromUrl(item.url);
    let res = { verdict: "inconnue", preuve: null, httpStatus: null };
    if (id) {
      const ad = await injectArgs(tabId, biFetchAd, [id]);
      if (ad && ad.status === 429) break;          // mur anti-robots : on arrête (rien retiré)
      res = classifierConfirmationBienici(ad);
    }
    verdicts.push({ list_id: item.list_id, verdict: res.verdict, preuve: res.preuve,
                    url: item.url, http_status: res.httpStatus });
    done++;
    if (done < liste.length && done < CAP_CONFIRMATION) await sleep(jitter(CONF_MIN, CONF_MAX));
  }
  if (verdicts.length) await apiConfirmationBatch(opts, verdicts);
  return done;
}

// Bloc Bien'ici d'une soirée : ouvre un onglet bienici.com (session chaude), enchaîne nouvelles →
// relecture → confirmation (sous-ensemble Bien'ici de la liste à confirmer). Ferme l'onglet.
async function runSoireeBienici(opts, capturedAt, etat, confItems, source) {
  let tabId = null;
  try {
    tabId = await openWorkTab(opts.bieniciSearchUrl);
    const nNouv = await passeNouvellesBienici(opts, tabId, capturedAt, etat, source);
    const nRel = await passeRelectureBienici(opts, tabId, capturedAt, source);
    const nConf = await passeConfirmationBienici(opts, tabId, confItems);
    return { nNouv, nRel, nConf };
  } finally {
    if (tabId !== null) { try { await chrome.tabs.remove(tabId); } catch (_) {} }
  }
}

// =========================================================================
// Plan de soirée
// =========================================================================

// `source` = "auto" (alarme du soir) | "manuel" (bouton « Capturer maintenant »).
async function runEvening(source) {
  source = source || "auto";
  const opts = await getOpts();
  if ((!opts.searchUrl && !opts.bieniciSearchUrl) || !opts.labuseUrl || !opts.token) {
    await notify("Radar : configuration incomplète (Options).");
    await setBadge("✗", "#c0392b");
    await setOpts({ lastResult: "Configuration incomplète — ouvrez les Options (recherche, URL, jeton)." });
    return;
  }
  // RADAR-FIX-2 (Lot B) — BASCULE : si l'hôte LABUSE a changé depuis la dernière capture réussie (ou
  // première capture tout court), on est en rattrapage → `passeNouvelles` remonte jusqu'à 40 pages.
  const host = hostOf(opts.labuseUrl);
  const rattrapage = host !== (opts.lastCaptureHost || "");
  const capturedAt = nowIso();
  let tabId = null;
  let budget = CAP_TOTAL_PAGES;
  const parts = [];
  await setOpts({ running: true });
  try {
    // État courant du back (seuil "nouvelles" + liste à confirmer), partagé par les deux portails.
    const etat = await apiEtat(opts);
    const aConf = (etat && Array.isArray(etat.a_confirmer)) ? etat.a_confirmer : [];
    // Chaque portail ne confirme QUE ses propres liens (routage par hôte). Un lien d'un autre portail,
    // ou sans hôte reconnu, reste pour la voie manuelle — jamais classé à tort.
    const confLbc = aConf.filter((it) => isLeboncoin(it.url));
    const confBi = aConf.filter((it) => isBienici(it.url));

    // ── Bloc Leboncoin (inchangé : lecture de page riche + clics « page suivante ») ──
    if (opts.searchUrl) {
      tabId = await openWorkTab(opts.searchUrl);
      const nNouv = await passeNouvelles(opts, tabId, capturedAt, etat, budget, source, rattrapage);
      budget -= nNouv;
      let nRel = 0;
      if (budget > 0) {
        await chrome.tabs.update(tabId, { url: opts.searchUrl, active: false });
        await waitTabComplete(tabId);
        nRel = await passeRelecture(opts, tabId, capturedAt, budget, source);
        budget -= nRel;
      }
      const nConf = await passeConfirmation(opts, tabId, confLbc);
      parts.push(`LBC nouv ${nNouv}, relec ${nRel}, conf ${nConf}`);
      try { await chrome.tabs.remove(tabId); } catch (_) {}
      tabId = null;
    }

    // ── Bloc Bien'ici (RADAR-SOURCES-2 : appel API même-origine, pas de lecture de page) ──
    if (opts.bieniciSearchUrl) {
      const bi = await runSoireeBienici(opts, capturedAt, etat, confBi, source);
      parts.push(`BI nouv ${bi.nNouv}, relec ${bi.nRel}, conf ${bi.nConf}`);
    }

    const stamp = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    await setBadge("✓", "#27ae60");
    await setOpts({
      lastRun: capturedAt,
      lastCaptureHost: host,     // la bascule est consommée : les soirs suivants ne rattrapent plus
      lastResult: `OK ${stamp} (${source}${rattrapage ? ", rattrapage" : ""}) — ${parts.join(" · ")} → ${host}`
    });
  } catch (e) {
    // Blocage OU erreur réseau : on arrête net, on prévient, on n'insiste pas. Message LISIBLE dans le
    // popup (lastResult) ; côté back, l'absence de capture fait apparaître « Déposer Radar » dans À faire.
    await setBadge("✗", "#c0392b");
    const msg = e && e.message ? e.message : "erreur réseau";
    await setOpts({ lastRun: capturedAt, lastResult: `Échec (${source}) — ${msg}. Déposez à la main si ça dure.` });
    if (e instanceof BlockError) {
      await notify("Radar bloqué, dépose à la main");
    } else {
      await notify("Radar arrêté : " + msg);
    }
  } finally {
    await setOpts({ running: false });
    if (tabId !== null) {
      try { await chrome.tabs.remove(tabId); } catch (_) {}
    }
  }
}

// =========================================================================
// Planification (alarme quotidienne + jitter)
// =========================================================================

// RADAR-FIX-2 (Lot A) — POURQUOI l'alarme ne partait jamais seule, et le correctif.
//
// AVANT : une alarme UNIQUE (`when`) était posée pour « ce soir 21 h + jitter 0-3 h ». Trois défauts se
// cumulaient : (1) une alarme `when` unique à heure fixe est FRAGILE — si Chrome dort/est fermé pile sur
// ce créneau, l'alarme brûle au réveil (après minuit → la signature observée par l'audit), ou est
// ÉCRASÉE par le reschedule d'`onStartup` avant d'avoir pu partir ; (2) rien ne garantissait un passage
// DANS la fenêtre du soir une fois l'instant manqué ; (3) la capture ne portait aucune trace « auto ».
//
// APRÈS : un BATTEMENT DE CŒUR. Une alarme PÉRIODIQUE (toutes les 5 min) réveille le worker ; à chaque
// battement on regarde si on est DANS la fenêtre du soir [heure .. heure+jitter] et si on n'a pas encore
// capturé ce soir — si oui, on capture UNE fois (source « auto »). Robuste au déchargement MV3 (le
// périodique survit), honnête sur la fenêtre (Mac réveillé à 2 h = hors fenêtre → on NE capture pas à
// 2 h), et une seule capture par soir (garde `autoRunDate` posée AVANT le run).

const HEARTBEAT_MIN = 5;             // battement : on vérifie la fenêtre toutes les 5 minutes
const TEST_ALARM = "radar-soir-test"; // recette : déclenche un run « auto » dans 2 min

// Bornes de la fenêtre du soir pour un instant donné (heure locale). [début, fin].
function fenetreSoir(opts, now) {
  const debut = new Date(now); debut.setHours(opts.hour || 21, 0, 0, 0);
  const fin = debut.getTime() + (opts.jitterMaxMin || 180) * 60 * 1000;
  return { debut: debut.getTime(), fin };
}

// Décide (et exécute) la capture du soir. `force` = recette (ignore fenêtre + « déjà fait »).
async function maybeRunTonight(force) {
  const opts = await getOpts();
  const now = new Date();
  const today = localDateStr(now);
  const { debut, fin } = fenetreSoir(opts, now);

  // Minute-cible du jour : tirée UNE fois par date, dans la fenêtre (le jitter « humain » d'autrefois).
  let targetTs = opts.todayTargetTs;
  if (opts.todayTargetDate !== today) {
    targetTs = debut + Math.floor(Math.random() * ((fin - debut) + 1));
    await setOpts({ todayTargetDate: today, todayTargetTs: targetTs });
  }

  if (!force) {
    if (opts.autoRunDate === today) return;          // déjà capturé ce soir
    if (now.getTime() < targetTs) return;            // pas encore l'heure tirée
    if (now.getTime() > fin) return;                 // fenêtre du soir passée (réveil après minuit) → on s'abstient
  }
  if (opts.running) return;                          // un run est déjà en cours (entre deux réveils du worker)
  await setOpts({ autoRunDate: today });             // marque AVANT de lancer : une seule capture auto par soir
  await runEvening("auto");
}

// Le battement périodique. Idempotent : (re)créer avec le même nom remplace proprement.
async function ensureHeartbeat() {
  try {
    await chrome.alarms.create(ALARM_NAME, { periodInMinutes: HEARTBEAT_MIN, delayInMinutes: 1 });
  } catch (_) { /* API alarms indisponible : rien à faire */ }
}

// Au CHARGEMENT du worker (démarrage de Chrome, réveil, reprise après déchargement) et aux événements.
ensureHeartbeat();
chrome.runtime.onInstalled.addListener(() => { ensureHeartbeat(); });
chrome.runtime.onStartup.addListener(() => { ensureHeartbeat(); });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_NAME) { await maybeRunTonight(false); return; }
  if (alarm.name === TEST_ALARM) { await maybeRunTonight(true); return; }  // recette : run « auto » forcé
});

// Message depuis le popup : "Capturer maintenant" ou recette.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "run-now") {
    runEvening("manuel").then(() => sendResponse({ ok: true })).catch((e) =>
      sendResponse({ ok: false, error: String(e) })
    );
    return true; // réponse asynchrone
  }
  if (msg && msg.type === "reschedule") {
    // Nouvelle heure/jitter : on oublie la cible du jour (retirée au prochain battement) et on réarme.
    setOpts({ todayTargetDate: "", todayTargetTs: 0 })
      .then(ensureHeartbeat)
      .then(() => sendResponse({ ok: true }));
    return true;
  }
  // RADAR-FIX-2 (Lot A) — RECETTE : alarme à +2 min qui déclenche une capture AUTO (pas le bouton), pour
  // PROUVER que le chemin automatique part seul et laisse la trace « auto » dans le journal.
  if (msg && msg.type === "test-alarm") {
    const when = Date.now() + 2 * 60 * 1000;
    Promise.resolve(chrome.alarms.create(TEST_ALARM, { when }))
      .then(() => sendResponse({ ok: true, when: new Date(when).toISOString() }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // réponse asynchrone
  }
  return false;
});

// RADAR-FIX-3 — surface testable (recette hors-navigateur) : la classification PURE d'un lien vérifié.
// N'expose rien en production (le drapeau n'est posé que par la recette avant l'import).
if (globalThis.__RADAR_TEST__) {
  globalThis.__radar = { classifierConfirmation, classifierConfirmationBienici, bieniciIdFromUrl,
                         isBienici, isLeboncoin };
}
