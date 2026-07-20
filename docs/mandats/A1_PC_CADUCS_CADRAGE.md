# PHASE A cycle 2 — CADRAGE & BACKTEST « PC caducs »

**Branche `phaseA/pc-caducs` · Étape 1 · LECTURE SEULE.** Aucune écriture DB, run servi `q_v7_defisc`
(et `q_v6_m8` en hystérésis) intouché. Aucune identité de personne physique n'est stockée ni inférée : le
signal est **la parcelle et ses dates**, jamais le demandeur.

> **Verdict d'instruction.** Le signal **existe et le critère de GO est atteint**. Un PC octroyé jamais
> réalisé mute **1,62× plus** dans la fenêtre [+3,+6] ans que la même population de PC **réalisés** —
> OR **1,62 IC95 [1,34 ; 1,94]** (comparateur principal). Contre l'univers apparié sans PC : OR **1,54
> IC95 [1,28 ; 1,83]**. **Différence doctrinale avec le défisc** : signal **RÉTROSPECTIF** (un PC mort en
> 2019 prédit des mutations que le label courant voit) → **l'arène est juge de plein droit** à l'étape 2,
> pas d'exception forward. Couverture : **954 caducs dans l'univers scoré non-écarté** (7× le périmètre V
> défisc). Recommandation : **GO** vers badge + composante V (poids calibré pré-label).

---

## 3.1 Inventaire Sitadel & la fragilité n°1

| Table | Lignes | Rôle |
|---|---|---|
| `m10_permit_delais` | 50 290 | délais : `date_depot` (99,9 %), `date_autorisation` (100 %), **`date_achevement`/DAACT (41,3 %)** |
| `p_model_permits` | 58 945 | rattachement parcelle : `idu` (100 %), `type` (PC/PA/DP/PD), `date_autorisation` |
| `sitadel_permits` | 50 043 | source SDES : `raw.etat` (état), `raw.daact`, `idu_codes` |

**Profondeur** : autorisations **2013 → 2026** (~45 900 PC). **Rattachement** : `p_model_permits.idu` →
`parcels.idu`, 100 %, **44 875 parcelles distinctes avec ≥1 PC**.

**Fragilité n°1 — chiffrée AVANT tout.** La **DOC (ouverture de chantier) N'EXISTE PAS** dans nos données :
aucune colonne « début de travaux » nulle part. On ne peut donc **pas** distinguer directement « jamais
commencé » de « commencé non achevé ». Le seul témoin de réalisation est la **DAACT (achèvement)**, remplie
à **41,3 % sur l'ensemble** — MAIS l'état Sitadel `raw.etat` sauve le mécanisme :

| `etat` | sens | PC | DAACT |
|---|---|---|---|
| **6** | achevé | 20 099 | oui |
| **4** | accordé (non achevé) | 4 179 | non |
| **5** | rejeté | 10 983 | non |
| **2** | en instruction | 10 464 | non |

Parmi les PC **octroyés** (états 4 + 6 = 24 278), **83 % sont achevés** : la sous-déclaration DAACT est
concentrée sur les rejetés/en-instruction, pas sur les octroyés. Le **17 % restant (accordé jamais achevé)**
est notre gisement de caducs — un signal *porté par l'état Sitadel lui-même*, sans avoir besoin de la DOC.

## 3.2 Définition opérationnelle retenue

Au niveau **parcelle** (une parcelle peut porter plusieurs PC) :
- **réalisé** = ≥1 PC achevé (`etat=6` OU DAACT présent) ;
- **caduc probable** = **octroyé** (`etat∈{4,6}`) MAIS **aucun réalisé** → accordé jamais achevé, `Y+4`
  dépassé (marge d'un an au-delà des 3 ans légaux pour absorber les prorogations invisibles) ;
- **rejeté seul / en-instruction seul : EXCLUS** — pas de constructibilité prouvée.
- Cohorte `Y` = plus ancienne année d'autorisation octroyée de la parcelle.

**Contre-vérif bâti — testée, jugée FAIBLE (finding).** Croiser avec `p_model_bati.emprise_bati_m2` pour
« rattraper les DOC non déposées » **ne fonctionne pas proprement** : l'emprise est celle de la **parcelle
entière** (bâti préexistant compris, non datée) et 127 k parcelles n'ont pas de ligne bâti (→ faux « nues »).
Mesure : emprise médiane quasi identique **réalisés 135 m² vs non-achevés 125 m²**, ~30-35 % « nues » **dans
les deux groupes**. La variante « caduc ∩ nue » (§3.3) est **plus faible** (OR 1,40 < 1,62) — elle ajoute du
bruit, pas du signal. **Définition retenue = état Sitadel, sans contre-vérif bâti.**

## 3.3 Backtest à deux comparateurs

P(mutation de la parcelle dans **[Y+3, Y+6]**) ; cohortes **Y ∈ [2014, 2019]** (fenêtre ⊆ DVF 2014-2025) ;
OR + IC95 bootstrap (tirage binaire trié, seed 974, 2000 rééch.). `caduc=1 553`, `réalisés=12 172`.

| Comparateur | OR | IC95 | p_caduc (n) | p_réf (n) | Verdict |
|---|---|---|---|---|---|
| **(a) vs PC réalisés** *(principal)* | **1,62** | **[1,34 ; 1,94]** | .1005 (1553) | .0645 (12172) | ✅ **IC exclut 1, OR>1,5** |
| **(b) vs sans-PC apparié** (commune×surface×zonage) | **1,54** | **[1,28 ; 1,83]** | .1005 (1553) | .0675 (23502) | ✅ IC exclut 1 |
| (a') caduc ∩ « nue » vs réalisés | 1,40 | [1,06 ; 1,80] | .0878 (763) | .0645 (12172) | ⚠ plus faible (bâti = bruit) |

Le comparateur (a) est le plus exigeant — même population d'**intention prouvée**, seul le **destin** diffère
(réalisé vs abandonné) : il isole le signal « échec de projet ». Il passe nettement.

**Par cohorte** (p_caduc vs p_réalisé) — le signal est concentré **2016-2019** ; les cohortes **2014-2015
s'inversent** (petit effectif, fenêtre à cheval histo/récent DVF) :

| Y | caduc | réalisé |
|---|---|---|
| 2014 | .051 (177) | .076 (2250) |
| 2015 | .058 (189) | .070 (2013) |
| 2016 | **.093** (279) | .073 (1889) |
| 2017 | **.132** (326) | .052 (2023) |
| 2018 | **.119** (295) | .063 (1999) |
| 2019 | **.112** (287) | .053 (1998) |

## 3.4 Couverture

**Caducs probables actuels** (`Y ≤ 2022`, Y+4 dépassé) croisés au run servi `q_v7_defisc` :

| tier | caducs |
|---|---|
| écartée | 1 230 *(hors périmètre)* |
| **à creuser** | **863** |
| **chaude** | **47** |
| **réserve foncière** | **41** |
| **brûlante** | **3** |

→ **954 caducs dans l'univers non-écarté** (ce que l'arène peut physiquement voir) — **7× le périmètre V
défisc (131)**. Top communes : **Saint-Paul 174, Saint-Pierre 140, Le Tampon 87, Saint-Louis 74, Saint-Leu
64, Saint-Denis 53**. La donnée permis est **déjà exposée en fiche** (radar M10) : le badge s'y greffe.

## 3.5 Limites honnêtes

- **DOC absente** : « jamais commencé » est inféré de `etat=accordé ∧ non achevé`, pas observé.
- **Sous-déclaration DAACT** : un PC réellement construit mais DAACT jamais déposée apparaît en caduc
  (faux caduc). Atténué par le fait que 83 % des octroyés sont marqués achevés, mais résiduel réel.
- **Contre-vérif bâti inopérante** (emprise parcelle entière, non datée, 127 k lignes manquantes) — ne
  sépare pas réalisé/non-réalisé (finding §3.2).
- **Prorogations invisibles** : un PC prorogé (2×1 an) n'est pas caduc mais paraît vieux → la marge Y+4
  n'absorbe qu'une partie. Prudence des seuils.
- **Transferts de PC** : terrain vendu avec permis valide = **une mutation qu'on VEUT** (le signal la
  capte à raison), pas du bruit.
- **PC modificatifs** réinitialisent les délais (non modélisé).
- **Périmètre** : **PC seuls** (les PA/permis d'aménager exclus à ce stade). Passoires DPE F/G = challenger
  suivant, procès séparé ; nos croisements bâti/DPE ne les servent pas ici.
- **Inversion 2014-2015** (§3.3) : à surveiller ; l'anti-leakage (§3.6) l'évite mécaniquement.

## 3.6 Proposition d'intégration

**Badge** (table additive, ex. `pc_caducs`) — wording **factuel, jamais accusatoire** :
> « PC autorisé 2019 · jamais commencé · caduc probable » — autorisation **Sourcé** (Sitadel), caducité
> **Estimé** (inféré). **Jamais** « échec/abandon du propriétaire », jamais une date de vente, jamais le
> demandeur. Greffé sur le **bloc permis M10** existant de la fiche.

**Composante V** (challenger dérivé de `q_v7_defisc`, même montage structurel que défisc : **triplet gelé
verbatim**, V module le seul rang `p_raw`, plafonné, restreint aux **954 non-écartés**) — donc le signal
seul ne franchit **jamais** un seuil de tier (gate boussole 0/64 par construction).

**Anti-leakage (impératif)** : le **poids** de V est calibré **UNIQUEMENT sur les cohortes pré-label** —
celles dont la fenêtre [Y+3,Y+6] se **termine avant** l'année d'évaluation de l'arène (~2025), c.-à-d.
cohortes `Y ≤ 2018` (fenêtres ≤ 2024). **Jamais** calibrer sur les mutations 2025 que l'arène jugera. Ceci
évite aussi l'artefact d'inversion 2014-2015 (on calibre sur 2016-2018, le cœur du signal).

**Verdict d'étape 2 = l'arène, juge de plein droit** : ΔRR apparié IC95 excluant zéro (≈ +0,9 pt) contre
`q_v7_defisc`, gate boussole 0/64 trois axes, ECE non dégradée, churn commenté. **Pas d'exception forward.**
Si l'arène rejette avec churn ~0 % (pointe insensible, symptôme vu sur défisc), c'est signalé comme
diagnostic — mais **le rejet compte**, sauf décision explicite de Vic (doctrine : exception documentée,
jamais implicite). Avec 954 non-écartés touchés dont 51 déjà en chaude/brûlante/réserve, la pointe top-1158
devrait bouger davantage que sur défisc — l'arène a une vraie chance de voir le signal.

---

### Critère de GO (décision Vic)
- **OR ≥ ~1,5, IC excluant 1, comparateur (a)** : ✅ **1,62 [1,34 ; 1,94]** (et (b) 1,54 [1,28 ; 1,83]).
- **Couverture non anecdotique dans le non-écarté** : ✅ **954 parcelles**.

**Recommandation : GO vers l'étape 2.** Signal rétrospectif propre, jugeable par l'arène, couverture 7× le
défisc. Étape 2 seulement après GO explicite.

### Repro
```bash
python scripts/pc_caducs_backtest.py     # reports/pc-caducs/backtest.json + tables (seed 974, reproductible)
```
Lecture seule ; `dbname=labuse user=openclaw` ; définition caduc = état Sitadel (accordé jamais achevé).
