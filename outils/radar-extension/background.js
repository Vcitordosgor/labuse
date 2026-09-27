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
    labuseUrl: "http://localhost:8205",
    token: "",
    hour: 21,
    jitterMaxMin: 180,
    relectureCursor: 0,
    lastRun: null,
    lastResult: null
  });
  return d;
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
    indexDates: []
  };
  try {
    out.outerHTML = document.documentElement.outerHTML;

    // Détection blocage / captcha / vérification.
    const bodyTxt = (document.body ? document.body.innerText : "").toLowerCase();
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

async function apiCapture(opts, passe, url, page, html, capturedAt) {
  const r = await fetch(opts.labuseUrl.replace(/\/$/, "") + "/admin/radar/capture", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Radar-Token": opts.token },
    body: JSON.stringify({ passe, url, page, html, captured_at: capturedAt })
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

async function apiConfirmation(opts, listId, verdict, url, httpStatus) {
  const r = await fetch(opts.labuseUrl.replace(/\/$/, "") + "/admin/radar/confirmation", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Radar-Token": opts.token },
    body: JSON.stringify({ list_id: listId, verdict, url, http_status: httpStatus })
  });
  if (!r.ok) throw new Error("confirmation HTTP " + r.status);
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
async function passeNouvelles(opts, tabId, capturedAt, etat, budget) {
  const seuil = etat && etat.derniere_capture_at
    ? Date.parse(etat.derniere_capture_at) - 3600 * 1000 // −1 h
    : null;
  let page = 1;
  let used = 0;
  const maxPages = Math.min(CAP_NOUVELLES, budget);
  while (page <= maxPages) {
    const info = await readPage(tabId);
    await apiCapture(opts, "nouvelles", opts.searchUrl, page, info.outerHTML, capturedAt);
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

async function passeRelecture(opts, tabId, capturedAt, budget) {
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
      await apiCapture(opts, "relecture", opts.searchUrl, page, info.outerHTML, capturedAt);
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

async function passeConfirmation(opts, tabId, etat) {
  const liste = (etat && Array.isArray(etat.a_confirmer)) ? etat.a_confirmer : [];
  let done = 0;
  for (const item of liste) {
    if (done >= CAP_CONFIRMATION) break;
    let verdict = "inconnue";
    let httpStatus = null;
    try {
      await chrome.tabs.update(tabId, { url: item.url, active: false });
      await waitTabComplete(tabId);
      const t = await chrome.tabs.get(tabId);
      const finalUrl = t.url || "";
      const info = await inject(tabId, inspectPage);
      if (info && info.looksBlocked) throw new BlockError("Vérification pendant confirmation");
      const txt = (info ? info.outerHTML : "").toLowerCase();
      const gone = /page introuvable|cette annonce n'est plus|n'existe plus|404|annonce supprimée|expirée/.test(txt);
      const redirectedAway = finalUrl && item.url && !finalUrl.includes(String(item.list_id));
      if (gone || redirectedAway) {
        verdict = "supprimee";
        httpStatus = gone ? 404 : 301;
      } else if (info && (info.hasAditemContainer || info.nextData || txt.includes("prix") || txt.includes("€"))) {
        verdict = "presente";
        httpStatus = 200;
      } else {
        verdict = "inconnue";
      }
    } catch (e) {
      if (e instanceof BlockError) throw e; // remonte pour stopper la soirée
      verdict = "inconnue";
    }
    await apiConfirmation(opts, item.list_id, verdict, item.url, httpStatus);
    done++;
    if (done < liste.length && done < CAP_CONFIRMATION) {
      await sleep(jitter(CONF_MIN, CONF_MAX));
    }
  }
  return done;
}

// =========================================================================
// Plan de soirée
// =========================================================================

async function runEvening() {
  const opts = await getOpts();
  if (!opts.searchUrl || !opts.labuseUrl || !opts.token) {
    await notify("Radar : configuration incomplète (Options).");
    await setBadge("✗", "#c0392b");
    return;
  }
  const capturedAt = nowIso();
  let tabId = null;
  let budget = CAP_TOTAL_PAGES;
  try {
    // Ouverture page 1 normalement (page riche).
    tabId = await openWorkTab(opts.searchUrl);

    // État courant du back (seuil "nouvelles" + liste à confirmer).
    const etat = await apiEtat(opts);

    // 1) Nouvelles.
    const nNouv = await passeNouvelles(opts, tabId, capturedAt, etat, budget);
    budget -= nNouv;

    // 2) Relecture (on rouvre page 1 pour repartir proprement).
    if (budget > 0) {
      await chrome.tabs.update(tabId, { url: opts.searchUrl, active: false });
      await waitTabComplete(tabId);
      const nRel = await passeRelecture(opts, tabId, capturedAt, budget);
      budget -= nRel;
    }

    // 3) Confirmation.
    const nConf = await passeConfirmation(opts, tabId, etat);

    const stamp = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    await setBadge("✓", "#27ae60");
    await setOpts({
      lastRun: capturedAt,
      lastResult: `OK ${stamp} — nouv ${nNouv}, relec ${CAP_TOTAL_PAGES - budget - nNouv}, conf ${nConf}`
    });
  } catch (e) {
    // Blocage OU erreur réseau : on arrête net, on prévient, on n'insiste pas.
    await setBadge("✗", "#c0392b");
    await setOpts({ lastRun: capturedAt, lastResult: "STOP — " + (e && e.message ? e.message : "erreur") });
    if (e instanceof BlockError) {
      await notify("Radar bloqué, dépose à la main");
    } else {
      await notify("Radar arrêté : " + (e && e.message ? e.message : "erreur réseau"));
    }
  } finally {
    if (tabId !== null) {
      try { await chrome.tabs.remove(tabId); } catch (_) {}
    }
  }
}

// =========================================================================
// Planification (alarme quotidienne + jitter)
// =========================================================================

async function scheduleDaily() {
  const opts = await getOpts();
  const now = new Date();
  const target = new Date();
  target.setHours(opts.hour || 21, 0, 0, 0);
  // Jitter : 0..jitterMaxMin minutes après l'heure de base.
  const extraMin = Math.floor(Math.random() * ((opts.jitterMaxMin || 180) + 1));
  target.setMinutes(target.getMinutes() + extraMin);
  if (target.getTime() <= now.getTime()) {
    target.setDate(target.getDate() + 1);
  }
  await chrome.alarms.create(ALARM_NAME, { when: target.getTime() });
}

// Auto-réarme (RADAR-FIX-1 · 3). En MV3 le service worker est ÉPHÉMÈRE : Chrome le décharge après
// ~30 s d'inactivité et le réveille pour délivrer un événement (alarme, message du popup…). Les
// `chrome.alarms` SURVIVENT à ce déchargement ET à la fermeture du popup (elles vivent dans le
// navigateur, pas dans le worker ni dans la page popup). Mais si l'alarme a été PERDUE (crash, mise à
// jour, profil réinitialisé), plus rien ne la recrée entre deux démarrages de Chrome. Donc à CHAQUE
// réveil du worker on vérifie qu'elle existe et on la recrée SI ELLE MANQUE (jamais sinon : on ne
// repousse pas l'heure du soir à chaque réveil).
async function ensureAlarm() {
  try {
    const a = await chrome.alarms.get(ALARM_NAME);
    if (!a) await scheduleDaily();
  } catch (_) { /* API alarms indisponible : rien à faire */ }
}

// Au CHARGEMENT du service worker (démarrage de Chrome, réveil, ou reprise après déchargement).
ensureAlarm();

chrome.runtime.onInstalled.addListener(() => { scheduleDaily(); });   // installation / mise à jour
chrome.runtime.onStartup.addListener(() => { scheduleDaily(); });     // démarrage de Chrome (nouveau jitter du jour)

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  await runEvening();
  // Reprogrammation pour le lendemain (avec un nouveau jitter).
  await scheduleDaily();
});

// Message depuis le popup : "Capturer maintenant" ou relecture de config.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "run-now") {
    runEvening().then(() => sendResponse({ ok: true })).catch((e) =>
      sendResponse({ ok: false, error: String(e) })
    );
    return true; // réponse asynchrone
  }
  if (msg && msg.type === "reschedule") {
    scheduleDaily().then(() => sendResponse({ ok: true }));
    return true;
  }
  // RADAR-FIX-1 (3) — RECETTE : forcer l'alarme à +2 min pour VOIR la capture partir par le chemin
  // ALARME (pas seulement « Capturer maintenant »). Prouve que l'alarme déclenche bien runEvening.
  if (msg && msg.type === "test-alarm") {
    const when = Date.now() + 2 * 60 * 1000;
    Promise.resolve(chrome.alarms.create(ALARM_NAME, { when }))
      .then(() => sendResponse({ ok: true, when: new Date(when).toISOString() }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // réponse asynchrone
  }
  return false;
});
