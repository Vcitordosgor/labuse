// RADAR-FIX-NU3-4 — recette hors-navigateur du VERROU À ÉCHÉANCE (K-RAD-02), de la reprise après un
// échec transitoire (K-RAD-03) et de la DÉTECTION DE VEILLE du Mac (K-RAD-01).
// PROUVE :
//   1. verrouActif : un verrou FRAIS bloque, un verrou PÉRIMÉ (passe tuée) est considéré libre ;
//   2. veilleDetectee : un grand écart entre deux battements = Mac endormi (minutes rapportées) ;
//   3. une passe TUÉE (running resté true, horodaté « vieux ») se relâche seule → la soirée REPART ;
//   4. autoRunDate est posé APRÈS le succès seulement : un échec ne « brûle » pas la nuit.
//   node outils/radar-extension/recette_verrou.mjs
import assert from "node:assert";

const _real = setTimeout;
globalThis.setTimeout = (fn) => _real(fn, 0);   // délais « rythme humain » neutralisés

globalThis.__RADAR_TEST__ = true;   // expose les surfaces pures sur globalThis.__radar

let store, captures, failCapture, journals;
function reset(o = {}) {
  store = { searchUrl: "https://www.leboncoin.fr/recherche?x", bieniciSearchUrl: "",
            labuseUrl: "https://app.labuse.immo", token: "jeton", lastCaptureHost: "app.labuse.immo", ...o };
  captures = []; failCapture = false; journals = [];
}
reset();

function fakeInspect() {   // une seule page Leboncoin « riche », pas de suivante
  return { hasNext: false, hasAditemContainer: true, looksBlocked: false,
           searchAds: [{ index_date: "2026-10-30T20:00:00+04:00" }], vignettes: [], indexDates: [] };
}

globalThis.chrome = {
  alarms: { _onAlarm: [], create: async () => {}, get: async () => null,
            onAlarm: { addListener: (f) => chrome.alarms._onAlarm.push(f) } },
  storage: { local: { get: async (def) => ({ ...def, ...store }),
                      set: async (p) => { Object.assign(store, p); } } },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  notifications: { create: async () => {} },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ id: 1, status: "complete", url: "https://x/" }),
          update: async () => {}, remove: async () => {} },
  scripting: { executeScript: async ({ func }) => [{ result: func.name === "clickNext" ? false : fakeInspect() }] },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} },
             onMessage: { addListener() {} }, openOptionsPage() {} },
};
globalThis.fetch = async (url, opts = {}) => {
  const body = opts.body ? JSON.parse(opts.body) : {};
  if (url.includes("/admin/radar/etat"))
    return { ok: true, json: async () => ({ derniere_capture_at: null, actives: [], a_confirmer: [] }) };
  if (url.includes("/admin/radar/capture")) {
    if (failCapture) return { ok: false, status: 500, json: async () => ({}) };
    captures.push({ passe: body.passe });
    return { ok: true, json: async () => ({ ok: true, nb_annonces: 1, nb_nouvelles: 1, nb_maj: 0,
      nb_hors_perimetre: 0, nb_a_qualifier: 0, provenance: "json", mode: "resultats" }) };
  }
  if (url.includes("/admin/radar/journal")) { journals.push(body); return { ok: true, json: async () => ({ ok: true }) }; }
  return { ok: true, json: async () => ({}) };
};

const bg = await import("./background.js");
void bg;
const R = globalThis.__radar;
assert(R && typeof R.verrouActif === "function", "surfaces pures non exposées");

const MIN = 60 * 1000;
async function alarmeTest() {   // chemin AUTO forcé (ignore fenêtre/déjà-fait, PAS le verrou)
  for (const f of chrome.alarms._onAlarm) await f({ name: "radar-soir-test" });
  await new Promise((r) => _real(r, 30));
}

// ── 1) verrouActif (pur) ───────────────────────────────────────────────────
const now = 1_000_000_000_000;
assert.strictEqual(R.verrouActif({ running: false, runningSince: now }, now), false, "pas de run = pas de verrou");
assert.strictEqual(R.verrouActif({ running: true, runningSince: now - 5 * MIN }, now), true, "verrou frais (5 min) = actif");
assert.strictEqual(R.verrouActif({ running: true, runningSince: now - (R.RUN_STALE_MIN + 5) * MIN }, now), false,
  `verrou vieux de ${R.RUN_STALE_MIN}+ min = périmé → libre`);
assert.strictEqual(R.verrouActif({ running: true, runningSince: 0 }, now), true, "verrou legacy sans date = respecté une fois");

// ── 2) veilleDetectee (pur) ─────────────────────────────────────────────────
assert.strictEqual(R.veilleDetectee(0, now).endormi, false, "pas de battement précédent = pas de veille");
assert.strictEqual(R.veilleDetectee(now - 5 * MIN, now).endormi, false, "écart 5 min = cadence normale");
const v = R.veilleDetectee(now - 40 * MIN, now);
assert(v.endormi && v.minutes === 40, `écart 40 min = sommeil détecté (${JSON.stringify(v)})`);

// ── 3) PASSE TUÉE → se libère seule → la soirée REPART ──────────────────────
// Verrou FRAIS (un run réellement en cours) : la soirée NE repart PAS (pas de double-déclenchement).
reset({ running: true, runningSince: Date.now() - 2 * MIN });
await alarmeTest();
assert.strictEqual(captures.length, 0, "verrou frais : aucune capture (run en cours respecté)");

// Verrou PÉRIMÉ (passe tuée, finally jamais atteint) : il se relâche seul → la soirée repart.
reset({ running: true, runningSince: Date.now() - (R.RUN_STALE_MIN + 10) * MIN });
await alarmeTest();
assert(captures.length > 0, "verrou périmé : la soirée doit REPARTIR (passe tuée libérée)");
assert.strictEqual(store.running, false, "après la passe, le verrou est relâché");
assert.strictEqual(store.runningSince, 0, "runningSince remis à 0");

// ── 4) autoRunDate posé APRÈS le succès seulement (K-RAD-03) ────────────────
// Échec : autoRunDate NON posé → la nuit n'est pas « brûlée », une reprise reste possible.
reset(); failCapture = true;
await alarmeTest();
assert.strictEqual(store.autoRunDate || "", "", "échec : autoRunDate NE doit PAS être posé");
assert(/Échec/.test(store.lastResult || ""), "échec : compte-rendu lisible");
assert(journals.some((j) => j.statut === "echec"), "échec : un compte-rendu est tout de même envoyé au serveur");

// Reprise la nuit même : le réseau revient → la capture réussit → autoRunDate posé.
failCapture = false;
await alarmeTest();
assert(captures.length > 0, "reprise : la capture réussit au 2e passage");
assert(store.autoRunDate, "succès : autoRunDate posé (une seule capture auto par soir ensuite)");
assert(journals.some((j) => j.statut === "ok"), "succès : compte-rendu « ok » envoyé au serveur");

console.log("OK — verrou à échéance, reprise après échec, détection de veille :");
console.log(`   verrou   : frais = bloque · > ${R.RUN_STALE_MIN} min = libéré (passe tuée repart)`);
console.log(`   veille   : écart ≥ ${R.SEUIL_VEILLE_MIN} min = sommeil du Mac détecté (${v.minutes} min)`);
console.log("   K-RAD-03 : échec → autoRunDate vide (reprise possible) ; succès → autoRunDate posé + journal serveur");
