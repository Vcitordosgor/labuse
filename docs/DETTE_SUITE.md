# Dette de la suite de tests — inventaire des ~30 rouges pré-existants

Mesuré le 22/08/2026 sur `main` (branche `fix/dette-suite`) : **30 failed · 1613 passed · 43 skipped**.
Phase 1 = INVENTAIRE (ci-dessous). Phase 2 = RÉPARÉ.

## ✅ PHASE 2 — RÉSOLU (22/08/2026) : suite 0 failed (1643 passed · 43 skipped)
- **Cluster 2 (cascade proprietaire)** : SEED corrigé (`demo_saint_paul.py` — nom de source aligné
  sur `SRC_FF`), tests conservés. PM vérifiée LIVE sur parcelle réelle. Indivision = mock démo,
  noté dans le seed ET §2 (jamais un signal client tant que Fichiers fonciers non ingérés).
- **Les 27 autres** : tests RÉ-ANCRÉS sur la décision produit en vigueur, chacun portant en
  commentaire le mandat + la date (M124-A PDF data-only, M126 troncature, M128 bilan, M129 §1
  CERFA/superficie, M129-E nommage pack, rename SAR→Potentiel foncier Région, M128-6 scoreur
  constat nu, division_or dormant).
- **Point 3** : le test qui grep le source (`test_vocabulary` SAR) est réécrit sur la SORTIE
  SERVIE (exécute `SarLayer`, lit le verdict). `test_front_reliquats`/`test_ens_commune`/
  `test_decisions` étaient déjà sur la sortie servie (strings mises à jour).
- **AUCUN code produit modifié** hors le seed démo : ce n'étaient pas des défauts, mais des
  tests dérivés. Verdict Phase 1 confirmé (cf. cluster 2 : PM live, aucune régression).

---

## PHASE 1 — inventaire (au moment de la mesure). Groupé par CAUSE, **ordonné par gravité produit**.

## Cadre (corrige une idée reçue)
Tous les mandats concernés (M124-A, M126, M128, M129, M129-C, M135/M136/M137, la bascule
SAR→« Potentiel foncier Région », le scoreur M128-6) **SONT dans `main`** (ancêtres de HEAD,
vérifié). Ces rouges ne sont donc PAS des correctifs « en attente de merge » : ce sont des
**tests qui encodent un contrat que le produit a délibérément changé** — la décision produit est
en prod, le test ne l'a pas suivie. (La mémoire « M137 NON mergé » était vraie à l'écriture ;
Vic a mergé depuis.)

## Verdict de client-visibilité (l'essentiel)
**Aucun défaut client confirmé.** 27/30 sont des tests dérivés contre une décision produit
assumée. **3 restent À CONFIRMER** (cascade `proprietaire`, cluster D) : seul endroit où une
régression visible ne peut pas être exclue par lecture seule.

**Réponse directe au doute n°1 (« un tier s'affiche-t-il encore en interne quelque part ? »)** :
NON. Sur le PDF client, les assertions « aucun code technique ne fuite » PASSENT ; ce qui
échoue, c'est « le libellé client est présent » — car **le PDF n'imprime plus AUCUN verdict**
(M124-A, `pdf_premium.py:6` « plus de verdict/rang/score — l'analyse reste à l'écran »). Rien ne
fuite ; le verdict est simplement absent du PDF, par décision.

---

## 1. PDF — libellés de tier absents · 12 tests · `tests/test_m54ab_verdict_rendu.py`
**Cause unique** : M124-A a retiré verdict/rang/score du PDF client (données pures) ;
`render_fiche_pdf` n'imprime plus `TIER_LABELS[tier]` ni le rang. Le test (contrat M54-AB, 08/10)
exige encore le libellé + `rang/rang_total` dans le PDF.
**Surface** : PDF premium (livrable client). **Gravité : HAUTE** (gros bloc, surface client) —
mais **DRIFTED TEST**, pas de défaut : rien ne fuite, le verdict est volontairement hors PDF.
- `test_aucun_code_technique_par_tier[×11]` (:42) — `TIER_LABELS[tier]` absent du PDF — DRIFTED — le PDF n'affiche aucun libellé de tier (M124-A).
- `test_rang_avec_denominateur` (:52) — `57643/428239` absent (PDF finit « page 1/1 ») — DRIFTED — le rang n'est plus imprimé (M124-A).

## ⚠ SIGNAL DÉMO-SEULEMENT — l'indivision n'est pas sourçable sur du réel
Le flag « indivision » de la couche `proprietaire` n'existe QUE dans le seed démo (mock). Sa
seule source réelle possible serait les **Fichiers fonciers (Cerema)** = statut « manuel »
(convention interdite, jamais ingérée) ; la table servie `parcelle_personne_morale` (DGFiP,
82 701) ne porte NI indivision NI `nb_droits`. **Ne jamais présenter l'indivision comme un signal
client disponible** tant que les Fichiers fonciers ne sont pas conventionnés/ingérés. (La
personne morale, elle, EST réelle et servie — voir ci-dessous.)

## 2. Cascade `proprietaire` (seed démo Saint-Paul) · 3 tests · `tests/test_cascade.py` — RÉSOLU
**Vérifié sur parcelle RÉELLE** (`97411000DE0285`, COMMUNE DE SAINT DENIS) : la personne morale
s'affiche bien (`_q_v2_fiche.proprietaire_moral` + cascade `foncier_public`) → **aucun défaut
client**. **Cause = SEED DÉRIVÉ** : la couche lit `SRC_FF="DGFiP — parcelles des personnes
morales"` (phase2.py:16, renommée M125-C6) mais le seed injectait encore le mock sous l'ancien
« Fichiers fonciers (Cerema) » → `latest_source_result` ne trouvait rien → UNKNOWN.
**Fix = seed corrigé** (`demo_saint_paul.py`, nom de source aligné) ; les 3 tests sont conservés
(ils testent vraiment la couche, on ne les affaiblit pas). Indivision = mock démo (encart ci-dessus).
- `test_statuts_attendus` (:50) — P7 attendu `a_creuser`, obtenu autre — SEED DÉRIVÉ — statut démo P7.
- `test_opportunite_p1_signaux_positifs` (:64) — `proprietaire` POSITIVE (personne morale) = None sur P1 — À CONFIRMER.
- `test_indivision_flag_fort` (:98) — `proprietaire` SOFT_FLAG « indivision » FORT = None sur P7 — À CONFIRMER.

## 3. Calculette / bilan foncier · 4 tests · `tests/test_bilan.py`
**Cause** : reformulation M128-2/M128-3 — SDP = `surface/coef_rendement` (÷0,80) au lieu de
`shab×coef` (×1,15) ; charge foncière négative n'est plus écrêtée à 0 (« plus d'écrêtage muet ») ;
« fragile » arrondi au k€ et non au 100 k€ (l'arrondi 100 k€ affichait « 0 € » = c'était LUI le bug).
**Surface** : nombres de charge foncière (fiche/exports, client). **Gravité : MOYENNE-HAUTE**
(surface client chiffrée) — mais **DRIFTED TEST** : nombres cohérents entre eux sous les
nouvelles formules ; le test garde l'ancienne formule.
- `test_charge_fonciere_a_rebours_formule` (:72) — SDP `÷coef_rendement` ≠ `×coef_plancher` — DRIFTED.
- `test_charge_fonciere_negative_signalee` (:88) — CF négative gardée (non écrêtée à 0) — DRIFTED — l'alerte « négative » se déclenche toujours.
- `test_prix_fragile_arrondi_et_simulation_indicative` (:104) — arrondi k€ ≠ 100 k€ — DRIFTED — l'ancien arrondi était le défaut.
- `test_calculette_arithmetique_independante` (:131) — même reformulation SDP — DRIFTED.

## 4. Autres PDF / exports · 3 tests
**Cause** : symboles/contrats retirés ou renommés côté PDF, tous DRIFTED, aucun défaut client.
- `tests/test_api_q_v2.py::test_pdf_verdict_pas_de_matrice_morte` (:69) — `pdf_premium.TIER_V2_COLOR` absent (constante de tier retirée du PDF, M124-A/M126) — DRIFTED — le test lit un symbole qui n'existe plus.
- `tests/test_mp_exports.py::test_pdf_premium_pas_de_matrice_morte_et_exclut_age_dirigeant` (:18) — le PDF ne tronque plus à 2 pages (M126) → `sections_omises` absent — DRIFTED — fonction de troncature supprimée, sans impact client.
- `tests/test_pre_dossier.py::test_pack_cerfa_prerempli_et_libelle` (:53 StopIteration) — entrée zip nommée `{pfx}-CERFA-13406-17-prerempli.pdf`, le test cherche `cerfa_13406-17…` — DRIFTED — le CERFA est présent, nom de fichier changé.

## 5. Vocabulaire SAR → « Potentiel foncier Région » · 4 tests
**Cause unique** : la couche SAR a été renommée (`phase1.py:23` `SRC_SAR="Potentiel foncier
Région (Région ODS)"`, messages :165/:175 sans le mot « SAR »). Les tests attendent les anciennes
chaînes « proxy SAR »/« SAR ». **Surface** : wording cascade (fiche) + stub IA. **Gravité :
MOYENNE** — **DRIFTED TEST**, wording honnête dans les deux sens.
- `tests/test_decisions_1_3.py::test_d2_divergence_sur_zone_u` (:105) — attend « proxy SAR divergent… » vs « Potentiel foncier Région divergent… » — DRIFTED.
- `tests/test_decisions_1_3.py::test_d2_divergence_au_remontee_en_vigilance` (:138) — idem côté `resume.py:110` — DRIFTED.
- `tests/test_ai.py::test_stub_est_valide_et_ne_corrige_pas` (:33) — attend le flag « SAR juridiquement supérieur au PLU. » plus émis — DRIFTED.
- `tests/test_vocabulary.py::test_sar_libelles_honnetes_dans_la_cascade` (:45) — grep « …aucune contrainte SAR déduite… », le code dit « …aucune contrainte déduite… » (mot SAR retiré) — DRIFTED.

## 6. Scoreur d'adresse — badge marché · 1 test · `tests/test_front_reliquats.py`
- `test_r5_scoreur_verdicts_prix` (:174) — `ScoreurAdresse.tsx` sert le « constat nu » M128-6
  (prix probable, écart, marge) et n'a AUCUN de `sous_marche/dans_marche/sur_marche/non_estimable`.
  **Gravité : BASSE** — **DRIFTED TEST** : cible un badge « marché » (M137-S) **non ajouté** au
  produit ; le scoreur servi fonctionne (constat honnête), aucun défaut client. `sous_marche` est
  une feature non-encore-là, pas une feature retirée.

## 7. ENS commune — wording PASS · 1 test · `tests/test_ens_commune.py`
- `test_ens_commune_couverte_sans_intersection_pass` (:43) — verdict PASS correct, mais la chaîne
  de détail attendue (« Hors ENS ») a changé. **Gravité : BASSE** — **DRIFTED TEST probable**
  (le classement PASS est bon ; seul le libellé diffère) — à confirmer d'un coup d'œil sur la
  branche PASS de `EnsLayer` en Phase 2.

## 8. division_or (outil DORMANT) · 2 tests · `tests/test_division_or.py`
**Cause** : outil SORTI DU PRODUIT (M129-C, dormant). Tests `@pytest.mark.db` gated sur une table
de référence non matérialisée dans cette base.
**Gravité : MINIMALE** — **DRIFTED / infra**, **NON client-visible** (outil retiré).
- `test_resolution_insee_vers_nom` (:226) — `'97415' == 'Saint-Paul'` : la résolution renvoie l'INSEE (table ref vide) — DRIFTED/infra.
- `test_all_communes_liste_canonique` (:239) — `0 == 24` : liste vide (table ref vide) — DRIFTED/infra.

---

## Synthèse pour l'arbitrage Phase 2
| # | cluster | n | gravité | verdict |
|---|---------|--:|---------|---------|
| 1 | PDF libellés de tier (M124-A) | 12 | Haute (surface, volume) | DRIFTED — rien ne fuite |
| 2 | Cascade `proprietaire` (démo) | 3 | Haute | **À CONFIRMER** (seul risque client) |
| 3 | Calculette/bilan (M128) | 4 | Moyenne-haute | DRIFTED — nombres cohérents |
| 4 | Autres PDF/exports | 3 | Moyenne | DRIFTED |
| 5 | Vocabulaire SAR (rename) | 4 | Moyenne | DRIFTED |
| 6 | Scoreur badge marché (M137-S) | 1 | Basse | DRIFTED — feature non ajoutée |
| 7 | ENS wording PASS | 1 | Basse | DRIFTED probable |
| 8 | division_or (dormant) | 2 | Minimale | DRIFTED/infra — non client-visible |

**Deux natures de réparation possibles (à trancher par Vic, Phase 2)** :
- **Ré-ancrer le test** sur la décision produit en vigueur (clusters 1,3,4,5,6,7,8) — le produit
  a raison, le test suit. Gros du travail, sans risque client.
- **Vérifier d'abord** le cluster 2 (cascade `proprietaire`) sur une parcelle réelle : si les
  signaux propriétaire manquent VRAIMENT sur la fiche → défaut à corriger dans le code ; sinon →
  dérive du seed démo, ré-ancrer. **À faire en premier** (seule inconnue à risque client).
