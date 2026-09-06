# RETOURS-21 — COMPTE-RENDU

Branche `fix/retours-21`, partie de `origin/main` à jour (`cabaa5b7`, qui contient déjà le merge
de `fix/retours-12` = RETOURS-13→19). Un commit par lot. **Rien n'est mergé, rien n'est basculé.**

Étape 0 : l'arbre portait un fichier non suivi `frontend/retours16_shots.mjs` (script de captures
RETOURS-16, sans valeur) — supprimé sur consigne. `git fetch` puis branche depuis `origin/main`.

---

## Lot A — les 484 zones d'aléa servies au mauvais niveau

### Ce qu'on a trouvé avant de coder

Le mapping de classes est **déjà corrigé dans le code** (RETOURS-13 R6, présent sur main) :
`src/labuse/ingestion/layers_ingest.py::_ALEA_NIVEAU` mappe déjà `ELEVE`/`TRES_ELEVE → ("fort", …)`.
Le commentaire R6 (l. 357-361) le disait : « la correction ELEVE/TRES_ELEVE→fort ne s'applique
qu'à la prochaine ré-ingestion + run ». Autrement dit : **la donnée servie était périmée**, pas le
code. Mesuré en base (`spatial_layers`, kind `georisque_alea`, subtype `mouvement_terrain`) :

| degré      | niveau servi (avant) | classe (déjà bonne) | zones |
|------------|----------------------|---------------------|-------|
| ELEVE      | **moyen**            | eleve               | 360   |
| TRES_ELEVE | **moyen**            | tres_eleve          | 124   |
| MOYEN      | moyen                | moyen               | 299   |
| FAIBLE     | faible               | faible              | 96    |
| FAIBLE_A_MODERE | faible          | faible              | 31    |
| MOYEN_B2U / MODERE / MOYEN_SECURISABLE | moyen | moyen        | 7     |

La `classe` d'AFFICHAGE était déjà juste (fix R6) et l'endpoint la lit directement
(`api/app.py`, `"classe": r["classe"]`, aucune retraduction) — rien à changer côté affichage.
Seul le `niveau` de CASCADE (celui qui pilote le score) restait à « moyen » sur les **484** zones
les plus graves, d'où la quarantaine CIRCUIT-3.

### Impact mesuré (avant recalcul)

La couche de scoring `cascade/layers/phase1.py::RisquesLayer` émet, pour chaque zone d'aléa
intersectée (aucun seuil de couverture sur les aléas — `if coverage <= 0: continue`), un
`soft_flag` de sévérité tirée du `niveau`. Un flag **fort** vs **moyen** :
- coûte **−5 pts d'opportunité de plus** (moyen = −10, fort = −15, `opportunity_weights.yaml`) ;
- pose `has_fort_flag=True`, ce qui **bloque le statut « opportunité »** (forçage « à creuser »),
  et abaisse le rang → peut faire tomber une parcelle « chaude »/« brûlante ».

Rayon d'impact (croisement spatial `parcels ↔ 484 zones graves`, EPSG:2975) :

- **73 179 parcelles** intersectent au moins une zone ELEVE/TRES_ELEVE → gagnent un flag fort au
  lieu de moyen.
- **Delta de score d'opportunité** (déterministe = −5 pts × nombre de zones graves intersectées) :
  médiane **−5 pts** (1 zone), moyenne 1,19 zone, **max −145 pts** (une parcelle sur 29 zones).
- **Changement de palier** — seules les parcelles aujourd'hui dans un palier « chaud » peuvent
  descendre (une « écartée » / « à creuser » / « déclassée » est déjà au plancher). Parmi les
  73 179 : **67 chaudes + 1 brûlante** ; dont **13 chaudes sans flag fort préexistant**
  (les seules qui gagnent un `has_fort_flag` NEUF → bascule quasi certaine « chaude → à creuser »).
  Les 55 747 écartées et 10 469 à-creuser intersectantes ne changent pas de palier.

Le **nombre exact** de changements de palier se lit dans le run candidat (les tiers sont un
classement global, non calculable sans re-scorer) — voir plus bas.

### Correction à la source

`layers_ingest.py::reclassifier_alea_niveau()` (+ CLI `labuse alea-reclassifier`) : recalcule
`niveau`/`classe`/`residuel` de chaque zone `georisque_alea` **à partir de son `degre` stocké**,
avec les **mêmes fonctions de mapping** que l'ingestion (`_normalise_alea`/`_classe_alea`, source
de vérité). Résultat identique à une ré-ingestion, mais déterministe, hors réseau, idempotent, et
qui ne touche QUE les zones dont le niveau diffère du mapping (on nomme ce qui bouge). Exécuté :

```
ELEVE: moyen→fort (classe eleve→eleve) · 360 zones
TRES_ELEVE: moyen→fort (classe tres_eleve→tres_eleve) · 124 zones
✓ 484 zones réalignées.
```

Ce n'est PAS un correctif d'affichage : la donnée servie (`spatial_layers.attrs.niveau`) est
désormais juste, l'affichage la lit telle quelle. Le run servi (`q_v11_m137`) est un instantané
figé dans `parcel_p_score_v2` — il n'est PAS modifié : la correction ne se propage au score qu'à
la bascule d'un nouveau run (geste de Vic).

### Quarantaine levée

Le filtre CIRCUIT-3 rejoué sur la donnée corrigée passe au vert — le contrôle bloquant
`d_alea_non_retrograde` (« aléa fort jamais rétrogradé en moyen ») compte 0 :

```
✓ georisques_mvt [sync 2026-07-05] : ok — 0 bloquant(s) KO, 0 avertissant(s) KO (9 contrôles)
✓ garde pompe : aucune source `run` en quarantaine.
```

La quarantaine s'est levée **parce que le filtre passe**, pas par un `servir-quand-même`. Le
verdict OK est persisté dans `filtre_versions`.

### Run candidat (non servi)

`labuse flux-run --label q_v11_r21_alea` (cascade 24 communes + score-v2, sur la donnée aléa
corrigée) : débit mesuré ~33 parcelles/s → **~3,6 h** sur 431 663 parcelles ; résumable
(`--resume`), écrit `dryrun_*` + `parcel_p_score_v2` sous le label candidat. **NON servi** — la
bascule reste manuelle (`labuse golden promote q_v11_r21_alea`), après note de version. La garde
pompe étant verte, la bascule n'est plus bloquée.

> **État à la remise : run À LANCER FRAIS dans une fenêtre dédiée — PAS `--resume`.** Le run a
> été tenté 4× dans la fenêtre de session, jamais mené au bout, pour des causes distinctes : (1)
> double lancement de ma part (2 process concurrents → collision `uq_dryrun_eval`) ; (2)+(3)
> `AdminShutdown` d'un backend quand le heal de schéma de l'app de captures a terminé le backend
> que le run tenait (verrou sur `parcels`) ; (4) `--resume` → `UniqueViolation uq_dryrun_eval` :
> l'état `dryrun_*` partiel laissé par les tentatives interrompues rend la REPRISE incohérente
> (elle ré-insère une parcelle déjà écrite). **Leçon : le `--resume` de `flux-run` n'est fiable
> que sur un état partiel PROPRE ; après des interruptions multiples, il faut repartir de zéro.**
> J'ai donc **purgé complètement** le label (`dryrun_parcel_evaluations` + `dryrun_cascade_results`
> pour `q_v11_r21_alea` = 0 ligne) : l'état est net.
>
> **À faire (Vic ou fenêtre dédiée), DB au calme, aucun autre client :**
> `labuse flux-run --label q_v11_r21_alea` (frais, ~3,6 h, `caffeinate -i` pour empêcher la veille).
> **NE PAS** relancer d'app/monitoring pendant : le heal de schéma d'un `labuse api` concurrent
> termine le backend du run (cause de (2)/(3)). À la fin : `labuse golden candidat` puis, si la note
> de version convient, `labuse golden promote q_v11_r21_alea` (bascule = geste de Vic). Le **diff de
> tiers candidat vs `q_v11_m137`** (compte exact des changements de palier) se lira alors ; l'impact
> attendu est petit — cf. les ~13 chaudes ci-dessus.
>
> **Ce qui NE dépend PAS de ce run et est FAIT :** la donnée aléa corrigée à la source (484 zones),
> la quarantaine `georisques_mvt` levée, et l'impact mesuré déterministiquement (73 179 parcelles,
> delta médian −5 pts). Le run ne sert qu'à produire le classement candidat pour la revue de Vic.

### Golden

Le golden ne bouge PAS tant que le run candidat n'est pas servi (il se grave sur le run servi).
À la bascule seulement, `golden promote` régénère le golden sur le nouveau run ; le diff attendu
touche les parcelles chaudes qui descendent (aléa désormais fort) — évolution voulue, pas
régression. **Aucune régénération silencieuse** : le diff sera listé au moment de la bascule.

### Fichiers Lot A
- `src/labuse/ingestion/layers_ingest.py` — `reclassifier_alea_niveau()`.
- `src/labuse/cli.py` — commande `alea-reclassifier`.
- `tests/test_retours21_lotA.py` — réalignement + idempotence.

---

## Lot B — les 2 894 permis sans localisation

### Caractérisation (mesurée avant de coder)

Les **2 894** permis `geom IS NULL` sans repli d'adresse (à distinguer des 580 démis-adresse de
RETOURS-14, qui portent `geoloc='localisation approximative…'`). Motif :

- **Référence : tous bien formés.** 2 894 / 2 894 ont un IDU de 14 caractères, INSEE `974xx`
  valide. **Aucune** référence vide, hors-974, ou de longueur anormale. Aucun IDU n'est dans
  `cadastre_historique` (donc jamais retrouvé dans les millésimes 2017-02→2025-09 de RETOURS-14).
  → le motif « référence illisible » est **quasi nul** ; l'essentiel = parcelle introuvable.
- **Par année du permis** (le millésime disponible commence en 2017-02) :

  | année | permis | | année | permis |
  |-------|-------:|-|-------|-------:|
  | 2013  | 664 | | 2020 | 110 |
  | 2014  | 595 | | 2021 |  72 |
  | 2015  | 514 | | 2022 |  72 |
  | 2016  | 363 | | 2023 |  57 |
  | 2017  |  91 | | 2024 |  55 |
  | 2018  |  65 | | 2025 |  63 |
  | 2019  |  90 | | 2026 |  83 |

  → **2 136 (74 %) sont 2013-2016**, antérieurs au premier cadastre archivé (2017-02) : parcelle
  disparue AVANT. Les 758 de 2017+ référencent une parcelle absente de TOUS les millésimes
  2017→2025 → référence erronée (parcelle inexistante) ou parcelle éphémère entre deux millésimes.

- **Par commune** (top) : 97416 (363), 97422 (280), 97418 (255), 97415 (239), 97411 (194)…

### Pistes de millésime < 2017-02 (ouvertes une par une)

1. **PCI vecteur DGFiP** (`cadastre.data.gouv.fr/data/dgfip-pci-vecteur/`) : millésime le plus
   ancien = **2017-02-13**. Aucune édition antérieure. → **absence confirmée après avoir regardé.**
2. **BD PARCELLAIRE vecteur, version gelée 2018** (WFS `parcelle`) : postérieure à 2017-02, donc
   inutile (une parcelle disparue avant 2017 en est déjà absente). → écartée après avoir regardé.
3. **BD PARCELLAIRE couches image 2008-2013 / 2013-2018** (WMTS) : **raster**, sans géométrie
   vectorielle ni IDU exploitable pour rattacher une parcelle. → écartée après avoir regardé.
4. **BD PARCELLAIRE VECTEUR, édition 974 du 27/06/2008** (archive opendatarchives, SHP en
   RGR92 UTM 40S = EPSG:2975) : **la seule source vecteur antérieure à 2017-02 trouvée.** 334 873
   parcelles ; l'IDU se reconstitue depuis `CODE_DEP+CODE_COM+COM_ABS+SECTION+NUMERO`.
   **MESURÉ : 1 041 des 2 391 IDU orphelins distincts y figurent** (majorité des permis 2013-2016 :
   433/664, 348/595, 295/514, 176/363 ; quasi rien après 2021, ce qui confirme les refs erronées).

### Récupération sûre (BD PARCELLAIRE 2008)

`cadastre_historique.py::_pass_bdparcellaire_2008()` (câblée dans `run()`, après le PCI EDIGEO) :
télécharge l'archive, reconstitue l'IDU, insère la géométrie 2008 (reprojetée 4326) des parcelles
CIBLES dans `cadastre_historique` (millésime `2008-06-27`), puis `rattacher_par_geometrie` pose le
permis sur `ST_PointOnSurface` de la parcelle d'origine et le rattache aux parcelles actuelles
(≥10 % de couverture) — **exactement la méthode RETOURS-14** (IDU exact dans un cadastre d'époque
→ récupération sûre ; jamais deviné). Exécuté :

```
BD PARCELLAIRE 2008 : 1262 parcelles d'origine retrouvées (reliquat pré-2017)
rattachement géométrique : 1587 permis posés sur leur parcelle d'origine · 1887 encore sans geom
```

**Bilan permis** (avant → après) :

| état | avant | après |
|------|------:|------:|
| localisés (geom présente) | 47 071 | **48 658** (+1 587) |
| sans geom, « approximative (adresse) » | 580 | 309 |
| sans geom, muets (geoloc NULL) | 2 894 | **0** |
| sans geom, « sans localisation » (mention neuve) | 0 | 1 578 |

1 587 permis récupérés (dont ~271 qui n'avaient qu'un repli d'adresse et ont désormais une
géométrie exacte). Le reliquat vraiment non localisable = **1 578** (parcelle absente des cadastres
2008 ET 2017→2025 : créée après 2008 puis disparue avant 2017, ou référence erronée).

### Le reliquat n'est jamais muet

`cadastre_historique.py::marquer_reliquat_sans_localisation()` (câblée dans `run()`) : tout permis
resté `geom IS NULL` SANS `geoloc` reçoit une mention honnête (« sans localisation — parcelle
d'origine absente des cadastres disponibles (2008 et 2017→2025), non affichée en point »).
La liste (`api/modules.py`) affiche déjà ces permis sans jamais de point (`carte` = geom présente
seule, règle S5) et le pied de liste dit le reliquat (`sans_localisation`). Exécuté : 1 578 marqués
→ **0 permis muet restant.**

### Fichiers Lot B
- `src/labuse/ingestion/cadastre_historique.py` — `_pass_bdparcellaire_2008()`,
  `marquer_reliquat_sans_localisation()`, câblage `run()`.
- `tests/test_retours21_lotB.py` — reliquat jamais muet.
- Dépendance : `py7zr` (lecture archive .7z IGN) ; `ogr2ogr` (reprojection, déjà utilisé).

---

## Lot C — accordéons de la fiche parcelle

Le mandat `MANDAT-RETOURS-20.md` a été poussé sur main (`d505ac2d`) puis récupéré dans la branche.
Il lève les deux ambiguïtés : Z3 = « ce qui disparaît » (boîtes imbriquées, >4 tailles de texte,
sources en fin de phrase, valeurs en milieu de ligne, chips de tailles différentes) ; Z4 (icônes)
= le traitement du **survol** (la maquette montrait le repos, pas de divergence).

### Z4 — LIVRÉ (les deux reports de RETOURS-19)

- **Z4a — scrollbar de la Veille** : la règle Y4 « pouce vert au survol » est **globale**
  (`styles/index.css` l. 329-334 : `::-webkit-scrollbar-thumb:hover { background: var(--mint) }`
  + `* { scrollbar-color }`), **sans aucune surcharge** ailleurs (vérifié : `grep` de
  `scrollbar-*` ne trouve que ce bloc). Elle s'applique donc déjà à tout conteneur défilant, Veille
  compris — aucun panneau oublié. Rien à changer.
- **Z4b — icônes des accordéons de la fiche** : au survol d'une carte de section, la tuile d'icône
  gardait un **fond sombre** (`--ink`) + glyphe vert (l'ancien RETOURS-11 T2) → « carré sombre sur
  la barre verte » (constat Vic). Corrigé pour suivre EXACTEMENT les 4 icônes d'accueil (`.acc-entry`
  Y2) : fond **transparent**, contour et glyphe en **encre sombre**. Mesuré avant→après sur la tuile
  survolée : `bg rgb(7,16,9)` → `transparent` · `color rgb(74,222,128)` → `rgb(7,16,9)`. Une seule
  règle CSS (`styles/index.css` l. 464), qui devient le traitement d'en-tête de Z1 → vaut pour les
  neuf accordéons. Captures `captures/icone-survol-{avant,apres}.png`.

### Z1 / Z2 / Z3 — PRÉPARÉS, NON LIVRÉS (budget de session)

Les composants partagés existent déjà (`fiche/primitives.tsx` : `RefDrawer` en-tête, `GroupLabel`
kicker, `Line`+`SourceRef` ligne de fait, `StepProv` badges, `PorteOutil` action, `pill-*`) — Z1 est
donc un **alignement** sur la grammaire de la maquette (tailles 14/13/12,5/11,5/10,5, source SOUS la
ligne avec badge, filets), pas une création. Z2 vise `Fiche.tsx::ReglementPluBlock` + le tiroir
`regles` et `fiche/reseaux.tsx`. Z3 retire les boîtes imbriquées (carte « RÈGLEMENT PLU », boîte de
fraîcheur, bloc gestionnaires) que montre le « avant ».

Ce refactor des deux sections denses, fidèle au pixel et sans casser la logique servie, est un
chantier à part entière (RETOURS-20 en était le mandat plein). Après l'investissement des lots A/B
et la remise en état de l'infra de run (voir Lot A), je n'ai pas voulu livrer un refactor bâclé ni
un commit atomique à moitié fait sur une UI aussi visible. **Prep faite** : reconnaissance complète
(composants + lignes), maquette rendue (`captures/` de référence), et **captures « avant » des deux
sections** prises sur une parcelle réelle (`captures/reglement-avant.png`, `reseaux-avant.png`,
parcelle 97415000AH0674). Il reste à écrire l'alignement CSS + le passage des deux sections, puis
les captures « après ».

### Fichiers Lot C (Z4)
- `frontend/src/styles/index.css` — survol icône d'accordéon (l. 464).
- `docs/audit-2026-09/RETOURS-20/MANDAT-RETOURS-20.md` — le mandat récupéré.
- Captures : `icone-survol-{avant,apres}.png` (Z4b) ; `reglement-avant.png` / `reseaux-avant.png`
  (base Z2, « après » à venir).

