# COHERENCE-HOOK-1 — compte-rendu

Branche `fix/coherence-hook-1` · worktree `~/Desktop/labuse-hook` · ports 9200/6400 · **pas de merge**.
Prod en LECTURE SEULE (point 4 seulement). Aucune ligne de code applicatif touchée : uniquement
tests, hook, scripts et la base locale (les sessions // RADAR-4 et VITESSE-3 gardent le code applicatif).

Pourquoi ce mandat : l'app dérivait sans rien casser — un même fait servi à plusieurs valeurs, et des
tests rouges qui restaient rouges des jours sans alarme. Ce travail rend la dérive **impossible à ignorer**.

---

## 1. Suite de cohérence unique — `tests/coherence/`

Nouvelle suite, marqueur `coherence` (déclaré dans `pyproject.toml`). Sur les **12 parcelles témoins**
du lot A (mêmes IDU que `test_sdp_unique_coherence`), chaque FAIT est extrait **tel qu'il est servi**
par les points d'entrée réels (appelés en process, sans serveur HTTP) et comparé **à l'euro / au m²**.
Le moindre écart fait échouer.

| Fait | Points de lecture confrontés | Invariant vérifié |
|------|------------------------------|-------------------|
| **Zone PLU** | fiche (`reglement_plu.zones[0]`) ↔ moteur `zone_servie.zone_dominante` (celui qu'appellent le Copilote `destination_zone`/`regles_plu_zone` et l'Étude de zone) | même zone dominante, label pour label |
| **Surface terrain** | fiche (`surface_terrain_m2`) ↔ point unique `surface.surface_terrain(dessin, contenance)` | ≤ 1 m² |
| **Médiane de marché (bâti)** | point unique `mediane_commune` ↔ tableau Radar `_dvf_bati_type` ↔ bloc commune `marche_commune_bloc` | ≤ 1 € (maison + appartement) |
| **Estimation** | endpoint `radar_annonce_estimation` (outil « Estimer un bien » + PDF + 9ᵉ doc) ↔ point unique `estimation_annonce` | ≤ 1 € (y compris « rien » des deux côtés) |
| **Nombre d'aléas / risques** | fiche `aleas.n == len(aleas.liste)` ; endpoint `n_aleas` ↔ point unique `_risques_rows(fiche)` | égalité stricte |
| **SDP résiduelle** | en-tête (`parcel_residuel`) ↔ verdict (`score_labuse`) ↔ scoring (`parcel_p_score_v2`) | ≤ 1 m² (consolide SDP-UNIQUE-1) |

Fichiers : `tests/coherence/__init__.py`, `tests/coherence/conftest.py`, `tests/coherence/test_temoins.py`.

**Distinctions établies empiriquement (pour ne pas comparer des pommes et des poires) :**
- La **médiane de l'estimation** (`estimation_annonce.median`, à rayon de comparables) n'est PAS la
  médiane de COMMUNE (`mediane_commune`) — ce sont deux grandeurs distinctes ; seule l'égalité des TROIS
  lectures de la médiane commune bâtie est exigée (comme `test_marche_unique_1`). Le terrain n'est pas
  servi par le tableau bâti (`_dvf_bati_type`) → hors de cette égalité.
- Le **bloc « aléas naturels » de la fiche** (`aleas.n`) et la table **« risques et pièges »**
  (`_risques_rows`, qui dédoublonne DEAL/PPR et inclut d'autres pièges) sont des notions DIFFÉRENTES ;
  chacune est vérifiée contre SA source, jamais l'une contre l'autre.

**« Regroupe les tests posés par SDP-UNIQUE / PPR-UNIQUE / MARCHE-UNIQUE / ESTIMER-2 » :** le marqueur
`coherence` a été ajouté à `test_sdp_unique_coherence`, `test_marche_unique_1` et `test_ppr_unique` — ils
sont donc rejoués par `-m coherence` et par le banc de nuit, en plus des nouveaux tests témoins.

Résultat local (base réelle, run servi 17) : **6/6 verts** (`pytest tests/coherence/ -m coherence`, ~62 s).

---

## 2. Hook pre-push — la suite au push, ou rouge jamais silence

`scripts/git-hooks/pre-push` gagne une 4ᵉ étape « Cohérence » qui appelle `scripts/ci/coherence_run.sh`
(point d'entrée partagé avec le banc de nuit) :

- **Base locale OK** → joue `pytest -m coherence tests/coherence/` avec `LABUSE_COHERENCE_REQUIRE_DB=1`
  (un skip silencieux devient alors un ÉCHEC). Un écart (1 €/1 m²) **REFUSE le push**.
- **Base injoignable** → message **ROUGE explicite** (« BASE LOCALE INJOIGNABLE — suite NON EXÉCUTÉE »),
  jamais un silence. Par défaut NON bloquant (code 2) pour ne pas paralyser les sessions // qui
  poussent base froide ; `LABUSE_COHERENCE_HOOK=block` rend ce cas bloquant aussi. Le banc de nuit reste
  le filet dur. `git push --no-verify` contourne (secours documenté, inchangé).

`tests/coherence/conftest.py` porte la bascule skip/échec : sans `LABUSE_COHERENCE_REQUIRE_DB` → SKIP
(dev/CI) ; avec (hook + nuit) → ÉCHEC rouge. Vérifié : base absente + `REQUIRE_DB` ⇒ 6 ERROR (rouge) ;
base OK ⇒ 6 passed.

---

## 3. Zéro test rouge

### 3.a — les 9 échecs hérités (6 `test_cascade`, `test_pente_exposition`, `test_implantation2`, `test_boot_verrou_1`)

Diagnostic : **tous de classe « fixture / isolation manquante dans `labuse_test` », aucun comportement
applicatif changé.**

- **6 `test_cascade` + `test_pente_exposition`** : cause unique — un cache dérivé figé
  `spatial_layers_sub` (26 lignes `vefa_neuf` laissées par un test antérieur, survivant au rollback)
  que `cascade.context.prime()` lit À LA PLACE des couches semées dans la transaction. Le remède existait
  déjà (fixture `cascade_live_layers`, VITESSE-2 Lot 5, qui DROP le sub dans la transaction) mais n'était
  pas câblé ici. Corrigé : `demo(cascade_live_layers)` dans `test_cascade.py`, idem pour les deux tests
  cascade de `test_pente_exposition.py`. **Tests-only.**
- **`test_implantation2`** : le calcul de la route `etude_implantation` tourne dans un PROCESSUS « spawn »
  (ETUDE-ASYNC-1) qui ne voit pas l'engine rebranché en mémoire — il relit `LABUSE_DATABASE_URL` que
  conftest épingle sur `labuse_test` (vide des parcelles) → « parcelles introuvables ». Corrigé : la
  fixture `_base_reelle` pointe AUSSI l'ENV sur la base réelle (hérité par le fils). **Tests-only.**
  - Ce correctif a révélé un **faux vert masqué** : `test_route_etude_entrees_invalides` affirmait
    « `type_projet=lotissement` → 400 » — vrai jadis (collectif seul actif), FAUX aujourd'hui
    (`service._TYPES_PROJET` sert le lotissement). Le cas ne passait QUE parce que le fils 400-ait sur
    « introuvables ». Garde remise en POSITIF : lotissement SERVI (`moteur.livrable == ETUDE-V6-LOTISSEMENT`).
- **`test_boot_verrou_1`** : vert en isolation ET dans le banc COMPLET (absent de la liste des échecs
  du run de nuit, §3.c) — fragilité d'ordre résorbée. Aucune action de code requise.

Vérifié : `test_cascade` + `test_pente_exposition` + `test_implantation2` = **tous verts** en ciblé, et
aucun des 9 n'apparaît dans les échecs du banc complet (§3.c).

### 3.b — les échecs signalés par RADAR-4 sur main (client/marche, test_g7) + `test_selection_sql`

- **marche — `test_marche_commune::test_gisement_run_servi_et_dpe_denominateur_connu`** : le test
  affirmait que le libellé BRUT du run (`q_v20`) figure dans l'`etiquette` du gisement. Origine (git) :
  `29025ba3f8` (COMMUNE-FIX-1, famille des merges commune/marché, adjacente à MARCHE-UNIQUE) a
  DÉLIBÉRÉMENT rendu l'étiquette LISIBLE (« Analyse LABUSE · run servi ») en gardant le run technique
  dans `date_amont` (« run q_v20 · 2026-10-21 »). **Changement de comportement SERVI voulu** (commentaire
  explicite dans `ligne7_gisement`). Correctif **tests-only** : on vérifie le run dans `date_amont` (là où
  il est servi) et « run servi » dans l'étiquette — sans toucher au comportement servi. ✓ 5/5.
- **client — `test_pige_client` / `test_pige_marche`** : rejoués sur base isolée → **14/14 verts**,
  aucun écart reproduit (pas de régression MARCHE-UNIQUE côté client).
- **`test_g7_vert_apres_sonde`** (`verrous/test_garanties.py`, `@pytest.mark.local`) : **NE vient PAS de
  MARCHE-UNIQUE**. Verdict « casse » parce que la SONDE `circuit_controles` n'a pas tourné depuis 3 j sur
  ce Mac (« au-delà de 48 h ») — les « 2 fuites ouvertes » étaient « toutes affichables » (non pénalisantes).
  Signal OPÉRATIONNEL juste (probe périmée), pas une dérive de code : correctif = faire tourner la sonde
  (hors périmètre — ni code applicatif, ni mensonge du test).
- **`test_sources_fix::test_selection_sql_egale_predicat_python` (115 contre 116)** : vrai écart SQL↔Python.
  **Ligne en cause trouvée** : la source `50 pas géométriques — limite haute (DEAL)` portait
  `affichage_desactive = TRUE` dans `labuse_test` (dérive accumulée) alors qu'elle est **affichée (FALSE)
  en prod**. Le SQL `WHERE_AFFICHEES` l'écartait (115) ; le prédicat `est_affichee`, appelé par le test
  sans la colonne `affichage_desactive` (défaut False), la comptait (116). **Correction de la SOURCE, pas
  du test** : la donnée locale est réalignée sur la prod (source de nouveau affichée) → 115 = 116. ✓.
  (Latents SIGNALÉS, non touchés car code applicatif : `est_affichee` défausse `affichage_desactive` par
  défaut, et `WHERE_AFFICHEES` exclut `DOUBLON%` quand le prédicat Python n'exclut que `DOUBLON de` — deux
  inéquivalences à aligner par les propriétaires ; aucune ligne ne les déclenche aujourd'hui.)

### 3.c — autres rouges pré-existants surfacés par le banc de nuit complet

Le banc COMPLET (`pytest -m "not network"`, base réelle) a tourné en 47 min : **9 failed / 4346 passed /
88 skipped**. Les 9 de §3.a sont RÉSOLUS (absents de la liste). Restent, TOUS `local`/`reel` (base réelle
servie, souvent rendu PDF / serveur / enrichissement vifs que ce poste n'offre pas), **pré-existants sur
`main`, hors des périmètres nommés et NON touchés par ce mandat** (aucun code applicatif modifié) :

| test | marqueur | motif (non ignoré — surfacé par le banc, à trier par les propriétaires) |
|------|----------|--------|
| `test_sources_fix::test_selection_sql…` | db | **RÉSOLU** depuis ce run (réalignement base locale, §3.b) |
| `test_garanties::test_g7_vert_apres_sonde` | local | sonde `circuit_controles` périmée (ops), §3.b |
| `test_circuit_provenance::…[97416000DY0106]` | local | provenance des nombres de documents, base réelle |
| `test_docs1_ecran_egale_pdf::test_gabarit_…` | local | égalité écran==PDF Gabarit (rendu PDF vif) |
| `test_etude_v6_stationnement::test_senior_…` (×2) | reel | règle stationnement « senior », base réelle |
| `test_implantation3_pdf::test_route_rend_un_pdf[Étang-Salé]` | reel | route PDF (WeasyPrint), base réelle |
| `test_verrous/test_lot1_tables::…base_reelle` | local | verrou tables sur base réelle |
| `test_verrous/test_lot3_versions::…base_reelle` | local | verrou versions sur base réelle |

Ces rouges NE SONT PAS masqués : le banc de nuit les affiche et notifie. Leur correction demande soit
l'environnement vif (serveur/PDF/enrichissement), soit du code applicatif tenu par les sessions // — hors
du périmètre « tests/hook/scripts/base locale » de ce mandat. **Aucun n'est marqué « ignoré ».**

---

## 4. Base du Mac alignée sur la prod (lecture seule prod)

Script reproductible `scripts/aligner_base_prod.sh` (idempotent, `--verif` pour vérifier sans écrire) :

- **Garde** : le run résiduel servi doit être le **17** des DEUX côtés (sinon ABANDON). Vérifié :
  prod=17, mac=17, `mvt_meta.run_label=q_v20`, manifeste `residuel_run_seq=17`.
- **`parcel_cadastre_remplacement`** : absente du Mac → importée par `pg_dump -t` (prod lecture seule).
  **3007 lignes** (= prod).
- **Annonces Bien'ici** : import ADDITIF par bien (tout bien portant ≥1 annonce bienici + ses annonces
  bienici + ses faits), **IDs décalés de +1 000 000** pour ne jamais entrer en collision avec les
  Leboncoin du Mac → la session RADAR-4 garde ses annonces intactes. **100 annonces bienici** (= prod).
  - Divergence de schéma rencontrée et contournée : `pige_biens` a les MÊMES colonnes Mac/prod mais dans
    un ORDRE différent (`a_qualifier` ↔ `rattachement_criteres`) → le script sélectionne les colonnes de
    prod dans l'ordre du Mac. Les ~4 annonces Leboncoin de biens fusionnés inter-portails ne sont pas
    réimportées (déjà présentes côté Mac → collision `uq_pige_annonces_url`).

**Écart résiduel Mac vs prod (après alignement) :**

| grandeur | Mac | prod | note |
|----------|-----|------|------|
| `parcel_cadastre_remplacement` | 3007 | 3007 | aligné |
| annonces bienici | 100 | 100 | aligné |
| annonces leboncoin | 428 | 344 | **+84** : annonces de test locales préexistantes (hors de ce mandat ; préservées par l'import additif) |
| annonces (total) | 528 | 444 | = +84 leboncoin ci-dessus |

Effets de bord notés : séquences `pige_biens_bien_id_seq` / `pige_annonces_annonce_id_seq` relevées
au-dessus du décalage (futurs inserts locaux ≥ 1 000 435 — sans conséquence fonctionnelle).

---

## 5. Banc de nuit — 22 h 30 heure Réunion

- `scripts/nuit/banc_coherence.sh` : rejoue la suite COMPLÈTE avec base (`-m "not network"` =
  db + reel + local + coherence) sur la base réelle, `LABUSE_COHERENCE_REQUIRE_DB=1` (base muette = rouge,
  jamais silence). Rapport daté `~/labuse-nuit/coherence-AAAA-MM-JJ.log`. **Notification macOS
  (osascript) UNIQUEMENT si un test est rouge.**
- Ancrage HEURE RÉUNION robuste au changement d'heure de Paris (doctrine RADAR-COUVERTURE-1) : le script
  ne tourne que dans la fenêtre [22:15, 23:45] Réunion (`TZ=Indian/Reunion`), au plus une fois/jour (verrou
  `~/labuse-nuit/.ran-JJ`). Le job launchd `immo.labuse.banc-coherence` l'amorce à 19:30 ET 20:30 Paris
  (qui encadrent 22:30 Réunion été comme hiver).
- Installation : `scripts/nuit/installer_banc.sh` (séparé d'`install_agents.sh` à dessein : ce banc LIT
  le dépôt sous `~/Desktop`, ce que la garde TCC d'`install_agents.sh` interdit). **⚠ macOS/TCC : donner
  « Accès complet au disque » à `/bin/bash`** (le job lit `~/Desktop`), sinon « Operation not permitted ».
- Vérifié (plomberie, `--force`) : rapport écrit, run servi détecté (17), vert en sélection ciblée ;
  chemin ROUGE (base down) → rapport + notification + code ≠ 0.

---

## 6. Fumée de déploiement — âge du run servi + caches de médianes

`deploy/scripts/smoke_test.sh` gagne deux contrôles BLOQUANTS (seuils configurables) :

- **Âge du run servi** : `now − residuel_runs.computed_at_max` du run servi ≤
  `LABUSE_SMOKE_RUN_MAX_AGE_DAYS` (défaut 90). Complète le check manifeste existant (QUEL run) par la
  fraîcheur (pas un run figé / promote oublié). Prod actuel : 10 j ✓.
- **Âge des caches de médianes** (`dvf_secteur_medianes`) : présent + non vide + À JOUR — si la colonne
  `millesime_dvf` existe (NU-E-032), son millésime == le millésime DVF courant (comparaison
  autoritative) ; sinon repli sur l'âge de `computed_at` ≤ `LABUSE_SMOKE_CACHE_MAX_AGE_DAYS` (défaut 180).
  Miroir SQL de `marche_dvf_commune.caches_marche_perimes`. Constat : `millesime_dvf` ABSENTE des deux
  caches EN PROD (NU-E-032 jamais posé sur ces tables) → repli âge utilisé ; prod actuel : 75 j ✓.

Vérifié : seuils par défaut → vert ; seuils serrés (5 j / 30 j) → les deux checks passent au ROUGE.

---

## 7. Recette

- **Preuve que la suite CASSE sur un écart d'UN euro** : fichier jetable `tests/coherence/_recette_ecart_1euro.py`
  qui fait mentir d'1 € UNE lecture de la médiane (`_dvf_bati_type` +1 €) puis rejoue la vérification.
  → la suite devient ROUGE (`mediane_commune=2380.09 ≠ tableau_radar=2381.09`, idem Cilaos/Saint-Denis/
  Saint-Philippe/Salazie). **Révélation de recette** : la tolérance initiale (`> 1 €`) TOLÉRAIT l'écart d'1 € —
  corrigée en ÉGALITÉ STRICTE (tout écart ≥ 1 €/1 m² échoue), conforme au mandat. Fichier **retiré** ensuite.
- **Suite de cohérence 0 rouge** : `pytest tests/coherence/ -m coherence` → **6/6 verts** (égalité stricte,
  base réelle, run servi 17).
- **Hook vert** : `scripts/ci/coherence_run.sh` → sonde OK (run 17) + 6/6 ; base coupée → code 2 ROUGE
  explicite (jamais silence). Étape câblée dans `scripts/git-hooks/pre-push`.
- **Commit** : `fix/coherence-hook-1` (pas de merge, pas de push — cf. mandat).

---

## Décisions notables

- **Hook DB-down non bloquant par défaut** : choisi pour ne pas forcer `--no-verify` à chaque push des
  sessions // (RADAR-4/VITESSE-3) base froide, tout en restant ROUGE visible. `LABUSE_COHERENCE_HOOK=block`
  disponible si Vic préfère bloquer. Le filet DUR reste le banc de nuit (notification).
- **Import bienici additif (décalage d'ID) plutôt que remplacement** : zéro perte des données locales,
  zéro perturbation de RADAR-4, écart résiduel documenté (conforme à « écrire l'écart restant »).
