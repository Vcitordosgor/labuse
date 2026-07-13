# M6 Phase 1 — §1.2 Golden dataset de parcelles étalon

Audit LECTURE SEULE — 2026-07-13. Base `labuse` (SELECT uniquement), API `http://127.0.0.1:8010`.
Run cascade servi : `q_v3_datagap` · run scoring v2 servi : `m36-l2f-2026-2026-07-12`.

## Livrables

| Fichier | Rôle |
|---|---|
| `reports/m6-audit/golden/golden-parcelles.json` | Référence versionnée : 32 entrées (une par IDU), valeurs `db` (18 blocs de couches) + `api` (fiche premium + `/v2/score`) + `coherence_db_api`, tolérances et run_id en méta. |
| `reports/m6-audit/golden/golden-parcelles.md` | Vue lisible (tableau : rôle, tier/rang, statut, étage 0/motifs, surface, zone PLU, couches notables). |
| `qa/golden_check.py` | Contrôleur rejouable (lecture seule : SELECT + GET). `python qa/golden_check.py` → PASS/FAIL par parcelle/champ, exit ≠ 0 si écart ; `--dump` imprime l'état courant pour régénérer la référence. Usage documenté en tête de fichier. |

## Méthode de sélection

32 parcelles, 18 communes (littoral et hauts, premium et non premium — dont Cilaos, Salazie,
Entre-Deux, Sainte-Rose, Petite-Île). Couverture par construction :

- **Témoins M5.1 (5)** — dont les 2 obligatoires 97410000AS1425 et 97423000AB1908 ;
  97423000AB1341 (écartée étage 0 PPR rouge), 97410000CD0905, 97415000EY1509 (bailleur).
- **Chaque tier v2** : brûlante ×8 (rangs 1 à 194), chaude ×7 (rangs 2 à 707),
  réserve foncière ×3, à creuser ×6, écartée ×8.
- **Étage 0, motifs variés (10 parcelles)** : risques/PPR rouge (AB1341), zonage A/N (Cilaos),
  surface (Saint-Pierre), foncier public (Saint-Denis, Saint-Leu, Saint-Pierre),
  emprise linéaire/voirie (Sainte-Rose), pente (Salazie), bâti (Petite-Île, Saint-Leu),
  prescription PLU (Le Tampon).
- **Cas riches en couches** : piscine ortho validée (CX1395), vue mer (AX0289, CR1351, AS1425),
  DPE G/F rattachés (CS0160, DM0210, BY0489), solaire (BI0350), canopée 87 % (AC1870),
  copro RNIC 31 lots (AL0360), bailleur (EY1509), public (CD0729, AO0748), permis récent et
  veille succession (AS1425, AS1450), mutation DVF 2025 (AX1253).
- **Cas pauvres en données** : AK1725 (Bras-Panon) et AI0355 (Cilaos), `a_completude` 67
  (minimum observé en run — le `completeness_score` des parcelles en run est uniformément 92).
- **Cas frontières volontaires** : AP1647 (chaude au rang global 2, devant des brûlantes),
  CW1056 (à creuser au rang 33), CD0729 (brûlante rang 194 MAIS étage 0 — l'une des
  2 brûlantes écartées, d'où les 117 effectives sur 119), AL0360 (copro ⇒ rang NULL).

## Champs figés par parcelle

Côté **base** : commune, section/numéro, surface ; éval cascade (`matrice_statut`, `status`,
q/a_score, a_completude, completeness, étage 0 + motifs HARD_EXCLUDE) ; scoring v2 (tier, rang,
mult_base, percentile, copro, model_version, event_date) ; zonage PLU (détail + zone + % de
recouvrement) ; risques ; vue mer ; solaire ; piscines ortho ; DPE ; végétation ; copros RNIC ;
veille succession ; score V/owner_type ; personne morale ; résiduel (SDP) ; adresse BAN ;
DVF (n, dernière) ; permis SITADEL (n, dernier).
Côté **API** : fiche premium (`/parcels/{idu}?source=q_v3_datagap` — statut, étage 0, scores,
score_v2, zonage, copros, DVF, SIREN, nb lignes cascade) et `/v2/score/{idu}` (tier, rang,
mult, percentile, run_id, badge veille).
Tolérances (JSON `meta.tolerances`) : mult_base ±0,011, percentile ±0,11, surface ±1 m²,
canopée ±2 pts, NDVI ±0,03, prod. solaire ±5, distance côte ±10 m, pente ±0,5°, obstruction ±2 pts ;
égalité stricte partout ailleurs.

## Résultat du run initial

```
python qa/golden_check.py   →   32/32 PASS, 0 FAIL,
                                0 parcelle avec incohérence base↔API, exit 0
```

Attendu (référence = état courant) et vérifié. Le contrôleur émet un WARN si le run v2 servi a
changé depuis la référence (écarts tier/rang alors légitimes → régénérer via `--dump`).

## Vérification manuelle de plausibilité (11 parcelles, dont les 2 obligatoires)

Croisement externe apicarto IGN (cadastre `contenance` + GPU `zone-urba` au centroïde) :

| IDU | Surface base / contenance cadastre | Zone base (norm. / brute) / GPU | Verdict |
|---|---|---|---|
| 97410000AS1425 ★ | 300 / 302 | AUc / AUa5 / AUa5 | OK |
| 97423000AB1908 ★ | 313 / 318 | AUc / 1AUb / 1AUb | OK |
| 97410000CD0905 | 334 / 308 (−8 %) | AUc / AUb19 / AUb19 | OK (écart contenance à surveiller) |
| 97423000AB1341 | 355 / 359 | N 94 % / Nco+1AUb / 1AUb au centroïde | OK mais **doublon N** (voir anomalie 1) |
| 97415000EY1509 | 1 352 / 1 328 | U / U3a / U3a | OK |
| 97411000KA0296 | 300 / 300 | AUc / AUm / AUm | OK |
| 97408000AP1647 | 382 / 386 | AUc / AUBm / AUBm | OK (ligne AUBm dupliquée en base) |
| 97424000AD0409 | 8 / 8 | A / A / A | OK (étage 0 surface+zonage justifié) |
| 97411000AO0748 | 7 483 / 7 486 | U / Udo / Udo | OK (foncier public → étage 0 justifié) |
| 97413000CS0160 | 581 / 600 | U / UC / (apicarto vide) | OK sur libellé brut |
| 97413000CD0729 | 337 / 340 | AU / AUE / (apicarto vide) | OK sur libellé brut |

★ = parcelles obligatoires. Surfaces : écarts ≤ 2 % sauf CD0905 (−8 %, contenance légale vs
géométrie — dans la nature des deux mesures, consigné). Zonages : le libellé brut ingéré
(`spatial_layers.attrs->>'libelle'`) coïncide avec le GPU dans 9/9 cas comparables ; le champ
`subtype` de la base est une classe normalisée (U/AU/AUc/A/N) — c'est elle qui alimente la fiche.
Apicarto ne renvoie aucun zonage au centroïde pour Saint-Leu (2 parcelles) alors que la base a
des zones GPU ingérées : limite côté apicarto, vérification faite sur le libellé brut.

## Anomalies consignées en constituant le set

1. **Doublons PLU (confirme le finding A1 du lot 4, M5.1)** — observés en direct :
   97423000AB1341 a sa zone N **en double** (47 % + 47 % = 94 % ≥ seuil 90 %) → le HARD_EXCLUDE
   zonage de cette parcelle repose sur un recouvrement doublé (réel ≈ 47 % → mixte, pas
   exclusion) ; l'exclusion reste vraie via le PPR (risques). 97408000AP1647 a aussi sa zone
   AUBm dupliquée (sans effet : 100 % plafonné). À traiter par la dédup A1 avant recompute.
2. **Étage 0 ≠ tier v2 écartée** — le tier v2 est calculé indépendamment de l'étage 0 :
   10 335 parcelles étage 0 portent un tier non écarté (9 321 à creuser, 940 réserve,
   72 chaudes, **2 brûlantes** — d'où 117 brûlantes effectives / 119). L'inverse est sain :
   tier « ecartee » ⟹ étage 0 (0 contre-exemple). Sans impact client (règle 1 M5 : l'étage 0
   du run servi prime partout), mais toute liste construite sur le tier seul re-exposerait ces
   10 335 parcelles. Témoins dans le set : CD0729, CR1351, AO0748.
3. **Copro ⇒ rang NULL** — les parcelles `copro=true` du run v2 sont hors classement
   (rang NULL : 376 à creuser, 15 réserve, 3 033 écartées). Design assumé (copro hors cible),
   mais le rang NULL doit être géré par tout consommateur (témoin : AL0360, tier a_creuser).
4. **`matrice_statut` (legacy) contredit le tier v2** — ex. AS1425/AB1908/CD0905 : legacy
   « ecartee », v2 « brulante ». Connu (unification M5.1 : le v2 pilote, le legacy n'est plus
   exposé comme verdict) ; figé dans le golden pour détecter toute régression d'affichage.
5. **Base↔API : 0 divergence** sur les 32 parcelles (statut, étage 0, scores, tier/rang/mult
   sur les deux endpoints, copros, SIREN, badge veille succession). Aucune anomalie de
   cohérence runtime détectée — la classe de contrôles reste armée dans `golden_check.py`.

## Rejouer le contrôle

```bash
# après chaque refresh de données :
/Users/openclaw/miniforge3/envs/labusedb/bin/python qa/golden_check.py            # exit 0 = OK
# après un changement LÉGITIME (nouveau run v2, recompute) :
/Users/openclaw/miniforge3/envs/labusedb/bin/python qa/golden_check.py --dump \
  > reports/m6-audit/golden/golden-parcelles.json     # puis versionner le diff
```
