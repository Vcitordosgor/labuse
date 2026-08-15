# AUDIT M91 — les 13 rouges honnêtes : tri par nature

**Mandat M91 · Phase 1 (tri) · branche `audit/m91-treize-rouges` · NON mergé**

M90 a retiré les faux rouges d'environnement. Restent 13 rouges honnêtes, jadis
masqués derrière les `ProgrammingError`. Trois natures, à ne pas confondre :
**finding réel** (le code a un défaut) · **test périmé** (le test teste un monde
disparu) · **seed obsolète** (la fixture ment). Doctrine : *mesurer avant
d'affirmer* · *un test rouge est une question* · *jamais de vert en cassant ce
qu'il protège* · *ne jamais aligner un test sur le code sans savoir lequel a
raison*.

## Résultat du tri (preuve, pas intuition)

| # | Test | Nature | Sert un chiffre servi ? | Mandat du changement | Preuve |
|---|---|---|---|---|---|
| 1 | test_phase2_layers::test_dvf_mutations_contexte_positif | **Test périmé** | Oui (prix terrain DVF, bonus scoring) | **M79 P1** | le stub `_Ctx` du test fournit `dvf_stats()` mais pas `dvf_sector_terrain()` que le code lit (phase2.py:39) ; la vraie `EvalContext` (context.py:453) l'implémente. M79 a basculé rayon→secteur cadastral. |
| 2 | test_phase2_layers::test_dvf_aucune_mutation_pass | **Test périmé** | Oui | M79 P1 | idem — stub sans `dvf_sector_terrain`. |
| 3 | test_phase2_layers::test_dvf_commune_non_ingeree_unknown | **Test périmé** | Oui | M79 P1 | idem. |
| 4 | test_residuel::test_terrain_nu_residuel_quasi_integral | **Test périmé** | Oui (SDP résiduelle, sous-densité) | **M32 Phase C** | le test passe `session=None` ; le code lit désormais `parcel_bati_revele` (residuel.py:72, bâti révélé CoSIA M32). Test antérieur (2026-06-12) au mandat (2026-08-05). |
| 5 | test_residuel::test_parcelle_dense_pas_sous_densite | **Test périmé** | Oui | M32 Phase C | idem `session=None`. |
| 6 | test_residuel::test_sdp_estimee_flaggee_quand_hauteur_absente | **Test périmé** | Oui | M32 Phase C | idem. |
| 7 | test_residuel::test_seuil_sous_densite_borne | **Test périmé** | Oui | M32 Phase C | idem. |
| 8 | test_flash_report::test_collect_parcelle_pauvre_sections_omises | **Test périmé** | **Non** (état d'absence honnête, aucun chiffre) | **M73-D** | le test attend `data["terrain"] is None` sur base pauvre ; `_terrain` y met `mode_b` depuis M73-D (c8e208d1). `compute_mode_b` hors-population renvoie `{disponible:False, motif:"hors population…"}` — un ÉTAT (« Sans objet »/« Non évaluée »), jamais un chiffre inventé (docstring : « pas de bilan inventé »). |
| 9 | test_faisabilite::test_au_st_non_constructible_neuf | **Test périmé** | **Non** (le verdict servi est correct) | **M58-P1 Q2** | le test attend `"transition"` dans le verdict ; M58-P1 a retiré ce hardcode (engine.py:188) → verdict réel « Construction neuve non autorisée en zone AU3st ». La substance (non-constructible, 0 logement) passe ; seul le mot vieilli. |
| 10 | test_deps_declared::test_tous_les_imports_du_code_sont_declares | **Finding réel** | Non (packaging) | — | `fitz`/`PIL`/`requests`/`urllib3` sont RÉELLEMENT importés (plan_situation.py, plu_ingest.py, plu_corpus.py) mais ABSENTS de pyproject.toml. Le garde a raison : dépendances non déclarées (risque d'install). |
| 11 | test_front_reliquats::test_r1_nav_onglets_hors_du_panneau_ia | **Test périmé** | Non (structure front) | **M61-P1** | le test attend `onClose={() => setAskOpen(false)}` ; M61-P1 (panneau IA unifié) a remplacé le booléen `askOpen` par l'état `iaOuvert` → `onClose={() => setIaOuvert('aucun')}` (Fiche.tsx:1844). L'onClose EXISTE ; la protection R1 (AskBar séparé/repliable, « plus de navigation par onglets ») tient. |
| 12 | test_api::test_fiche_double_score_et_cascade | **Seed/fixture obsolète** | Non (structure de route) | — | la fixture `client` appelle `evaluate_parcels(..., persist=True)` SANS `dryrun_label` ; la persistance dryrun est conditionnelle (pipeline.py:132) → aucune ligne cascade produite sous le run que la fiche lit. `assert len(f["cascade"]) > 10` → 0. La parcelle démo `97415000AB0001` est bien seedée (seed_demo insee=97415), mais sans cascade servie. |
| 13 | test_api::test_fiche_core_sans_bloc_promoteur_lazy | **Seed/fixture obsolète** | Non | — | même cause : `len(f["cascade"]) > 10` échoue faute de cascade produite au run lu. |

## Synthèse

- **10 tests périmés** — le CODE a raison, l'attente du test teste un monde disparu :
  M79 (terrain-secteur ×3), M32 (bâti révélé ×4), M73-D (réhab servie ×1), M58-P1
  (verdict zone réelle ×1), M61-P1 (panneau IA unifié ×1). **Aucun ne révèle un
  chiffre servi faux** — au contraire, chaque changement de monde est une correction
  déjà arbitrée par Vic et servie.
- **1 finding réel** — `test_deps_declared` : 4 dépendances importées non déclarées
  dans `pyproject.toml`. Ne touche aucun chiffre client (packaging).
- **2 seeds obsolètes** — `test_api` ×2 : la fixture `client` ne produit plus de
  cascade lisible au run servi (`evaluate_parcels` appelé sans `dryrun_label`).

### Le tri prioritaire : le drift `mode_b` (M73-D) — TRANCHÉ

La réhabilitation est servie dans les 5 documents. **Question du mandat : le drift
est-il dans le code servi ou seulement dans l'attente du test ?** Réponse mesurée :
**seulement dans l'attente du test.** `compute_mode_b` hors-population renvoie un
état d'absence (`disponible:False`, « Sans objet »/« Non évaluée »), JAMAIS un chiffre
inventé — la docstring l'exige explicitement. Aucun banquier ne voit un chiffre de
réhabilitation faux. Le test attend l'omission d'une section que M73-D a délibérément
transformée en état servi. **Il n'y a pas de finding servi caché ici.**

### Verdict d'ensemble

**Aucun des 13 rouges ne signale un chiffre servi faux.** Les 4 qui touchent un
chiffre servi (phase2 ×3, residuel ×4) sont des tests dont le SCAFFOLDING est périmé
(stub sans la méthode M79 ; `session=None` alors que M32 lit la base) — le chiffre
servi est le bon, c'est le test qui ne l'exerce plus. C'est rassurant : M90 a démasqué
de la dette de test, pas des bugs servis.

## Traitement proposé (Phase 2, après arbitrage Vic)

- **Findings réels (1)** — `test_deps_declared` : déclarer `pymupdf`/`pillow`/`requests`/
  `urllib3` dans `pyproject.toml`. Réparer le code (la config), pas le test.
- **Tests périmés qui SERVENT un chiffre (7 : phase2 ×3, residuel ×4)** — ne PAS juste
  changer une assertion : remettre à jour le SCAFFOLDING pour que le test EXERCE la
  logique servie actuelle (stub `_Ctx` qui fournit `dvf_sector_terrain` avec des valeurs
  représentatives par scénario ; tests residuel dotés d'une vraie session lisant
  `parcel_bati_revele`). La protection est préservée, l'attente documentée (M79 / M32).
- **Tests périmés sans chiffre (3 : mode_b, verdict, front)** — mettre l'attente à jour
  en documentant le mandat responsable (M73-D / M58-P1 / M61-P1), sans abaisser
  l'exigence (mode_b : vérifier que `terrain` ne porte QUE des états d'absence, pas un
  chiffre ; verdict : asserter le libellé réel + la substance 0 logement ; front :
  asserter l'`onClose` réel `setIaOuvert('aucun')`).
- **Seeds obsolètes (2 : test_api)** — corriger la fixture `client` pour produire une
  cascade lisible au run servi (passer un `dryrun_label` = run servi à `evaluate_parcels`,
  ou lire la cascade au bon run), vérifier qu'elle reste représentative.

## STOP — arbitrage Vic

Aucun finding servi caché → aucune réparation de code servi + rejeu de run n'est
requise (bonne nouvelle). Reste à valider le périmètre et la manière (voir arbitrage
joint). Chaque correction sera un commit séparé nommé par le test et sa nature ; aucun
test ne sera mis au vert en abaissant son exigence ou en retirant une assertion.
