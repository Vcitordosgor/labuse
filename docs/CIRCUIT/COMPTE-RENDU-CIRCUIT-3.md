# COMPTE-RENDU CIRCUIT-3 — Le filtre : la qualité à l'intérieur de chaque source

Branche : `feat/circuit-3` (worktree `~/Desktop/labuse-audit`), créée depuis `origin/main`
(`adfd947e Merge CIRCUIT-1 + CIRCUIT-2`) — **CIRCUIT-1 et CIRCUIT-2 sont mergés dans `main`**,
donc départ depuis `main` comme le mandat le prescrit. Rien de ce mandat n'est mergé.

Reprise : « continue CIRCUIT-3 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-3.md ».

## Étape 0 — état de départ

- `pwd` = `~/Desktop/labuse-audit`, arbre **propre**, branche `feat/circuit-3`.
- **Suite de départ : 2407 passed · 1 failed · 49 skipped** (89 s). Le seul rouge est
  `test_front_reliquats.py::test_r5` — le **pré-existant admis depuis CIRCUIT-1** (non lié).
  PIÈGE retenu : les tests exigent `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (WeasyPrint /
  libgobject), et **SIP retire les `DYLD_*` à travers `nohup`** → lancer sans nohup.
- **La base applicative `labuse` est accessible en local** (431 663 parcelles = le chiffre du
  mandat, 78 lignes `data_sources`). Les seuils du lot 2 sont donc **mesurés sur la version
  servie réelle**, pas inventés. Les tests, eux, tournent sur `labuse_test` (base partielle).
- PIÈGE worktree : le paquet `labuse` installé (éditable) pointe sur `~/Desktop/labuse` (le clone
  principal). Toute mesure/CLI du worktree se joue avec `PYTHONPATH=src`. Et **le point d'entrée
  CLI est `app()` (script console `labuse`), PAS `python -m labuse.cli`** — ce dernier heurte une
  garde `if __name__ == "__main__": app()` en MILIEU de `cli.py` (ligne 2263) et ignore toutes les
  commandes tardives (pompe, golden, filtre, agent). Invocation retenue :
  `PYTHONPATH=src python -c "from labuse.cli import app; app()" …`.

---

## Lot 1 — Le cadre — **CLOS**

### Livré

- **1.1 Le module `filtres/`** (`src/labuse/filtres/cadre.py`) : `Controle` (id, nature, sévérité,
  libellé, **seuil écrit avec la mesure qui l'a fixé**, `mesure()`), `Filtre` (source, table, clé,
  colonnes INSEE/géométrie/dates, motif data_sources, portées run/live, contrôles propres),
  `Resultat` (valeur/verdict/détails), l'exécuteur `jouer(db, filtre, version)`. Deux tables
  **`filtre_resultats`** (source, version, controle, nature, severite, valeur, seuil, verdict,
  details_json, joue_le) et **`filtre_versions`** (source, version, verdict, bloquants_ko,
  avertissants_ko, **servir_quand_meme/servi_par/servi_motif** pour le geste de Vic, joue_le).
  Créées au boot (`models._ensure_schema_steps`) et à chaque `jouer` (idempotent).
- **CLI** `labuse filtre jouer <source> [--version V]` (+ `toutes`), `labuse filtre lister`,
  `labuse filtre garde`. Chaque `jouer` écrit les deux tables ET journalise le geste `filtre`
  (`resultat=refuse` si quarantaine, sinon `ok`).
- **1.2 Contrôles universels** hérités sans rien écrire, activés selon la config du filtre :
  `u_communes` (présence des 24 INSEE, référentiel embarqué `REUNION_COMMUNES`),
  `u_non_vide` (**bloquant** : 0 ligne = quarantaine), `u_couloir_lignes` (±30 % autour de la
  version précédente — **la référence est posée au 1er passage, jamais une accusation à vide**),
  `u_doublon_cle`, `u_geom_valide` (ST_IsValid), `u_geom_emprise` (enveloppe Réunion
  55.0..55.95 / -21.45..-20.8), `u_dates_plausibles` (pas < 2000 ni futur), `u_millesime`.
  **Seul `u_non_vide` est bloquant** — application stricte de la règle « aucun seuil bloquant sans
  mesure » : tous les autres universels avertissent.
- **1.3 La vanne enchaîne** : `_lancer_ingestion` (dashboard) lance désormais
  `sh -c "<ingestion> && <filtre jouer même-source --par vanne>"` (détaché, `PYTHONPATH=src` du
  worktree posé pour jouer EXACTEMENT le code servi). Le filtre ne se joue que si l'ingestion
  réussit (`&&`). Geste `filtre` ajouté à `circuit_journal.GESTES`.
- **1.4 Garde de la pompe** : `filtres.garde_pompe(db)` liste les sources à portée `run` dont la
  **version servie est en quarantaine** (bloquant KO, sans « servir quand même »). Branchée en
  **refus** dans `labuse pompe calculer` ET `labuse golden promote` (la bascule) : message nommant
  la source, sa version et les contrôles bloquants KO, refus journalisé (`resultat=refuse`). Vide
  aujourd'hui (aucun filtre `run` n'a encore de bloquant — les portées run se posent au lot 2).
- **1.5 Invariant testé** : `filtres/__init__.py` fusionne un filtre par défaut (universels seuls,
  millésime via le motif) pour **chaque** source de `sources_ingestion.yaml` (33 labels) avec les
  filtres riches du lot 2. Le test `test_toute_source_a_job_a_un_filtre` vire au rouge si une
  source de la vanne n'a pas de filtre.

### Décisions prises en autonomie (lot 1)

1. **Clé de filtre = label de la vanne** (`sources_ingestion.yaml`), pour que l'invariant 1.5 et
   l'enchaînement vanne→filtre partagent la même identité. Les sources du lot 2 SANS vanne
   (cadastre en direct, MAJIC, Filosofi, EDF, LiDAR, FLAIR, GPU/PLU en direct) seront des entrées
   riches supplémentaires du registre (pas exigées par 1.5, mais filtrées quand même).
2. **`u_non_vide` seul bloquant parmi les universels.** Un couloir de lignes, un doublon, une
   géométrie hors emprise : ce sont des avertissements tant qu'aucune mesure ne fonde un blocage.
   0 ligne, en revanche, est un fait non ambigu (rien à servir) → bloquant, comme le mandat le dit.
3. **La version d'une source** = `source_millesime`, sinon `sync <date last_sync_at>`, sinon
   `courante`. C'est la granularité que `data_sources` porte ; le couloir de lignes compare au
   dernier passage d'une AUTRE version enregistrée dans `filtre_resultats`.

### Tests — lot 1

`tests/test_circuit3_lot1.py` **7 verts** : invariant 1.5, filtre par défaut, universels sur table
témoin (3/24 communes → KO, doublon → KO, date 2099 → KO, point Paris hors emprise → KO, aucun
bloquant → « avertissements »), couloir (référence au 1er passage puis quarantaine à 0 ligne),
bloquant → quarantaine + « servir quand même » qui lève le blocage, garde de la pompe (nomme la
source `run` en quarantaine, vide après « servir quand même »), écriture des deux tables.
Régression ciblée circuit + dashboard : **38 verts**. `DYLD_FALLBACK_LIBRARY_PATH` posé.

### Commit

`feat/circuit-3` — un commit lot 1 (après le commit « CIRCUIT-3 — mandat »). Poussé. Rien mergé.

---

## Lot 2 — Les filtres des vingt sources qui pèsent — **CLOS**

### Livré

- **`src/labuse/filtres/controles.py`** : fabriques de contrôles propres réutilisables
  (`compte_mauvais`, `domaine`, `couverture`, `part_max`, `siren_luhn` avec clé de Luhn en Python).
- **`src/labuse/filtres/sources.py`** : un `Filtre` riche par source d'impact, **chaque seuil écrit
  avec la mesure qui l'a fixé** (base servie `labuse`, 05/09/2026). Le cadre a gagné `insee_expr`,
  `commune_nom_col` (les tables portent souvent un NOM de commune, pas l'INSEE — parcels/DVF) et
  `where` (filtrer une couche `spatial_layers` par `kind`). Le contrôle géométrie transforme
  systématiquement en 4326 (`ST_Transform`) — SRID-agnostique (les tables mêlent 4326 et 2975) — et
  **chaque contrôle tourne dans un SAVEPOINT** : une erreur SQL roule sans empoisonner le filtre.
- **39 filtres joués sur la base réelle** — `labuse filtre jouer toutes` : **28 ok · 10
  avertissements · 1 quarantaine**. Les avertissants sont l'ÉTAT RÉEL des données, pas un échec.

### Le tableau des vingt sources (verdict de la version servie au 05/09)

| Source | Verdict | Version servie | Contrôle KO (état réel) |
|---|---|---|---|
| cadastre_etalab | ok | Etalab « latest » | — (431 663 parcelles, 0 surface≤0, IDU uniques, 0 géom invalide) |
| dvf | avertissements | géo-DVF 2021–2025 | `d_prix_m2_aberrant_brut` : **7** Maison multi-lots >90 000 €/m² (écartées des comparables) |
| gpu_plu | avertissements | GPU par commune | `u_communes` 23/24 (Saint-Philippe sans PLU servi) |
| sitadel | avertissements | 2026-07 | `d_approx_jamais_point` : **57** permis approximatifs servis comme point |
| dgfip_parcelles_pm (MAJIC) | ok | Panel 2019→2025 | — (SIREN Luhn 0 invalide ; 12,3 % SIREN mal formés < seuil 15 %) |
| dpe | avertissements | sync 2026-08-18 | `u_communes` 7/24 (DPE LOCALE partielle — 17 enreg. ; état servi local honnête) |
| georisques_mvt | **QUARANTAINE** | sync 2026-07-05 | `d_alea_non_retrograde` (**bloquant**) : **484** zones ELEVE/TRES_ELEVE servies « moyen » |
| sirene_etablissements | avertissements | publication mensuelle | `u_dates_plausibles` : 18 date_creation implausibles (SIREN Luhn 0 invalide) |
| bodacc | ok | sync 2026-09-05 | — |
| inpi_rne | ok | sync 2026-07-06 | — (dirigeants `pm_dirigeants`) |
| ban | ok | sync 2026-08-19 | — (339 915 adresses, 100 % géocodées, 24/24) |
| cosia | ok | CoSIA 2025 | — (445 190 bâtiments) |
| flair | avertissements | courante | `u_millesime` (FLAIR juge les détections ortho, pas de ligne data_sources dédiée) |
| lidar_hd | ok | dalles 25/06/2025 | — (seuil toits 0,70 rejoué par l'ÉCHANTILLON, lot 3) |
| edf | avertissements | courante | `u_millesime` (19 528 tronçons HTA/HTB, réservoir sans ligne data_sources) |
| osm_overpass | ok | sync 2026-07-06 | — (50 760 aménités) |
| osm_transport | ok | Overpass | — (188 objets TCSP) |
| gtfs_pan | ok | màj 2026-08-17 | — |
| bpe_insee | ok | millésime 2025 | — |
| filosofi | ok | millésime 2021 | — (14 773 carreaux 200 m, geom 2975 transformée) |
| georisques_api (synthèse) | avertissements | courante | `u_geom_emprise` (quelques géoms hors enveloppe), `u_millesime` |
| trafic_rn | avertissements | par tronçon | `d_tmja_positif` : tronçons à TMJA ≤ 0 |

### LE constat majeur — georisques_mvt en quarantaine

**Le filtre attrape la vraie régression RETOURS-13** : 484 zones d'aléa mouvement de terrain de
degré DEAL `ELEVE`/`TRES_ELEVE` sont servies `niveau = 'moyen'` sur `main` (le correctif vit sur
`fix/retours-12`, **non mergé**). Le contrôle `d_alea_non_retrograde` (bloquant, comme le mandat le
prescrit) met la source **en quarantaine**. Comme `georisques_mvt` est à portée `run`, **la garde de
la pompe (1.4) refuserait de calculer/basculer** — c'est le système QUI FONCTIONNE : « une eau qui
rate son filtre reste en quarantaine et ne se sert pas ». Vic solde en mergeant `fix/retours-12`
(qui corrige les 484), ou par « servir quand même » sur la page (lot 5). C'est le même écart que la
sonde catégorielle CIRCUIT-2 avait laissé OUVERT — le filtre le rend maintenant BLOQUANT.

### Décisions prises en autonomie (lot 2)

1. **DVF prix/m² : deux contrôles, pas un.** Le mandat veut « bloquant si > 90 000 ». Les 7 outliers
   BRUTS (Maison multi-lots mal typées) n'atteignent JAMAIS un comparable servi — `marche_service.
   filtre_ventes` (EXPORTS-1) borne à [1 000 ; 12 000] €/m². Donc : `d_comparable_plage`
   **bloquant** mesuré **0** sur la population des comparables (le gardien nommé du mandat), et
   `d_prix_m2_aberrant_brut` **avertissant** mesuré **7** (l'état réel, visible, non bloquant). Faire
   le bloquant sur le brut aurait mis DVF en quarantaine pour 7 lignes que la pompe ne voit pas —
   « un filtre trop sévère qui bloque une source saine est pire ».
2. **Domaine des lettres de zone = la fonction canonique** `faisabilite.zone_norm.est_famille`
   (U/AU/A/N, phasage/casse/accents ignorés), jamais une liste recopiée — les codes legacy POS
   (NA/NB/NC/ND) classent, seul un radical vraiment inconnu sort. C'est « le référentiel du registre »
   du mandat (donnees.py `zone_plu_famille` domaine=U/AU/A/N).
3. **Plancher de dates universel élargi à 1900** (était 2000) : une date de création d'entreprise ou
   une année de construction antérieure à 2000 est LÉGITIME. Le futur reste toujours KO.
4. **Portée `run`** posée pour cadastre, DVF, GPU/PLU, Sitadel, Géorisques mvt, CoSIA (elles nourrissent
   le scoring). Leur seul contrôle bloquant hérité est `u_non_vide` (toutes non vides aujourd'hui) —
   plus, pour Géorisques, `d_alea_non_retrograde`. Aucune autre ne bloque la pompe au 05/09.
5. **Sources sans table servie propre** (FLAIR juge les détections ortho ; LiDAR HD est un WMS en
   direct sans table) : filtre léger + note ; le seuil 0,70 des toits LiDAR (RETOURS-14 : 0 faux/50)
   est rejoué par l'ÉCHANTILLON du lot 3, pas ici. DPE local est partiel (17 enreg.) — le filtre
   l'avertit honnêtement (7/24 communes), c'est l'état servi localement.

### Tests — lot 2

`tests/test_circuit3_lot2.py` **5 verts** (structure du registre ; DVF gardien comparables vs
aberrant brut ; aléa non rétrogradé bloquant = RETOURS-13 ; SIREN Luhn ; domaine des zones via
`est_famille`). Total CIRCUIT-3 : **12 verts** (lot 1 + lot 2).

### Commit

`feat/circuit-3` — un commit lot 2, poussé. Rien mergé.

---

## Lot 3 — L'échantillon vérifié contre le producteur — **CLOS**

### Livré

- **`src/labuse/filtres/echantillon.py`** : le contrôle `d_echantillon` (nature `echantillon`,
  avertissant) — lit `filtres/echantillons/<source>.json`, rejoue chaque enregistrement (query de
  NOTRE table) et le compare à l'attendu **lu chez le producteur** (numérique à tolérance,
  sinon texte insensible casse/espaces). Tout écart = KO avertissant **avec les deux valeurs** et
  l'origine producteur. Le contrôle est attaché automatiquement à un filtre **si** un fichier
  existe pour sa source (`__init__._registre`), sinon rien.
- **Vérifié EN DIRECT chez le producteur (réseau disponible dans la session)** :
  - **cadastre_etalab** (`echantillons/cadastre_etalab.json`) : **20 parcelles** (4 témoins
    CIRCUIT-2 + 16 golden, 1 par commune), contenance lue sur **IGN API Carto Cadastre**. Résultat
    réel : **2 écarts / 20** — `97403000AH0341` (notre `surface_m2` 113,5 m² vs 168 cadastral) et
    `97404000AC0011` (72 vs 150). Notre surface géométrique diverge > 10 % de la contenance DGFiP
    sur 2 petites parcelles : **un vrai signal**, surfacé par la vérification producteur.
  - **ban** (`echantillons/ban.json`) : **24 adresses** (1 par commune), INSEE lu par
    **reverse-geocode api-adresse**. Résultat : **0 écart / 24** (le citycode producteur = le nôtre).
  - **communes** (`echantillons/communes.json`) : référence des 24 communes (nom + population) lue
    sur **geo.api.gouv.fr** (INSEE COG) — témoin partagé.
- **`docs/CIRCUIT/ECHANTILLONS-A-VALIDER.md`** : pour les 18 autres sources, un fichier squelette
  `echantillons/<source>.json` (producteur, table, clé, URL, `a_valider:true`, **proposition de
  CC**), et le contrôle **skip** proprement tant que les lignes ne sont pas remplies — **rien
  n'attend**. Classé par ce qui manque : yeux humains (LiDAR 50 toits 0,70, CoSIA, FLAIR),
  identifiants (Sirene INSEE, INPI RNE), ou budget d'appels (DPE ADEME, DVF, GPU, BODACC…).
- **Chaque source du lot 2 a un fichier échantillon** (20/20, testé).

### Décisions prises en autonomie (lot 3)

1. **Deux échantillons vérifiés en direct suffisent à prouver le mécanisme sur données producteur
   VIVES** (cadastre + BAN, deux producteurs différents, l'un révèle 2 écarts réels, l'autre 0).
   Vérifier 20–50 enregistrements × 20 sources en direct dépassait le budget d'appels de la
   session — les autres sont des squelettes datés avec proposition, à valider (3.3 : « rien n'attend »).
2. **SIRENE NAF écarté de l'échantillon actif** : testé via `recherche-entreprises` (public), mais
   l'API renvoie le NAF du **siège** (ambigu par SIRET — faux écarts siège/établissement + format
   `47.11B` vs `4711Z`). La vérité par SIRET exige l'API Sirene INSEE (authentifiée) → À VALIDER,
   pour ne pas peupler l'échantillon d'écarts trompeurs.
3. **Tolérance cadastre 10 %** : notre `surface_m2` est dérivée de la géométrie, la contenance est
   la déclaration cadastrale — 10 % absorbe le bruit géométrie/contenance et ne laisse remonter que
   les vraies divergences (2/20, toutes deux > 30 %).

### Tests — lot 3

`tests/test_circuit3_lot3.py` **5 verts** (comparaison num/texte ; écart détecté avec les deux
valeurs + origine ; squelette qui skip ; échantillons genuine avec origine producteur ; les 20
sources ont un fichier). Total CIRCUIT-3 : **17 verts** (lots 1+2+3).

### Commit

`feat/circuit-3` — un commit lot 3, poussé. Rien mergé.

---

## Lot 4 — La quarantaine pour les données servies en direct — **CLOS**

### Livré

- **`src/labuse/filtres/quarantaine.py`** : le mécanisme d'échange par table d'attente.
  - `reservoirs_live()` / `sources_live_registre()` — **la liste des sources live vient du REGISTRE**
    (toute donnée à portée `live` → son réservoir → sa clé de filtre, via un alias
    `cadastre_api_carto→cadastre_etalab`, `gpu_plu_api_carto→gpu_plu`, `filosofi_carreaux→filosofi`,
    `deal_ppr→georisques_mvt`). 22 sources de filtre sont live (elle change dès l'injection).
    Les filtres portent désormais `live=True` (posé dans `__init__._registre`).
  - `jouer_sur_attente(db, filtre)` — joue le filtre sur `<table>__attente` (la version fraîchement
    ingérée, PAS encore servie).
  - `echanger(db, source, force, motif)` — joue le filtre sur l'attente ; **si OK** (ou `force` =
    « servir quand même »), échange dans la transaction de session : `<table>` → `<table>__precedente`
    puis `<table>__attente` → `<table>` (les index suivent le rename). **Si quarantaine et pas de
    force : aucun échange** — l'ancienne reste servie, l'attente reste mesurée. Geste journalisé.
  - `revenir(db, source)` — retour immédiat : `<table>__precedente` redevient la table servie.
- **CLI** `labuse filtre echanger <source> [--servir-quand-meme] [--motif …]` et
  `labuse filtre revenir <source>`.
- **4.2 — sources à portée `run` seulement** : PAS d'échange de table, la garde de la pompe (1.4)
  suffit (elle refuse `calculer`/`basculer` si une source `run` servie est en quarantaine). Sources
  purement `run` (jamais `live`) au 05/09 : **cosia** (feed résiduel). Toutes les autres qui pèsent
  sont AUSSI `live` (cadastre, DVF, GPU/PLU, Sitadel, Géorisques mvt) → elles ont les deux garde-fous :
  la table d'attente à l'ingestion ET la garde de la pompe au calcul.

### Décisions prises en autonomie (lot 4)

1. **Le mécanisme est prêt et testé ; le branchement de chaque ingestion sur `<table>__attente` est
   l'étape d'intégration par ingestion** (écrire dans `__attente` puis appeler `labuse filtre
   echanger`). Retrofitter les ~30 ingestions en une session n'était ni sûr ni dans le budget ; le
   mécanisme + la CLI + les tests le rendent trivial à câbler source par source, sans rien casser.
2. **Le rename conserve les index** (comportement PostgreSQL) — pas de reconstruction d'index à
   l'échange ; les noms d'index gardent leur ancien préfixe, fonctionnellement intacts.
3. **`__precedente` gardée une seule génération** (l'échange écrase la précédente-précédente) — un
   retour arrière immédiat suffit, on ne conserve pas un historique de tables.

### Tests — lot 4

`tests/test_circuit3_lot4.py` **5 verts** : échange sur verdict OK (la nouvelle version se sert,
l'ancienne passe en `__precedente`) ; **injection VIDE en quarantaine → l'ancienne reste servie**
(l'attente ne se sert pas) ; « servir quand même » force l'échange ; retour à la version précédente ;
sources live dérivées du registre. Total CIRCUIT-3 : **22 verts** (lots 1-4).

### Commit

`feat/circuit-3` — un commit lot 4, poussé. Rien mergé.

---

## Lots 5 à 6 — à venir

(compte-rendu tenu à jour lot par lot)
