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
  osm_faux_positif: "Bâti (OSM)",
};
const shortLayer = (c) => LAYER_SHORT[c.layer_name] || c.layer_name;

let FEATURES = [];          // toutes les parcelles (GeoJSON features)
let layer = null;           // couche Leaflet courante
const byIdu = {};           // idu -> layer (pour highlight)
let map;
let COVERAGE = null;        // couverture des couches critiques (/coverage)

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
  const opp = p.status === "opportunite";          // l'opportunité prime aussi sur la carte
  return { color: c, weight: opp ? 1.4 : 0.7, fillColor: c, fillOpacity: opp ? 0.62 : 0.4, opacity: 0.95 };
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
  const fc = { type: "FeatureCollection", features: FEATURES.filter((ft) => passesFilter(ft.properties)) };
  layer = L.geoJSON(fc, {
    style: (ft) => styleFor(ft.properties),
    onEachFeature: (ft, lyr) => {
      byIdu[ft.properties.idu] = lyr;
      lyr.on("click", () => openSheet(ft.properties.idu));
      lyr.bindTooltip(tipHtml(ft.properties), { sticky: true, direction: "top", className: "lb-tip" });
    },
  }).addTo(map);
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
  b.innerHTML = `<span class="warn-ico">⚠</span><span><b>Verdicts partiels</b> — une opportunité peut masquer une contrainte non encore intégrée.
    Couches manquantes : <span class="missing">${COVERAGE.missing.map(esc).join(" · ")}</span></span>`;
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

function focusParcel(idu) {
  const lyr = byIdu[idu];
  if (lyr) { map.fitBounds(lyr.getBounds(), { maxZoom: 18 }); lyr.openTooltip(); }
  openSheet(idu);
}

function applyFilters() { renderMap(); renderList(); }

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

  const liRow = (c, cls) => `<li class="rd-li ${cls}">
      <span class="rd-detail">${esc(c.detail)}</span>
      <span class="rd-src">${esc(shortLayer(c))}${c.source ? " · " + esc(c.source) : ""}</span></li>`;
  const block = (arr, cls, emptyMsg) => arr.length
    ? `<ul class="rd-list">${arr.map((c) => liRow(c, cls === "lim" ? (c.result === "HARD_EXCLUDE" ? "hard" : "soft") : cls)).join("")}</ul>`
    : `<p class="rd-empty">${emptyMsg}</p>`;

  const unverifiedLine = unknown.length ? `
    <section class="unverified">
      <span class="uv-mark">◔</span>
      <span><b>Non vérifié à ce jour</b> — ${unknown.map((c) => esc(shortLayer(c))).join(" · ")}.
      Le verdict reste partiel tant que ces couches ne sont pas intégrées.</span>
    </section>` : "";

  const cascadeRows = cascade.map((c) => `
    <tr>
      <td><span class="ct-tag v-${c.result}">${esc(c.result)}</span></td>
      <td><span class="ct-detail">${esc(c.detail)}</span>
          <span class="ct-src">${esc(c.layer_name)}${c.source ? " · " + esc(c.source) : ""}</span></td>
    </tr>`).join("");

  const chips = (arr, cls) => (arr || []).map((s) => `<span class="src-chip ${cls}">${esc(s)}</span>`).join("");
  const loc = [p.commune, p.section ? "section " + esc(p.section) : "",
    p.surface_m2 ? fmt(Math.round(p.surface_m2)) + " m²" : ""].filter(Boolean).join(" · ");

  return `
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
      <div class="read"><h3 class="rd-h lim">Ce qui contraint</h3>${block(limits, "lim", "Aucune contrainte relevée sur les couches disponibles.")}</div>
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
      <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=md" target="_blank">Export Markdown</a>
      <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=html" target="_blank">Export HTML</a>
      <button class="btn good" data-fb="good_lead">Bon lead</button>
      <button class="btn bad" data-fb="false_positive">Faux positif</button>
    </footer>
    <p class="disclaimer">${esc(f.disclaimer || "")}</p>`;
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
}

function closeSheet() { $("#sheet").classList.add("hidden"); $("#scrim").classList.add("hidden"); }

// ───────────────────────── Bootstrap ─────────────────────────
async function main() {
  initMap();
  await loadStats();
  await loadCoverage();
  await loadSignals();
  const fc = await (await fetch(`/map/parcels.geojson?commune=${encodeURIComponent(COMMUNE)}`)).json();
  FEATURES = fc.features || [];
  applyFilters();
  if (FEATURES.length && layer) map.fitBounds(layer.getBounds(), { maxZoom: 15 });

  // filtres
  const debounce = (fn, ms = 140) => { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; };
  ["f-opp", "f-cpl", "f-surf"].forEach((id) => {
    const out = $("#" + id.replace("f-", "") + "-out") || $("#" + ({ "f-opp": "opp", "f-cpl": "cpl", "f-surf": "surf" }[id]) + "-out");
    $("#" + id).addEventListener("input", (e) => { if (out) out.textContent = e.target.value; });
    $("#" + id).addEventListener("input", debounce(applyFilters));
  });
  document.querySelectorAll("#filter-statuses input").forEach((i) => i.addEventListener("change", applyFilters));
  $("#sheet-close").addEventListener("click", closeSheet);
  $("#scrim").addEventListener("click", closeSheet);
}
main();
