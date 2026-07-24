// =============================================================================
// LA BUSE — ATLAS DES SURFACES (Bloc A · A1) — harnais Playwright v2
// -----------------------------------------------------------------------------
// TOUT ce que l'app montre, photographié : routes, 7 onglets de fiche, 17 outils
// du registre + outils O (y compris ceux SANS surface front — capturés en JSON
// brut, leur surface réelle d'aujourd'hui), projet (liste/kanban/tri), CRM,
// Vues, Sources, IA, flux d'entrée, états vide/chargement/erreur/succès.
//
// Contrat d'exhaustivité : le catalogue SURFACES ci-dessous EST l'inventaire.
// Chaque entrée finit « capturée » ou « impossible + raison » dans le manifest —
// jamais silencieusement absente. Convention : surface__etat__device.png.
//
// Usage :
//   node qa/atlas.mjs                          # local (BASE=http://127.0.0.1:8010/socle/)
//   LOGIN_BASE=http://127.0.0.1:8012 node qa/atlas.mjs        # + flux login local
//   MODE=prod BASE=https://app.labuse.immo/ LABUSE_QA_BASIC=u:p LABUSE_QA_PASSWORD=… \
//     node qa/atlas.mjs                        # passe de PARITÉ (subset, rythme humain)
//   GREP=fiche node qa/atlas.mjs               # re-run filtré (regex sur slug)
//
// Sortie : ~/labuse-atlas/<stamp>__<mode>/ (HORS git — politique binaires) avec
// index.html navigable (vignettes par section) + manifest.json. Deux runs du
// harnais = la comparaison avant/après de chaque mandat UI.
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { homedir } from 'node:os';

const MODE = process.env.MODE || 'local';
const BASE = (process.env.BASE || 'http://127.0.0.1:8010/socle/').replace(/\/?$/, '/');
const API = BASE.replace(/\/(socle|app)\/$/, '').replace(/\/$/, '');
const LOGIN_BASE = process.env.LOGIN_BASE || '';          // instance locale AVEC auth (rideau/login)
const GREP = process.env.GREP ? new RegExp(process.env.GREP) : null;
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = `${process.env.OUT || homedir() + '/labuse-atlas'}/${STAMP}__${MODE}`;
mkdirSync(OUT, { recursive: true });
// parité prod = rythme humain (jamais marteler la prod)
const PACE_MS = MODE === 'prod' ? 2500 : 0;

// ── manifest ────────────────────────────────────────────────────────────────
const manifest = [];   // {section, slug, etat, device, file?, ok, note}
function record(section, slug, etat, device, ok, note, file) {
  manifest.push({ section, slug, etat, device, ok, note: note || '', file: file || null });
  console.log(`  ${ok ? '📸' : '⚠'} ${slug}__${etat}__${device}${note ? ' — ' + note : ''}`);
}

// ── devices : le double viewport systématique (+ 1024 sur les écrans denses) ─
const DEVICES = [
  { name: 'desktop', viewport: { width: 1440, height: 900 } },
  { name: 'mobile', viewport: { width: 390, height: 844 }, touch: true },
];
const TABLET = { name: 'tablet', viewport: { width: 1024, height: 768 } };

// =============================================================================
// LE CATALOGUE — l'inventaire exécutable.
// Chaque surface : { slug, section, desc, dense?, devices?, run(ctx) }.
// ctx : { page, api, ids, shot(etat, note?), miss(etat, raison), app(...), goFiche(idu) }
// =============================================================================
const SURFACES = [];
const S = (o) => SURFACES.push(o);

// ── ENTRÉE ──────────────────────────────────────────────────────────────────
S({
  slug: 'entree__login', section: 'Entrée', desc: 'Page /login (pilote) — défaut + erreur mot de passe',
  async run(c) {
    const base = MODE === 'prod' ? API : LOGIN_BASE;
    if (!base) return c.miss('defaut', 'LOGIN_BASE absent (instance locale avec auth non lancée)');
    // contexte VIERGE : une session valide ferait rediriger /login vers l'app
    const ctx2 = await c.page.context().browser().newContext({ viewport: c.page.viewportSize(), httpCredentials });
    const p2 = await ctx2.newPage();
    try {
      await p2.goto(base + '/login', { waitUntil: 'networkidle' });
      await p2.waitForTimeout(500);
      await p2.screenshot({ path: `${OUT}/entree__login__defaut__${c.device}.png` });
      record(this.section, this.slug, 'defaut', c.device, true, 'page de connexion actuelle (rideau pilote)', `entree__login__defaut__${c.device}.png`);
      await p2.fill('input[type=password]', 'mauvais-mot-de-passe');
      await Promise.all([p2.waitForLoadState('networkidle'), p2.keyboard.press('Enter')]);
      await p2.waitForTimeout(500);
      await p2.screenshot({ path: `${OUT}/entree__login__erreur__${c.device}.png` });
      record(this.section, this.slug, 'erreur', c.device, true, 'mauvais mot de passe — message neutre + 401', `entree__login__erreur__${c.device}.png`);
    } finally { await ctx2.close(); }
  },
});
S({
  slug: 'entree__404-api', section: 'Entrée', desc: 'URL inconnue hors SPA → 404 JSON FastAPI (ce que voit un client sur une faute d’URL)',
  async run(c) {
    await c.page.goto(API + '/cette-page-n-existe-pas', { waitUntil: 'domcontentloaded' });
    await c.shot('defaut', '404 brut — aucun écran d’erreur habillé');
  },
});

// ── NAVIGATION / DASHBOARD ──────────────────────────────────────────────────
S({
  slug: 'nav__dashboard', section: 'Navigation', desc: 'Vue d’accueil (cartes) — analyse OFF puis ON', dense: true,
  async run(c) {
    await c.app();
    await c.shot('verdict-off', 'arrivée : verdict opt-in, carte neutre');
    await c.page.evaluate(() => window.__labuse.setVerdict(true));
    await c.page.waitForTimeout(2500);
    await c.shot('verdict-on', 'analyse activée : tiers colorés + compteurs');
  },
});
S({
  slug: 'nav__omnibox', section: 'Navigation', desc: 'Omnibox — saisie + suggestions',
  async run(c) {
    await c.app();
    await c.page.fill('[data-omnibox]', 'Saint-P');
    await c.page.waitForTimeout(900);
    await c.shot('suggestions', 'suggestions communes en saisie');
  },
});
S({
  slug: 'nav__popover-filtres', section: 'Navigation', desc: 'Popover « + Filtre » (multi-critères)',
  async run(c) {
    await c.app();
    await c.page.click('text=+ Filtre');
    await c.page.waitForTimeout(400);
    await c.shot('ouvert', 'les champs de filtre avancé');
  },
});
S({
  slug: 'nav__popover-communes', section: 'Navigation', desc: 'Sélecteur de commune (24 + Toute l’île)',
  async run(c) {
    await c.app();
    const b = await c.page.waitForSelector('[data-commune-select]', { timeout: 10000 }).catch(() => null);
    if (!b) return c.miss('ouvert', 'sélecteur commune non visible sur ce viewport');
    await b.click();
    await c.page.waitForTimeout(400);
    await c.shot('ouvert', 'liste des 24 communes');
  },
});
S({
  slug: 'nav__rail-outils', section: 'Navigation', desc: 'Tiroir Outils (3 groupes, phares ★)',
  async run(c) {
    await c.app();
    await c.page.click('text=Outils');
    await c.page.waitForSelector('[data-outil-group]');
    await c.shot('ouvert', 'le tiroir des outils');
  },
});
S({
  slug: 'nav__contexte-commune', section: 'Navigation', desc: 'Panneau contexte commune (SRU/ANRU/PLH/QPV)',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setCommune('Saint-Paul'));
    await c.page.waitForTimeout(1500);
    const btn = await c.page.$('[data-contexte-btn]');
    if (!btn) return c.miss('ouvert', 'bouton contexte introuvable (data-contexte-btn)');
    await btn.click();
    await c.page.waitForSelector('[data-contexte-panel]', { timeout: 8000 });
    await c.page.waitForTimeout(800);
    await c.shot('ouvert', 'SRU, ANRU, PLH, marché INSEE, QPV');
  },
});
S({
  slug: 'nav__entonnoir', section: 'Navigation', desc: 'Panneau entonnoir (motifs d’écartement)',
  async run(c) {
    await c.app();
    // l'entonnoir vit dans la section Résultats : il n'apparaît qu'analyse activée
    await c.page.evaluate(() => window.__labuse.setVerdict(true));
    await c.page.waitForTimeout(2000);
    const btn = await c.page.$('[data-entonnoir-btn]');
    if (!btn) return c.miss('ouvert', 'bouton entonnoir absent de cette vue');
    if (!(await btn.isVisible())) return c.miss('ouvert', 'bouton entonnoir NON VISIBLE sur ce viewport — constat d’audit (mobile)');
    await btn.click();
    await c.page.waitForSelector('[data-entonnoir-panel]', { timeout: 8000 });
    await c.shot('ouvert', 'l’entonnoir par motif');
  },
});

// ── CARTE ───────────────────────────────────────────────────────────────────
S({
  slug: 'carte__ile', section: 'Carte', desc: 'Île entière, tuiles MVT chargées', dense: true,
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setVerdict(true));
    await c.page.waitForTimeout(4000);                       // laisse les tuiles se poser
    await c.shot('defaut', 'vue île — tiers visibles');
  },
});
S({
  slug: 'carte__commune', section: 'Carte', desc: 'Zoom commune (Saint-Paul)', dense: true,
  async run(c) {
    await c.app();
    await c.page.evaluate(() => { window.__labuse.setVerdict(true); window.__labuse.setCommune('Saint-Paul'); });
    await c.page.waitForTimeout(5000);
    await c.shot('defaut', 'parcellaire de commune au zoom');
  },
});
S({
  slug: 'carte__couches', section: 'Carte', desc: 'Couches (zonage, overlays) — tiroir mobile / inline desktop',
  async run(c) {
    await c.app();
    const mob = await c.page.$('[data-couches-mobile]');
    if (mob && !(await mob.isVisible())) {
      await c.page.waitForTimeout(800);
      return c.shot('inline', 'couches inline (déclencheur tiroir présent mais masqué sur ce viewport)');
    }
    if (!mob) {
      // desktop : pas de tiroir, les couches sont inline dans le panneau gauche
      await c.page.waitForTimeout(800);
      return c.shot('inline', 'couches visibles dans le panneau gauche (desktop)');
    }
    await mob.click();
    await c.page.waitForTimeout(800);
    await c.shot('ouvert', 'le tiroir des couches (mobile)');
  },
});

// ── LISTE / RÉSULTATS ───────────────────────────────────────────────────────
S({
  slug: 'liste__resultats', section: 'Liste', desc: 'Panneau résultats — succès et vide',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setVerdict(true));
    await c.page.waitForSelector('[data-results-scroll]', { timeout: 15000 }).catch(() => {});
    await c.page.waitForTimeout(2000);
    await c.shot('succes', 'liste de parcelles classées');
    // état vide honnête : une recherche IDU sans résultat
    await c.page.fill('[data-omnibox]', 'ZZZZ99999');
    await c.page.keyboard.press('Enter');
    await c.page.waitForTimeout(1200);
    await c.shot('vide', 'aucun résultat — le message que voit le client');
  },
});

// ── FICHE : les 7 onglets sur une brûlante ──────────────────────────────────
const ONGLETS = [
  ['synthese', 'Synthèse'], ['regles', 'Règles'], ['risques', 'Risques'],
  ['marche', 'Marché'], ['proprio', 'Proprio'], ['faisabilite', 'Faisabilité'], ['bilan', 'Bilan'],
];
for (const [key, label] of ONGLETS) {
  S({
    slug: `fiche__${key}`, section: 'Fiche', desc: `Onglet ${label} (brûlante)`,
    async run(c) {
      await c.goFiche(c.ids.brulante);
      if (key !== 'synthese') {
        const tab = c.page.locator(`aside button:has-text("${label}")`).first();
        if (!(await tab.count())) return c.miss('defaut', `onglet « ${label} » introuvable`);
        await tab.click();
        await c.page.waitForTimeout(1500);
      }
      await c.shot('defaut', `fiche ${c.ids.brulante} — ${label}`);
    },
  });
}
S({
  slug: 'fiche__calculette', section: 'Fiche', desc: 'Calculette charge foncière (onglet Faisabilité)',
  async run(c) {
    await c.goFiche(c.ids.brulante);
    await c.page.locator('aside button:has-text("Faisabilité")').first().click();
    await c.page.waitForSelector('[data-calculette]', { timeout: 10000 });
    await c.page.locator('[data-calculette]').scrollIntoViewIfNeeded();
    await c.page.waitForTimeout(400);
    await c.shot('defaut', 'la calculette rapatriée (M11 C)');
  },
});
S({
  slug: 'fiche__pourquoi-pas', section: 'Fiche', desc: 'Onglet « Pourquoi pas ? » (écartée, O3)',
  async run(c) {
    await c.goFiche(c.ids.ecartee);
    await c.shot('bandeau', 'bandeau écartée en tête de fiche');
    const tab = c.page.locator('aside button:has-text("Pourquoi pas ?")').first();
    if (!(await tab.count())) return c.miss('motifs', 'onglet absent sur cette écartée');
    await tab.click();
    await c.page.waitForSelector('[data-pourquoi-pas]', { timeout: 10000 });
    await c.shot('motifs', 'motifs hiérarchisés RÉDHIBITOIRE/VIGILANCE');
  },
});
S({
  slug: 'fiche__badge-defisc', section: 'Fiche', desc: 'Badge fenêtre défiscalisation (A-1)',
  async run(c) {
    if (!c.ids.defisc) return c.miss('defaut', 'aucun IDU à fenêtre défisc active trouvé');
    await c.goFiche(c.ids.defisc);
    await c.shot('defaut', `fiche ${c.ids.defisc} — badge défisc visible en synthèse`);
  },
});
S({
  slug: 'fiche__badge-caduc', section: 'Fiche', desc: 'Badge PC caduc (cycle 2)',
  async run(c) {
    if (!c.ids.caduc) return c.miss('defaut', 'aucun IDU pc_caducs trouvé');
    await c.goFiche(c.ids.caduc);
    await c.shot('defaut', `fiche ${c.ids.caduc} — badge Estimé (wording non-accusatoire)`);
  },
});
S({
  slug: 'fiche__tiers', section: 'Fiche', desc: 'Une fiche de chaque tier (chaude → à creuser → réserve)',
  async run(c) {
    for (const t of ['chaude', 'a_creuser', 'reserve_fonciere']) {
      if (!c.ids[t]) { c.miss(t, `pas d'IDU ${t}`); continue; }
      await c.goFiche(c.ids[t]);
      await c.shot(t, `fiche ${c.ids[t]} (${t})`);
    }
  },
});
S({
  slug: 'fiche__inconnue', section: 'Fiche', desc: 'Parcelle inconnue — l’écran d’erreur réel',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.select('97499000ZZ9999'));
    await c.page.waitForSelector('[data-fiche-erreur]', { timeout: 15000 }).catch(() => {});
    await c.page.waitForTimeout(800);
    await c.shot('erreur', 'IDU inexistant : fiche indisponible + bouton réessayer');
  },
});
S({
  slug: 'fiche__chargement', section: 'Fiche', desc: 'État de chargement (réseau ralenti artificiellement)',
  async run(c) {
    await c.app();
    await c.page.route('**/parcels/**', async (route) => {
      await new Promise((r) => setTimeout(r, 4000));
      try { await route.continue(); } catch { /* la route a pu être démontée entre-temps */ }
    });
    await c.page.evaluate((idu) => window.__labuse.select(idu), c.ids.brulante);
    await c.page.waitForTimeout(1200);
    await c.shot('chargement', 'ce que voit le client pendant l’attente');
    await c.page.unroute('**/parcels/**');
  },
});
S({
  slug: 'fiche__429', section: 'Fiche', desc: 'Rate-limit 429 — message dédié (mock réseau, recette e2e_429)',
  async run(c) {
    await c.app();
    await c.page.route(`**/parcels/${c.ids.brulante}*`, async (route) => {
      try { await route.fulfill({ status: 429, contentType: 'application/json', body: '{"detail":"rate limited"}' }); } catch { /* idem */ }
    });
    await c.page.evaluate((idu) => window.__labuse.select(idu), c.ids.brulante);
    await c.page.waitForSelector('[data-ratelimit-429]', { timeout: 10000 }).catch(() => {});
    await c.shot('erreur', 'le 429 habillé (pas un écran blanc)');
    await c.page.unroute(`**/parcels/${c.ids.brulante}*`);
  },
});
S({
  slug: 'fiche__signalement', section: 'Fiche', desc: 'Formulaire signalement (QA humaine, M9) — ouvert, sans envoi',
  async run(c) {
    await c.goFiche(c.ids.brulante);
    const b = await c.page.$('[data-signaler-erreur]');
    if (!b) return c.miss('ouvert', 'bouton signalement introuvable');
    await b.click();
    await c.page.waitForSelector('[data-signalement-form]', { timeout: 8000 });
    await c.shot('ouvert', 'form ouvert — PAS soumis (garde-fou : zéro écriture)');
  },
});
S({
  slug: 'fiche__askbar', section: 'Fiche', desc: 'Barre de question IA (M11 surface A) — ouverte, sans envoi',
  async run(c) {
    await c.goFiche(c.ids.brulante);
    const b = await c.page.$('[data-askbar-open]');
    if (!b) return c.miss('ouvert', 'askbar introuvable sur la fiche');
    await b.click();
    await c.page.waitForSelector('[data-askbar]', { timeout: 8000 });
    await c.shot('ouvert', 'poser une question à LA fiche');
  },
});
S({
  slug: 'fiche__exports', section: 'Fiche', desc: 'Boutons d’export (PDF · Dossier · Banquier)',
  async run(c) {
    await c.goFiche(c.ids.brulante);
    const b = c.page.locator('[data-banquier-btn], a:has-text("Banquier")').first();  // B1.5 : bouton à états
    if (await b.count()) await b.scrollIntoViewIfNeeded();
    await c.shot('defaut', 'la rangée d’exports en bas de fiche');
  },
});

// ── OUTILS DU REGISTRE (17) — via __labuse.setModule ────────────────────────
const REGISTRE = [
  ['scoring-v2', 'M25 Scoring v2 (P)'], ['programme', 'M22 Faisabilité programme'],
  ['division', 'M01 Division parcellaire'], ['fantome', 'M07 Foncier fantôme'],
  ['patrimoine', 'M02 Scan patrimoine'], ['bailleur', 'M06 Mode bailleur'],
  ['matching', 'M19 Matching promoteurs'], ['assemblage', 'M16 Assemblage'],
  ['barometre', 'M18 Baromètre foncier'], ['permis', 'M03 Radar permis'],
  ['promesses', 'M04 Promesses mortes'], ['velocite', 'M05 Vélocité admin'],
  ['simulplu', 'M15 Simulateur PLU'], ['zan', 'M17 Simulateur ZAN'],
  ['temps', 'M08 Remonter le temps'], ['duediligence', 'M10 Due diligence'],
  ['courriers', 'M09 Courrier propriétaire'],
  // BLOC B partie 2 : les outils O ont désormais une UI (verdict Vic sur maquettes)
  ['o5-servitudes', 'O5 Servitudes invisibles'], ['o6-comparateur', 'O6 Comparateur de communes'],
  ['o7-carnet', 'O7 Carnet de secteur'], ['o9-rarete', 'O9 Pipeline rareté'],
  ['o10-bascules', 'O10 Bascules datées'],
];
for (const [key, label] of REGISTRE) {
  S({
    slug: `outil__${key}`, section: 'Outils (registre)', desc: label,
    async run(c) {
      await c.app();
      await c.page.evaluate((k) => window.__labuse.setModule(k), key);
      await c.page.waitForSelector('[data-module-breadcrumb]', { timeout: 12000 }).catch(() => {});
      await c.page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await c.page.waitForTimeout(1500);
      await c.shot('defaut', label);
    },
  });
}
// états supplémentaires ciblés sur deux outils du registre
S({
  slug: 'outil__patrimoine-recherche', section: 'Outils (registre)', desc: 'M02 — recherche PM avec suggestions',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setModule('patrimoine'));
    await c.page.waitForSelector('[data-module-breadcrumb]', { timeout: 12000 }).catch(() => {});
    const input = c.page.locator('[data-outil="patrimoine"] input, aside input').first();
    if (!(await input.count())) return c.miss('suggestions', 'champ de recherche M02 introuvable');
    await input.fill('SEM');
    await c.page.waitForTimeout(1500);
    await c.shot('suggestions', 'suggestions SIREN/nom en saisie');
  },
});

// ── OUTILS O — surfaces réelles (UI quand elle existe, JSON brut sinon) ─────
S({
  slug: 'outil__o2-scoreur', section: 'Outils O', desc: 'O2 Scoreur d’adresse — vide, résultat, hors-base',
  async run(c) {
    await c.app();
    // M12-D4 : le scoreur vit désormais dans le tiroir Outils (rail → carte).
    await c.page.click('button[title="Outils"]');
    await c.page.click('[data-outil="scoreur-adresse"]');
    await c.page.waitForSelector('[data-scoreur-adresse]');
    await c.shot('vide', 'panneau ouvert, champ adresse + prix');
    await c.page.fill('[data-scoreur-adresse]', '12 rue du Général de Gaulle, Saint-Paul');
    await c.page.waitForTimeout(600);   // autocomplétion BAN (M12-D)
    await c.page.keyboard.press('Enter');
    await c.page.waitForSelector('[data-scoreur-resultat]', { timeout: 25000 }).catch(() => {});
    await c.page.waitForTimeout(800);
    await c.shot('resultat', 'seconde opinion sur une adresse en base');
    await c.page.fill('[data-scoreur-adresse]', '1 rue de la Paix, 75002 Paris');
    await c.page.waitForTimeout(600);
    await c.page.keyboard.press('Enter');
    await c.page.waitForTimeout(6000);
    await c.shot('hors-base', 'adresse hors périmètre — le refus propre');
  },
});
S({
  slug: 'outil__o1-banquier-pdf', section: 'Outils O', desc: 'O1 Dossier banquier — 1ʳᵉ page du PDF rendue', devices: ['desktop'],
  async run(c) {
    const url = `${API}/dossier-banquier/${c.ids.brulante}.pdf`;
    const resp = await c.page.request.get(url, { timeout: 90000 });
    if (!resp.ok()) return c.miss('page1', `PDF en échec (${resp.status()})`);
    const pdfPath = `${OUT}/_banquier.pdf`;
    writeFileSync(pdfPath, Buffer.from(await resp.body()));
    try {
      // sips (macOS) rend la page 1 — le visuel exact que reçoit un financeur
      execFileSync('sips', ['-s', 'format', 'png', pdfPath, '--out', `${OUT}/outil__o1-banquier-pdf__page1__pdf.png`]);
      record(this.section, this.slug, 'page1', 'pdf', true, `1ʳᵉ page du dossier ${c.ids.brulante}`, `outil__o1-banquier-pdf__page1__pdf.png`);
    } catch (e) { c.miss('page1', 'conversion sips en échec : ' + String(e).slice(0, 80)); }
  },
});
// Outils O sans surface front : la vérité = JSON brut dans le navigateur.
// BLOC B partie 2 : o5/o6/o7/o9 sont devenus des MODULES (boucle REGISTRE ci-dessous) ;
// o4 est un bloc de l'onglet Règles (capturé par fiche__regles) ; o10 = outil__o10-bascules.
const O_JSON = [
  ['o4-traducteur', 'O4 Traducteur PLU', (ids) => `/traducteur-plu/${ids.brulante}`, 'POST'],
];
for (const [key, label, path, method] of O_JSON) {
  S({
    slug: `outil__${key}`, section: 'Outils O', desc: `${label} — AUCUNE surface front (constat) : JSON brut`, devices: ['desktop'],
    async run(c) {
      const url = API + path(c.ids);
      if (method === 'POST') {
        const r = await c.page.request.post(url, { data: {}, timeout: 30000 });
        const body = await r.text();
        writeFileSync(`${OUT}/outil__${key}__reponse.json`, body);
        return c.miss('json', `endpoint POST sans UI — réponse archivée (${r.status()}, outil__${key}__reponse.json)`);
      }
      await c.page.goto(url, { waitUntil: 'domcontentloaded' });
      await c.shot('json', 'la surface actuelle vue du client : du JSON');
    },
  });
}
// BLOC B : o10 (surface D) = module outil__o10-bascules (boucle REGISTRE).

// ── PROJET ──────────────────────────────────────────────────────────────────
S({
  slug: 'projet__liste', section: 'Projet', desc: 'Mes projets — cartes + DedupBanner',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('projets'));
    await c.page.waitForSelector('[data-projet-card], [data-projets-vide]', { timeout: 12000 });
    await c.page.waitForTimeout(1200);
    const dedup = await c.page.$('[data-dedup-banner]');
    await c.shot('defaut', dedup ? 'liste + bannière doublons visible' : 'liste des projets');
  },
});
// ouvre le projet le plus « vivant » (des parcelles à trier de préférence)
async function ouvreKanban(c) {
  await c.app();
  await c.page.evaluate(() => window.__labuse.setView('projets'));
  await c.page.waitForSelector('[data-projet-ouvrir], [data-projets-vide]', { timeout: 12000 });
  const cards = c.page.locator('[data-projet-card]');
  const n = await cards.count();
  let target = null;
  for (let i = 0; i < n; i++) {                       // priorité : un projet avec du « à trier »
    const txt = await cards.nth(i).textContent();
    if (/[1-9]\d*\s*(à trier|proposée)/i.test(txt || '')) { target = cards.nth(i); break; }
  }
  const btn = (target || cards.first()).locator('[data-projet-ouvrir]');
  if (!(await btn.count())) return false;
  await btn.click();
  await c.page.waitForSelector('[data-kanban-col]', { timeout: 15000 }).catch(() => {});
  await c.page.waitForTimeout(2000);
  return !!(await c.page.$('[data-kanban-col]'));
}
S({
  slug: 'projet__kanban', section: 'Projet', desc: 'Kanban 3 colonnes d’un projet peuplé', dense: true,
  async run(c) {
    if (!(await ouvreKanban(c))) return c.miss('defaut', 'aucun kanban ouvrable');
    await c.shot('defaut', 'colonnes À analyser / Retenues / Écartées peuplées');
  },
});
S({
  slug: 'projet__tinder', section: 'Projet', desc: 'Parcours de tri (lancé depuis le kanban) — carte + 3 boutons',
  async run(c) {
    if (!(await ouvreKanban(c))) return c.miss('defaut', 'aucun kanban ouvrable');
    const trier = await c.page.$('[data-kanban-trier]');
    if (!trier) return c.miss('defaut', 'bouton « Trier » absent (rien à trier dans ce projet)');
    if (!(await trier.isVisible())) return c.miss('defaut', 'bouton « Trier » NON VISIBLE sur ce viewport — constat d’audit (mobile)');
    try { await trier.click({ timeout: 8000 }); }
    catch { return c.miss('defaut', 'bouton « Trier » visible mais NON CLIQUABLE sur ce viewport (recouvert) — constat d’audit (mobile)'); }
    await c.page.waitForSelector('[data-decision-card]', { timeout: 15000 }).catch(() => {});
    const card = await c.page.$('[data-decision-card]');
    if (!card) return c.miss('defaut', 'pas de carte de décision — AUCUN clic de tri (zéro écriture)');
    await c.shot('defaut', 'Écarter · À analyser · Retenir — aucun bouton de décision cliqué');
    const plus = await c.page.$('[data-parcours-plus]');
    if (plus) { await plus.click(); await c.page.waitForTimeout(1500); await c.shot('chercher-plus', 'le panneau « chercher plus »'); }
  },
});

// ── CRM ─────────────────────────────────────────────────────────────────────
S({
  slug: 'crm__kanban', section: 'CRM', desc: 'Pipeline prospection (colonnes + cartes)', dense: true,
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('crm'));
    await c.page.waitForTimeout(2500);
    await c.shot('defaut', 'le pipeline avec ses entrées réelles');
  },
});

// ── VUES (SEGMENTS) ─────────────────────────────────────────────────────────
S({
  slug: 'vues__accueil', section: 'Vues', desc: 'Moteur de vues — presets + hero',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('segments'));
    await c.page.waitForSelector('[data-seg-page], [data-vues-hero]', { timeout: 12000 }).catch(() => {});
    await c.page.waitForTimeout(1500);
    await c.shot('defaut', 'la page Vues');
  },
});
S({
  slug: 'vues__preset-resultat', section: 'Vues', desc: 'Une vue ouverte (résultats du preset)',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('segments'));
    await c.page.waitForSelector('[data-seg-preset-open]', { timeout: 12000 }).catch(() => {});
    const b = c.page.locator('[data-seg-preset-open]').first();
    if (!(await b.count())) return c.miss('resultat', 'aucun preset ouvrable');
    await b.click();
    await c.page.waitForSelector('[data-seg-row], [data-seg-count]', { timeout: 20000 }).catch(() => {});
    await c.page.waitForTimeout(1500);
    await c.shot('resultat', 'résultats + export + argumentaire');
  },
});

// ── IA ──────────────────────────────────────────────────────────────────────
S({
  slug: 'ia__copilote', section: 'IA', desc: 'Copilote — les deux portes',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('ia'));
    await c.page.waitForSelector('[data-porte-recherche]', { timeout: 12000 });
    await c.shot('defaut', 'porte Recherche NL + porte Montage projet');
  },
});
S({
  slug: 'ia__recherche-nl', section: 'IA', desc: 'Recherche NL — restitution réelle (1 appel IA)',
  async run(c) {
    if (MODE === 'prod') return c.miss('restitution', 'appel IA réservé au local (coût/parité inutile)');
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('ia'));
    await c.page.waitForSelector('[data-porte-recherche]', { timeout: 12000 });
    const input = c.page.locator('[data-porte-recherche] input, [data-porte-recherche] textarea').first();
    if (!(await input.count())) return c.miss('restitution', 'champ NL introuvable');
    await input.fill('terrains de plus de 1000 m² en zone U à Saint-Paul');
    await c.page.keyboard.press('Enter');
    await c.page.waitForSelector('[data-ia-restitution], [data-ia-aggregate], [data-ia-zero]', { timeout: 45000 }).catch(() => {});
    await c.page.waitForTimeout(1000);
    await c.shot('restitution', 'compteur + top 3 + voir tout');
  },
});
S({
  slug: 'ia__entretien', section: 'IA', desc: 'Porte Montage projet (entretien)',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('ia'));
    const p = await c.page.$('[data-porte-projet]');
    if (!p) return c.miss('defaut', 'porte projet introuvable');
    await p.click();
    await c.page.waitForSelector('[data-entretien], [data-decrire-projet]', { timeout: 12000 }).catch(() => {});
    await c.page.waitForTimeout(800);
    await c.shot('defaut', 'l’entrée de l’entretien structuré');
  },
});
S({
  slug: 'ia__mode-degrade', section: 'IA', desc: 'IA en mode dégradé (stub) — instance sans clé',
  async run(c) {
    if (!LOGIN_BASE) return c.miss('defaut', 'nécessite l’instance secondaire (LOGIN_BASE) démarrée sans clé IA');
    // l'instance B tourne SANS clé Anthropic : le bandeau dégradé est sa vérité
    await c.page.goto(LOGIN_BASE + '/socle/', { waitUntil: 'networkidle' }).catch(() => {});
    const pw = process.env.LOGIN_PASSWORD || '';
    if (await c.page.$('input[type=password]')) {
      await c.page.fill('input[type=password]', pw);
      await Promise.all([c.page.waitForLoadState('networkidle'), c.page.keyboard.press('Enter')]);
      await c.page.goto(LOGIN_BASE + '/socle/', { waitUntil: 'networkidle' }).catch(() => {});
    }
    await c.page.evaluate(() => window.__labuse && window.__labuse.setView('ia')).catch(() => {});
    await c.page.waitForSelector('[data-ia-badge-stub], [data-porte-recherche]', { timeout: 12000 }).catch(() => {});
    await c.page.waitForTimeout(800);
    await c.shot('defaut', 'bandeau mode dégradé visible');
  },
});

// ── SOURCES ─────────────────────────────────────────────────────────────────
S({
  slug: 'sources__page', section: 'Sources', desc: 'Fraîcheur des données (badges, « données jusqu’au X · ingéré le Y »)',
  async run(c) {
    await c.app();
    await c.page.evaluate(() => window.__labuse.setView('sources'));
    await c.page.waitForSelector('[data-sources-page]', { timeout: 12000 });
    await c.page.waitForTimeout(1500);
    await c.shot('defaut', 'la page Sources complète');
  },
});

// ── ÉTATS SYSTÈME non capturables (documentés, jamais silencieux) ───────────
S({
  slug: 'etat__tooltips-natifs', section: 'États système', desc: 'Tooltips ×N / jauge / TierBadge', devices: ['desktop'],
  async run(c) {
    c.miss('hover', 'tooltips natifs (attribut title) : invisibles en screenshot headless — FINDING : passer en tooltips custom pour une app premium');
  },
});
S({
  slug: 'etat__error-boundary', section: 'États système', desc: 'ErrorBoundary React (crash JS)', devices: ['desktop'],
  async run(c) {
    c.miss('crash', 'non provocable sans injecter un crash dans le bundle (interdit : zéro modification produit)');
  },
});
S({
  slug: 'etat__rideau-basic-auth', section: 'États système', desc: 'Rideau Caddy 401 (prod)', devices: ['desktop'],
  async run(c) {
    if (MODE !== 'prod') return c.miss('defaut', 'rideau = prod uniquement (passe de parité)');
    // sans credentials : le navigateur montre sa boîte de dialogue NATIVE (hors DOM, non
    // capturable) — on capture la page 401 rendue derrière, la seule vérité photographiable.
    const ctx2 = await c.page.context().browser().newContext({ viewport: c.page.viewportSize() });
    const p2 = await ctx2.newPage();
    await p2.goto(BASE, { waitUntil: 'domcontentloaded' }).catch(() => {});
    await p2.waitForTimeout(1500);
    await p2.screenshot({ path: `${OUT}/etat__rideau-basic-auth__defaut__desktop.png` });
    record(this.section, this.slug, 'defaut', 'desktop', true,
      'corps 401 derrière la boîte native (la boîte elle-même est hors DOM)', 'etat__rideau-basic-auth__defaut__desktop.png');
    await ctx2.close();
  },
});

// =============================================================================
// PARITÉ PROD : sous-ensemble ciblé (rideau réel, login réel, Sources, une fiche)
// =============================================================================
const PARITY = new Set([
  'entree__login', 'etat__rideau-basic-auth', 'nav__dashboard', 'sources__page',
  'fiche__synthese', 'carte__ile',
]);

// =============================================================================
// MOTEUR
// =============================================================================
async function discoverIds(request) {
  const ids = {};
  for (const t of ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee']) {
    try {
      const r = await request.get(`${API}/parcels?source=q_v7_defisc&tiers=${t}&limit=1&sort=rang`);
      ids[t] = (await r.json())[0]?.idu || null;
    } catch { ids[t] = null; }
  }
  // exemplaires badges (découverts en base locale au moment du run — surchargeables)
  ids.defisc = process.env.ATLAS_IDU_DEFISC || '97401000AL0711';
  ids.caduc = process.env.ATLAS_IDU_CADUC || '97416000DO0273';
  return ids;
}

const browser = await chromium.launch();
const httpCredentials = process.env.LABUSE_QA_BASIC
  ? { username: process.env.LABUSE_QA_BASIC.split(':')[0], password: process.env.LABUSE_QA_BASIC.split(':').slice(1).join(':') }
  : undefined;

// découverte des données réelles (une seule fois)
const bootCtx = await browser.newContext({ httpCredentials });
const bootPage = await bootCtx.newPage();
if (MODE === 'prod' && process.env.LABUSE_QA_PASSWORD) {           // login app (session)
  await bootPage.request.post(`${API}/login`, { data: { password: process.env.LABUSE_QA_PASSWORD } }).catch(() => {});
}
const ids = await discoverIds(bootPage.request);
console.log('IDU découverts :', JSON.stringify(ids));
const storageState = await bootCtx.storageState();
await bootCtx.close();

for (const device of DEVICES) {
  console.log(`\n═══ ${device.name} (${device.viewport.width}×${device.viewport.height}) ═══`);
  await runDevice(device);
}
// breakpoint intermédiaire : uniquement les écrans denses
console.log(`\n═══ tablet (1024×768) — écrans denses ═══`);
await runDevice(TABLET, (s) => s.dense);

async function runDevice(device, extraFilter) {
  const context = await browser.newContext({
    viewport: device.viewport, httpCredentials, storageState,
    hasTouch: !!device.touch, isMobile: !!device.touch,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  let appLoaded = false;

  for (const surface of SURFACES) {
    if (GREP && !GREP.test(surface.slug)) continue;
    if (MODE === 'prod' && !PARITY.has(surface.slug)) continue;
    if (surface.devices && !surface.devices.includes(device.name)) continue;
    if (extraFilter && !extraFilter(surface)) continue;

    const ctx = {
      page, ids, api: API, device: device.name,
      shot: async (etat, note) => {
        await page.waitForTimeout(500);
        const file = `${surface.slug}__${etat}__${device.name}.png`;
        await page.screenshot({ path: `${OUT}/${file}`, fullPage: false });
        record(surface.section, surface.slug, etat, device.name, true, note, file);
        if (PACE_MS) await page.waitForTimeout(PACE_MS);
      },
      miss: (etat, raison) => record(surface.section, surface.slug, etat, device.name, false, raison),
      // charge l'app — rechargement COMPLET à chaque surface : zéro pollution d'état
      // (tiroir resté ouvert, recherche précédente…) entre deux captures.
      app: async () => {
        await page.goto(BASE, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('[data-omnibox]', { timeout: 30000 });
        await page.waitForTimeout(appLoaded ? 900 : 1800);
        appLoaded = true;
      },
      goFiche: async (idu) => {
        await ctx.app();
        await page.evaluate((i) => { window.__labuse.setVerdict(true); window.__labuse.select(i); }, idu);
        await page.waitForSelector('[data-fiche-adresse], [data-fiche-erreur]', { timeout: 25000 }).catch(() => {});
        await page.waitForTimeout(1200);
      },
    };
    try {
      await surface.run.call(surface, ctx);
    } catch (e) {
      record(surface.section, surface.slug, 'run', device.name, false, String(e).slice(0, 140));
      appLoaded = false;                                   // l'état du SPA est suspect : recharge
    }
  }
  await context.close();
}

await browser.close();

// =============================================================================
// INDEX NAVIGABLE — le document de travail de l'audit
// =============================================================================
const bySection = {};
for (const m of manifest) (bySection[m.section] ||= {})[m.slug] ||= [], bySection[m.section][m.slug].push(m);
const ok = manifest.filter((m) => m.ok).length;
const ko = manifest.length - ok;
const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LA BUSE — Atlas des surfaces (${STAMP} · ${MODE})</title>
<style>
  body{background:#060A08;color:#C9DCD1;font:14px/1.5 -apple-system,Inter,sans-serif;margin:0;padding:24px 32px}
  h1{color:#ECF5EF;font-size:20px} h2{color:#5CE6A1;font-size:15px;margin:32px 0 8px;border-bottom:1px solid #1B2620;padding-bottom:6px}
  h3{color:#ECF5EF;font-size:13px;margin:18px 0 6px;font-weight:600}
  .meta{color:#8FA69A;font-size:12px}
  .grid{display:flex;flex-wrap:wrap;gap:12px}
  figure{margin:0;width:300px} figure.mobile{width:120px}
  img{width:100%;border:1px solid #1B2620;border-radius:6px;display:block;background:#0B100D}
  figcaption{font-size:11px;color:#8FA69A;padding:4px 2px} figcaption b{color:#C9DCD1;font-weight:500}
  .miss{border:1px dashed #E8695A55;border-radius:6px;padding:10px 12px;font-size:12px;color:#E8695A;width:300px}
  .miss b{color:#ECF5EF} a{color:inherit;text-decoration:none}
  code{font-family:ui-monospace,monospace;font-size:11px;color:#5C7268}
</style></head><body>
<h1>LA BUSE — Atlas des surfaces</h1>
<p class="meta">${STAMP} · mode ${MODE} · base ${BASE} · <b style="color:#5CE6A1">${ok} captures</b> · ${ko} impossibles (documentées) · convention <code>surface__etat__device.png</code></p>
${Object.entries(bySection).map(([sec, slugs]) => `<h2>${sec}</h2>` +
  Object.entries(slugs).map(([slug, entries]) => {
    const desc = SURFACES.find((s) => s.slug === slug)?.desc || '';
    return `<h3>${slug} <span class="meta">— ${desc}</span></h3><div class="grid">` +
      entries.map((m) => m.ok
        ? `<figure class="${m.device}"><a href="${m.file}" target="_blank"><img loading="lazy" src="${m.file}"></a><figcaption><b>${m.etat}</b> · ${m.device}${m.note ? '<br>' + m.note : ''}</figcaption></figure>`
        : `<div class="miss"><b>${m.etat} · ${m.device}</b> — impossible :<br>${m.note}</div>`).join('') + '</div>';
  }).join('')).join('')}
</body></html>`;
writeFileSync(`${OUT}/index.html`, html);
writeFileSync(`${OUT}/manifest.json`, JSON.stringify({ stamp: STAMP, mode: MODE, base: BASE, ok, ko, entries: manifest }, null, 1));
console.log(`\n${ok} captures, ${ko} impossibles documentées → ${OUT}/index.html`);
process.exit(ok >= (MODE === 'prod' ? 5 : 40) ? 0 : 1);
