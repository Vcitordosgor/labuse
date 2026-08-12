# RAPPORT M59 — Section « Mode B — Réhabilitation » — PHASE 0 (diagnostic)

Branche `feat/m59-rehabilitation` (de `main`, contient m58 mergé). **Diagnostic seul,
aucun correctif, aucune formule touchée.** L'arithmétique est JUSTE (vérifié mandant :
26 k€ / 68 k€ se recalculent). Le problème mesuré est le **cadrage**, pas le calcul.
Sources : code (`bilan.py`, `defisc.py`, `Fiche.tsx`, `export.py`), base `labuse`
(run servi **q_v8_calibre**), population Mode B = **33 958 parcelles** (2 tiers déclassés
bâti : `declasse_bati_sature` + `declasse_bati_revele`, arbitrage Vic 06/08).

Point de calcul : `compute_mode_b()` `src/labuse/faisabilite/bilan.py:749-864` ;
sortie locative `src/labuse/faisabilite/defisc.py:80-138`. Rendu :
`ModeBDrawer` `frontend/src/components/fiche/Fiche.tsx:1014-1093`.

---

## Q1 — VALEUR DU TERRAIN : jamais dans le calcul

**Le calcul de réhabilitation porte UNIQUEMENT sur la surface habitable du bâti
existant.** Formule (`bilan.py:790-794`) :
```
SHAB        = emprise_bâti × niveaux ÷ 1,15
achat_max   = SHAB × prix_sortie × coef_CA − SHAB × travaux
            = SHAB × (prix_sortie × 0,79 − travaux)
```
`coef_CA = 1 − marge 9 % − frais 12 % = 0,79`. **La surface du foncier (ici 1 941 m²)
n'entre NULLE PART** : ni la contenance, ni un prix terrain, ni une valeur vénale du sol.
Le résultat est pourtant présenté comme un **« prix d'achat max »** (global, du bien).

**Mesure — sur combien de parcelles le « prix d'achat max réhab » est-il INFÉRIEUR à la
valeur du terrain nu au prix du secteur** (`surface_parcelle × médiane DVF terrain` du
secteur → repli commune, `dvf_secteur_medianes type_bien='terrain'`) :

| Défaut travaux | réhab achat_max < valeur terrain nu | dont bilan négatif |
|---|---|---|
| **1 200 €/m²** (défaut FRONT, `useApp.ts:95`) | **50,2 %** (~17 050) | 2 226 |
| **1 500 €/m²** (défaut BACK, `bilan.py:719`) | **64,4 %** (21 864) | 7 115 |

→ Sur **la moitié à près des deux tiers** de la population, la réhabilitation « justifie »
un prix d'achat **inférieur à ce que vaut le sol nu seul**. Le chiffre lit comme un prix
d'achat du BIEN alors qu'il ne finance QUE le bâti à réhabiliter — le foncier (souvent
l'essentiel de la valeur) est ignoré. Les 33 958 parcelles ont toutes un prix terrain et
un prix bâti mesurables (0 cas sans donnée).

**Effet de bord relevé (à trancher)** : **défaut travaux incohérent front/back** — la
fiche initiale (`f.mode_b`, `compute_mode_b` sans paramètre) calcule à **1 500 €/m²**,
mais le curseur front par défaut est **1 200 €/m²** (`MODE_B_DEFAUT.travauxM2`). Le
montant servi change donc selon qu'on lit la fiche initiale ou qu'on touche le curseur —
tension avec la garde « valeurs identiques ». Signalé, non corrigé.

## Q2 — LOYER : plafond réglementaire employé comme revenu, étiqueté « Sourcé »

`defisc.py:98-105` — le loyer par défaut est le **plafond réglementaire d'un dispositif de
défiscalisation** :
```
loyer_m2_effectif = plafond_brut × coef_surface
plafond base = 12,21 €/m²/mois   (config/calibrage/defisc_2026.yaml:24)
coef_surface = min(0,7 + 19/SHAB, 1,20)   → mord sur les petites surfaces
```
Sur une petite SHAB, `coef_surface` monte au plafond 1,20 → `12,21 × 1,20 ≈ 14,65` — d'où
le **« ~14 €/m²/mois »** observé. **Ce n'est PAS un loyer de marché observé** : c'est un
**plafond** (barème BOFiP **BOI-BAREME-000017**, dispositif type logement intermédiaire) —
un maximum autorisé, pas une observation, pas une prédiction de loyer atteignable.

**Étiquette servie** (`defisc.py:104`) : `"Sourcé (BOFiP BOI-BAREME-000017 · 2026-03-10)"`.
Le « Sourcé » est vrai pour **la valeur du plafond** (elle vient bien du BOFiP) mais
**trompeur comme hypothèse de revenu** : un plafond *borne* le loyer, il ne le *prédit*
pas ; l'employer tel quel comme recette locative surestime le revenu là où le marché réel
est plus bas.

**Source de loyer de MARCHÉ ?** — **Aucune.** La seule alternative (`defisc.py:94-97`,
voie b) est un `loyer_marche_m2` **saisi par le client**, étiqueté « Estimé (paramètre
client) ». Pas d'observatoire des loyers, pas de DVF locatif ingéré. Le produit ne connaît
que le plafond (Sourcé) ou une saisie manuelle (Estimé).

## Q3 — COHÉRENCE DES MÉDIANES : deux requêtes différentes, périmètres non dits

- **Prix de sortie Mode B** (`_prix_bati_local` `bilan.py:726-746`) : table
  **`dvf_secteur_medianes`** pré-agrégée — `max(mediane_prix_m2)` maison/appartement du
  **secteur** (IDU[:10], `n_ventes ≥ 3`) → repli **commune** (IDU[:5]). **AUCUN rayon**,
  aucune distance : médiane sectorielle pré-calculée. Libellé servi : « médiane DVF
  maison/appartement du secteur (n ≥ 3) ».
- **Prix du tiroir « Marché »** (`sector_price` `bilan.py:163-232`, Mode A) : requête sur
  **transactions DVF brutes** avec **rayon adaptatif** 500 → 1000 → 1500 m → commune.

→ **Requête différente, table différente, agrégation différente, périmètre géographique
différent.** Les deux médianes (2 296 vs 2 503 €/m²) **peuvent légitimement diverger** :
elles ne mesurent pas la même chose. Le problème : **aucun des deux chiffres n'affiche son
périmètre** (rayon, nombre de ventes retenues, millésimes) — la divergence reste
inexpliquée à l'écran, elle lit comme une incohérence.

## Q4 — SEUIL DE PERTINENCE : il n'y en a pas

**Gating de la section** (`compute_mode_b` `bilan.py:765-777`) — trois conditions, **aucun
seuil de surface habitable** :
1. `tier ∈ (declasse_bati_sature, declasse_bati_revele)` ;
2. `emprise_bâti ≥ 20 m²` (dur) ;
3. un prix de sortie DVF existe (secteur ou commune).

**Mesure** (population tier, SHAB = emprise × niveaux ÷ 1,15, niveaux BD TOPO sinon 1) :

| | parcelles |
|---|---|
| population tier (declassé bâti) | 33 958 |
| dont emprise ≥ 20 m² | **33 958** (100 %) |
| dont prix DVF dispo → **section AFFICHÉE** | **33 958** (100 %) |
| **affichée avec SHAB < 50 m²** | **1 851 (5,5 %)** |
| affichée avec SHAB < 35 m² | 567 |
| SHAB médiane | 148 m² |

→ La section s'affiche sur **toute** parcelle de la population ; **1 851 (5,5 %)** portent
une thèse de réhabilitation sur **moins de 50 m² habitables** (567 sous 35 m²), où la thèse
a peu de sens (un bilan travaux/revente sur ~30-40 m² est fragile). **Il n'existe aucun
seuil** ; seule la garde `emprise ≥ 20 m²` filtre, et à niveaux=1 elle laisse passer
SHAB ≈ 17 m².

## Q5 — NOM « Mode B » : où il apparaît, et ce qu'un renommage touche

**Chaînes d'AFFICHAGE (renommage purement cosmétique)** :
- `Fiche.tsx:1029` — titre du tiroir « Mode B — Réhabilitation ».
- `export.py:78, 201, 480, 489` — 4 emplacements PDF (Markdown, HTML, one-pager REVENTE +
  LOCATIF) : « Mode B — Réhabilitation », « Mode B — Réhab · REVENTE / LOCATIF ».

**CLÉS INTERNES servies / dont d'autre code dépend (NE PAS renommer)** :
- route API `GET /parcels/{idu}/mode-b` (`app.py:2408`) ;
- `RefDrawer id="mode-b"` + `queryKey ['mode-b', …]` (`Fiche.tsx:1020,1029`) ;
- params API `modeb_travaux_m2` / `modeb_loyer_m2` / `modeb_rendement_pct` (`api.ts:108-110`) ;
- champ de fiche **`mode_b.disponible`** (gating front) ;
- const `MODE_B_DEFAUT` (`useApp.ts:95`), clé de filtre `modeBRentable` / `mode_b_rentable`
  (`filters.ts`) ;
- back `MODE_B_TIERS`, `compute_mode_b()`, `tests/test_mode_b.py`.

→ **Renommer les 5 chaînes d'affichage (fiche + 4 PDF) = cosmétique, sans risque.**
Renommer route / champ `mode_b` / params / clés de filtre **casserait des contrats servis**
(front↔back, filtres, tests) → à laisser tels quels.

## Q6 — STATUT DE LA SECTION : conditionnelle (8ᵉ tiroir)

Rendu **sous condition** (`Fiche.tsx:1876`) : `{f.mode_b?.disponible && <ModeBDrawer …/>}`.
Elle **n'est PAS** affichée sur toute parcelle bâtie : uniquement sur les **33 958**
parcelles de la population déclassée-bâti (tier) avec emprise ≥ 20 m² et prix DVF.
Conforme au registre M55-O : Mode B est resté un **8ᵉ tiroir conditionnel**, jamais
généralisé à tout le bâti.

---

## Synthèse

| Q | Constat mesuré |
|---|---|
| 1 | Réhab calcule sur la **SHAB seule**, terrain (1 941 m²) **jamais** dans la formule. Sur **50–64 %** des 33 958 parcelles (selon défaut travaux 1200/1500), le « prix d'achat max » est **sous la valeur du terrain nu** ; 2 226–7 115 négatifs. **Bonus** : défaut travaux front 1200 ≠ back 1500. |
| 2 | Loyer = **plafond réglementaire** BOFiP (BOI-BAREME-000017) × coef surface ≈ 14 €, employé comme **revenu**, étiqueté **« Sourcé »**. Aucune source de loyer de **marché** (seule alternative = saisie client « Estimé »). « Sourcé » vrai pour le plafond, trompeur comme recette. |
| 3 | Prix sortie Mode B = `dvf_secteur_medianes` (secteur→commune, **sans rayon**) ; « Marché » = `sector_price` (**rayon adaptatif** 500-1500 m sur DVF brut). Requêtes/tables/périmètres **différents** → divergence légitime (2296 vs 2503) mais **aucun périmètre affiché**. |
| 4 | Gating = tier + emprise ≥ 20 + prix DVF. **Aucun seuil de SHAB.** Affichée sur **100 %** (33 958) ; **1 851 (5,5 %) avec SHAB < 50 m²** (567 < 35 m²). |
| 5 | « Mode B » d'AFFICHAGE : fiche (1 titre) + PDF (4). Renommage cosmétique OK. Clés INTERNES (route `/mode-b`, champ `mode_b`, params `modeb_*`, filtre, tiers, tests) **servies** → à ne pas toucher. |
| 6 | **Conditionnelle** (`f.mode_b.disponible`, `Fiche.tsx:1876`) — 8ᵉ tiroir M55-O, jamais sur tout le bâti. |

## STOP — PHASE 0
Phase 0 terminée. **Aucun correctif, aucune formule modifiée.** En attente d'arbitrage sur
la Phase 1 (a→f). Points ouverts pour le mandant :
- **Q1** : le « prix d'achat max réhab » doit-il dire « hors valeur du terrain » (option b)
  et/ou intégrer le foncier ? (intégrer = **modification de formule**, hors P0, à arbitrer) ;
- **Q1 bonus** : aligner le défaut travaux front/back (1200 vs 1500) — lequel fait foi ?
- **Q2** : plafond → retirer « Sourcé » comme hypothèse de revenu, avertissement AVANT le
  chiffre (option c) ;
- **Q4** : quel **seuil de SHAB** arbitrer sous lequel la section ne s'affiche pas (ou dit
  « surface trop faible ») ? (option e) ;
- **Q5** : renommer « Mode B » → « Réhabilitation » côté affichage seulement (option a).

NE PAS MERGER.
