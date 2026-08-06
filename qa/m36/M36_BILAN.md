# M36 — BILAN (étiquettes de source, chiffres servis, RR par commune)

**Branche `m36-etiquettes-chiffres`** · base `main` 00f53763 · commits atomiques `[M36-LotA…E]`.
**Aucune écriture sur le run servi, les tiers, le cache scoring.** Golden **117/117** après
chaque lot (dernier passage : API bootée sur le code final).

## LOT A — Étiquettes de source fausses (corrigées) + inventaire complet

**Corrigées** (le chiffre était bon, la provenance affichée était fausse) :

| Surface | Avant (faux) | Après (vrai) |
|---|---|---|
| Infobulle marqueurs communes (carte) | « N en priorité dossier **(matrice Q×A)** » | « N parcelles brûlantes ou chaudes **au classement servi** » |
| Badge légende carte | « Verdict · **Matrice Q×A** » | « Verdict · **Classement servi** » (nominal) / « Verdict · Classement historique » (repli honnête) |
| API partenaire `/api/v1/parcels` (surface EXTERNE) | « Données indicatives LABUSE **(scoring q_v2)** » — run MORT | « (classement interne **historique** — pas le classement servi) » — dit ce qu'elle sert |
| Chips communes création de projet (`projets.py`) | note « run premium **q_v2** » + compteur MATRICE | compteur = **tiers servis** + note vraie (compteur produit échappé à l'inventaire M35) |

**Cause racine du badge vu en revue — DOUBLE** :
1. `/v2` MANQUAIT au proxy vite → `useV2Actif()` (fetch `/v2/modele`) échouait en dev →
   repli matrice affiché alors que le run servi existe. `/v2` ajouté ('/mutation' retiré).
2. Découvert à la vérification : un **`vite.config.js` COMPILÉ (artefact tsc du 5 août)**
   traînait à côté du `.ts` — Vite charge le `.js` EN PRIORITÉ → le dev tournait sur une
   config FIGÉE (toute évolution du .ts ignorée). Artefact supprimé + `vite.config.d.ts`
   (tracké par erreur) retiré du dépôt. Vérifié après nettoyage : `/v2` proxifié (200),
   badge « Verdict · Classement servi » à l'écran (capture 1).

**Inventaire — étiquettes VRAIES conservées** (rien à corriger) :
- BD TOPO « éd. 2026-06-15 » + CoSIA « PVA juil.-août 2025 » (badges M28, filtre bâti,
  bâti révélé) : millésimes réels des caches servis ;
- « Statut matrice (historique) » (fiche web, PDF premium) + TierBadge « (matrice : X) » :
  ils affichent DES VALEURS matrice, étiquetées historiques — vrai ;
- fraîcheur PLU GPU-vs-mairie (M32), DVF « ventes jusqu'à… », Sourcé/Estimé : vrais.

**Inventaire — vrais problèmes NON corrigés ici (consignés)** :
- `score_e` (chip « Marge estimée · Estimé ») : les VALEURS servies ont été construites sur
  `q_v7_defisc` (défaut en dur, relevé train 3) — pas d'étiquette de run affichée. Correction
  = rebuild sur le run servi (backlog train 3), pas un relabel ;
- payload partenaire = matrice historique (la mention le dit désormais) — migration tiers
  avec l'extinction (c) ;
- badge Header « DÉMO (run q_v2_demo) » : outil de démo, étiquette vraie ;
- docstrings/commentaires internes citant q_v2/q_v7 (scoreur.py:8, modules.py:1…) : non
  affichés, à toiletter avec (c).

## LOT B — Les deux chiffres non informatifs retirés du client

Retirés des surfaces RENDUES (calcul + payloads API conservés en interne) :
exports md/html/one-pager (ligne « Opportunité N/100 · Complétude N/100 ») · PDF premium
(jauge COMPLÉTUDE ; Q/A conservées = matrice, famille (c)) · fiche web (couronne
« Complétude · N % » ; tiroir Confiance = ICD ou « — ») · cartes Kanban (point + %) ·
Tinder projets (puce) · assistant IA (retirés des FAITS — l'IA ne peut plus les citer ;
ligne Fiabilité = sources muettes comptées + listées).
Vérif réintroduction : `/shortlist` sans consommateur front (payload seul) ; export CSV sans
colonne score legacy ; le tri interne shortlist les utilise (calcul, autorisé).

## LOT C — Libellés (arbitrages Q1–Q3)

- **Q1** : > 100 % non plafonné, libellé FACTUEL « bâti existant supérieur à l'emprise
  constructible actuelle (~N % — à vérifier) » — `residuel.py::_libelle` (point unique) +
  one-pager. Zéro inférence (« antériorité probable » écartée).
- **Q2** : bornes identiques à l'affichage → valeur unique « ~X » (one-pager CA
  `_eur_fourchette`, calculette fiche web, « 2 logements » au lieu de « 2–2 »). Vérifié
  bout-en-bout : AL1154 affiche désormais « CA ~3.4 M€ ».
- **Q3** : rang sur brûlante/chaude UNIQUEMENT (exports verdict + tableaux voisines → « — »,
  faits assistant conditionnels ; fiche web + resume déjà conformes M5/M34).

## LOT D — Fiche commune : le compteur en dur

- **Un point de calcul unique** : `/communes` extrait en `_communes_data` (mémoïsé 5 min),
  consommé par le sélecteur, les marqueurs ET la fiche commune — le même chiffre partout.
- `/communes/{commune}/contexte` sert `classement` : tiers hauts + dossiers PM + libellé +
  étiquette vraie. Vérifié : Saint-Denis → « **103 parcelles brûlantes ou chaudes au
  classement servi** » · source « Classement servi LABUSE (tiers brûlante + chaude) —
  recalculé à chaque bascule, jamais figé ».
- Front : section « CLASSEMENT LABUSE » en tête du volet contexte — visible sans survol.
- Sélecteur inchangé (décision P8/A2 maintenue).

## LOT E — RR par commune (mesure seule, rien servi)

**Méthodologie** (harnais réutilisé, rien recodé) : scores OUT-OF-SAMPLE du walk-forward
fold 2025 (`reports/m36-foncier/scores-2025-fold-final.csv`, artefact figé) · labels L2-F
2025 (`p_model_dataset`) · hors copro (n = 428 239) · RR@k via `p_model.evaluate.rr_at_k`
(ties seedés 974) · k_c ∝ 1158 · **médiane sur 20 tirages d'ex æquo + bornes** · IC95
bootstrap (500) · ⚠ « aucune conclusion » si < 5 positifs dans le top-k_c.

**Deux découvertes de méthode (à connaître avant tout usage commercial du 6,73)** :
1. **Le RR île n'est défini qu'à l'ordre des ex æquo près** : la coupure top-1158 tombe dans
   un PALIER de scores identiques (AUDIT1 train 5) → RR île = **6,66 médian [6,09–7,00]**
   sur 20 tirages. Le « 6,73 » gelé est UNE réalisation de ce tirage, pas une constante.
   (Renvoie au départage explicite des ex æquo — train 5 N°2, déjà au backlog.)
2. **Le label 2025 a bougé depuis le gel ALGO-1** (fenêtre DVF vivante, rebuild dataset) :
   6 466 → 6 495 positifs hors copro, flips dans les deux sens.

**Tableau (labels du 06/08, médiane [min–max tirages], IC95)** — `qa/m36/rr_commune.csv` :

| Commune | n | k_c | RR intra | [tirages] | IC95 | ⚠ |
|---|---:|---:|---:|---|---|---|
| Sainte-Suzanne | 12 490 | 34 | **19,5** | [19,5–22,8] | [6,1 ; 35,7] | |
| Le Port | 10 114 | 27 | **18,1** | [14,1–22,2] | [7,0 ; 27,8] | |
| L'Étang-Salé | 9 011 | 24 | **17,9** | [17,9–20,4] | [6,7 ; 29,3] | |
| Sainte-Rose | 6 284 | 17 | 14,5 | [14,5–14,5] | [0 ; 40,2] | ⚠ |
| Saint-Benoît | 21 622 | 58 | **14,0** | [12,9–15,2] | [7,4 ; 22,0] | |
| Saint-Philippe | 4 155 | 11 | 12,0 | [12,0–12,0] | [0 ; 29,9] | ⚠ |
| Saint-Pierre | 42 045 | 114 | **9,9** | [8,7–10,4] | [5,7 ; 14,3] | |
| Petite-Île | 13 122 | 35 | 8,8 | [5,9–9,8] | [1,9 ; 15,5] | |
| Les Avirons | 8 560 | 23 | 8,6 | [5,7–8,6] | [0 ; 16,3] | ⚠ |
| Saint-André | 22 513 | 61 | **8,5** | [8,5–8,5] | [2,6 ; 14,1] | |
| La Plaine-des-Palmistes | 6 446 | 17 | 7,4 | [3,7–11,0] | [0 ; 17,0] | ⚠ |
| Sainte-Marie | 16 646 | 45 | 6,7 | [6,7–6,7] | [1,5 ; 13,4] | ⚠ |
| Salazie | 7 034 | 19 | 6,1 | [6,1–6,1] | [0 ; 20,0] | ⚠ |
| Saint-Leu | 22 763 | 62 | 4,9 | [2,4–7,3] | [0 ; 9,7] | ⚠ |
| Entre-Deux | 6 301 | 17 | 4,6 | [0–4,6] | [0 ; 12,9] | ⚠ |
| Saint-Paul | 50 593 | 137 | **4,4** | [2,9–6,7] | [2,1 ; 6,8] | |
| Saint-Louis | 29 141 | 79 | 4,1 | [2,7–5,5] | [0,9 ; 8,3] | ⚠ |
| La Possession | 13 148 | 36 | 3,8 | [2,5–3,8] | [0 ; 7,7] | ⚠ |
| Saint-Denis | 36 981 | 100 | **3,7** | [3,1–5,0] | [1,3 ; 7,1] | |
| Le Tampon | 42 523 | 115 | **3,1** | [3,1–3,6] | [1,0 ; 5,7] | |
| Saint-Joseph | 28 875 | 78 | 2,5 | [2,5–2,5] | [0 ; 5,5] | ⚠ |
| Bras-Panon | 6 016 | 16 | **0,0** | [0–0] | [0 ; 7,2] | ⚠ |
| Cilaos | 6 555 | 18 | **0,0** | [0–0] | [0 ; 0] | ⚠ |
| Les Trois-Bassins | 5 301 | 14 | **0,0** | [0–0] | [0 ; 4,9] | ⚠ |

**Lecture honnête pour le discours client** : le classement discrimine TRÈS fort sur les
marchés secondaires actifs (Sainte-Suzanne, Le Port, L'Étang-Salé, Saint-Benoît : RR 14-20,
IC95 excluant 1) ; il reste NETTEMENT au-dessus du hasard sur les 4 gros parcs
(Saint-Pierre 9,9 · Saint-Paul 4,4 · Saint-Denis 3,7 · Le Tampon 3,1 — IC95 excluant 1
partout) mais SOUS la moyenne île — un promoteur de Saint-Denis doit entendre « ×3,7 », pas
« ×6,7 ». 14 communes sur 24 sont NON CONCLUANTES (< 5 positifs top-k) et 3 ont un RR nul
(Bras-Panon, Cilaos, Trois-Bassins — IC95 compatibles avec un vrai zéro local : ne pas
promettre le classement intra-commune là-bas). Cohérent ALGO-1 (comportement attendu d'un
rang absolu île) — pas un bug, un choix produit à assumer dans le discours.

## VÉRIFICATIONS

1. Golden **117/117** après chaque lot (dernier passage sur le code final, 0 incohérence).
2. Non-régression M34/M35 : re-mesure bout-en-bout (1 071 parcelles) — **0 déclassement
   silencieux, 0 montante, 0 vocabulaire legacy, 0 incohérence — PASS**.
3. Aucun changement de tier, aucune écriture run/cache scoring.
4. Suite pytest : **1 301+ verts** (1 298 avant mise à jour des verrous, 21/21 sur le fichier R3 après) — 3 verrous R3 mis à jour vers la nouvelle vérité
   (absence complétude Kanban, étiquettes légende, wording marqueurs) ; 5 échecs
   PRÉ-EXISTANTS hors périmètre (residuel ×4 + au_ouverture — env test, consignés M34).
5. Captures `qa/m36/screens/` : 1 légende « Classement servi » + marqueurs (app, après
   nettoyage config) + 1b dump verbatim des infobulles (« Saint-Denis — 103 parcelles
   brûlantes ou chaudes au classement servi ») · 2 AT2542 (brûlante, rang visible, sans
   scores) · 3 BW0326 (dépassement d'emprise libellé) · 4 AL1154 (fourchette valeur
   unique « CA ~3.4 M€ » + sans scores) · 5 AI1821 (réserve — rang masqué) · 6 fiche
   commune Saint-Denis (compteur 103 en dur).

## Reliquats consignés
- score_e servi bâti sur q_v7_defisc (backlog train 3 — rebuild, pas relabel).
- Payload partenaire matrice + sélections modules Outils + digest events → extinction (c).
- Départage explicite des ex æquo (train 5 N°2) — la sensibilité du RR le rend d'autant
  plus nécessaire.
- Q/A (matrice) encore affichés (PDF premium, Tinder, fiche) — famille (c), arbitrage à venir.
