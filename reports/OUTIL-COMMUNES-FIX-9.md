# OUTIL-COMMUNES-FIX-9 — réponse au recontrôle 03-COMMUNES-ASTRA-6

Branche `fix/outil-communes-1`. Base locale `labuse` lue seulement (preuves), jamais écrite hors des
caches de réponses autorisés par Vic (listés au LOT B). Pas de fusion dans `main`.

---

## LOT A — DIAGNOSTIC (écrit AVANT toute correction)

### Cause racine (résumé)
L'API locale est un **processus Python long-running démarré AVANT la mise à jour du code**, et
`uvicorn` tourne avec **`reload=False`** (`src/labuse/cli.py:3484`). Python garde en mémoire le
bytecode importé **au démarrage** ; les fichiers réécrits ensuite sur le disque sont ignorés tant que
le processus n'est pas **redémarré**. S'y ajoute un cache de configuration **`@lru_cache` illimité**
sur les YAML (`config.py:579`) qui fige `config/veille_plu.yaml` pour toute la vie du processus.
Le front (node/vite sur 5173) se recharge à chaud → **nouveau bandeau** ; l'API non → **vieux prix /
vieux liens**. D'où l'incohérence « front neuf / API vieille » exactement décrite par l'audit.

Preuves horodatées :
- Processus `:8000` = **PID 93830**, `PPID 1`, démarré **Mer 25 nov 07:17:23 2026**, `cwd
  /Users/openclaw/Desktop/labuse-main`, commande `/Users/openclaw/Desktop/labuse/.venv/bin/labuse api`.
- Fichiers du correctif réécrits **25 nov 08:39:24** (`dvf_secteur.py`, `faisabilite/bilan.py`,
  `config/veille_plu.yaml`, `api/fiche_commune.py`). → le process (07:17) **précède de ~1 h 22** le code
  qu'il est censé servir (08:39).
- `git -C labuse-main rev-parse HEAD` = **`86e33892422a`** (`Merge … origin/fix/outil-communes-1`) : le
  code on-disk contient bien FIX-7/FIX-8 ; seul le processus en mémoire est périmé.
- `GET /parcels/97415000CD0003` **renvoie encore `133`** dans le JSON alors que le code on-disk
  (`dvf_secteur.prix_section`, seuil appliqué) le **masque**.

### a. Quel processus écoute 8000, et d'où importe-t-il `labuse` ?
- PID 93830, démarré 07:17:23, cwd `labuse-main`, cmd `~/Desktop/labuse/.venv/bin/labuse api`,
  environnement `PYTHONPATH=src` + `PWD=/Users/openclaw/Desktop/labuse-main`.
- **Import = `labuse-main/src/labuse`** (le bon dossier). Démonstration : le venv
  `~/Desktop/labuse/.venv` a un *editable install* `__editable__.labuse-0.1.0.pth` pointant vers
  **`/Users/openclaw/Desktop/labuse-ecrans2/src`** — mais **`labuse-ecrans2` n'existe plus** (`ls` =
  *No such file or directory*). Sans `PYTHONPATH=src`, `python -c "import labuse"` → **`ModuleNotFoundError`**.
  Donc c'est bien `PYTHONPATH=src` (résolu depuis `cwd=labuse-main`) qui fournit le module, prioritaire
  sur le `.pth` mort du venv. **Conclusion : bon dossier, mais COPIE EN MÉMOIRE périmée** (chargée à
  07:17, code réécrit à 08:39, pas de reload).

### b. Quelles réponses sont mises en cache (fiche parcelle, commune, carnet, comparateur, PLU) ?
| # | Cache | Où | Portée / TTL | Invalidé par | Survit redémarrage ? | Survit *changement de code* ? |
|---|---|---|---|---|---|---|
| 1 | **`load_yaml_config`** (`config.py:579`, `@lru_cache(maxsize=None)`) — contient **`veille_plu.yaml`** (liens/objets PLU) | mémoire, par process | vie du process (TTL ∞) | **rien** au runtime ; seulement un redémarrage | **Non** (relu) | **Non** — un `.yaml` édité est ignoré tant que le process tourne |
| 2 | **Le code Python lui-même** (`reload=False`) — `dvf_secteur`/`bilan`/`fiche_commune` | mémoire | vie du process | redémarrage | **Non** | **Non** (redémarrage obligatoire) |
| 3 | **`_mem_cached` / `_MEM_CACHE`** (`app.py:1234`) — liste communes (300 s), **Carnet** liste+secteur (`o7-*`, 3600 s), **population fiche commune** (3600 s), L1 comparateur (3600 s), sondes | mémoire, par process | TTL par clé (30 s → 6 h) | expiration TTL, `clear_mem_cache()` (tests), redémarrage | **Non** | sans objet (meurt avec le process) — mais dans un process vivant, un Carnet reste caché **jusqu'à 1 h** même après un `git pull` |
| 4 | **`fiche_cache`** (table DB) + `_FICHE_CACHE` L1 par worker — **fiche parcelle** | base + mémoire | clé = `empreinte_attendue` (run+cascade+résiduel+sources+**code_sha**) + `_fiche_version` (data_sources·tuyau_rev·**`_FICHE_CODE_REV`**) + jeton parcelle | bascule de run (`vider_fiche_cache_partage`), déploiement (code dans la clé), bornage 20000 | **Oui** (table) | **Oui, s'auto-invalide** : `_FICHE_CODE_REV` est **figé à l'import** → un process au nouveau code calcule une clé différente et **ne sert pas** la vieille fiche |
| 5 | **`comparateur_raw_cache`** (table DB) — 24 indicateurs communes bruts (ancien/neuf/permis/vélocité/stock), lus aussi par la **fiche commune** | base | clé = `empreinte_attendue` **seule** | changement d'empreinte (bascule run / nouveau commit **on-disk**), purge > 7 j | **Oui** | **partiellement** : `code_sha()` vient de `git HEAD` **on-disk** (pas du code en mémoire) et est **mémoïsé** au 1ᵉʳ appel → la clé reflète le **disque**, pas la **mémoire** (voir piège ci-dessous) |

Autres caches DB keyés par la même empreinte : `commune_contexte_cache`, `ia_cache`. `dvf_secteur_medianes`
est une **donnée pré-calculée** (le seuil est appliqué *à la lecture*), pas un cache de réponse.

**Ce qui cause les symptômes de l'audit = lignes 1 (yaml → liens PLU) et 2 (code figé → prix de
section).** Ni l'une ni l'autre ne survit à un **vrai redémarrage**. Les caches DB (4, 5) sont keyés
par la révision — mais cette révision est lue **du disque** (`git HEAD`), pas du **code réellement
exécuté** : ils protègent un process *fraîchement démarré*, pas un process laissé tourner sur du
vieux code.

**Piège démontré (ligne 5)** : `code_sha()` (`fraicheur_caches.py:46`) est **mémoïsé** (`_CODE_SHA["v"]`)
au 1ᵉʳ appel. Un process périmé dont le `code_sha` aurait été figé **après** un merge écrirait des
payloads **calculés par l'ancien code** sous la clé du **nouveau** sha (empoisonnement du cache
partagé). Ici le process a démarré à **07:17 < merge 08:39**, donc `code_sha` a (très probablement) été
figé sur **l'ancien** sha → pas d'empoisonnement, caches cohérents-anciens, le redémarrage régénère.
`fiche_cache` (ligne 4) est protégée dans tous les cas car sa clé inclut `_FICHE_CODE_REV` figé à
l'import, distinct entre ancien et nouveau process.

### c. « `lsof -ti :8000 | xargs kill` » arrête-t-il vraiment le serveur avant le nouveau ?
- Ici un **seul** process écoute 8000 (`reload=False`, pas de workers) → `lsof -ti` renvoie ce PID,
  `kill` envoie **SIGTERM**. Uvicorn fait un arrêt **gracieux** (attend les requêtes en vol + lifespan
  shutdown) : **le port reste lié pendant le drain**.
- La commande **rend la main immédiatement** (`kill` n'attend pas la mort du process). Si le nouveau
  `labuse api` démarre aussitôt, son `bind(8000)` peut échouer sur **`[Errno 48] Address already in
  use`** → le nouveau serveur **avorte**, l'ancien (ou rien) reste. **Aucune attente de libération du
  port, aucune vérification que le remplaçant a chargé le nouveau code.**
- Si le process ignore SIGTERM (bloqué), `kill` (TERM) ne le force pas (il faudrait `kill -9`).
- **Verdict** : le plus souvent `kill` arrête, mais **sans garantie d'arrêt effectif avant le
  redémarrage ni de bonne révision servie** → fragile. C'est exactement le scénario observé (process de
  07:17 ayant survécu à la MAJ de 08:39). → corrigé au LOT B (attente des ports + vérification de la
  révision servie).

### d. Le même mécanisme existe-t-il en PRODUCTION ?
- Prod = **systemd** `labuse.service` : Uvicorn **5 workers** sur `127.0.0.1:8000`, `Restart=always`
  (`docs/DEPLOYMENT_OVH_VPS.md:236-237`, `deploy/systemd/labuse.service`).
- Le vrai déploiement `deploy/scripts/deploy_app.sh:291` fait **`sudo systemctl restart labuse`**, et le
  runbook (`docs/DEPLOY_RUNBOOK.md:43`, étape 5) ajoute un **healthcheck `/readyz`** (attend 60 s).
  `deploy.sh` (racine, variante locale/partielle) écrit `config/deploiement.json` (= `git HEAD`) et joue
  `labuse rebuild`, mais **ne redémarre que `cron`**, pas l'API.
- **Réponse** : en prod, **non** — un `systemctl restart labuse` remplace proprement le process (les 5
  workers), chaque worker recalcule `code_sha`/`_FICHE_CODE_REV` sur le nouveau code → les caches DB
  (keyés par l'empreinte, qui inclut `code_sha` = sha écrit dans `deploiement.json`) **ne servent plus
  l'ancien code**. **Le risque n'existe QUE si le redémarrage est sauté** — précisément le cas en local
  (pas de systemd, redémarrage manuel non garanti) → la cause du présent incident. Garde-fou prod
  implicite supplémentaire : `Restart=always` + le healthcheck `/readyz` du runbook.

### Complément (journal de l'API locale) — `/readyz` 503 et `source=q_v8_calibre`
- **`/readyz` = 503 en boucle.** Le corps le dit : `served_run.ok=true, run="q_v20"` (le run servi est
  **bien q_v20**), `data.ok=true`, `schema.missing=[]`. Le SEUL motif du 503 est **`heal.ok=false`** :
  le **heal de schéma au boot** a avorté sur un `IntegrityError` —
  `null value in column "is_placeholder" of relation "bilan_params"` sur l'UPDATE
  `SET is_placeholder = (provenance = 'estimee')` (`models.py:1741`). Cause exacte : une ligne
  **`_probe`** traîne dans `bilan_params` (`secteur='_probe', param='_probe', value=1, is_placeholder=false,
  provenance=NULL`, posée le 24/11 10:51 — **aucun code du dépôt n'écrit `_probe`** : artefact local).
  Pour cette ligne, `(NULL = 'estimee')` vaut **NULL** → viole le `NOT NULL` de `is_placeholder` → tout
  le heal échoue → `/readyz` (FIX-GB-011) reflète honnêtement `ready=false` → **503**. (Les deux autres
  signaux du corps — `1862` zones AU en attente, `base_url=localhost` — sont des *warn/actions*, PAS la
  cause du 503.)
- **`source=q_v8_calibre`.** `q_v8_calibre` est un **label de run** (la cible de bascule scoring M28,
  `bascule_gardes.TARGET`), **3 runs EN ARRIÈRE** du run servi `q_v20`. Il arrive par le **paramètre de
  requête `?source=<run>`** que le client (le front / un onglet laissé ouvert) ajoute pour épingler un
  run (`app.py:763`, `app.py:2501`). Les **404** sur `97417000AE0003`, `97410000BV0120`,
  `97415000AC0253` = ces parcelles **n'existent pas dans le run q_v8_calibre** (ajoutées à des runs
  ultérieurs) → 404 légitime pour un run épinglé périmé. Le **défaut serveur**, lui, est bien le run
  servi (`runs.cascade()`/`runs.current()` = q_v20) — l'ancien défaut `"q_v8_calibre"` a déjà été retiré
  des cascades expertes (`served_cascade.py:22`).
- **L'un des deux cause-t-il le fait de ne pas servir le code de main ? NON.** Les trois faits sont
  **indépendants** : (i) le code périmé = `reload=False` + process long + `lru_cache` YAML ; (ii) le 503 =
  bug d'intégrité du heal (ligne `_probe` à `provenance=NULL` + UPDATE non *null-safe*) ; (iii) le
  `q_v8_calibre` = un **client** qui épingle un vieux run via `?source=`. Mais le 503 est un **signal
  d'instance malsaine** : `relancer_local.sh` doit **exiger `/readyz` == 200** (donc le heal doit être
  rendu *null-safe* — LOT B) ; et le pin `q_v8_calibre` rappelle que le script doit aussi **vérifier le
  run servi** et qu'un client ne doit pas épingler un run mort.

---

## LOT B — correction de la cause

**(1) `scripts/relancer_local.sh`** — relance SÛRE : arrête l'API (:8000) et le front (:5173), **attend
que les ports soient réellement libres** (SIGTERM → boucle d'attente → SIGKILL en dernier recours ; c'est
le point qui manquait au `lsof | xargs kill`), démarre l'API depuis le dépôt, puis **échoue bruyamment**
si l'une des conditions suivantes n'est pas remplie :
- `/readyz` != 200 ;
- la **révision du code CHARGÉE** par l'API (`/readyz.code_rev`, figée à l'import = git HEAD au démarrage
  du process — nouveau champ exposé dans `app.py`) **≠** `git HEAD` du dépôt → « l'API sert un AUTRE code
  que le dépôt » (le process survivant à une MAJ est enfin DÉTECTÉ, pas supposé) ;
- le run servi est affiché (warn si ≠ `LABUSE_EXPECTED_RUN`).
Le défaut de fond (`code_sha()` lit git HEAD **on-disk**, pas la mémoire) est ainsi neutralisé : la
vérification compare la révision **en mémoire** (`code_rev`) au disque.

**(2) Invalidation des caches par révision.** `/readyz` ne passait pas 200 à cause du heal (LOT A) :
corrigé — `models.py` rend l'UPDATE `bilan_params.is_placeholder` **null-safe** (`(provenance='estimee')
IS TRUE`), donc une ligne à `provenance` NULL ne fait plus échouer le heal. Et le script **PURGE au
démarrage** les caches de RÉPONSES de `labuse` (autorisé par Vic — ceux-là seuls) :
`fiche_cache`, `comparateur_raw_cache`, `commune_contexte_cache`, `ia_cache`. Aucune table de DONNÉES
n'est touchée. Rappel : `fiche_cache` est **déjà** keyée par `_FICHE_CODE_REV` (figé à l'import) → une
fiche d'un ancien code n'est de toute façon pas servie par un process neuf ; la purge couvre les caches
dont la clé ne porte que l'empreinte (comparateur) et ferme le piège d'empoisonnement du LOT A.

Preuve (sortie brute de `scripts/relancer_local.sh` + routes réelles) : voir l'annexe B ci-dessous.

## LOT C — points réels du rapport

**(3) Bilan — « sections » vs « ventes » + explication du seuil.** `compute_mode_b` sert désormais
`effectif_unite` (« ventes » au niveau secteur = effectifs d'actes, « sections » au repli communal) et
une phrase `note_seuil` : « Hypothèse de Bilan fondée sur N ventes. Un prix de marché est publié à partir
de 8 ventes. » Rendu à l'écran (`constructibilite.tsx`), dans le PDF (`rehab_bloc`) et les exports
markdown/HTML. Preuve `scripts/communes_fix9_bilan_unite.py` (sortie en annexe C) :
- secteur 7 ventes (97406000AR) → « 74 €/m² × 500 m² · **7 ventes** · Estimé » + la phrase de seuil ;
- repli communal (97415000CD0003 terrain, l'exemple EXACT du §3 : 291 €/m², 56 sections) → « 291 €/m² ×
  500 m² · **56 sections** · Estimé » — **jamais** « 56 ventes ».
**Bilan rendu de bout en bout : IMPOSSIBLE sur cette base, dit en clair.** Le mode B exige
`parcel_p_score_v2.tier ∈ {declasse_bati_sature, declasse_bati_revele}` (`bilan.py:1222`) ; le run servi
**q_v20 en contient 0** (tiers présents : sans_signal 279 144, ecartee 153 283, a_suivre 659, priorite
143). Le run q_v20 de cette base n'émet pas les deux tiers « déclassé pour cause de bâti » → aucune
parcelle n'ouvre le mode B. (Prouvé en annexe C.)

**(4) Liens PLU** (10/10 vérifiés par `scripts/communes_fix8_liens.py`, sortie en annexe D) :
- **Les Trois-Bassins** : date au MOIS — `etat_source_date: "2025-05"` → rendu « **en mai 2025** » (et non
  « 01/05/2025 »), par `_fr_date_iso`/`_fr_date_au` (back) et `bandeauEtatPluSous` (front), préposition
  « en » pour une précision mois/année.
- **Saint-Denis / Saint-Paul** : l'objet servi est bien « **document opposable au GPU (rattachement à la
  révision générale non certifié)** » (`piece_objet`), pas « révision générale » — vérifié dans la
  citation servie (annexe D).
- **Sainte-Marie** : le PDF de la délibération (26/11/2025) **s'ouvre en HTTP 200 dans un vrai navigateur**
  (Chromium/Playwright, annexe D) ; le 406 observé par le relecteur est un filtre anti-robot sur les
  requêtes sans en-têtes de navigateur — un promoteur qui clique l'obtient.
- **La Plaine-des-Palmistes** (arbitrage Vic 25/11/2026 — on n'invente rien, on ne re-date pas sur une
  pièce non ouvrable) : la fiche affiche l'ÉTABLI — **révision générale prescrite le 24/09/2015
  (délibération DCM40-240915)** — et dit « **aucune pièce postérieure retrouvée par LABUSE** » avec
  « **vérifié le 25/11/2026** » (date_constat servie par la fiche). **Le lien vers la séance du 27/11/2025
  est RETIRÉ** (aucune de ses 39 délibérations ne porte sur le PLU) ; `source_url` ouvre la **page PLU
  municipale** qui liste la délibération de prescription. Citation servie : « Ville de La
  Plaine-des-Palmistes — révision générale prescrite le 24/09/2015 (délibération DCM40-240915) — aucune
  pièce postérieure retrouvée par LABUSE — dernière pièce connue de LABUSE au 24/09/2015 ». L'adresse exacte
  d'une pièce postérieure, si le relecteur externe la fournit, sera intégrée.

**(5) Décompte.** « 433 » = couples section × type de bien à 3-7 ventes, répartis en **212 terrains, 151
maisons, 70 appartements**, sur **364 sections cadastrales distinctes**. Pour la dérogation du Bilan sur
le terrain nu, le nombre pertinent est **212** (prouvé par requête, annexe C).

## LOT D — test `test_simulplu` et angle mort du hook

**Confirmé** : `tests/test_simulplu.py::test_communes_en_procedure_actives_seulement` cassait — il
attendait `{97409, 97413, 97423}` alors que le registre `veille_plu.yaml` compte désormais **8** révisions
générales actives servies (97404, 97406, 97409, 97411, 97413, 97414, 97415, 97423 : toutes `revision_plu`,
SOURCE, prescrites, non dormantes). `communes_en_procedure()` les remonte toutes — c'est CORRECT. Le test
était un canari figé sur 3.

**Pourquoi le hook ne l'a pas vu** : le module `tests/test_simulplu.py` porte `pytestmark =
pytest.mark.db` (l.21). Ce test PUR (registre seul, aucune base) héritait donc du marqueur `db`, et le
hook pre-push sélectionne `-m "not db and not local and not reel and not network"` → **le module entier
est désélectionné** (`--collect-only` : « no tests collected (5 deselected) »). La CI GitHub (qui joue les
tests `db`) l'aurait vu ; le hook rapide, non.

**Corrigé** : l'invariant PUR est DÉPLACÉ dans `tests/test_veille_plu.py` (sans marqueur `db` → joué par
le hook), réécrit en **robuste** (superset des 8 révisions + exclusions dures dormante/clôturée/« aucune »
+ égalité avec `procedure_active` du registre) : il ne recassera pas à l'ajout d'une révision, mais casse
si une inactive fuit. Le contrat DB (`moteurs.simulplu_procedures`) reste dans `test_simulplu.py`, son
assertion alignée sur le superset.

---

## Annexes (sorties brutes)

### Annexe B — `scripts/relancer_local.sh` (depuis le worktree, qui porte FIX-9) + routes réelles
```
→ arrêt API (:8000) — PID(s) 41584 (SIGTERM)…
✓ API arrêté, :8000 libre
→ purge des caches de réponses (fiche_cache, comparateur_raw_cache, commune_contexte_cache, ia_cache)…
   · fiche_cache: 1 ligne(s) supprimée(s)
   · comparateur_raw_cache: 1 ligne(s) supprimée(s)
   · commune_contexte_cache: 0 ligne(s) supprimée(s)
   · ia_cache: 0 ligne(s) supprimée(s)
→ démarrage de l'API depuis /Users/openclaw/Desktop/labuse-communes-fix (git HEAD e570064878f8)
✓ /readyz = 200
✓ révision servie = e57006487 == git HEAD e570064878f8 (le code de main EST servi)
✓ run servi = q_v20
✓ front en écoute sur :5173
✓ RELANCE OK — API saine, code de e570064878f8 servi, caches de réponses purgés.
```
Routes réelles APRÈS relance (API :8000, code FIX-9) :
```
CD0003 fiche  — « 133 » présent : False        (prix masqué = code de main servi)
Carnet 97415000CD — « 133 » présent : False
Carnet 97401000AT (Avirons) — maison « 3905 » présent : False   (masquée au seuil 8)
Carnet 97408000AB (Possession) — maison « 2624 » présent : False
HTTP /communes/Saint-André/contexte — lien MRAe « 2025areu7 » servi : True ; data.gouv générique : False
/readyz — ready=True, code_rev=git:e57006487, served_run=q_v20, heal.ok=True, schema.ok=True
```
10 liens PLU servis par `plu_statut` (fonction de l'API) :
```
97404 Étang-Salé   letangsale.fr/.../revision-allegee-n-1-...-approuvee-le-17-septembre-2025
97406 Plaine       ville-plainedespalmistes.fr/plan-local-urbanisme/  (prescription 2015 DCM40-240915 ; aucune pièce postérieure retrouvée, vérifié le 25/11/2026)
97409 Saint-André  mrae.../IMG/pdf/2025areu7_rev_plu_saint_andre.pdf
97411 Saint-Denis  geoportail-urbanisme.gouv.fr/document/by-id/eee143…  (97411_PLU_20260805)
97413 Saint-Leu    saintleu.re/pdf/plu/2026/enquete-publique/conclusions-motivees-et-avis-de-la-commission.pdf
97414 Saint-Louis  saintlouis.re/images/pdf/PLU/ANNEXE DCM N191_DOSSIER MS DU PLU N5…pdf
97415 Saint-Paul   geoportail-urbanisme.gouv.fr/document/by-id/0f717…  (97415_PLU_20251217)
97418 Sainte-Marie ville-saintemarie.re/wp-content/uploads/2026/03/99_DE-974-219740180-20251126-…pdf
97420 Ste-Suzanne  data.geopf.fr/annexes/gpu/documents/DU_97420/…/97420_reglement_20250929.pdf
97423 Trois-Bassins docs.trois-bassins.re/urbanisme/PLU/REVISION/PADD/Support_PLU_…PADD_…Mai_2025.pdf
```

### Annexe C — Bilan : unité « sections/ventes » + note de seuil + accès mode B (`communes_fix9_bilan_unite.py`)
```
[ACCÈS MODE B] run servi=q_v20 · parcelles éligibles (tier ∈ ('declasse_bati_sature','declasse_bati_revele')) = 0
  tiers présents q_v20 : sans_signal 279144, ecartee 153283, a_suivre 659, priorite 143
[A] secteur 7 ventes (97406000AR) :
  terrain_nu.effectif=7 effectif_unite='ventes'
  note_seuil = 'Hypothèse de Bilan fondée sur 7 ventes. Un prix de marché est publié à partir de 8 ventes.'
  [rendu] Terrain nu au prix du secteur : ~25 k€ – 49 k€ (74 €/m² × 500 m² · 7 ventes · Estimé, fourchette ±30 %)
[B] repli communal (97415000CD0003 terrain, exemple §3) :
  _prix_terrain_local = {prix_m2: 291, n: 56, niveau: 'commune', libelle: 'médiane DVF terrain de la commune — 56 sections (repli)'}
  [rendu] Terrain nu au prix du secteur : ~100 k€ – 190 k€ (291 €/m² × 500 m² · 56 sections · Estimé, fourchette ±30 %)
SUCCÈS : « ventes » (secteur) vs « sections » (repli) ; note_seuil servie ; accès mode B q_v20 = 0.
```
Décompte (5), requête `dvf_secteur_medianes WHERE n_ventes BETWEEN 3 AND 7` :
```
couples section×type : 433  →  terrain 212, maison 151, appartement 70
sections cadastrales DISTINCTES : 364      TERRAIN (nombre pertinent) : 212
```

### Annexe D — liens PLU (`communes_fix8_liens.py`) + Sainte-Marie navigateur
```
10/10 : HTTP 200 + jeton date/objet trouvé dans la pièce OU l'URL (curl + pdftotext). Dont :
  97406 Plaine        200  jetons ['révision générale','plan local','plainedespalmistes','PLU'] (page PLU listant la prescription 2015)
  97423 Trois-Bassins 200  jetons ['padd','mai 2025','trois-bassins','réunions publiques']
Sainte-Marie (PDF délibération) — navigateur Chromium/Playwright : GET …99_DE-974-…-20251126-… => [200] OK
  (le 406 du relecteur = filtre anti-robot sur requêtes sans en-têtes navigateur ; un clic l'obtient)
Citations servies (objet) : Saint-Denis / Saint-Paul = « document opposable au GPU (rattachement … non certifié) » ;
  Trois-Bassins = « … (concertation, mai 2025) — dernière pièce connue de LABUSE en mai 2025 ».
```

