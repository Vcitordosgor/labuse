# DONNEES-FIX-1 — Badge LiDAR juste · faux changements de propriétaire · hauteur LiDAR dans le résiduel

- **Branche** : `fix/donnees-fix-1` (depuis `main` `df386bfc`) · worktree `~/Desktop/labuse-donneesfix` · ports 8515/5715 · non mergée.
- **Suite d'exécution** de l'audit `docs/audit-2026-09/DONNEES-LIDAR-PROPRIO.md` (mergé).
- **DB** : `postgresql://openclaw@localhost:5432/labuse` (lecture + un run de test NON servi). venv `~/Desktop/labuse/.venv`.
- **Un commit par lot.** tsc/vitest/pytest verts (détail §Vérification).
- **Date** : 2026-09-25.

---

## Lot A — Le badge « Sources discordantes » compare la bonne grandeur

### Le défaut

FICHE-FIX-2 comparait le **faîtage** LiDAR (p99) à la hauteur BD TOPO. Or BD TOPO stocke une hauteur **≈ l'égout** (bord de toit) : sur un toit en pente ou un R+n, le faîtage dépasse *toujours* l'égout ≈ BD TOPO — l'écart n'est pas une erreur, c'est la **définition**. Le badge s'allumait donc sur **52 759 bâtis** (|faîtage − BD TOPO| > 3 m, ≈ 16 % des comparables) alors que l'audit ne trouve que des cas normaux + une poignée de vraies aberrations.

### La correction

Règle **UNIQUE** `discordance_hauteur` (`faisabilite/hauteur_lidar.py`), lue par la fiche §Bâti **et** la marge en hauteur (Potentiel) — une seule règle pour les deux écrans. Deux motifs, tous deux réels :

1. **« égout ↔ BD TOPO »** — `|égout LiDAR − hauteur BD TOPO| > 15 m` (la **même** grandeur).
2. **« faîtage aberrant »** — `faîtage ≤ 0` ou `> 60 m` (hauteur physiquement impossible sur l'île).

#### Justification des seuils (distribution mesurée)

`|égout − BD TOPO|` sur **273 552** comparables : médiane **1,70 m**, moyenne 2,14 m, p90 **4,50 m**, p99 **8,40 m**, max ≈ 30 m.

> ⚠️ La prémisse « égout ≈ BD TOPO, serré » (l'audit rapportait la moyenne **signée** +0,55 m, qui se compense) est à nuancer : la dispersion **absolue** est réelle (médiane 1,70 m). Un seuil bas donnerait des milliers de badges (>3 m : 66 030 ; >8 m : 3 269). Sensibilité : >12 m → 448 ; **>15 m → 132** ; >20 m → 14.

Le bruit normal (arrondi BD TOPO, débords de toiture, pente du terrain sous l'emprise) reste ≤ ~8 m (p99). **15 m** (≈ 1,8 × p99, ~5 niveaux d'écart sur la même grandeur) désigne un écart qu'aucune mesure ne peut expliquer → une des deux sources est fausse : **132** parcelles.

Le **plafond faîtage** > 60 m (plus haut immeuble de l'île ~15 étages ≈ 45 m) capte les 2 aberrations de coordonnée de l'audit (**53 401 m**) ; `faîtage ≤ 0` (MNS < MNT, mesure cassée) en capte 56 de plus → **58** au total.

Le seuil `SEUIL_ECART_EGOUT_BDTOPO_M = 15.0` et le plafond `PLAFOND_FAITAGE_ABERRANT_M = 60.0` sont des constantes documentées, réglables par Vic.

### Compte badgé — avant / après

| | Avant (faîtage↔BD TOPO > 3 m) | Après (égout↔BD TOPO > 15 m **ou** faîtage aberrant) |
|---|---:|---:|
| Parcelles badgées | **52 759** | **189** (58 hauteurs impossibles + 131 discordances ≥ 15 m) |
| Part des comparables | 15,9 % | 0,07 % |

- **BZ1065** : faîtage 10,3 · égout 3,6 · BD TOPO 4,2 → |égout − BD TOPO| = 0,6 m. **Badgée avant, plus badgée après** ✅ (capture 01 = avant, capture 02 = après).
- **Aberrations** `97418000AZ0128/0417` (faîtage 53 401) : **badgées après** ✅ (motif « faîtage aberrant »).

### Ce qui change dans la fiche

- §Bâti : la hauteur mesurée s'affiche en **trois lignes libellées sans ambiguïté** — « Faîtage mesuré (LiDAR) » · « Égout mesuré (LiDAR) » · « Hauteur BD TOPO (≈ égout) ». Le badge nomme le motif (égout↔BD TOPO avec l'écart, ou faîtage impossible).
- Potentiel (marge en hauteur) : **même** règle ; le drapeau ne s'allume que si la marge repose sur une mesure LiDAR (`nature = sourcé`).

---

## Lot B — Plus de faux changements de propriétaire dans la fiche

### Le défaut

`historique()` (fiche §Identité) comparait le **SIREN brut** d'un millésime à l'autre sans écarter les **pseudo-siren « U… »** (attribués par LABUSE quand la DGFiP n'a pas résolu le SIREN, ~13 % des lignes) ni le SIREN **absent** des premiers millésimes → des « changements de propriétaire » qui n'ont jamais eu lieu. La frise « Remonter le temps » les neutralisait déjà, mais avec une règle **dupliquée** (« startswith U ») qui, en plus, **ratait le cas NULL → SIREN réel**.

### La correction

Règle **UNIQUE** `changements_millesimes` (`proprietaire_historique.py`), lue par la fiche §Identité **et** la frise (`moteurs.py` consomme le drapeau `non_identifiable`, plus de copie) :

- un changement n'est **affirmé** que si les deux SIREN sont **réels** (9 chiffres, ni « U… » ni absent) **et différents** ;
- toute autre transition apparente → **« propriétaire PM non identifiable (DGFiP) »** (comme la frise), jamais un changement inventé ;
- une re-clé de dénomination à SIREN réel inchangé n'est **pas** un changement.

`n_changements` ne compte désormais que les changements **réels** ; `n_transitions` = réels + non identifiables.

### Témoins (chaîne 2019→2025 réelle en base)

| Témoin | Chaîne SIREN | Faux changements **avant** | Après |
|---|---|---:|---|
| **SCI Laurent Grandpre** `97411000CD1214` | NULL → U23719996 → 483339628 (réel) | 2 | **0 réel** ; 2 « non identifiable » |
| **ONF** `97415000AB0001` | U15960284 → U15960284 → 662043116 (réel) | 1 | **0 réel** ; 1 « non identifiable » |
| **Vrai changement** `97402000AD0359` | 229740014 (Département) → 219740024 (Commune) | 1 | **1 réel conservé** ✅ |

Capture 03 = §Identité avant (faux « SCI LAURENT GRANDPRE → SCI LAURENT GRANDPRE »), capture 04 = après.

---

## Lot C — La hauteur LiDAR entre dans le résiduel

### Le principe

Une **seule** implémentation (le moteur résiduel `compute_residuel`), lue par la fiche, le Gabarit et le filtre Capacité (tous lisent la vue `parcel_residuel` d'un run). Le lot ne touche NI l'emprise bâtie NI la capacité max (`sdp_max`) — seuls **les niveaux existants** (leur source) et un **coefficient de plancher** changent.

### 1. Niveaux existants depuis l'ÉGOUT LiDAR

`niveaux = max(1, round(égout_LiDAR / 3,0 m))`. L'**égout** (bord de toit), **pas le faîtage** : le faîtage inclut le volume de toiture, qui n'est pas un niveau habitable — le compter surestimerait l'existant.

**Calibrage** sur **229 615** bâtiments portant un `nombre_d_etages` BD TOPO renseigné (bâtiment principal de la parcelle joint à l'égout LiDAR) :

| hauteur d'étage | accord exact `round(égout/h) = étages BD TOPO` |
|---|---:|
| 2,5 m | 69,1 % |
| 2,7 m | 73,1 % |
| **3,0 m** | **75,7 %** |
| 3,2 m | 76,5 % |

À **3,0 m** : **75,7 % d'accord exact**, **98,3 % à ±1 niveau**. 3,0 m est la hauteur d'étage standard, déjà employée par le repli BD TOPO (`hauteur/3`). Constante `ETAGE_REF_M`.

Priorité : **LiDAR égout** → à défaut (**~8 % de micro-bâti sans LiDAR**) **BD TOPO** (étages puis hauteur/3) → à défaut placeholder prudent. La colonne **`hauteur_source`** (`lidar` / `bdtopo` / `sans`) est écrite au run (ALTER + vue `parcel_residuel`).

### 2. SDP existante / restante

- `SDP existante = emprise bâtie (portion U/AU, correctif run 5) × niveaux existants × coef_sdp_existante`.
- `SDP restante = max(0, SDP autorisée − SDP existante)` — c'est `sdp_residuelle_m2`, la valeur que lisent la fiche, le Gabarit et le filtre Capacité.

**Coefficient de plancher `coef_sdp_existante = 0,95`** : l'emprise BD TOPO est l'emprise du **toit** (débords ~5 %) ; on la ramène à l'emprise de **plancher** pour rester sur la même convention de surface de plancher que le plafond `surface_plancher_m2` (= emprise de plancher × niveaux, sans coefficient par niveau). Volontairement proche de 1 : un coefficient plus agressif sur l'existant **seul** surestimerait le résiduel (asymétrie avec le plafond) — le biais même que ce lot corrige.

### 3. Golden — 55 parcelles Saint-Denis, avant / après

Fichier : `golden-55.csv` (script `scripts/donnees_fix1_golden.py`, lecture seule). Isolation exacte du lot C : mêmes parcelles, même emprise, même `sdp_max` ; **avant** = ancienne règle (BD TOPO seul, coef 1,0), **après** = LiDAR égout + coef 0,95.

- **42/55** constructibles (13 non constructibles). **19** voient leurs niveaux changer.
- Corrections dans **les deux sens** — la mesure remplace la déclaration :
  - LiDAR révèle **plus** de niveaux (existant sous-compté) → restant **baisse** : `AC0090` égout 8,1 R+1→R+2 restant 5 710 → 3 235 (**−2 475**) ; `HV0079` égout 5,3 R+0→R+1 1 877 → 749 (**−1 128**) ; `BL0179` 406 → 0.
  - LiDAR révèle **moins** de niveaux (BD TOPO sur-déclarait) → restant **monte** : `BZ0542` égout 4,1 R+1→R+0 478 → 792 (**+314**) ; `BZ0313` 61 → 213.
- **BZ1065** : égout **3,6 m** → **1 niveau** (`round(3,6/3) = 1`), `hauteur_source = lidar`. **Cohérent avec ses 10,3 m** : le 10,3 m est le **faîtage** (apex de toiture), pas 3 étages — l'égout (3,6 m) *et* BD TOPO (1 étage, 4,2 m) confirment un R+0 à l'égout. La règle égout ne crée donc **aucun** niveau fantôme ; SDP existante 193 → 183 (coef 0,95), restant 26 → 36 (le +10 est le seul coefficient de plancher). C'est le comportement correct : le volume de toiture n'est pas de la surface de plancher.

> Nuance de la prémisse du mandat : « BZ1065 lue R+0 → SDP restante surestimée » supposait que la hauteur mesurée ferait grimper les niveaux. La mesure **de l'égout** (celle qui compte pour les niveaux) confirme au contraire le R+0 ; c'est sur les bâtiments **sans** hauteur BD TOPO fiable, ou dont BD TOPO se trompe, que la correction opère (cf. golden + run ci-dessous).

### 4. Run de test — Saint-Denis (non servi), comparé au run 10

Commande (chronométrée, `--assiette-clippee` pour la même base que le run 10 servi « q_v15 assiette gabarit ») :

```
labuse compute-residuel --commune 97411 --new-run "DONNEES-FIX-1 test lidar Saint-Denis" --assiette-clippee
```

Résultat : **run 11**, 38 138 parcelles · **26 826 calculées** · 11 312 avec cause (terrain_exigu 9 523, zones non constructibles…) · **0 erreur** · **1 711 s** (~28,5 min).

Comparaison **run 11 vs run 10**, sur les **24 478 parcelles bâties** disponibles dans les deux runs (`hauteur_source` : lidar 24 153 · bdtopo 93 · sans 232 — le LiDAR sert 98,7 % des bâtis) :

| SDP restante | parcelles | médiane | moyenne | total |
|---|---:|---:|---:|---:|
| **baisse** (existant relevé) | **1 446** | −164 m² | −622 m² | **−899 090 m²** |
| monte (coef plancher + niveaux LiDAR < BD TOPO) | 6 966 | +15 m² | +135 m² | +940 370 m² |
| inchangée | 16 066 | — | — | — |
| **net** | | | | +41 280 m² |

- **1 446 parcelles bâties voient leur SDP restante baisser** — c'est la correction visée : l'égout LiDAR révèle un existant bâti en hauteur là où il était sous-compté (placeholder/BD TOPO). Baisses **grosses** (médiane −164, queue jusqu'à −33 366 m²), pour **−899 090 m²** de droits résiduels retirés à tort.
- Les **6 966 hausses** sont **petites** (médiane **+15 m²**) : coefficient de plancher 0,95 (emprise-toit → plancher) + les cas où le LiDAR mesure **moins** de niveaux que BD TOPO ne déclarait (BD TOPO sur-déclarait). Le **net** est quasi neutre (+41 280 m²) : le résiduel est **redistribué vers l'exactitude**, pas gonflé ni rogné en bloc.
- **3 663 parcelles (15,0 %) changent de bande de potentiel** (fort/modéré/faible/nul, l'entrée résiduel-driven de q_v15).

**10 plus gros écarts (baisses)** — tous expliqués par la hauteur mesurée (l'égout révèle plusieurs niveaux existants) :

| IDU | égout | faîtage | source | restant run 10 | restant test | écart |
|---|---:|---:|---|---:|---:|---:|
| 97411000AB0012 | 12,8 | 33,8 | lidar | 33 366 | 0 | −33 366 |
| 97411000DE0210 | 19,8 | 33,0 | lidar | 32 156 | 0 | −32 156 |
| 97411000BN0537 | 10,4 | 20,7 | lidar | 30 741 | 0 | −30 741 |
| 97411000BP0897 | 13,4 | 21,3 | lidar | 19 586 | 0 | −19 586 |
| 97411000HM0284 | 7,4 | 12,0 | lidar | 17 018 | 0 | −17 018 |
| 97411000BL0108 | 5,2 | 9,2 | lidar | 26 590 | 10 798 | −15 792 |
| 97411000BL0098 | 7,1 | 11,5 | lidar | 15 668 | 2 002 | −13 666 |
| 97411000BL0313 | 6,9 | 10,9 | lidar | 23 471 | 11 197 | −12 274 |
| 97411000HK0151 | 7,7 | 25,3 | lidar | 11 656 | 0 | −11 656 |
| 97411000BL0075 | 6,9 | 10,2 | lidar | 10 437 | 0 | −10 437 |

Chacun : un égout mesuré à 5–20 m (R+1 à R+6) contre le R+0/faible de run 10 → l'existant occupe désormais toute (ou presque) la capacité → le résiduel « fantôme » disparaît. Ce sont exactement les parcelles où le mandat diagnostiquait la surestimation.

- **BZ1065** : run 10 = 26 m² → run 11 = 36 m² (`hauteur_source = lidar`, pct_potentiel 88 → 84). Niveaux **inchangés** (égout 3,6 m → R+0, cf. §C3) ; la hausse de 10 m² est le seul coefficient de plancher. Aucun niveau fantôme créé par le faîtage de 10,3 m — **cohérent**.

> ⚠️ Run 11 est **non servi** (garde-fou : `is_served=false`). Il ne changera la fiche/le Gabarit/le filtre Capacité qu'après `residuel-serve` (geste de Vic, hors mandat). C'est pourquoi les captures « Potentiel après » ci-dessous montrent le changement de **badge** (live) mais la SDP encore issue du run 10.

### 5. Commande du run 11 pour Vic (île, la nuit, seul sur la machine)

```
labuse compute-residuel --ile --new-run "q_v16 lidar existant" --assiette-clippee
```

Puis (séquence habituelle, hors de ce mandat) : comparer run 11 / run 10 → `residuel-serve 11` → `run_qv15.py` → séquence finale. Si le sharding est disponible, lancer en 2 shards (comme run 8 « post-plu8-clip-2shard ») pour la durée.

---

## Vérification

- **tsc** (front) : exit 0. **build** (front) : ✓. **vitest** : 188/188.
- **pytest** ciblé (mandat : golden, residuel, fiche, gabarit, capacité + lots A/B) : **184/184** — dont `test_fiche_complete_200_avec_ligne_residuelle` (le test d'appel complet de la fiche) vert, `test_golden_run_servi`, `test_residuel(_runs)`, `test_proprietaire_historique`, `test_faisabilite1_capacite`, `tests/gabarit`.
- **11 tests neufs** : `test_donnees_fix1_discordance.py` (7, lot A) + `test_donnees_fix1_proprietaire.py` (5, lot B) ; `test_residuel.py` étendu (lot C, niveaux LiDAR + `hauteur_source`).
- **Endpoint fiche en direct** (API 8515) : `GET /parcels/97411000BZ1065?source=q_v11_m137` → **HTTP 200**, `le_bien.hauteur_discordante=false`, `ecart_egout_bdtopo_m=-0.6`, trois hauteurs servies ; `potentiel.hauteur_discordante=false`.
- **pytest complet** : **3 348 passés · 19 échecs · 64 skips**. Les 19 échecs sont **PRÉ-EXISTANTS** — prouvé en rejouant les mêmes tests sur le commit de base `df386bfc` (worktree jetable) : ils y échouent à l'identique (14 gardes de registre/vocabulaire/deps hors-DB + 5 gardes verrous/garanties sur base réelle). Aucune régression de ce mandat (les 3 348 passés incluent mes 12 tests neufs, d'où +13 vs base).

## Captures

- `captures/01-badge-avant-BZ1065.png` · `02-badge-apres-BZ1065.png` — badge fiche §Bâti (avant : badge « Sources discordantes » LiDAR 10,3 / BD TOPO 4,2 ; après : trois lignes libellées, plus de badge).
- `captures/07-badge-apres-aberration.png` — aberration `97418000AZ0128` (faîtage 53 401 m) : badge « faîtage physiquement impossible » (motif faîtage aberrant).
- `captures/03-identite-avant-SCI.png` · `04-identite-apres-SCI.png` — §Identité SCI Laurent Grandpre (avant : faux « SCI LAURENT GRANDPRE → SCI LAURENT GRANDPRE » ; après : « Propriétaire PM non identifiable (DGFiP) », 0 faux changement).
- `captures/05-potentiel-avant-BZ1065.png` · `06-potentiel-apres-BZ1065.png` — Potentiel/Capacité BZ1065 (marge en hauteur : avant badgée « discordantes », après non ; SDP restante issue du run 10 tant que run 11 n'est pas servi).

> Le fond de carte animé (maplibre) fait expirer le screenshot MCP (« MCP expire sur carte ») ; captures « après » produites par `scripts/donnees_fix1_captures.mjs` (node playwright, canvas masqué). Captures « avant » = celles de l'audit DONNEES-LIDAR-PROPRIO (état pré-fix).

## Hors mandat (non fait)

Servir un run · la bascule · la nature du toit · les autres usages du LiDAR · merger.
