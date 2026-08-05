# M32 — Bascule Phase C : BILAN (GO Vic, geste gardé complet)

Intégration AU 21 communes + départage basculée sous le label servi `q_v8_calibre`. Archive de
l'état antérieur : `q_v8_calibre_pre_m32` (par renommage). Geste : `scripts/bascule_m32.py`.

## Conformité (garde centrale)
- **Dry-run préalable** : re-scoring `rebuild=False` sur cache AU reconstruit → **0 écart** vs
  `q_v13_m32_mesure` avant d'archiver quoi que ce soit (dé-risque le demi-état).
- **Bascule** : re-scoring servi → **CONFORME STRICT** à la mesure (0 écart avant registre).
- **Recompte post-bascule vs mesure** : **2 écarts, tous deux au registre** →
  - `97422000AK1442` brûlante → **a_creuser** (piscine FLAIR 88 m², M28)
  - `97419000AL1154` chaude → **a_creuser** (piscine FLAIR 0,888, M32 — décision Vic)
  - **Aucun écart non listé.** Pas de rollback.

## 6 gardes + fraîcheur
disque · péremption · backups · run_absent (label libéré avant re-score) · complétude
(431 663 / 431 663) · **golden régénéré DANS le geste** (`qa/golden_regen.py` → **117/117 PASS**,
seule ancre bougée = `97418000AT2542` chaude→brûlante, la nue confirmée par Vic) ·
**check_fraicheur** : toutes les couches datées dans leur cadence.

## Registre rejoué (boucle générique, 5 entrées, aucun idu en dur)
| idu | origine → servi | nature |
|---|---|---|
| 97422000AK1442 | brûlante → a_creuser | override piscine (M28) |
| 97419000AL1154 | chaude → a_creuser | override piscine (M32, Vic) |
| 97404000AP0323 | brûlante → brûlante | documentaire (CoSIA sous seuil) |
| 97411000HE0234 | brûlante → brûlante | documentaire (badge géométrie N/A, dette #12) |
| 97404000AT0870 | brûlante → brûlante | documentaire (angle mort ortho) |

## Tiers servis (q_v8_calibre après bascule)
brûlante **119** · chaude **1041** · a_creuser 29 974 · reserve_fonciere 2 964 ·
declasse_bati_sature 29 907 · declasse_bati_revele 4 051 · declasse_non_constructible 6 168 ·
declasse_zone_fermee 2 804 · declasse_au_statut_inconnu 210 · declasse_au_fermee 70 · écartée 354 355.
(= mesure moins les 2 overrides piscine : brûlante 120→119, chaude 1042→1041.)

## SDP bâties révélées (correction de mention, tier-safe)
`residuel.py` : `emprise_batie` retient désormais la mesure la plus grande entre BD TOPO et
**CoSIA (parcel_bati_revele)**. Résiduel recalculé pour **8 031** bâties révélées constructibles
→ elles n'affichent plus « terrain nu » mais « bâtie à ~N % de l'emprise constructible »
(ex. 22 %, 54 %, 51 %). Ces parcelles étant déjà déclassées (`declasse_bati_revele`), le résiduel
ne les fait pas entrer en tête → **0 impact tier** (recompte resté à 2). Cache isolé du scoring.

## 3 Salazie hors-PLU (M-A) → outillées
Salazie intégrée (calibration densité 20/20/10 + AU conditionnelle_operation). Sur **441 parcelles
servies**, **0 hors-PLU faisabilité** — les 3 parcelles M-A sont subsumées (commune entièrement
outillée). **4 têtes servies** confirmées, toutes avec résiduel présent :
AV0815 (brûlante, UB) · AL0369 · AL0550 · AV0926 (chaude, UB).

## CY0197 — entrée brûlante (vérif badge)
`97422000CY0197` : servie **brûlante** (rang 163), zone Uc, 868 m². Bâtie (2 bâtiments, emprise
250 m² = 22 %, marginale) ET divisible : faisabilité **R+2, 5-7 logements, résiduel 194 m², étage 3**.
Le profil « bâtie + division possible » est bien porté par la fiche (bâti + faisabilité résiduelle).
**⚠ Discordance notée (hors périmètre, non modifiée)** : le *statut de synthèse* de la fiche affiche
`a_creuser` (« bâti significatif 22 %, occupation à vérifier ») là où le TIER servi est `brûlante`.
C'est le double-rail pré-existant tier de prospection (`parcel_p_score_v2`) vs verdict de fiche
(moteur `score_e`/verdict, qui déclasse le bâti marginal indépendamment). M32 l'a élargi (chaude→brûlante).
Non corrigé unilatéralement (changement du moteur verdict, portée large) — **à arbitrer** : le
verdict de fiche doit-il refléter le tier servi (badge « bâtie mais divisible ») plutôt que déclasser ?

## Dette ouverte
**#13 piscine** (BACKLOG) : le signal piscine ne déclasse pas par règle produit — porté au registre
parcelle par parcelle (a_creuser). Manquant nommé : couche piscine surfacique + seuil.

## Suites (hors geste, non faites)
build-mvt exécuté (tuiles run servi : 431 663 + 6 012 overlays). **Aucun merge** — Vic merge --no-ff.
