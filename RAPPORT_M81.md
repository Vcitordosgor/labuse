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
