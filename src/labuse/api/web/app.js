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

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString("fr-FR"));

// ───────────────────────── Carte ─────────────────────────
function initMap() {
  map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([-21.01, 55.285], 13);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd", maxZoom: 20,
    attribution: '&copy; OpenStreetMap &copy; CARTO',
  }).addTo(map);
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
  return `<span class="t-idu">${esc(p.idu)}</span><span class="t-st st-${p.status || "inconnu"}">${lbl}</span>${sc}`;
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
  const s = await (await fetch(`/stats?commune=${encodeURIComponent(COMMUNE)}`)).json();
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
  return COVERAGE && COVERAGE.reliable_ready
    ? `<span class="fiable-tag ok">opportunité fiable</span>`
    : `<span class="fiable-tag reserve">sous réserve · couches manquantes</span>`;
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
  $("#scrim").classList.remove("hidden");
  $("#sheet-body").innerHTML = `<div class="loading">Chargement de la fiche…</div>`;
  let f;
  try { f = await (await fetch(`/parcels/${encodeURIComponent(idu)}`)).json(); }
  catch { $("#sheet-body").innerHTML = `<div class="loading">Parcelle introuvable.</div>`; return; }
  $("#sheet-body").innerHTML = renderFiche(f);
  wireSheetActions(idu);
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

    ${unverifiedLine}

    <section class="reads">
      <div class="read"><h3 class="rd-h ok">Ce qui favorise</h3>${block(favors, "ok", "Aucun signal franchement favorable sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h lim${hasHard ? " has-hard" : ""}">Ce qui contraint</h3>${block(limits, "lim", "Aucune contrainte relevée sur les couches disponibles.")}</div>
      <div class="read"><h3 class="rd-h unk">Ce qu'on n'a pas vérifié</h3>${block(unknown, "unk", "Toutes les couches critiques ont répondu.")}</div>
    </section>

    ${renderAi(f.ai)}

    <details class="cascade">
      <summary>Cascade complète · la traçabilité est le produit <span class="cc-count">${cascade.length} couches</span></summary>
      <table class="cascade-table">${cascadeRows}</table>
    </details>

    <section class="sources">
      <h3 class="src-h">Sources qui ont répondu</h3>
      <div class="src-chips">${chips(f.sources_responded, "ok") || '<span class="src-chip silent">—</span>'}</div>
      ${(f.sources_silent || []).length ? `<h3 class="src-h muted">Restées silencieuses</h3><div class="src-chips">${chips(f.sources_silent, "silent")}</div>` : ""}
    </section>

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
  document.querySelectorAll("[data-fb]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    await fetch("/feedback", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ idu, verdict: b.dataset.fb }) });
    b.textContent = "✓ Enregistré";
  }));
  const pb = $("[data-print]");
  if (pb) pb.addEventListener("click", () => { expandCascadeForPrint(); window.print(); });

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

function closeSheet() { $("#sheet").classList.add("hidden"); $("#scrim").classList.add("hidden"); }

// ───────────────────────── Pipeline / Kanban (T1) ─────────────────────────
async function loadMeta() {
  try { KANBAN_META = await (await fetch("/pipeline/meta")).json(); }
  catch { KANBAN_META = { columns: [], priorities: [], defaults: {} }; }
}
const colLabel = (k) => (KANBAN_META && KANBAN_META.columns.find((c) => c.key === k) || {}).label || k;
const prioLabel = (k) => (KANBAN_META && KANBAN_META.priorities.find((p) => p.key === k) || {}).label || k;

async function loadKanban() {
  if (!KANBAN_META) await loadMeta();
  let entries = [];
  try { entries = await (await fetch("/pipeline")).json(); } catch { entries = []; }
  renderKanban(entries);
}

function kbCard(e) {
  const v = e.verdict || {};
  const st = v.status || "inconnu";
  const cols = (KANBAN_META.columns || []);
  const prios = (KANBAN_META.priorities || []);
  const opts = cols.map((c) => `<option value="${c.key}" ${c.key === e.status ? "selected" : ""}>${esc(c.label)}</option>`).join("");
  const prioOpts = prios.map((p) => `<option value="${p.key}" ${p.key === e.priority ? "selected" : ""}>${esc(p.label)}</option>`).join("");
  const surf = e.parcel && e.parcel.surface_m2 ? fmt(Math.round(e.parcel.surface_m2)) + " m²" : "—";
  return `
    <div class="kb-card st-${st}" data-id="${e.id}" data-idu="${esc(e.idu)}">
      <div class="kb-card-top">
        <span class="kb-idu">${esc(e.idu)}</span>
        <span class="chip ${st}">${STATUS_LABEL[st] || "?"}</span>
      </div>
      <div class="kb-sub">
        <span class="kb-opp">${v.opportunity_score ?? "—"}</span> opp · <span>${surf}</span>
        <span class="kb-prio prio-${esc(e.priority)}">${esc(prioLabel(e.priority))}</span>
      </div>
      ${e.reminder_date ? `<div class="kb-rem">⏰ rappel ${esc(e.reminder_date)}</div>` : ""}
      ${e.notes ? `<div class="kb-notes">${esc(e.notes)}</div>` : ""}
      <div class="kb-foot">
        <select class="kb-move" title="Changer de colonne">${opts}</select>
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
          <button class="kb-save">Enregistrer</button>
          <button class="kb-cancel">Annuler</button>
        </div>
      </div>
    </div>`;
}

function renderKanban(entries) {
  const cols = KANBAN_META.columns || [];
  const n = entries.length;
  $("#kb-count").textContent = n ? `${n} parcelle${n > 1 ? "s" : ""} suivie${n > 1 ? "s" : ""}` : "Aucune parcelle suivie";
  const byCol = {};
  cols.forEach((c) => { byCol[c.key] = []; });
  entries.forEach((e) => { (byCol[e.status] = byCol[e.status] || []).push(e); });
  $("#kb-board").innerHTML = cols.map((c) => `
    <div class="kb-col" data-col="${c.key}">
      <div class="kb-col-head"><span class="kb-col-title">${esc(c.label)}</span><span class="kb-col-n">${(byCol[c.key] || []).length}</span></div>
      <div class="kb-cards">${(byCol[c.key] || []).map(kbCard).join("") || '<div class="kb-empty">—</div>'}</div>
    </div>`).join("");
  wireKanban();
}

function patchEntry(id, body) {
  return fetch(`/pipeline/${id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

function wireKanban() {
  document.querySelectorAll("#kb-board .kb-card").forEach((card) => {
    const id = card.dataset.id;
    const idu = card.dataset.idu;
    card.addEventListener("click", (ev) => {            // clic carte → fiche (sauf sur les contrôles)
      if (ev.target.closest(".kb-foot, .kb-editor")) return;
      openSheet(idu);
    });
    card.querySelector(".kb-move").addEventListener("change", async (ev) => {
      await patchEntry(id, { status: ev.target.value }); loadKanban();
    });
    card.querySelector(".kb-edit").addEventListener("click", () => card.querySelector(".kb-editor").classList.toggle("hidden"));
    card.querySelector(".kb-cancel").addEventListener("click", () => card.querySelector(".kb-editor").classList.add("hidden"));
    card.querySelector(".kb-del").addEventListener("click", async () => {
      await fetch(`/pipeline/${id}`, { method: "DELETE" }); loadKanban();
    });
    card.querySelector(".kb-save").addEventListener("click", async () => {
      await patchEntry(id, {
        notes: card.querySelector(".kb-notes-in").value,
        priority: card.querySelector(".kb-prio-in").value,
        reminder_date: card.querySelector(".kb-rem-in").value,   // "" = efface
      });
      loadKanban();
    });
  });
}

function markFollowing(btn, statusKey) {
  btn.classList.add("on");
  btn.textContent = `✓ Suivie · ${colLabel(statusKey)}`;
}

// ───────────────────────── Bootstrap ─────────────────────────
async function main() {
  window.addEventListener("beforeprint", expandCascadeForPrint);
  initMap();
  await loadStats();
  await loadCoverage();
  await loadSignals();
  await loadMeta();
  const fc = await (await fetch(`/map/parcels.geojson?commune=${encodeURIComponent(COMMUNE)}`)).json();
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
  // Bandeau « verdicts partiels » repliable : lu une fois → pastille discrète
  $("#banner").addEventListener("click", (e) => {
    const b = $("#banner");
    if (e.target.closest(".banner-collapse")) { b.classList.add("collapsed"); return; }
    if (b.classList.contains("collapsed")) b.classList.remove("collapsed");
  });
  $("#sheet-close").addEventListener("click", closeSheet);
  $("#scrim").addEventListener("click", closeSheet);
}
main();
