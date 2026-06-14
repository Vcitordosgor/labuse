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
const COLORS = { opportunite: "#37976a", a_creuser: "#c2913f", exclue: "#697079", faux_positif_probable: "#b85f4c", inconnu: "#3a434e" };
const STATUS_LABEL = { opportunite: "Opportunité", a_creuser: "À creuser", exclue: "Exclue", faux_positif_probable: "Faux positif probable" };
const VERDICT_GLOSS = {
  opportunite: "Foncier a priori mobilisable — reste à confirmer sur le terrain.",
  a_creuser: "Signaux mitigés : une vérification s'impose avant de démarcher.",
  exclue: "Contrainte rédhibitoire identifiée — écartée du radar.",
  faux_positif_probable: "La donnée terrain contredit le signal — probable faux positif.",
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
let layer = null;           // couche Leaflet courante
const byIdu = {};           // idu -> layer (pour highlight)
let map;
let PERMITS_LAYER = null;   // couche marqueurs SITADEL (Lot C4)
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
    L.control.layers(
      { "Plan (radar)": plan, "Vue du ciel (IGN)": ortho,
        "Ciel · 2010": h2010, "Ciel · 1989": h1989, "Ciel · 1980": h1980, "Ciel · 1961": h1961 },
      { "Permis (SITADEL)": PERMITS_LAYER }, { position: "topright", collapsed: true }
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
    case "opportunite":            return { color: "#9bf0c7", weight: 2.2, fillColor: "#41c08c", fillOpacity: 0.88, opacity: 1 };
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
  const empty = $("#map-empty"); if (empty) empty.classList.toggle("hidden", shown.length > 0);
  updateResultMeta(shown.length);
}

// Compteur de résultats + bouton « Réinitialiser » (visible si filtre non par défaut).
function isDefaultFilter() {
  const st = new Set([...document.querySelectorAll("#filter-statuses input:checked")].map((i) => i.value));
  const defStatus = st.size === 2 && st.has("opportunite") && st.has("a_creuser");
  return defStatus && +$("#f-opp").value === 0 && +$("#f-cpl").value === 0 && +$("#f-surf").value === 0;
}
function updateResultMeta(n) {
  const c = $("#rm-count"); if (c) c.textContent = `${fmt(n)} parcelle${n > 1 ? "s" : ""} sur la carte`;
  document.querySelectorAll(".rm-reset").forEach((b) => b.classList.toggle("hidden", isDefaultFilter()));
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
  $("#veille-count").textContent = fmt(s.active_signals || 0);
}

async function loadSignals() {
  let sig = [];
  try { sig = await (await fetch(`/signals?commune=${encodeURIComponent(COMMUNE)}&limit=8`)).json(); } catch { sig = []; }
  // Audit J8 : pas de section VIDE en permanence (effet « inachevé »), pas de jargon CLI.
  const section = document.querySelector(".veille");
  if (!sig.length) { if (section) section.classList.add("hidden"); return; }
  if (section) section.classList.remove("hidden");
  const TYPE = { zonage_change: "Changement de zonage", mutation_dvf: "Mutation DVF", new_permit_nearby: "Permis à proximité" };
  $("#veille-list").innerHTML = sig.map((s) => {
    const p = s.payload || {};
    const det = (p.from || p.to) ? `<br>${esc(p.from)} → ${esc(p.to)}` : (p.date_mutation || p.date ? `<br>${esc(p.date_mutation || p.date)}` : "");
    return `<div class="alert"><span class="a-type">${TYPE[s.signal_type] || esc(s.signal_type)}</span> · <span class="a-idu">${esc(s.idu)}</span>${det}</div>`;
  }).join("");
}

async function loadCoverage() {
  try { COVERAGE = await (await fetch("/coverage")).json(); } catch { COVERAGE = null; }
  renderBanner();
}

function renderBanner() {
  const b = $("#banner");
  if (!COVERAGE || COVERAGE.complete) { b.classList.add("hidden"); return; }
  b.classList.remove("hidden");
  b.innerHTML = `<span class="warn-ico">⚠</span>
    <span class="banner-text"><b>Verdicts partiels</b> — une opportunité peut masquer une contrainte non encore intégrée.
    Couches manquantes : <span class="missing">${COVERAGE.missing.map(esc).join(" · ")}</span></span>
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
  $("#list-count").textContent = matched.length > rows.length ? `(${rows.length} affichées / ${matched.length})` : `(${matched.length})`;
  const more = matched.length > rows.length
    ? `<button class="list-more" type="button">Afficher 80 de plus (${matched.length - rows.length} restantes)</button>` : "";
  $("#parcel-list").innerHTML = rows.map((p) => `
    <div class="prow st-${p.status}" data-idu="${esc(p.idu)}">
      <span class="idu">${esc(p.idu)}</span>
      <span class="p-verdict"><span class="chip ${p.status}">${STATUS_LABEL[p.status] || "?"}</span></span>
      <span class="scores"><b>${p.opportunity_score ?? "—"}</b> opp · ${p.completeness_score ?? "—"} cpl</span>
      <span class="p-surf">${fmt(p.surface_m2)} m²</span>
      ${p.downgrade_reason ? `<span class="p-downgrade">⚠ déclassée : ${esc(p.downgrade_reason)}</span>` : ""}
    </div>`).join("") + more || `<div class="loading">Aucune parcelle ne correspond.</div>`;
  document.querySelectorAll(".prow").forEach((el) => el.addEventListener("click", () => focusParcel(el.dataset.idu)));
  const mb = document.querySelector(".list-more");
  if (mb) mb.addEventListener("click", () => { LIST_LIMIT += 80; renderList(); });
}

// Navigation : radar (Carte ⇄ Liste, mobile) ⇄ Kanban (plein écran, desktop + mobile).
function setView(view) {
  const kanban = view === "kanban";
  document.body.classList.toggle("view-kanban", kanban);
  if (!kanban) {
    document.body.classList.toggle("view-map", view === "map");
    document.body.classList.toggle("view-list", view === "list");
    if (view === "map" && map) setTimeout(() => map.invalidateSize(), 60);
  }
  document.querySelectorAll(".js-view").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.view === view)));
  if (kanban) loadKanban();
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
function clearKpiActive() { document.querySelectorAll(".kpi").forEach((k) => k.classList.remove("active")); }
function filterByStatus(status) {
  document.querySelectorAll("#filter-statuses input").forEach((b) => { b.checked = (status === "all") || (b.value === status); });
  document.querySelectorAll(".kpi").forEach((k) => k.classList.toggle("active", k.dataset.status === status));
  applyFilters();
}

// ───────────────────────── Fiche premium §8 ─────────────────────────
let CURRENT_IDU = null;   // fiche ouverte (pour le recalcul bilan après calibration, 1.C)
async function openSheet(idu) {
  CURRENT_IDU = idu;
  $("#sheet").classList.remove("hidden");
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

    <section class="verdict v-${status}">
      <div class="verdict-eyebrow">Verdict LA BUSE</div>
      <h1 class="verdict-word">${STATUS_LABEL[status] || esc(status) || "—"}</h1>
      <p class="verdict-gloss">${esc(VERDICT_GLOSS[status] || "")}</p>
      ${v.downgrade_reason ? `<p class="verdict-downgrade">⚠️ Déclassée malgré un score brut élevé — ${esc(v.downgrade_reason)}.</p>` : ""}
      ${fiableBadge(status)}
    </section>

    <section class="scores v-${status}">
      <div class="score">
        <div class="score-top"><span class="score-num">${v.opportunity_score ?? "—"}</span><span class="score-lbl">Opportunité</span></div>
        <div class="bar opp"><i style="width:${w(v.opportunity_score)}%"></i></div>
      </div>
      <div class="score">
        <div class="score-top"><span class="score-num">${v.completeness_score ?? "—"}</span><span class="score-lbl">Complétude</span></div>
        <div class="bar cpl"><i style="width:${w(v.completeness_score)}%"></i></div>
      </div>
      <p class="golden-note">L'opportunité ne s'affiche jamais seule — une complétude &lt; 50 plafonne le verdict à « à creuser ».</p>
    </section>

    ${renderResume(f.resume)}

    ${renderBati(f.bati)}

    ${unverifiedLine}

    <section class="reads">
      <div class="read"><h3 class="rd-h ok">Ce qui favorise</h3>${block(favors, "ok", "Aucun signal franchement favorable sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h lim${hasHard ? " has-hard" : ""}">Ce qui contraint</h3>${block(limits, "lim", "Aucune contrainte relevée sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h unk">Ce qu'on n'a pas vérifié</h3>${block(unknown, "unk", "Toutes les couches critiques ont répondu.")}</div>
    </section>

    ${renderFaisabilite(f.faisabilite)}

    ${renderPermits(f.permits)}

    ${renderVoisinage(f.voisinage)}

    ${renderAi(f.ai)}

    ${promoteurSlot()}

    <details class="cascade">
      <summary>Cascade complète · la traçabilité est le produit <span class="cc-count">${cascade.length} couches</span></summary>
      <table class="cascade-table">${cascadeRows}</table>
    </details>

    <section class="sources">
      <h3 class="src-h">Sources qui ont répondu</h3>
      <div class="src-chips">${chips(f.sources_responded, "ok") || '<span class="src-chip silent">—</span>'}</div>
      ${(f.sources_silent || []).length ? `<h3 class="src-h muted">Restées silencieuses</h3><div class="src-chips">${chips(f.sources_silent, "silent")}</div>` : ""}
    </section>

    ${renderProspection(f)}

    <footer class="fiche-actions">
      <button class="btn follow" data-follow>+ Suivre cette parcelle</button>
      <button class="btn js-compare-add" data-idu="${esc(p.idu)}">⊕ Comparer</button>
      <a class="btn primary" href="/parcels/${encodeURIComponent(p.idu)}/export?format=onepager" target="_blank" title="Fiche 1 page A4 — à imprimer en PDF pour un comité">📄 Fiche 1 page (PDF)</a>
      <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=md" target="_blank">Export Markdown</a>
      <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=html" target="_blank">Export HTML</a>
      <button class="btn good" data-fb="good_lead">Bon lead</button>
      <button class="btn bad" data-fb="false_positive">Faux positif</button>
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
  const posTitle = declassee ? "Signaux bruts (avant déclassement)" : "Pourquoi elle ressort";
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
  const factBody = `
    <p class="pm-na"><b>Propriétaire :</b> ${ownerBadge} ${esc(own.note || "non vérifié")}</p>
    ${spfBtn}
    ${viaBlock}
    <ul class="pm-list net">${netRow("Eau potable", net.eau_potable)}${netRow("Électricité (EDF)", net.electricite)}${netRow("Assainissement", net.assainissement)}</ul>
    <p class="pm-src">${esc((net && net.source) || "")}</p>`;

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

// 1.C — bandeau « non calibré » si un paramètre CRITIQUE manque.
function renderBilanBanner(b) {
  const nc = b.non_calibres_critiques || [];
  if (!nc.length) return "";
  return `<div class="bilan-noncal">⚠️ Bilan <b>non fiable</b> tant que ces paramètres clés ne sont pas calibrés : ${nc.map(esc).join(", ")}. Renseignez-les ci-dessous (secteur <b>${esc(b.secteur || "—")}</b>).</div>`;
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
        const src = p.source && p.source !== "défaut" ? `<span class="bp-src">${esc(p.source)}</span>` : "";
        return `<label class="bp-row${nonCal ? " bp-nc" : ""}">
          <span class="bp-lbl">${esc(p.label)}${p.critique ? " ★" : ""}${nonCal ? ' <span class="bp-badge">non calibré</span>' : ""}${src}</span>
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
  const compBlock = (cmp.n_vefa == null && cmp.n_ancien == null) ? "" : `
      <div class="bilan-comp">
        <div class="bilan-comp-t">Comparables de prix utilisés</div>
        <dl class="bilan-comp-grid">
          <dt>Prix retenu</dt><dd><b>${fmt(px.median)} €/m²</b> · ${esc(px.type_prix || "")} · ${px.n} ventes · ${per} · ${px.commune_fallback ? "commune" : km(px.radius_m)}</dd>
          <dt>Médiane ancien</dt><dd>${ancienCell}</dd>
          <dt>Médiane neuf / VEFA</dt><dd>${vefaCell}</dd>
          <dt>Écart neuf vs ancien</dt><dd>${ecartCell}</dd>
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
    return `<div class="ds-box ds-ok"><b>✅ Démo prête</b> ${when}<div class="ds-grid">${dots}</div></div>`;
  }
  const actions = (st.actions || []).map((a) => `<code>${esc(a)}</code>`).join("<br>");
  return `<div class="ds-box ds-bad"><b>⚠ Démo non prête</b> ${when}
    <div class="ds-grid">${dots}</div>
    <div class="ds-actions">À lancer :<br>${actions || "<code>labuse doctor</code>"}</div></div>`;
}
function closeDemo() {
  const ov = $("#demo-overlay");
  ov.classList.add("hidden"); ov.setAttribute("aria-hidden", "true");
}
function renderDemoPanel(d) {
  const items = (d.parcels || []).map((p) => {
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
  }).join("");
  const warn = d.all_conform ? "" :
    `<p class="dp-warn">⚠ Une parcelle a dérivé (statut ≠ attendu) — relancer <code>labuse rebuild-demo</code> avant la démo.</p>`;
  return `<p class="dp-intro">Parcours guidé sur des parcelles déjà validées (${esc(d.commune)}). Cliquez une ligne pour ouvrir sa fiche.</p>${warn}<div class="dp-list">${items}</div>`;
}

// ───────────────────────── Pipeline / Kanban (T2) ─────────────────────────
async function loadMeta() {
  try { KANBAN_META = await (await fetch("/pipeline/meta")).json(); }
  catch { KANBAN_META = { columns: [], priorities: [], defaults: {} }; }
}
const colLabel = (k) => (KANBAN_META && KANBAN_META.columns.find((c) => c.key === k) || {}).label || k;
const prioLabel = (k) => (KANBAN_META && KANBAN_META.priorities.find((p) => p.key === k) || {}).label || k;
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
  $("#kb-count").textContent = total ? `${total} parcelle${total > 1 ? "s" : ""} suivie${total > 1 ? "s" : ""}` : "Aucune parcelle suivie";
  const byCol = {}; cols.forEach((c) => { byCol[c.key] = []; });
  entries.forEach((e) => { (byCol[e.status] = byCol[e.status] || []).push(e); });
  // État vide pédagogique : on explique comment démarrer une prospection.
  const emptyHint = total === 0
    ? `<div class="kb-empty-hint">Aucune parcelle suivie pour l'instant.<br>Ouvrez une fiche parcelle, cliquez <b>« + Suivre cette parcelle »</b>, puis passez-la en <b>« Propriétaire à identifier »</b> et notez votre prochaine action pour démarrer votre prospection.</div>`
    : "";
  $("#kb-board").innerHTML = emptyHint + cols.map((c) => `
    <div class="kb-col" data-col="${c.key}">
      <div class="kb-col-head"><span class="kb-col-title">${esc(c.label)}</span><span class="kb-col-n">${(byCol[c.key] || []).length}</span></div>
      <div class="kb-cards">${(byCol[c.key] || []).map(kbCard).join("") || '<div class="kb-empty">—</div>'}</div>
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
  btn.textContent = `✓ Suivie · ${colLabel(statusKey)}`;
}

// ───────────────────────── Audit pull (Lot A) ─────────────────────────
// Auditer un terrain à la demande : référence cadastrale, adresse (BAN) ou polygone dessiné.
// Tout converge vers POST /audit/* → ingestion 'audit' + cascade → on ouvre la fiche produite.
const AUDIT_REF_RX = /^([A-Za-z]{1,2})\s*0*(\d{1,4})$/;   // « BV 912 », « bv912 », « BV 0912 »

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
  if (q.length < 3) { auditMsg("Saisissez une adresse ou une référence (ex. BV 912)."); return; }
  const m = AUDIT_REF_RX.exec(q);
  if (m) return runAudit("/audit/reference", { section: m[1].toUpperCase(), numero: m[2] });
  return runAudit("/audit/adresse", { q });
}

// Dessin de polygone (Leaflet natif : clic = sommet, double-clic = terminer).
let DRAW_PTS = [], DRAW_LAYER = null, DRAWING = false;
function startDraw() {
  if (!map) { auditMsg("Carte indisponible."); return; }
  if (DRAWING) return finishDraw();
  DRAWING = true; DRAW_PTS = [];
  if (DRAW_LAYER) { map.removeLayer(DRAW_LAYER); DRAW_LAYER = null; }
  $("#audit-draw").classList.add("on");
  $("#audit-draw").textContent = "✓ Terminer le tracé";
  auditMsg("Cliquez pour poser les sommets ; double-clic ou « Terminer » pour boucler.");
  map.doubleClickZoom.disable();
  map.on("click", onDrawClick);
  map.on("dblclick", finishDraw);
}
function onDrawClick(e) {
  DRAW_PTS.push([e.latlng.lng, e.latlng.lat]);
  if (DRAW_LAYER) map.removeLayer(DRAW_LAYER);
  DRAW_LAYER = L.polygon(DRAW_PTS.map(([lng, lat]) => [lat, lng]),
    { color: "#c9a86a", weight: 2, dashArray: "4", fillOpacity: 0.08 }).addTo(map);
}
async function finishDraw(e) {
  if (e && e.originalEvent) L.DomEvent.stop(e);
  map.off("click", onDrawClick); map.off("dblclick", finishDraw);
  setTimeout(() => map.doubleClickZoom.enable(), 300);
  DRAWING = false;
  $("#audit-draw").classList.remove("on");
  $("#audit-draw").textContent = "✏ Dessiner sur la carte";
  if (DRAW_PTS.length < 3) { auditMsg("Tracé annulé (au moins 3 points requis)."); return; }
  const ring = DRAW_PTS.concat([DRAW_PTS[0]]);     // fermeture de l'anneau
  await runAudit("/audit/polygone", { geometry: { type: "Polygon", coordinates: [ring] } });
  if (DRAW_LAYER) { map.removeLayer(DRAW_LAYER); DRAW_LAYER = null; }
}

// ───────────────────────── Bootstrap ─────────────────────────
async function main() {
  window.addEventListener("beforeprint", expandCascadeForPrint);
  initMap();
  // Chargements initiaux INDÉPENDANTS en parallèle (chacun gère déjà son échec) →
  // moins de latence au premier rendu qu'une chaîne de 5 await séquentiels.
  await Promise.all([loadStats(), loadCoverage(), loadSignals(), loadMeta(), fetchPipeline()]);
  // La carte est le cœur de la démo : si le geojson échoue (réseau), on ne laisse jamais
  // un écran mort silencieux — message lisible + filtres encore utilisables au retour.
  let fc = { features: [] };
  try { fc = await (await fetch(`/map/parcels.geojson?commune=${encodeURIComponent(COMMUNE)}`)).json(); }
  catch { showMapError(); }
  FEATURES = fc.features || [];
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
  const ftog = $("#filter-toggle");
  ftog.addEventListener("click", () => { const hid = $("#filters-panel").classList.toggle("hidden"); ftog.setAttribute("aria-expanded", String(!hid)); });
  document.querySelectorAll(".js-reset").forEach((b) => b.addEventListener("click", resetFilters));
  document.querySelectorAll(".js-view").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  wireKanbanControls();
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
  const ad = $("#audit-draw"); if (ad) ad.addEventListener("click", startDraw);
  // Comparateur (Lot D2) : ajout depuis la fiche, barre, panneau.
  document.addEventListener("click", (e) => {
    const add = e.target.closest(".js-compare-add"); if (add) { addToCompare(add.dataset.idu); return; }
    const rm = e.target.closest("[data-rm]"); if (rm) { removeFromCompare(rm.dataset.rm); return; }
    if (e.target.closest("#cmp-go")) { openCompare(); return; }
    if (e.target.closest("#cmp-clear")) { clearCompare(); return; }
    const open = e.target.closest(".cmp-open"); if (open) { e.preventDefault(); closeCompare(); openSheet(open.dataset.idu); }
    const bps = e.target.closest(".bp-save"); if (bps) { const box = bps.closest(".bilan-params"); if (box) saveBilanParams(box); }
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
