# M39 — PHASE 0 · CONSTAT (piscine surfacique, solde dette #13)

**Branche** `m39-signaux-negatifs` · base `main` a2a28031 · **STOP obligatoire après ce rapport.**
**Nature de la phase : LECTURE SEULE.** Zéro écriture DB / run servi / config / src. Seuls
fichiers nouveaux : `qa/m39/*`. Golden, re-mesures M34/M35, SHA256 vigilances M37 : intacts par
construction (rien touché) — ils seront le gate des phases 1-2.

Tout ci-dessous est **vérifié sur pièces en base** (`labuse`, run servi `q_v8_calibre`,
millésime ortho 2025). Les affirmations des mandats antérieurs qui ne tiennent pas sont signalées.

---

## 1. Inventaire de l'actif piscine réel

**L'actif existe et il est SURFACIQUE.** Tables présentes et peuplées en base servie :

| Table | Contenu | Volume |
|---|---|---|
| `ortho_detections` (type='piscine') | polygones `geom`(4326)+`geom_2975`, `surface_m2`, `confiance`, `criteres` jsonb, `juge_flair`, `probe_score`, `validation` | **19 899** détections |
| `parcel_equipements` | agrégat parcelle : `piscine` bool, `piscine_surface_m2`, `piscine_confiance` | **8 299** parcelles `piscine=true` |
| `ortho_tiles` | tuiles + `millesime`, `traite_at` | 5 041 / 5 041 traitées |

- **Millésime : 2025, UNIQUE.** Une seule campagne ortho en base (BD ORTHO 974 20 cm, WMS IGN).
- **Forme : surfacique** (polygone réel, `ST_Area(geom_2975)` ≈ `surface_m2` au décimètre près).
  Pas des centroïdes.
- **Règle de matérialisation** (les 8 299) = `(juge_flair ≥ 0,30 ET probe_score ≥ 0,50)` **∪**
  `validation='ok'` (humain). Vérifié : 7 601 détections juge-seul, 680 juge+humain, 815 'ok'
  humain (dont 135 hors-juge), 804 'faux_positif'. Précision annoncée **90,7 %** / rappel 74,5 %
  (source `RAPPORT_WAVE_ORTHO.md`, échantillon interne indépendant — libellé produit « détectée »,
  jamais « présente certifiée »).
- **Faux positifs connus** : bâches/toits bleus (rectilignes, rejet si recouvrement bâti),
  trampolines, terrains de sport. La **grande surface est FP-prone** : sur détections
  humain-validées ≥ 60 m², **14 'ok' contre 19 'faux_positif'** — au-delà de ~60 m² le signal
  « piscine résidentielle » se dégrade (bassins collectifs, plans d'eau, grands bleus).

### ⚠ Constat majeur — AK1442 / AL1154 ne sont PAS dans la couche matérialisée

Le mandat pose : « AK1442 et AL1154 doivent sortir naturellement de la mesure ». **Sur pièces,
elles n'en sortent pas.** Vérifié détection par détection :

| Parcelle | dans `parcel_equipements` | `surface_m2` | `confiance` V0 | `juge_flair` | `probe_score` | `validation` |
|---|---|---|---|---|---|---|
| 97422000**AK1442** | **absente** | 87,7 | 0,785 | **NULL** | **0,000** | NULL |
| 97419000**AL1154** | **piscine = f** | 73,6 | 0,888 | **NULL** | **0,001** | NULL |

**Ce que le registre M28/M32 appelle « FLAIR 88 m² » / « FLAIR 0,888 » est en réalité le
`confiance` colorimétrique V0 et le `surface_m2` — PAS un score FLAIR.** `juge_flair` est **NULL**
pour les deux : FLAIR n'a jamais été calculé sur elles. Raison établie sur pièces : **FLAIR a été
gaté par le probe** — détections avec FLAIR calculé : probe moyen 0,881 ; détections FLAIR-NULL :
probe moyen 0,034 (max 0,350). AK1442/AL1154 sont à probe ≈ 0,00 → sous le gate → FLAIR jamais
lancé → non matérialisées. Autrement dit **le classifieur produit (probe DINOv2) contredit
activement** que ce soit des piscines.

Ce que V0 a vu (colorimétrie forte, plausible visuellement) : AK1442 `couleur 0,916 solidité 0,86
forme 0,8` ; AL1154 `couleur 0,985 solidité 0,937 forme 1,0` — des taches cyan de forme bassin,
72–88 m², hors emprise bâtie. Vic les a confirmées à l'œil (« PVA 2025 ») au registre. **Trois
instruments, trois verdicts** : V0 colorimétrique = oui ; probe DINOv2 = non (≈0) ; œil de Vic =
oui. La couche matérialisée servie ne retient que le verdict probe/FLAIR → elle les rate.

**Conséquence directe pour la Phase 1** : une règle générique bâtie sur la couche matérialisée
telle quelle **ne réconciliera pas** AK1442/AL1154. Le « zéro double comptage » demandé est
atteignable (les deux ensembles sont disjoints — voir §4), mais la « réconciliation registre →
règle générique » n'est PAS possible en l'état sans décision. **Arbitrage requis (voir §5).**

---

## 2. La datation — « récente » est INFABRICABLE sur l'actif actuel

**Une seule campagne ortho en base : millésime 2025.** Il n'existe aucun millésime N-1 pour
opposer « absente N-1 / présente N ». La BD ORTHO 974 est re-survolée tous les ~3-4 ans et le
mandat Ortho n'a ingéré que 2025.

- **Signal « piscine RÉCENTE » (datée) : non fabricable** avec l'actif présent.
- **Seul chemin vers une vraie datation** : acquérir un millésime ortho **historique** IGN pour le
  974 (flux `ORTHOIMAGERY.ORTHOPHOTOS.HISTORIQUE`, campagnes ~2012/2017 disponibles) **et rejouer
  la détection dessus** — un coût d'acquisition + calcul réel, à décider (Phase 1). Proxys de
  récence sans ortho N-1 (mutation récente, déclaration préalable Sitadel piscine) sont des signaux
  **différents**, pas une datation de la piscine.
- À défaut, le signal disponible est **« présente 2025 » (non daté)** — moins fort. Le mandat
  l'anticipe : « on arbitrera ce que vaut un signal présente non daté (beaucoup moins) ».

**Point de doctrine engagé.** « Le doute ne profite jamais au classement — dans les deux sens :
on ne déclasse pas non plus sur un signal douteux. » Déclasser une chaude sur une piscine **non
datée** revient à écarter une parcelle que le propriétaire a peut-être équipée il y a 15 ans (le
signal « il vient d'investir » ne tient plus). C'est le cœur de l'arbitrage §5.

---

## 3. Le seuil surfacique — distribution et proposition

Distribution des 8 299 surfaces matérialisées : min 10,0 · médiane **22,3** · moyenne 24,9 · max
144,8 m². Distribution par validation humaine (le seul étalon de vérité) :

| validation | n | médiane | sous 12 m² | sous 15 m² | ≥ 60 m² |
|---|---|---|---|---|---|
| **ok** | 815 | 21,2 | 80 | 190 | 14 |
| **faux_positif** | 804 | 15,8 | 175 | 355 | 19 |

Lecture : les FP sont **plus petits** (médiane 15,8 < 21,2) et **la queue haute est FP-prone**.
Un plancher coupe surtout du FP : sous 15 m², 355 FP pour 190 ok.

**Proposition de seuil (à arbitrer)** : bande **[15 m² ; 60 m²]** pour « piscine résidentielle
typique déclassante ».
- Plancher **15 m²** : élimine 355 FP contre 190 ok validés (le sous-15 est FP-majoritaire).
- Plafond/flag **60 m²** : au-delà, FP-majoritaire (19/14) → soit exclusion, soit exigence de
  `validation='ok'` humaine (les grands bassins collectifs ne sont pas un « investissement usage
  du propriétaire »). Note : AK1442 (87,7) / AL1154 (73,6) tomberaient **au-dessus** de 60 m² —
  mais leur problème n'est pas la surface, c'est le classifieur (§1).

Le seuil surfacique est un **gate produit additionnel** par-dessus la précision juge 90,7 % déjà
acquise — il ne la remplace pas.

---

## 4. Population d'impact (mesurée, run servi `q_v8_calibre`)

Parcelles servies **brûlante/chaude** portant une **piscine matérialisée** :

| tier servi | piscine matérialisée | ≥ 15 m² | ≥ 20 m² | ≥ 25 m² |
|---|---|---|---|---|
| **brûlante** (119 servies) | 2 | 2 | 2 | 0 |
| **chaude** (1 041 servies) | 45 | 32 | 26 | 18 |
| **TOTAL** | **47** | **34** | **28** | **18** |

→ **La règle générique déclasserait 47 chaudes/brûlantes** (34 au seuil 15 m²). Digest exhaustif
et revue-humaine : `qa/m39/candidats_declassement_p0.csv` (47 lignes).

**Contrôle de cohérence avec le registre — le point sensible :**
- Les 47 candidats ont **zéro recouvrement** avec les 5 entrées du registre servi
  (`served_run_exceptions`). Donc **pas de double comptage** entre règle et registre.
- **MAIS AK1442/AL1154 ne figurent PAS dans les 47** : (a) elles sont déjà servies `a_creuser`
  (le registre M32 les a fait basculer depuis leur tier naturel — AK1442 **brûlante**→a_creuser,
  AL1154 **chaude**→a_creuser) ; (b) elles ne sont pas matérialisées (§1). Elles étaient donc de
  vraies « fausses chaudes », **mais captées par l'œil de Vic, pas par la couche automatique.**
- Il existe une **bande « probe-ratée »** : 4 858 détections FLAIR-NULL à V0 fort
  (`confiance ≥ 0,7`, `surface ≥ 15`) sur l'île, dont **11 sur des chaudes servies**. C'est la
  famille où vivent AK1442/AL1154 : V0 crie piscine, le probe dit non, FLAIR n'a pas tranché.
  Déclasser sur cette bande = déclasser sur un signal que le classifieur produit conteste →
  **interdit par la doctrine** en l'état. C'est exactement l'arbitrage §5-C.

---

## 5. STOP — arbitrages Vic requis

Le mandat interdit toute bascule dans ce chantier ; ces arbitrages cadrent la Phase 1. **Rien ne
sera écrit avant réponses.**

**A. Définition de « récente ».** Confirmes-tu que la datation vraie est infabricable sur l'actif
2025 (§2) ? Deux voies :
- **A1** — signal **« présente 2025 » non daté**, assumé plus faible, seuil de déclassement
  prudent (ex. exiger tier chaude *et* surface ≥ seuil *et* juge matérialisé). Aucune acquisition.
- **A2** — financer l'**acquisition d'un millésime ortho historique** (IGN 974 ~2012/2017) + re-run
  détection pour dater réellement les piscines. Coût réel, Phase 1 longue. Recommandation : A1
  d'abord (livrer le signal présent), A2 en dette si la valeur le justifie.

**B. Seuil surfacique.** Valides-tu la bande **[15 ; 60] m²** (§3), et le traitement du >60
(exclure, ou exiger `validation='ok'`) ?

**C. Périmètre du déclassement — LE point dur.** Deux instruments coexistent :
- **C1 — Règle sur la couche matérialisée seule** (probe/FLAIR + humain 'ok', précision 90,7 %) :
  déclasse **47** hot (34 à ≥15 m²), **haute confiance**, doctrine respectée. Mais **AK1442/AL1154
  restent hors règle** — on les **laisse au registre à l'identique** (motif client inchangé, pas de
  double comptage car disjoints). Honnête, prudent. **Recommandé.**
- **C2 — Compléter FLAIR sur la bande probe-ratée hot** (relancer FLAIR-INC sur les tuiles des
  candidats FLAIR-NULL hot, ~une dizaine + les 2 seeds) pour obtenir un vrai `juge_flair` : soit il
  confirme AK1442/AL1154 → elles rentrent naturellement dans la règle (réconciliation vraie) ; soit
  il les infirme → alors le registre M28/M32 s'appuyait sur du V0 colorimétrique seul, à réexaminer.
  C'est la voie « constater plutôt que présumer », mais elle exige de **re-télécharger des tuiles**
  (cache purgé à la clôture Ortho) — coût Phase 1. **Recommandé en complément de C1** si tu veux
  vraiment solder les deux seeds par la règle et non par la main.
- **C3 — Faire confiance à V0 colorimétrique seul** (conf ≥ 0,7) pour rattraper les seeds :
  **déconseillé** — tire ~4 858 détections île que le probe conteste, précision inconnue,
  « le doute profiterait au déclassement ». À écarter sauf mini-validation visuelle dédiée.

**Ma recommandation synthèse : A1 + B(15–60) + C1, avec C2 en option pour solder AK1442/AL1154 par
la règle plutôt que par le registre.** Cela livre un signal fort et honnête (47 fausses chaudes
écartables), sans jamais déclasser sur un signal que le classifieur conteste, et sans prétendre à
une datation qu'on n'a pas.

---

## Annexes / preuves
- `qa/m39/candidats_declassement_p0.csv` — les 47 hot ∩ piscine matérialisée (revue humaine).
- `qa/m39/piscines_materialisees_x_tier.csv.gz` — exhaustif 8 299 piscines × tier servi (convention M37).
- `qa/m39/_global.txt` — SHA256 d'intégrité des deux digests.
- Aucune écriture servie. Golden / re-mesures / vigilances M37 : non touchés (lecture seule).
