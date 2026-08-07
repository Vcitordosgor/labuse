# M48 — BILAN · Audit de cohérence globale (« LABUSE ne dit jamais deux choses »)

**Branche** `m48-coherence-globale` (pas de merge). Grille outillée **26 parcelles × 8 surfaces**,
rejouable (`qa/m48/audit_grid.py`, `LABUSE_DEV_MODE=1 labuse api` puis le script). La grille est un
**actif** — elle resservira à chaque release.

## Résultat central (la question de Vic)

**Sur une même parcelle, aucune surface ne dit deux chiffres contraires — désormais vérifié.**
- **Prix identiques partout** : CA et charge foncière `compute_bilan` — module == fiche legacy ==
  one-pager, **20/20 parcelles, 0 divergence** (jamais touché : c'était déjà sain).
- **Verdict unifié** : tier/rang/mult via `verdict_servi`/`tier_v2` (M34) — fiche V2, fiche legacy,
  exports, DB **cohérents 26/26**. Le « verdict split V2/legacy » craint est **infirmé sur pièces**.
- **Grille finale : 0 divergence G1.**

## Les 3 contradictions trouvées — toutes corrigées

| # | Défaut | Correction | Preuve |
|---|---|---|---|
| **F1** | **L'IA annonçait un classement CONTRAIRE à la fiche** (brûlante → « écartée ») : `fiche_ask.py:130` passait le champ mort `statut` (matrice v1) ; le vrai tier absent du contexte IA. 71 115 parcelles. | `statut_tier = verdict_servi(...)` + `rang_classement`. Test de non-régression. | live AT2542 : « écartée » → **« Brûlante… rang 14 »** ; AP1610 → « Chaude… rang 3 ». `preuves_ia_apres/` |
| **F2/F3** | **Carte périmée** : 4 tiers + 7 854 SDP divergents (tuile vs fiche). | **Cause = M39 basculée sans `build-mvt`** (cf. investigation). `build-mvt` **rejoué** (ta main) → **drift 0/0**. Câblé au geste + garde de péremption. | `check_peremption_tuiles` ✓ live (mvt 16:30 > amont 00:17) |
| **F4** | Champ mort `statut`/`status` (matrice v1) exposé fiche V2 + tuiles (munition de F1). | **Retiré** partout (payload, build_mvt, props, front, golden_check) + **golden régénéré**. | fiche sans `statut` ; golden **117/117** |

## L'investigation hors cadre (le vrai apprentissage)

En posant le gate golden, découvert que le run servi `q_v8_calibre` avait été **re-scoré**
(07/08 00:17 +04 = **06/08 22:17 +02**, la veille). Établi sur pièces : c'est la **bascule M39**
(même `model_sha256`, mêmes params que `pre_m39` ; les **4 idus documentés** AR1289/BV0606/CX0650/
AC2215 déclassés ; agrégat **119→118 brûlante, 1041→1038 chaude** ; 0 p_raw/rang). **Légitime,
bénie par Vic** — pas de rollback.

**Le défaut n'était pas le re-score mais un trou de PROCESS** : la bascule M39 a régénéré le
golden **mais pas les tuiles**. Constaté : **AUCUN** des 6 scripts bascule n'appelait `build-mvt` —
tous imprimaient « SUITE : build-mvt » en TODO manuel. **Corrigé** (doctrine « un geste = tout ou
rien ») :
- `tiles.rebuild_mvt_servies()` = **point d'orchestration unique** (tuiles + overlays + parcel_flags
  + renouvellement + mvt_meta + **garde de péremption**) ; le CLI `build-mvt` n'en est qu'un appelant.
- Câblé **dans le geste** : `bascule_m39.py` (7bis) + `bascule_v8_calibre.py` (modèle commun).
- `check_peremption_tuiles()` : `mvt_date < dernier re-score/résiduel → alerte bruyante`. Elle
  **détectait** l'état périmé (retard 1487 min) — le garde-fou qui a manqué le 06/08.

Les 3 dérives golden `n_lignes_cascade` (114/117 au départ) = **dédup contraintes M46** (mergée
après la régén du 06/08) — `AC0156` est le témoin nommé dans le code. Absorbées par la régén F4.

## Points annexes du mandat — tous soldés

- **EP0228** (piscine, dossier M40) : aucune vigilance car M39 sert le déclassement mais **aucune
  couche piscine n'est exposée en vigilance** — EP0228 qualifie (en bande, contenue) ; **aucune
  surface ne se contredit** → cohérent, non-issue.
- **Renouvellement « 0 retenue » — FAIT** : mention posée (FiltreLabuse) quand le filtre est actif —
  *« Segment consultable via la voie manuelle — coupez l'Analyse LABUSE… écartées par conception
  (d'où 0 retenue) »*. Capture `captures/mention_renouvellement.png`. tsc vert.
- **Backlog — FAIT** : les 5 affirmations factuelles fausses corrigées dans `docs/BACKLOG.md`,
  chacune avec sa pièce : score_e « q_v7 » (→ Q_A_RUN_LABEL M44) · pc_caducs « q_v7 » (→ aucun run,
  M44) · renouvellement « mort » (→ q_v8 67 258, M47) · « 68 445 » (→ 67 258) · entonnoir_motifs
  « mort » (→ 317 lignes q_v8).

## Vérification (gate du mandat)

| Gate | Résultat |
|---|---|
| **Golden** | **117/117** (régénéré, 84 ancres préservées, 0 triplet bougé) |
| **Grille finale G1** | **0** |
| **0 tier modifié** | oui — F1/F4/gardes/wiring ne touchent ni scoring ni tiers (le re-score M39 est antérieur, béni) |
| re-mesures M34/M35 · SHA256 vigilances M37 | intacts (aucun code verdict/vigilance touché) |
| Tests | **63/63** (F1 lock 2 · péremption 5 · coherence/serving/gardes/renouv/mvt/m45) |

## Reste (à ta main — rien de bloquant)

1. **Bundle front** : `npm run build` au prochain déploiement (embarque F1/F4 + la mention ; tsc vert).
2. **Colonne `mvt_parcels.status` vestigiale** : disparaît au prochain `build-mvt` (build SQL F4) —
   déjà non servie (props l'excluent). Rien à faire d'urgent.
3. **Dette nommée** (déjà consignée M47, rappelée au backlog) : **stamper + câbler les CLI isolées**
   (`score_e`, `division_or_candidates`, sans `run_label`) — mandat futur.

## Annexes (.csv.gz — la grille est un actif de release)
- `M48_P0_PROTOCOLE.md` · `M48_P1_RAPPORT.md` · `M48_RESCORE_INVESTIGATION.md` · `M48_P2_STATUS.md`
- `select_sample.py` · `audit_grid.py` · `echantillon.csv`
- `grille.csv.gz` · `divergences.csv.gz` (0 G1) · `pieges_latents.csv.gz` · `findings.csv`
- `preuves_ia/` (avant) · `preuves_ia_apres/` (après F1) · `F4_staged.patch` (appliqué)

**Pas de merge — la main reste à toi.**
