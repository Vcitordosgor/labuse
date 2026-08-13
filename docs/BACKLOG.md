 # BACKLOG LABUSE — source de vérité

> Règles : CC met à jour ce fichier à la fin de chaque train (statuts + date).
> Vic arbitre, CC exécute, ce fichier fait foi.
> Statuts : [ ] à faire · [~] en cours · [x] fait · [!] bloqué (dire par quoi)

Dernière mise à jour : 2026-08-06 (M46 ménage) — **VAGUE 2 CLOSE** : M37→M45-B mergés sur main
(6a6e0c17). **Bascule M39 EXÉCUTÉE (06/08)** : règle piscine [15;60] servie → 4 déclassements ;
état servi `q_v8_calibre` : **brûlante 118 · chaude 1 038 · à-creuser 29 978 · réserve 2 964**
(opportunités = brûlantes+chaudes = 1 156). Golden régénéré 117/117. Rail legacy
parcel_evaluations.status éteint (M37) ; filtres & recherche complets (M45/M45-B : 2 voies,
20 facettes SQL, parcel_flags, curseur mode B, ResultsSection unifiée). **Dettes #13 (piscine) et
#14 (double-rail) FERMÉES.** M33 (mode B) + M34/M35/M36 clos avant.
> ⚠ Les effectifs ci-dessus sont un instantané de la bascule M39 (06/08) — à RAFRAÎCHIR à chaque
> bascule (source unique : le run servi). La vitrine Train 8 les LIT du run, ne les fige pas.
**Chemin critique restant : TRAIN 8 (VPS/prod) → premier client.**
Avant client (Vic seul) : SMTP DMARC/DKIM, avocat CGU/CGV.

## M66→M74 — SOURCES & SCORING (le catalogue reflète le produit) [S] Fable
> Le registre ne mentionnait ni aménités, ni piscines, ni équipements — il a fallu fouiller la base.
> M66/M66-B (audit mesuré), M71 (réparation), M74 (fermeture). RAPPORT_M66*.md, RAPPORT_M71.md,
> RAPPORT_SOURCES.md, RAPPORT_M74.md — non commités (mesure) ; branches feat/m71-sources (mergé),
> feat/m74-catalogue (NON mergé).

**Dettes CLOSES (mesurées) :**
- [x] Bandeau « 62 sources branchées » MENSONGER (comptait a_faire/partiel/manuel) → mesuré, filtré
  `connecte` hors doublons : **49** partout (bandeau = accueil, dynamique, M71-A + M74-A/F).
- [x] DPE squelette dans le scoring (13 lignes) → RETIRÉ du scoring, servi en info fiche seule ;
  ré-ingéré 17/17 de son amont réel (le « 913 » ADEME est contaminé 98 % métropole). M71-B1.
- [x] Signaux morts en silence (Renouvellement, entonnoir, pv_candidat) → garde de non-constance.
- [x] BODACC « sondage non démontré » → journal `bodacc_sondages`, **12 605/12 605** couverts. M71-D.
- [x] Trous terrain (8 211) → RÉCUPÉRÉS (parcel_terrain 100 %). M71-E.
- [x] 7 sources branchées absentes du bandeau → 6 requalifiées connecte + la vraie source
  propriétaire **DGFiP parcelles PM** AJOUTÉE au catalogue (elle alimentait la fiche sans y figurer) ;
  « Fichiers fonciers (Cerema) » laissé manuel (couche cascade = 100 % UNKNOWN, convention interdit
  le démarchage). M74-A.
- [x] Écarts résiduels ICPE 1 252→1 261, sols pollués périmètre tranché (casias+instructions+sis,
  exclut conclusions_sup = doublon SUP). M74-B.
- [x] 4 NON MESURÉ levés (Potentiel foncier, ABF/MH, ONF, OCS GE) = tous MAXIMUM. M74-C.
- [x] Page Sources confrontée à la mesure : doublons retirés, notes de proxy visibles, bandeau
  documenté. M74-C bis.

**Dettes OUVERTES (inscrites) :**
- [ ] **Tuilage ortho — végétation manquante** : 5 556 parcelles (1,3 %) hors emprise du tuilage
  IRC/MNH (Sainte-Rose 9,5 % — le pire taux). Neutralisées documentées (motif_absence). Levée =
  étendre `ortho_tiles` sur ces zones puis `labuse vegetation-irc` + `labuse vegetation`.
- [ ] **Gisements dormants** : PVGIS (`parcel_solar` 431 663, table riche score_solaire/prod/facture)
  et Parkings APER (`parkings_aper` 901 ≥500 m²) matérialisés, JAMAIS lus. Statut `partiel — ingéré
  non exploité`. Proposition d'usage fiche au RAPPORT_M74 bloc D — arbitrage Vic.
- [ ] **Session de jugement PV** (M71-B2, GO Vic donné, montage EN PAUSE) : 300 vignettes,
  worktree spin-off, ~320 Mo tuiles. Tant qu'elle n'a pas eu lieu, `pv_candidat` reste hors scoring
  sous exemption datée `NON_CONSTANCE_EXEMPTIONS`.
- [ ] **Doublons bbox spatial_layers** : `foret_publique` 227 lignes = 65 distinctes ; `ocs_ge`
  3 250 = 1 643 distinctes (features à cheval sur 2 communes comptées 2×). Dedup + re-score requis.
- [ ] **ABF endpoint mort** : data.culture.gouv.fr ODS décommissionné (301) → re-sourcer via dump
  data.gouv avant toute ré-ingestion MH.
- [ ] **Golden gelé 07/08 : 33 FAIL préexistants** (la fiche sert `score_v2` aux déclassées que le
  golden gelé attend `<absent>`) — **à rebaser AVANT Train 8** (régénérer la référence sur le run
  servi). Diff M71/M74 = 0 (aucune régression ajoutée).

**Règle ACQUISE (grave, transverse) :**
- **Tout signal du scoring porte un test de NON-CONSTANCE** (garde M71-B3, `check_non_constance`
  au build). Trois signaux étaient morts en silence avant qu'elle existe. Une exemption est DATÉE
  et motivée, jamais un silence.

## M37 — CLOS (mergé 06/08) — bilan qa/m37/M37_BILAN.md

- [x] Extinction rail legacy `parcel_evaluations.status` (option c tracée M34-P0). Lecteurs
      coupés (geojson fallback supprimé → défaut run servi ; assemblage/audit/demo re-sourcés
      tiers), writer gelé (_persist n'écrit plus status), colonne ARCHIVÉE par renommage
      `status_pre_m37` (réversible, 0 donnée détruite). GARDE MÉCANIQUE : dump vigilances
      avant/après = SHA256 identique + diff digests VIDE (431 632 parcelles) → 0 vigilance
      perdue/modifiée/inventée (elles vivent en cascade_results, hors rail).
- [x] matrice_statut assainie : chip « Statut matrice (historique) » + mention TierBadge
      SORTIS ; modules Outils/moteurs/API partenaire basculés sur les tiers (zéro partenaire
      actif — fait maintenant) + étiquette partenaire vraie. Maintenus (étiquette « historique »
      vraie) : légende repli, tuiles MVT, /stats?legacy=1, digest events.
- [x] Lot 0.1 mode B au k€ (point de formatage unique compute_mode_b). Lot 0.2 : « Confiance
      et données » = ICD (19 valeurs, médiane 90) — distinct de la Complétude, GARDÉ.
- Reliquats consignés (bilan) : révision copy narration démo · micro-libellé ICD · digest
      events sur matrice · suppression physique status_pre_m37 (à froid, Vic).

## M36 — CLOS (mergé 06/08) — bilan qa/m36/M36_BILAN.md

- [x] D2/D3 : score d'Opportunité + Complétude RETIRÉS de l'affichage client (exports,
      one-pager, PDF, fiche web, Kanban, Tinder, faits IA) ; calcul conservé en interne.
- [x] Q1/Q2/Q3 : dépassement d'emprise factuel sans inférence · fourchettes à bornes
      identiques → « ~X » · rang sur brûlante/chaude uniquement.
- [x] Étiquettes de source VRAIES : infobulle marqueurs + badge légende (« Classement
      servi »/« Classement historique ») + mention API partenaire + compteur chips projets
      basculé tiers. CAUSE RACINE dev : vite.config.js COMPILÉ masquait le .ts (supprimé,
      gitignoré) + /v2 ajouté au proxy.
- [x] Fiche commune : compteur du tier haut EN DUR (« 103 parcelles brûlantes ou chaudes au
      classement servi », Saint-Denis) — un point de calcul unique partagé avec /communes.
- [x] RR par commune MESURÉ (qa/m36/rr_commune.csv, IC95, harnais gelé) — DÉCOUVERTES :
      RR île défini à l'ordre des ex æquo près (6,66 médian [6,09-7,00] — le 6,73 gelé est
      UNE réalisation → renforce le départage explicite, train 5 N°2) ; label 2025 vivant
      (fenêtre DVF). 14/24 communes non concluantes, 3 RR nuls (Bras-Panon, Cilaos,
      Trois-Bassins) — discours client à calibrer par commune.
- Reliquats consignés au bilan : ~~score_e servi encore bâti sur q_v7_defisc (train 3)~~
  **[CORRIGÉ — audit backlog M48]** : FAUX. `score_e.build_score_e` lit `run=Q_A_RUN_LABEL`
  (point de vérité `config/served_run.txt`) depuis **M44 Lot 0** ; le « q_v7_defisc » était le
  défaut d'argument, aligné en M44. Pièce : `src/labuse/ingestion/score_e.py` (en-tête + signature),
  table `score_e` sans colonne `run_label` (idu-scopée). · payload partenaire matrice + sélections
  modules Outils + digest events + Q/A affichés (PDF/Tinder/fiche) → extinction (c) post-Train 8.

## Régimes de supervision

- [S] Sensible — touche un chiffre servi. Points d'arrêt à chaque étape, arbitrage Vic.
- [A] Standard — features / refontes. UN point d'arrêt final, avec captures.
- [M] Autonome — mécanique. Zéro point d'arrêt, rapport de fin, Vic lit.

## Règles de décision par défaut (valables dans tout mandat)

1. Choix d'implémentation → option réversible, notée au rapport.
2. Chiffre servi touché → s'arrêter, rapporter, attendre Vic.
3. Cosmétique / interne → décider seul, noter au rapport.
4. Ressource ou appel réseau non désigné par le mandat → le dire avant.
5. Livrable annoncé = livrable vérifié (ls -la avant d'annoncer un chemin).
6. Jamais de merge. Commit + push sur branche dédiée. Vic merge en --no-ff.
7. Revue visuelle obligatoire avant toute exposition d'une surface servie.

## TRAIN 1 — PONDERATION [S] Fable — PRIORITAIRE
- [x] Option B : pondération au_sous_plancher ×(1−manque/seuil) — implémentée (facteur_ponderation + _pondere_au_sous_plancher, même point de calcul que la mention, kill-switch LABUSE_DISABLE_AU_POND), tests verts. **NON basculée** (point d'arrêt).
- [x] Mesure d'effet : population réelle 1 069 (les 708 + calibrations depuis). 117 mouvements : 38 sorties de tête sous-plancher, 0 entrée indue, 44 entrées mécaniques (rangs libérés), effectifs stables (brûlantes 120). Contrôle ≡ servi à 2 exceptions près (les manuelles). Cartes ortho IGN des 82 mouvements en tête. Rapport : docs/mandats/TRAIN1_PONDERATION_RAPPORT.md.
- [x] **Bascule pondération SERVIE (GO Vic 04/08, AB1908/AB1910 tiennent)** — remplacement sous label (scoring v2 épinglé Q_A_RUN_LABEL), archive par RENOMMAGE q_v8_calibre_pre_pond (rien détruit, rollback: scripts/rollback_ponderation.py), 5 gardes passées, conformité STRICTE à la mesure validée (écart unique = CH1893). Tiers servis : 119 brûlantes, 1 038 chaudes. MVT rebuildées. Golden 116/116 PASS (référence régénérée — elle était restée sur q_v7, dette v8 réparée ; 84 ancres préservées, diff versionné).
- [x] CX2555 **levée** (servie au naturel : a_creuser rang 427 206, plus d'exception au journal du run servi).
- [x] Dette #4 : 46 suspectes mesurées (13 brûlantes, 19 chaudes) — revue Vic APRÈS AB1908/AB1910, rien de déclassé d'ici là. Profil sectoriel mesuré (arbitrage 4) : 1 061 parcelles-trou (piscine × couche <20 m²), 456 secteurs, 24 communes — 39 secteurs = 25 % du volume, 111 = 50 % : points chauds réels (Saint-Paul 188) mais dette DIFFUSE → rechargement par commune plutôt que par secteur.
- [x] CH1893 : **pérennisée (validé Vic 04/08)** — motif mis à jour dans served_run_exceptions : « couche bâtiment lacunaire, vérifié ortho 04/08, à lever au rechargement de la couche », lié à la dette racine train 5.
- [x] Purge post-bascule faite : q_v9_pond_avant/apres + orphelin q_v9_avant (1,29 M lignes). L'archive q_v8_calibre_pre_pond est CONSERVÉE (c'est le rollback) — à purger quand Vic déclarera la pondération stable.
- [x] Inventaire des tables run-scopées mortes en silence (consigne Vic) : parcel_renouvellement (q_v7), entonnoir_motifs (q_v2/q_v6), ia_cache (q_v6/q_v7, cache) — consigné en tête du train 5, garde #6 posée côté golden. **TRAIN 1 CLOS.** — **[MAJ M47/M48]** : `parcel_renouvellement` et `entonnoir_motifs` ne sont PLUS sur q_v7/q_v2 — **rebâties sur `q_v8_calibre`** (renouvellement câblé au geste `build-mvt` en M47 ; entonnoir monte avec le scoring). Pièces : DB (67 258 lignes q_v8 ; entonnoir 317 lignes q_v8), commits `[M47-P1]`/`[M48-P2]`.

## TRAIN 2 — TECH [M] Opus — en parallèle de tout
- [x] Rebase + push EXPRESS-01 : EXPRESS-01 (485f7a9) déjà mergé dans main → fast-forward. 3 poses IDU (Fiche/Tinder/Kanban) déjà servies ; 4e pose (gen_tops) livrée avec les tops ci-dessous.
- [ ] Merge fix/m13-e (Vic merge), puis rebase EXPRESS-01 dessus — action Vic, non faite par CC.
- [x] Régénérer les tops : IDU complet + run servi (Q_A_RUN_LABEL au lieu de q_v2 gelé/absent). 25 HTML (24 communes + top50) régénérés sur q_v8_calibre, générateur + HTML commités ensemble.
- [x] Gardes de bascule → briques importables (module src/labuse/bascule_gardes.py) : 5 gardes extraites VERBATIM, bascule les importe, aucune logique recopiée. Tests verts.
- [x] **GARDE #6 (consigne Vic 04/08) : toute bascule régénère le golden dans le même geste** — check_golden_regenere ajoutée au module (refus BRUYANT si la référence cite un autre run que le servi), branchée dans bascule_ponderation.py et bascule_v8_calibre.py, 3 tests. Le golden resté sur q_v7 pendant la bascule v8 était une dette de process, pas un incident.
- [x] Requête A1.3 : 0 IDU manquant. Sans adresse BAN, mesuré sur le CHAMP adresse de la fiche (déf. Vic, API servie) : **brûlantes 39,3 % (46/117)**, **top-1000 rangs 41,0 %**, île 40,4 %. **PAS un non-sujet en tête** : 46 brûlantes affichent « Adresse non disponible ». Les 5,3 %/0 % provisoires ne se reproduisent pas. → train 4 (change d'ampleur). Détail : docs/mandats/A1_3_IDU_ADRESSES_MANQUANTS.md.
- [x] Purge des jetables q_v8_au_* : déjà absents des 11 tables run-scopées (vérifié par balayage) — rien à purger, scripts QA conservés.
- [x] Drapeaux EBC/ER sur fiche (dette #10) : badge « partiellement en EBC (~N%) » / « emplacement réservé n°X », information seule (jamais exclusion), dérivé du frontend. Captures avant/après : reports/train-tech/ebc_er/.

## TRAIN 3 — PROD-CHECKS [M] Opus
- [x] Check sécurité : /docs, LABUSE_SECRET_KEY, en-têtes, endpoints — M31 : posture saine (docs local-only, secret fail-closed, admin middleware-gated, CORS restreint prod, .env jamais commité) ; garde test admin ajoutée. Voir qa/m31/M31_RAPPORT.md §PC2.
- [x] Check vitesse (endpoints clés, top 5 lent) — M31 : 5 endpoints servis < 1 s ; pas de N+1 fiche. Reste `/map/parcels.geojson` commune = 2,2 s sur Saint-Denis (candidat MVT commune). §PC3.
- [~] Test architecture mail : M31 — SPF ✓ ; **DMARC ABSENT** (à créer, `p=none` d'abord) ; **DKIM non aligné** (envoi Gmail perso `d=gmail.com` ≠ From `labuse.immo`). DNS/ops, hors code. Preuve qa/m31/preuve_dns_mail.txt. §PC4.
- [~] Inventaire des API déconnectées — M31 : cross-réf textuelle NON fiable (faux positifs massifs, ma propre erreur sur /map/parcels.geojson) → PAS de liste publiée. Exige une passe de **traçage par helper** api.ts. Seul candidat avéré : `/api/v1/*` (API partenaire externe, caller-less par conception — ne pas retirer sans savoir si un partenaire consomme). §PC4.
- [x] **[S] Vic — bascule run servi (révélé + CORRIGÉ M31)** : point de vérité UNIQUE versionné `config/served_run.txt = q_v8_calibre`, lu par backend + bundle (vite) + build-mvt. `LABUSE_SERVED_RUN` = override dev loggé WARNING. Suite verte sans env, golden 117/117, run servi identique (plomberie). §ANNEXE CORRECTION RUN SERVI.
- [ ] **[A] Passe helper-tracing des routes mortes** (déférée de M31) : résoudre chaque fn api.ts → chemin, tracer les appels, + fetch directs + cron/webhook/PDF, avant tout retrait.
- [x] ~~**Cohérence run des builders de signaux dérivés** (relevé M31) : `score_e.py:158` et `pc_caducs` ont un défaut d'argument `run="q_v7_defisc"` en dur~~ — **[RÉSOLU / relevé M31 FAUX — audit backlog M48, sur pièces]** : (1) `score_e` lit `Q_A_RUN_LABEL` depuis **M44 Lot 0** (le défaut q_v7_defisc a été aligné) ; (2) `pc_caducs` **ne dépend d'AUCUN run** — `pc_caducs.py:5-7` documente que la note « run servi q_v7_defisc » de M31 était fausse (le builder lit les permis + l'univers `parcels`, pas `parcel_p_score_v2`). Aucune des deux tables n'a de colonne `run_label`. Aligner un run ici est **sans objet**. Pièces : `src/labuse/ingestion/score_e.py`, `src/labuse/ingestion/pc_caducs.py`. (Doctrine : une note de backlog n'est pas une source — se vérifie sur pièces.)

## TRAIN 4 — FILTRES / RECHERCHE [A] Opus
- [ ] Inventaire filtres : lesquels existent, marchent, mentent
- [ ] Architecture 2 voies : filtrer soi-même OU analyse LABUSE
- [ ] Filtrer sur tout (toute variable exposée)
- [ ] Théâtre de l'analyse : compteur en direct
- [ ] Tout montrer : l'écarté consultable avec son motif
- [ ] Filtrabilité par motif de déclassement (dette des 427)
- [ ] Fiche (surface) : adresse absente — (a) afficher « Adresse : Absente (BAN) », jamais un champ vide ; (b) ampleur RÉELLE (mesurée) : 46/117 brûlantes et 41 % du top-1000 sans adresse → enrichissement adresse sur les têtes, pas qu'un habillage (cf. A1.3)
- [ ] Fiche (surface) : sous une surface plancher (à définir), dire « délaissé » au lieu de dérouler un bilan — anomalie AI1886 : bilan R+6 servi sur une parcelle de 9 m²
- [ ] Passe de clarté générale
- [ ] Vocabulaire produit (revue M30, 05/08/2026) — 5 libellés consignés, arbitrage Vic requis
      avant tout geste (3 autres corrigés au geste M30-revue : fermée à l'urbanisation,
      inconstructible (géométrie), AU statut suffixé) :
      · « Réserve foncière » (PRIORITAIRE : collision avec l'emplacement réservé PLU — c'est un tier)
      · « À creuser » (générique — garder si assumé)
      · « Viabilisation confirmée par les faits » (« confirmée » = faisceau ≥70 pts, pas certitude)
      · « Brûlante » (métaphore assumée produit)
      · « Potentiel ≥ /100 » (potentiel de QUOI = Score Q ; tip E1 M12 déjà présent)

## TRAIN 5 — SCORING [S] Fable
- [~] **N°1 — COUCHE BATIMENT : pilote CoSIA rendu, cartes DATÉES servies — attend contre-revue Vic des 14 + arbitrage GO.** Rappel brut 79 % / ajusté 100 % (les 8 « ratées » = erreurs de vérité terrain, contre-revue : pilote_cosia_discordances.pdf, cartes datées). **Correction 2ᵉ passe : l'ortho de revue N'ÉTAIT PAS périmée** (graphe de mosaïquage : les 14 zones = PVA 2025, vols 21/07-02/08/2025) — les divergences sont des différences de LECTURE (chantier/dalle vs Bâtiment ; produit-parlant CoSIA a raison), le 38 % reste LE taux. **Seuil 50 RÉFUTÉ par la mesure** (rappel 63 %, perd 6 vraies maisons à 23-45 m²) → seuil 20 conservé, cas limites à l'adjudication. Architecture validée : p_model_bati_cosia datée, max des deux emprises. AB1908 : à re-trancher par Vic (structure visible carte datée, CoSIA 160 m²) ; AB1910 confirmée nue (CoSIA 0). Effet Saint-Paul : 73/169 (43 %). Inventaire rétroactif : 0 revue à refaire pour cause d'ortho. RIEN branché.
- [~] Les 90 têtes vues bâties par le cadastre (2026-06) : revue-exceptions SANS déclassement automatique — cartes O12 en génération pour revue Vic (le cadastre ne voit que 3 % de l'angle mort et peut se tromper dans l'autre sens).
- [ ] Entretien (validé Vic, APRÈS le pilote) : BD TOPO trimestrielle avec dates conservées (code fait : ingest_batiments garde date_creation/date_modification/date_d_apparition/date_de_confirmation) + RNB pour l'ID pivot.
- [ ] **N°2 — Saturation p=1,0** : 5 parcelles à p_raw=1,0 exact aux rangs 1-5 → le sommet du classement est un ex aequo départagé par un tri arbitraire (sujet de CRÉDIBILITÉ : le « n°1 de l'île » doit être le meilleur, pas le premier d'une égalité). Mesures : (a) combien de parcelles p_raw ≥ 0,99 et leurs rangs ; (b) « permis < 2 ans » (+1,30) seule cause ? ; (c) si on la plafonne, le top 20 change-t-il d'ordre ? ; (d) départage EXPLICITE des ex aequo (surface, faisabilité, charge foncière).
- [x] ~~**N°3 — Rebuild parcel_renouvellement sur q_v8_calibre** : actif unique du positionnement (68 445 parcelles, 0 concurrent), mort en silence depuis la bascule v8~~ — **[FAIT / prémisse FAUSSE — M47, sur pièces]** : la table n'était PAS morte — **déjà rebâtie sur `q_v8_calibre`** (constat M47-P0 : reproductible bit-à-bit). Compte réel **67 258** (pas 68 445 — chiffre historique d'un dataset antérieur). **Câblée au geste `build-mvt`** (`tiles.rebuild_mvt_servies`, M47/M48) + garde de cohérence. `entonnoir_motifs` : **pas morte** non plus (317 lignes q_v8, monte avec le scoring). `ia_cache` = cache (inchangé). Doctrine appliquée. Pièces : commits `[M47-P0..P2]`, `qa/m47/`, DB. Dette nommée restante : **stamper + câbler les CLI isolées** (`score_e`, `division_or_candidates`, sans `run_label`).
- [x] Étapes exactes de l'algo : docs/mandats/ALGO_ETAPES_EXACTES.md (9 étapes, fichier:ligne, 4 parcelles témoins, seuils vivants).
- [x] PHASE 2 RENDUE (6 audits, lecture seule, rien modifié — docs/mandats/train5/) : AUDIT1 saturation (3 à p=1,0 MAIS **top 1000 = 19 valeurs de p, 988/1000 ex aequo, palier de 514 — coupures de tiers en plein palier** ; départage explicite proposé) · AUDIT2 renouvellement (rebuild à blanc : 67 258, ~2 min, sans risque) · AUDIT3 entonnoir (317 lignes, secondes) · AUDIT4 P/C (+ bâties-connues : 8 brûlantes + 432/1043 chaudes (41 %), portées par tenure/permis et même la feature piscine +0,41 — le filtre doit être une règle produit, pas un poids) · AUDIT5 cartographie (motifs 100 % reconstructibles sur 50 000 testées ; trous : params de coupure non persistés, ordre intra-palier) · AUDIT6 SDP bâties (5 132 parcelles affichent 3,48 M m² de SDP terrain-nu-théorique ; recalcul = bascule complète type v8). **POINT D'ARRÊT — phase 3 sur arbitrages.**
- [ ] Dette #4 : filtre client bâti + hiérarchie par année (DPE/BDNB)
- [x] Dette #9 FERMÉE (signal servi, arbitrage b, 05/08) : parcel_entree_tete (514 entrées tracées via la chaîne d'archives), libellé factuel « entrée en tête à la bascule du JJ/MM — signal inchangé/en progression » (Sourcé), fiche seule, 0 effet de classement. À recalculer au geste de chaque bascule.
- [x] Dette #11 FERMÉE pour la part PM (signal servi, arbitrage b, 05/08) : parcel_acquerabilite 3 états factuels (même propriétaire PM 329 / distincts 46 / non déterminable 685) sur la mention assemblage, Sourcé SIREN DGFiP-Cerema (millésime amont non tracé → Estimé affiché, champ prévu). 0 effet de classement.
- [ ] Dette #11-PP (DISTINCTE, maintenue) : acquérabilité des personnes physiques NON déterminable — manquant nommé : source de propriété PP inexistante en open data (anonymisation DGFiP). Structurel.
- [x] **Dette #13 FERMÉE (bascule M39 exécutée 06/08)** : le signal piscine est passé de « registre parcelle par parcelle » à **RÈGLE PRODUIT servie** (seuil [15;60] m²) → 4 déclassements à la bascule (brûlante 119→118, chaude 1041→1038, à-creuser 29974→29978), golden régénéré 117/117. Le registre `served_run_exceptions` n'est plus le porteur du signal piscine. (Historique : ouverte M32 ; entrées AK1442/AL1154 désormais couvertes par la règle.)
- [x] **Dette #14 FERMÉE (M34, mergé 05/08, option a — dérivation totale)** : le verdict de
      fiche est désormais une TRADUCTION du tier servi (`src/labuse/verdict_servi.py`, point de
      calcul unique) sur TOUTES les surfaces non-v2 (fiche legacy, exports/one-pager comité,
      comparateur, assistant IA, shortlist, Kanban, voisinage, /parcels et /stats fallback,
      enrichment). Le rail cascade legacy ne pilote plus aucun verdict (signaux non-francs =
      vigilances). Constat P0 : le moteur divergent était le rail cascade
      (`parcel_evaluations.status`), PAS `score_e` ; ampleur réelle 3 251 déclassements
      silencieux (97/119 brûlantes) + 2 263 divergences MONTANTES. Re-mesure : 0 divergence
      dans les deux sens (1 071 fiches). CY0197 = Brûlante rang 163 + badge « bâtie + division
      possible ». Bilan : qa/m34/M34_BILAN.md. RELIQUATS tracés au bilan : (c) extinction du
      rail legacy post-Train 8 · compteurs /communes encore sur matrice_statut (même
      incohérence côté chiffres, arbitrage Vic) · golden 115/117 (2 champs residuel, écart
      externe hermes — writer désactivé, RÉGÉN RÉFÉRENCE À M35).
- [ ] Cartographie retenue/écartée : motif traçable par parcelle
- [ ] Anomalie AT1740 : « constructible N » + SDP 2 689 m² en zone N + 19-22 logts, ET deux SDP différentes sur la même fiche (2 689 vs 2 827). Mesurer : combien de zones N servent une SDP > 0 ? Localiser la violation du point de calcul unique.
- [ ] Revue de code intégrale (propositions, rien d'appliqué)

## TRAIN 6 — CALIBRATION-14 + ANNUAIRE [S] Fable — fil continu
- [ ] Re-télécharger les archives manquantes (parallèle, sha vérifié)
- [ ] Extraction exhaustive des 14 communes restantes
- [ ] Saint-Benoît : 19 fiches annexes une à une
- [ ] Saint-Paul → fermee + scan formulations (20 communes)
- [ ] Saint-Leu : calibrer depuis le règlement 2013
- [ ] OAP : extraire et brancher (prévalence)
- [ ] Annuaire PLU interrogeable (verbatim + article + page + lien)
- [ ] Garde-fou fraîcheur GPU-vs-mairie
- [ ] Rebuild + re-score final post-calibration (bascule, 5 gardes)

## TRAIN 7 — MODE B [A] Opus — CLOS (M33 mergé 06/08)
- [x] Mode B réhabilitation 24/24 SERVI (M33, bilan qa/m33/M33_BILAN.md) : population = 2 tiers
      déclassés bâti (33 958 = saturé 29 907 + révélé 4 051 ; les « 8 031 » M32 incluaient la
      bande adjudication non déclassée). Sortie = prix d'achat max réhab (homogène mode A),
      briques mode A réutilisées (coef CA, préséance prix secteur→commune), TOUJOURS Estimé
      (paramètre travaux défaut 1 500 €/m², bornes 500-4 000, jamais persisté). Étiquettes
      PAR composante, niveaux Sourcé/Estimé visibles par parcelle. Bilan négatif dit
      honnêtement. Tiroir de fiche subordonné au verdict M34 + exports + assistant. 0 tier
      touché, golden 117/117, non-persistance prouvée.
      RELIQUATS : locatif/défisc = vague 2 pré-client (dette q_v7_defisc) · Q6 close
      (v1 = zéro reclassement ; tout mode B CLASSANT futur exige une dimension parcellaire
      discriminante : prix d'acquisition observé, état du bâti).

## TRAIN 8 — VPS / PRODUCTION [A] Opus — dernier avant client
- [ ] Déploiement VPS + Caddy + certificats + SECRET_KEY
- [ ] Licence nominative, session concurrente unique
- [ ] Stripe live + page tarifs réelle
- [ ] Site vitrine labuse.immo à jour
- [ ] Discours commercial

## Vic seul (hors trains)
- [~] Réponse mairie Saint-André (relancer si silence)
- [ ] Mairie Saint-Benoît : modifs n°2 et n°3
- [ ] Avocat CGU/CGV
- [ ] Appel promoteur : coût construction → Sourcé
- [ ] Décision exposition O12 · mode D · C5 · EnR

## Dettes (index)
#4 bâti · #9 mérite/héritage · #10 EBC/ER · #11 acquérabilité ·
geometrie_drapeau · fraîcheur GPU-vs-mairie · couche batiment lacunaire · #12 voirie surfacique absente (HE0234, M-C.4) ·
#13 signal piscine (registre a_creuser, pas encore une règle produit) ·
#14 double-rail verdict/tier FERMÉE (M34 05/08 — traduction unique verdict_servi ; M35 a soldé : golden régénéré 117/117, compteurs /communes sur tiers ; reliquat : rail legacy à éteindre post-Train 8) ·
exceptions actives (run servi) : CH1893 + les 14 bâties de la revue dette #4
(CX2555 levée le 04/08 à la bascule pondération)

## Site marketing + perf sites + gelés (transmis Vic, post-M32)
- [ ] **Split app / marketing** : séparer l'application (produit scoré) du site marketing (vitrine
  labuse.immo). Deux surfaces, deux cycles de déploiement.
- [ ] **Chiffres à afficher sur la vitrine** (état servi `q_v8_calibre` après **bascule M39, 06/08**) :
  431 663 parcelles · **118 brûlantes · 1 038 chaudes** · 29 978 à creuser · 2 964 réserve foncière
  (opportunités = 1 156). ⚠ **À DÉRIVER du run servi au build de la vitrine, ne JAMAIS figer** — ces
  chiffres bougent à chaque bascule (source unique : le run). Le nombre ci-dessus n'est qu'un repère daté M39.
- [ ] **Perf sites (Lighthouse)** : passer app + marketing au crible Lighthouse (perf/SEO/a11y),
  budget de perf déclaré. À faire avant exposition client.
- [ ] **MoteurImmo : GELÉ** — ne pas reprendre l'intégration/compat MoteurImmo (décision Vic).
- [ ] **Reco Urbanease** : recommandation à formaliser (positionnement / différenciation vs Urbanease).
- [ ] **Saint-Paul : référence à DÉCLARER CLOSE** — la commune de référence Saint-Paul est traitée ;
  acter sa clôture (plus de point ouvert dessus) pour ne pas la rouvrir par inadvertance.

## Doctrine (leçons gravées)
- **Archives de bascule `q_v8_calibre_pre_*` = DÉPENDANCE PRODUIT, pas des déchets (Vic 06/08, M46)** :
  « Les archives de bascule `pre_*` ne sont pas des déchets purgeables : la chaîne d'archives est la
  source du signal `parcel_entree_tete` (dette #9). Toute purge exige d'abord de matérialiser
  l'historique ailleurs — mandat dédié, pas un geste de ménage. » Concrètement : `lignee_tete.py`
  `CHAINE_GESTES` lit `pre_pond`/`pre_regle`/`pre_m28` (+ le run servi) pour bâtir l'entrée-en-tête.
  GARDE : `scripts/m46_purge_runs.py` REFUSE dynamiquement tout label présent dans `CHAINE_GESTES`.
  (M46 : seul `pre_m32`, hors chaîne, a été purgé ; `pre_m39` conservé = rollback.)
- **Frontière modèle/règles (Vic 04/08, prouvée par la mesure piscine)** : « Le modèle prédit
  la mutation, il ne juge pas l'état de la parcelle. Tout ce qui relève de l'état (bâti,
  zone, statut) est une règle explicite, jamais un poids. »
- **RÈGLE DE CONCEPTION (Vic 04/08, 3 occurrences en une semaine — PLU GPU-vs-mairie, bâti
  BD TOPO-vs-cadastre triennal, ortho de revue) : « La fraîcheur d'une donnée est celle de sa
  source amont, jamais celle de son ingestion ni celle du moment où on la regarde. »
  EXIGENCE TRANSVERSE : toute couche servie porte la date de sa source amont, AFFICHÉE.**
  Audit 04/08 + mesures DVF (DVF_FRAICHEUR_MESURES.md) : **DVF est À JOUR au dernier millésime
  publié** (7 184 = 7 184 mutations 2025, vérifié au fichier ; le « retard » est le cycle
  semestriel de la source, ~3 273 mutations S1-2026 en attente d'octobre) MAIS **la tuile
  Marché sert la médiane SANS étiquette de fraîcheur** (le bandeau « ventes jusqu'à… » n'est
  que dans le tiroir Bilan) — et un cycle déplace les médianes de ±10-20 % dans plusieurs
  communes. Sitadel : parse corrigé (validation date, future→NULL tracée+compteur bruyant,
  ligne fautive neutralisée, 0 date future en base). DPE/BODACC sains. **SPEC millésime amont
  RÉDIGÉE (SPEC_MILLESIME_AMONT.md) — attend lecture Vic, rien d'implémenté.**
  Corollaire outillé : dates BD TOPO conservées à l'ingestion (fait) ; date de prise de vue
  affichée sur toute carte de revue (fait — helper qa/dette4/ortho_dates.py).
- **« Une détection d'indice ne prouve pas l'absence d'indice. »** (Vic 04/08 — le filet
  piscine/PV/DVF a ses propres trous, cas #079.) Ne jamais conclure « pas d'indice donc
  pas de bâti ».

## Mandat séparé — flux IA (issu de M62-P1, arbitrage rail)
- **Câbler l'amorce `entretienDirect` dans `CopiloteView`, puis RETIRER `IAStub`.** M62-P1 a
  renommé l'entrée rail « Copilote »→« IA » (étincelles) et laissé l'entrée `IAStub` sous le nom
  « Recherche », car le Copilote NE couvre PAS encore ce que fait IAStub : la recherche
  `/ia/search` (NL→filtres) ET l'entretien projet (`ProjetEntretien`, armé par `ouvrirEntretien`
  → view:'ia'). `CopiloteView` a un `brief` local vide et ne lit pas `entretienDirect`. Étapes du
  mandat : (1) faire lire `entretienDirect` par CopiloteView (préremplir le brief) ; (2) porter la
  recherche `/ia/search` dans le Copilote (ou l'assumer retirée) ; (3) retirer l'entrée rail
  « Recherche » + la vue `ia`/`IAStub` + rerouter `ouvrirEntretien` vers 'copilote' + les ~15 QA
  `setView('ia')`. C'est un flux, pas de la présentation → hors M62.
