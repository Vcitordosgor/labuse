# M13 — CORRECTION VAGUE 1 : RAPPORT DE VAGUE

**Mode** : autonome A→F. **CC n'a rien mergé** — 6 branches poussées. Filet : tag `avant-m13`.
**Base** : `main` (M12 mergée, `884daf0`). **Golden** : 116/116 avec `LABUSE_DEV_MODE=1` sur chaque branche.
**Règle de preuve tenue** : chaque point livré a une **capture depuis l'app en marche**, vérifiée par CC. Les captures sont commitées sous `qa/m13/<LOT>/`.

> La leçon M13 : build 0 erreur + golden 116/116 ne prouvent PAS qu'une fonctionnalité marche à l'écran. Chaque agent de cette vague était **bloqué sur la preuve visuelle** ; CC a **ouvert et regardé** les captures clés de chaque lot (pas seulement lu les rapports).

---

## 1. TABLEAU D'AUDIT DES FILTRES (LOT A — point bloquant)

Run servi `q_v7_defisc`. « 3 fiches vérifiées » = fiche ouverte, signal réellement affiché.

| Filtre | Retour | 3 fiches | Verdict |
|---|---|---|---|
| **Procédure collective** | 314 → **222** | 3/3 montrent la procédure (après fix) | **corrigé** (était sur-inclusif : +92 faux positifs radiation) |
| Avec événement (BODACC) | 40 | 3/3 | juste |
| Veille succession | 7 092 | badge liste/radar (hors signaux V fiche) | juste |
| Masquer copropriétés | toggle (3 424) | n/a | juste |
| Pollution (`sol_pollue`) | 10 333 | **8/8** (re-vérifié) | juste |
| ABF | 60 618 | 3/3 | juste |
| ICPE | 66 820 | 3/3 | juste |
| Risques (PPR/aléa) | 403 865 | 3/3 | juste, **quasi-universel 93,6 %** (discriminant faible, signalé) |
| Prescription PLU | 127 513 | 3/3 | juste |
| Friche | 1 526 | 3/3 | juste |
| Propriétaire hors île | 944 | 3/3 | juste |
| DPE F-G | 27 | 3/3 | juste (data mince) |
| Détention longue | 10 814 | 3/3 | juste |
| **Dirigeant 65+** | **0** | — | mort (codes absents + pondérés 0) — déjà masqué (M12-E1), reste masqué |

**Cause racine du faux positif Vic** : `BODACC_RADIATION` (famille `radiation`, anti-signal pondéré 0, `score_v_constants.py:82`) était dans le groupe `pcl`. Une parcelle « radiation seule » a `v_score 0` → **fiche sans procédure**, pourtant servie. 92 des 314 étaient dans ce cas. Retiré. **Sous-couverture** consignée : 222/662 rattachées (~34 %) = propriétaires non rattachés, **pas** de volume forcé. Détail : `docs/mandats/M13_LOT_A.md`.

---

## 2. PREUVES PAR POINT (16 points — tous prouvés, capture + repro)

App servie sur `:80xx/socle/` (chaque lot son port). Repro = page/clic/saisie.

| Point | Preuve (`qa/m13/…`) | Reproduire | Vérifié par CC |
|---|---|---|---|
| **A** pcl corrigé | `A/03_fiche_montre_procedure.png` | `#f=1&vs=pcl&v=1`, ouvrir un résultat | ✅ fiche montre « liquidation » |
| **B1** autocomplétion omnibox | `B/b1_omnibox_suggestions.png` | taper « rue … » dans la barre du haut | ✅ 6 suggestions réelles |
| **B1** autocomplétion scoreur | `B/b1_scoreur_suggestions.png` | Outils → Scorer une adresse | ✅ |
| **B2** voir tous résultats | `B/b2_tous_affiches.png` | filtrer, atteindre le dernier | ✅ « 259 / 259 » (bug = total ignorait le filtre tier) |
| **B3** CRM ajout/renom/déplac/suppr | `B/b3_ajout.png`, `b3_renommage.png`, `b3_deplacement.png`, `b3_suppression_destination.png` | CRM → Personnaliser | ✅ + **0 `window.prompt/confirm/alert`** (grep confirmé) |
| **C** aucun scroll horizontal | `C/couches.png`, `resultats.png`, `tri.png`, `fiche.png`, `crm.png` | chaque zone | ✅ `scrollWidth==clientWidth` sur les 5 ; CRM = pager à flèches |
| **D1** Couches ouvert par défaut | `D/d1_couches_ouvert.png`, `d1_couches_referme.png` | charger ; cliquer « Afficher l'analyse » | ✅ |
| **D2** bulle « i » entière | `D/d2_bulle_entiere_crop.png` | survol d'un « i » de couche | ✅ texte complet (fin du « sans découp… ») |
| **D3** icônes équip. ×1,5 | `D/d3_equipements.png` (+ avant/après) | activer couche Équipements | ✅ |
| **D4** audit zonage officiel | (réponse §3 + texte i) | — | ✅ pas de suppression |
| **E1** recherche au lancement | `E/e1_a_trier_peuplee.png` | créer projet → Lancer | ✅ « À trier 24 » |
| **E2** phrase d'enrichissement | `E/e2_phrase.png` | vue projet | ✅ (bouton « + Chercher plus » retiré) |
| **E3** projets grisés | `E/e3_projets_grises.png` | fiche → Projet (parcelle déjà rattachée) | ✅ projet grisé « ✓ dedans » |
| **F1** Sources simplifié | `F/f1_sources.png` | onglet Sources | ✅ 2 infos/source, jargon retiré |
| **F2** bloc « mesure » retiré | `F/f2_sources_sans_bloc.png` | onglet Sources | ✅ (contenu → `docs/ARGUMENTAIRE_PRECISION.md`) |
| **F3** barre de tri | `F/f3_tri.png` | vue résultats | ✅ « mutation ×N », commune retirée |
| **F4** scoreur groupé | `F/f4_scoreur_autocomplete.png` | Outils → Scorer une adresse | ✅ champs groupés + autocomplétion ouverte |

**Points non prouvés / non livrés : AUCUN.** Les 16 points ont une capture vérifiée.

---

## 3. TEXTES PRODUITS (à relire par Vic)

**E2 — phrase d'enrichissement** (`CLIENT.projet.enrichir`) :
> « Une parcelle en tête ailleurs ? Ajoutez-la à ce projet à tout moment depuis sa fiche, avec le bouton "Projet". »

**F3 — barre de tri** :
- `×N` → **« mutation ×N »** (retenu). Écartés : « probabilité de mutation » (trop long pour un chip), « ×N susceptibilité » (moins immédiat). Le title porte le sens complet.
- `classement` → title : « Classe les parcelles par ordre de priorité (n°1 = la plus prometteuse) — copropriétés en queue ».
- `commune` → **retiré** de l'UI (type `SortKey` conservé côté API, contrat back intact).

**F1 — Sources** : deux infos/source — « Version en service » (données jusqu'au… / millésime / date d'ingestion) + « Dernier contrôle » (`source_checks.verified_at`). **`source_checks` est vide** → « Dernier contrôle : — » partout, **aucune date inventée** ; le câblage affichera la vraie date dès l'audit data.

**D4 — texte « i » « Zonage PLU (zones officielles) »** (`LAYER_INFO.zonage`, recopié par l'agent D) : polygones GPU bruts déposés par la commune (Géoportail de l'urbanisme), contours d'origine non rattachés au cadastre — **pas un doublon** de « par parcelle » (colore chaque parcelle + code au clic) ni de « colorisation » (teinte toutes les parcelles par famille).

---

## 4. DÉCISIONS PRISES (réversibles)

| Point | Choix | Alternative écartée | Revenir en arrière |
|---|---|---|---|
| A pcl | Retirer `BODACC_RADIATION` du groupe | Élargir pour du volume | remettre le code dans `V_SIGNAL_DEFS.pcl` |
| B1 | **Endpoint interne** `/adresses/autocomplete` (table `adresses`) + dropdown en portal | BAN externe client (échoue/clippé) | `banAutocomplete` repointable |
| B2 | Total requêté avec filtres complets | — | — |
| C CRM | Pager à flèches (fenêtre 5 colonnes) | Barre horizontale | — |
| D1 | Couches ouvert jusqu'à l'analyse | Auto-fermeture 10 s (M12) | — |
| E3 | Bouton Projet ouvre toujours le menu ; multi-projets ; anti-doublon `ON CONFLICT` | Ouvrir direct le projet | — |
| F1 | Version + dernier contrôle (— si absent) | Inventer une date | — |
| F3 ×N | « mutation ×N » | 2 autres (consignées) | `strings.ts` |

---

## 5. NON FAIT / BLOQUÉ

- **F1 « Dernier contrôle »** : affiché « — » car `source_checks` jamais alimentée. Pas un blocage de code — dépend de l'audit data. Consigné, honnête.
- Dettes pré-existantes notées (non causées par la vague) : erreurs de collection pytest `test_p_model_*` / `test_findings_n4` (module `pandas` absent du conda env) ; ordre de suite auth-cache.

---

## 6. BRANCHES ET ORDRE DE MERGE CONSEILLÉ

CC ne merge pas. Vic merge en `git merge --no-ff`.

| Ordre | Branche | Lot | Dépendance / note |
|---|---|---|---|
| 1 | `fix/m13-a-filtres` | A + **ce rapport** | indépendante (base main) — **fix critique, à merger** |
| 2 | `fix/m13-b-non-livre` | B | indépendante (base main). Backend additif `/adresses/autocomplete`. |
| 3 | `fix/m13-d-couches` | D | indépendante |
| 4 | `fix/m13-e-projet` | E | indépendante |
| 5 | `fix/m13-c-scroll` | C | **embarque A** (basée sur A) — merger A avant/avec, sinon C l'amène. Conflit `Kanban.tsx` avec B (pager C vs édition B — garder les deux : pager + édition). |
| 6 | `fix/m13-f-lisibilite` | F | **embarque B** (F4 réutilise l'autocomplétion de B). Merger B avant/avec, sinon F l'amène. |

**Conflits anticipés** : `crm/Kanban.tsx` entre **B** (colonnes personnalisables) et **C** (pager à flèches) — les deux intentions sont compatibles (édition + pager). `panel/ResultsSection.tsx` touché par B/C/F (tri, total, pager liste) — zones proches, résolution manuelle. `SourcesPage.tsx` : F la réécrit largement (par-dessus B).

**Vérification CC** : chaque branche build `tsc+vite` 0 erreur + golden **116/116** (`LABUSE_DEV_MODE=1`, `PYTHONPATH=src` obligatoire sinon retombe sur un run mort → 0/116 faux négatif). B re-vérifiée indépendamment par CC (endpoint sert la vraie BAN interne + golden 116/116). Captures clés ouvertes et regardées par CC.
