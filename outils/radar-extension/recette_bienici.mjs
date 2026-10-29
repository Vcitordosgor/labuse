// RADAR-SOURCES-2 — recette hors-navigateur du volet Bien'ici de l'extension.
// PROUVE : (1) le routage par portail (isBienici/isLeboncoin), (2) l'extraction de l'id Bien'ici depuis
// l'URL d'annonce (dernier segment), (3) la CLASSIFICATION de confirmation — même doctrine RADAR-FIX-3 :
// on ne retire QUE sur preuve positive (404, ou off-market déclaré) ; tout le reste = « inconnue ».
//   node outils/radar-extension/recette_bienici.mjs
import assert from "node:assert";

globalThis.__RADAR_TEST__ = true;
const noop = () => {};
globalThis.chrome = {
  alarms: { create: noop, get: async () => null, clear: noop, onAlarm: { addListener: noop } },
  storage: { local: { get: async (d) => ({ ...d }), set: async () => {} } },
  action: { setBadgeText: noop, setBadgeBackgroundColor: noop },
  notifications: { create: noop },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ id: 1 }), update: noop, remove: noop },
  scripting: { executeScript: async () => [{ result: null }] },
  runtime: { onInstalled: { addListener: noop }, onStartup: { addListener: noop },
             onMessage: { addListener: noop }, openOptionsPage: noop },
};

await import("./background.js");
const { classifierConfirmationBienici, bieniciIdFromUrl, isBienici, isLeboncoin } = globalThis.__radar;
assert(typeof classifierConfirmationBienici === "function", "classifierConfirmationBienici non exposée");

let ok = 0;
function check(nom, cond) { assert(cond, `cas « ${nom} »`); console.log("OK — " + nom); ok++; }

// 1) Routage par portail
check("isBienici bienici.com", isBienici("https://www.bienici.com/annonce/vente/x/maison/4pieces/immo-facile-1"));
check("isBienici faux sur leboncoin", !isBienici("https://www.leboncoin.fr/ad/ventes_immobilieres/42"));
check("isLeboncoin leboncoin.fr", isLeboncoin("https://www.leboncoin.fr/ad/ventes_immobilieres/42"));
check("isLeboncoin faux sur bienici", !isLeboncoin("https://www.bienici.com/annonce/vente/x/maison/4pieces/z"));

// 2) Id Bien'ici = dernier segment de l'URL d'annonce
check("id depuis URL", bieniciIdFromUrl(
  "https://www.bienici.com/annonce/vente/saint-gilles-les-bains/maison/5pieces/immo-facile-61412190")
  === "immo-facile-61412190");
check("id robuste au slash final", bieniciIdFromUrl(
  "https://www.bienici.com/annonce/vente/x/maison/4pieces/apimo-87295864/") === "apimo-87295864");

// 3) Classification — on ne retire QUE sur preuve positive
const cas = [
  ["présente (200, onTheMarket)",   { status: 200, found: true, onTheMarket: true },   "presente",  null],
  ["expirée (200, off-market)",     { status: 200, found: true, onTheMarket: false },  "supprimee", "expiree"],
  ["disparue (404)",                { status: 404, found: false, onTheMarket: null },  "supprimee", "http_404"],
  ["bloqué/429 (0)",                { status: 0,   found: false, onTheMarket: null },  "inconnue",  null],
  ["200 sans statut lisible",       { status: 200, found: false, onTheMarket: null },  "inconnue",  null],
];
for (const [nom, ad, verdict, preuve] of cas) {
  const res = classifierConfirmationBienici(ad);
  assert.strictEqual(res.verdict, verdict, `${nom} : verdict ${res.verdict} ≠ ${verdict}`);
  assert.strictEqual(res.preuve, preuve, `${nom} : preuve ${res.preuve} ≠ ${preuve}`);
  if (res.verdict === "supprimee")
    assert(["expiree", "http_404"].includes(res.preuve), `${nom} : retrait SANS preuve positive !`);
  console.log(`OK — ${nom.padEnd(30)} → ${res.verdict}${res.preuve ? " / " + res.preuve : ""}`);
  ok++;
}
console.log(`\n${ok} cas verts — routage par portail + confirmation Bien'ici sur preuve positive uniquement.`);
