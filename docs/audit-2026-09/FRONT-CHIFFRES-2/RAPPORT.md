# FRONT-CHIFFRES-2 — les 420 occurrences, jusqu'à la dernière

**Branche** `fix/front-chiffres-2` (depuis `origin/main` `3a0f9b5a`, = main APRÈS merge de COHERENCE-FIX-1 + FRONT-CHIFFRES-1) · worktree `~/Desktop/labuse-frontchiffres` · 8615/5815 · **plusieurs sessions**.

**Règle d'or.** Après ce mandat, le front **ne décide plus aucun chiffre, seuil, plafond,
conversion ni libellé dérivé d'un nombre** : il rend ce que le back sert, sous un id du registre,
avec un format de `lib/format.ts`. Les valeurs affichées ne changent pas — sauf quand l'ancienne
était fausse (listé dans `CHANGEMENTS.csv`).

**Base.** `docs/audit-2026-09/FRONT-CHIFFRES-1/INVENTAIRE.csv` : 966 occurrences. On ne touche
NI les 525 `legitime`, NI les 21 `supprimer` (déjà traités en FC-1). Restent **420 actionnables**
= 213 `remonter_back` + 207 `declarer_registre`.

---

## Instruments en place (hérités de COHERENCE-FIX-1, vérifiés au démarrage)
- **Banc** : `labuse coherence` (= `python -m scripts.coherence.banc --echantillon`), DSN via
  `LABUSE_COHERENCE_DSN`/`LABUSE_DATABASE_URL`, API via `LABUSE_COHERENCE_API`. Écrit `ECARTS.csv`,
  journalise `coherence_runs`.
- **Verrou V6b** : `tests/verrous/test_v6b_coherence.py` (le banc en test).
- **Vocabulaire d'absence** (lot D) : `src/labuse/registre/absences.py` — CINQ formes
  (non_disponible / aucun / hors_perimetre / sans_objet / non_calculable). Toute phrase d'absence
  déclarée doit matcher une forme, sinon V6 échoue. Rendu compact = « — » (format.ts).
- **Verrou front** : `tests/test_front_chiffres_orphelins.py` (FC-1, réconcilié au merge).

**Baseline (Étape 0)** : servers 8615/5815 up ; `test_v6b_coherence` + `test_front_chiffres_orphelins`
**verts (4/4)** ; banc `--echantillon` rejoué → **3161 comparaisons · 188 écarts (166 INCOHERENT /
22 TOLERABLE)** (= l'état laissé par COHERENCE-FIX-1, 0 FAUX-CLIENT). C'est le point de départ ;
chaque famille doit garder ce nombre ≤ 188 (0 écart nouveau).

---

## Plan — 159 familles (`FAMILLES.csv`), ordre = gravité

| priorité | type | familles | lignes | traitement |
|---|---|---|---|---|
| P1 | **seuil / plafond** | F01–F32 (32) | ~75 | remonter le seuil au moteur qui porte la notion, servi sous un id ; le composant lit |
| P2 | **calcul** | F33–F68 (36) | ~130 | le calcul passe au back sous un id ; conversions d'unité comprises |
| P3 | **texte chiffré / defaut** | F69–F113 (45) | ~95 | nombre en dur dans la prose → interpolé depuis l'id servi ; `?? 0` → vocabulaire d'absence |
| P4 | **format** | F114–F159 (46) | ~120 | `toLocaleString`/`toFixed` bruts → formateur partagé + `chiffreId` (déclaration) |

`INVENTAIRE.csv` (ce dossier) = l'inventaire FC-1 **rejoué** avec deux colonnes ajoutées :
`famille` et `etat` (a_faire · remonté · déclaré · fusionné · arrêté_pour_décision).

### Le patron d'une famille (un commit)
1. **Remonter** (`remonter_back`) : la règle/seuil/calcul va dans le moteur back qui porte déjà la
   notion (jamais un moteur parallèle), servi sous un id du registre ; le composant lit l'id.
2. **Déclarer** (`declarer_registre`) : l'id existe côté back → déclaré au registre (fiche V5d,
   commune V5e, outils V5f) avec lecteur front, tolérance, phrase d'absence ; `sync` base faite ici.
3. **Tolérance** dans `NOTIONS.csv` (dérivée par unité) ; banc `--echantillon` rejoué : la notion
   apparaît, 0 écart nouveau.
4. **Même valeur partout** : `grep` avant/après — tout lecteur (autre composant, PDF, Copilote) lit l'id.
5. **Capture** avant/après (sauf déclaration pure sans effet visible).
6. `tsc` 0, `vitest` vert, V6 vert, tests back de la famille verts.

### Garde-fous
- Toute valeur affichée modifiée → `CHANGEMENTS.csv` (id · ancienne · nouvelle · pourquoi l'ancienne
  était fausse). Non listé = régression.
- Aucun seuil inventé : un seuil remonté garde sa valeur, sauf s'il contredit un seuil déjà servi
  (le back gagne, noté dans `CHANGEMENTS.csv`).
- Aucun run île / bascule. Une famille exigeant un recalcul de table est isolée en fin de mandat et
  **arrêtée pour décision de Vic** (`etat=arrêté_pour_décision`).
- Un id = une notion ; deux lignes qui décrivent la même chose → un seul id (`etat=fusionné`).

---

## Journal des sessions

### Session 1 (Étape 0 + planification)
- Worktree recréé sur `fix/front-chiffres-2` depuis `origin/main` `3a0f9b5a` (l'ancien worktree
  FC-1 avait été supprimé ; travail FC-1 sauf sur `origin/main`). `.env` + `node_modules` (symlink).
- Baseline verrous verts, banc lancé.
- `FAMILLES.csv` (159) + `INVENTAIRE.csv` rejoué (colonnes famille/etat) produits.

**Familles traitées cette session :**
- **F04 — `FinancierQuestionnaire` bornes du garde « hors marché » (7 lignes, remonté).** Les bornes
  20 000 / 8 000 / 12 000 €/m² étaient CODÉES au front (le garde client reproduisait le moteur). Le
  back les sert désormais (`GET /financier/{idu}/questionnaire` → `hors_marche_bornes`) depuis la
  SOURCE UNIQUE `faisabilite/engine.py` (déjà lue par le garde PDF `financier_bilan._hors_marche` —
  un seul point de vérité, cf. `test_hypotheses_source_unique`). Le composant lit `hors_marche_bornes` ;
  aucune valeur affichée ne change (bornes identiques des deux côtés) → 0 écart banc, 0 capture.
  Garde : `tests/test_front_chiffres2_familles.py::test_f04_...`. tsc 0 · vitest 225 · back+V6 verts.

**Reste : 413 lignes actionnables (voir `INVENTAIRE.csv` colonne `etat`).**

### Session 2 (lot P1 — seuils)
Cadence adoptée (décision Vic) : **une session = un lot d'une même priorité**, un commit par
famille, un seul compte rendu en fin de session. Garde-fous de fin : banc ≤ 188 / 0 FAUX-CLIENT,
V6b + verrou front verts, tsc 0, vitest vert, `CHANGEMENTS.csv` à jour.

**10 familles P1 traitées :**

*Remonters (le seuil passe au back, servi sous une constante, le front lit) :*
- **F14 — badges Radar « Nouveau » / « En vente longue »** (`RadarEcran`). `j<2` / `j>90` étaient
  recalculés au front (fuseau/dates ≠ back → divergence liste vs marché). Back : `SEUIL_NOUVEAU_J=2`
  (à côté de `SEUIL_VENTE_LONGUE_J=90`), `pige/client` sert `nouveau` à plat (base Réunion), le badge
  « en vente longue » lit le `statut` du cycle. **CHANGEMENTS.csv ×2** (décisions désormais canoniques).
- **F25 — bandeau « corpus jeune »** (`RadarMarche`). `corpus_total < 40` → back `SEUIL_CORPUS_JEUNE=40`,
  `/radar/marche` sert le flag `corpus_jeune`. 0 valeur changée.
- **F31 — ligne ZAN** (`blocB`). `(horizon ?? 99) < 5` fabriquait un horizon de 99 ans pour une
  absence → supprimé (absent = ton neutre) ; le palier de couleur `< 5 ans` reste présentation. 0 valeur changée.
- *(F04 déjà fait en session 1.)*

*Reclassements « présentation pure » (couleur/cran d'une valeur servie — aucun chiffre/libellé décidé,
cf. `RECLASSEMENT.md`) :* **F11** (aléa→cran), **F15** (couleur d'écart), **F17** (teinte dépense/budget),
**F22** (couleur de jauge). → `legitime`.

*~~Arrêté~~ → REMONTÉ (décision Vic : servir la DA avec le tier) :* **F13** (pastille Projets) + **F29**
(badge Outils). Le back sert, par palier, le **jeton DA + le ton + le libellé** (`scoring/tiers_client`
`PALIER_DA`, endpoint `GET /vocabulaire/paliers`) ; la pastille et le badge LISENT la même carte, plus
de correspondance palier→couleur en dur. À q_v15 (bandes A/B/C/D) un seul endroit change. F29 sans
changement visible (déjà canonique) ; **F13 corrige une dérive** (CHANGEMENTS.csv) : la pastille
colorait `brulante` en « Priorité » (corail) alors que `PRIORITE_SERVIE=false` le résout en « À suivre »
(ambre). Gardes `test_f13_f29`. → **12 familles P1 traitées cette session.** Checkpoint F13/F29 **re-validé banc = 188** (0 nouveau, 0 FAUX-CLIENT) après le fix `LABUSE_RATE_LIMIT_OFF` (le compteur anti-scraping bloquait le rejeu du banc en DEV — cf. `PRE-DEPLOY-1/NOTES.md`).

### Session 3 (lot P1, suite) — F01a réglementaire + quick-wins + CatNat
- **F01a (remonté, réglementaire)** — verdict de constructibilité NEUVE servi par la cascade
  (`zone_dominante` → `reglement_plu.zone_famille` + `constructible_neuf`), même valeur que le
  Pré-dossier / la garde SDP. **2 CORRECTIONS mesurées** (CHANGEMENTS.csv, pas des déplacements) :
  (a) famille GPU (subtype) prime sur le libellé (token-collision « UD », 1/433) ; (b) `/^(A|N)/`
  flaguait les zones **AU** comme non constructibles (sous-titres SDP + verdict) — corrigé.
- **F21 (remonté)** — drapeau « à cheval » servi par la cascade (`reglement_plu.a_cheval`,
  `SEUIL_A_CHEVAL_PCT`), plus de `part[0] < 0,9` au front.
- **Reclassés présentation** : F07 (SRU statut→couleur/label + couleur d'un signe), F20 (≥2
  millésimes = minimum inhérent d'une frise), F24 (>20000 = plafond de RENDU carte). Cf. RECLASSEMENT.md.
- **Arrêté pour Vic** : F26 (ScoringV2 1/50 = scoring) ; **CatNat** (carte Géorisques brut 17/22 vs
  servi dédoublonné 15/20 — nos lecteurs sont TOUS cohérents à 15/20, le 17/22 réintroduirait les
  doublons GASPAR ; aligner = recalcul de table → `PRE-DEPLOY-1/NOTES.md`).
- **Dev-tooling** : `LABUSE_RATE_LIMIT_OFF` (le banc sans DEV_MODE, cf. PRE-DEPLOY-1).

**État P1 (32) : 7 remonté · 7 reclassé · 1 arrêté · F01 partiel (a fait, b-e restent) · 16 a_faire.**
Guardrails fin de session : tsc 0 · vitest 225 · verrous + gardes FC-2 34 verts · banc `**188 écarts (166 INCOHERENT / 22 TOLERABLE) = baseline, 0 nouveau, 0 FAUX-CLIENT** (F01a aligne la fiche sur la cascade — mêmes notions).`.
**Les 20 P1 ne sont PAS toutes finies** : les 16 restantes (F02 constructibilite, F03 ModulePanel,
F05/F09 admin, F06/F08/F10/F12/F16/F18/F19/F23/F27/F28/F30/F32) sont de vrais *remonters* backend
(serveur qui expose un flag/verdict + front qui lit), ~5 fichiers chacun — à poursuivre en sessions P1.

### Session 4 (lot P1, suite) — F10 + décisions Vic
- **F10 (remonté)** — le seuil de suffisance (n<5 → « — ») des médianes locales par type est appliqué
  au BACK (`mon_secteur.SEUIL_N` ; `medianes_par_type` renvoie None sous le seuil) ; `marche.tsx` lit
  les médianes déjà filtrées, plus de `n >= 5` au front. Terrain nu → **méthode canonique
  `_terrain_section`** (`par_type.terrain_nu`) au lieu de refiltrer `dvf_parcelle.secteur`
  (CHANGEMENTS.csv : correction — inclut « terrain à bâtir », seuil au back).
- **F19 (reclassé présentation)** — `distance_m ≤ 100` ne décide qu'une couleur d'emphase (permis
  proches) ; distance servie & affichée.
- **CatNat — TRANCHÉ (Vic) : garder 15/20** (vrai doublon GASPAR, dédoublonnage COHERENCE-FIX-1
  correct, pas de re-ingestion). Noté dans `PRE-DEPLOY-1/NOTES.md`.
- **F26 (ScoringV2)** — expliqué à Vic (seuil 1/50 = « peu probable », touche l'affichage du
  scoring) ; en attente de sa décision (servir le cutoff ou garder la convention).

**État P1 (32) : 9 remonté · 8 reclassé · 1 arrêté (F26) · F01 partiel · ~13 a_faire.** Guardrails :
tsc 0 · vitest 225 · verrous + gardes 15 · banc `**188 (= baseline, 0 nouveau, 0 FAUX-CLIENT)** — F10 est front-only (lit des valeurs déjà servies).`. **Reste** (P1) : F02, F03, F05,
F06, F08, F09, F12, F16, F18, F23, F27, F28, F30, F32 + F01b–e — vrais remonters backend, à poursuivre.

### Session 5 (lot P1, suite) — F26 (décision Vic)
- **F26 (remonté)** — le seuil « peu probable » de la fraction de probabilité de vente (« sous 1/50 →
  tiret ») était codé en dur dans TROIS textes (ScoringV2, tooltip « i » des résultats, modal
  scoring). Remonté à la source unique `config/scoring_client.yaml` (via `fraction_client.
  seuil_bas_denominateur` + endpoint `/vocabulaire/scoring-fraction`, sert le dénominateur + les
  paliers). Le VERDICT (fraction ou « — ») était DÉJÀ calculé une fois au serveur (`fraction_humaine`)
  → cohérent fiche/filtres/Dossier/Copilote. Le front lit le seuil : `ScoringV2`, `CLIENT.tri.
  lunettes(d)` (ResultsSection), `CLIENT.algo.corps(d, paliers)` (AlgoExplainer). Une bascule de
  bandes met tout à jour, un seul endroit. 0 valeur changée. Garde `test_f26`.

**État P1 (32) : 10 remonté · 8 reclassé · 0 arrêté · F01 partiel · ~13 a_faire.** Guardrails :
tsc 0 · vitest 225 · verrous + gardes 16 · banc `**188 (= baseline, 0 nouveau, 0 FAUX-CLIENT)** — F26 sert un seuil de config (endpoint read-only), aucune notion comparée touchée.`. **Reste** (P1) : F02, F03, F05,
F06, F08, F09, F12, F16, F18, F23, F27, F28, F30, F32 + F01b–e.

### Session 6 (lot P1, suite) — 5 familles
*Remonters :*
- **F01b** — bande de pente (plat/modérée/forte/très forte) servie (`terrain.pente_bande`, fonction
  `_pente_bande`, bornes 5/15/30° en un endroit) ; front §1.2 + §2 ne classe plus.
- **F27** — « dépôt de comptes muet ≥ 3 ans → sommeil » servi à plat (`depot_comptes.muet`, seuil
  `SEUIL_DEPOT_MUET_ANS`) ; Successions ne décide plus.
- **F32** — note d'incohérence dépôt/autorisation permis : `lib/permis.ts` (front dupliqué) SUPPRIMÉ ;
  le back sert `note_incoherence` (source unique `miroir.permis_incoherence_note`) dans /modules/permis
  ET l'historique_site (autour).
- **F18** — échéance de relance CRM (« due aujourd'hui / échue ») servie sur le jour RÉUNION
  (`relance_echeance`, `tz.today_reunion`) au lieu du fuseau du navigateur. CHANGEMENTS.csv (correction TZ).
*Reclassé présentation :* **F30** (`periodAn >= 2016` = disponibilité surcouche cadastre d'époque,
fait historique fixe — plomberie viewer).

**État P1 (32) : 13 remonté · 9 reclassé · 0 arrêté · F01 partiel (a+b) · ~8 a_faire.** Guardrails :
tsc 0 · vitest 225 · verrous + gardes 20 · banc `**188 (= baseline, 0 nouveau, 0 FAUX-CLIENT)** — les notions touchées (pente/sommeil/permis note/relance) ne sont pas comparées par le banc.`. **Reste** (P1) : F02, F03, F05,
F06, F08, F09, F12, F16, F23, F28 + F01c–e.

### Session 7 (lot P1, suite) — 3 familles
*Remonters :*
- **F28** — exonération taxe « locaux agricoles » (zone A) : le prefill taxe sert `zone_famille`
  (`parcel_zone_plu.zone_fam`), le front teste `=== 'A'` au lieu d'une regex `/^A(?!U)/` (même notion
  canonique que la fiche §PLU, F01a). CHANGEMENTS.csv (alignement F01a).
- **F23** — badge de viabilisation : `mot` + `ton` servis (`viabilisation.py BANDE_DA`, source unique),
  la table front `VIAB_MOT` (band→libellé/ton) retirée.
- **F12** — le MOT « sous »/« au-dessus » de l'écart secteur↔commune servi (`ecart_commune.sens`) ;
  seule la couleur reste présentation.

**État P1 (32) : 16 remonté · 9 reclassé · 0 arrêté · F01 partiel (a+b) · ~5 a_faire.** Guardrails :
tsc 0 · vitest 225 · verrous + gardes 23 · banc `**188 (= baseline, 0 nouveau, 0 FAUX-CLIENT)**.`. **Reste** (P1) : F02, F03, F05,
F06, F08, F09, F16 + F01c–e.

### Session 8 (lot P1, suite) — reclassements + F02
- **Reclassements présentation** (cf. RECLASSEMENT.md) : **F06** (glyphes/couleurs de signe « + »/flèche +
  agrégation UI `sdp>0`), **F16** (note descriptive de la règle SQL nu/bâti 5 %), **F08 (part)**
  (`completudeColor` 50 % + `ageSignal` couleur/temps-relatif).
- **Arrêté (scoring)** : **F08** `PRIORITE_SERVIE` (drapeau de politique scoring, miroir testé).
- **F02 (mixte, remonté)** — le verdict « votre charge couvre / est sous le prix du marché » servi
  (`charge_couvre_marche`, `modules.faisabilite_charge`) ; le reste de F02 est présentation/inhérent
  (couleurs ER≥50 %/PEB, `<= 0` inhérents, step de saisie, garde relationnelle coût>sortie).

**État P1 (32) : 17 remonté(+parts) · 12 reclassé · 1 arrêté (PRIORITE_SERVIE) · F01 partiel (a+b) ·
~4 a_faire.** Guardrails : tsc 0 · vitest 225 · verrous + gardes 24 · banc `**188 (= baseline, 0 nouveau, 0 FAUX-CLIENT)**.`.
**Reste** (P1) : **F03** (ModulePanel, fenêtres 24/36 mois + rang), **F05/F09** (admin interne) + **F01c–e**.

### F01 — plan (prochaine session, à reprendre ici)
F01 (`Fiche.tsx`, 15 lignes « seuil ») n'est PAS une notion unique : c'est un **cluster réglementaire**
à SCINDER en sous-familles (1 commit chacune), car chaque notion a son moteur back :
- **F01a — zonage A/N → verdict de constructibilité** (Fiche 624/658/661/855/891/1246/1816 + constructibilite 986).
  Le front décide « zone A/N interdit la construction neuve » par regex `/^(A(?!U)|N)/i` sur `reglement_plu.zones[0].zone`.
  À remonter : servir `zone_famille` (moteur `zone_servie`, notion registre `zone_plu_famille`) + un flag
  `constructible_neuf` ; le front lit. **Même valeur partout** : PDF + Copilote citent le même verdict.
- **F01b — bandes de pente** (Fiche 859/1226, dupliquées). `pente_moy_deg` servi ; le front décide
  `plat/modérée/forte/très forte` (5/15/30°). À remonter : servir `pente_bande` (moteur terrain).
- **F01c — affichage SDP résiduelle** (Fiche 890/1246/1841/1819 : `reglesSdp>0` borne l'affichage) +
  **sdpMin=200** (1826, seuil de densification poussé au filtre). Servir le verdict/seuil (moteur potentiel).
- **F01d — encart « signal »** (Fiche 566 `multBase≥2`, 1045 `multBase≥4`) : seuils décidant un LIBELLÉ.
- **F01e — niveau de risque** (863, regex `/fort|élev/`) + **pctConsommé ≥ 100 ton ambre** (1522, couleur — présentation).
F02 (`constructibilite`) et F03 (`ModulePanel`) suivent le même découpage par notion.

**Garde-fous fin de session :** tsc 0 · vitest 225/225 · V6b + verrou front + gardes FC-2 8/8 ·
194 tests back des modules touchés (7 skips base-data pré-existants) · banc `--echantillon`
→ `**3161 comparaisons · 188 écarts (166 INCOHERENT / 22 TOLERABLE) — inchangé vs baseline, 0 écart nouveau, 0 FAUX-CLIENT** (les familles touchées — badges radar, corpus, ZAN, questionnaire — ne sont pas des notions comparées par le banc ; le garde-fou tient par construction).`.

**Reste P1 : 20 familles** (F13/F29 faits) — les grosses F01 `Fiche` (scinder, cf. plan ci-dessus),
F02 `constructibilite` 9, F03 `ModulePanel` 8 (fenêtres 24/36 mois, sommeil 3 ans) ; + admin F05/F09 ;
+ F06/F07(SRU_META)/F08/F10/F12/F16/F19/F20/F21/F23/F24/F27/F28/F30/F32 ; **F26 ScoringV2 = arrêté
(scoring)**. Prochaine session P1 : reprendre par **F01a** (zonage A/N → verdict constructibilité).

### Session 9 (lot P1, FIN) — F03, F01e remontés ; F01(reste)/F05/F09 reclassés ; arrêtés notés
- **F03 (remonté, 0 valeur affichée changée)** — deux décisions du `ModulePanel` remontées au back :
  (1) la **coupure « récent »** (fenêtre de 24 mois ancrée sur la fin du flux Sitadel) est SERVIE
  (`coupure_recent` = dmax − 24 mois, `modules.permis`) ; le front lisait `minus24m()` (supprimé),
  il lit désormais `coupure_recent` (vérifié live : `2024-07-31` = valeur identique) ; (2) le verdict
  **« société en sommeil »** lit le flag servi `muet` (F27, `SEUIL_DEPOT_MUET_ANS`) au lieu d'un seuil
  codé au front. Les **sélecteurs de fenêtre** (12/24/48/72/240, défauts 24/36) restent des contrôles
  de filtre = présentation.
- **F01e (remonté, 0 valeur affichée changée)** — la **synthèse du niveau de risque** (« rédhibitoire »
  / « fort ») est décidée au back (`_aleas_block` → `synthese`, moteur qui ordonne la sévérité) ; la
  tuile Risques lit `f.aleas?.synthese`. Vérifié sur témoins réels : `97415000BO0436` (rédhibitoire),
  `97415000BP0048` (fort) — 0 divergence vs l'ancienne logique front sur l'échantillon testé.
- **Reclassements (présentation / hors surface client)** — **F01 (reste)** : orientation, réglette,
  passe-plat `au_ouverture.motif`, gating SDP `reglesSdp>0` (inhérent), montage `FaisabiliteTab`, et le
  **push filtre `sdpMin`** (défaut de paramètre de requête, éditable, jamais affiché) ; **F05** & **F09**
  (écrans **admin** : fenêtres invitation/essai, budget IA, backlog Courrier > 5 j, âge sauvegarde > 1 j).
- **Arrêté (scoring, à trancher Vic)** — **F01 (part)** : `signalEcarte` (`mult_base ≥ 2`) et le libellé
  « signal fort » vs « au-dessus de la moyenne » (`mult_base ≥ 4`) sont des seuils sur le **multiplicateur
  de scoring** → décision de scoring (analogue à F26). **PRIORITE_SERVIE** : tranché **hors périmètre
  FC-2** (Vic) — laissé tel quel, à traiter avec la bascule q_v15 (DONNEES-FIX-1 + run 11).

**P1 TERMINÉ.** Bilan P1 (32 familles) : **19 remonté(+parts)** · **~11 reclassé** · **2 arrêté scoring**
(F01 mult_base à trancher, PRIORITE_SERVIE hors périmètre). Aucune valeur affichée modifiée sur toute
la P1 (CHANGEMENTS.csv inchangé — les remonters ne déplacent que la DÉCISION, pas la valeur).

**Garde-fous fin de session :** tsc 0 · vitest 225/225 · V6b + verrou front + gardes FC-2 (19 dans le
fichier familles, 26 avec verrous+rate-limit) · banc `--echantillon` →
`**3161 comparaisons · 188 écarts (166 INCOHERENT / 22 TOLERABLE) — inchangé vs baseline, 0 écart nouveau, 0 FAUX-CLIENT**`.

**Régime P2+ (consigne Vic reçue en fin de P1)** : lots de 15–20 familles/session, **un commit par lot**,
compte rendu unique ; cérémonial complet (commit dédié + garde + CHANGEMENTS) réservé aux familles qui
**changent une valeur affichée**. **Ne pas démarrer P2 sans feu vert de Vic.**

### Session 10 (P2 — lot 1, nouveau régime) — F33–F50 (18 familles `calcul`)
Premier lot au **régime P2** (15–20 familles/session, **un commit par lot**, cérémonial complet réservé
aux familles qui changent une valeur affichée). Classification confiée à 3 forks lecture-seule (héritant
des principes P1), exécution par moi.

- **Un seul remonter — F46** (`fiche/marche.tsx`, **valeur affichée inchangée**) : la « **Valeur au prix
  du secteur** » (`contenance × médiane terrain du secteur`) était un produit calculé au front, alors que
  le back calcule DÉJÀ ce produit (`score_e` « prix probable ») → divergence possible fiche↔Dossier↔Copilote.
  Servi `dvf_parcelle.valeur_terrain_secteur_eur` (même arithmétique exacte : `round(surface) × médiane`),
  le front lit. Vérifié sur témoins (`97402000AB0003` 7 027 416 · `AH0162` 44 304 · `AK1716` 24 786) =
  valeurs identiques. Guard `test_f46_valeur_secteur_servie`.
- **13 familles présentation** (reclassé légitime, 0 changement) — **F33** constructibilite, **F34**
  ContextePanel, **F36** ModulePanel, **F38** ProjetKanban, **F39** Fiche, **F40** SourcesPage, **F41**
  VeillePromoteurs, **F42** ResultsSection, **F43** ComparePanel, **F47** blocB, **F48** RadarEcran, **F49**
  geo.ts, **F50** Gabarit : tout `calcul` n'y re-exprime/agrège/formate que des valeurs **déjà servies**
  (somme, différence, ratio, max/min, complément à 100, conversion d'unité, temps relatif, jauge, couleur).
- **4 familles admin interne** (hors surface client, rendues sous `App.tsx` `view==='admin'`) — **F35**
  Licences, **F37** AdminView, **F44** Courrier, **F45** Produit : monitoring ops, pas des chiffres client.

**Garde-fous fin de session :** tsc 0 · vitest 225/225 · V6b + verrou front + gardes FC-2 (20 dans le
fichier familles, 27 avec verrous+rate-limit) · banc `--echantillon` →
`**3161 comparaisons · 188 écarts (166 INCOHERENT / 22 TOLERABLE) — inchangé vs baseline, 0 nouveau, 0 FAUX-CLIENT**`.

**État P2 (36 familles) : lot 1 = 18 fait** (1 remonté · 13 présentation · 4 admin). **Reste lot 2 =
F51–F68** (18 familles). Détail dans RECLASSEMENT.md § « P2 — lot 1 ». **Préviendra Vic à la fin de P2,
avant P3/P4.**

### Session 11 (P2 — lot 2) — F51–F68 · **P2 TERMINÉ**
Classification par 2 forks lecture-seule avec **test de divergence explicite par ligne** (inputs = champs
servis ? le résultat pourrait-il différer d'un calcul back de la même notion ? tout doute → remonter).

- **2 remonters — F57/F50 et F58** (tous deux **valeur affichée inchangée**, tous deux des formules DUPLIQUÉES) :
  - **F57 + F50** : le « **% à cheval** » (`portion / cadastre × 100`) vivait à DEUX sites front
    (`GabaritLine.tsx` **et** `Gabarit.tsx`) — divergence possible. Remonté `pctPortionZone` (calculé une
    fois dans `api/gabarit.py`), les deux le lisent. Vérifié témoins à cheval (`AB1116` 84 % · `AB1184`
    86 % · `AB0149` 83 %). **Ceci RÉVISE le classement F50 du lot 1** (présentation → remonter).
  - **F58** : la « **part de propriétaires** » (`100 × men_prop / men`) était recalculée au front alors que
    la MÊME formule vit au back (`solaire.py:328`, scoring). Remonté `part_proprietaires_pct` sur le bloc
    filosofi_200m. Vérifié témoin (`97402000AB0004` = 82 %).
- **14 présentation** (F51/F52/F53/F54/F59/F60/F61/F62/F63/F64/F65/F66/F67/F68) + **2 admin interne**
  (F55/F56). Détail ligne par ligne (inputs servis + « pas de divergence ») dans RECLASSEMENT.md § P2 lot 2.

**Garde-fous fin de session :** tsc 0 · vitest 225/225 · V6b + verrou front + gardes FC-2 (22 dans le
fichier familles, 29 avec verrous+rate-limit) · banc `--echantillon` →
`**3161 comparaisons · 188 écarts (166 INCOHERENT / 22 TOLERABLE) — inchangé vs baseline, 0 nouveau, 0 FAUX-CLIENT**`.

---

## RAPPORT DE FIN DE P2

**P2 (36 familles `calcul`, F33–F68) terminé en 2 lots.** Bilan : **4 remontés** (F46, F57, F50, F58 —
tous à **valeur affichée inchangée** ; chacun corrigeait une formule dupliquée front↔back ou front↔front)
· **26 reclassés présentation** · **6 admin interne** (hors surface client). banc **188** tout du long
(baseline, 0 FAUX-CLIENT). Aucun changement de valeur affichée sur toute la P2.

### 3 justifications de reclassement tirées au hasard (demande Vic — vérifier que « re-exprime des valeurs servies » ne masque pas un calcul qui pourrait diverger)
Tirage aléatoire (`random.sample`, 3 sur les 26 présentation) → **F67, F49, F66**.

**① F67 — `header/Header.tsx:557`** (pagination « Voir plus »)
```tsx
{(ev.data?.items?.length ?? 0) >= limite && (
  <ListPaginationFooter shown={ev.data?.items?.length ?? 0}
    total={(ev.data?.items?.length ?? 0) + PAGE_SIZE} … /> )}
```
Inputs = `ev.data.items` (liste **servie** par le back) ; `limite`/`PAGE_SIZE` = état d'UI. `shown` = longueur
de la liste chargée ; `total` = `shown + PAGE_SIZE` n'est **pas** un total revendiqué — c'est un artefact
de pied « il y en a probablement d'autres » (le back ne renvoie pas de total, commentaire à l'appui). **Aucun
nombre client, aucune divergence** : rien ici n'est comparé à un compte back.

**② F49 — `lib/geo.ts`** (géométrie carte côté client)
```ts
export function haversine(a, b) { … 2 * R * Math.asin(Math.sqrt(s)) }        // distance
export function polygonArea(pts) { … return Math.abs(s / 2) }                // aire (shoelace, projection locale)
export const fmtDistance = (m) => m >= 1000 ? `${(m/1000).toFixed(2)} km` : `${Math.round(m)} m`
export const fmtArea = (m2) => m2 >= 10_000 ? `${(m2/10_000).toFixed(2)} ha` : `${…} m²`
```
Inputs = géométrie **servie/dessinée** (coordonnées de la parcelle ou du polygone tracé par l'utilisateur).
Ce sont des mesures d'affichage pour l'outil de dessin de zone (distance/aire d'un tracé), « approximations
planes locales » assumées, **jamais un nombre du registre** — aucune de ces valeurs n'est un chiffre que le
back sert par ailleurs (cohérent avec F19 distance servie / F24 rendu). Pas de divergence possible : il n'y
a pas de « distance officielle » back que ceci contredirait.

**③ F66 — `projets/ProjetsPanel.tsx:51`** (barre de progression d'un projet)
```tsx
const c = p.counts ?? { proposee: 0, retenue: 0, ecartee: 0, a_analyser: 0 }
const decidees = c.retenue + c.ecartee + (c.a_analyser ?? 0)
const vivier   = c.proposee + decidees
// … pct = vivier > 0 ? Math.round((decidees / vivier) * 100) : 0
```
Inputs = `p.counts` (les 4 compteurs de pipeline **servis** par le back). `decidees`/`vivier` = **sommes
de ces compteurs servis**, `pct` = leur ratio, pour une barre de progression. **Ne peut pas diverger** :
sommer/diviser exactement les compteurs servis donne, par construction, la même chose que le back — il n'y
a pas de « % de progression » back concurrent (contrairement à F58, où une 2ᵉ formule existait au back → là
j'ai remonté, pas reclassé). C'est précisément le test appliqué à chaque ligne.

**État FC-2 : P1 + P2 faits.** Reste **P3 (45 familles) + P4 (46 familles)** = surtout `declarer`/format.
**⚠ Attente du feu vert de Vic avant d'entamer P3/P4.**

<!-- PROGRESSION -->

---

## Sortie visée
- 0 occurrence `remonter_back` / `declarer_registre` restante (toutes `remonté`/`déclaré`/`fusionné`,
  ou `arrêté_pour_décision` avec justification).
- `test_front_chiffres_orphelins.py` étendu : liste blanche = les 525 `legitime` commentés ; toute
  occurrence des motifs du lot A hors liste fait échouer la suite.
</content>

## RÉGIME P2+ (consigne Vic, reçue en fin de P1)
À partir des P2 : lots de **15 à 20 familles/session**, **un commit par lot** (plus par famille), **un seul compte rendu** en fin de session. Cérémonial complet (commit dédié + garde + entrée CHANGEMENTS) réservé aux familles qui **changent une valeur affichée**. Les reclassements/arrêtés se groupent.
