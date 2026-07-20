# PHASE A-1 — CADRAGE & BACKTEST « Fenêtre de tir : sortie de défiscalisation »

**Branche `phaseA/a1-defisc` · Étape 1 · LECTURE SEULE.** Aucune écriture DB, aucun re-scoring, run
servi `q_v6_m8` intouché. Aucune identité de personne physique n'est stockée ni inférée : le signal est
un **timing par parcelle** (« entre dans une fenêtre de sortie »), jamais une personne.

> **Verdict d'instruction (résumé exécutif).** Le mécanisme **existe et est prouvé rigoureusement** : au
> niveau du **lot appartement** (surface-matché, contamination retirée), un logement acheté neuf (VEFA)
> revend **≈ 6× plus** qu'un appartement ancien comparable dans la fenêtre +6/+11 ans — OR **5,96**
> IC95 [5,15 ; 6,90] sur [+6,+8] et OR **6,22** IC95 [4,24 ; 9,62] sur [+9,+11]. **MAIS** : ce signal
> significatif vit dans l'**appartement/copropriété**, où le niveau parcelle n'est **pas actionnable**
> (revendre un lot ne rend pas la parcelle acquérable). La tranche **actionnable — maisons /
> monopropriété** — montre la **même direction** (creux à +5, bosse à +6, plateau élevé +8..+11 ;
> OR +9 = 2,29) mais **ne peut pas atteindre la significativité** (n = 107 maisons neuves dont la fenêtre
> +9 est observable : DVF ne remonte qu'à 2014). Couverture prospective actionnable : **578 maisons/mono**
> portent une fenêtre active 2026-2028 (+ 154 copro) — **au-dessus de l'anecdote, en-deçà de l'arme**.
> Recommandation : **GO conditionnel** vers un **badge tracé + composante V plafonnée, restreinte au mono**,
> avec une réserve méthodologique forte (§7) — *l'arène RR ne peut pas valider un signal forward*.

---

## 1. Données & proxy « acquisition neuf »

### 1.1 Sources (lecture seule)

| Rôle | Table | Plage | Lien parcelle |
|---|---|---|---|
| Timeline mutations (ancienne) | `dvf_mutations_histo` | **2014–2020** | `id_parcelle` direct (varchar 14) |
| Timeline mutations (récente) | `dvf_mutations_parcelle` | **2021–2025** | `id_parcelle` direct — DVF récent déjà résolu à la parcelle |
| Label « achat neuf » (direct) | `nature_mutation = 'Vente en l'état futur d'achèvement'` (VEFA) | — | — |
| Proxy achèvement | `p_model_permits` (PC) ⋈ `m10_permit_delais.date_achevement` | 2013–2026 | `idu` ; **41 %** des permis ont une date d'achèvement |
| Copro / mono | `p_model_ext_copro (copro_rnic, copro_dvf)` | — | `idu` ; **mono = les deux false (99,2 %)** |

L'**union directe** `histo ∪ parcelle` (schémas identiques) reconstitue une **timeline continue 2014–2025**
par parcelle. C'est ce qui rend le mécanisme testable : une VEFA 2014-2016 observe alors pleinement sa
fenêtre +9 (2023-2027) dans la table récente.

### 1.2 Proxy retenu

Deux définitions de « acquisition neuf », par ordre de propreté :

1. **VEFA (étalon).** `nature_mutation = 'Vente en l'état futur d'achèvement'` **EST** un achat sur plan =
   logement neuf, sans aucune inférence. C'est le proxy principal. Bien plus propre que « ≤ 3 ans après
   achèvement ». Effectifs 2014-2020 : **1 760 mono**, **3 249 copro**.
2. **Permis ≤ 3 ans (complément).** `Vente` d'un logement dont la parcelle a un PC achevé dans les 3 ans
   précédents. Ajoute **402 mono** / **322 copro**. Sert surtout à ne pas manquer les maisons neuves
   achetées peu après livraison (hors VEFA enregistrée).

**Strate ancien** = `Vente` sans permis récent (pas de PC, ou achèvement > 5 ans avant l'achat). La
zone grise 3-5 ans est **exclue** pour ne pas polluer le contraste.

### 1.3 Neutralisation d'un artefact décisif (période de grâce)

Diagnostic : **821 / 1 063** VEFA-mono avec un « événement suivant » l'ont **à moins de 6 mois**, **ratio de
prix B/A = 1,00**. Ce ne sont **pas des reventes** : c'est l'acte de livraison VEFA (signature sur plan puis
acte définitif, même prix). Les vraies reventes se massent à **[5,7) ans** (ratio prix **0,68** — revendu à
68 % du prix neuf : « acheté pour l'avantage fiscal, pas pour durer »). → **Grâce de 2 ans** appliquée
**symétriquement** aux deux strates : une revente n'est comptée qu'au-delà de +2 ans. Sans cette correction,
le lift maison tombe artificiellement à ~1,2 (l'acte de livraison consomme le créneau de revente).

### 1.4 Couverture & trous (honnêteté)

- **Troncature 2014.** DVF ne remonte pas avant 2014. Les **plus grosses vagues défisc — Girardin
  (≲ 2012), Scellier DOM (2009-2012)** — sont **invisibles côté acquisition**. On teste donc la **queue**
  (ère Duflot/Pinel), pas le pic. Conséquence directe : seules les cohortes **2014-2016** observent une
  fenêtre +9 → **n = 107 maisons neuves** pour ce test. C'est la cause première du manque de puissance.
- **Achèvement 41 %.** Le proxy permis sous-compte les maisons neuves sans date d'achèvement.
- **DPE inutilisable pour le volume** : `dpe_records` = 914 lignes (0,2 % du parc) → bon pour des
  spot-checks d'année de construction, pas pour stratifier.
- **VEFA = quasi exclusivement appartement + dépendance** (copro). Maison-VEFA ≈ 137 parcelles sur 7 ans.
  Le neuf défiscalisé à La Réunion **est** de l'appartement — d'où toute la tension actionnabilité (§5).

---

## 2. La courbe à bosses (livrable central)

Graphique : **`reports/a1-defisc/courbe_bosses.svg`** (2 panneaux). Table sous-jacente :
`reports/a1-defisc/backtest.json`. Hazard discret annuel = P(revente dans l'année | survie à l'entrée de
l'année), table de mortalité avec censure au 31/12/2025. Lecture à partir de **+3** (la grâce masque +1/+2).

### 2.1 Maisons / monopropriété (tranche actionnable)

| +ans | 3 | 4 | 5 | **6** | 7 | 8 | **9** | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|
| **neuf** | .066 | .014 | **.007** | **.039** | .021 | .030 | .020 | .033 | .031 |
| ancien | .032 | .025 | .024 | .024 | .022 | .021 | .019 | .015 | .014 |
| ratio | 2,0 | 0,5 | 0,3 | **1,6** | 1,0 | 1,4 | 1,0 | 2,1 | 2,2 |

Signature nette : **creux à +5** (le bien est verrouillé par l'engagement), **bosse à +6** (Girardin/Pinel
6 ans), **plateau élevé +8..+11** (Scellier/Duflot/Pinel 9 ans + délai de mise en marché). La forme est
exactement celle attendue si le mécanisme existe.

### 2.2 Appartements lot-level (surface-matché) — preuve propre du mécanisme

On suit un **appartement précis** (parcelle + type Appartement + surface ±15 %) au lieu de la parcelle
entière, ce qui retire la contamination « un autre lot de l'immeuble se vend ». n_neuf = 3 536, n_anc = 32 280.

| +ans | 3 | 4 | 5 | **6** | 7 | 8 | **9** | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|
| **neuf VEFA** | .161 | .088 | .043 | .066 | .195 | .281 | .336 | .359 | .262 |
| ancien | .416 | .200 | .148 | .193 | .174 | .157 | .137 | .134 | .135 |

Les deux courbes **se croisent** : l'ancien revend tôt (churn normal) et décline ; le neuf, verrouillé
jusqu'à +5, **monte en flèche à partir de +7** et reste **2 à 2,7× au-dessus** de l'ancien jusqu'à +11.
C'est la rampe d'expiration d'engagement, sans ambiguïté.

---

## 3. Lifts chiffrés + IC95 (bootstrap apparié par tirage, seed 974, 2000 rééch.)

P(revente dans la fenêtre) neuf vs ancien, **cohortes dont la fenêtre est observable** (censure ≥ borne haute) :

| Population | Fenêtre | Cohortes | OR | IC95 | p_neuf (n) | p_anc (n) | Significatif |
|---|---|---|---|---|---|---|---|
| **Appartement lot** | [+6,+8] | 2014-17 | **5,96** | **[5,15 ; 6,90]** | .328 (1430) | .076 (6458) | ✅ |
| **Appartement lot** | [+9,+11] | 2014-16 | **6,22** | **[4,24 ; 9,62]** | .160 (407) | .030 (1349) | ✅ |
| Copro (parcelle) | [+6,+8] | 2014-17 | 13,61 | [11,32 ; 16,69] | .304 (1138) | .031 (5949) | ✅ *contaminé* |
| Copro (parcelle) | [+6,+11] | 2014-16 | 10,12 | [7,11 ; 14,92] | .437 (222) | .071 (1180) | ✅ *contaminé* |
| **Mono maison** | [+9,+11] | 2014-16 | **2,29** | [0,76 ; 4,40] | .065 (107) | .030 (2053) | ❌ *sous-alimenté* |
| **Mono maison** | [+6,+11] | 2014-16 | **1,63** | [0,88 ; 2,64] | .159 (107) | .104 (2053) | ❌ *sous-alimenté* |
| Mono maison | [+6,+8] | 2014-17 | 1,21 | [0,76 ; 1,74] | .052 (501) | .043 (9432) | ❌ |

**Lecture.** Le lift ≥ 1,5× dont l'IC95 exclut 1 **existe et est massif** — mais dans l'**appartement**
(preuve du mécanisme) et la **copro** (contaminée, non actionnable). La tranche **actionnable (maison)** a le
bon signe partout (OR 1,2 → 2,3) mais **ne franchit jamais** l'IC-exclut-1 : purement un problème de taille
d'échantillon (n = 107 pour +9, imposé par la troncature DVF 2014).

---

## 4. Couverture prospective (fenêtre active 2026-2028)

Parcelles de l'univers scoré dont la dernière acquisition neuf (VEFA ou Vente ≤ 3 ans après achèvement)
tombe en 2015-2020, si bien que [+6,+8] ou [+9,+11] recoupe **2026-2028** :

| Classe | Parcelles neuf identifiées | **Fenêtre active 2026-2028** |
|---|---|---|
| **Mono (actionnable)** | 1 166 | **578** |
| Copro (non actionnable en l'état) | 309 | 154 |

Top communes (mono, fenêtre active) : **Saint-Paul 102, Saint-Pierre 98, Saint-Leu 86, La Possession 41,
Saint-Denis 36, Saint-Joseph 33, Le Port 30, Saint-Benoît 22, Le Tampon 16**. Concentration cohérente avec
les pôles de locatif neuf de l'Ouest/Sud.

**578 parcelles actionnables** : ce n'est **pas une anecdote** (> 200), mais ce n'est **pas encore une arme**
(≪ « plusieurs milliers »). C'est un **signal compagnon** ciblé. Note : Pinel a couru jusqu'à fin 2024, donc
le gisement **grossit mécaniquement** vers 2027-2033 (les cohortes 2018-2024 entreront à leur tour) —
c'est un outil de moyen terme, pas un one-shot 2026.

---

## 5. Décision copropriété (tranchée)

**Le signal servi est restreint aux maisons individuelles / monopropriétés** (`copro_rnic = false ET
copro_dvf = false`, 99,2 % du parc). Raisons :

1. **Acquérabilité.** Une vente d'appartement ne rend pas la parcelle acquérable ; le signal parcelle en
   copro n'est pas défini au sens du produit (prospection foncière).
2. **Contamination de mesure.** Au niveau parcelle, la copro a un hazard +1 quasi nul après grâce puis un
   churn permanent (un lot se vend toujours) : le « prochain événement » n'est pas la revente du logement
   suivi. Seul le **lot-level surface-matché** (§2.2) est propre — et il sert à *prouver le mécanisme*, pas
   à désigner une parcelle.
3. **Le mécanisme fort est en copro** — c'est justement pour ça qu'il faut le traiter à part.

**Piste future (hors A-1)** : « **copropriété dont de nombreux lots entrent en fenêtre simultanément** » —
signal **au niveau immeuble** (compter les lots VEFA d'une même copro dont l'engagement expire dans la même
fenêtre), potentiellement très fort (OR copro ≈ 10) et *actionnable autrement* (approche syndic / veille de
mise en marché groupée). À instruire comme frère A-1 ou en A-3, avec sa propre unité d'analyse.

---

## 6. Limites honnêtes

- **On teste la queue, pas le pic** : Girardin/Scellier (gros volumes ≲ 2012) invisibles (DVF 2014+).
- **Puissance maison** structurellement bornée par la troncature (n = 107 pour +9). Le signe est stable et
  positif sur toutes les fenêtres, mais l'IC ne se referme pas : **preuve directionnelle, pas certitude**
  sur la tranche actionnable.
- **Neuf ≠ défisc** : une résidence principale neuve (hors dispositif) revend aussi, ce qui **dilue** vers
  le bas notre lift — le vrai effet défisc est probablement **plus fort** que mesuré (biais conservateur).
- **Défisc revendue avant terme** (rupture d'engagement, revente anticipée) **avance** la bosse → floute
  la datation exacte. C'est pourquoi le signal doit rester une **fenêtre** (« 2026-2027 »), jamais une date.
- **VEFA = date de signature**, pas de livraison : la vraie horloge d'engagement démarre à l'achèvement
  (souvent +1 à +2 ans). La grâce de 2 ans absorbe l'essentiel mais **décale peut-être les bosses de +1 an**
  vers la gauche. Ne pas sur-interpréter le pic exact.

---

## 7. Proposition d'intégration **sans retrain** (roadmap : voie « signal V »)

> **Réserve méthodologique majeure — à lire avant l'étape 2.** L'arène juge le classement contre les
> **mutations réalisées ~2025** (label M3.6). Or la fenêtre de tir **prédit 2026-2028**. Les deux sont
> **temporellement orthogonaux** : un signal *forward* correct ajoute au top des parcelles qui — à raison —
> **n'ont pas encore muté**, ce que le label 2025 lit comme des **faux positifs**. **L'arène RR@1158 ne peut
> donc pas récompenser ce signal** ; au mieux elle le voit neutre, au pire elle le pénalise. Ce n'est pas un
> échec du signal, c'est une **inadéquation de l'instrument** (même famille que la réconciliation RR in-sample
> de J2-bis). **Conséquence** : la victoire de ce challenger **ne peut pas** se mesurer au ΔRR standard.

Compte tenu de tout ce qui précède, je propose **trois briques**, par ordre de sûreté :

**(A) Badge tracé, honnête, boussole-safe — le cœur du livrable A-1.**
Pour chaque parcelle **mono** portant une fenêtre active : un badge *« fin d'engagement fiscal probable
2026-2027 — source : DVF VEFA 2016 + achèvement PC 2015 »*. Jamais une date de vente (roadmap « Rejeté »).
Jamais un nom. C'est un **signal de classement horodaté et tracé**, exactement au sens du mandat. Sa valeur
est **qualitative/prospection** (à qui parler, quoi surveiller), indépendante du ΔRR.

**(B) Composante V plafonnée — nudge de rang, jamais franchisseur de seuil.**
Une petite contribution positive `V_fenetre` (bornée, p.ex. ≤ +3 pts sur 100) qui **module le rang à
l'intérieur des bandes déjà plausibles** (« à creuser » → haut de « à creuser »/« chaude »), mais qui **ne
peut jamais, seule, créer une opportunité/brûlante depuis une écartée**. Garant : le **gate boussole 3 axes**
de l'arène (tier, statut cascade, matrice) — le run challenger `q_v6_m8 + V_fenetre` **doit** passer 0/64.
Restreinte au **mono**. C'est ce qui rend l'intégration compatible avec « un faux positif servi = péché
mortel ».

**(C) Validation par walk-forward dédié (pas l'arène RR).**
Puisque l'arène 2025 ne peut pas juger un signal 2026-2028, **valider la valeur prédictive** par un
backtest *as-of* : se placer fin 2018, marquer les fenêtres 2019-2022, mesurer le lift de mutation réel
observé 2019-2022. Le backtest §2-3 **est déjà** une preuve de ce type sur le passé ; le formaliser en
harnais walk-forward répétable serait le vrai juge de ce challenger.

**Impact estimé sur le classement.** Faible et ciblé : ~578 parcelles mono touchées, dont une fraction
seulement dans le top-1158. À l'arène, **attendre un ΔRR ≈ plat** (voire un churn commenté sans gain RR) —
et c'est **normal** (§7, réserve). Le gain réel est (A) le badge et (C) la valeur forward, pas le RR.

---

## 8. Recommandation & critère de GO

Le critère de GO (décision Vic) : *« ≥ 1 bosse avec lift ≥ ~1,5× dont l'IC95 exclut 1, ET couverture
prospective non anecdotique »*.

- **Bosse avec lift ≥ 1,5× IC-exclut-1** : ✅ **oui, massivement** — appartement lot-level (OR 5,96 / 6,22).
  Le mécanisme n'est pas plat : **l'idée ne meurt pas.**
- **Couverture non anecdotique** : ✅ **578 mono** (+154 copro) — au-dessus de l'anecdote.
- **Nuance décisive** : le lift significatif est en **copro/appartement** (non actionnable au niveau
  parcelle) ; la tranche **actionnable (maison)** est **directionnelle mais sous-alimentée**.

**Ma recommandation : GO conditionnel vers l'étape 2, sous la forme badge (A) + V plafonnée (B), validée
par walk-forward (C) et non par le ΔRR de l'arène** — l'arène restant le **garde-fou boussole/ECE/churn**
obligatoire, pas le juge de victoire de ce signal. Alternative défendable si Vic veut du significatif dur :
**pivoter vers le signal copro-immeuble** (§5, piste future) qui, lui, est fort et significatif — mais c'est
hors périmètre A-1 tel que cadré.

Si Vic estime que « actionnable mais sous-alimenté + instrument arène inadéquat » ne vaut pas l'intégration
maintenant : l'idée ne meurt pas pour autant (mécanisme prouvé), elle se **met en réserve** derrière un
harnais walk-forward, et on passe au challenger suivant de la famille A-1 (**PC caducs**, puis passoires
DPE F/G). Le présent rapport reste comme preuve d'instruction.

---

### Repro

```bash
python scripts/a1_defisc_backtest.py     # -> reports/a1-defisc/backtest.json + tables
python scripts/a1_svg.py                 # -> reports/a1-defisc/courbe_bosses.svg
```

Lecture seule ; connexion `dbname=labuse user=openclaw` ; seed 974 ; grâce 2 ans ; observation au 31/12/2025.

*Note : `docs/ROADMAP_ALGO.md` cité par le mandat est absent du dépôt (ni historique, ni autres branches ;
seul `docs/product/RADAR_MUTATION_PHASE0_AUDIT.md` existe, audit produit antérieur). Les règles liantes du
mandat — pas de date servie, voie « signal V », restriction identité — ont été appliquées telles qu'énoncées.*
