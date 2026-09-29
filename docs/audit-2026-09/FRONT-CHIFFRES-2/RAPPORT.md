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

<!-- PROGRESSION -->

---

## Sortie visée
- 0 occurrence `remonter_back` / `declarer_registre` restante (toutes `remonté`/`déclaré`/`fusionné`,
  ou `arrêté_pour_décision` avec justification).
- `test_front_chiffres_orphelins.py` étendu : liste blanche = les 525 `legitime` commentés ; toute
  occurrence des motifs du lot A hors liste fait échouer la suite.
</content>
