// RADAR-FIX-2 (Lot A) — recette hors-navigateur : PROUVE que l'ALARME (pas le bouton) déclenche la
// capture et qu'elle part avec la source « auto ». On simule l'API `chrome.*` d'un service worker MV3,
// on importe background.js tel quel, on fait sonner l'alarme de recette, et on vérifie le POST /capture.
//   node outils/radar-extension/_recette_alarme.mjs
import assert from "node:assert";

const captures = [];       // POST /admin/radar/capture reçus
const store = { searchUrl: "https://www.leboncoin.fr/recherche?x",
                labuseUrl: "https://labuse.immo", token: "jeton-recette" };

// Page Leboncoin « riche » simulée (une seule page, pas de suivante).
function fakeInspect() {
  return { hasNext: false, hasAditemContainer: true, looksBlocked: false,
           outerHTML: "<html><!--leboncoin--></html>", indexDates: ["2026-10-28T20:00:00+04:00"],
           nextData: { props: { pageProps: { searchData: { ads: [{ index_date: "2026-10-28T20:00:00+04:00" }] } } } } };
}

globalThis.chrome = {
  alarms: {
    _onAlarm: [],
    create: async () => {}, get: async () => null, clear: async () => {},
    onAlarm: { addListener: (f) => chrome.alarms._onAlarm.push(f) },
  },
  storage: { local: {
    get: async (def) => ({ ...def, ...store }),
    set: async (patch) => { Object.assign(store, patch); },
  } },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  notifications: { create: async () => {} },
  tabs: {
    create: async () => ({ id: 1 }),
    get: async () => ({ id: 1, status: "complete", url: store.searchUrl }),
    update: async () => {}, remove: async () => {},
  },
  scripting: { executeScript: async ({ func }) => {
    // inspectPage → infos de page ; clickNext → false (pas de page suivante)
    return [{ result: func.name === "clickNext" ? false : fakeInspect() }];
  } },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} },
             onMessage: { addListener() {} }, openOptionsPage() {} },
};

// fetch mocké : /etat (prod « à jour »), /capture (on enregistre la source).
globalThis.fetch = async (url, opts = {}) => {
  const body = opts.body ? JSON.parse(opts.body) : {};
  if (url.includes("/admin/radar/etat")) {
    return { ok: true, json: async () => ({ derniere_capture_at: null, actives: [], a_confirmer: [] }) };
  }
  if (url.includes("/admin/radar/capture")) {
    captures.push({ url, passe: body.passe, source: body.source });
    return { ok: true, json: async () => ({ ok: true, nb_annonces: 1, nb_nouvelles: 1, nb_maj: 0,
      nb_hors_perimetre: 0, nb_a_qualifier: 0, provenance: "json_riche", mode: "resultats" }) };
  }
  return { ok: true, json: async () => ({}) };
};

await import("./background.js");

// Fait sonner l'ALARME DE RECETTE (radar-soir-test) → chemin automatique, pas le bouton.
assert(chrome.alarms._onAlarm.length > 0, "aucun écouteur onAlarm enregistré");
for (const f of chrome.alarms._onAlarm) await f({ name: "radar-soir-test" });
// laisse les promesses asynchrones (openWorkTab/apiEtat/passeNouvelles) se vider
await new Promise((r) => setTimeout(r, 200));

assert(captures.length >= 1, "l'alarme n'a déclenché AUCUNE capture");
assert(captures.every((c) => c.source === "auto"), "une capture n'est pas en source « auto » : "
  + JSON.stringify(captures));
assert(captures.some((c) => c.url.startsWith("https://labuse.immo/")), "la capture ne vise pas la PROD : "
  + JSON.stringify(captures.map((c) => c.url)));
assert(store.autoRunDate, "autoRunDate non posé (garde une-seule-capture-par-soir)");
console.log(`OK — l'alarme a déclenché ${captures.length} capture(s), toutes source « auto », vers la prod.`);
console.log("   passes :", captures.map((c) => `${c.passe}/${c.source}`).join(", "));
console.log("   hôte   :", new URL(captures[0].url).host, "· autoRunDate =", store.autoRunDate);
