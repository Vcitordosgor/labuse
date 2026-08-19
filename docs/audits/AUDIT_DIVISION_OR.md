# AUDIT COURT — DIVISION_OR : SES ENTRÉES ET SES RÈGLES

*Audit pur, aucune correction. Module : `src/labuse/ingestion/division_or.py` (894 l., O12).
7 candidates en base (`division_or_candidates`), workflow de revue PAR COMMUNE, `EXPOSE=True`
(validé Vic 28/07 après 2 revues + calibrage PLU, 0 faux positif connu).*

---

## ⚠ PRÉMISSE DU MANDAT À RENVERSER (le point :260)

**`division_or` ne PRODUIT PAS le tampon `faux_positif_probable` — c'est l'inverse.** Les lignes
`:255-265` sont le commentaire d'un arbitrage (Vic 30/07) qui **REFUSE** de filtrer dessus : la
garde amont n'écarte un candidat que si sa parcelle support est `status = 'exclue'` au run servi
(fait définitif — PPR rouge, foncier public), **PAS** `faux_positif_probable` (« c'est une
probabilité, pas un fait ; le bâti-avec-résiduel EST la prémisse d'O12 »). Le tampon
`faux_positif_probable` des parcelles support est produit par la **CASCADE** (couche `bati`,
`phase1.py:864` kind=faux_positif → `opportunity.py:44` → statut) — pas ici. À M129, ce qui
« perd son tampon », c'est la parcelle support via la refonte cascade ; division_or, lui, y **lit**
l'étage 0 (`:263-265`) et devra simplement suivre la nouvelle définition d'« écartée ».

## 1. LES ENTRÉES (fichier:ligne · millésime · âge de ce que l'outil voit)

| Entrée | Où | Millésime / ingéré | Âge vu |
|---|---|---|---|
| **Cadastre** `parcels` (geom_2975, surface) | `:182-185` | Etalab bulk, ingéré 06/2026 | ~2 mois |
| **BD TOPO bâti** `spatial_layers kind='batiment'` | `:186-189` | ingéré **29/06/2026** ; photogrammétrie IGN sur ortho ~2023 (cycle DOM ~3 ans) | **le bâti réel peut avoir ~3 ans de retard** — l'outil le SAIT (garde PC, cf. §2) |
| **BD TOPO voirie** `kind='voirie'` (façades) | `:216-217`, découpe `:349` | ingéré 01/07/2026 | idem BD TOPO |
| **PLU/GPU** `kind='plu_gpu_zone'` (zone du LOT) | `:238-240` | ingéré 03/07/2026 (opposable ~06/2026 ; Sudocuh M124 : 0 commune en retard) | frais |
| **PAU estimée** `parcel_pau` (repli RNU) | `{pau_pred}` `:254` | dérivée | — |
| **Étage 0 du run servi** `dryrun_parcel_evaluations` | `:263-265` (`:served` = Q_A_RUN_LABEL) | run q_v9_m81 | suit la bascule |
| **Constructibilité** `parcel_constructibilite` (declasse_*) | `{constr_guard}` `:266` | run-scopée | — |
| **50 pas / forêt domaniale / cœur Parc / trait de côte** | `:281-288` | ingérés 06-07/2026 (millésimes amont 1877-2021) | couches cascade |
| **Sitadel PC** (garde fraîcheur bâti) | `PC_FRAIS_DEPUIS :124` | 2026-06 (sonde à jour) | frais |
| **Score É** `score_e` (gain estimé) | `:305` | run-scopé | — |
| **PLU calibré** `config/plu_<commune>.yaml` (emprise max zone) + `o12_exclusions_revue.yaml` | `{emprise_max}` `:277`, `{revue_pred}` `:273` | curation | — |

**Ce qu'il ne lit PAS** : **ni MNT/pente** (un lot à 40 % de pente passe — la revue visuelle est le
seul filet), **ni ortho directement** (l'ortho IGN n'est vue que par l'écran de revue,
`division_review.py`), ni réseaux, ni servitudes privées (assumé en tête de module `:45-46` :
« rien n'est affirmé sur la constructibilité réglementaire — la revue humaine tranche »).

## 2. LES RÈGLES, UNE PAR UNE (seuil · où · origine)

**Famille RÉSIDUELLE (lot = plus grand polygone de parcelle − bâti bufferisé 3 m) :**

| Règle | Seuil | Où | Origine |
|---|---|---|---|
| Surface parcelle | 1 000-6 000 m² | **en dur SQL** `:185` | conservateur (« place pour 2 lots ») |
| Ratio bâti | 8-45 % | **en dur SQL** `:207` | conservateur |
| Buffer autour du bâti | 3 m | en dur `:205` | recul prudent (pas une règle PLU) |
| Bâti d'activité exclu | ≥ 3 bâtiments OU ≥ 400 m² | `:210` via **constantes partagées** `bati.py` (ENSEMBLE_MIN_BATIMENTS, GRAND_BATIMENT_M2) | critère cascade réutilisé (chemin unique) |
| Lot min/max | 500 m² ≤ lot ≤ surface−400 ET ≤ 50 % | en dur `:219` | revue O12-ÎLE (démembrement refusé) |
| Cercle inscrit | ≥ 9 m de rayon | en dur `:219` | ~18 m constructibles (pas une lanière) |
| Compacité Polsby-Popper | ≥ **0,25** | constante `:66`, appliquée `:222` | **calibré sur la distribution île** (P25=0,11, méd=0,21) |
| Façade voirie du lot | ≥ 12 m | en dur `:253` | accès indépendant (« le vrai discriminant ») |
| Zone du lot | U ou AU* (dominante) ; RNU → PAU | `:254` | revue O12-ÎLE |
| Zonage d'activité exclu | par CODE (config) + par LIBELLÉ regex `:130-133` | `:270-271` | finding BP0363 (« Ua ZA du Chaudron ») |
| Démolition bornée | bâti_lot × 3 ≤ bâti_total | `:267` | anti-découpage inversé |
| Emprise du RESTE | ≤ emprise max **calibrée PLU** sinon **0,60** | constante `:73`, `:277` | revue 4e itération (cartes à 80-81 %) |
| Littoral/domaine public | 50 pas ∩, forêt domaniale ∩, cœur Parc ∩, trait de côte ≤ 1 m | `:281-288` | revue + trou Barachois |
| Étage 0 servi | `status='exclue'` seulement | `:263-265` | arbitrage Vic 30/07 (cf. prémisse) |

**Famille DÉCOUPE (« bande de façade », sur les recalées du ratio 50 %)** : lot 600-900 m²
(`:86-87`), ancre ≤ 25 m ×3 positions, profondeur 20-40 m (`:363-364`), compacité ≥ **0,55**
(`:88`, relevée de 0,28 en revue 2), **solidité** aire/enveloppe convexe ≥ **0,85** (`:123` — seuil
le plus haut préservant toutes les validées ; les « U modérés » 0,86-0,91 = limite consignée),
façade contiguë ≥ 12 m, **anti-enclavement** (le reste garde ≥ 12 m de façade), **érosion du
reste 2 m** d'un seul tenant (`:102` — un couloir < 4 m ne connecte pas), distance lot↔bâti ≥ 1 m
(`:103` — cohérence géométrique, PAS une règle d'urbanisme, le 3 m réglementaire refusé), reste
≥ 400 m², **fraîcheur bâti : PC ≥ 2023-01-01 → parcelle exclue** (`:124` — BD TOPO ne peut pas
avoir vu le chantier).

**Origines en synthèse** : ~1/3 calibré sur mesures (compacité, solidité, emprise PLU), ~1/3
issu des revues visuelles de Vic (50 %, 400 m², activité, littoral), ~1/3 prudence géométrique
en dur (1000-6000, 8-45 %, 9 m, 12 m, buffers). **La plupart sont EN DUR dans le SQL/constantes
module** — pas en config (sauf emprise PLU calibrée, exclusions de revue, codes activité).

## 3. LE « NOMBRE DE LOTS » — il n'existe pas

**Division_or n'estime PAS « ~N lots » : il propose UN lot détachable** (le plus grand résiduel,
ou une bande de façade), avec ses métriques (`residuel_m2`, rayon, façade, `clarte` =
rayon×2 + façade plafonnée à 30 m `:302`, `gain_estime_eur` = marge Score É `:301-305`). Le
« ~N logements/lots » que le client voit ailleurs vient du moteur de **FAISABILITÉ** (fourchette
`logements_au_sol`), pas d'ici. Si M129 veut un « nombre de lots », c'est une CONSTRUCTION nouvelle
(ex. résiduel_m2 / 350 m²) — à décider, rien à auditer aujourd'hui.

## 4. CE QU'IL NE VOIT PAS (chiffré où mesurable)

- **Construction récente absente de BD TOPO** : l'écart EST mesurable par CoSIA (PVA 2025) —
  **16 142 parcelles au bâti révélé** (BD TOPO aveugle), dont **7 551 à ≥ 50 m²**. L'outil ne lit
  PAS `parcel_bati_revele` ; il se protège autrement (PC Sitadel ≥ 2023 → exclu, `:117-124`). Le
  trou résiduel : un bâti récent SANS PC déclaré (ou PC < 2023 à chantier tardif) passe.
- **La pente** : aucun MNT lu — un lot escarpé n'est arrêté que par la revue visuelle.
- **Servitudes privées, réseaux, accès juridique** : assumé hors périmètre (`:45-46`) ; l'accès du
  lot BÂTI restant est jugé VISUELLEMENT (métrique automatique invalidée — finding O12 `:39-41`).
- **Le run stamp** : les 7 candidates portent `run_label = q_v8_calibre` (ancien run) alors que le
  servi est q_v9_m81 — la garde `bascule_gardes.py:614-616` le TOLÈRE (workflow de revue par
  commune, garde informative) ; à re-tamponner au prochain build.

## 5. SORTIES ET CONSOMMATEURS (la carte avant M129)

**Sortie** : table `division_or_candidates` (7 lignes, colonnes `:136-178` — géométrie du lot
`lot_geom`, type libre/démolition, métriques, gain, clarté, `note_revue`).

| Consommateur | Usage | Où |
|---|---|---|
| **Facette carte** `division_or` | `EXISTS(division_or_candidates)` | `app.py:1076-1077` |
| **Projets** (cadrage) | clé `divisionOr` → même filtre | `projets.py:188` |
| **Renouvellement** | `comp_divisibilite` 0\|**15 points** (« géométrie favorable », jamais une promesse) | `renouvellement.py:91,180` |
| **Dossier de revue** (écran Vic, cartes IGN) | lit `lot_geom` + métriques | `division_review.py:38` |
| **Bascule** | garde fraîcheur informative (tolérée par commune) | `bascule_gardes.py:608-616` |
| **CLI** | `division-or` (build par commune) | `cli.py:2682` |

**Ne le consomment PAS** : la cascade (aucune couche ne le lit), le score P (aucune feature),
la fiche verdict (`verdict_servi.py:47` « bâtie + division possible » lit **`parcel_filtre_bati`**,
un AUTRE signal de divisibilité — M28 filtre bâti — à ne pas confondre ; deux « divisibilités »
coexistent, à unifier ou distinguer explicitement à M129). Entrée inverse : division_or LIT
score_e (gain) et le run servi (garde étage 0).

---

*Interdits respectés : rien corrigé, chaque seuil avec son fichier:ligne, pas mergé.*
