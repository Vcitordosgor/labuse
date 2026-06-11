"use strict";
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
  sar: "SAR", risques: "Risques (PPR)", abf: "ABF / Monuments", ens: "ENS", safer: "SAFER",
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
function initMap() {
  map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([-21.01, 55.285], 13);
  const plan = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd", maxZoom: 20,
    attribution: '&copy; OpenStreetMap &copy; CARTO',
  }).addTo(map);
  // « Vue du ciel » : orthophotographie IGN (BD ORTHO) via la Géoplateforme (WMTS/PM).
  const ortho = L.tileLayer(
    "https://data.geopf.fr/wmts?layer=ORTHOIMAGERY.ORTHOPHOTOS&style=normal&tilematrixset=PM" +
    "&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image/jpeg" +
    "&TileMatrix={z}&TileCol={x}&TileRow={y}",
    { maxZoom: 21, attribution: "&copy; IGN — Géoplateforme (BD ORTHO)" }
  );
  L.control.layers(
    { "Plan (radar)": plan, "Vue du ciel (IGN)": ortho },
    null, { position: "topright", collapsed: true }
  ).addTo(map);
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
  return true;
}

function currentFilter() {
  const statuses = new Set([...document.querySelectorAll("#filter-statuses input:checked")].map((i) => i.value));
  return {
    statuses,
    minOpp: +$("#f-opp").value,
    minCpl: +$("#f-cpl").value,
    minSurf: +$("#f-surf").value,
  };
}

function renderMap() {
  if (layer) layer.remove();
  const shown = FEATURES.filter((ft) => passesFilter(ft.properties));
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
  const TYPE = { zonage_change: "Changement de zonage", mutation_dvf: "Mutation DVF", new_permit_nearby: "Permis à proximité" };
  $("#veille-list").innerHTML = sig.length ? sig.map((s) => {
    const p = s.payload || {};
    const det = (p.from || p.to) ? `<br>${esc(p.from)} → ${esc(p.to)}` : (p.date_mutation || p.date ? `<br>${esc(p.date_mutation || p.date)}` : "");
    return `<div class="alert"><span class="a-type">${TYPE[s.signal_type] || esc(s.signal_type)}</span> · <span class="a-idu">${esc(s.idu)}</span>${det}</div>`;
  }).join("") : `<div class="muted-sm">Aucune alerte. Lancer « labuse watch ».</div>`;
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
    return `<span class="fiable-tag ok" title="Contrôlée sur les couches disponibles : PLU, PPR, littoral, forêt, SAR partiel. Ne vaut pas garantie de constructibilité.">Opportunité vérifiée</span>`
      + `<span class="fiable-sub">vérifiée sur les couches disponibles (PLU, PPR, littoral, forêt, SAR partiel) — ne vaut pas garantie de constructibilité</span>`;
  }
  return `<span class="fiable-tag reserve" title="Des couches critiques ne sont pas encore ingérées.">sous réserve · couches manquantes</span>`;
}

function renderList() {
  const f = currentFilter();
  const matched = FEATURES
    .map((ft) => ft.properties)
    .filter((p) => p.status !== "exclue" && p.status !== "faux_positif_probable" && passesFilter(p))
    .sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0) || (b.surface_m2 || 0) - (a.surface_m2 || 0));
  const rows = matched.slice(0, 80);
  $("#list-count").textContent = matched.length > rows.length ? `(${rows.length} affichées / ${matched.length})` : `(${matched.length})`;
  $("#parcel-list").innerHTML = rows.map((p) => `
    <div class="prow st-${p.status}" data-idu="${esc(p.idu)}">
      <span class="idu">${esc(p.idu)}</span>
      <span class="p-verdict"><span class="chip ${p.status}">${STATUS_LABEL[p.status] || "?"}</span></span>
      <span class="scores"><b>${p.opportunity_score ?? "—"}</b> opp · ${p.completeness_score ?? "—"} cpl</span>
      <span class="p-surf">${fmt(p.surface_m2)} m²</span>
      ${p.downgrade_reason ? `<span class="p-downgrade">⚠ déclassée : ${esc(p.downgrade_reason)}</span>` : ""}
    </div>`).join("") || `<div class="loading">Aucune parcelle ne correspond.</div>`;
  document.querySelectorAll(".prow").forEach((el) => el.addEventListener("click", () => focusParcel(el.dataset.idu)));
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

function applyFilters() { renderMap(); renderList(); }

// KPI cliquable → filtre carte + liste par statut (P2). "all" = tout afficher.
function clearKpiActive() { document.querySelectorAll(".kpi").forEach((k) => k.classList.remove("active")); }
function filterByStatus(status) {
  document.querySelectorAll("#filter-statuses input").forEach((b) => { b.checked = (status === "all") || (b.value === status); });
  document.querySelectorAll(".kpi").forEach((k) => k.classList.toggle("active", k.dataset.status === status));
  applyFilters();
}

// ───────────────────────── Fiche premium §8 ─────────────────────────
async function openSheet(idu) {
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

  const nU = unknown.length;
  const unverifiedLine = nU ? `
    <section class="unverified">
      <span class="uv-mark">◔</span>
      <span><b>${nU} couche${nU > 1 ? "s" : ""} non vérifiée${nU > 1 ? "s" : ""}</b> à ce jour — verdict partiel. Détail en bas de fiche.</span>
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

    ${unverifiedLine}

    <section class="reads">
      <div class="read"><h3 class="rd-h ok">Ce qui favorise</h3>${block(favors, "ok", "Aucun signal franchement favorable sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h lim${hasHard ? " has-hard" : ""}">Ce qui contraint</h3>${block(limits, "lim", "Aucune contrainte relevée sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h unk">Ce qu'on n'a pas vérifié</h3>${block(unknown, "unk", "Toutes les couches critiques ont répondu.")}</div>
    </section>

    ${renderFaisabilite(f.faisabilite)}

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
      <button class="btn print" data-print>⎙ Imprimer / PDF</button>
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
  return `
    <section class="resume v-${r.statut}">
      <div class="rs-head">
        <span class="rs-eyebrow">Résumé opportunité</span>
        <span class="chip ${r.statut}">${esc(r.statut_label)}</span>
      </div>
      <p class="rs-synthese">${esc(r.synthese)}</p>
      <div class="rs-cols">
        <div class="rs-col"><h4 class="rs-h ok">Pourquoi elle ressort</h4>${li(r.positifs)}</div>
        <div class="rs-col"><h4 class="rs-h warn">À vérifier</h4>${li(r.vigilance)}</div>
      </div>
      <div class="rs-action"><span class="rs-action-k">Prochaine action</span> ${esc(r.prochaine_action)}</div>
    </section>`;
}

// Assemblage foncier (Phase 5) — parcelles voisines contiguës + drapeau prudent.
function renderVoisinage(vz) {
  if (!vz || !(vz.voisines || []).length) return "";
  const a = vz.assemblage || {};
  const items = vz.voisines.map((v) => `
    <button class="vz-item" data-idu="${esc(v.idu)}" title="Ouvrir la fiche ${esc(v.idu)}">
      <span class="vz-idu">${esc(v.idu)}</span>
      <span class="chip ${v.status || "inconnu"}">${STATUS_LABEL[v.status] || "—"}</span>
      <span class="vz-meta">${v.opportunity_score != null ? `<b>${v.opportunity_score}</b> opp · ` : ""}${v.plu_zone ? "zone " + esc(v.plu_zone) + " · " : ""}${v.surface_m2 != null ? fmt(v.surface_m2) + " m²" : ""}</span>
    </button>`).join("");
  const banner = a.possible ? `<div class="vz-assemblage">🧩 ${esc(a.note)}</div>` : "";
  return `
    <section class="voisinage">
      <h3 class="src-h">Parcelles voisines à regarder <span class="pm-sub">· contiguës, indicatif</span></h3>
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
      <p class="pp-disc">${esc(pr.disclaimer || "")}</p>
    </section>`;
}

// ───────────────────────── Données promoteur (Temps 1) ─────────────────────────
// Tout est indicatif & sourcé ; aucune valeur réglementaire fabriquée. Mesures EPSG:2975.
function renderPromoteur(pr, centroid) {
  if (!pr) return "";
  const alt = pr.altimetrie || {}, fac = pr.facade || {}, plu = pr.plu_detail || {};
  const own = pr.proprietaire || {}, net = pr.reseaux || {};
  const fig = (val, lbl) => `<span class="pm-fig"><b>${val ?? "—"}</b><i>${lbl}</i></span>`;
  const na = (o) => `<p class="pm-na">${esc(o.note || "Indisponible.")}</p>`;

  // 1 · Cote altimétrique (RGE ALTI, live échantillonné)
  const altBody = alt.available
    ? `<div class="pm-figs">${fig(alt.min_m, "min (m)")}${fig(alt.mean_m, "moy. (m)")}${fig(alt.max_m, "max (m)")}${fig(alt.amplitude_m, "amplitude (m)")}</div>
       <p class="pm-src">${esc(alt.source || "")} · ${alt.n_points || 0} pts</p>` : na(alt);

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
    sky = `<div class="pm-sky"><img loading="lazy" src="${url}" alt="Vue aérienne IGN de la parcelle"
        onerror="this.parentNode.innerHTML='<p class=&quot;pm-na&quot;>Orthophoto IGN momentanément indisponible.</p>'">
      <span class="pm-sky-cap">Orthophoto IGN (BD ORTHO) · centrée sur la parcelle</span></div>
      <p class="pm-src">Astuce : bascule le fond « Vue du ciel (IGN) » sur la carte (coin haut-droit).</p>`;
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
  const factBody = `
    <p class="pm-na"><b>Propriétaire :</b> ${esc(own.note || "non vérifié")}</p>
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
  if ($("#pm-slot") === slot) slot.outerHTML = renderPromoteur(pr, centroid);
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

  return `
    <section class="faisa${fa.constructible ? "" : " faisa-nc"}">
      <div class="faisa-eyebrow">Pré-faisabilité · carte promoteur</div>
      <h2 class="faisa-verdict">${esc(fa.verdict)}</h2>
      <div class="faisa-ctx">${ctxBits}</div>
      ${keyCards ? `<div class="faisa-cards">${keyCards}</div>` : ""}
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
      <div class="faisa-cards bilan-cards">
        <div class="fc"><span class="fc-num">${meur(ca.bas)}–${meur(ca.haut)}</span><span class="fc-lbl">Chiffre d'affaires potentiel</span></div>
        <div class="fc"><span class="fc-num">${fmt(px.median)} €/m²</span><span class="fc-lbl">Prix DVF médian · ${esc(px.type_prix || "")} (${px.n} ventes / ${px.commune_fallback ? "commune" : km(px.radius_m)})</span></div>
        <div class="fc fc-wide"><span class="fc-num">${meur(cf.central)}<span class="fc-sub">~${fmt(cf.par_m2_terrain)} €/m² terrain</span></span><span class="fc-lbl">Charge foncière (médiane)</span></div>
      </div>
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
  document.querySelectorAll("[data-prosp]").forEach((b) => b.addEventListener("click", async () => {
    const act = b.dataset.prosp;
    b.disabled = true;
    try {
      let pe = await (await fetch(`/pipeline/parcel/${encodeURIComponent(idu)}`)).json();
      let entry = pe.entry;
      if (!entry) {
        const r = await (await fetch("/pipeline", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ idu }) })).json();
        entry = r.entry;
      }
      if (act === "identify") {
        await fetch(`/pipeline/${entry.id}`, { method: "PATCH", headers: { "content-type": "application/json" },
          body: JSON.stringify({ status: "proprietaire_a_identifier", prospection: { statut_proprietaire: "a_identifier" } }) });
      } else if (act === "contact") {
        const d = entry.prospection || {};
        const nom = window.prompt("Nom / organisation du contact (saisie manuelle) :", d.contact_nom || d.contact_organisation || "");
        if (nom === null) { b.disabled = false; return; }
        const tel = window.prompt("Téléphone ou e-mail (optionnel) :", d.contact_telephone || d.contact_email || "") || "";
        const isMail = tel.includes("@");
        await fetch(`/pipeline/${entry.id}`, { method: "PATCH", headers: { "content-type": "application/json" },
          body: JSON.stringify({ prospection: { statut_proprietaire: "identifie_manuellement", source_statut: "saisi_utilisateur",
            niveau_confiance: "moyen", contact_nom: nom, [isMail ? "contact_email" : "contact_telephone"]: tel } }) });
      }
      openSheet(idu);   // recharge la fiche
    } catch { b.disabled = false; }
  }));

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
  if (FEATURES.length && layer) map.fitBounds(layer.getBounds(), { maxZoom: 15 });
  if (isMobile()) setTimeout(() => map.invalidateSize(), 120);

  // filtres
  const debounce = (fn, ms = 140) => { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; };
  ["f-opp", "f-cpl", "f-surf"].forEach((id) => {
    const out = $("#" + id.replace("f-", "") + "-out") || $("#" + ({ "f-opp": "opp", "f-cpl": "cpl", "f-surf": "surf" }[id]) + "-out");
    $("#" + id).addEventListener("input", (e) => { if (out) out.textContent = e.target.value; });
    $("#" + id).addEventListener("input", debounce(applyFilters));
  });
  document.querySelectorAll("#filter-statuses input").forEach((i) => i.addEventListener("change", () => { clearKpiActive(); applyFilters(); }));
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
  $("#scrim").addEventListener("click", closeSheet);
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
