# RAPPORT M71 — Phase 1 : réparation du catalogue et du scoring (suites M66/M66-B)

Branche `feat/m71-sources` depuis `main` (`c3a977bc`, M60 mergé — précondition corrigée par Vic :
« M70 » était une coquille). **Un commit par bloc, A → E + F. NON MERGÉ.**
Deux STOP d'arbitrage restent ouverts : **B2 (pv_candidat)** et **F (chiffre vitrine)**.

| Bloc | Commit | Contenu |
|------|--------|---------|
| A | `07375f66` | bandeau Sources honnête + requalifications catalogue |
| B | `fa454153` | DPE hors scoring + garde non-constance + mesures B2 |
| C | `2d8fd84a` | Saint-Philippe : l'aveuglement se dit |
| D | `000e0901` | journal BODACC + backfill 12 605/12 605 |
| E | `277a3394` | trous terrain récupérés / végétation neutralisée documentée |
| F | `847e9376` (amendé) | recomptage vitrine + rapport + ajustement test induit par A |

---

## BLOC A — Cesser de mentir au client

**Avant (mesuré M66)** : `/sources` servait les 62 lignes du catalogue sans filtre ; le bandeau
affichait « 62 SOURCES BRANCHÉES » en comptant 4 a_faire + 4 partiel + 2 manuel.

**Corrections** :
- `/sources` filtre `status='connecte'` (app.py) — comptage 100 % dynamique, aucun chiffre en dur.
- Statut **`hub`** ajouté à l'énum (colonne varchar, aucun DDL) ; front : pastille + badge « doublon ».
- Les lignes marquées `DOUBLON de …` restent listées (traçabilité) mais sont **exclues des comptages**.
- `seed_sources.py` aligné (source de vérité à tout re-seed). PVGIS/EDF/ODRE (48/49/50) sont HORS
  seed (insérés ad hoc — dérive constatée, requalifiés par UPDATE seulement).

**Journal des requalifications (avant → après → raison)** :

| id | Source | Avant | Après | Raison |
|----|--------|-------|-------|--------|
| 23 | ZNIEFF | connecte | **a_faire** | 0 donnée, 0 usage (M66-B) |
| 49 | EDF SEI | connecte, last_sync 11/07 | **a_faire**, last_sync **NULL** | 0 donnée ; fraîcheur sur du vide = faux positif |
| 50 | ODRÉ | connecte, last_sync 11/07 | **a_faire**, last_sync **NULL** | idem |
| 11 | Région Réunion OD | connecte | **hub** | un portail n'est pas une source |
| 14 | Géoplateforme IGN | connecte | **hub** | idem |
| 48 | PVGIS | connecte | **partiel** | ingéré (parcel_solar 431 663), non exploité |
| 51 | Parkings APER | connecte | **partiel** | ingéré (901), non exploité |
| 2 | Cadastre Etalab | connecte | connecte + note **DOUBLON de #1** | même donnée, canal bulk |
| 65 | RGE ALTI 5 m | connecte | connecte + note **DOUBLON de #6** | même référentiel |
| 67 | GPU assainissement (typeinf 19) | connecte | connecte + note **DOUBLON de #63** | même couche |
| 68 | Office de l'eau | note corrigée | — | usage RÉEL en seed versionné (nuance M66-B), pas un faux positif |

**Après (mesuré, Playwright)** : bandeau **« 42 SOURCES BRANCHÉES »** (45 lignes servies, 3 badges
doublon) · VÉRIFIÉES AUTO 9 → **8** · MILLÉSIME NON TRACÉ 27 → **14** (les compteurs ne portent plus
que sur les lignes servies). Catalogue : 45 connecte + 7 a_faire + 6 partiel + 2 manuel + 2 hub = 62.

---

## BLOC B — Le scoring ne lit plus de signaux morts

### B1 — DPE retiré du scoring
- **Retrait** : `DpePassoireLayer` (étage 2, flag INFO ×0) supprimée — cascade_rules.yaml,
  scoring_matrice.yaml (a_layers), registre, sets fiche `_A_LAYERS`/`_ONGLET`, contexte `passoire()`.
  Garde de câblage M-B verte (YAML ↔ registry cohérents des deux côtés).
- **Golden** : baseline AVANT retrait = 85/118 PASS + 33 FAIL **préexistants** (dérive antérieure à
  M71 : le golden gelé le 07/08 attend `score_v2 <absent>` sur 33 déclassées que la fiche sert
  désormais — à régénérer lors d'une prochaine bascule, hors périmètre M71). APRÈS retrait :
  **diff strictement vide champ à champ** (0 ligne). Le golden ne bouge pas → pas de STOP.
- **Les 2 lignes hors département** (code_insee 34172, 59350) : supprimées (journalisées). Cause
  mesurée = **trou du filtre inverse** : logements réunionnais authentiques (CP brut 97490/97434)
  dont le géocodage BAN ADEME est métropolitain menteur — `parse_record` stockait le
  `code_insee_ban` faux. Corrigé : identité BAN **purgée** quand elle contredit le CP brut
  (code_insee/code_postal/id_ban/x/y/score) ; le CP brut (diagnostiqueur) fait foi.
- **« Ré-ingérer les 913 » : sans objet, mesuré.** L'amont « 913 DPE 974 » est contaminé à 98 %
  (constat M-V du 09/08, documenté en tête de `ingestion/dpe.py` et revérifié live : filtre CP brut
  974xx → **17**). Ré-ingestion complète : **17 DPE, tous 974, 15 rattachés parcelle, 898
  métropolitains écartés, 0 code_insee menteur**. La source DPE est donc désormais **complète vs
  son amont réel** (17/17) — l'amont lui-même reste dérisoire (DPE réglementaire neuf en DROM).
- **INFO FICHE** : bloc `dpe_connu` (« DPE connu : G, 2023 », tiroir Propriétaire, mention « sans
  effet sur le classement ») — servi seulement si un DPE est rattaché, rien sinon.
- Résiduel signalé (non retiré — hors périmètre B1) : `score_v.py` famille E lit encore
  `dpe_records` F/G rattachées (**2 lignes** servies) et `surface_d.py` garde l'événement
  `dpe_passoire` (0 ligne). Quasi morts, mais le Score V n'est plus affiché (ALGO-1) — à trancher
  avec B2 si souhaité.

### B2 — pv_candidat : STOP D'ARBITRAGE (mesures livrées, Vic tranche)
**Constat** : 23 529 détections PV / **19 990 parcelles**, TOUTES `validation NULL` ; le scoring
exige `ok/probable` → feature **false partout** (morte) ; `parcel_equipements.pv_detecte` = 0.
Aucun juge n'a jamais tourné sur PV (`juge_vlm`/`juge_flair`/`valide_profil` = 0 partout ;
piscines : 815 ok / 804 faux positifs + quarantaine 472 + précision 90,7 % validée Vic).

- **(a) Passe de validation** : le processus piscines existe et se réapplique (juges VLM/FLAIR sur
  vignettes + session de validation humaine sur échantillon ~300 pour mesurer la précision).
  Coût : 23 529 vignettes à juger (run batch de plusieurs heures + coût API des juges VLM +
  une session Vic) ; aucune infra nouvelle.
- **(b) Alignement critère piscine** (non-infirmé = pris) : ressuscite immédiatement —
  **19 990 parcelles** passent true (4,6 % du parc). Profil : surface p10/50/90 = 4,6/9,1/29,9 m²,
  confiance 0,30–0,88 (méd 0,58), 100 % sur bâti. Tiers servis des parcelles concernées :
  17 527 écartée, 1 401 bâti saturé, **717 a_creuser, 164 réserve, 13 chaudes**. Impact scoring :
  feature D bool au coefficient épinglé de l'artefact (pas de re-fit) — effet au prochain build ;
  taux de faux positifs = celui des candidats bruts (inconnu tant que (a) n'a pas tourné).
- Interdit respecté : la feature n'est PAS laissée morte en silence — **exemption DATÉE**
  `NON_CONSTANCE_EXEMPTIONS['pv_candidat']` (B3), retirée dès l'arbitrage.

### B3 — Test de non-constance (règle des trois fois)
`check_non_constance(df)` sur la **matrice de features au BUILD** (p_v2/pipeline, après `derive`) :
une feature active constante sur tout le parc → `SignalConstantError` **bloquante** qui NOMME le
mort ; exemptions datées obligatoires (jamais un silence), renvoyées au rapport de run
(`signaux_constants_exemptes`). 6 tests unitaires (`tests/test_non_constance.py`) verrouillent la
logique (constante, 100 % NaN, exemption journalisée, retired ignorée, exemption motivée).

---

## BLOC C — Saint-Philippe : l'aveuglement se dit

Périmètre mesuré exact du « sans zone » : **4 153 Saint-Philippe (97417 — 0 couche PLU au GPU,
commune RNU) + 91 Saint-Leu (97413, résiduelles) + 0 ailleurs**.
- **Fiche** : champ Zone = **« Non publié au GPU »** (plus jamais « — » muet) ; contexte du tiroir
  Urbanisme aligné (« zone non publiée au GPU ») ; bandeau RNU (`f.rnu`, mention actée) inchangé
  et affiché — vérifié Playwright sur 97417000BC1159.
- **Scoring** : `zonage_plu_gpu` sans AUCUNE intersection → **UNKNOWN « non évaluable »** (impacte
  la complétude comme ABF), plus un PASS silencieux « Hors zonage PLU connu ». Un trou de donnée
  n'est pas un verdict. Effet au prochain build (runs servis immuables) ; le run servi actuel ne
  classe d'ailleurs AUCUNE de ces parcelles non-constructibles (mesuré : écartée/a_creuser/bâti).
- **Toast RNU M55-A** vérifié cohérent : « Saint-Philippe : commune au RNU — pas de zonage PLU. »

---

## BLOC D — BODACC : le sondage est prouvé

- **Table `bodacc_sondages`** (siren PK, sonde_le, resultat, n_procedures), remplie par
  `ingest_bodacc` à chaque appel — un « rien » daté vaut mieux qu'un silence ; helper
  `sirens_jamais_sondes()`.
- **Backfill exécuté** (`labuse ingest-bodacc`) : couverture finale **12 605 / 12 605** =
  **9 733 SIREN sondés** (dont **177 avec procédure** — le compteur de flux du run disait 193,
  le journal fait foi ; 9 556 « rien » datés ; 678 annonces upsert, dernière du 06/08/2026)
  **+ 2 872 identifiants MAJIC `U########`** (PM sans SIREN — structurellement non sondables)
  journalisés `non_sondable`. 9 733 + 2 872 = 12 605, zéro silence.
- **Déploiement (Train 8)** : le cron J+1 existant (`labuse ingest-bodacc` →
  `fraicheur.ingest_bodacc_quotidien`) entretient désormais le journal par construction (même
  voie d'ingestion). ⚠ Piège : `python -m labuse.cli` n'expose que les commandes définies AVANT
  la ligne 1736 (`app()` mi-fichier) — utiliser l'entry-point **`labuse`**.

---

## BLOC E — Trous diffus terrain et végétation

Diagnostic mesuré AVANT action :
- **Terrain (8 211 manquantes)** : 0 invalide, 84 % < 25 m² (slivers < 1 pixel du raster 5 m,
  aire médiane 10,3 m²), 100 % couvertes par `rgealti_pente_5m`.
- **Végétation (5 556 manquantes)** : aire médiane 6 634 m², **100 % HORS de toute tuile
  `ortho_tiles`** (IRC/MNH jamais acquis sur ces zones — la relance sans étendre le tuilage ne
  produirait rien, et l'extension = acquisition lourde, hors périmètre).

Actions (script versionné `scripts/m71_e_trous_terrain_vegetation.sql`) :
- **Terrain : 8 211/8 211 RÉCUPÉRÉES** (zonal `ST_Clip` + repli `ST_Value` au point-sur-surface
  pour les slivers) → `parcel_terrain` = **431 663 (100 %), 0 neutralisée**.
- **Végétation : 5 556 NEUTRALISÉES documentées** (colonne `motif_absence`, valeurs NULL →
  contribution nulle inchangée, l'absence est désormais DITE) → table = 431 663 lignes.
  Résiduel par commune : Saint-Benoît 660 · **Sainte-Rose 597 (9,5 % — à surveiller)** ·
  Saint-Paul 588 · Les Avirons 429 · Sainte-Marie 318 · Saint-Denis 304 · le reste < 300.
  Levée future : étendre le tuilage puis `labuse vegetation-irc` + `labuse vegetation`
  (`finalize()` upsert par idu → les motifs seront écrasés par de vraies valeurs).

---

## BLOC F — Le chiffre vitrine : STOP D'ARBITRAGE

Recomptage APRÈS blocs A–E (mesuré en base et à l'écran) :
- **Bandeau Sources (servi)** : **42** = connecte (45) − doublons (3). Plus aucun squelette dedans :
  ZNIEFF/EDF/ODRE sont a_faire, les hubs sortis, PVGIS/Parkings partiel, et DPE — resté connecte —
  est désormais **complet vs son amont réel** (17/17) et hors scoring.
- **Accueil** (`/accueil/chiffres`, compteur dynamique `status='connecte'` inchangé — interdit F
  respecté) : affiche mécaniquement **45** depuis les requalifications (52 avant M71).

**Vic décide de ce que la vitrine affiche** :
1. **42** — aligné sur le bandeau Sources : connecte hors doublons (il suffit d'exclure les
   3 lignes DOUBLON du compteur accueil, même règle que le bandeau) ;
2. **45** — statu quo : toutes les connecte, doublons inclus.
Aucun changement fait à l'accueil — j'attends l'arbitrage.

---

## Garde-fous (état final de la branche)

| Garde | Résultat |
|-------|----------|
| tsc --noEmit | **0 erreur** |
| vitest | **37/37** (5 fichiers) |
| npm run build | **vert** (880 ms) |
| pytest complet | **1 465 passed** ; 7 échecs PRÉEXISTANTS identiques sur main (test_deps_declared, test_faisabilite AU*st, test_front_reliquats, test_residuel ×4) + test_pdf_premium (ImportError RUN, préexistant, fichiers intacts depuis main) ; le SEUL échec induit (test_source_test_sans_connecteur, épinglait une source manuel) est corrigé dans ce commit |
| golden 118 | **diff baseline↔final = 0 ligne** (85/118 PASS ; 33 FAIL préexistants = golden gelé 07/08 vs fiche servant score_v2 aux déclassées — à régénérer à la prochaine bascule) |
| console navigateur | **0 erreur** (fiche 97417 + page Sources) |
| bandeau Sources | **42 mesuré** (45 lignes, 3 doublons badgés) |
| fiche Saint-Philippe | « Non publié au GPU » + bandeau RNU affichés |
| exports PDF | 97417 → **200**, 97415 → **200** |
| garde câblage M-B | verte (boot + tests) |

## Pièges notés
- `python -m labuse.cli` : commandes après la ligne 1736 invisibles (`app()` mi-fichier) → `labuse`.
- CP brut ADEME parfois ENTIER (97490) → cast str obligatoire avant `adresses.code_postal`.
- `parcel_p_score_v2.parcelle_id` est l'IDU (varchar), pas l'id parcelle.
- Le rate-limit 60/min (défi) fait échouer `qa/golden_check.py` en local → lancer l'API avec
  `LABUSE_RATE_LIMIT_RPM` élevé pour les passes QA.

**STOP — arbitrages attendus : B2 (pv_candidat : (a) validation vs (b) alignement piscine) et
F (vitrine : 42 vs 45). NE PAS MERGER.**

---

# ADDENDUM — Arbitrages Vic (13/08)

## F — TRANCHÉ : vitrine = 42 partout
`/accueil/chiffres` compte désormais `connecte` **hors doublons** (même règle que le bandeau
Sources), dynamique, aucun chiffre en dur. Vérifié live : accueil **42** = bandeau **42**.

## B2 — TRANCHÉ : option (a), session de jugement. CHIFFRAGE (session NON lancée)

**Rappel de la règle déjà actée dans le code** : `ortho_equipements.materialiser_pv()` ne
matérialise QUE si `precision_validee('pv') ≥ 75 %` (config `precision_min_pv`), puis prend
`validation='ok' OU (non-examinée ET confiance ≥ seuil)` — exactement « non-infirmé = pris »
après session, auto-appliqué. Il n'y a RIEN à coder pour l'après-session.

### Combien de vignettes : **300**
- Population : 23 529 candidats PV / 19 990 parcelles / 52 strates commune×confiance
  (terciles) / **3 202 tuiles**.
- Un tirage stratifié de 300 (simulé, seed fixe) touche **269 tuiles distinctes**.
- Précision statistique à n=300 : IC95 ±4,9 pts si la précision observée est ~75 % (le seuil),
  ±3,4 pts si ~90 %. (L'historique du code disait 150 — IC ±6,9 pts : trop lâche autour du
  seuil de décision 75 % ; 300 est le bon chiffre, conforme à ton arbitrage et au précédent
  piscines : 300 sanctuarisés.)
- Mode de tirage : l'outil tire ALÉATOIREMENT côté serveur dans la file non validée (uniforme
  = mesure de précision non biaisée). Le tirage STRATIFIÉ exigerait un petit profil config sur
  la branche spin-off — disponible si tu le veux, pas nécessaire pour la mesure.

### Outillage : l'outil n'est PLUS sur main
`/ortho/validation` est parti au spin-off « Vues » (M12 Lot C-bis) — il vit sur
`origin/spinoff/vues-solaire` (endpoints suivante / vignette.jpg / valider + page HTML,
**`?type=pv` déjà supporté**, quota CÔTÉ SERVEUR paramétrable `?quota=300`, arrêt auto).
Plan d'exécution sans merge ni code : **worktree éphémère sur la branche spin-off**, `labuse
api` (port 8003), MÊME base PostgreSQL — l'outil lit/écrit `ortho_detections.validation`.

### Préparation (moi, avant ta session) : ~30-45 min
1. Re-télécharger les tuiles RVB des vignettes : le cache est purgé (20 tuiles / 23 Mo
   restantes ; l'endpoint vignette renvoie 410 si tuile absente). Volume : ~269-300 tuiles ×
   1,2 Mo ≈ **320-360 Mo** WMS Géoplateforme (le motif de re-téléchargement ciblé existe déjà,
   cf. vegetation.preparer_validation — je le réutilise pour type='pv').
2. Monter le worktree spin-off + API 8003 + fumée sur 3 vignettes.

### Ta session : **~20-30 min, en une seule fois : OUI**
- Jugement binaire (panneau PV réel / faux positif), 300 vignettes à 3-5 s pièce.
  Précédent mesuré : ta session initiale piscines = **966 verdicts en une séance**.
- Quota serveur à 300 → l'outil s'arrête seul, stats live pendant la session.

### Après ta session (automatique + un build)
- `materialiser_pv()` applique la règle 75 % (matérialise ou refuse, avec le chiffre).
- Si matérialisé : je retire l'exemption `NON_CONSTANCE_EXEMPTIONS['pv_candidat']` (la garde
  B3 re-surveille), et la feature revit au prochain build P.
- Si < 75 % : plan B documenté au rapport juges piscines — probe DINOv2 + tes 300 labels =
  étage 1 PV local (~20 min de calcul), même recette que les piscines (90,7 %).

**En attente de ton GO pour lancer la préparation (rien n'est lancé).**
