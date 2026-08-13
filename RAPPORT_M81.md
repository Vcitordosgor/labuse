# RAPPORT M81 — Golden rebasé, rejeu, bascule
## PHASE 1 — Rebase du golden — **STOP, revue attendue**

Branche `feat/m81-rejeu` (main + reprise de M79 `feat/m79-dvf` : DvfLayer terrain, plo/phi 150/325).
Le code du rejeu a désormais TOUTES les corrections : M70 (ENS per-commune, BODACC sondage, OCS GE proxy,
S3REnR), M71 (DPE hors scoring, Saint-Philippe), M79 (DvfLayer terrain).

### Origine des « 33 FAIL » — classés un par un : **dérive légitime, ZÉRO bug**

D'abord un piège de harnais : `golden_check.py` cible par défaut le port **8010** ; l'API tourne sur **8000**
→ sans `LABUSE_API_BASE=http://127.0.0.1:8000`, les 33 ancres qui appellent l'API tombaient en
« Connection refused » (les 85 autres sont DB-only). **Avec la bonne cible : 0 incohérence base↔API.** Les
33 FAIL restants sont des écarts référence↔actuel, tous légitimes :

| Écart | Occurrences | Cause (mandat déjà mergé) |
|---|---|---|
| `score_v2.couleur_hex / declasse / exception_registre / label / motif / rang_total` | 33 chacun | champs **verdict_servi** ajoutés (M54-AB / M73 / M-D bailleurs) — la référence 07/08 les précède (`attendu='<absent>'`) |
| `db.dpe.{n, pire_etiquette, derniere_date}` → `<absent>` | 3 | **M71** : DPE sorti du scoring / payload (squelette M66-B) |
| `n_lignes_cascade` 33 → 32 | 3 | **M73** : arbitrage aléa (fusion d'un niveau côte à côte) |
| `veille_succession.dirigeant_age` 74 → 75 | 1 | fraîcheur : la personne a vieilli d'un an |

**Aucun vrai bug jamais traité** : tous les écarts sont la trace de corrections mergées que la référence
gelée ne portait pas encore. **Aucun triplet d'ancre (cascade_status/matrice_statut/tier_v2) n'a bougé**
(vérifié : « ancres dont le triplet a bougé : 0 »).

### Rebase
`qa/golden_regen.py` (API 8000, run servi q_v8_calibre) → référence régénérée sur les 118 parcelles.
**Résultat : 118/118 PASS, 0 FAIL, 0 incohérence base↔API.** Le diff git de
`reports/m6-audit/golden/golden-parcelles.json` (+214/−28) EST la revue : champs verdict_servi + DPE +
dirigeant_age + n_lignes_cascade, aucun verdict d'ancre modifié.

**STOP.** La référence est propre. Aucun rejeu tant que Vic n'a pas lu le diff du golden. Ensuite Phase 2
(rejeu, mesures, STOP avant bascule).

### Garde-fous Phase 1
Golden 118/118 (rebasé), garde-fou de branche vérifié. Rappel : lancer `golden_check.py` avec
`LABUSE_API_BASE=http://127.0.0.1:8000` (ou l'API sur 8010). **NE PAS MERGER.**

---

## PHASE 2 — Rejeu (mesures) — **STOP, 2 arbitrages avant bascule**

Rejeu `q_v9_m81` : **431 663 parcelles** évaluées (cascade complète + toutes les corrections), écrit
uniquement dans `dryrun_*` du label — **run servi `q_v8_calibre` intact**. `parcel_p_score_v2` et la
matrice restent à produire (voir blocage ci-dessous).

### ✅ Exigences RESPECTÉES

- **ENS** : **45 322** parcelles PASS→UNKNOWN (= les ~45k attendus). **0 parcelle non-exclue → exclue** :
  aucune ne devient écartée à cause de l'ENS. Les 7 113 ENS-UNKNOWN encore `exclue` l'étaient DÉJÀ en q_v8
  (par d'autres couches) ; 4 181 se libèrent même. Le rang est porté par le modèle P (non régénéré) → non
  perdu. **Exigence tenue.**
- **Saint-Philippe** : **4 153** parcelles UNKNOWN « Zonage PLU non publié au GPU », **0 HARD_EXCLUDE
  zonage** — jamais inconstructibles. **Exigence tenue.**
- **DVF prix nuls — aucune commune en bloc** : « aucune vente terrain » = max **Saint-Philippe 19,3 %**,
  Salazie 19,0 %, L'Étang-Salé 10,2 % (rural, faible liquidité) — rien à 100 %. À DIRE au client sur ces
  communes (« marché terrain partiellement établi »), pas un zéro masqué. 87 861 prix affichés, 3 050 sans
  vente terrain.

### ⚠️ Le delta est DOMINÉ par une correction HORS de ta liste

**La graduation PPR rouge (M-I) est le driver ÉCRASANT du delta**, pas les corrections listées. Elle était
mergée mais le run gelé du 29/07 la précédait :
- couche `risques` HARD_EXCLUDE : **−106 509 lignes** (151 545 → 45 036) ; **toutes les autres couches
  identiques** (zonage, bâti, surface… inchangées) ;
- effet parcelles : **`exclue` −55 514** (133 735 → 78 221) → **41 909** exclue→faux_positif, **13 570**
  exclue→**a_creuser** (nouvellement SERVIES), 35 exclue→opportunité. Sens = **desserrement**.
- exemple (parcelle 12484) : q_v8 « Exclue PPR zone rouge » → q_v9 « PPR rouge marginal : 12 m² (1,5 %),
  hors emprise probable » — la marginale <2 % ne rejette plus.

**Conséquence sur le recollement DVF** : ton attendu (rang 0, ~170 chaude en retrait) **ne peut pas être
isolé** — la graduation PPR ajoute ~14k parcelles au vivier servable, ce qui masque/compense le −170 du DVF.
Net « chaude approximée » (Q≥65 & A≥60 & compl≥50) : 4 373 → 4 547 (**+174**). La vraie matrice est bloquée
(ci-dessous), donc le chiffre chaude exact n'est pas mesuré.

### 🛑 BLOCAGE — l'ancre canari est PÉRIMÉE (garde matrice stoppée)

`matrice-apply` s'est **arrêté sur sa garde** (tuiles NON reconstruites, run servi intact) :
> `CANARI 97415000AC0253 = 'a_creuser' (attendu chaude PAR ÉVÉNEMENT BODACC)`

Cause : **donnée fraîche, pas un bug.** La procédure BODACC du canari est passée de « collective OUVERTE
(redressement) » (q_v8) à « **CLÔTURÉE — extinction du passif** » (q_v9) : la société a soldé son passif
depuis le 29/07 → plus d'événement rouge → plus chaude-par-événement. **Le mécanisme BODACC rouge est
sain** (41 événements en q_v9 vs 39 en q_v8, park entier). C'est l'**ancre golden + la garde matrice qui
figent CE parcelle** qui sont périmées.

### CE QUI RESTE (bloqué tant que le canari n'est pas tranché)
- **matrice** (`matrice-apply`) → `matrice_statut` (chaude/challengers) — le vrai chiffre chaude ;
- **modèle P** (`score-v2 --run-id q_v9_m81`) → `parcel_p_score_v2` (tier/rang) **+ garde de non-constance
  M71-B3** (elle s'exécute dans ce pipeline) ;
- puis delta de classement tier complet (attendu ~0 sur le rang P, cf. M79).

### ARBITRAGES demandés (avant toute suite)
1. **Graduation PPR (M-I)** : valides-tu qu'elle entre dans ce rejeu ? C'est l'effet dominant (~55k exclue
   en moins, ~14k nouvellement servies), mergé mais absent de la liste du mandat.
2. **Ancre canari** : la procédure a légitimement clôturé. Choisir un **nouveau canari** avec événement
   BODACC rouge actif (candidats mesurés : 97408000AR0414 / AR0385 / BK0215… à La Possession) et mettre à
   jour la garde matrice + l'ancre golden — ou relaxer la garde. **C'est ton geste** (ancre « non-balayable »).
   Sans ça, ni matrice ni bascule.

### Garde-fous Phase 2
Rejeu 431 663 (cascade), run servi intact, aucune écriture hors `dryrun_* q_v9_m81`. ENS/Saint-Philippe/
prix-nuls mesurés et conformes. **STOP — Vic tranche PPR + canari avant matrice/score-v2/bascule. NE PAS MERGER.**

---

## PHASE 2 (suite) — arbitrages appliqués, run complet, delta mesuré — **STOP, GO bascule attendu**

Vic a tranché : **graduation PPR OUI** (faux négatifs réparés) ; **nouveau canari** (pas de relaxe). Run
`q_v9_m81` désormais COMPLET (cascade + matrice + modèle P), run servi `q_v8_calibre` intact.

### Les DEUX effets, séparés (exigence Vic — 2 phrases pour le client)
1. **Graduation PPR rouge (M-I)** — « ~14 000 parcelles injustement exclues par un chevauchement PPR rouge
   MARGINAL (souvent en zone bleue dominante) sont réévaluées ; **362** entrent dans le classement matrice
   (dont **14 chaude**), le reste reste servi-mais-bas. » C'est le péché mortel inversé réparé.
2. **DVF terrain + ENS + DPE (M70/M71/M79)** — « le prix affiché devient un prix de TERRAIN, l'ENS ne dit
   plus "Hors ENS" sur les communes non couvertes, le DPE sort du scoring : ces corrections ajustent les
   SCORES (127 parcelles perdent "chaude" par le prix corrigé, 81 en gagnent), **sans changer une seule
   exclusion ni le rang**. »

### Delta de classement — le RANG NE BOUGE PAS
- **Tier modèle P** : **431 483 identiques / 180 changent** (0,04 %) — surtout → `declasse_au_statut_inconnu`
  (~153 : AU en attente d'ouverture, effet de fraîcheur, cf. 1 862 déclassées AU en attente au run).
- **Déplacement de rang : médian 0, p90 0, max 0.** Le classement P servi ne bouge PAS d'une ligne (confirme
  M79 : le modèle P calcule déjà son prix terrain, indépendant des corrections cascade).
- **Chaude matrice** : 960 → **928** (−32 net) = −127 (prix DVF corrigé, ordre du −170 prévu M79) +81 (autres)
  +14 (PPR). **Brûlantes** : 120.

### 10 échantillons nouvellement servies (exigence Vic — vérif à l'œil)
Toutes « Exclue : PPR zone rouge (inconstructible) » en q_v8 → en q_v9 :

| Commune | Parcelle | q_v9 (graduation) |
|---|---|---|
| La Plaine-des-Palmistes | 97406000AV1267 | Zone bleue PPR (~54 %) — constructible sous conditions |
| Saint-Denis | 97411000HD0281 | Zone bleue PPR (~70 %) |
| Saint-Denis | 97411000DZ0053 | PPR rouge marginal : 15 m² (1,6 %), hors emprise |
| Saint-Joseph | 97412000CX0763 | Zone bleue PPR (~88 %) |
| Entre-Deux | 97403000AS0866 | Zone bleue PPR (~20 %) |
| Saint-Paul | 97415000EW0824 | Zone bleue PPR (~12 %) |
| Saint-Leu | 97413000CC0216 | rouge gradué (part marginale) |
| Saint-Joseph / Saint-Paul / Saint-Benoît | 97412000BP0325 / CL0642 / 97410000AT0367 | rouge gradué sous seuil |

Le motif est constant : **la parcelle est majoritairement en zone BLEUE (constructible sous conditions)
mais un chevauchement ROUGE marginal l'excluait entièrement en q_v8**. La graduation dit vrai.

### Exigences RESPECTÉES (rappel + garde)
- **ENS** 45 322 flips, **0** devenue exclue ; **Saint-Philippe** 4 153 UNKNOWN, 0 HARD_EXCLUDE ; **prix nuls**
  aucune commune en bloc (max Saint-Philippe 19,3 %) ; **rang** inchangé.
- **Garde de non-constance (M71-B3) : PASSÉE** — `score-v2` a scoré 431 663 sans lever (un signal constant
  aurait stoppé le pipeline).
- **Canari** résolu : ancien 97415000AC0253 sorti (procédure clôturée, donnée fraîche), nouveau
  97414000CV0907 (Saint-Louis, liquidation stable, 2 signaux) — garde + golden + BACKLOG à jour.

### Ce qui reste (Phase 3 — bascule, sur ton GO)
`served_run.txt` → q_v9_m81 · `run_precedent.txt` → q_v8_calibre · `npm run build` + `matrice-apply`
(tuiles, garde canari passe maintenant) · purge de rétention (M80) · rebase golden sur q_v9_m81 (bascule
l'ancre canari) · vérifs écran (ENS/BODACC/prix terrain/Saint-Philippe) + non-contradiction M73.

**STOP — le rang ne bouge pas, les exigences sont tenues, les deux effets sont séparés. GO bascule ? NE PAS MERGER.**

---

## PHASE 3 — Bascule (GO Vic) — **FAITE, recette visuelle attendue**

Ordre exécuté : `matrice-apply q_v9_m81` (canari **chaude** ✓, tuiles 431 663) → `served_run.txt` → q_v9_m81 +
`run_precedent.txt` → q_v8_calibre → `build-mvt` (mvt_parcels 431 663) + `npm run build` (bundle q_v9_m81) →
purge rétention (**rien à purger**, servi+précédent+lignée+démo gardés) → **golden rebasé sur q_v9_m81**
(119/119 PASS ; ancre canari basculée : ancien 97415000AC0253 chaude→a_creuser, nouveau 97414000CV0907 chaude).

**Correctif de bascule** : la graduation PPR fait apparaître « intersection marginale » comme verdict à part
entière (plus une contradiction) → relibellé côté client « recouvrement marginal » (`risques_arbitrage`,
read-time, 5 docs) — le test de non-contradiction M73 repasse.

### VÉRIFS ÉCRAN (run servi q_v9_m81) — pour ta recette
| Attendu | Parcelle | Rendu réel |
|---|---|---|
| ENS « non disponible » sur commune vide (pas « Hors ENS ») | 97407000AK1345 (Le Port) | « **Donnée ENS non disponible sur cette commune.** » ✓ |
| BODACC « sondé le [date] » | 97415000BK0023 | « Aucune procédure collective — **propriétaire sondé le 13/08/2026.** » ✓ |
| Prix TERRAIN + seuils (plus le 379) | 97415000AC0253 (canari) | « **Prix médian terrain 173 €/m²** — 3 ventes, secteur cadastral, 2021-2025 — **échantillon fragile (~28 %)**. » ✓ |
| Saint-Philippe « non publié au GPU » | 97417000AE0003 | « **Zonage PLU non publié au GPU** … trou de donnée, pas un verdict. » ✓ |

### Garde-fous Phase 3 — TOUS VERTS
`golden_check` **119/119 PASS** · **non-contradiction M73 9/9** · cohérence run servi 4/4 (bundle reconstruit) ·
`test_risques_arbitrage` 6/6 · exports premium/dossier **200** (canari + Saint-Philippe) · garde canari
**passe** (nouveau canari chaude) · garde non-constance passée · run précédent q_v8_calibre conservé (rétention).

**Le run servi est désormais q_v9_m81.** Toutes les corrections M70/M71/M79 + graduation PPR sont visibles au
client, le rang n'a pas bougé. **NE PAS MERGER avant ta recette visuelle.**
