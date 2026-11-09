# ECRANS-NOV-2 — compte rendu

**Mandat** ECRANS-NOV-2 — l'écran **Analyse LABUSE par scénario**.
**Branche** `feat/ecrans-nov-2` (worktree `~/Desktop/labuse-ecrans2`). **Aucun merge, aucun accès
production.** Front (+ route back déjà servie) et quatre ajustements d'API (recette d'Astra).
Ports de travail : front **9990**, back **7190**. Run servi **q_v20** (base locale, 433 229 parcelles ;
table `parcel_scenario_v2_runs` déjà peuplée, keep/rebuild = 433 229 chacun).

Références : la maquette `docs/design/maquettes/nov-2026/7-analyse-labuse.png`, l'endpoint
`GET /analyse/scenarios` (ALGO-FIX-1, `docs/audit-2026-11/algo-fix-1/COMPTE-RENDU.md`), la DA
existante et les règles de focus/sélection uniques de l'app (RETOURS-21).

---

## 1. Ce qui est livré (écran)

Une **nouvelle vue plein écran** `analyse` (comme Documents / Sources), atteignable par le rail
(entrée « Analyse ») et le deep-link `#analyse=1`. Elle **LIT** `GET /analyse/scenarios` — elle
n'invente aucun chiffre ; tout (effectifs, bandes, quantités, adresses, vigilances) vient de la
réponse.

- **En-tête** : « Analyse LABUSE · N parcelles » + sélecteur de commune, « ← Retour » et
  « Comprendre l'analyse » sur une ligne. N = `n_selection` de l'API.
- **Objectif** : « Prospection vente » / « Potentiel foncier » (bascule, l'active en vert opaque).
  En potentiel, sous « Projet · logement » : « Bâti conservé » / « Reconstruction ».
- **La phrase qui classe**, toujours présente : « Classées par Signal de mutation à 12 mois… » /
  « Classées par bande, puis par surface de plancher supplémentaire. » / « … puis par capacité du
  nouveau projet. Le gain net est signé. »
- **Bloc de filtres repliable** : tout le bloc (objectif, scénario, puces) se replie en une ligne de
  résumé (ex. « Potentiel foncier · Bâti conservé · Toutes ▾ ») ; **ouvert par défaut** à la première
  analyse.
- **Puces comptées** + **barre de répartition** au-dessus ; les effectifs viennent de l'API et
  **font le total**. En prospection : Signal (Tous · Fort · Moyen · Faible · Non évalué). En
  potentiel : une seule rangée **bandes puis statuts** (Excellente · Bonne · À étudier · Faible · À
  vérifier · À différer · Aucun ajout · Hors projet · Calcul à compléter). Une puce **narrowe la
  liste** sans toucher les effectifs.
- **Cartes de résultat** : référence, adresse, une ligne de faits (surface · bâti/terrain nu ·
  zone), un chiffre et une raison ; puces **bande · Signal** (le Signal secondaire en potentiel,
  **principal en prospection**). Parcelle à cheval : « sur la portion U (X m²) ». Reconstruction :
  « Projet · existant · gain net signé », **orange s'il est négatif ». Pied (potentiel) : scénario ·
  « Voir le détail → ». Aucune formule sur la carte.
- **Détail** (overlay, `enrich=1`) : deux gros chiffres, gain net, **« Ce qui explique »** (points ×
  facteurs = score → bande), **« À vérifier avant d'aller plus loin »** (les vigilances servies).
- **Carte** : au-delà de la limite de peinture (20 000), un message clair invite à peindre les
  meilleures bandes (Excellente + Bonne) via « Voir sur la carte → » (qui passe à la carte avec le
  périmètre de commune + l'analyse allumée : la carte réutilise alors son mécanisme éprouvé
  `getFiltreIdus(f, bande)` + plafond serveur 20 000 + toast « meilleures bandes »). Entre-Deux
  (6 341) peint tout ; le cas « trop large » se vérifie à l'échelle île (voir §4).

### Fichiers front
- **Ajoutés** : `src/components/analyse/AnalyseScenario.tsx` (l'écran : en-tête, bloc repliable,
  barre + puces, cartes, détail, « Comprendre »), `src/lib/scenario.ts` (vocabulaire + ordonnancement,
  les libellés du mandat), `src/lib/__tests__/scenario.test.ts` (12 tests), `qa/ecrans_nov_2_webkit.mjs`.
- **Modifiés** : `src/lib/api.ts` (`getAnalyseScenarios` + types), `src/store/useApp.ts` (vue
  `analyse`), `src/App.tsx` (montage + deep-link), `src/components/Rail.tsx` (entrée + icône),
  `vite.config.ts` (proxy dev `/analyse/scenarios` — il **manquait**, distinct de `/analyse-annonce`).

---

## 2. Recette d'Astra — côté API (le strict nécessaire)

Quatre ajouts, additifs, lecture seule ; aucune table historique touchée.

1. **Codes AU phasés reconnus** (`scenarios_v2_build._famille_portion_productive`). La regex
   `([A-Za-z]+)` **échouait sur « 1AU », « 2AUc »…** (un chiffre de phase en tête) → l'AU phasée
   n'était pas vue, et sa portion au régime non établi passait pour « maintenant ». Corrigée en
   `(\d*[A-Za-z][0-9A-Za-z]*)` + retrait de l'indice de phase. Test paramétré (AU/AUc/1AU/2AU/1AUc/
   2AUm → AU ; U/Ub/UA → U ; A/N → aucun ; l'AU phasée prime sur U).
2. **Rangée de puces de prospection** + **puces qui narrowent la liste**
   (`scenarios_v2_persist`). En vente, l'API sert désormais `effectifs.par_signal`
   (fort/moyen/faible/non_evalue) sur toute la sélection — ils **font le total**. Les paramètres
   `band` / `statut` (potentiel) et `signal_niveau` (prospection) **filtrent la liste servie, jamais
   les effectifs** (toujours calculés sur la sélection entière). `n_filtre` est renvoyé à côté de
   `n_selection`.
3. **Échec d'enrichissement remonté explicitement** (`scenarios_v2_build.analyse_scenarios_payload`
   + `scenarios_v2`). La réponse live porte `enrichissement: {demande, echecs:[…], n_echecs}` (sur
   toute la sélection) et chaque parcelle un `etat_calcul` (`ok`/`failed`/…) — un échec n'est plus
   avalé en silence ni confondu avec un « calcul à compléter » demandé.
4. **Adresse factuelle** (BAN) servie pour la **seule page** (`adresses_pour`, un `DISTINCT ON`) —
   nécessaire à la carte de résultat, jamais inventée (absence = pas de clé).

Les tris, la précision et les versions mixtes live/persisté étaient déjà alignés par ALGO-FIX-1 ;
`test_algofix1_persist.py` (10) le re-vérifie vert sur q_v20, inchangé.

### Fichiers back
- **Modifiés** : `src/labuse/scoring/scenarios_v2_build.py` (regex AU, `adresses_pour`, `etat_calcul`
  + `enrichissement`), `src/labuse/scoring/scenarios_v2_persist.py` (`par_signal`, puces de liste,
  adresse de page), `src/labuse/scoring/scenarios_v2.py` (`enrich_state` dans `details`),
  `src/labuse/api/app.py` (params `band`/`statut`/`signal_niveau`).
- **Ajouté** : `tests/test_ecrans_nov_2_api.py` (18 : AU phasée, helpers de puce, et 3 DB-gardés sur
  la sélection réelle — effectifs intacts, `par_signal` fait le total, enrichissement remonté).

---

## 3. Vérifications (hook + WebKit)

- **Front** : `tsc -b` **0 erreur** · **vitest 322** (310 + 12) · `vite build` OK · scan de secrets
  « rien trouvé ».
- **Back** : `pytest -m "not db and not local and not reel and not network"` → **3200 passed**,
  0 échec. Avec base locale : `test_algofix1_*` + `test_ecrans_nov_2_api` → **tous verts** (DB-gardés
  compris). `test_proxy_dev_couvre_routes_api` vert (le proxy couvre `/analyse/scenarios`).
  `test_aucun_fichier_du_signal_modifie` vert (le Signal n'est pas touché).
- **WebKit (Safari, playwright 1.49.1 / webkit-2104)** : `qa/ecrans_nov_2_webkit.mjs` capture les
  cinq états + le détail + « Comprendre » + les filtres repliés (`captures/ecrans-nov-2/webkit-*.png`).
  **Règle de focus vérifiée APRÈS CLIC** : cliquer une puce laisse `html[data-input="mouse"]`,
  `activeElement=BODY`, `outline: none` — **aucun contour au clic** ; la sélection est un aplat vert
  opaque. (La règle est la règle globale de l'app, inchangée.)

Captures : la maquette `docs/design/maquettes/nov-2026/7-analyse-labuse.png` fait foi (« avant ») ;
les captures WebKit `frontend/captures/ecrans-nov-2/webkit-01…07.png` sont le rendu (« après »).

---

## 4. Effectifs réels (Entre-Deux, q_v20) — le croisement du mandat

| Puce (potentiel, bâti conservé) | n | Puce (reconstruction) | n |
|---|---:|---|---:|
| Excellente / Bonne / À étudier / Faible | 38 / 569 / 751 / 685 | Excellente / Bonne / À étudier / Faible | 77 / 922 / 1 033 / 527 |
| À vérifier / Aucun ajout / Hors projet | 582 / 564 / 3 152 | À vérifier / Hors projet | 630 / 3 152 |
| **Tous** | **6 341** | **Tous** | **6 341** |

Prospection (par Signal) : **Fort 1 · Moyen 5 · Faible 6 335** (somme = 6 341, « font le total »).

**Croisement « ~43 000 Bonne sur l'île »** (mandat) : à l'échelle île, `parcel_scenario_v2_runs`
keep/ESTIMATED band B = **43 122** ≈ 43 000 ✅. C'est cette cohorte que la carte peint au-delà du
plafond (meilleures bandes A+B + message), via le mécanisme carte existant.

---

## 5. Décision d'intégration (carte)

La maquette est **un panneau** (trois états, 342 px) ; l'écran est donc une vue plein écran centrée
sur ce panneau. Le mandat « Carte : au-delà de 20 000 → meilleures bandes + message » est honoré en
**réutilisant** le mécanisme de peinture éprouvé de la carte (RETOURS-21) : le bouton « Voir sur la
carte → » passe à la carte avec le périmètre de commune + l'analyse allumée ; la bannière « trop
large » (≥ 20 000) le dit explicitement. On **ne réimplémente pas** une peinture par bande V2 à
l'échelle île (non disponible à bas coût : l'endpoint est commune/IDU-scopé) — on s'appuie sur la
carte qui sait déjà peindre A/B avec son toast. Rien ne casse côté carte : son chemin est inchangé.

---

## 6. Limites honnêtes

- La **reconstruction chiffrée** n'est persistée qu'à Entre-Deux + Saint-Denis (enrich au run de
  nuit, cf. ALGO-FIX-1). Ailleurs, « Calcul à compléter » — l'écran le dit, jamais une capacité
  déduite. Le **détail** (overlay) force `enrich=1` par parcelle (≤ 500) : il chiffre la
  reconstruction à la demande.
- L'écran est **commune-scopé** (l'endpoint exige commune ∩ IDU) : défaut Entre-Deux, sélecteur de
  commune en en-tête. Pas d'analyse scénario « île entière » en un appel (par conception de
  l'endpoint).
- Le **type de bien** affiché (« bâti » / « terrain nu ») est dérivé de l'existant E (E>0 vs E=0) —
  factuel, pas inventé ; l'endpoint ne sert pas « maison / immeuble ».

---

*Fin du compte rendu. Branche `feat/ecrans-nov-2`, non mergée, run servi intact, Signal intact.*
