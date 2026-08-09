# ALGO-2 — Features propriétaire · Rapport (A : inventaire — POINT D'ARRÊT)

**Branche** `feat/algo2-proprio` (base main, aucun code de feature écrit — le mandat A
l'exige). Champion `q_v7_defisc` INTOUCHÉ ; tiers au bit près jusqu'à décision Vic.
**Note session : mandat « Modèle Fable », session exécutée sur Opus 4.8.**

## A — INVENTAIRE (mesuré en base, 26-27/07/2026)

| Source | Couverture réelle | Profondeur historique | AS-OF (anti-fuite) |
|---|---|---|---|
| **Panel DGFiP PM** `pm_proprietaires_millesimes` | 72 709 → 81 161 parcelles/an (**~19 % du frame** — le reste = personnes physiques, hors périmètre DGFiP-PM par construction) | **6 millésimes : 2019-2024** | ✅ **OUI** — propriétaire as-of 01/01/Y = millésime Y-1 → **les 6 folds walk-forward (2020-2025) sont TOUS couverts** ; 2017-2019 (train) → bin « inconnu » consigné, comme la fenêtre DVF |
| DGFiP PM courant `parcelle_personne_morale` | 82 701 parcelles (19,2 %) | millésime unique | ⚠ seul = fuite ; sert le SCORING 2026, le panel sert le train |
| **SIREN valide** (clé de C) | **~87 %** des lignes PM (≈10,4 k lignes/an sans SIREN → fallback dénomination, qualité à MESURER en C) | par millésime | ✅ |
| **BODACC** `bodacc_annonces_owner` | 1 418 annonces matchées propriétaires (volume FAIBLE — features rares) | **2008 → 2026, daté** | ✅ parfait (`date_annonce`) |
| **INPI/enrichment** `owner_enrichment` | 9 703 SIREN enrichis, `date_creation` **99,97 %** (immatriculation, dès 1900) | historique par construction | ✅ (immatriculation < 01/01/Y) |
| Groupes DGFiP (type détenteur) | PM non remarquables 33 921 · Commune 24 536 · HLM 7 681 · État 5 804 · SEM 4 128 · Dépt 3 960 · EP 2 213 | par millésime | ✅ |
| Dormance RNE (`date_mise_a_jour_rne`) | snapshot 2026 SEULEMENT | **aucune** | ❌ **non entraînable as-of** |
| Âge dirigeant (`v_pm_propension_vendre`) | 9 337 SIREN | — | ⛔ **BOUSSOLE : personne physique → écarté d'office** (`nb_dirigeants`, compte anonyme, reste licite) |
| Indivision structurelle | **0 signal trouvé** (cascade : 0 ; groupes DGFiP : pas de classe indivision) | — | ❌ inexistant |
| RNIC | 2 220 copros | — | déjà consommé (flag copro du modèle) |

### Part PM dans les 4 communes cibles (le plafond de l'espoir du mandat)

| Commune | Parcelles PM (2024) | % du parc |
|---|---:|---:|
| Saint-Denis | 11 639 | **30,5 %** |
| Saint-Paul | 12 260 | **24,0 %** |
| Le Tampon | 5 249 | **12,3 %** |
| Saint-Joseph | 3 472 | **12,0 %** |

Lecture honnête : le bloc propriétaire a une vraie portée à **Saint-Denis/Saint-Paul**
(au-dessus de la moyenne île 19 %) ; au **Tampon et à Saint-Joseph** — les deux communes
significativement faibles d'ALGO-1b — il ne touchera qu'**une parcelle sur huit**.
L'objectif « remonter les grandes » est plausible pour SD/SP, modéré pour Tampon/St-Joseph.

### Verdict d'inventaire par feature candidate (B)

| Feature | Verdict | Motif |
|---|---|---|
| B1 type détenteur (PM/public/HLM/SEM…) | **GO** | groupes DGFiP par millésime, as-of ✅ ; PP = absence (flag, pas d'identité) |
| B2 tenure fine (continue + bins fins) | **GO** | DVF ext 2014+ déjà as-of dans le pipeline |
| B3 multi-détention (portefeuille commune/île) | **GO sous condition C** | SIREN 87 % ; le solde exige la résolution d'entités (précision ≥ 95 % ou refus) |
| B4 ancienneté société (immatriculation) | **GO** | date_creation 99,97 % des 9 703 enrichis (≈77 % des SIREN propriétaires — solde en « inconnu ») |
| B5 dormance (dépôts de comptes / RNE) | **ÉCARTÉE** | aucune profondeur historique : `date_mise_a_jour_rne` = snapshot 2026 → entraîner dessus = fuite pure. (Réexaminable si l'INPI historisé est ingéré un jour.) |
| B6 détresse BODACC as-of | **GO prudent** | daté 2008-2026 ✅ mais 1 418 annonces → feature RARE (attendre peu du coefficient) |
| B7 indivision/succession | **ÉCARTÉE** | aucune donnée STRUCTURELLE en base ; la reconstruire passerait par du nominatif (⛔ boussole) |

**Écartées boussole/faisabilité, motifs gravés** : âge dirigeant (personne physique
identifiable) ; B5 (fuite temporelle) ; B7 (rien de structurel, nominatif interdit).

---

## ⛔ POINT D'ARRÊT (exigé par le mandat A)

L'inventaire est présenté AVANT tout code de feature. Si tu valides :
1. **C d'abord** : résolution d'entités (SIREN direct 87 % + dénomination normalisée pour
   le solde), échantillon vérifié à la main, **refus de servir sous 95 % de précision** ;
2. **B** : B1, B2, B3 (si C ≥ 95 %), B4, B6 — B5 et B7 écartées ;
3. **D** : re-train complet challenger, walk-forward 6 folds seed 974, RR@1158 hors copro
   + IC95 + ECE + signes + **RR par commune** (Tampon/St-Joseph/SP/SD), permutation,
   **ablation bloc propriétaire** (delta avec IC), arène + gate boussole golden ;
4. **E** : verdict honnête — pas de promotion sans ΔRR significativement > 0 ;
   la bascule reste ta décision.

Attente à cadrer dès maintenant (honnêteté) : couverture PM ~19 % île → le bloc ne peut
déplacer qu'une minorité de rangs ; l'effet le plus probable est à Saint-Denis/Saint-Paul.

---

## C — RÉSOLUTION D'ENTITÉS (validée : feu vert Vic sur A)

Mesure du gisement (millésime 2024) : 2 879 dénominations sans SIREN ; le rapprochement
par dénomination normalisée (upper, alphanumérique seul) vers les lignes à SIREN n'en
résout que **31 uniques** (+3 ambiguës multi-SIREN, rejetées d'office) — les sans-SIREN
sont massivement des entités qui n'apparaissent JAMAIS ailleurs avec un SIREN.

**Vérification EXHAUSTIVE à la main (32 paires — mieux qu'un échantillon)** : 32/32
littéralement exactes (variations d'apostrophes/espaces/sigles : « G F A CRATERE » =
« GFA CRATERE », « SICA LAIT » = « SICALAIT », Conservatoire du littoral avec/sans
apostrophe…). Risque résiduel identifié : les dénominations COURTES/GÉNÉRIQUES
(« WB », « DALY », « CORAIL », « SCI EMERAUDE »…) peuvent avoir des homonymes hors
panel — indétectable par construction.

**RÈGLE SERVIE (prudence mandat : « un portefeuille faux est un faux positif »)** :
1. SIREN strict (87 % des lignes PM) — confiance 1,0 ;
2. rapprochement dénomination SEULEMENT si normalisée **≥ 12 caractères** ET SIREN
   **unique** au panel (≈18 entités distinctives, toutes vérifiées exactes) ;
3. tout le reste (courtes, ambiguës, introuvables) → **« inconnu »** : jamais un
   portefeuille deviné.
**Précision mesurée : 32/32 = 100 % sur vérification exhaustive** (≥ 95 % exigé — OK) ;
la règle de longueur élimine la classe de risque homonyme résiduelle. Impact assumé :
~10,4 k lignes/an restent « inconnu » au multi-détention (bin réel, WoE propre).

---

## B + D — CHALLENGER : construction et mesure (27/07/2026)

**B construit as-of** (`algo2_prop_features`, préfixe dédié — champion intouché, zéro
ligne dans parcel_p_score_v2) : prop_type (catégories distinctes `non_pm` ≠ `inconnu`
panel — bin « inconnu » PROUVÉ vraie catégorie : effectif 1 294 989, WoE −0,074, test
unitaire 2/2), tenure_mois continue (100 % frame), portefeuille commune/île (résolution
C), ancienneté société, bodacc36 (590→3 301 TRUE/an — ≥ 200 au train ✓, précision n°4).
Protocole D = champion à l'identique (folds 2020-2025, train ≤ F-2, isotonique F-1,
C=5,0, 5 interactions gelées, seed 974).

### Walk-forward FULL (RR@1158 hors copro, IC95)

| Fold | Challenger | Champion | Δ |
|---|---|---|---|
| 2020 | 8,98 [7,47;10,09] | 9,41 | −0,43 |
| 2021 | 8,52 [7,44;9,59] | 8,61 | −0,09 |
| 2022 | 8,09 [6,91;9,17] | 8,63 | −0,54 |
| 2023 | 7,15 [6,12;8,28] | 7,30 | −0,15 |
| 2024 | 7,08 [5,94;8,33] | 7,08 | 0,00 |
| **2025** | **6,73 [5,53;7,87]** | **6,73 [5,53;7,84]** | **0,00** |

ECE 0,0012-0,0033 (calibration intacte). Aucun fold amélioré ; 2020-2022 légèrement
dégradés (bins « inconnu » pré-panel + variance ajoutée).

### Ablations fold 2025 (bootstrap APPARIÉ vs BASE) — la question n°2 de Vic

| Variante | RR | Δ vs BASE [IC95] |
|---|---|---|
| BASE (29 features champion) | 6,73 | — |
| **+ B2 tenure fine seule** | 7,07 | **+0,34 [−0,56;+1,02]** — seul frémissement, NON significatif |
| + bloc PM seul | 6,67 | −0,06 [−0,91;+1,07] — rien |
| FULL | 6,73 | +0,00 [−0,98;+0,96] — rien |

**Réponse à la question n°2 : le (maigre) signal vient de B2 — le bloc PROPRIÉTAIRE
n'apporte RIEN de mesurable.** Même B2 ne franchit pas la significativité.

### Arène-équivalente (fold 2025, out-of-sample des deux côtés)

- **Δ FULL − CHAMPION apparié : 0,00 [−0,98;+0,96] — NON significatif** (le critère
  d'avis exige une borne basse > 0) ;
- **churn top-1158 : 43 %** — une rotation massive de la réserve pour un gain nul,
  coût produit pur (budget d'arène : 25 %) ;
- permutation : RR 0,74 ≈ 1 ✓ (aucune fuite) ;
- **boussole** : 1 hit du PROXY top-1158 (97423000AB1341) — mais c'est une **étage-0**
  (cascade `exclue`) : dans le vrai pipeline l'étage 0 PRIME et elle ne peut JAMAIS
  devenir chaude, quel que soit son rang. Artefact du proxy (qui teste le rang, pas le
  tier), pas une violation réelle ; l'arène formelle sur run-candidat la testerait sur
  le TIER. Aucune autre négative factuelle au top.

### RR PAR COMMUNE (fold 2025, Δ apparié FULL−champion, k_c proportionnel)

| Commune | Champion | FULL | Δ apparié [IC95] |
|---|---|---|---|
| **Le Tampon** | 3,1 | 6,1 | **+3,06 [+0,48;+5,78] — SIGNIFICATIF** |
| Saint-Joseph | 2,5 | 4,1 | +1,65 [−1,74;+4,25] — ns |
| Saint-Paul | 4,6 | 5,0 | +0,42 [−1,68;+3,40] — ns |
| **Saint-Denis** | 3,8 | 2,5 | **−1,25 [−4,37;0,00]** — dégradation, borne haute à 0 pile |

Lecture prudente du +Tampon : (a) la moyenne île est STRICTEMENT inchangée — le gain
du Tampon est payé ailleurs (SD en tête) : une REDISTRIBUTION, pas une création de
signal ; (b) 1 seul test significatif sur 4 (α=5 % → ~18 % de chance d'un faux positif
par multiplicité) ; (c) l'ablation montre que ni B2 ni le bloc PM ne portent d'effet
propre — le mouvement communal vient de la recomposition d'ensemble, fragile par
nature. On ne promeut pas un modèle sur ce fondement.

---

## E — VERDICT : NE PAS PROMOUVOIR

Le challenger ne bat pas le champion : **Δ île = 0,00 pile [−0,98;+0,96]**, aucun fold
amélioré, **aucun apport propre du bloc propriétaire** (−0,06 en ablation), et un
**churn de 43 %** qui, à gain nul, n'est que du coût (clients qui verraient leur
réserve tourner sans raison). Le seul point significatif (+3,06 au Tampon) est une
redistribution non expliquée par les features testées, contredite par la dégradation
symétrique de Saint-Denis — pas un fondement de bascule.

**Le mandat le prévoyait : « un mandat qui conclut ça n'apporte rien est un mandat
réussi. »** C'est le cas. L'attente était d'ailleurs cadrée dès l'inventaire :
couverture PM ~19 % île, 12 % là où on espérait remonter.

**Recommandations motivées (aucune bascule — décision Vic)** :
1. **NE PAS PROMOUVOIR** ce challenger ; le champion `q_v7_defisc` reste servi tel quel.
2. **B2 (tenure continue)** : seul frémissement (+0,34 ns, 100 % du frame) — candidate
   à retester SEULE au prochain RE-TRAIN ANNUEL prévu par la politique de recalibration
   (jamais une bascule dédiée pour un effet non significatif).
3. Tampon/Saint-Joseph : confirmer la piste déjà actée par Vic — **voisinage
   hyper-local, mandat suivant** ; ce mandat établit leur base chiffrée (3,1 / 2,5).
4. Actifs réutilisables du mandat : la résolution d'entités C (100 % vérifiée) et la
   table as-of `algo2_prop_features` restent disponibles pour tout usage descriptif
   (fiche propriétaire, portefeuille affiché) — leur inutilité PRÉDICTIVE n'enlève
   rien à leur valeur PRODUIT éventuelle.

**Écartées (récapitulatif, motifs gravés)** : âge dirigeant (⛔ boussole personne
physique) ; B5 dormance (snapshot 2026 = fuite) ; B7 indivision (rien de structurel).

*Incident consigné : 3e collision de session concurrente dans ce clone (checkout main
pendant le run de fond — script disparu du worktree, complément relancé). La
recommandation « un clone/worktree par mandat simultané » devient pressante.*
