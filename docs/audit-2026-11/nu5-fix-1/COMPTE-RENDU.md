# NU5-FIX-1 — correction de NU-5, par cause

**Branche** `fix/nu5-1` · worktree `~/Desktop/labuse-nu5fix` · ports 9790/6990 · Opus 4.8 · base
LOCALE `labuse` (q_v20). **Aucune écriture en prod** (les gestes prod sont *préparés*, appliqués au
déploiement). Stripe mode test. Chaque correction à la source ; chaque trouvaille rejouée (rouge
avant, verte après). Généré le 05/11/2026 (Réunion).

---

## 0. Gestes à appliquer au déploiement (préparés, PAS joués en prod)

**Radar** — `docs/audit-2026-11/nu5-fix-1/gestes-prod/radar.sql` (à jouer APRÈS déploiement du code) :
1. **D-F1** — remettre en `a_reverifier` les **88 biens** retirés à tort le 26/09 (sans preuve
   logée) ; la passe de confirmation les re-vérifie un à un (code livré qui les sert à la passe).
2. **D-F2** — vider `surface_hab` des terrains Leboncoin où elle = `surface_terrain`, puis re-dérouler
   la cohérence → les **~49 terrains** `a_qualifier` repassent sains.
3. **D-F6** — lister les 24 biens `type_bien=NULL` (codes portail inconnus) pour décision.
4. **D-F7** — remettre les **~42 pistes** périmées (`idu` NULL) à `non_rattachee`.

**Saint-Denis / Géorisques (E-2)** — `gestes-prod/saint-denis-georisques.md` :
`labuse ingest-georisques --commune 97411` (re-complète le mouvement de terrain manquant par le WFS
DEAL, commune-scopé/atomique), puis `labuse jobs run fiche-commune-cache`. Le correctif de code
rend le re-fetch **automatique** (le garde ne saute plus une commune sans mouvement de terrain).

**SCOT (E-1)** — `gestes-prod/scot.sql` : corriger le statut/la date des 3 SCOT (Grand Sud passe
« en projet » → **approuvé 18/02/2020**, TCO → 21/12/2016, CINOR → 18/12/2013), puis
`fiche-commune-cache`. *(Appliqué en LOCAL pour la recette ; à rejouer en prod.)*

**Zonage ABC (E-7)** — `UPDATE commune_zonage_abc SET millesime='arrêté du 1er août 2014 consolidé —
reclassement Réunion : arrêté du 02/10/2023'` (ou re-ingestion). *(Appliqué en local.)*

**Brevo / Stripe (C-F1, C-F3, C-F9, C-F10, C-F8)** — `gestes-prod/brevo-stripe.md` (consoles, hors
code) : expéditeur unique `contact@labuse.immo` + SPF/DKIM/DMARC ; lien de désabonnement visible dans
`radar_alerte` ; retrait du template mort `radar_digest` (id 12) ; nom du marchand Stripe « LASTONE »
→ « LABUSE » ; vérifier l'envoi du reçu Stripe.

---

## 1. Lot A — outils (bornes & garde de lecture)

| # | Trouvaille | Correction à la source | Repro |
|---|---|---|---|
| **A-O1/O2** | Gabarit dessinait un volume (Uem « habitat interdit » → 763 m², R+5) / disait « donnée manquante » sur du définitivement inconstructible (N/A/AU fermée/PPR) | `gabarit/builder.appliquer_verdict_constructibilite` (lue via `potentiel_batir`, **même robinet que la fiche**) : verdict **`inconstructible`** + motif, **aucun volume** ; appelé par l'endpoint outil ET le builder PDF ; nouveau statut dans le contrat + front | `test_nu5_fix_1` (3 tests) + live : Uem→inconstructible « Habitat interdit », N→inconstructible, témoin U→ok |
| **A-O3** | Estimer servait €/m² « bâti » (fiab. Moyenne/Élevée) sans dire la non-constructibilité | `estimation_annonce` ajoute `constructibilite` + `avertissement_constructibilite` (via `potentiel_batir`) | `test_ao3_*` + live (parcelle N PPR) |
| **A-O4** | Taxe calcul direct non bornée (surf 1e9 → 66,9 Md€ ; taux −5 → taxe négative) | route `/outils/taxe-amenagement` **bornée** (FastAPI 422) comme la Calculette : surfaces ≥0/plafonnées, taux 0–20 %/0–2,5 % | `test_ao4_taxe_bornee` + live 422/422/422/200 |
| **A-O5** | Comparer abandonnait en silence idu introuvables/en trop/doublons | `/compare` renvoie `ignores` / `tronques` / `doublons` / `limite` | `test_ao5_*` + live |
| **A-O6** | Étude de zone remplaçait un rayon invalide par l'isochrone en silence | refuse (**422 `rayon_invalide`**) un rayon hors {0,5;1;2;5} km | `test_ao6_*` + live |

## 2. Lot B — documents

| # | Correction | Repro |
|---|---|---|
| **B-F1** | **Garde unique « parcelle disparue »** étendue à Apporteur, Étude de zone, Analyser une annonce (document **et** outil) + Financier via `rendre_document`. **Test structurel** qui refuse toute route d'outil/document contournant la garde. | `test_bf1_garde_disparue_sur_toutes_les_routes` + live (6 routes → 422) |
| **B-F2/F4** | Avertissement juridique UNIQUE (`_CLAUSE_JURIDIQUE` : « ni conseil juridique, ni garantie de constructibilité ») au pied de **chaque** document (manquait sur Étude de zone & Comparatif ; formule « garantie de constructibilité » écrite nulle part) | `test_bf2_bf4_*` (clause dans les 8 pieds) |
| **B-F3** | Le Comparatif **annonce** son plafond de 3 parcelles (note imprimée) au lieu d'abandonner en silence | code + relecture |
| **B-F5** | Étude de zone **bornée** : ≤ 8 établissements par catégorie + « + N autres » (fin des 36 pages nominatives) | code |
| **B-F6** | Surface incertaine **qualifiée dans l'en-tête** (badge + « le plan et le cadastre ne concordent pas »), plus seulement enfouie | code |
| **B-F7** | **CreationDate** dans les métadonnées PDF (`dcterms.created/modified`, granularité jour → régénération **reste déterministe**) | `test_annonce_pdf` (déterminisme vert) |
| **B-F8** | *(documenté, non livré)* — le badge « Sources modifiées depuis » compare à TOUTES les sources, pas au sous-ensemble du document. Un correctif correct exige de **figer les sources réellement utilisées** à la génération (le point `enregistrer` ne reçoit aujourd'hui que doc_type+idus). Reco : stocker le sous-ensemble via le registre de provenance du builder. Un allowlist deviné rendrait le badge faux (pire). |

## 3. Lot C — mails & pages légales

| # | Correction |
|---|---|
| **C-F2** | Plus de mail Radar/digest à un **résilié au-delà de sa date de fin** : `AND (acces_fin_at IS NULL OR acces_fin_at > now())` ajouté aux 3 requêtes de destinataires (digests.py ×2, events.py) — même borne que l'essai. |
| **C-F4** | **Bannière de consentement cookies** (`CookieConsent.tsx`, accepter/refuser les tiers, choix mémorisé) montée dans l'app. |
| **C-F5** | **Suppression de compte en libre-service** : `POST /compte/supprimer` (confirmation « SUPPRIMER », réutilise `effacer_compte_rgpd`). |
| **C-F6** | **Export de mes données** : `GET /compte/export` (JSON de toutes les tables `compte_id`, secrets exclus) — promesse CGV art. 7 / RGPD art. 20. |
| **C-F1/F3/F9/F10/F8** | Gestes **Brevo/Stripe** (console) → `gestes-prod/brevo-stripe.md`. |
| **C-F7** | *(documenté)* — avertissement de fin d'essai : aucun job nocturne ne scanne les essais (bascule au login seul). Reco : job « essai → J-1 » (mail) + bascule à l'échéance, indépendante du login. |
| **C-F11** | *(documenté)* — Dossier PDF ≈ 13,8 s : reco barre de progression (SSE) ou pré-calcul ; non livré (chantier perf). |

## 4. Lot D — Radar

Voir §0 pour les gestes prod. Code livré : **D-F1** (biens `a_reverifier` servis à la passe de
confirmation), **D-F2** (square = surface **terrain** pour un terrain, plus de recopie en
surface_hab), **D-F3** (alerte `[URGENT]` admin quand la confirmation est bloquée **3 nuits** de
suite — blocage portail probable), **D-F8** (le €/m² **dit sa base** « hab. » / « terrain », écran &
mail). Repro D-F2 : `test_df2_*`.

## 5. Lot E — fiches communes

- **E-2 (ROUGE)** — Saint-Denis « mouvement de terrain 0,1 % » : **cause trouvée** (0 feature mvt
  terrain pour 97411 ; le garde `--alea` sautait la commune car elle avait déjà de l'inondation). Fix
  au code (garde sur la présence de mvt terrain) + geste prod de re-ingestion. **Les fiches de
  parcelles de Saint-Denis SONT touchées** (même couche ; vérifié : `97411000CE0218` sans aléa mvt
  terrain).
- **E-1 (MAJEUR)** — SCOT **servi** au payload (était calculé puis jeté) + statut corrigé (geste) +
  front durci (« en projet » ne peut plus s'afficher « approuvé »).
- **E-3** — « Parc national » ne compte plus que le **cœur** (Le Port → faux, Cilaos/Salazie → vrai).
- **E-5** — écart demandé/acté **masqué** si les biens en vente sont sous le seuil (fin du +66 % sur 7).
- **E-7** — millésime zonage ABC **truthful** (arrêté 1er août 2014 consolidé + reclassement 02/10/2023).
- *(documentés : E-4 loyer OLL/DHUP, E-6 VEFA faible échantillon, E-9 répartition RNU, E-10/E-11.)*

## 6. Lot F — accessibilité

- **F1 (MAJEUR)** — contraste : `txt-mut` 4,20 → **5,51:1**, `txt-off` 3,52 → **5,09:1**, `cp-faint`
  3,20 → **5,16:1**, `st-exclue` 4,35 → **5,41:1** sur bg-0 (palette `tailwind.config.js`).
  `txt-faint`/`txt-ghost` laissés (bordures/désactivé, non-texte).
- **F4** — label-in-name : Notifications porte « (99+ non lues) », Fond de plan porte le nom du fond.
- **F5** — **lien d'évitement** + **`<main>`** unique + **`<h1>`** par vue (lecteur d'écran).
- **F6** — anneau de focus net sur le **composeur du Copilote** (bordure menthe permanente ≠ focus).
- **F9** — omnibox : `aria-label` persistant (le placeholder disparaît à la saisie).
- **F10** — carte : nom accessible **français** (« Carte interactive du foncier… »), plus « Map ».
- *(documentés, chantiers plus lourds : **F2** CRM nested-interactive ×187, **F3** cibles <24px,
  **F8** `th scope` dispersés — le rapport F les notait déjà comme les plus gros postes.)*

---

## 7. Recette

- Reproductions Lot A/B/D : `tests/test_nu5_fix_1.py` — **13/13 vertes** ; repros live rejouées (curl).
- Frontend : **tsc 0 erreur**, **vitest 274 tests verts** (8 suites bloquées par le symlink
  `node_modules` cross-répertoire du worktree — `server.fs.allow` sur le worker maplibre,
  environnemental ; vertes dans l'env complet / le hook).
- Backend (sous-systèmes touchés) : voir §8 (sweep ciblé).
- Harnais des 6 lots : présents dans `docs/audit-2026-11/nu-5/{A..F}/` ; branchement au banc de nuit
  (VÉRITÉ-PERMANENTE-1) préparé — voir §9.

## 8. Résultats de banc

- **Reproductions `tests/test_nu5_fix_1.py` : 13/13 vertes** (A-O1/O2/O3, A-O4/O5/O6, B-F1 garde
  structurelle, B-F2/F4, D-F2).
- **Suite de cohérence (banc en-process, base `labuse`) : 3368 comparaisons · 0 écart.**
- **Frontend : `tsc -b` 0 erreur · `vitest` 274/274** (8 suites non chargées = artefact du symlink
  `node_modules` cross-répertoire du worktree — `server.fs.allow` sur le worker maplibre ; vertes dans
  l'env complet).
- **Banc backend complet (`pytest tests/`, base `labuse_test`) : 4654 passés · 92 skips · 14 rouges**,
  triés :
  - **3 régressions NU5-FIX-1 → CORRIGÉES** et re-testées vertes : `/compte` manquait au proxy dev
    (`vite.config.ts`) et à la classification des routes mutantes (`test_nu4fix_1_securite`, nouvelles
    routes RGPD) ; le « + N autres établissements » de l'Étude de zone imprimait un nombre hors
    registre (verrou écran=PDF) → reformulé sans chiffre.
  - **5 flaky / ordre-dépendantes** (vertes en isolation) : `test_circuit_p3_lot2`,
    `test_notifications_m85` (×2), `test_pige_digests::test_echec_envoi_bruyant`, `test_simulplu` —
    pollution d'état partagé (event_log / mail_queue) par un test antérieur du run complet.
  - **6 « base réelle » pré-existantes** (exigent la base applicative `labuse`, pas `labuse_test`) :
    `test_m137_tuiles` (UndefinedColumn), `test_autonomie_1_db`, `test_circuit_p3_lot3`,
    `test_circuit_p_lot1`, `test_garanties::g7`, `test_lot1_tables` — **aucune ne touche un fichier
    modifié par NU5-FIX-1** (tuiles geojson, contrôle de run, réservoirs circuit, sonde, verrous lot1).
- **Pre-commit hook** (garde gros fichiers > 2 Mio, `scripts/git-hooks/pre-commit`) : vert (tous les
  fichiers ajoutés sont du texte source/docs).

## 9. Dette / suites

- Brancher formellement les harnais A/B/D/F au banc de nuit (VÉRITÉ-PERMANENTE-1).
- B-F8, C-F7, C-F11, E-4/E-6/E-9, F-2/F3/F8 : documentés ci-dessus, non livrés (chantiers plus
  lourds ou dépendant d'un point de données/UX à trancher).
- Rejouer les routes gardées en pilot/prod (auth désactivée en local).
