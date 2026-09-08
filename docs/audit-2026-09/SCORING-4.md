# SCORING-4 — ré-entraînement `q_v14` (les deux améliorations combinées)

**Nature** : ré-entraînement + run candidat. **Aucune promotion, aucune bascule, aucun merge.**
Le run servi reste `q_v11_m137` (`config/served_run.txt`) jusqu'à décision de Vic.
Branche `feat/scoring-4`, worktree `~/Desktop/labuse-scoring4`. Modèle CC : Fable (rédigé ici par Opus 4.8).

---

## Étape 0 — les deux réserves tranchées AVANT tout calcul

`pwd` = `/Users/openclaw/Desktop/labuse-scoring4` · branche = `feat/scoring-4` · arbre **propre** (vérifié).

### Réserve 1 — le pipeline sait-il réutiliser la cascade d'un run existant sous un nouveau `run_id` ?

**OUI. Réserve levée, sans rejeu de cascade.**

- Le pipeline expose un override **non destructif** dédié exactement à ce besoin :
  `src/labuse/scoring/p_v2/pipeline.py:366-369` —
  > « M8a — override NON DESTRUCTIF pour scorer un run CANDIDAT sur SA propre cascade sans
  > toucher la constante servie : `LABUSE_ETAGE0_RUN` (défaut = `Q_A_RUN_LABEL`). Utilisé
  > uniquement en batch candidat, jamais en prod. »
  ```python
  etage0_run = os.environ.get("LABUSE_ETAGE0_RUN", runs.current())
  ```
- L'étage 0 est lu depuis la cascade **déjà persistée** du run cité, pas recalculé :
  `src/labuse/scoring/p_v2/pipeline.py:370-374` — `SELECT p.idu FROM dryrun_parcel_evaluations d …
  WHERE d.run_label = :run AND d.status IN ('exclue','faux_positif_probable')`.
- `run_score_v2(session, *, run_id=…)` accepte un `run_id` explicite libre et refuse un doublon :
  `src/labuse/scoring/p_v2/pipeline.py:239-269` (`q_v14` sera donc accepté).
- **Précédent d'usage** identique : `qa/ponderation/mesure_ablanc.py:32` pose
  `LABUSE_ETAGE0_RUN = "q_v8_calibre"` puis score deux candidats sur cette cascade partagée.
- **Preuve en base** (base locale `labuse`) que la cascade de `q_v13_sources1` est bien là et
  réutilisable telle quelle :
  - `p_score_v2_runs` : `q_v13_sources1` présent (431 663 parcelles, `computed_at` 2026-09-07) ;
  - `dryrun_parcel_evaluations WHERE run_label='q_v13_sources1'` → **150 260 exclusions**
    (= 145 882 du servi `q_v11_m137` **+ 4 378 neuves**) sur 431 663 lignes. Les 4 378 exclusions
    neuves de SOURCES-1 sont donc dans l'étage 0 réutilisé, exactement le point de départ voulu.

→ `q_v14` repartira de l'étage 0 de `q_v13_sources1` via `LABUSE_ETAGE0_RUN=q_v13_sources1`.
**Coût du rejeu évité** : un `flux-run` complet (cascade sur 24 communes / 431 663 parcelles) se
compte en **heures** (`docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-1.md`, décision n° 16 ; `src/labuse/cli.py:668`).
Seul le scoring (P, tiers/rangs, contributions) est rejoué.

### Réserve 2 — les 22 sources de SOURCES-1 ont-elles ajouté des colonnes au dataset d'apprentissage ?

**NON. Réserve levée. Le rebuild features NE double PAS le temps.**

- SOURCES-1 n'a touché **que la cascade**, jamais le modèle :
  `docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md:363-364` —
  > « Recette scoring **inchangée** (m36 servie) : le run ne change QUE la **cascade** (les
  > nouveaux motifs SOURCES-1), **pas le modèle P**. »
- Les variables candidates issues des 22 sources (RPG canne, division récente DFI, vacance/âge
  IRIS) ont été **notées pour le banc K0 seulement**, jamais branchées :
  `docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md:135` et `:257` — « Rien au modèle sans banc ».
- Le dataset d'apprentissage a des **colonnes figées en dur**, non dérivées des sources :
  `src/labuse/scoring/p_model/ext_sql.py:150-287` (`build_ext_dataset`, SELECT explicite) et
  `src/labuse/scoring/p_model/sql.py:318-334` (`build_static`) ; le registre de features est une
  liste statique `FEATURES` : `src/labuse/scoring/p_model/features.py:40-151`.
- Le mandat lui-même acte que les 22 sources n'entrent pas dans `q_v14`
  (`docs/audit-2026-09/MANDAT-SCORING-4.md:49`).

→ Le rebuild du dataset reste au coût **habituel** : il n'est agrandi que des **4 variables neuves
prouvées par SCORING-DONNÉES-1** (`nu_asof`, `pct_bati_secteur_asof`, PC-de-PM, ancienneté PLU,
ventes PM secteur à surveiller) — pas des 22 sources. Pas de doublement.

### Verdict Étape 0

**Aucune des deux réserves ne bloque.** J'exécute le mandat. `q_v14` portera EN MÊME TEMPS
les gains de MODÈLE de `q_v12` (K2/K3/K4bis/isotonique par segment, rejoués) et les gains de
DONNÉES de `q_v13_sources1` (cascade + 4 378 exclusions, réutilisées via `LABUSE_ETAGE0_RUN`),
plus les 4 variables as-of de SCORING-DONNÉES-1. Le contrôle du manifeste (features q_v12 ∧
données/cascade q_v13_sources1 toutes présentes) sera fait et rapporté.

---

## Résultat d'ensemble (Étapes 1 → 7)

**Verdict : `q_v14` dépasse le servi ET q_v12 sur toute la tête, sans dégrader aucun
segment. Le candidat porte bien les DEUX améliorations.** Rien n'est promu ;
`q_v11_m137` reste servi (bascule = geste de Vic, `golden promote`).

Contrôle central du mandat (vérifié sur `reports/q-v14/FREEZE-q_v14.json`) :
- **features de MODÈLE q_v12** : toutes présentes (K1c censoring, K2 mortes retirées,
  K3 résiduel, K4bis voisinage, iso par segment) — 0 manquante ;
- **variables de DONNÉES as-of** : les 5 présentes (`nu_constructible_asof`,
  `pct_bati_secteur_asof`, `pc_pm_sur_parcelle_pp_36m`, `anciennete_plu_annees`,
  `ventes_pm_secteur_36m`) ;
- **cascade de `q_v13_sources1`** : réutilisée au run (`LABUSE_ETAGE0_RUN`), 150 260
  écartées servies (= 145 882 + 4 378). 35 features, 4 croisements.
  sha256 12m `214a1207…` / 24m `31f2b512…`.

### LE tableau (format SCORING-2) — modèle vs données vs les deux

| métrique | `q_v11_m137` (servi) | `q_v12` (modèle seul) | `q_v13_sources1` (données seules) | `q_v14` (les deux) |
|---|---|---|---|---|
| AUC K0 (2025) | 0,613 | 0,620 | 0,613 | **0,626** |
| préc@100 méd K0 | 0,060 | 0,080 | 0,060 | **0,080** |
| lift décile K0 | 2,06 | 2,27 | 2,06 | **2,27** |
| Priorité préc K0 | 0,137 | 0,076 | 0,137 | **0,305** |
| ECE global K0 | 0,0013 | 0,0022 | 0,0013 | 0,0020 |
| ECE PM K0 | 0,0063 | 0,0049 | 0,0063 | **0,0045** |
| brûlante (run 2026) | 111 | 92 | 96 | 92 |
| chaude (run 2026) | 1 367 | 1 133 | 1 173 | 1 114 |
| réserve foncière | 8 789 | 6 471 | 9 150 | 5 997 |
| cascade disponible (exclusions) | 145 882 | 145 882 | **150 260** | **150 260** |
| écartées servies par le run | 145 882 | 145 882 | 145 882 | **150 260** |

**Ce qui vient du modèle** se lit sur les lignes K0 : q_v12 gagne sur le servi (AUC
0,613→0,620), q_v14 gagne encore (0,626). **Ce qui vient des données** se lit sur la
cascade : `q_v13_sources1` porte les +4 378 exclusions de SOURCES-1, que `q_v14`
réutilise. `q_v14` combine les deux : meilleures métriques K0 **et** cascade élargie.

> Nuance de fidélité : le run `q_v13_sources1` a été scoré par SOURCES-1 sur l'étage 0
> **servi** (sans l'override) — sa cascade neuve (150 260) ne vivait que dans
> `dryrun_parcel_evaluations`. `q_v14` l'a explicitement réutilisée : ses écartées
> servies sont bien 150 260 (preuve de la combinaison données+modèle).

### Walk-forward 6 plis (comme l'artefact servi) — RR@1158 hors copro

| pli (test) | `q_v14` | `q_v12` |
|---|---|---|
| 2020 | 9,84 | 9,95 |
| 2021 | 8,34 | 8,11 |
| 2022 | 9,71 | 9,49 |
| 2023 | 9,30 | 8,74 |
| 2024 | 10,82 | 10,12 |
| 2025 | **8,38** | 7,35 |

`q_v14` : min 8,34 · max 10,82 · médiane 9,51 — dans/au-dessus de la plage de
référence m36 (6,9–11,0), supérieur à `q_v12` sur **5 plis sur 6**. Sur le pli le plus
récent (2025), `q_v14` (8,38) dépasse `q_v12` (7,35) et le servi m36 (6,73).

### Les paliers — effectifs, île et Saint-Paul (97415)

| run | zone | brûlante (Priorité) | chaude (À suivre) | réserve foncière |
|---|---|---|---|---|
| servi | île | 111 | 1 367 | 8 789 |
| servi | Saint-Paul | 21 | 264 | 1 251 |
| `q_v14` | île | 92 | 1 114 | 5 997 |
| `q_v14` | Saint-Paul | 13 | 181 | 826 |

*Réserve foncière 8 789 → 5 997 (corrigé PALIERS-1 A0, point 3)* : la réserve est un
bucket **relatif** — top-décile de SDP résiduelle **ET** p sous la médiane du run —, donc
q_v14 la recompose : en classant plus haut ces parcelles à forte capacité, il en fait
passer 3 083 (sur les 3 116 qui quittent la réserve) **au-dessus de sa médiane p**, où la
condition « p sous la médiane » ne tient plus ; 254 de plus sont écartées par la cascade
élargie — d'où la baisse nette.

*Précision par palier* : la précision réelle des paliers 2026 est par nature future
(ventes à 12 mois inconnues). La précision **mesurée** est celle du banc K0 (année
vierge 2025) : Priorité 13,7 % (servi) → **30,5 %** (`q_v14`) — le grand gain, porté
par le signal « permis d'un pro ». La tête `q_v14` est plus resserrée (92 brûlantes vs
111) : le modèle concentre la priorité sur des parcelles mieux étayées.

### Les 50 premières PAR RANG de `q_v14` face au servi

*(corrigé PALIERS-1 A0, point 2 : cette liste est triée **par rang** — le p le plus
fort —, pas « les 50 premières Priorité ». Un rang de tête peut être **déclassé** :
13 des 50 sont « Faible » (bâti saturé, etc.), gardées hors Priorité par la garde
actuelle malgré un p de tête — ex. 97416000CS0269, rang 3, p 0,60. C'est exactement
le cas que PALIERS-1 corrige : le déclassement devient un motif, la parcelle garde son
palier de probabilité.)*

`reports/q-v14/tableau5_top50.csv` — chacune avec ses trois raisons en français, sa
colonne `palier_q_v14` (visible : les 13 « Faible ») et son palier servi.
Extrait (rang q_v14 · IDU · rang servi · palier servi · raisons) :

| # | IDU | rang servi | palier servi | 3 raisons (FR) |
|---|---|---|---|---|
| 1 | 97416000ET2242 | 39 | Priorité | ancienneté du dernier permis · **un professionnel a déposé un permis sur cette parcelle détenue par un particulier** · permis à 100 m |
| 3 | 97416000CS0269 | 193 | Faible | ancienneté du dernier permis · **permis d'un pro** · piscine détectée |
| 8 | 97416000HN1803 | 1732 | À suivre | ancienneté du dernier permis · **permis d'un pro** · croisement mutation × permis |

**27 des 50 premières par rang** citent explicitement « un professionnel a déposé un
permis sur cette parcelle détenue par un particulier » : c'est le signal de
SCORING-DONNÉES-1 qui fait remonter des parcelles que le servi classait plus bas.

### Combien changent de palier — et lesquelles montent grâce au « permis d'un pro »

- **9 236 parcelles changent de palier** entre le servi et `q_v14`.
- **88 montent en Priorité** — **61 depuis À suivre, 27 depuis Neutre (a_creuser),
  jamais depuis une déclassée** (corrigé PALIERS-1 A0 : la garde de tête tient, une
  déclassée ne monte pas en Priorité même à p fort) — dont **87 sont portées par le
  signal « permis d'un pro »** (`pc_pm_sur_parcelle_pp_36m` positif dans leur top-5).
- Matrice de migration (servi → `q_v14`) : 84 Priorité→À suivre, 61 À suivre→Priorité,
  27 Neutre→Priorité — la tête est réordonnée, pas gonflée. *La matrice replie Faible/
  Neutre/Long terme dans « autre/à creuser » ; le détail granulaire (`montees_par_palier_
  servi` dans `tableau5_migration.json`) confirme : zéro montée depuis une déclassée.*

### Ce qui a été écarté et pourquoi

- **Étage 0 (cascade `q_v13_sources1`) : 150 260 parcelles** écartées du gisement — dont
  les 4 378 neuves fondées sur des servitudes réelles (EBC ≥ 80 %, ER ≥ 50 %, marchepied
  DPF 3,25 m, PEB A/B, réserves/APB). C'est le gain de DONNÉES, réutilisé sans rejeu.
- **Déclassées de tête** (gardes du pipeline, inchangées) : bâti saturé 122 198, non
  constructible 6 171, bâti révélé 5 333, zone fermée 2 765, AU 1 115.
- **`ventes_pm_secteur_36m` : GARDÉE** — le garde-fou ECE PM ne s'est pas déclenché
  (ΔECE PM = −0,0004 < 0,01 ; l'ECE PM s'améliore même : 0,0049 → 0,0045). Aucune autre
  variable n'a eu à sortir : aucun segment ne se dégrade de plus de 0,01.

### Garde-fous (mandat)

- **Test de fuite rejoué sur chaque variable neuve** : VERT. Voisinage égal à la source
  tronquée ; `pc_pm` et `ventes_pm` stables à l'ajout d'une année future ; `nu_asof`
  reconstruit l'état physique bâti/nu (permis/mutations datées), jamais la cible L2-F.
- **ECE par segment** : aucun segment ne se dégrade de plus de 0,01 vs q_v12.
- **Précision de tête** : elle DÉPASSE le servi (Priorité K0 13,7 % → 30,5 %, AUC
  0,613 → 0,626) — dit sans maquillage.
- **Coïncidence run/arène** : écart médian 1,9·10⁻⁷ (< 10⁻⁶), 0 parcelle hors norme.

### Libellés français (dictionnaire des contributions servi)

Les 4 (+1) variables neuves ont leur libellé FR dans `qv14.LIBELLES_QV14`, fusionné au
dictionnaire servi par le pipeline (`recette=q_v14`). Vérifié **dans le run réel** :
le top-5 stocké de la 1ʳᵉ brûlante affiche « un professionnel a déposé un permis sur
cette parcelle détenue par un particulier (+0,89) ». Une bascule afficherait donc des
phrases, jamais des noms de colonnes. Libellés :
- `nu_constructible_asof` → « terrain nu constructible » ;   <!-- corrigé PALIERS-1 A0 -->
- `pct_bati_secteur_asof` → « secteur peu bâti » ;   <!-- corrigé PALIERS-1 A0 -->
- `pc_pm_sur_parcelle_pp_36m` → « un professionnel a déposé un permis sur cette parcelle détenue par un particulier » ;
- `anciennete_plu_annees` → « ancienneté du PLU de la commune » ;
- `ventes_pm_secteur_36m` → « part des ventes du secteur parties à des sociétés ».

### Note de version

`reports/q-v14/NOTE-DE-VERSION-q_v14.md` (composée depuis les chiffres K0, jamais à la
main). En résumé : montent — la précision de tête (Priorité ×2,2), l'AUC, la calibration
PM ; descendent — rien de servi tant que Vic ne bascule pas ; churn de tête annoncé
franchement : **51,9 %** du top-1158 tourne vs le servi (**601 sorties du top-1158** par
rang ; **608 sorties de la tête servie** Priorité + À suivre = 1 478 — *pas* « de
Priorité », qui n'a que 111 parcelles ; corrigé PALIERS-1 A0), effet combiné du nouveau
modèle ET des 4 378 exclusions neuves.

---

## En passant — les 22 sources de SOURCES-1 comme variables futures (aucune n'entre dans `q_v14`)

Sans rien mesurer : lesquelles feraient de bonnes variables pour un PROCHAIN
ré-entraînement. Signal supposé · couverture · as-of possible.

| Source | Signal supposé | Couverture 974 | As-of possible |
|---|---|---|---|
| **DFI (filiation)** | division récente = mouvement foncier (fort) | 409 623 liens, 24 communes | **OUI** (dates de filiation) — meilleur candidat, déjà noté K0 |
| **RPG (canne)** | usage agricole = frein/friche | 12 464 parcelles canne | **OUI** (RPG annuel millésimé) — candidat, noté K0 |
| **IRIS RP2022** | vacance / âge du bâti / ménages | 344 IRIS, 24 communes | Partiel (RP ~5 ans) — candidat (vacance, âge), noté K0 |
| **Taux TFPB (REI)** | fiscalité communale (frein d'arbitrage) | 24/24 | **OUI** (millésimes annuels) — candidat maille commune |
| **Loyers OLL/DHUP** | rendement locatif (attractivité) | 16/24 mono-zone | **OUI** (millésimes) — candidat prix/zone |
| **Fibre Arcep** | viabilité/attractivité | 330 051 immeubles, 97,5 % FttH | OUI (trimestriel) — faible (quasi-uniforme 97,5 %) |
| **ORT / ACV / PVD** | dispositifs de revitalisation (Denormandie) | 19 communes, 13 ORT | Partiel (dates de signature) — maille commune |
| **Zones humides (DEAL)** | inconstructibilité/vigilance | 3 122 entités | Partiel (inventaires datés) — déjà porté par la cascade |
| **CASIAS / SIS** | pollution des sols | 453 / 4 | Partiel/NON (couverture faible pour SIS) |
| **Classement sonore** | nuisance (frein habitat) | 1 004 secteurs | NON (arrêté 2023, statique) — déjà en cascade |
| **Ravines DPF** | recul inconstructible | 275 tronçons | NON (arrêté 2006, statique) — déjà en cascade |
| **ER / EBC / SUP / PEB / DPU** | servitudes du droit des sols | GPU (un millésime) | **NON** (aucune archive de zonage géométrique) — déjà en cascade |
| **Zonage A/B/C (DHUP)** | tension logement (fiscalité) | 24/24 | Faible (arrêté daté, change rarement) — maille commune |
| **Potentiel foncier Région** | convergence gisement | 2 453 îlots | NON (estimation producteur, contrôle seulement) |
| **DVF Région / SAR / ZPPA** | contrôle / cadre / patrimoine | échantillon / proxy / nul | NON (figé 2021 / introuvable / injoignable) |
| **AZI / TRI** | risque inondation | 30 AZI / 9 TRI | NON (doublon de l'aléa déjà servi) |
| **Coût de construction** | chiffrage bilan | table sourcée | Annuel — contexte, pas un signal de vente |

**Meilleurs candidats pour un prochain ré-entraînement** (as-of net, couverture
suffisante, signal plausible) : **DFI/division récente**, **RPG canne/friche**,
**vacance IRIS**, et à la maille commune **TFPB** et **loyers OLL**. Tous notés au banc
K0 par SOURCES-1, aucun branché — et **aucun n'entre dans `q_v14`** (mandat).

---

## Reproduction (un commit + un cache par étape)

| Étape | Commit | Cache / artefact |
|---|---|---|
| 0 réserves | `8ad92a35` | — |
| 1 dataset | `25c27e9a` / `ca80637b` | `reports/q-v14/enrichi_2017_2026.pkl` (2,1 Go, gitignoré) + `reports/score-v2-arene/cache/` |
| 2 artefact | `b2d8aa93` | `reports/q-v14/artifacts-q_v14-{12m,24m}.joblib` + `FREEZE-q_v14.json` |
| 3 walk-forward | `27c8f318` | `reports/q-v14/q_v14_walkforward.csv` |
| 4 run | `76b5ff23` | run DB `q_v14` + `reports/q-v14/q_v14_verif.csv` |
| 5 arène | `7c781712` | `reports/q-v14/tableau5_*.{csv,md,json}` |
| 6-7 libellés + note | (ce commit) | `reports/q-v14/NOTE-DE-VERSION-q_v14.md` + ce rapport |

Rejeu : `q_v14_arene.py cache|fit|walk`, `run_qv14.py`, `q_v14_tableau.py`.
Chaque commande relit le cache de l'étape précédente ; on repart de la dernière
étape, jamais de zéro. **Aucun `promote`, aucune écriture `config/served_run.txt`,
aucun merge** — `q_v11_m137` reste le run servi jusqu'à décision de Vic.
