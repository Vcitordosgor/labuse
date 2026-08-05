# M32 — Phase C : 3 compléments avant GO (C1 réconciliation · C2 deck · C3 registre)

## C1 — Réconciliation des compteurs AU (aucun nombre ambigu)

Deux périmètres DIFFÉRENTS étaient cités : le **CACHE d'ouverture** (`parcel_au_statut`, classe par
zone) et le **TIER FINAL servi** (`parcel_p_score_v2`, résultat après préséance). Mini-table :

| Nombre | Population | Table | Périmètre / config |
|---|---|---|---|
| **101** | AU marquées phasage (`declasse_au_statut_inconnu`) | `parcel_au_statut` (CACHE) | baseline, config 4 communes |
| **2249** | AU non calibrées (`générique`, = phasage par défaut) | `parcel_au_statut` (CACHE) | baseline, config 4 communes |
| **2000** | AU marquées phasage | `parcel_au_statut` (CACHE) | config 21 communes **BUGGY** (`defaut: conditionnelle_etat_tiers`) — corrigé |
| **810** | AU marquées phasage | `parcel_au_statut` (CACHE) | config 21 communes **CORRIGÉE** |
| **560** | parcelles dont le **TIER FINAL** = `declasse_au_statut_inconnu` | `parcel_p_score_v2` (SERVI) | q_v8_calibre |
| **210** | idem, TIER FINAL | `parcel_p_score_v2` (MESURE) | q_v13_m32_mesure |

**Réconciliation CACHE → TIER (servi).** Au baseline, le cache marque **2350** AU-déclassables
(101 phasage + 2249 générique). Leur TIER FINAL se répartit (préséance : étage 0 et autres
déclassements priment) :

| tier final servi | n |
|---|---|
| écartée (étage 0) | 1 291 |
| **declasse_au_statut_inconnu** | **560** |
| declasse_zone_fermee | 281 |
| declasse_non_constructible | 218 |
| **TOTAL** | **2 350** ✓ |

Donc : **560** (servi, tier) et **210** (mesure, tier) sont les TIERS FINAUX ; **2000→810** est le
CACHE d'ouverture (le 2000 était mon défaut buggy, corrigé à 810). Le cache (810) devient un tier
final (210) après la même préséance. Les deux mondes sont réconciliés, aucun nombre n'est ambigu.

## C2 — Deck des 20 (PDF, format habituel) — FAIT

`qa/m32/deck20_mesure_m32.pdf` + export **`~/Desktop/deck20_mesure_m32.pdf`** (2,8 Mo, 20 cartes).
Chaque carte : idu · commune · zone · avant→après tier/rang · **cause unique** · ortho IGN + contour
parcelle + **millésime PVA 2025 (vols 21/07–02/08/2025)**. Ordre respecté : **dé-déclassées AU
d'abord** (entrent en tête, cause « déclassement AU RETIRÉ »), puis **recalibrations brûlante**, puis
la **sortie** (Saint-Pierre ET2162 brûlante→chaude). AK1442 porte sa note override-registre.
Générateur : `qa/m32/gen_deck_mesure.py` (harnais division_review, ortho cachée /tmp).

## C3 — Registre des overrides à la bascule (mécanisme générique confirmé)

Le geste de bascule ré-applique le registre par une **BOUCLE GÉNÉRIQUE**, pas AK1442 en dur :
`scripts/bascule_m28.py:69` — `for idu, override, motif in REGISTRE:` (AK1442 est une DONNÉE de la
liste, pas une règle). Le geste M32 réutilisera EXACTEMENT ce mécanisme (boucle sur le registre porté).

**Contenu du registre AUJOURD'HUI** (`served_run_exceptions`, run servi q_v8_calibre) :

| idu | tier_origine → tier_servi | motif |
|---|---|---|
| **97422000AK1442** | brûlante → **a_creuser** | V1 : piscine centrale FLAIR 88 m² (seul VRAI override) |
| 97404000AP0323 | brûlante → brûlante | V2 : CoSIA 18 m² sous seuil — servie telle quelle (documentaire) |
| 97404000AT0870 | brûlante → brûlante | A9 : angle mort image documenté — toiture visible (documentaire) |
| 97411000HE0234 | brûlante → brûlante | V3 opt. c : badge géométrie non applicable, dette #12 (documentaire) |

→ Un seul override effectif (AK1442) ; 3 entrées documentaires (servies telles quelles, motif tracé).
Le geste M32 porte ce registre à l'identique et le rejoue par la boucle générique — **aucun idu en dur**.

## Décision : GO / NO-GO après revue du deck

Rien d'autre modifié. Mesure inchangée (q_v13_m32_mesure), servi gelé (golden 117/117). Sur **GO** :
bascule gardée (6 gardes + check_fraicheur), golden régénéré dans le geste, archive `_pre_m32`,
registre rejoué (boucle), SDP bâties révélées + 3 Salazie inclus, recompte post-bascule vs mesure
(tout écart non listé = rollback).
