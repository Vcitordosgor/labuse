# BLOC A — L'ATLAS, LA MESURE, LA PORTE (rapport, STOP final)

Branche `tech/bloc-a-atlas`. **Mandat de mesure et de conception : zéro modification du produit**
(ni code app, ni config prod, ni DB — tenu ; seuls livrables code : le harnais `qa/atlas.mjs` et
deux maquettes `docs/mockups/login_*.html`). Suite locale **1088 verts / 0 échec** (env :
`LABUSE_DATABASE_URL` + `PROJ_DATA`, cf. mémoires), golden **116/116**.

---

## A1 · L'ATLAS

### Le contrat d'exhaustivité
L'inventaire est ENCODÉ dans le harnais (`qa/atlas.mjs`, catalogue `SURFACES`) : chaque entrée finit
**capturée** ou **impossible avec sa raison** dans `manifest.json` — jamais silencieusement absente.

**Bilan : 71 surfaces · 173 entrées surface×état×device — 167 captures (149 locales + 18 parité prod), 6 impossibles documentées.**

| Section | Surfaces | Captures | Impossibles |
|---|---|---|---|
| Entrée (login, 404) | 2 | 6 | 0 |
| Navigation (dashboard, omnibox, popovers, rail, contexte, entonnoir) | 7 | 17 | 1 |
| Carte (île, commune, couches) | 3 | 8 | 0 |
| Liste résultats (succès + vide) | 1 | 4 | 0 |
| Fiche (7 onglets + calculette + pourquoi-pas + badges défisc/caduc + tiers + inconnue + chargement + 429 + signalement + askbar + exports) | 18 | 42 | 0 |
| Outils du registre (17 modules M01→M25 + état recherche M02) | 18 | 36 | 0 |
| Outils O (O1 PDF p.1, O2 vide/résultat/hors-base, O4-O7/O9/O10) | 8 | 12 | 1 |
| Projet (liste, kanban, tri Tinder + chercher-plus) | 3 | 7 | 1 |
| CRM (pipeline) | 1 | 3 | 0 |
| Vues (accueil + preset ouvert) | 2 | 4 | 0 |
| IA (copilote, NL réelle, entretien, mode dégradé) | 4 | 8 | 0 |
| Sources | 1 | 2 | 0 |
| États système (tooltips, ErrorBoundary, rideau) | 3 | 0 | 3 |

Double viewport systématique **1440×900 + 390×844**, breakpoint **1024×768** sur les écrans denses
(dashboard, carte, kanbans). Données réelles représentatives : brûlante n°1 `97423000AB1908`, une
fiche par tier, écartée avec « Pourquoi pas ? », badge défisc `97401000AL0711`, badge caduc
`97416000DO0273`, projet peuplé (49 parcelles, 3 statuts), CRM réel (26 entrées), restitution NL
réelle (1 appel IA local). États d'erreur PROVOQUÉS en local, jamais en prod : mauvais mot de passe
(instance secondaire :8012 avec auth), 429 (mock réseau, recette e2e_429), parcelle inconnue,
chargement (réseau ralenti), IA dégradée (instance sans clé).

### Les 6 impossibles (toutes documentées au manifest)
1. **O4 traducteur PLU** : endpoint POST sans UI — réponse JSON archivée à côté des captures.
2. **Tooltips ×N / jauge / TierBadge** : attributs `title` natifs → invisibles en headless.
   **Finding : une app premium veut des tooltips custom** (stylés DA, capturables, mobiles).
3. **ErrorBoundary** : non provocable sans injecter un crash (interdit du mandat).
4. **Rideau basic auth en local** : capturé en prod (le dialogue navigateur est hors DOM ; la page
   401 derrière est photographiée).
5. **Entonnoir en mobile** : bouton **non visible au viewport 390** — constat d'audit.
6. **« Trier » (tri Tinder) en mobile** : visible mais **non cliquable** (recouvert) — constat d'audit.

### Constat structurant pour l'audit
**O4 (traducteur), O5 (servitudes), O6 (comparateur), O7 (carnet), O9 (rareté), O10 (surface D) n'ont
AUCUNE surface front** — leur « écran » aujourd'hui est du JSON brut (capturé tel quel, section
« Outils O » de l'index). Le front n'expose que O1 (bouton Banquier), O2 (scoreur) et O3 (onglet
Pourquoi pas). À trancher au bloc consolidation : les brancher au registre d'outils, ou assumer
l'API-first.

### Le livrable
- **Atlas local** : `~/labuse-atlas/2026-07-22-11-10__local/index.html` (149 captures, 50 Mo, hors git)
- **Parité prod** : `~/labuse-atlas/2026-07-22-11-20__prod/index.html` (18 captures : rideau réel,
  login réel, dashboard, carte, fiche, Sources — **parité visuelle confirmée**, à rythme humain)
- Convention stricte `surface__etat__device.png`, index navigable par section, vignettes cliquables,
  impossibles affichés en rouge avec leur raison. Deux runs du harnais = l'avant/après de chaque
  mandat UI. Re-run filtré : `GREP=fiche node qa/atlas.mjs`.

---

## A2 · LA MESURE (chiffres bruts en annexe)

### Le fait qui change la lecture
**RTT Mac→VPS mesuré : 17 ms** — pas d'océan depuis CE poste. L'écart Mac/VPS est donc quasi nul et
**tout ce qui est lent est lent CÔTÉ SERVEUR**. (Les clients réunionnais, eux, paieront ~180-200 ms
de RTT — l'argument edge/CDN vaut pour eux, pas pour ce poste.)

### Timings API (p50, 15 runs, session réelle) — serveur pur (VPS localhost) vs Mac→prod

| Endpoint | VPS (serveur pur) | Mac→prod | Verdict |
|---|---|---|---|
| Fiche `/parcels/{idu}` | 57 ms | 108 ms | sain |
| Score v2 | 12 ms | 52 ms | sain |
| **Liste brûlantes `?tiers=`** | **1 574 ms** | 1 683 ms | **serveur — SQL** |
| **Liste île (défaut)** | ~2 400 ms | **2 559 ms** | **serveur — SQL** |
| Recherche omnibox | 231 ms | 354 ms | correct |
| Dashboard `/stats` | 7 ms (froid 1,5 s) | 51 ms | cache 30 s OK |
| Tuile MVT z11 lourde | 8 ms | 97 ms | serveur OK, POIDS ↓ |
| Faisabilité | 75 ms | 111 ms | sain |
| Anti-fiche O3 | 14 ms | 58 ms | sain |
| **Comparateur O6** | **1 968 ms** | 1 942 ms | serveur — 1 grosse SQL |
| **Carnet O7** | **1 074 ms** | 1 101 ms | serveur |
| Rareté O9 / Servitudes O5 | 91 / 84 ms | 129 / 127 ms | sains |
| Sources | 403 ms | 474 ms | moyen |
| Scoreur O2 (POST, géocode BAN) | — | 381 ms | sain |
| Traducteur O4 (POST) | 36 ms | 83 ms | sain |
| **Dossier banquier PDF** | **9 262 ms** | 9 293 ms | **serveur — WeasyPrint** |

### Le front au microscope
- **Bundle** (dist, gzip) : maplibre 217 Ko + index 98 Ko + vendor 58 Ko + css 16 Ko ≈ **389 Ko** — sain.
- **Chargement à froid : 43 requêtes, dont 5 tuiles MVT z11 = 2,9 Mo gzip (9,2 Mo décodés)** — le
  poids initial est LA carte, pas le JS. Lighthouse : desktop 94 (LCP 1,1 s) ; **mobile 78 (LCP 4,0 s)**.
- **Requêtes par vue** : fiche = **8 appels API dont `/parcels/{idu}` EN DOUBLE** (dédoublonnage
  React Query à faire) ; Projets/CRM/Vues/Sources/IA = 1-3 appels chacune (sains).
- **Headers de cache** : tuiles = `public, max-age=3600` ✓ ; **assets hashés = ETag SEUL, aucun
  Cache-Control** → chaque navigation revalide 4 fichiers (4 × RTT client pour rien).
- **IGN** : uniquement M08 « Remonter le temps » — 72 tuiles ≈ 1,6 Mo à l'ouverture (~22 Ko/tuile), correct.
- **Accessibilité (Lighthouse 83-88)** : boutons sans nom accessible, contrastes insuffisants
  (txt-dim sur bg), cibles tactiles trop petites, pas de landmark `main` — liste exacte en annexe.

### La DB (EXPLAIN sur le pire)
Liste île (la vue par défaut de l'app) : le planner part de `parcels ⋈ dryrun_parcel_evaluations`
(seq scans parallèles, 430 k lignes) puis **trie TOUT sur `s2.rang`** (sort 1,34 s, 464 k buffers) —
**l'index `ix_p_v2_run_rang (run_id, rang)` existe mais est inutilisable** car le tri porte sur une
table LEFT JOINtée. Une réécriture pilotée par `parcel_p_score_v2` (top-N par index, PUIS jointures)
ferait ~50 lignes lues au lieu de 430 k.

### TOP 5 DES GAINS PROBABLES — rien n'est fixé (bloc consolidation, après l'audit)

| # | Gain | Impact estimé | Effort |
|---|---|---|---|
| 1 | `Cache-Control: immutable` sur `/assets/*` (Caddyfile, 3 lignes) | navigations répétées instantanées pour les clients Réunion | XS |
| 2 | Réécrire la liste v2 pilotée par l'index rang (top-N d'abord) | **2,5 s → ~0,1-0,3 s** sur LA vue quotidienne | M |
| 3 | Poids tuiles z11 (2,9 Mo au 1er écran) : simplification/props plus agressives z≤11, ou edge cache | LCP mobile 4 s → ~2 s | M |
| 4 | Cache TTL mémoire pour O6/O7 (réponse stable par run, pattern LRU tuiles déjà en place) | 1,9 s / 1,1 s → <50 ms au 2ᵉ hit | S |
| 5 | Dossier banquier : génération asynchrone (toast) + cache par (idu, run) | 9,3 s perçus → clic instantané | M |

Bonus courts : dédoublonner l'appel fiche (React Query), tooltips custom, page 404 habillée.

### Cloudflare proxy (orange) — évaluation demandée
**Pour** : PoP Cloudflare à La Réunion → assets/tuiles cachés à ~10-20 ms des clients (vs ~180-200 ms
jusqu'à Gravelines) ; WAF/rate-limit edge ; IP origine masquée.
**Contre / préalables** : ① sans le gain n°1 (Cache-Control assets), le CDN n'a rien à cacher ;
② **le rideau actuel neutralise le cache edge** — Cloudflare ne met pas en cache les requêtes
portant `Authorization` (basic auth) sans règle explicite, et les tuiles voyagent avec le cookie de
session ; ③ renouvellement Let's Encrypt à basculer (origin cert CF en Full strict, ou DNS-01) —
le HTTP-01 actuel casse derrière le proxy si mal configuré.
**Reco : pas maintenant.** L'orange prend son sens **après la vraie auth** (mandat Auth & Plans,
quand le rideau basic auth tombe) avec une règle de cache explicite assets+tuiles. D'ici là, les
gains n°1 et n°2 rendent l'essentiel du bénéfice sans toucher au DNS. (Décision réversible en
2 clics, TLS déjà stable.)

---

## A3 · LA PORTE (maquettes, zéro implémentation)

Deux directions **réellement opposées** (pas de 3ᵉ variante forcée — je n'avais pas de conviction
distincte des deux premières), 100 % statiques, DA de l'app, 4 états jouables (défaut · focus ·
erreur · chargement — interactions réelles + sélecteur de revue en bas à droite, chrome de maquette
à retirer au branchement), mobile au même niveau que le desktop, `prefers-reduced-motion` respecté.

- **`docs/mockups/login_coffre.html` — « Coffre »** : le luxe par la retenue — noir profond, l'oiseau
  doré seul, UN champ (clé d'accès), une signature « Radar foncier · La Réunion » ; focus mint,
  erreur qui ne fait pas trembler la page (espace réservé), chargement = anneau à la place de la flèche.
- **`docs/mockups/login_territoire.html` — « Territoire »** : la donnée comme décor — les contours
  des 24 communes en filigrane presque subliminal (générés depuis `communes974.geojson`, le vrai
  périmètre servi), module flottant identifiant+mot de passe, signature dosée « 431 663 parcelles
  analysées · 24 communes ».

Le design retenu se branche sur le rideau actuel puis sera hérité par la vraie auth — conçu une fois.
(Note : « Coffre » assume le champ unique du rideau pilote ; le passage à identifiant+mot de passe est
une extension triviale du même dessin.)

## Garde-fous — état
Zéro modification produit (aucun fichier app/config/DB touché — les seuls commits : `qa/atlas.mjs`,
`docs/mockups/`, ce rapport) · captures HORS git (`~/labuse-atlas/`) · prod sollicitée uniquement
pour la parité + le banc A2, séquentiel à rythme humain (150 ms entre appels, 15 max par endpoint) ·
zéro écriture applicative : aucun clic Retenir/Écarter, aucun signalement soumis, aucun lien de
partage généré ; seul 1 appel NL réel (cache IA = fonctionnement normal).

---

## ANNEXE — chiffres bruts

### Lighthouse (prod, session réelle)
| Page | Perf | LCP | TBT | A11y | BP |
|---|---|---|---|---|---|
| App desktop | 94 | 1,1 s | 150 ms | 83 | 96 |
| App mobile | 78 | 4,0 s | 20 ms | 87 | 96 |
| Login desktop | 100 | 0,2 s | 0 ms | 88 | 96 |

A11y en échec : `button-name`, `color-contrast`, `target-size`, `landmark-one-main`,
`label-content-name-mismatch`.

### Tuiles du premier écran (z11, gzip sur le fil)
217 + 510 + 1 080 + 251 + 827 Ko = **2 885 Ko** (5 tuiles) — la plus lourde : 1 348×1 147.

### Requêtes par vue (local, mesure Playwright)
froid 43 req/11,3 Mo (5 MVT = 9,2 Mo décodés, 24 basemap = 84 Ko, 4 API) · verdict-on +1 req/224 Ko ·
fiche 8 API (dont `/parcels/{idu}` ×2) + 20 basemap + 4 MVT · projets 1 · CRM 3 · vues 2 · sources 2 · IA 1.

### EXPLAIN liste île (extrait)
`Sort actual 1 339 ms` sur `s2.rang` après seq scans parallèles `parcels` (431 k) ⋈
`dryrun_parcel_evaluations` (77 k retenues) — buffers 366 681 hit + 97 599 read ;
`ix_p_v2_run_rang` non utilisé (tri sur table LEFT JOINtée). Endpoint : 2 559 ms p50 (Mac→prod).

### Bancs complets
CSV : `/tmp/bench_mac.csv` (Mac→prod, https, session) et `/tmp/bench_vps.csv` (VPS localhost:8000) —
recopiés dans le tableau A2 ci-dessus ; outil jetable `/tmp/bench_labuse.py` (non versionné, mandat).

---

**À ta review.** Ouvre `~/labuse-atlas/2026-07-22-11-10__local/index.html`, annote, tranche la porte
(Coffre / Territoire) — le bloc consolidation naîtra de tes annotations.
