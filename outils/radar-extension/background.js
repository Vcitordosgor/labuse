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

// `source` = "auto" (alarme du soir) | "manuel" (bouton « Capturer maintenant »).
async function runEvening(source) {
  source = source || "auto";
  const opts = await getOpts();
  if (!opts.searchUrl || !opts.labuseUrl || !opts.token) {
    await notify("Radar : configuration incomplète (Options).");
    await setBadge("✗", "#c0392b");
    await setOpts({ lastResult: "Configuration incomplète — ouvrez les Options (URL, jeton)." });
    return;
  }
  // RADAR-FIX-2 (Lot B) — BASCULE : si l'hôte LABUSE a changé depuis la dernière capture réussie (ou
  // première capture tout court), on est en rattrapage → `passeNouvelles` remonte jusqu'à 40 pages.
  const host = hostOf(opts.labuseUrl);
  const rattrapage = host !== (opts.lastCaptureHost || "");
  const capturedAt = nowIso();
  let tabId = null;
  let budget = CAP_TOTAL_PAGES;
  await setOpts({ running: true });
  try {
    // Ouverture page 1 normalement (page riche).
    tabId = await openWorkTab(opts.searchUrl);

    // État courant du back (seuil "nouvelles" + liste à confirmer).
    const etat = await apiEtat(opts);

    // 1) Nouvelles (rattrapage = remontée profonde après une bascule).
    const nNouv = await passeNouvelles(opts, tabId, capturedAt, etat, budget, source, rattrapage);
    budget -= nNouv;

    // 2) Relecture (on rouvre page 1 pour repartir proprement).
    if (budget > 0) {
      await chrome.tabs.update(tabId, { url: opts.searchUrl, active: false });
      await waitTabComplete(tabId);
      const nRel = await passeRelecture(opts, tabId, capturedAt, budget, source);
      budget -= nRel;
    }

    // 3) Confirmation.
    const nConf = await passeConfirmation(opts, tabId, etat);

    const stamp = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    await setBadge("✓", "#27ae60");
    await setOpts({
      lastRun: capturedAt,
      lastCaptureHost: host,     // la bascule est consommée : les soirs suivants ne rattrapent plus
      lastResult: `OK ${stamp} (${source}${rattrapage ? ", rattrapage" : ""}) — nouv ${nNouv}, `
                  + `relec ${CAP_TOTAL_PAGES - budget - nNouv}, conf ${nConf} → ${host}`
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
