# COMPTE-RENDU SCORING-3 — le run candidat « gains sûrs », et le potentiel

**Branche `feat/scoring-3`, un commit par lot. Le run candidat `q_v12` est
CALCULÉ par le pipeline réel (celui du bouton « Calculer »), JAMAIS basculé —
`q_v11_m137` reste le run servi. La bascule appartient à Vic (Données ›
Circuit › Basculer, note de version et écart affichés).**

---

## L1 — Le run candidat q_v12

**Fait.** La recette est EXACTEMENT ce que l'arène a validé, et vit désormais
dans UN module de production (`src/labuse/scoring/p_v2/qv12.py`) que l'arène et
le pipeline réel partagent : censoring K1c (`tenure_bin_v2` censurée fine) ·
K2 (4 mortes + 5 retired hors du fit) · K3 (résiduel lu à 100 %, 0 = réponse,
hors_plu seul inconnu) · K4 bis variante GLOBALE (voisinage/marché as-of, test
de fuite rejoué : passé) · **isotonique PAR SEGMENT sur 2024** (le seul apport
de K4 retenu — le fit reste global) · pas de recalage d'intercept (la
calibration est celle que l'arène a mesurée) · horizon 12 mois servi (p_raw),
**24 mois calculé et stocké** (`p_24m`, modèle dédié au protocole K1 bis).

Artefacts GELÉS (doctrine m36 : sha256 au manifeste, refus si mismatch) :
`reports/q-v12/artifacts-q_v12-{12m,24m}.joblib` + `FREEZE-q_v12.json`.

**Mesuré (banc K0, année vierge 2025)** — la ligne `q_v12` de `k0_table.csv` :

| Métrique | base | K4bis (SCORING-2) | **q_v12 (iso/segment)** |
|---|---|---|---|
| préc@100/commune (méd. 24) | 0,060 | 0,075 | **0,080** |
| lift décile sup | 2,06 | 2,11 | **2,27** |
| AUC global | 0,613 | 0,610 | **0,620** |
| ECE global | 0,0013 | 0,0012 | 0,0022 |
| effectif Priorité | 73 | 91 | 79 |
| précision Priorité* | 0,137 | 0,066 | 0,076 |
| churn top-1158 vs servi (arène) | 0,180 | 0,453 | 0,484 |
| 24 mois (test 2024) | — | — | AUC 0,638 · préc@100 0,125 |

\* rappel SCORING-2 : sur ~70-90 parcelles, la précision Priorité porte ±8
points de bruit (témoin re-fit 8,7 % vs artefact 13,7 %) — préc@100, lift et
AUC sont les lignes stables. **q_v12 est la meilleure tête du tableau.**

**Le run réel existe** : `q_v12` — 431 663 parcelles scorées par le pipeline du
bouton « Calculer » (`flux-run --recette q_v12` : cascade des 24 communes
~2 h 50 + scoring 461 s), `p_24m` rempli sur 431 663/431 663, Priorité 1 133
chaudes + 92 brûlantes. Au passage, deux vraies pannes corrigées : l'argv du
bouton (`-m labuse` sans `__main__` → `-m labuse.cli`) et la limite psycopg
des 65 535 paramètres (la 14e colonne p_24m faisait déborder l'INSERT →
chunksize dynamique).

**L1.2 — l'écart run réel vs arène** (attendu nommé) : 1 000 parcelles tirées
au hasard (seed 974), p de l'artefact via le chemin d'arène (enrichissement
recalculé FRAIS, sans les caches) vs `p_raw` stocké du run réel :
**écart médian 3,1 × 10⁻⁷** (= l'arrondi de stockage à 10⁻⁶), max hors AU
4,9 × 10⁻⁷, **0 parcelle > 10⁻⁶** hors les 5 sous pondération AU (politique de
RANG du pipeline, hors modèle — écart attendu, signalé). Ce qui a été mesuré
EST ce qui sera servi (`reports/q-v12/q_v12_verif.csv`).

**L1.3 — la note de version telle que Vic la lira** (composée depuis les
chiffres, stockée dans `p_score_v2_runs.params`, affichée au panneau Basculer) :

> Candidat q_v12 du 03/09/2026 — les gains sûrs de SCORING-2, produits par le
> pipeline réel. Ce qui change : 4 variables mortes + 5 retired retirées (K2) ·
> résiduel lu à 100 % (zéros M125, hors_plu seul inconnu — K3) · voisinage et
> marché as-of, architecture globale (K4 bis, fuite testée) · calibration
> isotonique par segment sur 2024 (seul apport de K4 retenu) · censoring
> explicite. Horizon 12 mois servi ; 24 mois calculé et stocké (p_24m), rien
> d'affiché. Les chiffres (banc K0, année vierge 2025) : préc@100/commune
> 0,060 → 0,080 ; Priorité 13,7 % sur 73 → 7,6 % sur 79 ; lift décile
> 2,06 → 2,27 ; AUC 0,613 → 0,620 ; ECE 0,0022 ; churn top-1158 : 48,4 %.
> Horizon 24 mois (test 2024) : AUC 0,638. Rien de servi ne change tant que la
> bascule n'est pas faite : q_v11_m137 reste le run servi.

**L1.4 — la garde de churn** (mesurée sur les DEUX runs stockés, pas l'arène) :
churn top-1158 q_v12 vs q_v11_m137 = **46,3 %** ; Priorité servie 1 478 →
candidate 1 225 ; **576 sorties de Priorité**, les 50 premières expliquées
(`reports/q-v12/q_v12_sorties_priorite.csv`) : **37 « variable retirée »**
(le score servi s'appuyait sur une morte K2), **8 « redistribution de la
tête »** (recalibration par segment), **5 « voisinage défavorable »** (K4 bis).
Vic ne bascule pas à l'aveugle : la moitié de la tête change, et chaque sortie
a sa raison.

**L1.5** — le panneau Basculer montre q_v12 : candidat COMPLET (cascade +
score), chip recette, **note de version dépliable**, écart avant/après
(4 688 tiers changent, promues 1 478 → 1 225, dérive −17,1 %). Le bouton
« Calculer » propose désormais les deux recettes (m36 / candidat q_v12) — même
pipeline, même CLI (`flux-run --recette`).

## L2 — Le feature store, corrigé à la source

**Fait.** La cause n'était pas la jointure (correcte) mais la **staleness** :
`p_model_static` n'est reconstruite qu'aux rafraîchissements PLU/bâti (~1 h 47
de jointures spatiales) et `rebuild_features` — le job de CHAQUE run — ne
rafraîchissait jamais les colonnes résiduel. Les écritures M125 (0 = réponse,
cause explicite) n'atteignaient donc jamais le dataset.

Correctif : `refresh_static_residuel` (`p_model/sql.py`) — UPDATE ciblé des
trois colonnes dérivées de `parcel_residuel`, câblé dans
`pipeline.rebuild_features` (5,7 s sur le parc, tracé au rapport de run).

**Mesuré** : avant → après (base réelle) : `sdp_residuelle_m2` 173 678 zéros
avalés → **0** ; `pct_potentiel` 182 → 0 ; `sous_densite` 199 → 0 ;
181 945 lignes rafraîchies (inclut les 436 « égarées » de K3).

**Les colonnes vérifiées** (`reports/q-v12/l2_colonnes_verifiees.csv`, un zéro
n'est jamais un NULL) : sdp_residuelle_m2 · pct_potentiel · sous_densite
(les 3 corrigées) ; pente_moy_deg · canopee_pct · ndvi_moyen · dist_ecole_m ·
dist_sante_m · dist_commerce_m · dist_tcsp_m · emprise_bati_m2 : **AUCUN zéro
avalé** (leurs NULL sont des sources réellement muettes, légitimes).

Test permanent : `tests/test_scoring3_featurestore.py` — ÉCHOUE si une parcelle
avec résiduel = 0 ressort « inconnue » (+ idempotence, + no-op sans tables).

## L3 — BDNB au catalogue et au CRON

**Fait — avec un CONSTAT AMONT MESURÉ qui change la donne** : depuis le
millésime 2026-02-a, le CSTB ne publie QUE l'export France entier (csv.tar.gz
**39,4 Go**, sondé le 03/09 ; plus d'extrait départemental, S3 refusé sur les
anciens chemins). Et cet export **ne couvre PAS La Réunion** : streamé et
vérifié ligne à ligne, `batiment_groupe_ffo_bat` contient 22 310 491 lignes sur
**96 départements — métropole seule, 0 ligne 974**
(`reports/q-v12/l3_bdnb_constat.csv`).

Ce qui est EN PLACE, prêt pour le trimestre où l'amont couvrira le 974 :
- **Ingestion** (`ingestion/bdnb.py`, `labuse ingest-bdnb`) : STREAME l'archive
  nationale (gunzip → tar flux → filtre `code_departement_insee`), sans jamais
  poser les 39 Go sur le disque ; **sonde de couverture d'abord** (~4 min :
  si 0 ligne 974, arrêt honnête, motif écrit au catalogue, re-sonde au
  trimestre suivant) ; idempotente par millésime ; tables cibles
  `bdnb_rel_parcelle` (la jointure bâtiment→parcelle PAR L'EMPRISE, croisement
  cadastre fait par le CSTB), `bdnb_ffo`, `bdnb_dpe`, `bdnb_groupe`.
- **Catalogue** : source « BDNB », statut honnête `a_faire`, millésime
  « 2026-02-a (métropole seule — 974 absent) », le constat daté aux notes.
- **Veille** : sentinelle `api` data.gouv (`last_update`, sondé : 2026-05-22)
  — elle prévient du prochain millésime, n'ingère jamais.
- **CRON** : job `ingest-bdnb` trimestriel (1er jan/avr/juil/oct, 05:00
  Réunion) — « le CRON calcule, Vic promeut » (plan v2 §5).

**L3.2 — tableau K0 avec/sans BDNB** : le banc est ÉCRIT et rejouable
(`scripts/audit/scoring/l3_bdnb.py` — année de construction, avant-1975,
classe DPE, F/G, écart de surface BDNB vs BD TOPO, même protocole que q_v12).
**Verdict : ELLES ATTENDENT** — non mesurables tant que l'amont ne couvre pas
le 974 (le proxy local `dpe_records` ne porte que 17 enregistrements — pas de
matière non plus). Aucune variable BDNB n'entre dans q_v12.

## L4 — Le potentiel, prêt pour la Priorité v2

**Fait** (`scoring/p_v2/potentiel.py`, backfillé sur le run candidat, colonnes
annexes — ni p_raw, ni rang, ni tier touchés, testé) :

- **par parcelle** : `potentiel_sdp_m2` (lecture K3 : 0 = réponse, NULL =
  hors_plu seul) · `prix_secteur_eur_m2` (médiane €/m² bâti de la COMMUNE,
  année Y-1 du run, DVF L2-F — la source du modèle) · `valeur_creee_eur` =
  SDP × prix, **intervalle honnête** `[SDP × q1, SDP × q3]` communal ·
  chaque terme nomme sa source dans `p_score_v2_runs.params → potentiel` ;
- **indice d'opportunité** = p_raw × valeur créée, **percentile intra-commune**
  (0-100) — un produit de deux colonnes existantes, aucun nouveau modèle ;
- **accès** (stocké) : `acces_pm_siren` (PM identifiable — les PP restent
  inconnus sans fichiers fonciers) · `acces_courrier` (adresse BAN connue) ·
  « déjà contacté par un compte » : vue `v_parcelle_contact_compte` PAR COMPTE
  (piste CRM ∪ courrier) — **jamais partagé entre comptes** (testé), jamais
  dans les colonnes communes du run. Aucun agrégat anonyme produit.

**Backfillé sur le run q_v12** : valeur créée sur 427 266 parcelles (99 % du
parc — les 4 397 hors_plu restent NULL, honnête), 142 158 à valeur > 0 ;
accès : 72 278 PM identifiables (SIREN), 257 340 courriers possibles (BAN).

**L4.3 — précision@100 de l'indice vs la probabilité seule** (attendu nommé) —
cible réelle du promoteur : vendue 2025 **et** fort potentiel (valeur créée >
médiane communale des valeurs > 0 ; n = 1 219) ; tableau complet
`reports/q-v12/l4_precision_potentiel.csv` :

| | proba seule | indice d'opportunité |
|---|---|---|
| préc@100/commune (médiane, 24) | 0,020 | **0,025** |
| communes où l'indice gagne | — | 9 (égalité 10, perd 5) |

L'indice gagne modestement mais nettement plus souvent qu'il ne perd — la
seconde moitié de « Priorité = mutation × potentiel » est calculée, stockée,
prête pour PALIERS-1. Caveat consigné : la SDP résiduelle est un état statique
(le résiduel au 01/01/2025 n'est pas archivé) — même convention que le modèle.

## L5 — Le retour terrain : commencer à capter

**Fait.** Sélecteur d'un clic (8 états : contacté · pas de réponse · refus
ferme · pas maintenant · ouvert à discuter · en négociation · vendu à nous ·
vendu à un autre) sur la **carte Kanban** ET la **fiche parcelle** (dès que la
parcelle est suivie). Stocké par compte (`pipeline_entries.contact_etiquette`
+ horodatage), **réversible** (« — » efface), chaque geste **journalisé**
(`contact_etiquette_log`).

**L5.2 — cloisonnement écrit et testé** (`tests/test_scoring3_terrain.py`) :
deux comptes réels sur LA MÊME parcelle — l'étiquette de A n'apparaît jamais
chez B (lecture, liste, parcelle), B ne peut pas étiqueter l'entrée de A
(404 : l'existence même est tue), la validation refuse tout état inventé,
le journal trace pose/correction/effacement. Aucun agrégat inter-comptes
n'est produit dans ce mandat (doctrine écrite au code et au test).

**L5.3** — compteur Pilotage : « retours terrain / 7 jours » (+ cumul, seuil
TERRAIN-1 : 200) dans la tuile Veilles, depuis le journal (comptes globaux
seulement).

---

## Clôture

**Tout vert** : tsc 0 erreur · vitest 137/137 · build front OK · pytest
**2 214 passed, 0 échec** (35 skipped d'environnement, comme avant).
14 tests neufs permanents (`test_scoring3_{qv12,featurestore,potentiel,terrain}.py`)
+ la garde sentinelle passée à 65 sources (BDNB).

**Reste** (dans l'ordre du plan v2) : la bascule éventuelle vers q_v12 —
**geste de Vic** depuis Données › Circuit › Basculer (note de version + écart
affichés ; churn 46 %, à lire avant) · PROPRIETAIRE-1 pour le vrai saut (le
plafond sans le bloc propriétaire reste confirmé) · PALIERS-1 pour afficher le
potentiel maintenant calculé · BDNB : la sentinelle préviendra au prochain
millésime, l'ingestion re-sondera la couverture 974 chaque trimestre.

*Harnais : `scripts/audit/scoring/{q_v12_arene,l2_colonnes,l3_bdnb,l4_potentiel}.py`
(rejouables) ; artefacts gelés `reports/q-v12/` ; tests permanents
`tests/test_scoring3_{qv12,featurestore,potentiel,terrain}.py`.
⚠ redémarrage serveur requis (pipeline, API, modèles).*
