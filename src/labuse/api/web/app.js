"use strict";
const COMMUNE = "Saint-Paul";
const COLORS = { opportunite: "#3a9d6e", a_creuser: "#c79a3e", exclue: "#6b7178", faux_positif_probable: "#a8584a", inconnu: "#3a4350" };
const STATUS_LABEL = { opportunite: "Opportunité", a_creuser: "À creuser", exclue: "Exclue", faux_positif_probable: "Faux positif probable" };

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
  return { color: colorFor(p), weight: 1, fillColor: colorFor(p), fillOpacity: 0.55, opacity: 0.9 };
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
      lyr.bindTooltip(`${ft.properties.idu} · ${STATUS_LABEL[ft.properties.status] || "non évaluée"}`, { sticky: true });
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
  const rows = FEATURES
    .map((ft) => ft.properties)
    .filter((p) => p.status !== "exclue" && passesFilter(p))
    .sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0) || (b.surface_m2 || 0) - (a.surface_m2 || 0))
    .slice(0, 80);
  $("#list-count").textContent = `(${rows.length})`;
  $("#parcel-list").innerHTML = rows.map((p) => `
    <div class="prow" data-idu="${esc(p.idu)}">
      <span class="idu">${esc(p.idu)}</span>
      <span class="scores"><b>${p.opportunity_score ?? "—"}</b> opp · ${p.completeness_score ?? "—"} cpl</span>
      <span class="meta"><span class="chip ${p.status}">${STATUS_LABEL[p.status] || "?"}</span></span>
      <span class="meta" style="text-align:right">${fmt(p.surface_m2)} m²</span>
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
  const reasons = (v.reasons || []);
  const reasonsHtml = reasons.length ? reasons.map((r) => `
    <div class="reason ${r.result}">
      <div class="r-head"><span>${esc(r.layer_name)} · ${esc(r.severity || r.result)}</span><span>${esc(r.source || "")}</span></div>
      <div class="r-detail">${esc(r.detail)}</div>
    </div>`).join("") : `<div class="reason">Aucune contrainte ni signal bloquant relevé.</div>`;

  const cascade = (f.cascade || []).map((c) => `
    <div class="casc-row">
      <span class="v-tag v-${c.result}">${esc(c.result)}</span>
      <span>
        <span class="c-detail">${esc(c.detail)}</span><br>
        <span class="c-src">${esc(c.layer_name)}${c.source ? " · " + esc(c.source) : ""}</span>
      </span>
    </div>`).join("");

  const chips = (arr, cls) => (arr || []).map((s) => `<span class="src-chip ${cls}">${esc(s)}</span>`).join("");

  return `
    <div class="sh-idu">${esc(p.idu)}</div>
    <div class="sh-sub">${esc(p.commune || "")}${p.section ? " · section " + esc(p.section) : ""}${p.surface_m2 ? " · " + fmt(Math.round(p.surface_m2)) + " m²" : ""}</div>

    ${ficheWarn()}
    <div class="sh-verdict"><span class="chip ${v.status}">${STATUS_LABEL[v.status] || esc(v.status) || "—"}</span>${fiableBadge(v.status)}</div>
    <div class="sh-scores">
      <div class="score-box opp"><div class="v">${v.opportunity_score ?? "—"}</div><div class="l">Opportunité</div></div>
      <div class="score-box"><div class="v">${v.completeness_score ?? "—"}</div><div class="l">Complétude</div></div>
    </div>
    <div class="golden">L'opportunité ne s'affiche jamais seule : complétude &lt; 50 ⇒ statut plafonné à « à creuser ».</div>

    <div class="sh-section"><h3>Pourquoi</h3>${reasonsHtml}</div>

    ${renderAi(f.ai)}

    <div class="sh-section"><h3>Sources qui ont répondu</h3>
      <div class="src-chips">${chips(f.sources_responded, "ok") || '<span class="src-chip silent">—</span>'}</div>
      ${(f.sources_silent || []).length ? `<div style="margin-top:8px" class="src-chips">${chips(f.sources_silent, "silent")}</div>` : ""}
    </div>

    <div class="sh-section"><h3>Cascade complète — la traçabilité est le produit</h3>${cascade}</div>

    <div class="sh-actions">
      <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=md" target="_blank">Export Markdown</a>
      <a class="btn" href="/parcels/${encodeURIComponent(p.idu)}/export?format=html" target="_blank">Export HTML</a>
      <button class="btn gold" data-fb="good_lead">👍 Bon lead</button>
      <button class="btn" data-fb="false_positive">🚫 Faux positif</button>
    </div>
    <div class="disclaimer">${esc(f.disclaimer || "")}</div>`;
}

function renderAi(ai) {
  if (!ai) return "";
  const list = (arr) => (arr && arr.length) ? `<ul>${arr.map((x) => `<li>${esc(typeof x === "string" ? x : (x.detail || x.source || JSON.stringify(x)))}</li>`).join("")}</ul>` : "";
  return `
    <div class="sh-section"><h3>Analyse LA BUSE (IA)</h3>
      <div class="ai-box">
        <div><span class="ai-tag">Statut recommandé :</span> ${esc(ai.recommended_status || "—")}
          · <span class="ai-tag">confiance :</span> ${esc(ai.confidence_level || "—")}
          ${ai.opportunity_score_adjustment != null ? `· ajust. ${ai.opportunity_score_adjustment > 0 ? "+" : ""}${esc(ai.opportunity_score_adjustment)}` : ""}</div>
        ${ai.reunion_specific_flags ? `<div style="margin-top:8px"><span class="ai-tag">Spécificités Réunion</span>${list(ai.reunion_specific_flags)}</div>` : ""}
        ${ai.blocking_or_risk_signals ? `<div><span class="ai-tag">Signaux bloquants / risque</span>${list(ai.blocking_or_risk_signals)}</div>` : ""}
        ${ai.must_check_before_showing_developer ? `<div><span class="ai-tag">À vérifier avant de montrer au promoteur</span>${list(ai.must_check_before_showing_developer)}</div>` : ""}
      </div>
    </div>`;
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
