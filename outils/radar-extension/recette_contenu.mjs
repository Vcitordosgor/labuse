// RADAR-FIX-NU3-4 — recette hors-navigateur du CONTENU envoyé au serveur (L-EXT-01) et de l'ÉCHEC
// VISIBLE sur JSON Bien'ici tronqué / schéma changé (L-EXT-02).
// PROUVE :
//   1. payloadDeCapture n'envoie QUE les annonces (searchData.ads), jamais le DOM d'une session
//      connectée (identité/messagerie de Vic) ; le payload reste parseable par le serveur et ne peut
//      pas injecter de faux </script> ;
//   2. variante B : seules les cartes <article> partent (stub __NEXT_DATA__ + cartes), pas la page ;
//   3. un JSON Bien'ici tronqué, une clé renommée ou `realEstateAds:null` = ÉCHEC LISIBLE — jamais une
//      « fin d'inventaire » silencieuse affichée « OK ».
//   node outils/radar-extension/recette_contenu.mjs
import assert from "node:assert";

const _real = setTimeout;
globalThis.setTimeout = (fn) => _real(fn, 0);

globalThis.__RADAR_TEST__ = true;

let store, biBody, journals;
function reset(o = {}) {
  store = { searchUrl: "", bieniciSearchUrl: "https://www.bienici.com/recherche/achat/la-reunion-974",
            labuseUrl: "https://app.labuse.immo", token: "jeton", lastCaptureHost: "app.labuse.immo", ...o };
  journals = [];
}
reset();

globalThis.chrome = {
  alarms: { _onAlarm: [], create: async () => {}, get: async () => null,
            onAlarm: { addListener: (f) => chrome.alarms._onAlarm.push(f) } },
  storage: { local: { get: async (def) => ({ ...def, ...store }),
                      set: async (p) => { Object.assign(store, p); } } },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  notifications: { create: async () => {} },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ id: 1, status: "complete", url: "https://www.bienici.com/" }),
          update: async () => {}, remove: async () => {} },
  scripting: { executeScript: async ({ func }) => {
    if (func.name === "biFetchResults") return [{ result: { status: 200, body: biBody } }];
    return [{ result: null }];
  } },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} },
             onMessage: { addListener() {} }, openOptionsPage() {} },
};
globalThis.fetch = async (url, opts = {}) => {
  const body = opts.body ? JSON.parse(opts.body) : {};
  if (url.includes("/admin/radar/etat"))
    return { ok: true, json: async () => ({ derniere_capture_at: null, actives: [], a_confirmer: [] }) };
  if (url.includes("/admin/radar/journal")) { journals.push(body); return { ok: true, json: async () => ({ ok: true }) }; }
  return { ok: true, json: async () => ({ ok: true }) };
};

const bg = await import("./background.js");
void bg;
const R = globalThis.__radar;
assert(R && typeof R.payloadDeCapture === "function", "payloadDeCapture non exposée");

// Le serveur extrait __NEXT_DATA__ par cette regex (src/labuse/pige/html_next.py:_SCRIPT_RE) : on la rejoue.
const SCRIPT_RE = /<script[^>]*\bid="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/;
function extraireNextData(html) {
  const m = SCRIPT_RE.exec(html);
  assert(m, "le serveur ne retrouverait pas __NEXT_DATA__ dans le payload");
  return JSON.parse(m[1]);
}

// ── 1) variante A : seules les annonces partent, jamais le contexte de session ──────────────────────
// `info` imite inspectPage SUR UNE PAGE CONNECTÉE : bodyText/title portent l'identité de Vic ; seul
// searchAds doit sortir. Un champ d'annonce contient « </script> » → doit être neutralisé.
const adPiege = { list_id: 42, subject: "Maison </script><script>pirate()</script>", prix: 315000 };
const infoA = {
  searchAds: [adPiege],
  vignettes: [],
  bodyText: "Bonjour Vic Hoarau — Mes messages (3) — Mon compte — déconnexion — jeton=SECRET123",
  title: "Mon compte — Leboncoin",
};
const payloadA = R.payloadDeCapture(infoA);
// a) le serveur le relit correctement, l'annonce est là
const ndA = extraireNextData(payloadA);
assert.deepStrictEqual(Object.keys(ndA), ["props"], "le payload ne doit porter QUE props");
assert.deepStrictEqual(Object.keys(ndA.props.pageProps), ["searchData"], "pageProps ne doit porter QUE searchData");
assert.strictEqual(ndA.props.pageProps.searchData.ads[0].list_id, 42, "l'annonce doit être transmise");
assert.strictEqual(ndA.props.pageProps.searchData.ads[0].subject, adPiege.subject, "le champ d'annonce est préservé à l'identique");
// b) RIEN du contexte de session connectée n'est présent
for (const fuite of ["Vic Hoarau", "Mes messages", "Mon compte", "SECRET123", "déconnexion"]) {
  assert(!payloadA.includes(fuite), `FUITE : « ${fuite} » ne doit JAMAIS partir au serveur`);
}
// c) pas d'injection : la SEULE balise fermante </script> est celle du conteneur
assert.strictEqual(payloadA.split("</script>").length, 2, "un « </script> » dans une annonce ne doit pas fermer la balise");

// ── 2) variante B : seules les cartes <article>, pas la page ─────────────────────────────────────────
const infoB = { searchAds: null, vignettes: ['<article id="aditem_42">carte annonce 42</article>'],
                bodyText: "Bonjour Vic — Mon compte", title: "Mon compte" };
const payloadB = R.payloadDeCapture(infoB);
assert(payloadB.includes("__NEXT_DATA__"), "variante B : stub __NEXT_DATA__ présent (le serveur ne lève pas)");
assert(payloadB.includes("aditem_42"), "variante B : la carte d'annonce part bien");
assert(!payloadB.includes("Vic") && !payloadB.includes("Mon compte"), "variante B : aucune fuite du contexte de session");

// ── 3) Bien'ici : JSON tronqué / schéma changé = ÉCHEC LISIBLE (jamais « OK » silencieux) ────────────
async function soireeBi(body) {
  reset(); biBody = body;
  for (const f of chrome.alarms._onAlarm) await f({ name: "radar-soir-test" });
  await new Promise((r) => _real(r, 30));
  return store.lastResult || "";
}
const casTronque = await soireeBi('{"realEstateAds":[{"id":');                  // JSON coupé net
assert(/Échec/.test(casTronque) && /illisible/i.test(casTronque), `JSON tronqué doit être un échec lisible : ${casTronque}`);
assert(!/^OK/.test(casTronque), "JSON tronqué ne doit JAMAIS s'afficher « OK »");

const casRenomme = await soireeBi('{"annonces":[{"id":"x"}],"total":10}');      // clé renommée
assert(/Échec/.test(casRenomme) && /structure/i.test(casRenomme), `clé renommée doit être un échec lisible : ${casRenomme}`);

const casNull = await soireeBi('{"realEstateAds":null}');                        // clé présente mais null
assert(/Échec/.test(casNull) && /structure/i.test(casNull), `realEstateAds:null doit être un échec lisible : ${casNull}`);

// chaque échec a bien déposé un compte-rendu serveur (K-RAD-04) — la nuit ratée laisse une trace.
assert(journals.length && journals[journals.length - 1].statut === "echec", "l'échec Bien'ici doit être journalisé côté serveur");

console.log("OK — contenu envoyé épuré + échec Bien'ici visible :");
console.log("   L-EXT-01 : seules les annonces partent (0 fuite identité/messagerie/jeton), </script> neutralisé");
console.log("   variante B : stub __NEXT_DATA__ + cartes <article> seulement");
console.log("   L-EXT-02 : tronqué → « illisible » · clé renommée/null → « structure changée » (jamais « OK »)");
