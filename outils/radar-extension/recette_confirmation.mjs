// RADAR-FIX-3 — recette hors-navigateur de la CLASSIFICATION d'un lien de confirmation.
// PROUVE, cas par cas, qu'on ne retire QUE sur preuve positive (annonce expirée reconnue, ou vraie
// page 404), et qu'une page bloquée / vide / illisible / redirigée ne retire JAMAIS rien (« inconnue »
// → non vérifiée côté serveur). C'est la régression des 60 fausses suppressions du 28/10.
//   node outils/radar-extension/recette_confirmation.mjs
import assert from "node:assert";

// Drapeau AVANT l'import : background.js expose alors classifierConfirmation sur globalThis.__radar.
globalThis.__RADAR_TEST__ = true;

// Stubs chrome minimaux pour que l'import du service worker ne lève pas (il pose des listeners au chargement).
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
const { classifierConfirmation } = globalThis.__radar;
assert(typeof classifierConfirmation === "function", "classifierConfirmation non exposée");

const LID = 3187081805;
const urlAnnonce = `https://www.leboncoin.fr/ad/ventes_immobilieres/${LID}`;

// Une page « annonce bien présente » (on est resté sur l'annonce, le prix s'affiche).
const pagePresente = {
  outerHTML: "<html>…</html>", looksBlocked: false, hasAditemContainer: false,
  title: "Maison F4 — Saint-Denis", bodyText: "Maison F4 à Saint-Denis\n315 000 €\nSurface 90 m²",
};
// Une page EXPIRÉE — contient aussi des annonces recommandées AVEC prix : la phrase doit trancher.
const pageExpiree = {
  outerHTML: "<html>…</html>", looksBlocked: false, hasAditemContainer: false,
  title: "Leboncoin", bodyText: "Cette annonce n'est plus disponible.\nAnnonces recommandées :\nAppartement 210 000 €",
};
// Une vraie page 404 du portail.
const page404 = {
  outerHTML: "<html>…</html>", looksBlocked: false, hasAditemContainer: false,
  title: "Page introuvable", bodyText: "Oups ! La page que vous recherchez est introuvable.",
};
// Un mur DataDome / captcha.
const pageBloquee = {
  outerHTML: "<html>…</html>", looksBlocked: true, hasAditemContainer: false,
  title: "Verification", bodyText: "datadome — veuillez vérifier que vous êtes humain",
};
// Une page vide / illisible (rien lu).
const pageVide = {
  outerHTML: "", looksBlocked: false, hasAditemContainer: false, title: "", bodyText: "",
};
// Une redirection hors de l'annonce (accueil leboncoin : plein de prix, mais on n'est PLUS sur l'annonce,
// et aucune phrase d'expiration). On n'a pas pu voir l'annonce → non vérifiée (jamais un retrait).
const pageAccueil = {
  outerHTML: "<html>…</html>", looksBlocked: false, hasAditemContainer: true,
  title: "Leboncoin — Immobilier", bodyText: "Immobilier à La Réunion\n210 000 €\n180 000 €\n305 000 €",
};
// Faux positif HISTORIQUE : « 404 » et « expirée » dans le HTML/JS mais annonce bien présente.
// Comme on classe sur le TEXTE VISIBLE, ce bruit n'a aucun effet → présente.
const pageAnnonceAvecBruit = {
  outerHTML: "<script>var e='erreur 404 annonce expirée';</script>", looksBlocked: false,
  hasAditemContainer: false, title: "Villa — Saint-Pierre", bodyText: "Villa à Saint-Pierre\n450 000 €\n4 pièces",
};

const cas = [
  ["présente",                 classifierConfirmation(pagePresente, urlAnnonce, LID),      "presente",  null],
  ["annonce expirée (preuve)", classifierConfirmation(pageExpiree, urlAnnonce, LID),       "supprimee", "expiree"],
  ["vraie 404 (preuve)",       classifierConfirmation(page404, urlAnnonce, LID),           "supprimee", "http_404"],
  ["bloquée DataDome",         classifierConfirmation(pageBloquee, urlAnnonce, LID),       "inconnue",  null],
  ["vide / illisible",         classifierConfirmation(pageVide, urlAnnonce, LID),          "inconnue",  null],
  ["redirigée vers l'accueil", classifierConfirmation(pageAccueil, "https://www.leboncoin.fr/", LID), "inconnue", null],
  ["bruit 404 dans le JS",     classifierConfirmation(pageAnnonceAvecBruit, urlAnnonce, LID), "presente", null],
];

let ok = 0;
for (const [nom, res, verdict, preuve] of cas) {
  assert.strictEqual(res.verdict, verdict, `cas « ${nom} » : verdict attendu ${verdict}, obtenu ${res.verdict}`);
  assert.strictEqual(res.preuve, preuve, `cas « ${nom} » : preuve attendue ${preuve}, obtenue ${res.preuve}`);
  // Invariant DUR : un retrait N'EXISTE QU'AVEC une preuve positive.
  if (res.verdict === "supprimee") {
    assert(["expiree", "http_404"].includes(res.preuve), `cas « ${nom} » : retrait SANS preuve positive !`);
  }
  console.log(`OK — ${nom.padEnd(26)} → ${res.verdict}${res.preuve ? " / " + res.preuve : ""}`);
  ok++;
}
console.log(`\n${ok}/${cas.length} cas verts — on ne retire que sur preuve positive ; bloquée/vide/redirigée = non vérifiée.`);
