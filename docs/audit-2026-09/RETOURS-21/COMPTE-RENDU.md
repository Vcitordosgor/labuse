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

> **État à la remise : run à compléter (~15 % fait, dryrun conservé pour `--resume`).** Deux
> tentatives interrompues dans la fenêtre de session : (1) double lancement de ma part (deux
> process concurrents → collision `uq_dryrun_eval`, nettoyé) ; (2) backend Postgres terminé
> côté serveur (`AdminShutdown`) à ~63 816 parcelles, cause externe non identifiée (Postgres lui
> n'a PAS redémarré — la base est saine). Un run de 3 h ne tient pas de façon fiable dans cette
> session. **À reprendre dans une fenêtre dédiée** : `labuse flux-run --label q_v11_r21_alea
> --resume` (repart des 63 816 déjà évaluées). Le **diff de tiers candidat vs `q_v11_m137`**
> (compte exact des changements de palier) se lira à la fin du run ; l'impact attendu est petit —
> cf. les ~13 chaudes ci-dessus. La correction de la donnée et la levée de quarantaine, elles,
> sont FAITES et indépendantes de ce run.

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

**Bloqué : `MANDAT-RETOURS-20.md` absent du dépôt.** Vérifié (06/09, après `git fetch`) :
`git ls-tree origin/main docs/audit-2026-09/RETOURS-20/` ne rend QUE
`maquette-fiche-parcelle-accordeons.html` ; `git log --all -- '**/MANDAT-RETOURS-20*'` est vide —
le blob n'existe dans AUCUNE ref. Le commit `dddbfb96` (« docs: mandat RETOURS-20 + maquette »)
n'a committé que la maquette (530 l.), jamais le mandat. Le fichier est probablement resté en
local non-committé, ou sur une autre machine.

Ce qui est reconstructible sans le mandat :
- **Z1 — les six composants partagés** : entièrement spécifiés par le panneau `aside` de la
  maquette (règles 01→06 : En-tête · Kicker · Ligne de fait · Badges · Vigilance/rappel · Actions),
  plus la règle « — » (ce qui disparaît).
- **Z2 — deux sections** : *Règlement et zonage* (§1) et *Réseaux et accès* (§5), nommées dans
  l'inline RETOURS-21. Structure et espacements fixés par la maquette.

Ce qui N'EST PAS reconstructible (le mandat seul tranche) :
- **Z3** : étape nommée « puis Z3 sur ces deux-là » — aucune description nulle part.
- **Z4** : l'inline dit « icônes d'accordéon en **fond vert / contour et glyphe noirs** », mais la
  maquette peint les icônes en `mint-soft` / `mint` (`.hd .ico`) — divergence non résolue ; et
  l'`ChevronSection.tsx` actuel (contour plein `border-line-2`, glyphe qui s'éclaircit au survol,
  inversion encre sur barre à fond plein) implémente déjà une grammaire dont Z4 semble vouloir
  s'écarter. Sans le mandat, on ne sait pas dans quel sens.

**Décision** : Lot C non entamé (un refactor de la fiche parcelle est un commit atomique — une
fiche à moitié refaite ne se livre pas ; et les captures avant/après exigent l'app lancée). En
attente du contenu du mandat (au minimum Z3 + l'intention exacte de Z4). Lots A et B livrés et
commités indépendamment.

