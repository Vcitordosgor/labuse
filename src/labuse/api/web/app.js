"use strict";
// Session expirée en cours d'usage : tout 401 d'API renvoie à la page de connexion
// (la page elle-même est déjà protégée par redirection côté serveur).
const _nativeFetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const r = await _nativeFetch(...args);
  if (r.status === 401) { window.location.href = "/login"; throw new Error("session expirée"); }
  return r;
};
const COMMUNE = "Saint-Paul";
const COLORS = { opportunite: "#2DBE87", a_creuser: "#C88422", exclue: "#7C8694", faux_positif_probable: "#D76055", inconnu: "#9BA3AF" };
const STATUS_LABEL = { opportunite: "Opportunité", a_creuser: "À creuser", exclue: "Exclue", faux_positif_probable: "Écartée" };
const VERDICT_GLOSS = {
  opportunite: "Foncier a priori mobilisable — reste à confirmer sur le terrain.",
  a_creuser: "Signaux mitigés : une vérification s'impose avant de démarcher.",
  exclue: "Contrainte rédhibitoire identifiée — écartée du radar.",
  faux_positif_probable: "Signal positif au départ, mais potentiel limité — non prioritaire.",
};
const LAYER_SHORT = {
  // Décision 2 : le SAR servi est un PROXY de vocation → badge explicite, jamais « SAR » nu.
  sar: "SAR (proxy indicatif)", risques: "Risques (PPR)", abf: "ABF / Monuments", ens: "ENS", safer: "SAFER",
  foret_publique: "Forêt publique", trait_de_cote: "Trait de côte", parc_national: "Parc national",
  zonage_plu_gpu: "PLU", eau: "Hydrographie", pente: "Pente", ocs_ge: "Occupation du sol",
  osm_faux_positif: "Bâti (OSM)", sitadel: "SITADEL", proprietaire: "Propriétaire",
  fichiers_fonciers: "Fichiers fonciers", dvf: "Marché (DVF)", surface: "Surface",
  potentiel_foncier_region: "Potentiel foncier", acces: "Accès voirie",
};
const shortLayer = (c) => LAYER_SHORT[c.layer_name] || c.layer_name;

let FEATURES = [];          // toutes les parcelles (GeoJSON features)
let DATA_READY = false;     // M1 — vrai une fois le geojson chargé (évite le faux « vide » au boot)
let layer = null;           // couche Leaflet courante
const byIdu = {};           // idu -> layer (pour highlight)
let map;
let PERMITS_LAYER = null;   // couche marqueurs SITADEL (Lot C4)
let WATCH_LAYER = null, WATCH_ZONES = [];   // 3.C — zones de veille (dessinées sur la carte)
let ASSISTANT_OK = false;                   // 3.A — l'assistant IA est-il configuré (clé API) ?
let COMPARE = [];           // IDU sélectionnés pour le comparateur (Lot D2), max 3
let COVERAGE = null;        // couverture des couches critiques (/coverage)
let KANBAN_META = null;     // colonnes & priorités du pipeline (/pipeline/meta)
let PIPELINE = [];          // entrées du pipeline chargées (mémoire → re-render local)
let KB_SORT = "score";      // tri courant des cartes dans chaque colonne
let KB_REMINDER_ONLY = false; // filtre « à rappeler »
let DRAG_ID = null;         // id de la carte en cours de glisser-déposer

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString("fr-FR"));

// ───────────────────────── Carte ─────────────────────────
// Leaflet est vendorisé (audit R2) ; par défense en profondeur, son échec éventuel ne doit
// JAMAIS tuer l'app : la carte se met en erreur lisible, KPIs/liste/fiches restent utilisables.
function initMap() {
  try {
    if (typeof L === "undefined") throw new Error("Leaflet indisponible");
    map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([-21.01, 55.285], 13);
    const plan = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      subdomains: "abcd", maxZoom: 20,
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    }).addTo(map);
    // Fonds IGN (Géoplateforme, WMTS/PM). Helper DRY : une couche par millésime.
    const ignWmts = (layer, { fmt = "image/jpeg", maxNativeZoom = 19, attr = "IGN — Géoplateforme" } = {}) =>
      L.tileLayer(
        "https://data.geopf.fr/wmts?layer=" + layer + "&style=normal&tilematrixset=PM" +
        "&Service=WMTS&Request=GetTile&Version=1.0.0&Format=" + encodeURIComponent(fmt) +
        "&TileMatrix={z}&TileCol={x}&TileRow={y}",
        { maxZoom: 21, maxNativeZoom, attribution: "&copy; " + attr });
    // « Vue du ciel » : orthophotographie IGN ACTUELLE (BD ORTHO).
    const ortho = ignWmts("ORTHOIMAGERY.ORTHOPHOTOS", { attr: "IGN — Géoplateforme (BD ORTHO)" });
    // 3.B — millésimes HISTORIQUES couvrant Saint-Paul (EduGéo La Réunion, vérifiés z≤16,
    // cf. RAPPORT_DISPO_3B.md) → « remonter le temps » directement sur le radar.
    const histOpts = { fmt: "image/png", maxNativeZoom: 16, attr: "IGN — EduGéo (ortho historique La Réunion)" };
    const h2010 = ignWmts("ORTHOIMAGERY.EDUGEO.LA-REUNION2010", histOpts);
    const h1989 = ignWmts("ORTHOIMAGERY.EDUGEO.LA-REUNION1989", histOpts);
    const h1980 = ignWmts("ORTHOIMAGERY.EDUGEO.LA-REUNION1980", histOpts);
    const h1961 = ignWmts("ORTHOIMAGERY.EDUGEO.LA-REUNION1961", histOpts);
    PERMITS_LAYER = L.layerGroup();   // marqueurs SITADEL (Lot C4), peuplés en différé
    WATCH_LAYER = L.layerGroup().addTo(map);   // 3.C — zones de veille (visibles par défaut)
    L.control.layers(
      { "Plan (radar)": plan, "Vue du ciel (IGN)": ortho,
        "Ciel · 2010": h2010, "Ciel · 1989": h1989, "Ciel · 1980": h1980, "Ciel · 1961": h1961 },
      { "Permis (SITADEL)": PERMITS_LAYER, "Zones de veille": WATCH_LAYER },
      { position: "topright", collapsed: true }
    ).addTo(map);
  } catch (e) {
    map = null;
    showMapError();
  }
}

function colorFor(p) { return COLORS[p.status] || COLORS.inconnu; }

function styleFor(p) {
  const c = colorFor(p);
  // Le radar fait CLIGNOTER la cible : l'opportunité ressort fort, le reste s'efface.
  switch (p.status) {
    case "opportunite":            return { color: "#86EFCC", weight: 2.2, fillColor: "#2DBE87", fillOpacity: 0.86, opacity: 1 };
    case "faux_positif_probable":  return { color: c, weight: 0.6, fillColor: c, fillOpacity: 0.3, opacity: 0.6 };
    case "a_creuser":              return { color: c, weight: 0.4, fillColor: c, fillOpacity: 0.18, opacity: 0.42 };
    case "exclue":                 return { color: c, weight: 0.4, fillColor: c, fillOpacity: 0.14, opacity: 0.34 };
    default:                       return { color: c, weight: 0.4, fillColor: c, fillOpacity: 0.16, opacity: 0.4 };
  }
}

function tipHtml(p) {
  const lbl = STATUS_LABEL[p.status] || "non évaluée";
  const sc = p.opportunity_score != null
    ? `<span class="t-sc"><b>${p.opportunity_score}</b> opp · ${p.completeness_score ?? "—"} cpl</span>` : "";
  const dg = p.downgrade_reason ? `<span class="t-dg">⚠ déclassée : ${esc(p.downgrade_reason)}</span>` : "";
  return `<span class="t-idu">${esc(p.idu)}</span><span class="t-st st-${p.status || "inconnu"}">${lbl}</span>${sc}${dg}`;
}

function passesFilter(p) {
  const f = currentFilter();
  if (!f.statuses.has(p.status || "inconnu") && !(p.status == null && f.statuses.has("inconnu"))) {
    if (!f.statuses.has(p.status)) return false;
  }
  if ((p.opportunity_score || 0) < f.minOpp) return false;
  if ((p.completeness_score || 0) < f.minCpl) return false;
  if ((p.surface_m2 || 0) < f.minSurf) return false;
  // Sous-densité (Lot B) : taux d'utilisation de l'emprise constructible sous le seuil.
  if (f.sousDensite && !(p.taux_emprise_pct != null && p.taux_emprise_pct < f.maxTaux)) return false;
  // Type de propriétaire (Lot C3).
  if (f.owner) {
    const fam = p.owner_famille || "inconnu";
    if (f.owner === "identifie" ? fam === "inconnu" : fam !== f.owner) return false;
  }
  return true;
}

function currentFilter() {
  const statuses = new Set([...document.querySelectorAll("#filter-statuses input:checked")].map((i) => i.value));
  return {
    statuses,
    minOpp: +$("#f-opp").value,
    minCpl: +$("#f-cpl").value,
    minSurf: +$("#f-surf").value,
    sousDensite: !!($("#f-sousdense") && $("#f-sousdense").checked),
    maxTaux: +(($("#f-taux") && $("#f-taux").value) || 40),
    owner: ($("#f-owner") && $("#f-owner").value) || "",
  };
}

function renderMap() {
  const shown = FEATURES.filter((ft) => passesFilter(ft.properties));
  if (!map) { updateResultMeta(shown.length); return; }   // carte en panne : liste/fiches vivent
  if (layer) layer.remove();
  const fc = { type: "FeatureCollection", features: shown };
  layer = L.geoJSON(fc, {
    style: (ft) => styleFor(ft.properties),
    onEachFeature: (ft, lyr) => {
      byIdu[ft.properties.idu] = lyr;
      lyr.on("click", () => openSheet(ft.properties.idu));
      lyr.bindTooltip(tipHtml(ft.properties), { sticky: true, direction: "top", className: "lb-tip" });
    },
  }).addTo(map);
  updateEmptyState(shown.length);
  updateResultMeta(shown.length);
}

// M1 — état initial sûr : on ne crie « aucune parcelle » qu'une fois les DONNÉES chargées, et on
// distingue « filtres trop stricts » de « radar encore en préparation ». Jamais d'écran « cassé ».
function updateEmptyState(shown) {
  const empty = $("#map-empty"); if (!empty) return;
  if (!DATA_READY || shown > 0) { empty.classList.add("hidden"); return; }
  const card = empty.querySelector(".me-card");
  if (FEATURES.length === 0) {
    card.innerHTML = `<div class="me-title">Radar en préparation</div>
      <div class="me-sub">Les parcelles de la commune se chargent, ou la base finalise sa préparation. Réessayez dans un instant.</div>
      <button class="me-reset js-reload" type="button">↻ Recharger</button>`;
  } else {
    card.innerHTML = `<div class="me-title">Aucune parcelle ne correspond</div>
      <div class="me-sub">Vos filtres masquent les ${fmt(FEATURES.length)} parcelles de la commune.</div>
      <div class="me-actions"><button class="me-reset js-reset" type="button">↺ Réinitialiser les filtres</button>
        <button class="me-all js-showall" type="button">Afficher toutes les parcelles</button></div>`;
  }
  empty.classList.remove("hidden");
}
function hideLoader() {
  const l = $("#app-loader"); if (!l) return;
  l.classList.add("gone");
  setTimeout(() => l.remove(), 450);   // laisse la transition d'opacité se jouer
}
function showAllParcels() {
  document.querySelectorAll("#filter-statuses input").forEach((b) => { b.checked = true; });
  ["opp", "cpl", "surf"].forEach((k) => { const el = $("#f-" + k); if (el) el.value = 0; const o = $("#" + k + "-out"); if (o) o.textContent = "0"; });
  clearKpiActive();
  applyFilters();
}

// Compteur de résultats + bouton « Réinitialiser » (visible si filtre non par défaut).
function isDefaultFilter() {
  const st = new Set([...document.querySelectorAll("#filter-statuses input:checked")].map((i) => i.value));
  const defStatus = st.size === 2 && st.has("opportunite") && st.has("a_creuser");
  return defStatus && +$("#f-opp").value === 0 && +$("#f-cpl").value === 0 && +$("#f-surf").value === 0;
}
function updateResultMeta(n) {
  const c = $("#rm-count"); if (c) c.textContent = `${fmt(n)} visible${n > 1 ? "s" : ""}`;
  const v = $("#visible-count"); if (v) v.textContent = `${fmt(n)} parcelle${n > 1 ? "s" : ""} visible${n > 1 ? "s" : ""}`;
  document.querySelectorAll(".rm-reset").forEach((b) => b.classList.toggle("hidden", isDefaultFilter()));
}
// Compteurs des raccourcis « actions rapides » (pipeline suivi / cas de démo).
function updateQuickCounts() {
  const p = $("#qa-pipeline-n"); if (p) p.textContent = PIPELINE.length ? `${PIPELINE.length} suivi${PIPELINE.length > 1 ? "s" : ""}` : "—";
}
async function updateDemoCount() {
  const el = $("#qa-demo-n"); if (!el) return;
  try { const d = await (await fetch("/demo")).json(); const n = (d.parcels || []).length; el.textContent = n ? `${n} cas` : "—"; }
  catch { el.textContent = "—"; }
}
function resetFilters() {
  document.querySelectorAll("#filter-statuses input").forEach((b) => { b.checked = (b.value === "opportunite" || b.value === "a_creuser"); });
  ["opp", "cpl", "surf"].forEach((k) => { $("#f-" + k).value = 0; const o = $("#" + k + "-out"); if (o) o.textContent = "0"; });
  clearKpiActive();
  applyFilters();
}
function setSliderBounds() {
  const props = FEATURES.map((f) => f.properties);
  const maxOf = (sel, floor, step) => Math.max(floor, Math.ceil(Math.max(0, ...props.map(sel)) / step) * step);
  $("#f-opp").max = maxOf((p) => p.opportunity_score || 0, 10, 5);
  $("#f-cpl").max = maxOf((p) => p.completeness_score || 0, 10, 5);
  $("#f-surf").max = maxOf((p) => p.surface_m2 || 0, 1000, 500);
}

// ───────────────────────── Dashboard / liste ─────────────────────────
async function loadStats() {
  let s = {};
  try { s = await (await fetch(`/stats?commune=${encodeURIComponent(COMMUNE)}`)).json(); } catch { s = {}; }
  $("#kpi-total").textContent = fmt(s.total);
  $("#kpi-opp").textContent = fmt(s.opportunite);
  $("#kpi-creuser").textContent = fmt(s.a_creuser);
  $("#kpi-exclue").textContent = fmt(s.exclue);
}

// Filet de sécurité (audit QA) : si /stats est indisponible, les KPIs ne restent JAMAIS bloqués
// sur « — » pendant que la carte affiche des parcelles. On les reconstruit depuis les parcelles
// déjà chargées (même périmètre commune → cohérent avec la carte). /stats reste autoritatif :
// on ne reconstruit que les compteurs encore vides.
function reconcileKpisFromFeatures() {
  if ($("#kpi-total") && $("#kpi-total").textContent !== "—") return;   // /stats a répondu
  const c = { total: FEATURES.length, opportunite: 0, a_creuser: 0, exclue: 0 };
  for (const ft of FEATURES) { const st = ft.properties.status; if (st in c && st !== "total") c[st]++; }
  $("#kpi-total").textContent = fmt(c.total);
  $("#kpi-opp").textContent = fmt(c.opportunite);
  $("#kpi-creuser").textContent = fmt(c.a_creuser);
  $("#kpi-exclue").textContent = fmt(c.exclue);
}

// 3.C — Veille = zones surveillées + parcelles suivies → liste de « nouveautés ».
async function loadVeille() { await Promise.all([loadWatchZones(), loadAlertes()]); }

async function loadWatchZones() {
  try { WATCH_ZONES = await (await fetch(`/watch-zones?commune=${encodeURIComponent(COMMUNE)}`)).json(); }
  catch { WATCH_ZONES = []; }
  if (WATCH_LAYER) {
    WATCH_LAYER.clearLayers();
    WATCH_ZONES.forEach((z) => {
      if (!z.geojson) return;
      L.geoJSON(z.geojson, { style: { color: "#D6B36A", weight: 1.5, dashArray: "5", fillOpacity: 0.05 } })
        .bindTooltip(`Veille : ${z.name}`, { sticky: true }).addTo(WATCH_LAYER);
    });
  }
  const box = $("#watch-zones");
  if (!box) return;
  box.innerHTML = WATCH_ZONES.length
    ? WATCH_ZONES.map((z) => `<span class="wz-chip" title="${z.area_m2 ? z.area_m2.toLocaleString("fr-FR") + " m²" : ""}"><svg class="ic wz-ic" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 9a4 4 0 0 1 8 0c0 3 1 4 1 4H5s1-1 1-4z"/><path d="M8.5 16a1.6 1.6 0 0 0 3 0"/></svg>${esc(z.name)}<button class="wz-del" data-id="${z.id}" title="Retirer cette zone de veille" aria-label="Retirer">×</button></span>`).join("")
    : `<span class="muted-sm">Aucune zone de veille — « + Zone » pour en dessiner une.</span>`;
}

async function loadAlertes() {
  let items = [];
  try { items = await (await fetch(`/alertes?commune=${encodeURIComponent(COMMUNE)}&limit=12`)).json(); } catch { items = []; }
  const nNew = items.filter((a) => !a.acknowledged).length;
  $("#veille-count").textContent = fmt(nNew);
  const list = $("#veille-list");
  if (!list) return;
  if (!items.length) {
    list.innerHTML = `<div class="muted-sm">Aucune nouveauté. Surveillez une zone (« + Zone ») ou suivez des parcelles dans le pipeline.</div>`;
    return;
  }
  const TYPE = { dvf_in_zone: "Vente DVF", permit_near_followed: "Permis à proximité" };
  list.innerHTML = items.map((a) => {
    const p = a.payload || {};
    const dt = p.date ? " · " + esc(String(p.date).slice(0, 10)) : "";
    const sub = a.kind === "dvf_in_zone"
      ? `${esc(a.zone_name || "")}${p.valeur_fonciere ? " · " + Number(p.valeur_fonciere).toLocaleString("fr-FR") + " €" : ""}${dt}`
      : `${esc(a.parcel_idu || "")}${p.within_m != null ? " · à " + p.within_m + " m" : ""}${dt}`;
    const target = a.kind === "permit_near_followed" ? (a.parcel_idu || "") : "";
    return `<div class="alert${a.acknowledged ? " ack" : ""}"${target ? ` data-idu="${esc(target)}"` : ""}>
      <span class="a-type">${TYPE[a.kind] || esc(a.kind)}</span> <span class="a-idu">${sub}</span>
      ${a.acknowledged ? "" : `<button class="al-ack" data-id="${a.id}" title="Marquer comme lu">✓</button>`}</div>`;
  }).join("");
}

// Dessiner une zone de veille (réutilise l'outil de tracé), puis POST.
function startWatchZone() {
  const name = (prompt("Nom de la zone à surveiller ?", "Ma zone de veille") || "").trim();
  if (!name) { auditMsg("Création de zone annulée."); return; }
  startDraw("zone", name);
}
async function createWatchZone(name, geometry) {
  auditMsg("Création de la zone de veille…", true);
  let res;
  try {
    res = await (await fetch("/watch-zones", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, geometry, commune: COMMUNE }) })).json();
  } catch { auditMsg("Création impossible — réessayez."); return; }
  const d = (res && res.detected) || {};
  auditMsg(`Zone « ${name} » créée${d.total ? ` · ${d.total} nouveauté(s) détectée(s)` : ""}.`);
  setTimeout(() => auditMsg(""), 4500);
  await loadVeille();
}
async function refreshAlertes() {
  auditMsg("Détection des nouveautés…", true);
  try { await fetch(`/alertes/refresh?commune=${encodeURIComponent(COMMUNE)}`, { method: "POST" }); } catch { /* silencieux */ }
  auditMsg(""); await loadVeille();
}
async function ackAlerte(id) {
  try { await fetch("/alertes/ack", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id, commune: COMMUNE }) }); } catch { /* silencieux */ }
  await loadAlertes();
}
async function deleteWatchZone(id) {
  try { await fetch(`/watch-zones/${id}`, { method: "DELETE" }); } catch { /* silencieux */ }
  await loadVeille();
}

async function loadCoverage() {
  try { COVERAGE = await (await fetch("/coverage")).json(); } catch { COVERAGE = null; }
  renderBanner();
}

function renderBanner() {
  const b = $("#banner");
  if (!COVERAGE || COVERAGE.complete) { b.classList.add("hidden"); return; }
  b.classList.remove("hidden");
  b.innerHTML = `<span class="warn-ico">◆</span>
    <span class="banner-text"><b>Transparence méthodologique</b> — verdicts établis sur les couches publiques disponibles.
    Restent à vérifier : <span class="missing">${COVERAGE.missing.map(esc).join(" · ")}</span></span>
    <span class="banner-pill">Verdicts partiels</span>
    <button class="banner-collapse" type="button" aria-label="Réduire le bandeau" title="Réduire">Réduire ✕</button>`;
}

function ficheWarn() {
  if (!COVERAGE || COVERAGE.complete) return "";
  return `<div class="sheet-warn"><b>⚠ Verdicts partiels.</b> Couches non encore intégrées : ${COVERAGE.missing.map(esc).join(" · ")}.</div>`;
}

function fiableBadge(status) {
  if (status !== "opportunite") return "";
  // « Vérifiée » (pas « fiable ») : couches critiques contrôlées, MAIS le SAR n'est que
  // partiel et rien ne garantit la constructibilité (PLU/PPR à croiser, terrain à vérifier).
  if (COVERAGE && COVERAGE.reliable_ready) {
    // Audit B2 : sous-texte raccourci (l'intégral reste dans l'infobulle).
    return `<span class="fiable-tag ok" title="Contrôlée sur les couches disponibles : PLU, PPR, littoral, forêt, SAR partiel, bâti BD TOPO. Ne vaut pas garantie de constructibilité.">Opportunité vérifiée</span>`
      + `<span class="fiable-sub">sur les couches disponibles — ne vaut pas garantie de constructibilité</span>`;
  }
  return `<span class="fiable-tag reserve" title="Des couches critiques ne sont pas encore ingérées.">sous réserve · couches manquantes</span>`;
}

// Tri liste : OPPORTUNITÉS d'abord (audit J9 — le score seul noyait les vraies pistes
// sous les « à creuser » surface réduite), puis score, puis surface.
const STATUS_RANK = { opportunite: 0, a_creuser: 1, faux_positif_probable: 2, exclue: 3 };
let LIST_LIMIT = 80;   // « Afficher plus » (audit J2 — 97 % des résultats étaient invisibles)

// Signal / action dérivés des PROPRIÉTÉS RÉELLES (aucune donnée inventée) — lecture promoteur.
function _ocSignal(p) {
  if (p.downgrade_reason) return esc(p.downgrade_reason);
  if (p.sous_densite) return "Sous-densité — potentiel de densification";
  if (p.taux_emprise_pct != null && p.taux_emprise_pct < 50) return "Emprise peu utilisée";
  if (p.owner_famille === "public") return "Propriétaire public identifiable";
  if (p.owner_famille === "prive") return "Personne morale identifiable";
  if (p.status === "opportunite") return "Signal d'opportunité";
  if (p.status === "a_creuser") return "Potentiel à instruire";
  return "À qualifier";
}
function _ocAction(p) {
  if (p.status === "opportunite") return "Vérifier le propriétaire";
  if (p.status === "a_creuser") return "Instruire les contraintes";
  if (p.status === "faux_positif_probable") return "Écartée — re-vérifier si besoin";
  if (p.status === "exclue") return "Hors périmètre d'instruction";
  return "À qualifier";
}
const CHEVRON = `<svg class="ic oc-chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg>`;

function renderList() {
  // La liste REFLÈTE les filtres : faux positifs/exclues y apparaissent si leur case est
  // cochée (audit B5 — « montrez-moi ce que vous écartez » est un argument de vente).
  const matched = FEATURES
    .map((ft) => ft.properties)
    .filter((p) => passesFilter(p))
    .sort((a, b) => (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9)
      || (b.opportunity_score || 0) - (a.opportunity_score || 0)
      || (b.surface_m2 || 0) - (a.surface_m2 || 0));
  const rows = matched.slice(0, LIST_LIMIT);
  $("#list-count").textContent = `${fmt(matched.length)} résultat${matched.length > 1 ? "s" : ""}`;
  const more = matched.length > rows.length
    ? `<button class="list-more" type="button">Afficher 80 de plus (${fmt(matched.length - rows.length)} restantes)</button>` : "";
  $("#parcel-list").innerHTML = rows.map((p) => {
    const st = p.status || "inconnu";
    const sel = p.idu === CURRENT_IDU ? " selected" : "";
    return `
    <article class="oc st-${st}${sel}" data-idu="${esc(p.idu)}" role="button" tabindex="0">
      <div class="oc-l">
        <div class="oc-top">
          <span class="oc-idu">${esc(p.idu)}</span>
          <span class="chip ${st}">${STATUS_LABEL[st] || "?"}</span>
        </div>
        <div class="oc-metrics"><b>Score ${p.opportunity_score ?? "—"}</b> · Données ${p.completeness_score ?? "—"} % · ${fmt(p.surface_m2)} m²</div>
        <div class="oc-signal"><span class="oc-k">Signal</span> ${_ocSignal(p)}</div>
        <div class="oc-action"><span class="oc-k">Action</span> ${_ocAction(p)}</div>
      </div>
      ${CHEVRON}
    </article>`;
  }).join("") + more || `<div class="loading">Aucune parcelle ne correspond.</div>`;
  const open = (idu) => { focusParcel(idu); document.querySelectorAll("#parcel-list .oc").forEach((c) => c.classList.toggle("selected", c.dataset.idu === idu)); };
  document.querySelectorAll("#parcel-list .oc").forEach((el) => {
    el.addEventListener("click", () => open(el.dataset.idu));
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(el.dataset.idu); } });
  });
  const mb = document.querySelector(".list-more");
  if (mb) mb.addEventListener("click", () => { LIST_LIMIT += 80; renderList(); });
}

// Navigation : radar (Carte ⇄ Liste, mobile) ⇄ vues plein écran (Shortlist, Kanban).
function setView(view) {
  const kanban = view === "kanban";
  const shortlist = view === "shortlist";
  document.body.classList.toggle("view-kanban", kanban);
  document.body.classList.toggle("view-shortlist", shortlist);
  if (!kanban && !shortlist) {
    document.body.classList.toggle("view-map", view === "map");
    document.body.classList.toggle("view-list", view === "list");
    if (view === "map" && map) setTimeout(() => map.invalidateSize(), 60);
  }
  document.querySelectorAll(".js-view").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.view === view)));
  if (kanban) loadKanban();
  if (shortlist) loadShortlist();
}
const isMobile = () => window.matchMedia("(max-width: 900px)").matches;

function focusParcel(idu) {
  if (isMobile()) setView("map");                 // sur mobile, montrer la carte avant de cadrer
  const lyr = byIdu[idu];
  const focus = () => {
    if (lyr && getComputedStyle($("#map")).display !== "none") {
      try { map.invalidateSize(); map.fitBounds(lyr.getBounds(), { maxZoom: 18 }); lyr.openTooltip(); } catch (e) { /* carte masquée */ }
    }
  };
  isMobile() ? setTimeout(focus, 90) : focus();
  openSheet(idu);
}

function applyFilters() { LIST_LIMIT = 80; renderMap(); renderList(); }

// KPI cliquable → filtre carte + liste par statut (P2). "all" = tout afficher.
function clearKpiActive() {
  document.querySelectorAll(".kpi").forEach((k) => k.classList.remove("active"));
  document.querySelectorAll(".qf").forEach((q) => q.classList.remove("active"));
}
function filterByStatus(status) {
  document.querySelectorAll("#filter-statuses input").forEach((b) => { b.checked = (status === "all") || (b.value === status); });
  document.querySelectorAll(".kpi").forEach((k) => k.classList.toggle("active", k.dataset.status === status));
  document.querySelectorAll(".qf").forEach((q) => q.classList.toggle("active", q.dataset.status === status));
  applyFilters();
}

// ───────────────────────── Fiche premium §8 ─────────────────────────
let CURRENT_IDU = null;   // fiche ouverte (pour le recalcul bilan après calibration, 1.C)
async function openSheet(idu) {
  CURRENT_IDU = idu;
  $("#sheet").classList.remove("hidden");
  $("#sheet").removeAttribute("inert");               // a11y : la fiche ouverte (re)devient focusable
  $("#sheet").setAttribute("aria-hidden", "false");   // a11y : le panneau ouvert n'est plus masqué aux lecteurs d'écran
  $("#scrim").classList.remove("hidden");
  $("#sheet-body").innerHTML = `<div class="loading">Chargement de la fiche…</div>`;
  let f;
  try { f = await (await fetch(`/parcels/${encodeURIComponent(idu)}`)).json(); }
  catch { $("#sheet-body").innerHTML = `<div class="loading">Parcelle introuvable.</div>`; return; }
  $("#sheet-body").innerHTML = renderFiche(f);
  wireSheetActions(idu);
  loadEnrichment(idu, f.parcel && f.parcel.centroid);   // bloc « promoteur » en arrière-plan (lazy)
}

// Jauge circulaire du score (signature) : anneau coloré par le verdict (CSS) + remplissage
// proportionnel au score réel (stroke-dashoffset). Score absent → anneau vide, « — » au centre.
const GAUGE_C = 326.726;   // circonférence = 2·π·52
function renderGauge(score) {
  const has = score != null && !Number.isNaN(Number(score));
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  const off = (has ? GAUGE_C * (1 - s / 100) : GAUGE_C).toFixed(1);
  return `<div class="gauge">
    <svg viewBox="0 0 116 116" aria-hidden="true">
      <circle class="g-track" cx="58" cy="58" r="52"/>
      <circle class="g-arc" cx="58" cy="58" r="52" style="stroke-dashoffset:${off}"/>
    </svg>
    <div class="g-center"><span class="g-num">${has ? s : "—"}</span><span class="g-max">/ 100</span></div>
  </div>`;
}

// ─────────────────────── NOTE PROMOTEUR (synthèse décisionnelle, en tête de fiche) ───────────────────────
// Répond en <10 s aux 5 questions du promoteur : ça vaut le coup ? quoi construire ? combien ?
// quel blocage ? quelle action ? — dérivée des données DÉJÀ calculées (zéro nouvelle logique métier).
const _eurK = (n) => (n == null ? "—"
  : Math.abs(n) >= 1e6 ? (n / 1e6).toFixed(Math.abs(n) >= 1e7 ? 0 : 1).replace(".", ",") + " M€"
  : Math.round(n / 1000) + " k€");

function _logtsLabel(fr) {
  const sol = fr.logements_au_sol, sous = fr.logements_sous_sol;
  const rng = (a) => (a && a.length === 2) ? (a[0] === a[1] ? `${a[0]}` : `${a[0]}–${a[1]}`) : null;
  const s = rng(sol) || rng(sous);
  return s ? `${s} logement${s === "1" || s === "0–1" ? "" : "s"}` : "";
}
function _blocagePrincipal(f) {
  const cascade = f.cascade || [];
  const hard = cascade.find((c) => c.result === "HARD_EXCLUDE");
  if (hard) return esc(hard.detail);
  const r = f.resume || {};
  if (r.vigilance && r.vigilance.length) return esc(r.vigilance[0]);
  const soft = cascade.find((c) => c.result === "SOFT_FLAG");
  if (soft) return esc(soft.detail);
  const surf = (f.parcel || {}).surface_m2;
  if (surf && surf < 300) return `Surface réduite (${fmt(Math.round(surf))} m²)`;
  return "Aucun blocage majeur identifié";
}
function _confiance(cpl) {
  if (cpl == null) return "—";
  return cpl >= 75 ? "Élevé" : cpl >= 50 ? "Moyen" : "Faible";
}

// Module 3 — Assemblage « star » : bloc DÉCISION (parcelle seule vs groupée) dans la note,
// pas seulement dans l'audit. Données réelles (voisinage adjacent) ; tout reste « à vérifier ».
function _potentielSeul(f) {
  const fa = f.faisabilite || {};
  if (!fa.constructible) return "Non constructible seule";
  const s = (f.parcel || {}).surface_m2 || 0;
  if (s < 500) return "Potentiel limité seule";
  if (s < 1500) return "Potentiel correct seule";
  return "Potentiel solide seule";
}
function renderAssembBloc(f) {
  const vz = f.voisinage || {}, a = vz.assemblage || {}, unlock = vz.assemblage_unlock || {};
  const voisines = vz.voisines || [];
  const possible = !!(a.possible || unlock.possible);
  const surfSeule = Math.round((f.parcel || {}).surface_m2 || 0);
  const surfCum = a.surface_cumulee_m2 || null;
  const n = a.n_interessantes || voisines.length;
  const memeProprio = !!unlock.priorite_meme_proprietaire;
  const gain = (possible && surfCum && surfSeule)
    ? `+${fmt(Math.max(0, surfCum - surfSeule))} m² (×${(surfCum / surfSeule).toFixed(1).replace(".", ",")})` : "—";
  const proprios = !possible ? "—" : memeProprio ? "Même propriétaire probable (à confirmer)" : "Multiples / à identifier";
  const complexite = !possible ? "—"
    : memeProprio ? "Faible — même propriétaire probable"
    : n <= 2 ? "Modérée — 2 propriétaires à aligner" : "Élevée — propriétaires multiples";
  const action = !possible ? "Traiter la parcelle seule — pas de contiguë exploitable détectée."
    : memeProprio ? "Vérifier le périmètre et approcher le propriétaire pour l'ensemble."
    : "Vérifier la faisabilité d'assemblage et identifier les propriétaires contigus.";
  return `
  <div class="asm-bloc${possible ? " asm-on" : ""}">
    <div class="asm-h">🧩 Parcelle seule <span>vs</span> assemblage</div>
    <div class="asm-cols">
      <div class="asm-col">
        <div class="asm-col-k">Parcelle seule</div>
        <div class="asm-col-v">${esc(_potentielSeul(f))}</div>
        <div class="asm-col-s">${surfSeule ? fmt(surfSeule) + " m²" : "—"}</div>
      </div>
      <div class="asm-arrow" aria-hidden="true">→</div>
      <div class="asm-col asm-col-grp">
        <div class="asm-col-k">En assemblage</div>
        <div class="asm-col-v">${possible ? "Assemblage possible — à vérifier" : "Aucune contiguë exploitable"}</div>
        <div class="asm-col-s">${possible ? `${n} contiguë${n > 1 ? "s" : ""} · ~${fmt(surfCum || 0)} m² cumulés` : "—"}</div>
      </div>
    </div>
    <dl class="asm-grid">
      <dt>Gain de surface</dt><dd>${gain}</dd>
      <dt>Propriétaires</dt><dd>${esc(proprios)}</dd>
      <dt>Complexité</dt><dd>${esc(complexite)}</dd>
    </dl>
    <div class="asm-action">▶ ${esc(action)}</div>
    <p class="asm-foot">Adjacence géométrique — faisabilité, accord et propriété restent à vérifier.</p>
  </div>`;
}

function renderNotePromoteur(f) {
  const v = f.verdict || {}, fa = f.faisabilite || {}, fr = fa.fourchette || {}, bil = fa.bilan || {};
  const r = f.resume || {};
  const status = v.status || "inconnu";
  const decision = r.prochaine_action ? esc(r.prochaine_action)
    : (status === "exclue" ? "Écarter — contrainte rédhibitoire, hors périmètre d'instruction."
      : "Sécuriser le foncier : qualifier le terrain et identifier le propriétaire.");

  const mc = (label, value, sub, tone) => `<div class="mc${tone ? " mc-" + tone : ""}">
    <div class="mc-k">${label}</div><div class="mc-v">${value}</div>${sub ? `<div class="mc-s">${sub}</div>` : ""}</div>`;
  const cards = [];
  cards.push(mc("Potentiel opération", fa.constructible ? esc(fr.niveaux || "—") : "Non constructible",
    fa.constructible ? _logtsLabel(fr) : esc(fa.zone || "")));
  if (fr.surface_plancher_m2) cards.push(mc("Surface plancher", `~${fmt(fr.surface_plancher_m2)}<i> m²</i>`, "estimée"));
  if (bil.ca) cards.push(mc("CA potentiel", `${_eurK(bil.ca.bas)} – ${_eurK(bil.ca.haut)}`, bil.fiabilite ? `prix ${esc(bil.fiabilite)}` : ""));
  if (bil.charge_fonciere) cards.push(mc("Charge foncière cible", _eurK(bil.charge_fonciere.central),
    bil.charge_fonciere.par_m2_terrain ? `~${bil.charge_fonciere.par_m2_terrain} €/m² terrain` : ""));
  cards.push(mc("Blocage principal", _blocagePrincipal(f), "", "warn"));
  cards.push(mc("Confiance", _confiance(v.completeness_score),
    v.completeness_score != null ? `complétude ${v.completeness_score} %` : ""));

  // Module 3 — l'assemblage est une décision : bloc dédié pour les verdicts actionnables.
  const asmBloc = (status === "opportunite" || status === "a_creuser") ? renderAssembBloc(f) : "";
  return `
    <section class="note-pro v-${status}">
      <div class="np-decision"><span class="np-decision-k">Décision promoteur</span>${decision}</div>
      <div class="np-cards">${cards.join("")}</div>
      ${asmBloc}
    </section>`;
}

function renderFiche(f) {
  const v = f.verdict || {};
  const p = f.parcel || {};
  const cascade = f.cascade || [];
  const status = v.status || "inconnu";
  const w = (n) => Math.max(0, Math.min(100, Number(n) || 0));

  const favors = cascade.filter((c) => c.result === "POSITIVE");
  const limits = cascade.filter((c) => c.result === "HARD_EXCLUDE" || c.result === "SOFT_FLAG");
  const unknown = cascade.filter((c) => c.result === "UNKNOWN");
  const hasHard = limits.some((c) => c.result === "HARD_EXCLUDE");  // rouge si blocage dur, sinon ambre

  const pts = (c) => (c.weight_applied ? `<span class="rd-pts ${c.weight_applied > 0 ? "pos" : "neg"}">${c.weight_applied > 0 ? "+" : "−"}${Math.abs(Math.round(c.weight_applied))}</span>` : "");
  const liRow = (c, cls) => `<li class="rd-li ${cls}">
      <span class="rd-detail">${esc(c.detail)}${pts(c)}</span>
      <span class="rd-src">${esc(shortLayer(c))}${c.source ? " · " + esc(c.source) : ""}</span></li>`;
  const block = (arr, cls, emptyMsg) => arr.length
    ? `<ul class="rd-list">${arr.map((c) => liRow(c, cls === "lim" ? (c.result === "HARD_EXCLUDE" ? "hard" : "soft") : cls)).join("")}</ul>`
    : `<p class="rd-empty">${emptyMsg}</p>`;

  const chips = (arr, cls) => (arr || []).map((s) => `<span class="src-chip ${cls}">${esc(s)}</span>`).join("");
  const loc = [p.commune, p.section ? "section " + esc(p.section) : "",
    p.surface_m2 ? fmt(Math.round(p.surface_m2)) + " m²" : ""].filter(Boolean).join(" · ");

  // Audit J7 : NOMMER les couches non vérifiées inline (au lieu d'un « verdict partiel »
  // anxiogène qui obligeait à descendre en bas de fiche pour savoir de quoi on parle).
  const nU = unknown.length;
  const uvNames = unknown.slice(0, 3).map(shortLayer).map(esc).join(", ")
    + (nU > 3 ? ` +${nU - 3}` : "");
  const unverifiedLine = nU ? `
    <section class="unverified">
      <span class="uv-mark">◔</span>
      <span><b>Non vérifié à ce jour :</b> ${uvNames} — le verdict porte sur les couches disponibles (détail en bas de fiche).</span>
    </section>` : "";

  const today = new Date().toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });

  const cascadeRows = cascade.map((c) => `
    <tr>
      <td><span class="ct-tag v-${c.result}">${esc(c.result)}</span></td>
      <td><span class="ct-detail">${esc(c.detail)}</span>
          <span class="ct-src">${esc(c.layer_name)}${c.source ? " · " + esc(c.source) : ""}</span></td>
    </tr>`).join("");

  return `
    <header class="print-head print-only">
      <div class="ph-brand">
        <svg class="ph-bird" viewBox="0 0 112 44" aria-hidden="true"><path d="M56 11 C58 13 59 15 61 17 C74 12 92 10 109 14 C93 17 75 20 62 25 C60 28 59 30 58 32 L56 35 L54 32 C53 30 52 28 50 25 C37 20 19 17 3 14 C20 10 38 12 51 17 C53 15 54 13 56 11 Z"/></svg>
        <div><div class="ph-name">LA&nbsp;BUSE</div><div class="ph-sub">Radar foncier · La Réunion</div></div>
      </div>
      <div class="ph-meta">Fiche parcelle<br>${today}</div>
    </header>

    <header class="fiche-head">
      <div class="fh-id">${esc(p.idu)}</div>
      <div class="fh-loc">${loc}</div>
    </header>

    ${p.origine === "audit" ? `<section class="audit-banner">🔎 <b>Audit à la demande</b> — parcelle récupérée au cadastre et évaluée à la volée (hors balayage initial). Mêmes règles et mêmes sources que le reste du radar.</section>` : ""}

    <section class="hero v-${status}">
      ${renderGauge(v.opportunity_score)}
      <div class="hero-txt">
        <div class="hero-eyebrow">Verdict LA BUSE</div>
        <h1 class="hero-verdict">${STATUS_LABEL[status] || esc(status) || "—"}</h1>
        <p class="hero-pitch">${esc(VERDICT_GLOSS[status] || "")}</p>
        ${v.downgrade_reason ? `<p class="verdict-downgrade">Signal positif, mais potentiel limité seul — ${esc(v.downgrade_reason)}.</p>` : ""}
        <div class="hero-meta">Complétude ${v.completeness_score ?? "—"}${p.surface_m2 ? " · " + fmt(Math.round(p.surface_m2)) + " m²" : ""}</div>
        ${fiableBadge(status)}
      </div>
    </section>

    ${renderNotePromoteur(f)}

    ${renderAssistant(p.idu)}

    ${renderResume(f.resume)}

    ${renderBati(f.bati)}

    ${unverifiedLine}

    <section class="reads">
      <div class="read"><h3 class="rd-h ok">Ce qui favorise</h3>${block(favors, "ok", "Aucun signal franchement favorable sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h lim${hasHard ? " has-hard" : ""}">Ce qui contraint</h3>${block(limits, "lim", "Aucune contrainte relevée sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h unk">Ce qu'on n'a pas vérifié</h3>${block(unknown, "unk", "Toutes les couches critiques ont répondu.")}</div>
    </section>

    <div class="audit-head"><span class="audit-head-t">Audit foncier complet</span>
      <span class="audit-head-s">détails, calculs, sources — la traçabilité de chaque verdict</span></div>

    ${renderFaisabilite(f.faisabilite)}

    ${renderPermits(f.permits)}

    ${renderVoisinage(f.voisinage)}

    ${renderAi(f.ai)}

    ${promoteurSlot()}

    <details class="cascade">
      <summary>Traçabilité des sources · chaque verdict pointe sa couche <span class="cc-count">${cascade.length} couches</span></summary>
      <table class="cascade-table">${cascadeRows}</table>
    </details>

    <section class="sources">
      <h3 class="src-h">Sources analysées · transparence méthodologique</h3>
      <p class="src-summary"><b>${(f.sources_responded || []).length + (f.sources_silent || []).length}</b> sources publiques analysées · <b class="src-ok-n">${(f.sources_responded || []).length}</b> ont répondu${(f.sources_silent || []).length ? ` · <b class="src-na-n">${(f.sources_silent || []).length}</b> à vérifier / non disponibles` : ""}.</p>
      <div class="src-chips">${chips(f.sources_responded, "ok") || '<span class="src-chip silent">—</span>'}</div>
      ${(f.sources_silent || []).length ? `<h3 class="src-h muted">Sources non disponibles · à vérifier</h3><div class="src-chips">${chips(f.sources_silent, "silent")}</div>` : ""}
      <p class="src-note">LA BUSE affiche ce qu'elle sait — et ce qu'elle ne sait pas encore. Chaque verdict est vérifiable, source par source.</p>
    </section>

    ${renderProspection(f)}

    <footer class="fiche-actions">
      <button class="btn cta-primary follow" data-follow>+ Ajouter au pipeline</button>
      <div class="fa-secondary">
        <button class="btn js-compare-add" data-idu="${esc(p.idu)}">⊕ Comparer</button>
        <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=onepager" target="_blank" title="Fiche 1 page A4 — pour un comité">📄 Fiche PDF</a>
        <details class="fa-more">
          <summary class="fa-more-btn">Plus d'actions</summary>
          <div class="fa-more-menu">
            <button class="btn good" data-fb="good_lead">Marquer « bon lead »</button>
            <button class="btn bad" data-fb="false_positive">Marquer « écartée »</button>
            <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=md" target="_blank">Export Markdown</a>
            <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=html" target="_blank">Export HTML</a>
          </div>
        </details>
      </div>
    </footer>
    <p class="disclaimer">${esc(f.disclaimer || "")}</p>

    <footer class="print-foot print-only">
      <b>LA&nbsp;BUSE</b> · Pré-analyse foncière sur données publiques · ${esc(p.idu)} · ${today}<br>
      Constructibilité, propriété, rentabilité, faisabilité — <b>jamais garanties</b>. Document indicatif à vérifier avant toute démarche.
    </footer>`;
}

// Résumé « business » (Phase 2) — lecture promoteur : pourquoi / vigilance / prochaine action.
// Le contenu vient du backend (build_resume) ; vocabulaire prudent garanti côté serveur.
function renderResume(r) {
  if (!r) return "";
  const li = (arr) => (arr && arr.length)
    ? `<ul class="rs-list">${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
    : `<p class="rs-empty">—</p>`;
  // Une parcelle DÉCLASSÉE ne « ressort » pas : ses positifs sont les signaux BRUTS
  // d'avant déclassement (audit J4 — lister « pourquoi elle ressort » sous un verdict
  // « faux positif » déroutait).
  const declassee = r.statut === "faux_positif_probable" || r.statut === "exclue";
  const posTitle = declassee ? "Signaux positifs (potentiel limité seul)" : "Pourquoi elle ressort";
  return `
    <section class="resume v-${r.statut}">
      <div class="rs-head">
        <span class="rs-eyebrow">Résumé opportunité</span>
        <span class="chip ${r.statut}">${esc(r.statut_label)}</span>
      </div>
      <p class="rs-synthese">${esc(r.synthese)}</p>
      <div class="rs-cols">
        <div class="rs-col"><h4 class="rs-h ok">${posTitle}</h4>${li(r.positifs)}</div>
        <div class="rs-col"><h4 class="rs-h warn">À vérifier</h4>${li(r.vigilance)}</div>
      </div>
      <div class="rs-action"><span class="rs-action-k">Prochaine action</span> ${esc(r.prochaine_action)}</div>
    </section>`;
}

// Occupation actuelle / bâti détecté (correctif R1) — toujours affiché, y compris
// « non vérifiée » si la couche bâtiments n'est pas ingérée (jamais un faux « vacant »).
function renderBati(b) {
  if (!b) return "";
  const tone = { vacant: "ok", peu_bati: "warn", partiellement_bati: "warn",
    deja_bati_probable: "bad", deja_bati: "bad", ensemble_bati: "bad", inconnu: "unk" }[b.code] || "unk";
  const figs = b.disponible
    ? `<span class="bt-figs">${b.ratio_pct} % bâti · ${b.nb_batiments} bâtiment${b.nb_batiments > 1 ? "s" : ""}${b.plus_grand_m2 ? ` · plus grand ${fmt(b.plus_grand_m2)} m²` : ""}</span>`
    : "";
  return `
    <section class="bati bt-${tone}">
      <span class="bt-k">Occupation actuelle</span>
      <span class="bt-label">${esc(b.label)}</span>
      ${figs}
      <span class="bt-src">${esc(b.source)} · confiance ${esc(b.confiance)}</span>
    </section>`;
}

// Assemblage foncier (Phase 5) — parcelles voisines contiguës + drapeau prudent.
// Autorisations d'urbanisme à proximité (Lot C4) — historique SITADEL < 300 m.
function renderPermits(pm) {
  if (!pm || (!pm.count && !(pm.dynamique && pm.dynamique.permis_recents))) return "";
  const dyn = pm.dynamique || {};
  const dynCls = { actif: "dyn-actif", "modéré": "dyn-modere", calme: "dyn-calme" }[dyn.niveau] || "dyn-calme";
  // 1.B-fix-b — toujours qualifier par la couverture (jamais « calme » sec si peu de PC géolocalisés).
  const cov = dyn.couverture_pct != null
    ? ` <span class="pmt-cov">— calculé sur ${dyn.geolocalises}/${dyn.total} autorisations géolocalisées (${dyn.couverture_pct}%${dyn.fiable ? "" : ", couverture partielle"})</span>` : "";
  const dynBanner = dyn.niveau ? `<div class="pmt-dyn ${dynCls}">Secteur <b>${esc(dyn.niveau)}</b> — ${dyn.permis_recents} autorisation(s)${dyn.logements_recents ? ` · ${dyn.logements_recents} logements` : ""} dans ${pm.radius_m} m sur ${dyn.annees} ans${cov}</div>` : "";
  const rows = (pm.items || []).map((x) => `
    <li class="pmt-li${x.rattache ? " pmt-rat" : ""}">
      <span class="pmt-type" title="${esc(x.type_label || x.type || "")}">${esc(x.type || "—")}</span>
      <span class="pmt-body"><span class="pmt-nat">${esc(x.nature || "")}</span>
        <span class="pmt-meta">${esc(x.statut || "")}${x.rattache ? " · sur la parcelle" : (x.distance_m != null ? ` · ~${x.distance_m} m` : "")}</span></span>
    </li>`).join("");
  return `
    <section class="permits">
      <h3 class="pmt-h">Autorisations d'urbanisme à proximité
        <span class="pmt-count">${pm.count} dans ${pm.radius_m} m${pm.rattaches ? ` · ${pm.rattaches} sur la parcelle` : ""}</span></h3>
      ${dynBanner}
      <ul class="pmt-list">${rows}</ul>
      <p class="pmt-src">Source ${esc(pm.source || "SITADEL")} — autorisations accordées (les refus n'y figurent pas). Géolocalisation par référence cadastrale, non exhaustive.</p>
    </section>`;
}

function renderVoisinage(vz) {
  if (!vz || !(vz.voisines || []).length) return "";
  const a = vz.assemblage || {};
  const items = vz.voisines.map((v) => `
    <button class="vz-item" data-idu="${esc(v.idu)}" title="Ouvrir la fiche ${esc(v.idu)}">
      <span class="vz-idu">${esc(v.idu)}</span>
      <span class="chip ${v.status || "inconnu"}">${STATUS_LABEL[v.status] || "—"}</span>
      <span class="vz-meta">${v.opportunity_score != null ? `<b>${v.opportunity_score}</b> opp · ` : ""}${v.plu_zone ? "zone " + esc(v.plu_zone) + " · " : ""}${v.surface_m2 != null ? fmt(v.surface_m2) + " m²" : ""}</span>
    </button>`).join("");
  const banner = a.possible ? `<div class="vz-assemblage">${esc(a.note)}</div>` : "";
  // Assemblage v1 (Lot C5) : paire contiguë qui débloque le seuil de taille.
  const unlock = vz.assemblage_unlock || {};
  const unlockBanner = unlock.possible
    ? `<div class="vz-unlock${unlock.priorite_meme_proprietaire ? " vz-prio" : ""}">🧩 ${esc(unlock.note)}</div>` : "";
  return `
    <section class="voisinage">
      <h3 class="src-h">Parcelles voisines à regarder <span class="pm-sub">· contiguës, indicatif</span></h3>
      ${unlockBanner}
      ${banner}
      <div class="vz-list">${items}</div>
      <p class="vz-foot">Adjacence géométrique uniquement — un même propriétaire, un accord ou la faisabilité d'un assemblage restent à vérifier.</p>
    </section>`;
}

// Bloc PROSPECTION propriétaire (manuel, Niveau 1) — aucune donnée nominative externe.
const PP_SRC = { non_renseignee: "non renseignée", saisi_utilisateur: "saisie utilisateur",
  deduit_manuellement: "déduit manuellement", document_externe_utilisateur: "document externe (utilisateur)", autre: "autre" };
const PP_CONF = { inconnu: "inconnu", faible: "faible", moyen: "moyen", eleve: "élevé" };
const PP_STATUT = { inconnu: "Propriétaire inconnu", a_identifier: "À identifier",
  identifie_manuellement: "Identifié (manuel)", public_probable: "Public probable",
  institutionnel_probable: "Institutionnel probable", indivision_probable: "Indivision probable",
  copropriete_probable: "Copropriété probable" };
function renderProspection(f) {
  const pr = f.prospection || {}, d = pr.data || {};
  const contact = [d.contact_nom, d.contact_organisation, d.contact_telephone, d.contact_email, d.contact_adresse].filter(Boolean).map(esc).join(" · ");
  const action = d.prochaine_action ? esc(d.prochaine_action) + (d.date_prochaine_action ? ` (rappel ${esc(d.date_prochaine_action)})` : "") : "—";
  const row = (k, v) => `<span class="pp-k">${k}</span><span class="pp-v">${v}</span>`;
  return `
    <section class="prospection">
      <h3 class="src-h">Prospection propriétaire</h3>
      <div class="pp-grid">
        ${row("Statut", esc(pr.statut_label || "Propriétaire inconnu"))}
        ${row("Source · confiance", esc(PP_SRC[d.source_statut] || "non renseignée") + " · " + esc(PP_CONF[d.niveau_confiance] || "inconnu"))}
        ${row("Contact", contact || "<i>Propriétaire à identifier — aucune donnée nominative dans LA BUSE.</i>")}
        ${row("Prochaine action", action)}
        ${row("Responsable", esc(d.responsable_interne || "—"))}
        ${row("Notes", esc(d.notes_contact || "—"))}
      </div>
      ${pr.in_pipeline ? "" : `<p class="pp-default">Propriétaire non identifié automatiquement. À compléter manuellement ou via une source autorisée.</p>`}
      <div class="pp-actions">
        ${pr.in_pipeline ? "" : `<button class="btn" data-prosp="add">+ Ajouter au pipeline</button>`}
        <button class="btn" data-prosp="identify">Marquer « propriétaire à identifier »</button>
        <button class="btn" data-prosp="contact">Ajouter / modifier contact manuel</button>
      </div>
      <form class="pp-form hidden" id="pp-form">
        <input class="pp-in" name="contact_nom" maxlength="200" placeholder="Nom ou organisation (saisie manuelle)" value="${esc(d.contact_nom || d.contact_organisation || "")}">
        <div class="pp-form-row">
          <input class="pp-in" name="contact_telephone" maxlength="40" placeholder="Téléphone" value="${esc(d.contact_telephone || "")}">
          <input class="pp-in" name="contact_email" type="email" maxlength="120" placeholder="E-mail" value="${esc(d.contact_email || "")}">
        </div>
        <div class="pp-form-row">
          <button class="btn pp-save" type="submit">Enregistrer le contact</button>
          <button class="btn pp-cancel" type="button">Annuler</button>
        </div>
        <p class="pp-disc">Saisie manuelle — aucune donnée récupérée automatiquement.</p>
      </form>
      <p class="pp-disc">${esc(pr.disclaimer || "")}</p>
    </section>`;
}

// ───────────────────────── Données promoteur (Temps 1) ─────────────────────────
// Tout est indicatif & sourcé ; aucune valeur réglementaire fabriquée. Mesures EPSG:2975.
function renderPromoteur(pr, centroid, idu) {
  if (!pr) return "";
  const alt = pr.altimetrie || {}, fac = pr.facade || {}, plu = pr.plu_detail || {};
  const exp = pr.exposition || {}, vm = pr.vue_mer || {};
  const own = pr.proprietaire || {}, net = pr.reseaux || {};
  const fig = (val, lbl) => `<span class="pm-fig"><b>${val ?? "—"}</b><i>${lbl}</i></span>`;
  const na = (o) => `<p class="pm-na">${esc(o.note || "Indisponible.")}</p>`;

  // 1 · Cote altimétrique + EXPOSITION (RGE ALTI, live échantillonné) — 2.A
  const expLine = exp.available
    ? `<p class="pm-exp">🧭 ${esc(exp.label || "")}${exp.azimut_deg != null ? ` (${exp.azimut_deg}°)` : ""}${exp.pente_locale_pct != null ? ` · pente locale ~${exp.pente_locale_pct} %` : ""}</p>` : "";
  // 2.B — vue mer (indicatif, ligne de vue 1D)
  const vmIcon = { oui: "🌊", partielle: "🌅", non: "⛰️" }[vm.vue] || "";
  const vmLine = vm.available
    ? `<p class="pm-vuemer pm-vm-${vm.vue}">${vmIcon} ${esc(vm.label || "")}${vm.distance_cote_m != null ? ` · côte à ${vm.distance_cote_m} m` : ""}${vm.altitude_obs_m != null ? ` · alt. ${vm.altitude_obs_m} m` : ""} <span class="pm-vm-note">(indicatif, profil 1D)</span></p>` : "";
  const altBody = alt.available
    ? `<div class="pm-figs">${fig(alt.min_m, "min (m)")}${fig(alt.mean_m, "moy. (m)")}${fig(alt.max_m, "max (m)")}${fig(alt.amplitude_m, "amplitude (m)")}</div>
       ${expLine}${vmLine}<p class="pm-src">${esc(alt.source || "")} · ${alt.n_points || 0} pts</p>`
    : (expLine || vmLine ? `${expLine}${vmLine}<p class="pm-src">${esc(exp.source || vm.source || "")}</p>` : na(alt));

  // 2 · Façade sur voie + profondeur (BD TOPO, EPSG:2975)
  let facBody;
  if (fac.sur_rue) {
    const prof = fac.profondeur_m != null
      ? `<span class="pm-fig"><b>${fac.profondeur_m}</b><i>profondeur (m)</i></span>`
      : `<span class="pm-fig degr"><b>≈</b><i>${esc(fac.profondeur_note || "")}</i></span>`;
    const forme = fac.forme
      ? `<p class="pm-src">forme : rectangularité ${fac.forme.rectangularite} · convexité ${fac.forme.convexite} · emprise orientée ${fac.forme.emprise_orientee_m?.join(" × ")} m</p>` : "";
    facBody = `<div class="pm-figs">${fig(fac.facade_totale_m, "façade totale (m)")}${fig(fac.facade_principale_m, "façade princ. (m)")}${fig(fac.nb_voies, "voie(s) longée(s)")}${prof}</div>
      ${forme}<p class="pm-src">${esc(fac.source || "")} · tampon ${fac.tolerance_laterale_m} m</p>`;
  } else {
    facBody = na({ note: fac.profondeur_note || "Aucune façade sur voie identifiée." });
  }

  // 3 · Vue du ciel (orthophoto IGN) — vignette + rappel du fond de carte
  let sky = "";
  if (centroid && centroid.lon != null) {
    const d = 0.0006;  // ~ ±65 m autour du centroïde
    const bbox = `${(centroid.lat - d).toFixed(6)},${(centroid.lon - d).toFixed(6)},${(centroid.lat + d).toFixed(6)},${(centroid.lon + d).toFixed(6)}`;
    const url = "https://data.geopf.fr/wms-r/wms?LAYERS=ORTHOIMAGERY.ORTHOPHOTOS&FORMAT=image/jpeg&SERVICE=WMS"
      + "&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:4326&WIDTH=440&HEIGHT=300&BBOX=" + bbox;
    // 3.B — « Remonter le temps » : lien IGN paramétré sur le centroïde (ortho actuelle ↔ ~1960).
    // URL servie par l'API (testée) ; repli client si cache d'enrichissement antérieur à 3.B.
    const rlt = (pr.remonter_le_temps && pr.remonter_le_temps.url)
      || `https://remonterletemps.ign.fr/comparer?lon=${centroid.lon.toFixed(6)}&lat=${centroid.lat.toFixed(6)}`
         + `&z=18&layer1=ORTHOIMAGERY.ORTHOPHOTOS&layer2=ORTHOIMAGERY.ORTHOPHOTOS.1950-1965&mode=doubleMap`;
    sky = `<div class="pm-sky"><img loading="lazy" src="${url}" alt="Vue aérienne IGN de la parcelle"
        onerror="this.parentNode.innerHTML='<p class=&quot;pm-na&quot;>Orthophoto IGN momentanément indisponible.</p>'">
      <span class="pm-sky-cap">Orthophoto IGN (BD ORTHO) · centrée sur la parcelle</span></div>
      <a class="btn pm-rlt" href="${rlt}" target="_blank" rel="noopener"
         title="Comparer la parcelle aux photos aériennes historiques de l'IGN (1950 → aujourd'hui)">📜 Remonter le temps (IGN)</a>
      <p class="pm-src">Astuce : bascule un millésime historique (1961 / 1980 / 1989 / 2010) sur la carte (coin haut-droit).</p>`;
  }

  // 4 · PLU détaillé (zonage ingéré + prescriptions GPU réelles ; règles chiffrées → règlement)
  const zChips = (plu.zonage || []).map((z) => `<span class="src-chip ok">${esc(z)}</span>`).join("") || '<span class="src-chip silent">zonage non trouvé</span>';
  const presc = (plu.prescriptions || []).length
    ? `<ul class="pm-list">${plu.prescriptions.map((x) => `<li><span class="pm-prtype">${esc(x.type)}</span> ${esc(x.libelle || "—")}${x.nature ? " · " + esc(x.nature) : ""}</li>`).join("")}</ul>`
    : `<p class="pm-na">${esc(plu.prescriptions_note || "Aucune prescription/servitude graphique interceptée.")}</p>`;
  const pluBody = `
    <div class="pm-row"><span class="pm-k">Zonage</span><span class="src-chips">${zChips}</span>${plu.idurba ? `<span class="pm-src">${esc(plu.idurba)}</span>` : ""}</div>
    <div class="pm-row"><span class="pm-k">Prescriptions / servitudes</span><div>${presc}</div></div>
    <p class="pm-note">⚠︎ ${esc(plu.regles_chiffrees_note || "")}</p>
    ${plu.reglement_url ? `<a class="btn" href="${esc(plu.reglement_url)}" target="_blank" rel="noopener">Ouvrir le règlement (GPU)</a>` : ""}`;

  // 5 · Propriétaire + viabilité/réseaux (honnêteté : aucun « raccordé/non raccordé »)
  const netRow = (label, o) => `<li><b>${label}</b> — ${esc((o && o.note) || "à vérifier")}</li>`;
  const via = net.viabilite || {};
  const viaBlock = via.presomption ? `
    <div class="pm-via">
      <span class="pm-via-h">Viabilité <span class="pm-via-tag">à vérifier</span></span>
      <p>${esc(via.presomption)}</p>
      ${via.a_verifier ? `<p class="pm-note">⚠︎ ${esc(via.a_verifier)}</p>` : ""}
    </div>` : "";
  // Type de propriétaire (Lot C3) : badge + bouton « demande SPF » si non identifiable.
  const famCls = { public: "own-pub", prive: "own-priv", inconnu: "own-unk" }[own.owner_famille] || "own-unk";
  const ownerBadge = own.owner_label
    ? `<span class="own-badge ${famCls}" title="${esc(own.owner_acquerabilite || "")}">${esc(own.owner_label)}</span>` : "";
  const spfBtn = own.needs_spf
    ? `<button type="button" class="own-spf js-spf" data-idu="${esc(idu)}" title="Courrier pré-rempli de demande au Service de la Publicité Foncière">✉ Générer demande SPF</button>` : "";
  // M8 — statuts COURTS au premier niveau ; le détail verbeux + sources sous un accordéon.
  const ownShort = own.owner_label ? ownerBadge : (own.needs_spf ? "à identifier" : esc(own.note || "à vérifier"));
  const psRow = (k, v) => `<li><span class="ps-k">${k}</span><span class="ps-v">${v}</span></li>`;
  const factBody = `
    <ul class="pm-status">
      ${psRow("Propriétaire", ownShort)}
      ${psRow("Viabilité", "à vérifier")}
      ${psRow("Eau potable", "données insuffisantes")}
      ${psRow("Électricité", "donnée agrégée, sans tracé")}
      ${psRow("Assainissement", "à vérifier")}
    </ul>
    ${spfBtn}
    <details class="pm-detail">
      <summary>Voir détails réseaux &amp; sources</summary>
      ${viaBlock}
      <ul class="pm-list net">${netRow("Eau potable", net.eau_potable)}${netRow("Électricité (EDF)", net.electricite)}${netRow("Assainissement", net.assainissement)}</ul>
      <p class="pm-src">${esc((net && net.source) || "")}</p>
    </details>`;

  const card = (title, body, tag) => `<div class="pm-card"><h4 class="pm-h">${title}${tag ? `<span class="pm-ind">${tag}</span>` : ""}</h4>${body}</div>`;

  return `
    <section class="promoteur">
      <h3 class="src-h">Données promoteur <span class="pm-sub">· publiques, tracées, indicatives</span></h3>
      <div class="pm-grid">
        ${card("Cote altimétrique", altBody, "indicatif")}
        ${card("Façade & profondeur", facBody, "indicatif · EPSG:2975")}
        ${card("Vue du ciel", sky || na({ note: "Centroïde indisponible." }), "")}
        ${card("PLU détaillé", pluBody, "")}
        ${card("Propriété & réseaux", factBody, "")}
      </div>
      <p class="pm-foot">${esc(pr.disclaimer || "")}${pr.computed_at ? ` · Dernière vérification : ${fmtDateTime(pr.computed_at)}` : ""}</p>
    </section>`;
}

// Format date/heure court (fr) à partir d'un ISO ; "" si invalide.
function fmtDateTime(iso) {
  const d = new Date(iso);
  return isNaN(d) ? "" : d.toLocaleString("fr-FR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Emplacement du bloc « promoteur » pendant son chargement lazy (appels externes lents).
function promoteurSlot() {
  return `<section class="promoteur" id="pm-slot">
    <h3 class="src-h">Données promoteur <span class="pm-sub">· publiques, tracées, indicatives</span></h3>
    <div class="pm-loading"><span class="pm-spin" aria-hidden="true"></span> Analyse réseaux &amp; terrain en cours…</div>
  </section>`;
}

// Charge le bloc « promoteur » en arrière-plan (GET /parcels/{idu}/enrichment) puis remplace
// l'emplacement. Échec/timeout : message clair, jamais de blocage ni de fiche cassée. Garde
// anti-course : si l'utilisateur a déjà rouvert une autre fiche, on n'écrase pas son contenu.
async function loadEnrichment(idu, centroid) {
  const slot = $("#pm-slot");
  if (!slot) return;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 35000);   // garde-fou (ALTI+GPU déjà bornés serveur)
  let pr;
  try {
    const r = await fetch(`/parcels/${encodeURIComponent(idu)}/enrichment`, { signal: ctrl.signal });
    if (!r.ok) throw new Error(String(r.status));
    pr = await r.json();
  } catch {
    if ($("#pm-slot") === slot) slot.innerHTML =
      `<h3 class="src-h">Données promoteur</h3>
       <p class="pm-na">Données réseaux &amp; terrain momentanément indisponibles — à vérifier auprès des sources officielles.</p>`;
    return;
  } finally { clearTimeout(timer); }
  if ($("#pm-slot") === slot) {
    slot.outerHTML = renderPromoteur(pr, centroid, idu);
    surfaceServitudesMajeures(pr);
    const spf = document.querySelector(".js-spf");
    if (spf) spf.addEventListener("click", () => openSpfLetter(spf.dataset.idu));
  }
}

// Lot C3 — ouvre le courrier SPF pré-rempli dans un nouvel onglet (texte brut, imprimable).
function openSpfLetter(idu) {
  window.open(`/parcels/${encodeURIComponent(idu)}/spf-letter`, "_blank", "noopener");
}

// ───────────────────────── Filtres sauvegardés (Lot D3) ─────────────────────────
function getFilterState() {
  return {
    statuses: [...document.querySelectorAll("#filter-statuses input:checked")].map((i) => i.value),
    opp: +$("#f-opp").value, cpl: +$("#f-cpl").value, surf: +$("#f-surf").value,
    sousDensite: !!($("#f-sousdense") && $("#f-sousdense").checked),
    taux: +(($("#f-taux") && $("#f-taux").value) || 40),
    owner: ($("#f-owner") && $("#f-owner").value) || "",
  };
}
function applyFilterState(s) {
  if (!s) return;
  document.querySelectorAll("#filter-statuses input").forEach((i) => { i.checked = (s.statuses || []).includes(i.value); });
  const set = (id, val, out) => { const el = $(id); if (el && val != null) { el.value = val; if (out) { const o = $(out); if (o) o.textContent = val; } } };
  set("#f-opp", s.opp, "#opp-out"); set("#f-cpl", s.cpl, "#cpl-out"); set("#f-surf", s.surf, "#surf-out");
  if ($("#f-sousdense")) $("#f-sousdense").checked = !!s.sousDensite;
  set("#f-taux", s.taux, "#taux-out"); if ($("#f-owner")) $("#f-owner").value = s.owner || "";
  clearKpiActive(); applyFilters();
}
let SAVED_FILTERS = [];
async function loadSavedFilters() {
  try { SAVED_FILTERS = await (await fetch("/filters")).json(); } catch { SAVED_FILTERS = []; }
  const sel = $("#f-saved"); if (!sel) return;
  sel.innerHTML = `<option value="">— filtres sauvegardés —</option>`
    + SAVED_FILTERS.map((f) => `<option value="${f.id}">${esc(f.name)}</option>`).join("");
}
async function saveCurrentFilter() {
  const name = ($("#fs-name").value || "").trim();
  if (!name) { $("#fs-name").focus(); return; }
  try {
    await fetch("/filters", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, params: getFilterState() }) });
    $("#fs-name").value = ""; await loadSavedFilters();
  } catch { /* silencieux */ }
}
async function deleteSavedFilter() {
  const id = $("#f-saved").value; if (!id) return;
  try { await fetch(`/filters/${id}`, { method: "DELETE" }); await loadSavedFilters(); } catch { /* */ }
}

// ───────────────────────── Comparateur (Lot D2) ─────────────────────────
function addToCompare(idu) {
  if (!idu || COMPARE.includes(idu)) return;
  if (COMPARE.length >= 3) { alert("Comparateur : 3 parcelles maximum."); return; }
  COMPARE.push(idu);
  renderCompareTray();
}
function removeFromCompare(idu) { COMPARE = COMPARE.filter((x) => x !== idu); renderCompareTray(); }
function clearCompare() { COMPARE = []; renderCompareTray(); }

function renderCompareTray() {
  const tray = $("#compare-tray"); if (!tray) return;
  tray.classList.toggle("hidden", COMPARE.length === 0);
  const chips = COMPARE.map((idu) =>
    `<span class="cmp-chip">${esc(idu)}<button class="cmp-x" data-rm="${esc(idu)}" title="Retirer">✕</button></span>`).join("");
  tray.innerHTML = `<span class="cmp-tray-lbl">Comparer :</span>${chips}
    <button class="cmp-go" id="cmp-go"${COMPARE.length < 2 ? " disabled" : ""}>Comparer (${COMPARE.length})</button>
    <button class="cmp-clear" id="cmp-clear">vider</button>`;
}

function meur(x) { return x == null ? "—" : (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(1) + " M€" : Math.abs(x) >= 1e3 ? Math.round(x / 1e3) + " k€" : Math.round(x) + " €"); }
// label · affichage · clé numérique de surlignage (raw) · sens "max"/"min"/"".
const CMP_ROWS = [
  ["Statut", (p) => STATUS_LABEL[p.status] || "—", null, ""],
  ["Opportunité", (p) => p.opportunity_score ?? "—", (p) => p.opportunity_score, "max"],
  ["Complétude", (p) => p.completeness_score ?? "—", (p) => p.completeness_score, "max"],
  ["Surface", (p) => p.surface_m2 != null ? fmt(p.surface_m2) + " m²" : "—", (p) => p.surface_m2, "max"],
  ["Zone PLU", (p) => esc(p.zone || "—"), null, ""],
  ["Capacité", (p) => esc(p.capacite || (p.constructible ? "—" : "non constructible")), null, ""],
  ["SDP max", (p) => p.sdp_max_m2 != null ? "~" + fmt(p.sdp_max_m2) + " m²" : "—", (p) => p.sdp_max_m2, "max"],
  ["Emprise utilisée", (p) => p.taux_emprise_pct != null ? p.taux_emprise_pct + " %" + (p.sous_densite ? " · sous-densité" : "") : "—", (p) => p.taux_emprise_pct, "min"],
  ["SDP résiduelle", (p) => p.sdp_residuelle_m2 != null ? "~" + fmt(p.sdp_residuelle_m2) + " m²" : "—", (p) => p.sdp_residuelle_m2, "max"],
  ["CA potentiel", (p) => p.ca_bas != null ? meur(p.ca_bas) + "–" + meur(p.ca_haut) : "—", (p) => p.ca_haut, "max"],
  ["Charge foncière /m²", (p) => p.charge_fonciere_m2 != null ? fmt(p.charge_fonciere_m2) + " €/m²" : "—", (p) => p.charge_fonciere_m2, "max"],
  ["Contraintes", (p) => p.n_contraintes, (p) => p.n_contraintes, "min"],
];

async function openCompare() {
  if (COMPARE.length < 2) return;
  $("#compare-panel").classList.remove("hidden"); $("#scrim").classList.remove("hidden");
  $("#compare-body").innerHTML = `<div class="loading">Comparaison…</div>`;
  let data;
  try { data = await (await fetch(`/compare?idus=${encodeURIComponent(COMPARE.join(","))}`)).json(); }
  catch { $("#compare-body").innerHTML = `<div class="loading">Comparaison indisponible.</div>`; return; }
  const ps = data.parcels || [];
  if (ps.length < 2) { $("#compare-body").innerHTML = `<div class="loading">Au moins 2 parcelles valides requises.</div>`; return; }
  const heads = ps.map((p) => `<th><a href="#" class="cmp-open" data-idu="${esc(p.idu)}">${esc(p.idu)}</a><span class="cmp-loc">${esc(p.commune || "")} ${esc(p.section || "")}${esc(p.numero || "")}</span></th>`).join("");
  const rows = CMP_ROWS.map(([label, disp, raw, dir]) => {
    let bestIdx = -1;
    if (raw && dir) {
      const nums = ps.map((p) => { const n = raw(p); return (n == null || isNaN(n)) ? null : Number(n); });
      const valid = nums.filter((n) => n != null);
      if (valid.length > 1) {
        const target = dir === "max" ? Math.max(...valid) : Math.min(...valid);
        bestIdx = nums.findIndex((n) => n === target);
      }
    }
    const cells = ps.map((p, i) => `<td class="${i === bestIdx ? "cmp-best" : ""}">${disp(p)}</td>`).join("");
    return `<tr><td class="cmp-lbl">${label}</td>${cells}</tr>`;
  }).join("");
  $("#compare-body").innerHTML = `
    <h2 class="cmp-h">Comparateur · ${ps.length} parcelles</h2>
    <table class="cmp-table"><thead><tr><th></th>${heads}</tr></thead><tbody>${rows}</tbody></table>
    <p class="cmp-foot">Surlignage = meilleure valeur par ligne (indicatif). Pré-analyse sur données publiques ; capacité et bilan ne valent pas étude réglementaire.</p>`;
}
function closeCompare() {
  $("#compare-panel").classList.add("hidden");
  if ($("#sheet").classList.contains("hidden")) $("#scrim").classList.add("hidden");
}

// Lot C4 — marqueurs SITADEL (différés) ; couche désactivée par défaut (toggle layer control).
async function loadPermitMarkers() {
  if (!map || !PERMITS_LAYER) return;
  let fc;
  try { fc = await (await fetch(`/map/permits.geojson?commune=${encodeURIComponent(COMMUNE)}`)).json(); }
  catch { return; }
  PERMITS_LAYER.clearLayers();
  (fc.features || []).forEach((ft) => {
    const [lon, lat] = ft.geometry.coordinates;
    L.circleMarker([lat, lon], { radius: 4, color: "#c98a3a", weight: 1, fillOpacity: 0.7 })
      .bindTooltip(`${esc(ft.properties.type || "permis")} ${esc(ft.properties.num || "")}${ft.properties.date ? " · " + esc(ft.properties.date) : ""}`,
        { direction: "top" })
      .addTo(PERMITS_LAYER);
  });
}

// Audit O6 : une servitude de MIXITÉ SOCIALE (« logements aidés », emplacement réservé)
// change le bilan d'un promoteur privé — elle ne doit pas rester enfouie dans le bloc
// enrichi. Quand l'enrichissement arrive, on la REMONTE dans la vigilance du résumé
// (les prescriptions GPU sont chargées en lazy : c'est le seul moment où on les connaît).
function surfaceServitudesMajeures(pr) {
  const prescs = ((pr || {}).plu_detail || {}).prescriptions || [];
  const RX = /logement(s)? (aid|soci)|mixit[ée] sociale|emplacement r[ée]serv[ée]/i;
  const hits = prescs.filter((x) => RX.test(`${x.libelle || ""} ${x.nature || ""}`));
  if (!hits.length) return;
  const col = document.querySelectorAll(".rs-col")[1];           // colonne « À vérifier »
  if (!col) return;
  let list = col.querySelector(".rs-list");
  if (!list) {                                                    // colonne vide (« — »)
    const empty = col.querySelector(".rs-empty"); if (empty) empty.remove();
    list = document.createElement("ul"); list.className = "rs-list"; col.appendChild(list);
  }
  const lbl = (hits[0].libelle || "servitude de mixité sociale").toString().slice(0, 80);
  if ([...list.children].some((li) => li.dataset.servitude)) return;   // déjà injectée
  const li = document.createElement("li");
  li.dataset.servitude = "1";
  li.textContent = `Servitude PLU : ${lbl} — % de logements aidés possible, à intégrer au bilan`;
  list.appendChild(li);
}

function renderFaisabilite(fa) {
  if (!fa) return "";
  const fr = fa.fourchette || {}, ctx = fa.contexte || {};
  const ctxBits = [
    `zone PLU <b>${esc(fa.zone)}</b>`,
    fa.surface_m2 ? fmt(fa.surface_m2) + " m²" : "",
    ctx.pente_pct != null ? "pente " + ctx.pente_pct + " %" : "",
    ctx.littoral ? "trait de côte" : "",
    ctx.safer ? "SAFER" : "",
  ].filter(Boolean).join(" · ");

  const reg = fr.stationnement_regime, sol = fr.logements_au_sol || [], sous = fr.logements_sous_sol || [];
  let logCard = "—";
  if (fa.constructible) {
    if (reg === "borne") logCard = `${sol[0]}–${sol[1]}<span class="fc-sub">au sol</span> · ${sous[0]}–${sous[1]}<span class="fc-sub">sous-sol</span>`;
    else logCard = `${sous[0]}–${sous[1]}${reg === "exempt" ? '<span class="fc-sub">non borné</span>' : ""}`;
  }
  const keyCards = fa.constructible ? `
    <div class="fc"><span class="fc-num">${esc(fr.niveaux || "—")}</span><span class="fc-lbl">Niveaux constructibles</span></div>
    <div class="fc"><span class="fc-num">~${fmt(fr.surface_plancher_m2)} m²</span><span class="fc-lbl">Surface de plancher</span></div>
    <div class="fc fc-wide"><span class="fc-num">${logCard}</span><span class="fc-lbl">Logements estimés</span></div>` : "";

  const stepRows = (fa.steps || []).map((s) => `
    <tr><td class="fs-lbl">${esc(s.label)}</td>
        <td class="fs-for">${esc(s.formule)}${s.valeur && s.valeur !== "—" ? ` <b>= ${esc(s.valeur)}</b>` : ""}<span class="fs-src">${esc(s.source)}</span></td></tr>`).join("");
  const bullets = (arr, cls, title) => (arr && arr.length)
    ? `<div class="fa-grp ${cls}"><span class="fa-grp-t">${title}</span><ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : "";

  // Badges « prescriptions GPU » (Décision 3) : mixité sociale, eaux pluviales, ER déduits.
  const eco = fa.prescriptions_eco || {};
  const badges = [
    eco.mixite_sociale ? `<span class="eco-badge" title="${esc(eco.mixite_sociale)}">Secteur de mixité sociale (logements aidés)</span>` : "",
    eco.eaux_pluviales ? `<span class="eco-badge" title="${esc(eco.eaux_pluviales)}">Zonage eaux pluviales</span>` : "",
    eco.er_deduit_m2 ? `<span class="eco-badge eco-er" title="surface d'emplacement réservé soustraite de l'emprise constructible">ER : ${fmt(eco.er_deduit_m2)} m² déduits</span>` : "",
  ].filter(Boolean).join("");

  return `
    <section class="faisa${fa.constructible ? "" : " faisa-nc"}">
      <div class="faisa-eyebrow">Pré-faisabilité · carte promoteur</div>
      <h2 class="faisa-verdict">${esc(fa.verdict)}</h2>
      <div class="faisa-ctx">${ctxBits}</div>
      ${badges ? `<div class="faisa-badges">${badges}</div>` : ""}
      ${keyCards ? `<div class="faisa-cards">${keyCards}</div>` : ""}
      ${renderVolume3D(fa.volume3d)}
      ${renderResiduel(fa.residuel)}
      <details class="faisa-calc" open>
        <summary>Le calcul, ligne par ligne — chaque ligne pointe sa règle PLU</summary>
        <table class="faisa-steps">${stepRows}</table>
      </details>
      ${bullets(fa.modulation, "mod", "Modulation réunionnaise")}
      ${bullets(fa.avertissements, "warn", "À vérifier (non comblé, jamais deviné)")}
      ${bullets(fa.hypotheses, "hyp", "Hypothèses de calcul (signalées)")}
      <p class="faisa-bandeau">⚠️ ${esc(fa.bandeau)}</p>
    </section>
    ${renderBilan(fa.bilan)}`;
}

// 3.A — Assistant IA : « Expliquer cette parcelle » → synthèse en prose des données RÉELLES.
// Sans clé API (ASSISTANT_OK=false), le bouton est désactivé avec un libellé clair — jamais d'erreur.
function renderAssistant(idu) {
  if (!ASSISTANT_OK) {
    return `<section class="assistant">
      <button type="button" class="ai-btn ai-off" disabled
        title="Définissez la variable d'environnement ANTHROPIC_API_KEY côté serveur pour activer l'assistant">
        <span class="ai-ic">✨</span> Expliquer cette parcelle <span class="ai-req">· clé API requise</span></button>
    </section>`;
  }
  return `<section class="assistant">
    <button type="button" class="ai-btn js-explain" data-idu="${esc(idu)}">
      <span class="ai-ic">✨</span> Expliquer cette parcelle</button>
    <p class="ai-pitch">Synthèse en langage clair : ce qui favorise, ce qui bloque, la prochaine action.</p>
    <div class="ai-out" id="ai-out" hidden></div>
  </section>`;
}
async function loadAssistantStatus() {
  try { ASSISTANT_OK = !!(await (await fetch("/assistant/status")).json()).configured; }
  catch { ASSISTANT_OK = false; }
}

// Markdown LÉGER et sûr pour la synthèse IA : on échappe d'abord (anti-XSS), puis on met en forme
// gras/italique, listes, et on isole visuellement les lignes de VIGILANCE (⚠).
function aiMarkdown(src) {
  const inline = (t) => esc(t)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
  let html = "", inList = false;
  for (const raw of String(src || "").split(/\n/)) {
    const t = raw.trim();
    if (/^[-*•]\s+/.test(t)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(t.replace(/^[-*•]\s+/, ""))}</li>`;
      continue;
    }
    if (inList) { html += "</ul>"; inList = false; }
    if (!t) continue;
    const warn = t.includes("⚠") ? " ai-warn" : "";
    // titre court terminé par « : » → mis en exergue
    const head = /^[^:]{2,40}:\s*$/.test(t) ? " ai-h" : "";
    html += `<p class="ai-p${warn}${head}">${inline(t)}</p>`;
  }
  if (inList) html += "</ul>";
  return html;
}

async function explainParcel(idu) {
  const out = $("#ai-out"), btn = document.querySelector(".js-explain");
  if (!out) return;
  out.hidden = false;
  out.innerHTML = `<div class="ai-loading"><span class="pm-spin" aria-hidden="true"></span> L'assistant rédige la synthèse…</div>`;
  if (btn) btn.disabled = true;
  let res;
  try { res = await (await fetch(`/parcels/${encodeURIComponent(idu)}/explain`)).json(); }
  catch { res = { available: false, message: "Assistant indisponible — réessayez." }; }
  if (btn) btn.disabled = false;
  if (res && res.available) {
    out.classList.add("ready");
    out.innerHTML = `<div class="ai-card-h"><span class="ai-ic">✨</span> Synthèse de la parcelle</div>
      <div class="ai-prose">${aiMarkdown(res.explanation)}</div>
      <p class="ai-foot">Rédigée par IA${res.model ? ` · ${esc(res.model)}` : ""} à partir des <b>seules données de la fiche</b> — à vérifier, aucune garantie.</p>`;
  } else {
    out.classList.remove("ready");
    out.innerHTML = `<div class="ai-na">${esc((res && res.message) || "Assistant indisponible.")}</div>`;
  }
}

// 3.D — Gabarit constructible en 3D : extrusion de l'emprise à la hauteur PLU, en AXONOMÉTRIE
// SVG (zéro dépendance 3D — cohérent avec la contrainte « vendorisé, offline-safe »). v1 simple :
// volume = emprise × hauteur ; ni architecture ni implantation réelle. Données en mètres locaux.
function renderVolume3D(v) {
  if (!v || !v.constructible || !(v.outline && v.outline.length >= 3)) return "";
  const foot = (v.emprise && v.emprise.length >= 3) ? v.emprise : v.outline;
  const h = v.hauteur_m || 0;
  const COS = 0.866, SIN = 0.5;
  const iso = (p, z) => [(p[0] - p[1]) * COS, (p[0] + p[1]) * SIN - z];   // (x,y,z) m → plan écran
  const proj = [];
  v.outline.forEach((p) => proj.push(iso(p, 0)));
  foot.forEach((p) => { proj.push(iso(p, 0)); proj.push(iso(p, h)); });
  const xs = proj.map((q) => q[0]), ys = proj.map((q) => q[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const W = 320, H = 220, pad = 16;
  const s = Math.min((W - 2 * pad) / Math.max(1e-6, maxX - minX), (H - 2 * pad) / Math.max(1e-6, maxY - minY));
  const tx = (q) => (pad + (q[0] - minX) * s).toFixed(1), ty = (q) => (pad + (q[1] - minY) * s).toFixed(1);
  const poly = (ring, z) => ring.map((p) => { const q = iso(p, z); return `${tx(q)},${ty(q)}`; }).join(" ");

  // Fiche claire : sol = papier teinté, gabarit en TERRE chaude (volume bâti, ressort sur le papier).
  let svg = `<polygon points="${poly(v.outline, 0)}" fill="#ECE6D8" stroke="#C9C0AE" stroke-width="1"/>`;
  const walls = [];                                    // murs triés arrière→avant (somme x+y)
  for (let i = 0; i < foot.length; i++) {
    const a = foot[i], b = foot[(i + 1) % foot.length];
    const quad = [iso(a, 0), iso(b, 0), iso(b, h), iso(a, h)].map((q) => `${tx(q)},${ty(q)}`).join(" ");
    const left = ((b[0] - a[0]) - (b[1] - a[1])) < 0;  // orientation écran → ombrage
    walls.push({ depth: a[0] + a[1] + b[0] + b[1], pts: quad, fill: left ? "#B07C36" : "#CDA05B" });
  }
  walls.sort((p, q) => p.depth - q.depth)
    .forEach((w) => { svg += `<polygon points="${w.pts}" fill="${w.fill}" stroke="#7A5E26" stroke-width="0.5"/>`; });
  svg += `<polygon points="${poly(foot, h)}" fill="#E3BE73" stroke="#9A7A33" stroke-width="1"/>`;

  return `<div class="v3d">
    <svg viewBox="0 0 ${W} ${H}" class="v3d-svg" role="img" aria-label="Gabarit constructible en 3D (indicatif)">${svg}</svg>
    <div class="v3d-figs">
      <span><b>${fmt(v.volume_m3)}</b><i>m³ · volume enveloppe</i></span>
      <span><b>${esc(v.niveaux || "—")}</b><i>${v.hauteur_m} m de haut</i></span>
      <span><b>${fmt(v.emprise_constructible_m2)}</b><i>m² · emprise au sol</i></span>
    </div>
    <p class="v3d-note">${esc(v.note || "")}</p>
  </div>`;
}

// Potentiel résiduel (Lot B) — « bâtie à N % de son potentiel » + SDP résiduelle.
function renderResiduel(r) {
  if (!r || !r.disponible) return "";
  const cls = r.sous_densite ? "sousdense" : "";
  const estim = r.estimation_sdp
    ? ` <span class="res-estim" title="hauteur du bâti BD TOPO non ingérée — niveaux existants supposés ${r.niveaux_existants}">SDP estimée</span>` : "";
  return `
    <div class="residuel ${cls}">
      <div class="res-head">
        <span class="res-eyebrow">Potentiel résiduel</span>
        ${r.sous_densite ? `<span class="res-badge">Sous-densité (&lt; ${r.sous_densite_seuil_pct} %)</span>` : ""}
      </div>
      <div class="res-cards">
        <div class="res-c"><span class="res-num">${r.taux_emprise_pct} %</span><span class="res-lbl">emprise au sol utilisée<br>(${fmt(r.emprise_batie_m2)} / ${fmt(r.emprise_constructible_m2)} m²)</span></div>
        <div class="res-c"><span class="res-num">${r.pct_potentiel} %</span><span class="res-lbl">bâtie de son potentiel SDP${estim}</span></div>
        <div class="res-c res-hi"><span class="res-num">~${fmt(r.sdp_residuelle_m2)} m²</span><span class="res-lbl">SDP résiduelle mobilisable<br>(max ${fmt(r.sdp_max_m2)} − existant ${fmt(r.sdp_existante_m2)})</span></div>
      </div>
      <p class="res-note">${esc(r.libelle)}</p>
    </div>`;
}

// 1.C — enregistrement des paramètres de bilan calibrés (par secteur) + recalcul.
async function saveBilanParams(box) {
  const secteur = box.dataset.secteur || "*";
  const msg = box.querySelector("#bp-msg");
  if (msg) msg.textContent = "Enregistrement…";
  const inputs = [...box.querySelectorAll("input[data-param]")];
  try {
    for (const i of inputs) {
      const v = i.value.trim() === "" ? null : Number(i.value);
      await fetch("/bilan/params", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secteur, param: i.dataset.param, value: v }) });
    }
  } catch { if (msg) msg.textContent = "Échec d'enregistrement."; return; }
  if (CURRENT_IDU) openSheet(CURRENT_IDU);   // re-fetch → bilan recalculé
}

// 1.C — bandeau bilan : DUR « non fiable » si un param critique n'a aucune valeur ; sinon SOUPLE
// « valeurs indicatives à affiner » si des params clés sont estimés (socle web, cf calibration).
function renderBilanBanner(b) {
  const nc = b.non_calibres_critiques || [];
  if (nc.length) {
    return `<div class="bilan-noncal">Bilan <b>à calibrer</b> — paramètres économiques à compléter : ${nc.map(esc).join(", ")}. Renseignez-les ci-dessous (secteur <b>${esc(b.secteur || "—")}</b>).</div>`;
  }
  const est = b.estimes_a_affiner || [];
  if (est.length) {
    return `<div class="bilan-estim">ℹ️ Charge foncière chiffrée sur un <b>socle de valeurs sourcées en ligne</b>. À affiner avec un promoteur : ${est.map(esc).join(", ")}.</div>`;
  }
  return "";
}

// 1.C — panneau de calibration des paramètres du bilan, par secteur (édition + persistance).
function renderBilanParams(b) {
  const params = b.params || [];
  if (!params.length) return "";
  const groups = {};
  params.forEach((p) => { (groups[p.groupe] = groups[p.groupe] || []).push(p); });
  const grpHtml = Object.entries(groups).map(([g, ps]) => `
    <div class="bp-grp"><div class="bp-grp-t">${esc(g)}</div>
      ${ps.map((p) => {
        const nonCal = p.is_placeholder;
        const badge = nonCal ? '<span class="bp-badge">non calibré</span>'
          : p.provenance === "estimee" ? '<span class="bp-badge bp-est">indicatif</span>'
          : p.provenance === "sourcee" ? '<span class="bp-badge bp-srcok">sourcée</span>' : "";
        const src = p.source && p.source !== "défaut" ? `<span class="bp-src">${esc(p.source)}</span>` : "";
        return `<label class="bp-row${nonCal ? " bp-nc" : ""}">
          <span class="bp-lbl">${esc(p.label)}${p.critique ? " ★" : ""} ${badge}${src}</span>
          <span class="bp-in"><input type="number" step="any" data-param="${esc(p.key)}" value="${p.value}"> <span class="bp-u">${esc(p.unite || "")}</span></span>
        </label>`;
      }).join("")}
    </div>`).join("");
  return `
    <details class="faisa-calc bilan-params" data-secteur="${esc(b.secteur || "*")}" data-idu="${esc(b._idu || "")}">
      <summary>Paramètres du bilan — calibration par secteur : <b>${esc(b.secteur || "—")}</b></summary>
      <p class="bp-note">Vic calibre ici (session terrain). Une valeur saisie s'applique à <b>tout le secteur</b> et recalcule le bilan. ★ = paramètre critique. Vider un champ = retour au défaut.</p>
      ${grpHtml}
      <div class="bp-actions"><button type="button" class="bp-save">💾 Enregistrer &amp; recalculer</button><span class="bp-msg" id="bp-msg"></span></div>
    </details>`;
}

function renderBilan(b) {
  if (!b) return "";
  const meur = (x) => (x == null ? "—" : (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(1) + " M€"
    : Math.abs(x) >= 1e3 ? Math.round(x / 1e3) + " k€" : Math.round(x) + " €"));
  const km = (m) => (m ? Math.round(m / 100) / 10 + " km" : "—");
  // Badge de fiabilité du PRIX DE SORTIE (pas du bilan complet) — toujours visible.
  const niveau = b.fiabilite || (b.fiable ? "fiable" : "insuffisant");
  const badgeTxt = { fiable: "Prix de marché fiable", fragile: "Prix de marché fragile", insuffisant: "Données insuffisantes" }[niveau] || niveau;
  const badge = `<span class="fiab fiab-${niveau}">${badgeTxt}</span>`;
  const bullets = (arr, cls, title) => (arr && arr.length)
    ? `<div class="fa-grp ${cls}"><span class="fa-grp-t">${title}</span><ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : "";

  const px = b.prix_dvf || {};
  const raisons = px.fiabilite_raisons || [];
  if (!b.fiable) {
    return `
    <section class="bilan bilan-nf">
      <div class="bilan-eyebrow">Bilan promoteur · potentiel économique ${badge}</div>
      <p class="bilan-msg">${esc(b.verdict)}</p>
      ${bullets(raisons, "warn", "Pourquoi le prix n'est pas fiable")}
      <p class="bilan-bandeau">⚠️ ${esc(b.bandeau)}</p>
    </section>`;
  }
  const ca = b.ca || {}, cf = b.charge_fonciere || {};
  const stepRows = (b.steps || []).map((s) => `
    <tr><td class="fs-lbl">${esc(s.label)}</td>
        <td class="fs-for">${esc(s.formule)}${s.valeur ? ` <b>= ${esc(s.valeur)}</b>` : ""}<span class="fs-src">${esc(s.source)}</span></td></tr>`).join("");
  // M6 — la méthode du prix, en clair (prix retenu, type, n, période, rayon, dispersion, écartés).
  const per = px.periode ? `${px.periode[0]}–${px.periode[1]}` : "—";
  const ecartes = [px.n_exclus ? `${px.n_exclus} aberrant(s)` : "", px.n_doublons ? `${px.n_doublons} doublon(s)` : ""].filter(Boolean).join(" · ") || "aucun";
  const methodRows = `
    <tr><td class="fs-lbl">Prix retenu</td><td class="fs-for"><b>${fmt(px.median)} €/m²</b> (Q1–Q3 ${fmt(px.q1)}–${fmt(px.q3)})<span class="fs-src">médiane DVF</span></td></tr>
    <tr><td class="fs-lbl">Type de biens</td><td class="fs-for">${esc(px.type_prix || "—")}${px.pct_appartement != null ? ` · ${px.pct_appartement}% appartements` : ""}<span class="fs-src">comparable visé : collectif</span></td></tr>
    <tr><td class="fs-lbl">Échantillon</td><td class="fs-for"><b>${px.n}</b> ventes · période ${per}<span class="fs-src">DVF géolocalisé (Etalab)</span></td></tr>
    <tr><td class="fs-lbl">Rayon utilisé</td><td class="fs-for">${px.commune_fallback ? "commune entière (peu de ventes proches)" : km(px.radius_m)}<span class="fs-src">500 → 1000 → 1500 m → commune</span></td></tr>
    <tr><td class="fs-lbl">Dispersion</td><td class="fs-for">min ${fmt(px.min)} / max ${fmt(px.max)} €/m²<span class="fs-src">après exclusion des aberrants</span></td></tr>
    <tr><td class="fs-lbl">Ventes écartées</td><td class="fs-for">${ecartes}<span class="fs-src">Tukey IQR + dédoublonnage</span></td></tr>`;

  const fragileBanner = niveau === "fragile"
    ? `<p class="bilan-fragile">⚠️ Prix de sortie <b>fragile</b> — ${esc(raisons.join(" ; ") || "échantillon DVF limité")}. Simulation à lire comme un <b>ordre de grandeur</b>, pas comme un bilan ferme.</p>`
    : "";

  // Transparence neuf/ancien (« Comparables de prix utilisés ») — n'altère pas le prix retenu.
  const cmp = px.comparables || {};
  const vefaCell = cmp.mediane_vefa != null
    ? `${fmt(cmp.mediane_vefa)} €/m² <span class="bc-n">(${cmp.n_vefa} ventes)</span>`
    : `<i>${esc(cmp.note || (cmp.n_vefa ? cmp.n_vefa + " vente(s), trop peu" : "aucune"))}</i>`;
  const ancienCell = cmp.mediane_ancien != null
    ? `${fmt(cmp.mediane_ancien)} €/m² <span class="bc-n">(${cmp.n_ancien} ventes)</span>`
    : `<i>${cmp.n_ancien ? cmp.n_ancien + " vente(s), trop peu" : "aucune"}</i>`;
  const ecartCell = cmp.exploitable
    ? `<b>${cmp.ecart_vefa_ancien_pct >= 0 ? "+" : ""}${cmp.ecart_vefa_ancien_pct} %</b> <span class="bc-n">(neuf vs ancien)</span>`
    : `<i>${esc(cmp.note || "écart non exploitable")}</i>`;
  // Raffinements marché : volatilité (dispersion) + tendance prudente (récent vs ancien).
  const TREND = { hausse: "↗ en hausse", baisse: "↘ en baisse", stable: "→ stable", indéterminée: "tendance indéterminée" };
  const volTxt = px.volatilite ? `dispersion ${esc(px.volatilite)}${px.volatilite_pct != null ? ` <span class="bc-n">(±${px.volatilite_pct} %)</span>` : ""}` : "";
  const trTxt = px.tendance && px.tendance !== "indéterminée"
    ? `${TREND[px.tendance] || esc(px.tendance)}${px.tendance_pct != null ? ` <span class="bc-n">(${px.tendance_pct > 0 ? "+" : ""}${px.tendance_pct} %)</span>` : ""}` : "";
  const dynCell = (volTxt || trTxt) ? `${volTxt}${volTxt && trTxt ? " · " : ""}${trTxt}` : "<i>non concluante</i>";
  const compBlock = (cmp.n_vefa == null && cmp.n_ancien == null) ? "" : `
      <div class="bilan-comp">
        <div class="bilan-comp-t">Comparables de prix utilisés</div>
        <dl class="bilan-comp-grid">
          <dt>Prix retenu</dt><dd><b>${fmt(px.median)} €/m²</b> · ${esc(px.type_prix || "")} · ${px.n} ventes · ${per} · ${px.commune_fallback ? "commune" : km(px.radius_m)}</dd>
          <dt>Médiane ancien</dt><dd>${ancienCell}</dd>
          <dt>Médiane neuf / VEFA</dt><dd>${vefaCell}</dd>
          <dt>Écart neuf vs ancien</dt><dd>${ecartCell}</dd>
          <dt>Dynamique marché</dt><dd>${dynCell}</dd>
          <dt>Fiabilité du prix</dt><dd>${badge}</dd>
        </dl>
        <p class="bilan-comp-note">Le prix au m² est une donnée de <b>marché</b> (DVF). Le bilan promoteur complet reste <b>indicatif</b> : travaux, marge, frais, TVA, VRD, stationnement et aléas sont à valider par un professionnel.</p>
      </div>`;

  return `
    <section class="bilan ${niveau === "fragile" ? "bilan-frag" : ""}">
      <div class="bilan-eyebrow">Bilan promoteur · potentiel économique ${badge}</div>
      <h3 class="bilan-verdict">${esc(b.verdict)}</h3>
      ${fragileBanner}
      ${renderBilanBanner(b)}
      <div class="faisa-cards bilan-cards">
        <div class="fc"><span class="fc-num" id="bilan-ca">${meur(ca.bas)}–${meur(ca.haut)}</span><span class="fc-lbl">Chiffre d'affaires potentiel</span></div>
        <div class="fc"><span class="fc-num">${fmt(px.median)} €/m²</span><span class="fc-lbl">Prix DVF médian · ${esc(px.type_prix || "")} (${px.n} ventes / ${px.commune_fallback ? "commune" : km(px.radius_m)})</span></div>
        <div class="fc fc-wide"><span class="fc-num" id="bilan-cf">${meur(cf.central)}<span class="fc-sub">~${fmt(cf.par_m2_terrain)} €/m² terrain</span></span><span class="fc-lbl">Charge foncière (médiane)</span></div>
      </div>
      ${renderLls(b.calc)}
      ${renderBilanParams(b)}
      ${compBlock}
      <details class="faisa-calc bilan-method">
        <summary>La méthode du prix, en clair — type, échantillon, rayon, ventes écartées</summary>
        <table class="faisa-steps">${methodRows}</table>
      </details>
      <details class="faisa-calc bilan-calc" open>
        <summary>Le calcul — prix DVF sourcé, hypothèses signalées</summary>
        <table class="faisa-steps">${stepRows}</table>
      </details>
      ${bullets(b.avertissements, "warn", "À surveiller")}
      ${bullets(b.hypotheses, "hyp", "Hypothèses (configurables)")}
      <p class="bilan-bandeau">⚠️ ${esc(b.bandeau)}</p>
    </section>`;
}

// Décision 3.b — secteur de mixité sociale : champs ÉDITABLES (quota % + prix LLS €/m²),
// recalcul INSTANTANÉ du CA pondéré et de la charge foncière, sans appel serveur.
// CA = surface vendable × [(1−pct)×prix DVF + pct×prix LLS] ; CF = CA×coef − coût constr.
// Tant que les PLACEHOLDERS (0) ne sont pas renseignés, le bilan affiché reste NON pondéré.
function renderLls(calc) {
  if (!calc || !calc.mixite) return "";
  const decl = !!calc.clause_declenchee;
  // Clause non déclenchée : info de pilotage, pas de pondération ni de champs.
  if (!decl) {
    return `
      <div class="bilan-lls bilan-lls-off">
        <div class="bilan-comp-t">Clause de mixité sociale — <b>non déclenchée</b></div>
        <span class="bilan-lls-note">${esc(calc.clause_detail || "programme sous les seuils")} — aucun quota de logements aidés sur ce programme. Dimensionner sous le seuil reste une stratégie possible.</span>
      </div>`;
  }
  const on = Number(calc.pct_lls) > 0 && Number(calc.prix_m2_lls) > 0;
  return `
      <div class="bilan-lls" id="bilan-lls"
           data-surf="${Number(calc.surf) || 0}" data-terrain="${Number(calc.terrain_m2) || 0}"
           data-q1="${Number(calc.q1) || 0}" data-med="${Number(calc.median) || 0}" data-q3="${Number(calc.q3) || 0}"
           data-coef="${Number(calc.coef) || 0}" data-ccbas="${Number(calc.cc_bas) || 0}" data-cchaut="${Number(calc.cc_haut) || 0}">
        <div class="bilan-comp-t">Clause de mixité sociale — <b>déclenchée</b> <span class="lls-crit">(${esc(calc.clause_critere || "")})</span></div>
        <label>quota logements aidés <input type="number" id="lls-pct" min="0" max="100" step="1" value="${Number(calc.pct_lls) || 0}"> %</label>
        <label>prix LLS <input type="number" id="lls-prix" min="0" step="50" value="${Number(calc.prix_m2_lls) || 0}"> €/m²</label>
        <span class="bilan-lls-note" id="lls-note">${on
          ? "pondération appliquée (prix LLS calibré)"
          : "impact non chiffré — prix LLS non calibré ; saisir le prix LLS pour pondérer le CA"}</span>
      </div>`;
}

document.addEventListener("input", (e) => {
  if (e.target.id !== "lls-pct" && e.target.id !== "lls-prix") return;
  const box = $("#bilan-lls"); if (!box) return;
  const d = box.dataset;
  const meur = (x) => (x == null ? "—" : (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(1) + " M€"
    : Math.abs(x) >= 1e3 ? Math.round(x / 1e3) + " k€" : Math.round(x) + " €"));
  const p = Math.min(1, Math.max(0, (Number($("#lls-pct").value) || 0) / 100));
  const lls = Number($("#lls-prix").value) || 0;
  const w = (px) => (p > 0 && lls > 0) ? (1 - p) * px + p * lls : px;
  const surf = +d.surf, coef = +d.coef;
  const caB = surf * w(+d.q1), caC = surf * w(+d.med), caH = surf * w(+d.q3);
  const cfB = caB * coef - +d.cchaut, cfC = caC * coef - (+d.ccbas + +d.cchaut) / 2, cfH = caH * coef - +d.ccbas;
  const caEl = $("#bilan-ca"), cfEl = $("#bilan-cf"), note = $("#lls-note");
  if (caEl) caEl.textContent = `${meur(caB)}–${meur(caH)}`;
  if (cfEl) cfEl.innerHTML = `${meur(cfC)}<span class="fc-sub">~${fmt(Math.round(+d.terrain ? cfC / +d.terrain : 0))} €/m² terrain</span>`;
  if (note) note.textContent = (p > 0 && lls > 0)
    ? `pondération appliquée : CA médian ${meur(caC)} · CF ${meur(Math.max(0, cfB))}–${meur(cfH)} (simulation locale, non enregistrée)`
    : "PLACEHOLDER non calibré → CA non pondéré ; saisir les deux valeurs pour simuler";
});

function renderAi(ai) {
  if (!ai || !Object.keys(ai).length) return "";
  const list = (arr) => (arr && arr.length) ? `<ul class="ai-list">${arr.map((x) => `<li>${esc(typeof x === "string" ? x : (x.detail || x.source || JSON.stringify(x)))}</li>`).join("")}</ul>` : "";
  return `
    <section class="ai">
      <h3 class="src-h">Analyse LA BUSE · IA</h3>
      <div class="ai-box">
        <div class="ai-line"><span class="ai-tag">Statut recommandé</span> ${esc(ai.recommended_status || "—")}
          · <span class="ai-tag">confiance</span> ${esc(ai.confidence_level || "—")}
          ${ai.opportunity_score_adjustment != null ? `· <span class="ai-tag">ajustement</span> ${ai.opportunity_score_adjustment > 0 ? "+" : ""}${esc(ai.opportunity_score_adjustment)}` : ""}</div>
        ${ai.reunion_specific_flags ? `<div class="ai-grp"><span class="ai-tag">Spécificités Réunion</span>${list(ai.reunion_specific_flags)}</div>` : ""}
        ${ai.blocking_or_risk_signals ? `<div class="ai-grp"><span class="ai-tag">Signaux bloquants / risque</span>${list(ai.blocking_or_risk_signals)}</div>` : ""}
        ${ai.must_check_before_showing_developer ? `<div class="ai-grp"><span class="ai-tag">À vérifier avant de démarcher</span>${list(ai.must_check_before_showing_developer)}</div>` : ""}
      </div>
    </section>`;
}

function wireSheetActions(idu) {
  // Voisines (assemblage) : un clic ouvre la fiche de la parcelle adjacente.
  document.querySelectorAll(".vz-item").forEach((el) =>
    el.addEventListener("click", () => focusParcel(el.dataset.idu)));
  document.querySelectorAll("[data-fb]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    await fetch("/feedback", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ idu, verdict: b.dataset.fb }) });
    b.textContent = "✓ Enregistré";
  }));
  const pb = $("[data-print]");
  if (pb) pb.addEventListener("click", () => { expandCascadeForPrint(); window.print(); });

  // Prospection MANUELLE : ajouter au pipeline / marquer « à identifier » / saisir un contact.
  // Audit J5 : le contact passe par un FORMULAIRE inline (plus de window.prompt « prototype »).
  const _ensureEntry = async () => {
    const pe = await (await fetch(`/pipeline/parcel/${encodeURIComponent(idu)}`)).json();
    if (pe.entry) return pe.entry;
    const r = await (await fetch("/pipeline", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ idu }) })).json();
    return r.entry;
  };
  document.querySelectorAll("[data-prosp]").forEach((b) => b.addEventListener("click", async (ev) => {
    ev.preventDefault();
    const act = b.dataset.prosp;
    if (act === "contact") {                    // ouvre/ferme le formulaire, sans réseau
      const f = $("#pp-form"); if (f) f.classList.toggle("hidden");
      return;
    }
    b.disabled = true;
    try {
      const entry = await _ensureEntry();
      if (act === "identify") {
        await fetch(`/pipeline/${entry.id}`, { method: "PATCH", headers: { "content-type": "application/json" },
          body: JSON.stringify({ status: "proprietaire_a_identifier", prospection: { statut_proprietaire: "a_identifier" } }) });
      }
      openSheet(idu);   // recharge la fiche
    } catch { b.disabled = false; }
  }));
  const ppForm = $("#pp-form");
  if (ppForm) {
    ppForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ppForm);
      const nom = (fd.get("contact_nom") || "").toString().trim();
      if (!nom) { ppForm.querySelector("[name=contact_nom]").focus(); return; }
      try {
        const entry = await _ensureEntry();
        await fetch(`/pipeline/${entry.id}`, { method: "PATCH", headers: { "content-type": "application/json" },
          body: JSON.stringify({ prospection: {
            statut_proprietaire: "identifie_manuellement", source_statut: "saisi_utilisateur",
            niveau_confiance: "moyen", contact_nom: nom,
            contact_telephone: (fd.get("contact_telephone") || "").toString().trim(),
            contact_email: (fd.get("contact_email") || "").toString().trim(),
          } }) });
        openSheet(idu);
      } catch { /* réseau : le formulaire reste ouvert, rien n'est perdu */ }
    });
    ppForm.querySelector(".pp-cancel").addEventListener("click", () => ppForm.classList.add("hidden"));
  }

  // « Suivre cette parcelle » → pipeline (statut Repérée par défaut ; si déjà suivie, affiche son statut)
  const fol = $("[data-follow]");
  if (fol) {
    fetch(`/pipeline/parcel/${encodeURIComponent(idu)}`).then((r) => r.json())
      .then((d) => { if (d.in_pipeline && d.entry) markFollowing(fol, d.entry.status); }).catch(() => {});
    fol.addEventListener("click", async () => {
      if (fol.classList.contains("on")) { closeSheet(); setView("kanban"); return; }   // déjà suivie → aller au pipeline
      try {
        const r = await (await fetch("/pipeline", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ idu }) })).json();
        if (r.entry) markFollowing(fol, r.entry.status);
      } catch { /* réseau */ }
    });
  }
}

// La cascade est repliée à l'écran ; on la déplie pour qu'elle figure dans le PDF.
function expandCascadeForPrint() { const d = document.querySelector(".cascade"); if (d) d.open = true; }

function closeSheet() {
  $("#sheet").classList.add("hidden");
  $("#sheet").setAttribute("aria-hidden", "true");
  $("#sheet").setAttribute("inert", "");              // a11y : fermée (hors écran), elle sort de l'ordre de tabulation
  $("#scrim").classList.add("hidden");
}

// Carte indisponible (réseau) : message lisible dans l'encart d'état vide, jamais d'écran mort muet.
function showMapError() {
  const empty = $("#map-empty");
  if (!empty) return;
  empty.classList.remove("hidden");
  const t = empty.querySelector(".me-title"), s = empty.querySelector(".me-sub");
  if (t) t.textContent = "Carte momentanément indisponible";
  if (s) s.textContent = "Le fond parcellaire n'a pas pu être chargé (réseau). Réessayez dans un instant.";
}

// ───────────────────────── Démo guidée (Phase 3) ─────────────────────────
// Raccourci de présentation : liste les parcelles de démo VALIDÉES (rôle + statut live)
// et ouvre leur fiche d'un clic. Ne masque aucune donnée réelle.
function openDemo() {
  const ov = $("#demo-overlay");
  ov.classList.remove("hidden"); ov.setAttribute("aria-hidden", "false");
  $("#demo-body").innerHTML = `<div class="loading">Chargement du parcours…</div>`;
  // Parcours (/demo) + état complet (/demo-status) en parallèle — l'état n'est jamais masqué.
  Promise.all([
    fetch("/demo").then((r) => r.json()),
    fetch("/demo-status").then((r) => r.json()).catch(() => null),
  ]).then(([d, st]) => {
    $("#demo-body").innerHTML = renderDemoStatus(st) + renderDemoPanel(d);
    document.querySelectorAll("#demo-body .dp-item").forEach((el) =>
      el.addEventListener("click", () => { closeDemo(); focusParcel(el.dataset.idu); }));
    const go = $("#demo-body [data-demo-go]");
    if (go) go.addEventListener("click", () => { closeDemo(); setView("shortlist"); });
  }).catch(() => { $("#demo-body").innerHTML = `<div class="loading">Démo momentanément indisponible.</div>`; });
}

// État de la démo (panneau admin) : healthcheck, couches, warm — avec la COMMANDE à lancer
// si quelque chose manque. On affiche l'erreur, on ne la cache jamais.
function renderDemoStatus(st) {
  if (!st) return `<div class="ds-box ds-bad">État de la démo indisponible (/demo-status injoignable).</div>`;
  const byName = {}; (st.healthcheck && st.healthcheck.checks || []).forEach((c) => { byName[c.name] = c.ok; });
  const items = [
    ["PPR", byName["PPR"]], ["SAR", byName["SAR"]], ["DVF geo-dvf", byName["DVF geo-dvf"]],
    ["OSM", byName["OSM faux positifs"]], ["Déclassement", byName["Déclassement appliqué"]],
    ["Top 20 propre", byName["Top 20 sans faux positif évident"]],
    ["Pipeline", byName["Module prospection"]], ["Exports", byName["Exports HTML/Markdown"]],
    ["Parcelles démo", st.demo && st.demo.all_conform],
    [`Cache chaud ${st.warm ? st.warm.warmed + "/" + st.warm.total : ""}`, st.warm && st.warm.done],
  ];
  const dots = items.map(([lbl, ok]) =>
    `<span class="ds-item ${ok ? "ok" : "ko"}">${ok ? "✓" : "✗"} ${esc(lbl)}</span>`).join("");
  const when = st.checked_at ? `<span class="ds-when">vérifié ${fmtDateTime(st.checked_at)}</span>` : "";
  if (st.ready_for_demo) {
    return `<div class="ds-box ds-ok"><div class="ds-h"><b>✅ Démo prête</b> ${when}</div><div class="ds-grid">${dots}</div></div>`;
  }
  // Commandes techniques : repliées dans un détail « développeur », jamais au premier plan.
  const actions = (st.actions || []).map((a) => `<code>${esc(a)}</code>`).join("");
  return `<div class="ds-box ds-bad">
    <div class="ds-h"><b>Démo à préparer</b> ${when}</div>
    <p class="ds-msg">Une vérification n'est pas passée. La démo reste présentable, mais relancez la préparation pour un parcours impeccable.</p>
    <div class="ds-grid">${dots}</div>
    <details class="ds-dev"><summary>Préparer la démo — commandes (développeur)</summary>
      <div class="ds-actions">${actions || "<code>labuse doctor</code>"}</div></details></div>`;
}
function closeDemo() {
  const ov = $("#demo-overlay");
  ov.classList.add("hidden"); ov.setAttribute("aria-hidden", "true");
}
function renderDemoPanel(d) {
  const parcels = d.parcels || [];
  const byAct = {};
  parcels.forEach((p) => { (byAct[p.attendu] = byAct[p.attendu] || []).push(p); });
  const acts = DEMO_ACTS.filter((a) => (byAct[a.key] || []).length).map((a) => `
    <section class="dp-act">
      <header class="dp-act-h"><span class="dp-act-n">${a.n}</span>
        <span class="dp-act-tt"><span class="dp-act-t">${esc(a.title)}</span><span class="dp-act-s">${esc(a.sub)}</span></span>
        <span class="dp-act-c">${byAct[a.key].length}</span></header>
      <div class="dp-list">${byAct[a.key].map(demoItem).join("")}</div>
    </section>`).join("");
  const warn = d.all_conform ? "" :
    `<p class="dp-warn">⚠ Une parcelle a dérivé (statut ≠ attendu) — voir « Préparer la démo » ci-dessus.</p>`;
  const n = parcels.length;
  return `
    <p class="dp-intro"><b>${esc(d.commune || "Saint-Paul")}</b> — de l'opportunité à la décision en 5 minutes.</p>
    <div class="dp-path">
      <button class="dp-cta" data-demo-go="shortlist" type="button">🎯 Ouvrir la shortlist du jour</button>
      <span class="dp-path-s">les ${n} parcelles ci-dessous montrent comment LA BUSE trie le vrai du faux.</span>
    </div>
    ${warn}
    ${acts}
    <p class="dp-close-note">▶ Chaque sujet retenu part au <b>pipeline de prospection</b> — notes, relances, propriétaire.</p>`;
}
// Parcours en 3 actes : faire ressortir → écarter (la rigueur) → instruire. Dérivé du statut
// ATTENDU de chaque parcelle de démo (aucune donnée ajoutée) — l'histoire à raconter au promoteur.
const DEMO_ACTS = [
  { key: "opportunite", n: "①", title: "Ce que LA BUSE fait ressortir",
    sub: "Opportunités foncières vacantes ou sous-denses — dont un cas d'assemblage." },
  { key: "faux_positif_probable", n: "②", title: "Ce qu'elle écarte — la rigueur",
    sub: "Faux bons plans corrigés et tracés (résidence déjà bâtie, parking, pente). La crédibilité du radar." },
  { key: "a_creuser", n: "③", title: "Les pistes à instruire",
    sub: "Sujets à creuser avant démarche : périmètre PPR, densification SAR." },
];
function demoItem(p) {
  const drift = p.conforme ? "" :
    `<span class="dp-drift" title="statut live ≠ attendu (${esc(p.attendu)})">⚠</span>`;
  return `<button class="dp-item" data-idu="${esc(p.idu)}">
    <span class="dp-num">${p.ordre}</span>
    <span class="dp-main">
      <span class="dp-role">${esc(p.role)}</span>
      <span class="dp-montre">${esc(p.montre)}</span>
    </span>
    <span class="dp-meta"><span class="chip ${p.status || "inconnu"}">${STATUS_LABEL[p.status] || "—"}</span>${drift}</span>
  </button>`;
}

// ───────────────────────── Pipeline / Kanban (T2) ─────────────────────────
async function loadMeta() {
  try { KANBAN_META = await (await fetch("/pipeline/meta")).json(); }
  catch { KANBAN_META = { columns: [], priorities: [], defaults: {} }; }
}
const colLabel = (k) => (KANBAN_META && KANBAN_META.columns.find((c) => c.key === k) || {}).label || k;
const prioLabel = (k) => (KANBAN_META && KANBAN_META.priorities.find((p) => p.key === k) || {}).label || k;
// Accent d'entonnoir piloté par la config (`tone`) — gold = progression, pas une couleur de verdict.
const TONE_ACCENT = { cold: "var(--muted)", warm: "var(--gold-soft)", hot: "var(--gold)", reject: "var(--exclue)" };
const toneAccent = (t) => TONE_ACCENT[t] || "var(--line)";
const prioRank = (k) => { const i = (KANBAN_META && KANBAN_META.priorities || []).findIndex((p) => p.key === k); return i < 0 ? 99 : i; };

// Rappel : état calculé côté client (échu / proche ≤ 3 j / —) — aucune dépendance backend.
function reminderState(dateStr) {
  if (!dateStr) return { state: "", days: null };
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const days = Math.round((new Date(dateStr + "T00:00:00") - today) / 86400000);
  if (days < 0) return { state: "overdue", days };
  if (days <= 3) return { state: "soon", days };
  return { state: "", days };
}
// Échéance d'action = la date la plus PROCHE entre le rappel (reminder_date) et la date de
// prochaine action saisie en prospection — pour un « à faire » unifié et actionnable.
function echeance(e) {
  const a = e.reminder_date || null;
  const b = (e.prospection && e.prospection.date_prochaine_action) || null;
  return (a && b) ? (a < b ? a : b) : (a || b);   // ISO yyyy-mm-dd → comparaison lexicale = chronologique
}
const isDue = (e) => reminderState(echeance(e)).state !== "";

async function fetchPipeline() {
  try { PIPELINE = await (await fetch("/pipeline")).json(); } catch { PIPELINE = []; }
  updateReminderBadges();
  updateQuickCounts();
}
function updateReminderBadges() {
  const overdue = PIPELINE.filter((e) => reminderState(echeance(e)).state === "overdue").length;
  document.querySelectorAll(".kb-badge").forEach((b) => { b.textContent = overdue; b.classList.toggle("hidden", overdue === 0); });
  const due = PIPELINE.filter(isDue).length;
  const rn = $("#kb-remn"); if (rn) rn.textContent = due;
  const rf = $("#kb-remfilter"); if (rf) rf.classList.toggle("has-due", due > 0);
}

async function loadKanban() {
  if (!KANBAN_META) await loadMeta();
  await fetchPipeline();
  renderKanban();
}

// Comparateur selon le tri courant (score / priorité / rappel) — le statut n'entre pas.
function sortKey(e) {
  const opp = e.verdict && e.verdict.opportunity_score != null ? e.verdict.opportunity_score : -1;
  const ech = echeance(e);
  const rem = ech ? Date.parse(ech) : Number.POSITIVE_INFINITY;
  if (KB_SORT === "priority") return [prioRank(e.priority), -opp];
  if (KB_SORT === "reminder") return [rem, -opp];
  return [-opp, prioRank(e.priority)];
}
function cmpKey(a, b) { for (let i = 0; i < a.length; i++) { if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1; } return 0; }

function kbCard(e) {
  const v = e.verdict || {};
  const st = v.status || "inconnu";
  const cols = (KANBAN_META.columns || []);
  const prios = (KANBAN_META.priorities || []);
  const opts = cols.map((c) => `<option value="${c.key}" ${c.key === e.status ? "selected" : ""}>${esc(c.label)}</option>`).join("");
  const prioOpts = prios.map((p) => `<option value="${p.key}" ${p.key === e.priority ? "selected" : ""}>${esc(p.label)}</option>`).join("");
  const surf = e.parcel && e.parcel.surface_m2 ? fmt(Math.round(e.parcel.surface_m2)) + " m²" : "—";
  const ech = echeance(e);
  const rs = reminderState(ech);
  let remHtml = "";
  if (ech) {
    const lbl = rs.state === "overdue" ? `en retard (${esc(ech)})`
      : rs.state === "soon" ? (rs.days === 0 ? "aujourd'hui" : `dans ${rs.days} j (${esc(ech)})`)
        : esc(ech);
    remHtml = `<div class="kb-rem ${rs.state}">⏰ échéance ${lbl}</div>`;
  }
  return `
    <div class="kb-card st-${st}${rs.state ? " rem-" + rs.state : ""}" data-id="${e.id}" data-idu="${esc(e.idu)}" draggable="true">
      <div class="kb-card-top">
        <span class="kb-idu">${esc(e.idu)}</span>
        <span class="chip ${st}">${STATUS_LABEL[st] || "?"}</span>
      </div>
      <div class="kb-sub">
        <span class="kb-opp">${v.opportunity_score ?? "—"}</span> opp · <span>${surf}</span>
        <span class="kb-prio prio-${esc(e.priority)}">${esc(prioLabel(e.priority))}</span>
      </div>
      ${remHtml}
      ${e.proprietaire_label ? `<div class="kb-prosp">👤 ${esc(e.proprietaire_label)}${(e.prospection && e.prospection.prochaine_action) ? ` · ▶ ${esc(e.prospection.prochaine_action)}` : ""}${(e.prospection && e.prospection.responsable_interne) ? ` · ${esc(e.prospection.responsable_interne)}` : ""}</div>` : ""}
      ${e.notes ? `<div class="kb-notes">${esc(e.notes)}</div>` : ""}
      <div class="kb-foot">
        <select class="kb-move" title="Changer de colonne (alternative au glisser-déposer)">${opts}</select>
        <button class="kb-iconbtn kb-edit" title="Éditer">✎</button>
        <button class="kb-iconbtn kb-del" title="Retirer du pipeline">🗑</button>
      </div>
      <div class="kb-editor hidden">
        <textarea class="kb-notes-in" placeholder="Notes libres…">${esc(e.notes || "")}</textarea>
        <div class="kb-editor-row">
          <select class="kb-prio-in" title="Priorité">${prioOpts}</select>
          <input type="date" class="kb-rem-in" title="Date de rappel" value="${esc(e.reminder_date || "")}">
        </div>
        <div class="kb-editor-row">
          <select class="kb-pp-statut" title="Statut propriétaire">${Object.entries(PP_STATUT).map(([k, l]) => `<option value="${k}"${((e.prospection || {}).statut_proprietaire || "inconnu") === k ? " selected" : ""}>${l}</option>`).join("")}</select>
          <input class="kb-pp-resp" placeholder="Responsable" value="${esc((e.prospection || {}).responsable_interne || "")}">
        </div>
        <div class="kb-editor-row">
          <input class="kb-pp-action" placeholder="Prochaine action (manuelle)…" value="${esc((e.prospection || {}).prochaine_action || "")}">
          <input type="date" class="kb-pp-date" title="Échéance de la prochaine action (alimente « à faire »)" value="${esc((e.prospection || {}).date_prochaine_action || "")}">
        </div>
        <div class="kb-editor-row">
          <button class="kb-save">Enregistrer</button>
          <button class="kb-cancel">Annuler</button>
        </div>
      </div>
    </div>`;
}

function renderKanban() {
  const cols = KANBAN_META.columns || [];
  let entries = PIPELINE.slice();
  if (KB_REMINDER_ONLY) entries = entries.filter(isDue);
  entries.sort((a, b) => cmpKey(sortKey(a), sortKey(b)));
  const total = PIPELINE.length;
  // Résumé CRM : suivies · propriétaires à identifier · relances prévues.
  const aIdentifier = PIPELINE.filter((e) => {
    const sp = (e.prospection || {}).statut_proprietaire;
    return (!sp || sp === "a_identifier" || sp === "inconnu") && !e.has_manual_contact;
  }).length;
  const relances = PIPELINE.filter((e) => (e.prospection || {}).date_prochaine_action).length;
  $("#kb-count").textContent = total
    ? `${total} parcelle${total > 1 ? "s" : ""} suivie${total > 1 ? "s" : ""} · ${aIdentifier} propriétaire${aIdentifier > 1 ? "s" : ""} à identifier · ${relances} relance${relances > 1 ? "s" : ""} prévue${relances > 1 ? "s" : ""}`
    : "Aucune parcelle suivie";
  const byCol = {}; cols.forEach((c) => { byCol[c.key] = []; });
  entries.forEach((e) => { (byCol[e.status] = byCol[e.status] || []).push(e); });
  // État vide pédagogique : on explique comment démarrer une prospection.
  const emptyHint = total === 0
    ? `<div class="kb-empty-hint">Aucune parcelle suivie pour l'instant.<br>Ouvrez une fiche parcelle, cliquez <b>« + Suivre cette parcelle »</b>, puis passez-la en <b>« Propriétaire à identifier »</b> et notez votre prochaine action pour démarrer votre prospection.</div>`
    : "";
  $("#kb-board").innerHTML = emptyHint + cols.map((c) => `
    <div class="kb-col tone-${esc(c.tone || "none")}" data-col="${c.key}" style="--col-accent: ${toneAccent(c.tone)}">
      <div class="kb-col-head"><span class="kb-col-title">${esc(c.label)}</span><span class="kb-col-n">${(byCol[c.key] || []).length}</span></div>
      <div class="kb-cards">${(byCol[c.key] || []).map(kbCard).join("") || '<div class="kb-empty">Aucune parcelle à ce stade<span>les parcelles qualifiées apparaîtront ici</span></div>'}</div>
    </div>`).join("");
  wireKanban();
}

function patchEntry(id, body) {
  return fetch(`/pipeline/${id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

// Déplacement (drag OU sélecteur) : maj mémoire + DOM (carte glissée vers la colonne, position triée)
// + persistance via PATCH ; resync si le serveur refuse. Pas de re-render global → fluide, scroll préservé.
async function moveEntry(id, status) {
  const e = PIPELINE.find((x) => x.id === id);
  if (!e || e.status === status) return;
  const prev = e.status;
  e.status = status;
  const card = document.querySelector(`#kb-board .kb-card[data-id="${id}"]`);
  if (card) {
    const sel = card.querySelector(".kb-move"); if (sel) sel.value = status;
    placeCardInColumn(card, status);
    updateColumnCounts();
  } else { renderKanban(); }
  try {
    const r = await patchEntry(id, { status });
    if (!r.ok) { e.status = prev; await loadKanban(); }
  } catch { e.status = prev; await loadKanban(); }
}

function placeCardInColumn(card, colKey) {
  const container = document.querySelector(`#kb-board .kb-col[data-col="${colKey}"] .kb-cards`);
  if (!container) return;
  const empty = container.querySelector(".kb-empty"); if (empty) empty.remove();
  const me = PIPELINE.find((x) => x.id === +card.dataset.id);
  let before = null;
  container.querySelectorAll(".kb-card").forEach((o) => {
    if (before || o === card) return;
    const oe = PIPELINE.find((x) => x.id === +o.dataset.id);
    if (oe && cmpKey(sortKey(me), sortKey(oe)) < 0) before = o;
  });
  card.classList.add("just-moved");
  container.insertBefore(card, before);
  setTimeout(() => card.classList.remove("just-moved"), 260);
}

function updateColumnCounts() {
  document.querySelectorAll("#kb-board .kb-col").forEach((col) => {
    const cont = col.querySelector(".kb-cards");
    const cards = cont.querySelectorAll(".kb-card");
    const n = col.querySelector(".kb-col-n"); if (n) n.textContent = cards.length;
    if (cards.length === 0 && !cont.querySelector(".kb-empty")) {
      const d = document.createElement("div"); d.className = "kb-empty"; d.textContent = "—"; cont.appendChild(d);
    }
  });
}

function wireKanban() {
  document.querySelectorAll("#kb-board .kb-card").forEach((card) => {
    const id = +card.dataset.id;
    const idu = card.dataset.idu;
    card.addEventListener("click", (ev) => {
      if (ev.target.closest(".kb-foot, .kb-editor")) return;
      openSheet(idu);
    });
    card.addEventListener("dragstart", (ev) => {
      if (ev.target.closest(".kb-foot, .kb-editor")) { ev.preventDefault(); return; }
      DRAG_ID = id; card.classList.add("dragging");
      ev.dataTransfer.effectAllowed = "move";
      try { ev.dataTransfer.setData("text/plain", String(id)); } catch { /* compat */ }
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      document.querySelectorAll(".kb-col.drag-over").forEach((c) => c.classList.remove("drag-over"));
      DRAG_ID = null;
    });
    card.querySelector(".kb-move").addEventListener("change", (ev) => moveEntry(id, ev.target.value));
    card.querySelector(".kb-edit").addEventListener("click", () => card.querySelector(".kb-editor").classList.toggle("hidden"));
    card.querySelector(".kb-cancel").addEventListener("click", () => card.querySelector(".kb-editor").classList.add("hidden"));
    card.querySelector(".kb-del").addEventListener("click", async () => {
      await fetch(`/pipeline/${id}`, { method: "DELETE" }); await loadKanban();
    });
    card.querySelector(".kb-save").addEventListener("click", async () => {
      await patchEntry(id, {
        notes: card.querySelector(".kb-notes-in").value,
        priority: card.querySelector(".kb-prio-in").value,
        reminder_date: card.querySelector(".kb-rem-in").value,
        prospection: {
          statut_proprietaire: card.querySelector(".kb-pp-statut").value,
          responsable_interne: card.querySelector(".kb-pp-resp").value,
          prochaine_action: card.querySelector(".kb-pp-action").value,
          date_prochaine_action: card.querySelector(".kb-pp-date").value,
        },
      });
      await loadKanban();
    });
  });
  // Colonnes = zones de dépôt (drag & drop, desktop).
  document.querySelectorAll("#kb-board .kb-col").forEach((col) => {
    col.addEventListener("dragover", (ev) => { ev.preventDefault(); ev.dataTransfer.dropEffect = "move"; col.classList.add("drag-over"); });
    col.addEventListener("dragleave", (ev) => { if (!col.contains(ev.relatedTarget)) col.classList.remove("drag-over"); });
    col.addEventListener("drop", (ev) => {
      ev.preventDefault(); col.classList.remove("drag-over");
      if (DRAG_ID != null) moveEntry(DRAG_ID, col.dataset.col);
      DRAG_ID = null;
    });
  });
}

// Tri + filtre « à rappeler » (en-tête du board).
function wireKanbanControls() {
  const sortSel = $("#kb-sort");
  if (sortSel) sortSel.addEventListener("change", () => { KB_SORT = sortSel.value; renderKanban(); });
  const rf = $("#kb-remfilter");
  if (rf) rf.addEventListener("click", () => { KB_REMINDER_ONLY = !KB_REMINDER_ONLY; rf.setAttribute("aria-pressed", String(KB_REMINDER_ONLY)); renderKanban(); });
}

function markFollowing(btn, statusKey) {
  btn.classList.add("on");
  btn.textContent = `✓ Dans le pipeline · ${colLabel(statusKey)}`;
}

// ───────────────────────── Shortlist promoteur ─────────────────────────
// « Les sujets à traiter aujourd'hui » : priorisation métier (serveur), pas le score brut.
let SHORTLIST = [];
async function loadShortlist() {
  const board = $("#sl-board"); if (!board) return;
  const limit = ($("#sl-limit") && $("#sl-limit").value) || 5;
  board.innerHTML = `<div class="sl-loading">Calcul des priorités foncières…</div>`;
  let data = null;
  try { data = await (await fetch(`/shortlist?commune=${encodeURIComponent(COMMUNE)}&limit=${limit}`)).json(); }
  catch { data = null; }
  if (!data || !Array.isArray(data.sujets)) {
    board.innerHTML = `<div class="sl-empty"><div class="sl-empty-t">Shortlist indisponible</div>
      <div class="sl-empty-s">Le calcul des priorités n'a pas abouti. Réessayez dans un instant.</div></div>`;
    return;
  }
  SHORTLIST = data.sujets;
  const c = $("#sl-count");
  if (c) c.textContent = data.candidates_total != null
    ? `${data.sujets.length} sujet${data.sujets.length > 1 ? "s" : ""} · sur ${fmt(data.candidates_total)} parcelles actionnables`
    : "";
  if (!data.sujets.length) {
    board.innerHTML = `<div class="sl-empty"><div class="sl-empty-t">Aucun sujet prioritaire</div>
      <div class="sl-empty-s">Aucune parcelle « opportunité » ou « à creuser » sur ${esc(COMMUNE)} pour l'instant.</div></div>`;
    return;
  }
  renderShortlist(data.sujets);
}

const BADGE_CLASS = {
  "Priorité du jour": "b-prio", "Assemblage à vérifier": "b-asm", "À appeler": "b-call",
  "À surveiller": "b-watch", "Risque fort": "b-risk", "Données à consolider": "b-cons",
};
function _caRange(ca) {
  if (!ca) return null;
  return ca.bas !== ca.haut ? `${_eurK(ca.bas)} – ${_eurK(ca.haut)}` : _eurK(ca.central ?? ca.bas);
}
function renderShortlist(sujets) {
  const board = $("#sl-board");
  board.innerHTML = sujets.map((s) => {
    const st = s.verdict_status || "inconnu";
    const asm = s.potentiel_assemblage || {};
    const ca = _caRange(s.ca);
    const cf = s.charge_fonciere;
    const prop = s.proprietaire || {};
    const conf = s.confiance || {};
    const badges = (s.badges || []).map((b) => `<span class="sl-badge ${BADGE_CLASS[b] || ""}">${esc(b)}</span>`).join("");
    const fiabMarche = s.fiabilite_marche
      ? `<span class="sl-fiab fiab-${esc(s.fiabilite_marche)}">marché ${esc(s.fiabilite_marche)}</span>` : "";
    return `
    <article class="sl-card st-${st}" data-idu="${esc(s.idu)}">
      <div class="sl-rang">${s.rang}</div>
      <div class="sl-main">
        <div class="sl-top">
          <span class="sl-idu">${esc(s.idu)}</span>
          <span class="chip ${st}">${STATUS_LABEL[st] || "?"}</span>
          <span class="sl-score">${s.score ?? "—"}<small>opp</small></span>
          <span class="sl-surf">${fmt(Math.round(s.surface_m2 || 0))} m²</span>
        </div>
        ${badges ? `<div class="sl-badges">${badges}</div>` : ""}
        <div class="sl-grid">
          <div class="sl-cell"><span class="sl-k">Potentiel seul</span><span class="sl-v">${esc(s.potentiel_seul || "non disponible")}</span></div>
          <div class="sl-cell"><span class="sl-k">Assemblage</span><span class="sl-v">${asm.possible
            ? `${asm.n_interessantes || "?"} contiguës · ~${fmt(Math.round(asm.surface_cumulee_m2 || 0))} m²`
            : "à vérifier / non détecté"}</span></div>
          <div class="sl-cell"><span class="sl-k">CA potentiel</span><span class="sl-v">${ca || "non chiffré"} ${fiabMarche}</span></div>
          <div class="sl-cell"><span class="sl-k">Charge foncière cible</span><span class="sl-v">${cf
            ? `${_eurK(cf.central)}${cf.par_m2_terrain ? ` · ${cf.par_m2_terrain} €/m² terrain` : ""}` : "non chiffrée"}</span></div>
          <div class="sl-cell"><span class="sl-k">Blocage principal</span><span class="sl-v">${esc(s.blocage_principal || "—")}</span></div>
          <div class="sl-cell"><span class="sl-k">Propriétaire</span><span class="sl-v">${esc(prop.statut || prop.famille || "à identifier")}${prop.in_pipeline ? " · suivi" : ""}</span></div>
        </div>
        <div class="sl-foot">
          <span class="sl-action">▶ ${esc(s.prochaine_action || "À qualifier")} <em>· confiance ${esc(conf.label || "—")}</em></span>
          <span class="sl-btns">
            <button class="btn sl-open" data-idu="${esc(s.idu)}">Ouvrir la fiche</button>
            <button class="btn cta-primary sl-add" data-idu="${esc(s.idu)}"${prop.in_pipeline ? " disabled" : ""}>${prop.in_pipeline ? "✓ Au pipeline" : "+ Pipeline"}</button>
          </span>
        </div>
      </div>
    </article>`;
  }).join("");
  board.querySelectorAll(".sl-open").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); openSheet(b.dataset.idu); }));
  board.querySelectorAll(".sl-card").forEach((c) => c.addEventListener("click", (e) => { if (!e.target.closest("button")) openSheet(c.dataset.idu); }));
  board.querySelectorAll(".sl-add").forEach((b) => b.addEventListener("click", async (e) => {
    e.stopPropagation();
    b.disabled = true; b.textContent = "…";
    try {
      const r = await (await fetch("/pipeline", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ idu: b.dataset.idu }) })).json();
      b.textContent = r && (r.ok || r.id) ? "✓ Au pipeline" : "+ Pipeline";
      if (!(r && (r.ok || r.id))) b.disabled = false;
      fetchPipeline();
    } catch { b.textContent = "+ Pipeline"; b.disabled = false; }
  }));
}

// ───────────────────────── Audit pull (Lot A) ─────────────────────────
// Auditer un terrain à la demande : référence cadastrale, adresse (BAN) ou polygone dessiné.
// Tout converge vers POST /audit/* → ingestion 'audit' + cascade → on ouvre la fiche produite.
// Réf. cadastrale : IDU COMPLET (INSEE 5 + préfixe 3 + section + n°) OU forme courte (section + n°).
// Ex. « 97415000BP0571 », « 97415 000 BP 0571 », « BV 912 », « bv912 », « BP0571 ».
// g1 = INSEE (option.), g2 = section, g3 = numéro.
const AUDIT_REF_RX = /^(?:(\d{5})\s*\d{3}\s*)?([A-Za-z]{1,2})\s*0*(\d{1,4})$/;

function auditMsg(text, busy = false) {
  const el = $("#audit-msg");
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("busy", !!busy);
  el.classList.toggle("err", !!text && !busy && !/en cours|analyse/i.test(text));
}

async function reloadParcelLayer() {
  // Rafraîchit la couche carte/liste pour faire apparaître la parcelle auditée.
  try {
    const fc = await (await fetch(`/map/parcels.geojson?commune=${encodeURIComponent(COMMUNE)}`)).json();
    FEATURES = fc.features || [];
    setSliderBounds();
    applyFilters();
  } catch { /* la fiche s'ouvre quand même ; la carte se resynchronisera au prochain chargement */ }
  loadStats();
}

async function runAudit(url, body) {
  auditMsg("Analyse en cours… (cadastre + cascade)", true);
  let res;
  try {
    res = await (await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    })).json();
  } catch { auditMsg("Service d'audit indisponible — réessayez."); return; }
  if (!res || !res.ok) { auditMsg((res && res.message) || "Audit impossible."); return; }
  auditMsg(res.cached ? "Déjà au référentiel — fiche ouverte." : `Parcelle ajoutée (${res.n}) — fiche ouverte.`);
  if (!res.cached) await reloadParcelLayer();
  openSheet(res.idu);
  setTimeout(() => auditMsg(""), 4000);
}

function submitAudit(e) {
  if (e) e.preventDefault();
  const q = ($("#audit-q").value || "").trim();
  if (q.length < 3) { auditMsg("Saisissez une adresse ou une référence (ex. BV 912 ou 97415000BP0571)."); return; }
  const m = AUDIT_REF_RX.exec(q);
  if (m) {
    const body = { section: m[2].toUpperCase(), numero: m[3] };
    if (m[1]) body.code_insee = m[1];   // IDU complet → on transmet l'INSEE (contrôle commune)
    return runAudit("/audit/reference", body);
  }
  return runAudit("/audit/adresse", { q });
}

// Dessin de polygone (Leaflet natif : clic = sommet, double-clic = terminer).
// Deux usages (DRAW_MODE) : 'audit' (auditer un terrain) et 'zone' (zone de veille 3.C).
let DRAW_PTS = [], DRAW_LAYER = null, DRAWING = false, DRAW_MODE = "audit", DRAW_ZONE_NAME = "";
function startDraw(mode = "audit", zoneName = "") {
  if (!map) { auditMsg("Carte indisponible."); return; }
  if (DRAWING) return finishDraw();
  DRAWING = true; DRAW_PTS = []; DRAW_MODE = mode; DRAW_ZONE_NAME = zoneName;
  if (DRAW_LAYER) { map.removeLayer(DRAW_LAYER); DRAW_LAYER = null; }
  const btn = mode === "zone" ? $("#watch-add") : $("#audit-draw");
  if (btn) { btn.classList.add("on"); btn.textContent = "✓ Terminer le tracé"; }
  auditMsg(mode === "zone"
    ? `Zone « ${zoneName} » : cliquez les sommets, double-clic pour boucler.`
    : "Cliquez pour poser les sommets ; double-clic ou « Terminer » pour boucler.");
  map.doubleClickZoom.disable();
  map.on("click", onDrawClick);
  map.on("dblclick", finishDraw);
}
function onDrawClick(e) {
  DRAW_PTS.push([e.latlng.lng, e.latlng.lat]);
  if (DRAW_LAYER) map.removeLayer(DRAW_LAYER);
  DRAW_LAYER = L.polygon(DRAW_PTS.map(([lng, lat]) => [lat, lng]),
    { color: "#D6B36A", weight: 2, dashArray: "4", fillOpacity: 0.08 }).addTo(map);
}
async function finishDraw(e) {
  if (e && e.originalEvent) L.DomEvent.stop(e);
  map.off("click", onDrawClick); map.off("dblclick", finishDraw);
  setTimeout(() => map.doubleClickZoom.enable(), 300);
  DRAWING = false;
  const mode = DRAW_MODE;
  if (mode === "zone") { const b = $("#watch-add"); if (b) { b.classList.remove("on"); b.textContent = "+ Zone"; } }
  else { const b = $("#audit-draw"); if (b) { b.classList.remove("on"); b.textContent = "Dessiner une zone sur la carte"; } }
  if (DRAW_PTS.length < 3) {
    auditMsg("Tracé annulé (au moins 3 points requis).");
    if (DRAW_LAYER) { map.removeLayer(DRAW_LAYER); DRAW_LAYER = null; }
    return;
  }
  const ring = DRAW_PTS.concat([DRAW_PTS[0]]);     // fermeture de l'anneau
  if (mode === "zone") await createWatchZone(DRAW_ZONE_NAME, { type: "Polygon", coordinates: [ring] });
  else await runAudit("/audit/polygone", { geometry: { type: "Polygon", coordinates: [ring] } });
  if (DRAW_LAYER) { map.removeLayer(DRAW_LAYER); DRAW_LAYER = null; }
}

// ───────────────────────── Bootstrap ─────────────────────────
async function main() {
  window.addEventListener("beforeprint", expandCascadeForPrint);
  initMap();
  // Chargements initiaux INDÉPENDANTS en parallèle (chacun gère déjà son échec) →
  // moins de latence au premier rendu qu'une chaîne de 5 await séquentiels.
  await Promise.all([loadStats(), loadCoverage(), loadVeille(), loadMeta(), fetchPipeline(), loadAssistantStatus()]);
  updateDemoCount();
  // La carte est le cœur de la démo : si le geojson échoue (réseau), on ne laisse jamais
  // un écran mort silencieux — message lisible + filtres encore utilisables au retour.
  let fc = { features: [] };
  try { fc = await (await fetch(`/map/parcels.geojson?commune=${encodeURIComponent(COMMUNE)}`)).json(); }
  catch { showMapError(); }
  FEATURES = fc.features || [];
  reconcileKpisFromFeatures();                    // QA : KPIs jamais bloqués sur « — » si /stats a échoué
  DATA_READY = true;                              // M1 — données chargées : l'état vide est désormais fiable
  hideLoader();
  // Délégation des actions de l'état vide (réinitialiser / tout afficher / recharger).
  const me = $("#map-empty");
  if (me) me.addEventListener("click", (e) => {
    if (e.target.closest(".js-showall")) showAllParcels();
    else if (e.target.closest(".js-reload")) location.reload();
    else if (e.target.closest(".js-reset")) resetFilters();
  });
  setSliderBounds();                              // P3 : curseurs bornés à la plage réelle
  applyFilters();
  if (map && FEATURES.length && layer) map.fitBounds(layer.getBounds(), { maxZoom: 15 });
  if (map && isMobile()) setTimeout(() => map.invalidateSize(), 120);
  loadPermitMarkers();   // couche SITADEL (Lot C4), différée, désactivée par défaut

  // filtres
  const debounce = (fn, ms = 140) => { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; };
  ["f-opp", "f-cpl", "f-surf"].forEach((id) => {
    const out = $("#" + id.replace("f-", "") + "-out") || $("#" + ({ "f-opp": "opp", "f-cpl": "cpl", "f-surf": "surf" }[id]) + "-out");
    $("#" + id).addEventListener("input", (e) => { if (out) out.textContent = e.target.value; });
    $("#" + id).addEventListener("input", debounce(applyFilters));
  });
  document.querySelectorAll("#filter-statuses input").forEach((i) => i.addEventListener("change", () => { clearKpiActive(); applyFilters(); }));
  // Filtre sous-densité (Lot B) : case + seuil.
  const sd = $("#f-sousdense"); if (sd) sd.addEventListener("change", applyFilters);
  const ft = $("#f-taux");
  if (ft) ft.addEventListener("input", () => { const o = $("#taux-out"); if (o) o.textContent = ft.value; applyFilters(); });
  const fo = $("#f-owner"); if (fo) fo.addEventListener("change", applyFilters);
  // Filtres sauvegardés (Lot D3).
  const fsv = $("#fs-save"); if (fsv) fsv.addEventListener("click", saveCurrentFilter);
  const fsd = $("#fs-del"); if (fsd) fsd.addEventListener("click", deleteSavedFilter);
  const fsel = $("#f-saved"); if (fsel) fsel.addEventListener("change", () => {
    const f = SAVED_FILTERS.find((x) => String(x.id) === fsel.value);
    if (f) applyFilterState(f.params);
  });
  loadSavedFilters();
  document.querySelectorAll(".kpi[data-status]").forEach((k) => {
    k.addEventListener("click", () => filterByStatus(k.dataset.status));
    k.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); filterByStatus(k.dataset.status); } });
  });
  document.querySelectorAll(".qf").forEach((q) => q.addEventListener("click", () => filterByStatus(q.dataset.status)));
  const ftog = $("#filter-toggle");
  ftog.addEventListener("click", () => { const hid = $("#filters-panel").classList.toggle("hidden"); ftog.setAttribute("aria-expanded", String(!hid)); });
  document.querySelectorAll(".js-reset").forEach((b) => b.addEventListener("click", resetFilters));
  document.querySelectorAll(".js-view").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  wireKanbanControls();
  const slLim = $("#sl-limit"); if (slLim) slLim.addEventListener("change", loadShortlist);
  const slRef = $("#sl-refresh"); if (slRef) slRef.addEventListener("click", loadShortlist);
  // Bandeau « verdicts partiels » repliable : lu une fois → pastille discrète
  $("#banner").addEventListener("click", (e) => {
    const b = $("#banner");
    if (e.target.closest(".banner-collapse")) { b.classList.add("collapsed"); return; }
    if (b.classList.contains("collapsed")) b.classList.remove("collapsed");
  });
  $("#sheet-close").addEventListener("click", closeSheet);
  $("#scrim").addEventListener("click", () => { closeCompare(); closeSheet(); });
  // Audit pull (Lot A) : référence/adresse via le formulaire, polygone via le bouton dessiner.
  const af = $("#audit-form"); if (af) af.addEventListener("submit", submitAudit);
  const ad = $("#audit-draw"); if (ad) ad.addEventListener("click", () => startDraw("audit"));
  // Actions rapides : « Auditer » révèle le champ d'audit ; « Dessiner » arme le tracé.
  const qaA = $("#qa-audit"); if (qaA) qaA.addEventListener("click", () => {
    const box = $("#audit-form"); if (box) box.classList.toggle("collapsed");
    if (box && !box.classList.contains("collapsed")) { box.scrollIntoView({ block: "nearest" }); const q = $("#audit-q"); if (q) q.focus(); }
  });
  const qaD = $("#qa-draw"); if (qaD) qaD.addEventListener("click", () => startDraw("audit"));
  // 3.C — veille : surveiller une zone, rafraîchir les nouveautés.
  const wa = $("#watch-add"); if (wa) wa.addEventListener("click", startWatchZone);
  const ar = $("#alertes-refresh"); if (ar) ar.addEventListener("click", refreshAlertes);
  // Comparateur (Lot D2) : ajout depuis la fiche, barre, panneau.
  document.addEventListener("click", (e) => {
    const add = e.target.closest(".js-compare-add"); if (add) { addToCompare(add.dataset.idu); return; }
    const rm = e.target.closest("[data-rm]"); if (rm) { removeFromCompare(rm.dataset.rm); return; }
    if (e.target.closest("#cmp-go")) { openCompare(); return; }
    if (e.target.closest("#cmp-clear")) { clearCompare(); return; }
    const open = e.target.closest(".cmp-open"); if (open) { e.preventDefault(); closeCompare(); openSheet(open.dataset.idu); }
    const bps = e.target.closest(".bp-save"); if (bps) { const box = bps.closest(".bilan-params"); if (box) saveBilanParams(box); }
    // 3.C — veille : accuser une nouveauté, retirer une zone, ouvrir la parcelle suivie.
    const ack = e.target.closest(".al-ack"); if (ack) { e.stopPropagation(); ackAlerte(+ack.dataset.id); return; }
    const wzd = e.target.closest(".wz-del"); if (wzd) { deleteWatchZone(+wzd.dataset.id); return; }
    const al = e.target.closest(".alert[data-idu]"); if (al) { openSheet(al.dataset.idu); return; }
    // 3.A — assistant IA : « Expliquer cette parcelle ».
    const ex = e.target.closest(".js-explain"); if (ex) { explainParcel(ex.dataset.idu); return; }
  });
  const cc = $("#cmp-close"); if (cc) cc.addEventListener("click", closeCompare);
  // Démo guidée : bouton d'ouverture, fermeture (croix + clic sur le fond).
  document.querySelectorAll(".js-demo").forEach((b) => b.addEventListener("click", openDemo));
  $("#demo-close").addEventListener("click", closeDemo);
  $("#demo-overlay").addEventListener("click", (e) => { if (e.target.id === "demo-overlay") closeDemo(); });
  // Échap ferme la couche ouverte (démo d'abord, sinon la fiche).
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#demo-overlay").classList.contains("hidden")) closeDemo();
    else if (!$("#sheet").classList.contains("hidden")) closeSheet();
  });
}
main();
