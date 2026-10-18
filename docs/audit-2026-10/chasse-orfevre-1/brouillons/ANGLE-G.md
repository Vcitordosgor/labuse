# ANGLE G — Les petits riens du front (CHASSE-ORFEVRE-1)

Date : 18/10/2026 · Worktree `~/Desktop/labuse-orfevre` (= main) · **Lecture seule** (aucun
formulaire mutant soumis ; seules écritures techniques inhérentes aux GET — voir « Écritures
techniques observées » en bas).

## Environnement et méthode

- Backend `labuse api` **:8802** (venv PDF-capable `~/Desktop/labuse/.venv`, `.env` chargé,
  run servi q_v19) ; front Vite **:6002** (`/socle/`). Auth locale : `/moi` → `mode:"local"`.
- Parcours automatisé : `scripts/angle_g_front.mjs` (Playwright, **Chrome système
  `channel:'chrome'`**, 1440×900, 1 navigateur, 1 page à la fois). Rapport brut :
  `scripts/angle_g_report.json` ; captures de preuve : `captures-g/angle-g_*.png`
  (brut complet : `/tmp/angleg_caps/`).
- **49 écrans** : carte · 2 fiches parcelle (97401000AC0428, 97415000CR0849, tiroirs ouverts
  un à un) · fiche commune (Saint-Denis) · **21 outils** (`#m=…` : plu, permis, promesses,
  communes, barometre, calculette-fonciere, mon-secteur, patrimoine, veille-promoteurs,
  assemblage, comparer, risques, etude-zone, temps, programme, gabarit, taxe-amenagement,
  prospection-solaire, blocs-fonciers, successions, courriers) · radar · veille (parcelles,
  critères) · vues documents / copilote / projets / CRM / sources · **admin 8 sections**
  (`#admin=1` : pilotage, licences/Comptes, données, courrier, radar, produit, IA, contacts) ·
  **7 pages serveur** sur l'origine API (`/login`, `/reset`, `/cgv`, `/invitation` sans token,
  `/onboarding/retour?ok=1|0`, `/flash?idu=…`).
- Collecte par écran : console (warning/error dédupliqués, bruit Vite/HMR filtré), réseau
  (≥ 400 + requêtes échouées), texte rendu (`innerText` : regex undefined/NaN/null/[object/
  Invalid Date, « 1 xxxs », doubles espaces, apostrophes, espaces avant ponctuation, nombres
  sans séparateur, €/EUR/euros, tirets), inventaire input/textarea (type, maxlength,
  inputmode), + 3 sondes ciblées sans effet (double-clic recherche, collage 10 000 car.,
  texte dans champs nombre).

## Synthèse

**0 bloquant · 1 gênant · 10 cosmétiques · 3 à surveiller.** Ce qui est PROPRE est listé en bas.

| # | Anomalie | Gravité |
|---|---|---|
| G-01 | `GET/POST /moi/prefs-carte` → **401 sur TOUS les écrans** de l'app (2 erreurs console rouges par chargement) | gênant (dev) |
| G-02 | Outil « Suivre le temps » : **36 × 404** tuiles ortho « mer » → spam console | cosmétique |
| G-03 | `/login` local → 302 `/` → Swagger **page 100 % blanche** (CSP bloque les assets CDN) | cosmétique (dev, complète A-07-1) |
| G-04 | Pages serveur en dev : polices `/socle/fonts/*.woff2` **404** (pas de dist) | cosmétique (dev) |
| G-05 | **Apostrophes mélangées** `'` / `’` dans toute l'app (3 526 vs 498 occurrences, visibles côte à côte) | cosmétique |
| G-06 | **Aucune espace insécable** avant `: ; ! ?` (0 NBSP dans le front… sauf 4 `&nbsp;` isolés) | cosmétique |
| G-07 | « **1 / 1 affichées** » (ListPagination, pas de singulier) ; « l'envoi de **1 courrier** » | cosmétique |
| G-08 | Nombres sans séparateur de milliers là où le reste en a : « **1289** commits d'avance » (admin) | cosmétique |
| G-09 | Contacts admin : téléphone saisi affiché brut « **0648345707** » à côté de standards « 02 62 31 89 89 » | cosmétique |
| G-10 | « Mes documents » : colonne Document affiche le slug « **etude-faisabilite** » | cosmétique |
| G-11 | Double-clic « Lancer la recherche » → **2 × `/parcels/search`** (pas de garde anti-redéclenchement) | à surveiller |
| G-12 | Omnibox sans maxlength : accepte 10 000 caractères collés | à surveiller |
| G-13 | Textarea du Copilote sans maxlength | à surveiller |
| G-14 | SIREN affichés bruts (`388712853`) dans l'outil Successions | cosmétique |

---

## Constats détaillés

### G-01 — 401 `/moi/prefs-carte` sur chaque écran — **gênant (environnement dev/local)**
- **Preuve** : sur les 42 écrans SPA parcourus, console : `error|Failed to load resource: …
  401 (Unauthorized) (×2)` ; réseau : `401 http://localhost:6002/moi/prefs-carte`.
  Reproductible : `curl -i http://127.0.0.1:8802/moi/prefs-carte` → 401.
- **Cause** : `App.tsx` appelle `getPrefsCarte()`/`postPrefsCarte()` au boot (COMPTE-2 Lot 6) ;
  côté serveur `onboarding.py:1252` passe par `_compte_session` → `tenant.compte_ou_401`, qui
  401-e **même en mode local** (alors que `/moi` répond gentiment `mode:"local"`). Le front
  catch (best-effort) : la mémoire du fond/couches est silencieusement MORTE en local, et
  chaque écran démarre avec 2 erreurs console rouges — bruit qui masque les vraies erreurs
  en recette.
- **Correction proposée (non appliquée)** : en mode local, `/moi/prefs-carte` GET → 200
  `{basemap:null, couches:null}` et POST → 204 no-op (même esprit que `/moi`) ; OU front :
  ne pas appeler prefs-carte quand `/moi` dit `mode:"local"`.

### G-02 — Outil « Suivre le temps » : 36 × 404 tuiles ortho — **cosmétique**
- **Preuve** : écran `outil-temps` : console `404 (Not Found) (×36)`, réseau
  `404 /map/tiles/ortho/1950/13/5352/4584`, `404 /map/tiles/ortho/express/13/…` (et un lot
  équivalent à chaque pan/zoom). Capture `angle-g_outil-temps.png`.
- **Cause** : par CONCEPTION, `ortho_proxy.py` répond `404 "Tuile mer (aplat)"` pour les tuiles
  au large (cache `.mer`) — la légende de l'outil l'assume (« Zones noires : … ce n'est pas un
  défaut de chargement »). Mais chaque 404 est logué en rouge par le navigateur → ~36 erreurs
  console par affichage, et la famille « réseau ≥ 400 » de n'importe quelle recette sonne.
- **Correction proposée** : servir un PNG transparent 1×1 (200, fort max-age) ou un 204 pour
  les tuiles `.mer`/no-data, plutôt qu'un 404.

### G-03 — `/login` local = page blanche (Swagger cassé par la CSP) — **cosmétique, artefact dev**
- **Preuve** : `/login` → 302 `/` (auth désactivée) ; `/` sert Swagger `/docs`, dont les assets
  `cdn.jsdelivr.net/npm/swagger-ui-dist@5/*` et le script inline sont **bloqués par la CSP**
  (`style-src 'self' 'unsafe-inline'`, `script-src 'self'`) → 4 erreurs console
  `FAILED(csp)` et un rendu **entièrement blanc**. Capture `angle-g_srv-login.png`.
- Complète l'anomalie connue **A-07-1** (recette générale) : non seulement `/login` atterrit
  sur Swagger en local, mais ce Swagger ne se rend même pas.
- **Correction proposée** : en mode local, `/login` pourrait rediriger vers `/socle/` ; et/ou
  exempter `/docs` de la CSP stricte (routes dev), ou servir swagger-ui en self-host.

### G-04 — Pages serveur : polices 404 en dev — **cosmétique, artefact dev**
- **Preuve** : `/reset`, `/cgv`, `/invitation`, `/onboarding/retour`, `/flash` chargent
  `/socle/fonts/inter-latin-400-normal.woff2` etc. → **404** (3 à 5 par page) sur l'origine
  API :8802. Cause : `coffre_ui.py` référence `/socle/fonts/…` servi par le build front
  (`frontend/public/fonts` → dist) ; **pas de `frontend/dist` sur ce poste** → repli police
  système. En prod (dist présent, noms de fichiers stables) : OK.
- **Correction proposée** : rien d'obligatoire ; éventuellement embarquer les 2-3 woff2 dans
  un petit static de l'API pour que les pages compte soient fidèles même sans dist.

### G-05 — Apostrophes mélangées `'` (droite) et `’` (typographique) — **cosmétique transverse**
- **Preuve code** : `grep` sur `frontend/src` → **3 526** apostrophes droites entre lettres
  contre **498** typographiques : les deux conventions cohabitent, parfois dans le MÊME écran :
  - Outil Gabarit : titre registre `'Où et jusqu’où implanter…'` (typo, `registry.ts:118`)
    puis sous-titre `« Où et jusqu'où une construction peut s'implanter »` (droite,
    `Gabarit.tsx:234`). Capture `angle-g_outil-gabarit.png`.
  - « Toute l’île » (typo : `ProspectionSolaire.tsx:157`, sélecteur d'en-tête) vs
    « Toute l'île » (droite : `ModulePanel.tsx:159`, `Blocs.tsx`).
  - Fiche parcelle : « jusqu’à déc. 2025 » (typo) à trois lignes de « certificat d'urbanisme »
    (droite).
- **Correction proposée** : trancher UNE convention (la typographique `’` est celle du
  français soigné) et normaliser — un codemod + une règle lint (interdire `'` entre lettres
  dans les littéraux JSX) empêchent la rechute.

### G-06 — Pas d'espace insécable avant la ponctuation haute — **cosmétique transverse**
- **Preuve** : 0 NBSP avant `: ; ! ?` dans tout `frontend/src` (grep ` `), alors que les
  textes français en affichent partout (« Secteur : le Tévelave », « QUELLE PARCELLE VOIR
  ÉVOLUER ? », « gardée 15 min si vous revenez. … ; »). Conséquence : une ponctuation peut
  passer SEULE à la ligne sur les textes qui wrap (tiroirs de fiche, descriptions d'outils).
  Micro-incohérence en plus : 4 `&nbsp;` isolés existent déjà (`ScanPatrimoine.tsx:179`,
  `BlocIndisponible.tsx:16`, `leBien.tsx:104`) — deux poids deux mesures.
- **Correction proposée** : espace fine insécable (U+202F ou `&nbsp;`) avant `: ; ! ?` au
  moins dans les libellés longs sujets au retour à la ligne ; ou un composant/t() qui le fait.

### G-07 — Pluriels sans singulier — **cosmétique**
- « **1 / 1 affichées** » : Tour de contrôle › Pilotage › Journal (capture
  `angle-g_admin-pilotage.png`, bas du journal). Source : `ListPagination.tsx:67`
  (`{shown} / {total} affichées`) — composant générique, le même « affichées » sort aussi dans
  `ResultsSection.tsx` (« 1 sur 1 affichées » possible sur une recherche à résultat unique).
- « Un client demande **l'envoi de 1 courrier** (Saint-Pierre ×1) » (même écran) : « de 1 »
  au lieu de « d'un » (phrase composée côté serveur).
- **Correction proposée** : `affichée(s)` selon `shown`, et « d'un courrier » quand n = 1.

### G-08 — Séparateurs de milliers incohérents — **cosmétique**
- Admin › Pilotage › À faire : « Déployer — **1289 commits** d'avance sur la prod » (phrase
  serveur, `deploiement.py`) alors que l'app formate partout ailleurs (« 50 808 permis »,
  « 434 582 parcelles », tuiles admin en `fmtInt`). Capture `angle-g_admin-pilotage.png`.
- **Correction proposée** : formater le compte côté phrase serveur (ou passer le nombre au
  front qui `toLocaleString('fr-FR')`).

### G-09 — Téléphone brut dans Contacts admin — **cosmétique**
- Tour de contrôle › Contacts › fiche Cilaos : contact nommé « jordan » affiché
  « **0648345707** · victorlaganepro@gmail.com » juste sous le standard formaté
  « 02 62 31 89 89 » (capture `angle-g_admin-contacts.png`). Le numéro saisi n'est jamais
  reformaté (`Contacts.tsx` affiche `c.telephone` verbatim).
- **Correction proposée** : normaliser à l'affichage (XX XX XX XX XX) — pas en base.

### G-10 — « Mes documents » : slug technique affiché — **cosmétique**
- Vue Docs › Mes documents : colonne Document = « **etude-faisabilite** » (ligne du
  18/10/2026, 97404000AW0099) alors que les tuiles au-dessus disent « Dossier », « Étude de
  zone »… Capture `angle-g_vue-documents.png`. `DocumentsView.tsx:331` rend `{r.document}`
  servi par l'API sans table slug → libellé ; « etude-faisabilite » n'est d'ailleurs pas dans
  les 7 types à filtre (le filtre par pills ne peut pas l'isoler).
- **Correction proposée** : mapping slug → libellé humain côté front (avec repli slug), et
  décider du sort des types hors des 7 pills.

### G-11 — Double-clic « Lancer la recherche » = double requête — **à surveiller**
- **Preuve (sonde)** : omnibox remplie `97401000AC0428`, 2 clics rapprochés sur
  `[aria-label="Lancer la recherche"]` → **2 ×** `GET /parcels/search?q=97401000AC0428`
  (rapport JSON, `probes.doubleClicRecherche`). Conséquence bénigne (GET idempotent, la fiche
  s'ouvre bien), mais le bouton n'a ni état chargement ni garde anti-redéclenchement.
- Aucun autre bouton mutant n'a été double-cliqué (mandat lecture seule).
- **Correction proposée** : désactiver le bouton pendant la requête en cours (pattern déjà
  présent ailleurs : « Ouvrir » des documents passe en `busy`).

### G-12 / G-13 — Champs sans maxlength — **à surveiller**
- **Omnibox** : collage de 10 000 caractères → accepté intégralement (`maxlength=null`),
  aucun plantage, pas de requête massive déclenchée sans Entrée. Un maxlength (~120) serait
  sain (c'est une recherche IDU/SIREN/adresse).
- **Textarea du Copilote** (« Ex. combien de parcelles en procédure à Saint-Denis ? ») : pas
  de maxlength côté client (non soumis — l'envoi créerait un run copilote réel). À vérifier
  côté serveur (plafond de prompt) ; un maxlength client éviterait l'aller-retour.
- **Propre en face** : Surface min/max des FILTRES = `type=number inputmode=numeric`,
  **refusent** `abc!!` (sonde `champsSurface`, valeur reste vide) ; `/reset` e-mail =
  `type=email required` (validation navigateur, en français).

### G-14 — SIREN bruts dans Successions — **cosmétique**
- Outil Successions : chaque carte affiche « ZOGREV · **388712853** », « BATITEC ·
  **341465854** »… (capture `angle-g_outil-successions.png`). Un SIREN se lit usuellement
  groupé (388 712 853). Les surfaces voisines sont, elles, formatées (« 13 455 m² ») — le
  contraste rend le bloc chiffré peu lisible.
- **Correction proposée** : grouper 3-3-3 à l'affichage.

### Notes informatives (pas des anomalies)
- `/invitation` sans token → **statut 404** mais page d'erreur soignée « CE LIEN N'EST PLUS
  VALIDE » avec porte de sortie « Se connecter » : bon comportement, le 404 apparaît juste
  dans la famille réseau des recettes.
- Tuiles `.pbf` en `FAILED(net::ERR_ABORTED)` pendant les zooms : annulations maplibre
  normales (pas des erreurs serveur).
- Admin › Données : « Le producteur a publié « 93781 » » — valeur de version amont affichée
  verbatim (voulu).

## Ce qui est PROPRE (vérifié sur les 49 écrans)
- **0** `undefined` / `NaN` / `null` / `[object Object]` / `Invalid Date` dans le texte rendu
  (regex sur `innerText` de chaque écran, tiroirs de fiche compris).
- **0** erreur console applicative (React keys, props, deprecation) : les SEULES entrées
  console de toute l'app sont G-01 (401) et G-02 (404 tuiles) + CSP de G-03 côté Swagger.
- **0** HTTP 500 sur tout le parcours.
- Monnaie : « € » partout (0 « EUR », 0 « euros » rendus) ; absence de donnée : « — »
  (tiret cadratin) de façon cohérente (documents, fiche, contacts) ; grands nombres formatés
  avec séparateur partout sauf G-08/G-14.
- Doubles espaces : aucun VISIBLE (les `'  ·  '` de `Contacts.tsx:63` / `ContextePanel.tsx:127`
  sont recollapsés par le HTML — non retenus comme anomalie).
- Pages compte serveur (`/reset`, `/cgv`, `/flash`, `/onboarding/retour`) : rendu propre,
  messages en français, anti-énumération du reset en place (constaté recette, non rejoué).
- Empty-states et singuliers ailleurs corrects sur les écrans parcourus (« 0 destinataire —
  une parcelle à la fois », « aucune parcelle sélectionnée »…).

## Écritures techniques observées (tolérées, à signaler)
- Chaque GET de fiche/écran passe par les logs d'usage du backend (heartbeat `startHeartbeat`,
  `signalOutil`, consultations) — inhérent à la navigation, rien soumis.
- `POST /moi/prefs-carte` tenté par le front à chaque session → **401**, donc AUCUNE écriture.
- Aucun formulaire soumis, aucun objet créé (pas de veille/courrier/compte/paiement), aucune
  modification de code applicatif ni de base volontaire.

## Pièges d'environnement (pour rejouer)
- Worktree sans `node_modules` : `cp -R` depuis le repo principal NE SUFFIT PAS — ce main
  est passé à **maplibre-gl ~6.4.1** (repo principal : 4.7.1) → `npm install` obligatoire
  après la copie (rapide, lockfile).
- Backend : `~/Desktop/labuse/.venv/bin/python -c "from labuse.cli import app; app()" api
  --port 8802` avec `.env` sourcé (rôle `openclaw`) et `PYTHONPATH=src`.
- Les pages compte (`/login`, `/reset`, `/invitation`…) ne sont PAS dans le proxy Vite :
  les tester sur l'origine API.
- Chrome système uniquement (`channel:'chrome'`) ; captures d'écrans carte lourdes (~1 Mo)
  → redimensionnées à 1200/900 px dans `captures-g/`.
