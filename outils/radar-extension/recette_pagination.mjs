// RADAR-COUVERTURE-1 — recette hors-navigateur : PROUVE la RÈGLE D'ARRÊT PAR NOUVEAUTÉ de la passe
// « nouvelles », pour LES DEUX portails. On tourne les pages tant que la dernière rapporte ≥ 1 annonce
// nouvelle (`nb_nouvelles` renvoyé par /capture), on s'arrête à la 1ʳᵉ page sans nouveauté, le plafond
// reste une garde dure, et le nombre de pages POSTÉES (= n_pages serveur) reflète les pages réellement lues.
//   node outils/radar-extension/recette_pagination.mjs
import assert from "node:assert";

const _real = setTimeout;
globalThis.setTimeout = (fn) => _real(fn, 0);   // délais « rythme humain » neutralisés pour la recette

let store, captures, novelty, noveltyDefault, biEmptyFrom;
function reset(o = {}) {
  store = { searchUrl: "", bieniciSearchUrl: "", labuseUrl: "https://app.labuse.immo",
            token: "jeton", lastCaptureHost: "app.labuse.immo", ...o };  // host = prod → pas de rattrapage
  captures = []; novelty = {}; noveltyDefault = 0; biEmptyFrom = Infinity;
}

function fakeInspect() {   // page Leboncoin « riche » : toujours une page suivante
  return { hasNext: true, hasAditemContainer: true, looksBlocked: false,
           outerHTML: "<html><!--lbc--></html>", indexDates: [],
           nextData: { props: { pageProps: { searchData: { ads: [] } } } } };
}
const fakeAds = (n) => Array.from({ length: n }, (_, i) => ({ id: "x" + i, modificationDate: "2026-10-30T10:00:00+04:00" }));

globalThis.chrome = {
  alarms: { _onAlarm: [], create: async () => {}, get: async () => null,
            onAlarm: { addListener: (f) => chrome.alarms._onAlarm.push(f) } },
  storage: { local: { get: async (def) => ({ ...def, ...store }),
                      set: async (p) => { Object.assign(store, p); } } },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {} },
  notifications: { create: async () => {} },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ id: 1, status: "complete", url: "https://x/" }),
          update: async () => {}, remove: async () => {} },
  scripting: { executeScript: async ({ func, args }) => {
    if (func.name === "clickNext") return [{ result: true }];
    if (func.name === "biFetchResults") {          // Bien'ici : page = args[1]
      const page = args && args[1];
      const ads = page >= biEmptyFrom ? [] : fakeAds(24);
      return [{ result: { status: 200, body: JSON.stringify({ realEstateAds: ads }) } }];
    }
    if (func.name === "biFetchAd") return [{ result: { status: 200, found: true, onTheMarket: true } }];
    return [{ result: fakeInspect() }];            // inspectPage (Leboncoin)
  } },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} },
             onMessage: { addListener() {} }, openOptionsPage() {} },
};

globalThis.fetch = async (url, opts = {}) => {
  const body = opts.body ? JSON.parse(opts.body) : {};
  if (url.includes("/admin/radar/etat"))
    return { ok: true, json: async () => ({ derniere_capture_at: null, actives: [], a_confirmer: [] }) };
  if (url.includes("/admin/radar/capture")) {
    const nb = novelty[body.page] !== undefined ? novelty[body.page] : noveltyDefault;
    captures.push({ passe: body.passe, page: body.page, nb });     // 1 entrée = 1 page POSTÉE = +1 n_pages
    return { ok: true, json: async () => ({ ok: true, nb_annonces: 24, nb_nouvelles: nb, nb_maj: 0,
      nb_hors_perimetre: 0, nb_a_qualifier: 0, provenance: "json", mode: "resultats" }) };
  }
  return { ok: true, json: async () => ({}) };
};

const bg = await import("./background.js");
void bg;
async function soiree() {
  captures = [];
  for (const f of chrome.alarms._onAlarm) await f({ name: "radar-soir-test" });
  await new Promise((r) => _real(r, 50));
}
const pagesNouvelles = () => captures.filter((c) => c.passe === "nouvelles");

// ── Leboncoin ────────────────────────────────────────────────────────────
// A) nouveauté décroissante 5,3,1,0 → s'arrête à la page 4 (la 1ʳᵉ sans nouveauté). 4 pages lues.
reset({ searchUrl: "https://www.leboncoin.fr/recherche?x" });
novelty = { 1: 5, 2: 3, 3: 1, 4: 0 };
await soiree();
let p = pagesNouvelles();
assert.strictEqual(p.length, 4, `LBC : attendu 4 pages (arrêt à la 1ʳᵉ sans nouveauté), obtenu ${p.length}`);
assert.strictEqual(p[p.length - 1].nb, 0, "LBC : la dernière page lue doit être celle à 0 nouveauté");

// B) dès la page 1 aucune nouveauté → on lit cette seule page puis on s'arrête.
reset({ searchUrl: "https://www.leboncoin.fr/recherche?x" });
novelty = { 1: 0 };
await soiree();
assert.strictEqual(pagesNouvelles().length, 1, "LBC : page 1 sans nouveauté → exactement 1 page lue");

// C) nouveauté sur CHAQUE page → le plafond dur (15 en régime normal) borne la passe.
reset({ searchUrl: "https://www.leboncoin.fr/recherche?x" });
noveltyDefault = 1;
await soiree();
assert.strictEqual(pagesNouvelles().length, 15, `LBC : plafond normal attendu 15, obtenu ${pagesNouvelles().length}`);

// ── Bien'ici (MÊME RÈGLE) ─────────────────────────────────────────────────
// D) nouveauté 5,3,0 → 3 pages lues, arrêt à la 1ʳᵉ sans nouveauté.
reset({ bieniciSearchUrl: "https://www.bienici.com/recherche/achat/la-reunion-974" });
novelty = { 1: 5, 2: 3, 3: 0 };
await soiree();
p = pagesNouvelles();
assert.strictEqual(p.length, 3, `BI : attendu 3 pages (arrêt à la 1ʳᵉ sans nouveauté), obtenu ${p.length}`);
assert.strictEqual(p[p.length - 1].nb, 0, "BI : la dernière page lue doit être celle à 0 nouveauté");

// E) page vide (au-delà du dernier résultat) → fin propre : seules les pages à contenu sont postées.
reset({ bieniciSearchUrl: "https://www.bienici.com/recherche/achat/la-reunion-974" });
noveltyDefault = 1; biEmptyFrom = 3;            // les pages ≥ 3 reviennent vides
await soiree();
assert.strictEqual(pagesNouvelles().length, 2, `BI : attendu 2 pages postées avant la page vide, obtenu ${pagesNouvelles().length}`);

console.log("OK — arrêt par nouveauté, même règle Leboncoin / Bien'ici :");
console.log("   LBC  5·3·1·0 → 4 pages · page 1 à 0 → 1 page · nouveauté partout → plafond 15");
console.log("   BI   5·3·0   → 3 pages · page vide en 3 → 2 pages postées (n_pages = pages réellement lues)");
