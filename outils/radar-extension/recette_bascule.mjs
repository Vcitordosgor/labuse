// RADAR-FIX-2 (Lot B) — recette hors-navigateur : PROUVE (1) le rattrapage profond à la 1ʳᵉ capture
// après bascule (jusqu'à 40 pages, vs 15 en régime normal), (2) le message lisible en cas d'échec.
//   node outils/radar-extension/_recette_bascule.mjs
import assert from "node:assert";

// Accélère les délais « rythme humain » pour la recette (sinon 40 pages × ~6 s).
const _real = setTimeout;
globalThis.setTimeout = (fn, _ms) => _real(fn, 0);

let store, captures, failCapture;
function reset(overrides = {}) {
  store = { searchUrl: "https://www.leboncoin.fr/recherche?x", labuseUrl: "https://app.labuse.immo",
            token: "jeton", lastCaptureHost: "", ...overrides };
  captures = []; failCapture = false;
}

// Page « riche » perpétuelle : toujours une page suivante, toujours des annonces récentes (jamais
// sous le seuil index_date) → l'arrêt ne vient QUE du plafond de pages.
function fakeInspect() {
  return { hasNext: true, hasAditemContainer: true, looksBlocked: false,
           outerHTML: "<html><!--lbc--></html>", indexDates: ["2026-10-28T20:00:00+04:00"],
           nextData: { props: { pageProps: { searchData: { ads: [{ index_date: "2026-10-28T20:00:00+04:00" }] } } } } };
}

globalThis.chrome = {
  alarms: { _onAlarm: [], create: async () => {}, get: async () => null,
            onAlarm: { addListener: (f) => chrome.alarms._onAlarm.push(f) } },
  storage: { local: { get: async (def) => ({ ...def, ...store }),
                      set: async (p) => { Object.assign(store, p); } } },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  notifications: { create: async () => {} },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ id: 1, status: "complete", url: store.searchUrl }),
          update: async () => {}, remove: async () => {} },
  scripting: { executeScript: async ({ func }) => [{ result: func.name === "clickNext" ? true : fakeInspect() }] },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} },
             onMessage: { addListener() {} }, openOptionsPage() {} },
};
globalThis.fetch = async (url, opts = {}) => {
  const body = opts.body ? JSON.parse(opts.body) : {};
  if (url.includes("/admin/radar/etat"))
    return { ok: true, json: async () => ({ derniere_capture_at: "2020-01-01T00:00:00+04:00", actives: [], a_confirmer: [] }) };
  if (url.includes("/admin/radar/capture")) {
    if (failCapture) return { ok: false, status: 500, json: async () => ({}) };
    captures.push({ passe: body.passe, source: body.source });
    return { ok: true, json: async () => ({ ok: true, nb_annonces: 1, nb_nouvelles: 1, nb_maj: 0,
      nb_hors_perimetre: 0, nb_a_qualifier: 0, provenance: "json_riche", mode: "resultats" }) };
  }
  return { ok: true, json: async () => ({}) };
};

const bg = await import("./background.js");
void bg;
// On rejoue la soirée via l'alarme de recette (chemin automatique).
async function soiree() {
  captures = [];
  for (const f of chrome.alarms._onAlarm) await f({ name: "radar-soir-test" });
  await new Promise((r) => _real(r, 50));
}

// 1) BASCULE (lastCaptureHost vide) → rattrapage : les « nouvelles » remontent jusqu'à 40 pages.
reset({ lastCaptureHost: "" });
await soiree();
const nouv1 = captures.filter((c) => c.passe === "nouvelles").length;
assert.strictEqual(nouv1, 40, `rattrapage attendu 40 pages « nouvelles », obtenu ${nouv1}`);
assert.strictEqual(store.lastCaptureHost, "app.labuse.immo", "la bascule doit être consommée (lastCaptureHost=prod)");

// 2) RÉGIME NORMAL (host déjà la prod) → pas de rattrapage : plafond « nouvelles » = 15.
reset({ lastCaptureHost: "app.labuse.immo" });
await soiree();
const nouv2 = captures.filter((c) => c.passe === "nouvelles").length;
assert.strictEqual(nouv2, 15, `régime normal attendu 15 pages « nouvelles », obtenu ${nouv2}`);

// 3) ÉCHEC → message LISIBLE dans le popup (lastResult), invitant au dépôt manuel.
reset({ lastCaptureHost: "app.labuse.immo" });
failCapture = true;
await soiree();
assert(/Déposez à la main/.test(store.lastResult || ""), `message d'échec peu lisible : ${store.lastResult}`);

console.log("OK — bascule : rattrapage 40 pages ; régime normal : 15 pages ; échec : message lisible.");
console.log("   bascule   :", nouv1, "nouvelles · host consommé =", store.lastCaptureHost);
console.log("   normal    :", nouv2, "nouvelles");
console.log("   échec     :", JSON.stringify(store.lastResult));
