# PLU-CALIBRAGE-5 — les 81 exceptions entrent dans le calcul

**Branche** `fix/plu-calibrage-5` · worktree `~/Desktop/labuse-calibrage5` · base `origin/main` (`f5cde690`).
**Règle absolue tenue : AUCUN run.** Le moteur est modifié et testé sur des témoins à la volée ; aucune
valeur en base n'a été recalculée. Le résiduel servi aujourd'hui est inchangé — seul le moteur change,
pour le prochain run de Vic.

## Point de départ — ce qui existait déjà (DONNEES-FIX-1 point 4)

Les 81 exceptions `modifie_calcul=true` de `PLU-EXCEPTIONS-1/A_CALIBRER.csv` étaient **déjà classées et
partiellement câblées** par DONNEES-FIX-1 point 4 : un calibrage figé `config/plu_exceptions_effet.json`
(indexé sur la ligne du CSV), consommé par `zonage.appliquer_exceptions_calcul()` (appelée dans
`parcel_faisabilite`), qui applique les majorations conditionnées à la surface et porte les autres en
« règle non modélisée » (`regles_non_modelisees`). PLU-CALIBRAGE-5 **audite ce tri de façon
indépendante, le complète, le teste témoin par témoin, et câble l'affichage manquant** (verbatim +
badge Estimé sur la fiche). Le tri (4/21/9/47) est confirmé après relecture — voir ci-dessous.

## Lot A — tri des 81 (→ `PLU-CALIBRAGE-5/TRI.csv`)

Trois familles du mandat, dérivées des 4 décisions du calibrage :

| Famille (mandat) | Décision calibrage | N | Suite |
|---|---|---:|---|
| **Modélisable** | `applique` | 4 | Lot B — entre au moteur |
| **Déjà couverte** | `deja_couvert` | 21 | vérifiée sur parcelle, rien à faire |
| **Non modélisable** | `non_modelisee` | 47 | Lot C — portée + badge Estimé |
| Non modélisable *(sans effet SDP)* | `hors_sdp` | 9 | stationnement — n'affecte pas la capacité, **pas** de badge |

`TRI.csv` porte pour chacune : exception, commune, zone, règle, `porte`, article/page, famille, décision,
`badge_estime`, justification.

Répartition par `porte` (les 81) : `sous_secteur` 30 · `majoration_conditionnelle` 17 · `voie_specifique`
12 · `bande_limite` 12 · `autre` 5 · `destination` 4 · `hauteur_alternative` 1.

### Pourquoi les 47 ne sont pas modélisées (relecture indépendante — je confirme)
- **`voie_specifique` (12)** — dépend de l'adjacence à une voie *nommée* (RN2, RD3, « rue des Limites »).
  La géométrie voirie existe (`hauteur_mode='prospect'` lit la largeur de voie), mais l'appariement à une
  voie nommée par parcelle n'est pas fiable → non approximé.
- **`bande_limite` (12)** — hauteur plafonnée dans une bande depuis une limite (ou une liste de parcelles).
  Le moteur SDP compte les niveaux sur **une** hauteur d'égout (SDP = emprise × niveaux) ; il n'a pas de
  gabarit 3D en biais depuis la limite. Un plafond appliqué à toute la parcelle serait faux (trop
  pénalisant) ; le modéliser exactement demande un gabarit que le moteur n'a pas → porté, non déduit.
- **`sous_secteur` non déjà couverts (9)** — sous-secteur à valeur distincte **non calibré séparément**
  (ex. Saint-Joseph U6ch = 10/13 m plus bas que U6 = 12/15 m). Non appliqué : il faudrait que la couche
  de zonage résolve ce sous-secteur *et* qu'on le calibre au YAML — c'est le domaine des mandats de
  **calibration** (PLU-CALIBRAGE-4/6/7), à valider par un run, hors de ce mandat « exceptions ».
- **`destination` (4)**, **`autre` (5)**, **`hauteur_alternative` (1)**, **`majoration_conditionnelle`
  non-surfacique (4 : U4 commerce, U1a/U3a PPRI)** — dépendent de la destination du projet, d'un cas
  géométrique conditionnel, ou d'une donnée non câblée au chemin résiduel. Voir « pistes » en fin.

## Lot B — modéliser (→ `PLU-CALIBRAGE-5/IMPACT.csv`)

**Seules 4 clauses sont modélisables sans inventer de valeur : les majorations conditionnées à la
surface** (Bras-Panon, secteurs `Ub` et `1AUb`, art. UB 10.2 p.31) — « pour les projets dont le terrain
d'assiette est ≥ 2 000 m², hauteur portée à 10 m à l'égout et 13 m au faîtage ». Elles entrent par le
même système unique (`appliquer_exceptions_calcul`, effet `majoration_surface`), qui **ne relâche que
vers le haut** (garde de sens : jamais d'abaissement d'une contrainte de zone).

### Témoin à la volée (aucun run) — secteur Ub, terrain 2 500 m² (≥ seuil), emprise insetée 1 500 m²

| | hauteur égout | niveaux | SDP |
|---|---|---|---|
| Sans majoration (terrain < 2 000 m²) | 8 m | R+1 | **1 350 m²** |
| Avec majoration (terrain ≥ 2 000 m²) | 10 m | R+2 | **2 025 m²** |

→ **+675 m² de SDP** sur le témoin (test `test_temoin_majoration_modelisable_augmente_la_sdp`, calcul
`estimate_capacity` en mémoire). Les 4 lignes d'`IMPACT.csv` (égout+faîtage × Ub + 1AUb) sont **une même
majoration par zone** : l'égout pilote les niveaux ; la ligne faîtage est portée par la même clause. Par
parcelle, l'effet est **+675 m² (une seule fois)**, pas +2 700.

**Aucune exception appliquée ne réduit la capacité** : les seules modélisables sont des *majorations*
(effet ↑). Les réductions potentielles vivent toutes dans les non-modélisées (bande depuis limite,
sous-secteur plus bas, pleine terre PPRI) — **portées, jamais déduites**. `IMPACT.csv` = 4 lignes, sens
`augmente`.

## Lot C — dire ce qui n'est pas modélisé (drapeau + badge Estimé)

Une exception non modélisée **ne disparaît pas** :
1. **Backend** — `appliquer_exceptions_calcul` porte désormais le **verbatim** (`texte`, source
   `A_CALIBRER.csv`, ajouté aux 81 entrées du calibrage) dans `regles_non_modelisees`, à côté de
   l'article/page.
2. **Badge Estimé** — la capacité d'une parcelle qui porte une non-modélisée est marquée **Estimé,
   jamais Sourcé**, même en zone calibrée : `capacite_estimee = (not calibree) OR regles_non_modelisees`
   (dans `residuel.py`, écrit au prochain run ; et dans le chemin fiche `app.py`, honnête *tout de suite*
   sans run). **La SDP n'est jamais approximée** — le badge change, jamais le chiffre
   (`test_capacite_estimee_quand_exception_non_modelisee`).
3. **Fiche** — sous la capacité (`constructibilite.tsx`), un bloc « Une exception du règlement n'est pas
   modélisée — à vérifier » avec le **texte verbatim** de l'exception et son article/page.
4. **Dossier & Copilote** — suivent **par le registre** : le pré-dossier lit `capacite_estimee` du
   potentiel servi (CERFA inchangé) ; le payload fiche porte `regles_non_modelisees` (texte + source)
   pour tout consommateur. Aucune logique spécifique dupliquée.

## Non modélisées par commune (47)

| Commune | N | Zones · règles |
|---|---:|---|
| Bras-Panon (97402) | 3 | 1AUb/Ub/Uba · hauteur.egout · voie_specifique (rue des Limites) |
| Petite-Île (97405) | 2 | AUE/UEa · retraits.voie · RN2 |
| La Plaine-des-Palmistes (97406) | 1 | Ua · retraits.limites (implantation conditionnelle) |
| Le Port (97407) | 2 | Uem/Us · retraits.voie · RN1001/RN7 (Loi Barnier) |
| Saint-Denis (97411) | 7 | Ud/Ui emprise+retraits, Udop/Udp hauteur par rue, Up recul falaise (Upr) |
| Saint-Joseph (97412) | 12 | 1AU3/1AU6/U6 sous-secteurs, U3 bande de profondeur, U4 majoration commerce, U1/U5ma |
| Saint-Leu (97413) | 1 | UAt (=UAT) · faîtage +1,50 m côté aval (surélévation) |
| Saint-Louis (97414) | 2 | UZ · hauteur selon schéma « individuels » (destination) |
| Saint-Paul (97415) | 3 | U1a/U3a pleine terre 50 % en aléa fort PPRI, U4b commerce à l'alignement |
| Saint-Pierre (97416) | 9 | Ue/Uemi/Uep/Uf/Uazi/AUazi bandes depuis limite, Uaza sous-secteur |
| Le Tampon (97422) | 5 | Ua bande mitoyenne 18 m, 1AUa/Ua/Uav recul RD3 |

## Estimation des parcelles de l'île concernées (SQL, sans run)

Comptage sur `parcel_zone_plu` (427 419 parcelles), par (commune, zone) — détail dans
`PLU-CALIBRAGE-5/ESTIMATION_PARCELLES.csv` :

| Famille | Parcelles île | Zones |
|---|---:|---:|
| **Portent une exception NON modélisée → badge Estimé** | **~43 113** | 35 |
| Déjà couverte (sous-secteur calibré, servi juste) | ~22 136 | 12 |
| Sans effet SDP (stationnement) | ~4 629 | 8 |

- La **majoration modélisable** (Bras-Panon Ub+1AUb) touche 2 261 parcelles, dont **93 ont ≥ 2 000 m²**
  et verront donc la hauteur relâchée (R+1→R+2) au prochain run.
- **Vic, pour comparer le prochain run au précédent** : attendre ~43 k parcelles basculées `capacite_estimee=true`
  (badge Estimé) sur les 35 zones à non-modélisée, et une **hausse locale de SDP sur ~93 parcelles**
  Bras-Panon ≥ 2 000 m². Le reste du parc est inchangé.
- Notes d'appariement : `97413 UAt` → libellé réel `UAT` (8 parcelles) ; `97411 Up` → le secteur porteur
  est `Upr` (6 parcelles, recul falaise) et non la zone parente `Up` (0 parcelle). Ces 14 sont déjà dans
  le total Estimé.

## Pistes de modélisation ultérieure (documentées, non faites — prudence)

- **PPRI aléa fort → pleine terre 50 %** (Saint-Paul U1a/U3a) : *réductrice*, conditionnée à un critère
  géométrique. Non faite car « aléa fort PPRI » ≠ « zone rouge PPR (INTERDICTION) » servie : promouvoir
  sans vérifier la couche d'aléa reviendrait à inventer un mappage. À reprendre quand une couche d'aléa
  fort PPRI est câblée au chemin résiduel.
- **Sous-secteurs plus bas non calibrés** (Saint-Joseph U6ch 10/13 m, ZA Vincendo…) : à porter au YAML
  de calibration *si* la couche de zonage les résout — travail des mandats de calibration, à valider par
  un run.

## Garde-fous

- **`pytest tests/`** (base fixture isolée `labuse_c5`) : **35 échecs / 3 525 passés / 72 skips** —
  état de départ identique. Les 35 échecs sont **environnementaux** (verrous `…_sur_la_base_reelle`,
  provenance/circuit sur IDU réels, `test_faisabilite` sur zones réelles) : ils exigent la base
  applicative 52 Go, pas la fixture 71 Mo. Aucun n'est causé par ce mandat (les 2 `test_faisabilite`
  figuraient déjà au baseline).
- **+6 tests neufs verts** (`test_plu_calibrage5_exceptions.py`) + assertion `texte` ajoutée à
  `test_donnees_fix1_exceptions_calcul.py`.
- **`tsc -b` = 0**, **`vitest` = 225 passés**, **V6b vert**.

## Fichiers touchés

- `config/plu_exceptions_effet.json` — verbatim `texte` ajouté aux 81 entrées (source unique).
- `src/labuse/faisabilite/zonage.py` — `texte` porté dans `regles_non_modelisees`.
- `src/labuse/faisabilite/residuel.py` — `capacite_estimee` inclut « porte une non-modélisée ».
- `src/labuse/api/app.py` — idem au chemin fiche (badge honnête sans run).
- `frontend/src/lib/types.ts` — champ `regles_non_modelisees` sur `PotentielTransformation`.
- `frontend/src/components/fiche/constructibilite.tsx` — bloc « exception non modélisée » + verbatim.
- `tests/test_plu_calibrage5_exceptions.py` (neuf), `tests/test_donnees_fix1_exceptions_calcul.py`.
- `docs/audit-2026-09/PLU-CALIBRAGE-5.md` + `PLU-CALIBRAGE-5/{TRI,IMPACT,ESTIMATION_PARCELLES}.csv`.
