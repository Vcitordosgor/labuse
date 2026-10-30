// RADAR-COUVERTURE-1 — recette hors-navigateur : PROUVE que la fenêtre du soir est calculée en HEURE DE
// LA RÉUNION (Indian/Reunion), même quand l'horloge de la machine est à PARIS (le cas du Mac de Vic).
// On force le fuseau du process à Europe/Paris AVANT d'importer background.js, puis on vérifie que
// `fenetreSoir` ancre la fenêtre sur 21 h RÉUNION (= 18 h Paris en hiver), et pas 21 h Paris — ce qui, à
// la passe 336, décalait la capture vers ~02 h Réunion.
//   node outils/radar-extension/recette_fenetre.mjs
process.env.TZ = "Europe/Paris";   // horloge machine simulée = Paris (doit être posé AVANT tout new Date)
import assert from "node:assert";

globalThis.__RADAR_TEST__ = true;
globalThis.chrome = {
  alarms: { create: async () => {}, get: async () => null, onAlarm: { addListener() {} } },
  storage: { local: { get: async (def) => ({ ...def }), set: async () => {} } },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  notifications: { create: async () => {} },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ id: 1, status: "complete" }),
          update: async () => {}, remove: async () => {} },
  scripting: { executeScript: async () => [{ result: null }] },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} },
             onMessage: { addListener() {} }, openOptionsPage() {} },
};

await import("./background.js");
const { fenetreSoir, reunionParts } = globalThis.__radar;

// Petit utilitaire : l'heure MURALE Paris d'un instant (le fuseau du process étant Paris, getHours suffit).
const heureParis = (epoch) => new Date(epoch).getHours();
const opts = { hour: 21, jitterMaxMin: 180 };

// 1) Fenêtre ancrée sur 21 h RÉUNION, un soir donné (instant absolu = 23 h Réunion le 30/10).
const soir = new Date("2026-10-30T23:00:00+04:00");
const { debut, fin } = fenetreSoir(opts, soir);
const pDebut = reunionParts(new Date(debut));
const pFin = reunionParts(new Date(fin));
assert.strictEqual(pDebut.hour, 21, `début attendu 21 h Réunion, obtenu ${pDebut.hour} h`);
assert.strictEqual(pDebut.minute, 0, "début attendu pile à l'heure");
assert.strictEqual(pDebut.dateStr, "2026-10-30", `date Réunion attendue 2026-10-30, obtenue ${pDebut.dateStr}`);
assert.strictEqual(pFin.hour, 0, `fin attendue à minuit Réunion, obtenue ${pFin.hour} h`);

// 2) La machine est bien à Paris : 21 h Réunion = 18 h Paris (hiver, Paris UTC+1 / Réunion UTC+4).
//    L'ANCIEN code (setHours(21) en heure locale) aurait placé le début à 21 h PARIS.
assert.strictEqual(heureParis(debut), 18, `début attendu 18 h Paris (=21 h Réunion), obtenu ${heureParis(debut)} h`);

// 3) L'instant 23 h Réunion est DANS la fenêtre [21 h, minuit].
assert(soir.getTime() >= debut && soir.getTime() <= fin, "23 h Réunion devrait être dans la fenêtre");

// 4) 02 h 39 Réunion (la signature de la passe 336) est HORS fenêtre : avant le début du soir même, et
//    après la fin de la veille → aucune capture ne doit partir à cette heure-là.
const apresMinuit = new Date("2026-10-30T02:39:00+04:00");
const f30 = fenetreSoir(opts, apresMinuit);
assert(apresMinuit.getTime() < f30.debut, "02 h 39 devrait être AVANT le début de la fenêtre du soir même");
const veille = fenetreSoir(opts, new Date("2026-10-29T23:00:00+04:00"));
assert(apresMinuit.getTime() > veille.fin, "02 h 39 devrait être APRÈS la fin de la fenêtre de la veille");

console.log("OK — fenêtre du soir en heure Réunion, horloge machine à Paris :");
console.log(`   machine TZ = ${process.env.TZ} · début = 21 h Réunion = ${heureParis(debut)} h Paris · fin = minuit Réunion`);
console.log(`   23 h Réunion : DANS la fenêtre · 02 h 39 Réunion : HORS fenêtre (ni ce soir, ni la veille).`);
