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
