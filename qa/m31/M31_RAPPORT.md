# M31 — TRAIN 3 : PROD-CHECKS

Régime [A] · Opus · branche `m31-train3-prodchecks` · base main post-M30 (`5486915`)
Corrections **une à une**. Un point d'arrêt final. **PAS de merge.**
Format : chaque check = constat → action → preuve.

---

## PROD-CHECK N°1 — pytest rouge (diagnostic d'abord, fix ensuite)

**Avant M31** : `2 failed, 915 passed, 394 skipped, 23 errors`.
**Après M31** : `1 failed (CONSIGNÉ), 1310 passed, 22 skipped, 0 error`.

Deux familles distinctes, comme prévu à la note préparée au M30.

### Famille A — 9 FAILED, `NameError: marque` (régression code)

**Diagnostic** (confirmé par `git show 98363d7`, [M23-A]) : le commit M23-A « Marque du client sur
les documents ABONNÉ » a câblé `marque` dans `_build_pdf` + la route, ET ajouté `marque=marque` à
l'appel `garde_entete` DANS une fonction de section — mais **sans threader `marque` jusqu'à cette
fonction**. Le diff le prouve : la ligne parent était `bandeau=LIBELLE)` (aucune référence à
`marque`), la ligne M23-A est `bandeau=LIBELLE, marque=marque)`. La régression date donc EXACTEMENT
de M23-A ; elle est restée rouge depuis, masquée par les erreurs DB de la famille B (la suite ne
tournait jamais entièrement sur ce poste).

**Action** (3 fichiers, une correction ciblée par fichier — thread `marque` jusqu'à la section) :
- `src/labuse/api/argumentaire.py` : `_synthese(out, marque=None)` + appel `_synthese(out, marque)`.
- `src/labuse/api/potentiel.py` : idem (`_synthese`).
- `src/labuse/api/lettre_zonage.py` : `_identification(p, rap, ref, marque=None)` — DEUX symboles
  hors portée ici (`marque` ET `_marque_bloc`, importé dans `_build_pdf` mais utilisé dans
  `_identification`). **Aucun test ne couvrait ce chemin** → NameError LATENT en prod : tout PDF
  « Lettre de vérification de zonage » plantait. Import local + `marque` threadée + import mort retiré.

**Preuve** : `tests/test_argumentaire.py` + `tests/test_potentiel.py` verts. **Test de non-régression
ajouté** `tests/test_lettre_zonage.py::test_identification_rend_sans_nameerror_avec_et_sans_marque`
(rend la couverture avec et sans marque — le trou qui a laissé passer M23-A est désormais gardé).

### Famille B — 23 ERRORS, `OperationalError: role "labuse" does not exist` (environnement)

**Diagnostic** : `.env` (gitignoré) pose l'URL qui marche (`openclaw@localhost`, auth peer) — c'est
elle qui fait tourner l'app, golden, scoring. MAIS `tests/conftest.py` lisait `LABUSE_DATABASE_URL`
depuis `os.environ` **avant** que `labuse.config` (qui fait `load_dotenv`) ne soit importé → repli sur
le défaut codé `labuse:labuse@localhost`, rôle inexistant sur ce poste. Les tests utilisant la fixture
`engine` skippaient proprement ; ceux qui ouvrent `session_scope()` directement (facturation,
audit_stripe, comptes, fiche_ask, alertes) **erroraient**. Confirmé : avec l'URL correcte exportée,
ces 7 tests passent.

**Action** (environnement, rendu reproductible) : `tests/conftest.py` **charge le `.env`** (via
`python-dotenv`, `override=False`) avant de dériver l'URL de test — exactement comme l'app. Un `.env`
valide (que tout dev a déjà pour lancer l'app) suffit désormais, plus d'export manuel. `docs/TESTS.md`
mis à jour (commande simplifiée + explication du piège).

**Preuve** : les 23 erreurs disparaissent, **393 tests DB auparavant skippés tournent** désormais
(915 → 1310 passed).

### Effet de bord révélé — dette de test M30 (/discover)

Une fois la base joignable, 2 tests **jusque-là masqués** ont surgi : ils appelaient `/discover`,
**route supprimée au M30** (orphelin, remplacé par /parcels + /stats). Le golden M30 ne les couvrait
pas (il vérifie des fiches, pas la liste), et la famille B les faisait errorer → la suppression a
shippé sans mettre à jour ses tests.

**Action** : `tests/test_api.py` — `test_discover_classe_les_survivantes` retiré (endpoint disparu,
vocabulaire pré-M5.1) ; ligne `/discover` retirée de `test_limit_negatif_rejete_en_422` (les 2 autres
assertions /map + /signals conservées). Commentaires traçant le pourquoi.

### Rouge CONSIGNÉ (non corrigé — décision de service, régime [S], Vic)

`test_run_serving_coherence.py::test_tuiles_mvt_materialisees_sur_le_run_servi` reste rouge en défaut.
**C'est le garde-fou qui fait son travail** : les **tuiles** `mvt_meta.run_label` sont sur
`q_v8_calibre` (rebuild M28) mais la constante de code `Q_A_RUN_LABEL` (+ le défaut front `api.ts`
SOURCE + le bundle `dist`) restent sur **`q_v7_defisc`**. La bascule M28 a avancé les tuiles + l'env +
les scores, mais **pas les constantes du dépôt**. Preuve que ce n'est pas un réglage d'env : forcer
`LABUSE_SERVED_RUN=q_v8_calibre` fait au contraire tomber 7 tests (gardes front/bundle + tests couplés
aux données anti_fiche/carnet/scoreur) — **aucune valeur d'env n'aligne les trois surfaces**.

C'est une **bascule de run servi non terminée au niveau du dépôt**. La terminer = avancer
`Q_A_RUN_LABEL` + `api.ts` SOURCE sur `q_v8_calibre`, `npm run build`, `labuse build-mvt`, en un seul
geste coordonné. **C'est une décision sur CE QUI EST SERVI** → régime [S], Vic. Un prod-check [A] ne
la tranche pas. Consigné aussi dans `docs/TESTS.md`.

> ⚠ Implication déploiement à vérifier : si la prod ne pose PAS `LABUSE_SERVED_RUN`, elle sert le run
> `q_v7_defisc` (pré-M28) avec des tuiles `q_v8_calibre` → incohérence silencieuse. À trancher.

---

## PROD-CHECK N°2 — Sécurité

Un audit adversarial (agent) a levé 4 axes ; **2 « criticals » se sont révélés de FAUX POSITIFS**
après vérification directe (l'agent regardait le `Depends()` de route, pas la garde middleware
globale ; et n'avait pas vérifié le suivi git de `.env`). État réel :

| Axe | Constat vérifié | Verdict |
|---|---|---|
| **/docs, /redoc, /openapi.json** | `auth.is_public` (auth.py:59-64) : publics **uniquement si `env == 'local'`** ; hors local → garde middleware → 401/redirect. | ✓ Fermé en prod |
| **SECRET_KEY** | `config.py:50` défaut `None` ; `auth.exiger_secret_prod()` (appelée au boot) **refuse de démarrer** hors local sans clé (fail-closed). `.env.example` = placeholders. | ✓ Correct |
| **Endpoints admin** (`/protection/admin`, `/admin/gel/{sujet}`, `/admin/degel/{sujet}`) | PAS de `Depends()` de route, MAIS la garde globale `_auth_guard` (app.py:204-230) protège TOUTE route hors allowlist `_PUBLIC`. Ces chemins n'y sont pas → **401 sans session** hors local. Vérifié empiriquement (`is_public`=False) + test. | ✓ Protégés (middleware) |
| **CORS** | `app.py:151-157` : `allow_origins=["*"]` **en local seulement**, sinon `[public_url]` ou `[]`. Pas de `allow_credentials=True`. | ✓ Restreint en prod |
| **Secrets committés** | `.env` **jamais commité** (0 commit sur toutes branches, `git log --all -- .env`) ; aucun secret réel dans l'historique traqué. Les secrets vivent dans `.env` gitignoré (sur disque, normal en dev). | ✓ Rien de fuité |

**Action** : aucun correctif nécessaire (posture saine). **Durcissement ajouté** : le finding admin
est verrouillé en invariant testé — `tests/test_audit_secu.py::test_protection_admin_exige_une_session`
(sans session → 401 sur admin/gel/degel + `is_public` False). Convertit un doute d'audit en garde permanent.

**Note (pas un correctif code)** : `.env` local contient de vraies clés de test (Stripe `sk_test_`,
Anthropic, INPI, SMTP). Gitignoré et jamais commité → risque nul côté dépôt. Mentionné pour mémoire :
une rotation reste saine si le disque/poste change de mains (ops, hors périmètre).

---

## PROD-CHECK N°3 — Vitesse

**5 endpoints les plus servis** (API `LABUSE_DEV_MODE=1` port 8010, run q_v8_calibre) — froid = 1er hit,
chaud = médiane de 3 :

| Endpoint (route réelle servie) | Froid | Chaud (méd.) | HTTP | Seuil >1s |
|---|---|---|---|---|
| Fiche — `/parcels/{idu}?source=` | 0,63 s | **0,10 s** | 200 | ✓ ok |
| Tuiles île — `/map/tiles/{z}/{x}/{y}.pbf` (MVT) | 0,36 s (z11, 652 Ko) | **0,004 s** | 200 | ✓ ok |
| Recherche — `/parcels/search?q=` | 0,17 s | **0,05 s** | 200 | ✓ ok |
| Liste île — `/parcels?limit=100&sort=rang` | 0,01 s | **0,005 s** | 200 | ✓ ok |
| Verdict — `/stats` | 0,51 s | **0,004 s** | 200 | ✓ ok |

**Les 5 endpoints les plus servis ne dépassent pas 1 s**, même à froid. Les tuiles île passent par
les **MVT matérialisés** (`/map/tiles`), rapides — pas par le GeoJSON.

**Un 6ᵉ chemin, plus lent — `/map/parcels.geojson` (mode COMMUNE)** : servi par `getParcelsGeojson`
(api.ts:111, appelé dans 4 composants — MapView, ResultsSection, Header, TimeMachine — tous
`enabled: !ile`, donc **commune uniquement** ; l'île utilise les MVT). Scopé à la commune via le
`q()` global (api.ts:43 injecte `commune()`). Payload et temps proportionnels à la taille de la
commune : Saint-Leu **0,88 s**, **Saint-Denis 2,2 s** (21 Mo). Le plus gros dépasse le seuil 1 s.
Non bloquant (l'île, le cas lourd, est déjà sur MVT), mais **candidat MVT commune** si on veut
lisser les grosses communes. _(Correction d'un premier jet de ce rapport qui, sur une lecture
erronée du nom du helper, avait classé cette route « morte » — elle est bien SERVIE.)_

**N+1 fiche** : log SQL d'une ouverture de fiche = **28 requêtes** au total, **max 3 sur une même
table** (`parcel_renouvellement`). Pas de N+1 (qui montrerait des dizaines de requêtes proportionnelles
aux lignes) — c'est une fiche COMPOSÉE (parcels, scoring, DVF, PM, renouvellement, spatial_layers,
cascade…), bornée, rendue en 0,10 s. RAS.

---

## PROD-CHECK N°4 — Mails + API mortes + MIN_DISPLAY_SURFACE

### Config mail — SPF ✓, DKIM (alignement) ⚠, DMARC ✗

Domaine d'envoi : `labuse.immo` (`mail_from = LABUSE <contact@labuse.immo>`), transport SMTP Gmail
(`contactlabuse@gmail.com`). `dig` collé :

- **SPF** ✓ : `v=spf1 include:_spf.mx.cloudflare.net include:_spf.google.com ~all` — inclut Google
  (envoi Gmail) et Cloudflare, soft-fail. Correct.
- **DKIM** ⚠ : `cf2024-1._domainkey.labuse.immo` présent (clé RSA valide) — mais c'est la DKIM de
  **Cloudflare Email Routing** (entrant/forwarding). **`google._domainkey` ABSENT.** L'app envoie via
  un Gmail PERSO avec From `contact@labuse.immo` → Gmail signe en `d=gmail.com`, **pas aligné** au
  domaine From `labuse.immo`. L'envoi applicatif ne passe donc probablement PAS l'alignement DKIM.
- **DMARC** ✗ : `_dmarc.labuse.immo` → **0 enregistrement**. Aucune politique anti-usurpation.

**Erreurs de config listées** (DNS/ops, hors code → NON corrigées ici) :
1. **Ajouter un DMARC** `_dmarc.labuse.immo TXT "v=DMARC1; p=none; rua=mailto:…"` (démarrer en `p=none`
   pour observer avant de durcir).
2. **Aligner l'envoi** : l'app envoyant du `labuse.immo`, il faut soit un Google Workspace avec DKIM
   `labuse.immo` (sélecteur `google._domainkey`), soit une boîte authentifiée `@labuse.immo`. Sinon,
   une fois DMARC en `p=reject`, les mails applicatifs seraient rejetés.

### MIN_DISPLAY_SURFACE_M2 — carte ET liste alignées (arbitrage M30) ✓ CORRIGÉ

**Constat** (inventaire M30) : le plancher d'affichage `MIN_DISPLAY_SURFACE_M2 = 2 m²` (slivers
cadastraux) était appliqué à la CARTE/geojson (app.py:1311, 1485) mais PAS à la LISTE `_q_v2_list` —
asymétrie. Impact mesuré : **850 parcelles < 2 m², TOUTES `ecartee`, 0 dans un tier servi**, aucun
anchor golden.

**Action** (lecture seule, aligne liste sur carte) : `_q_v2_list` — garde `(surface_m2 IS NULL OR
surface_m2 >= :minsurf)` ajoutée aux **deux** chemins (fast-path index + slow-path). Les slivers
restent en base ET dans les compteurs de volumétrie (comme la carte) — simplement plus listés.

**Preuve** : liste `tiers=ecartee` (1000 lignes) → **0 sliver < 2 m²** ; la fiche d'un sliver
(`97414000ET1914`) reste **directement accessible (HTTP 200)** — masqué de l'affichage, présent en
base, exactement comme la carte. **Golden 117/117**, `tests/test_api.py` + `test_etage0_filtre_dur.py` verts.

### Inventaire API mortes (candidates à retrait — LISTE SEULEMENT, aucun retrait)

**Résultat honnête : l'inventaire automatique n'est PAS fiable en l'état — je ne publie donc PAS de
liste de « routes mortes », qui serait trompeuse.** Détail du pourquoi :

Une cross-référence par recherche textuelle du chemin (216 routes vs le code) rend **86 à 103
candidats** — mais **truffés de faux positifs**, car le front n'appelle presque jamais un chemin en
dur : il passe par des helpers TypeScript de `frontend/src/lib/api.ts` (`getParcelsGeojson`,
`iaSearch`, `getFaisabilite`…) qui construisent l'URL. La liste brute classait « mortes » des routes
manifestement VIVES : `/ia/search` (le copilote), `/modules/faisabilite/{idu}` (mesuré servi en
PC3), `/stripe/webhook` (appelé par Stripe), `/cgv` `/mentions-legales` (légal), les 8 routes PDF…

**Preuve que la méthode est dangereuse — je m'y suis fait prendre moi-même** : un premier jet classait
`/map/parcels.geojson` « morte » (helper cru non appelé). Vérification faite : le helper s'appelle
`getParcelsGeojson` (pas `getMapParcels`), il est appelé dans **4 composants**. La route est VIVE.
Un retrait sur la foi de la liste brute aurait cassé la carte en mode commune.

**Un seul candidat de fait avéré, à confirmer** — `/api/v1/parcels` et `/api/v1/docs`
(`partners.py:450,471`) : API « partenaire » externe, sans appelant front (par conception — c'est
une API tierce). À NE PAS retirer sans savoir si un partenaire la consomme (hors front, hors dépôt).

**Conclusion (doctrine « non calculable proprement → l'écrire et s'arrêter »)** : un inventaire de
routes mortes fiable exige un **traçage par helper** (résoudre chaque fonction de `api.ts` → chemin,
puis chercher les appels de la fonction, + les `fetch()` directs, + cron/webhook/PDF). Ce n'est pas
faisable de façon sûre par recherche de chaîne dans cette passe. **Aucune route retirée, aucune liste
non fiable publiée.** Recommandation : une passe dédiée par traçage de helper si le nettoyage est voulu
(NOTÉ au BACKLOG, non fait en M31).

---

## Non-régression globale

- Suite pytest : **1310 passed, 22 skipped, 1 failed CONSIGNÉ** (cohérence run servi, ci-dessus).
  0 error (les 23 disparues). Avant M31 : 2 failed + 23 errors + 915 passed.
- **Golden 117/117 PASS, 0 incohérence** (API `LABUSE_SERVED_RUN=q_v8_calibre`, badges M28).
- Fichiers touchés (code/tests) : `argumentaire.py`, `potentiel.py`, `lettre_zonage.py`, `app.py`
  (`_q_v2_list` sliver), `conftest.py`, `test_api.py`, `test_lettre_zonage.py` (+test),
  `test_audit_secu.py` (+test). Docs : `docs/TESTS.md`, `docs/BACKLOG.md`. Preuves : `qa/m31/`
  (rapport, `preuve_dns_mail.txt`, `preuve_vitesse.txt`). **Aucun fichier de scoring / de règles.**

## Ce qui reste OUVERT (noté, non fait — hors périmètre [A])

1. **[S] Vic** — terminer la bascule du run servi sur `q_v8_calibre` (constantes + bundle + build-mvt).
   C'est une décision sur ce qui est servi. Le rouge de test consigné disparaîtra alors seul.
2. **Ops/DNS** — créer le DMARC `labuse.immo` (`p=none` d'abord) et aligner l'envoi (DKIM `labuse.immo`,
   pas Gmail perso). Sinon un DMARC `p=reject` rejetterait les mails applicatifs.
3. **[A]** — passe de traçage par helper pour un inventaire fiable des routes mortes (avant tout retrait).
4. Perf : envisager des tuiles MVT en mode commune pour les plus grosses communes (Saint-Denis 2,2 s).
