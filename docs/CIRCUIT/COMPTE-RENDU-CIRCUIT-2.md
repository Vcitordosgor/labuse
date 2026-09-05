# COMPTE-RENDU CIRCUIT-2 — tenu au fil des lots

Branche `feat/circuit-2` depuis `feat/circuit-1` (CIRCUIT-1 non mergé dans main), worktree `~/Desktop/labuse-audit`, base locale `labuse`. Mandat : `docs/CIRCUIT/MANDAT-CIRCUIT-2.md`.

## Étape 0 (05/09/2026)

- pwd = `~/Desktop/labuse-audit`, arbre propre, `git fetch` fait ; branche créée depuis `feat/circuit-1` (`13aa2bd7`, mandat commité `480ae1db`).
- `docs/audit-2026-09/EXPORTS/RECONCILIATION-CIRCUIT.md` ABSENT → **le code de main fait foi** (règle du 0-bis).
- Suite de départ (après merge de main, cf. 0-bis) : **2356 passed · 1 failed (`test_r5`, pré-existant admis depuis CIRCUIT-1) · 36 skipped** — référence de non-régression.

## Décisions prises en autonomie

1. **(0-bis, compte des chiffres)** Le mandat dit « Compte réel : 94 dans chiffres.py (pas 98) ». Le recompte EXÉCUTÉ (runtime, `len(CHIFFRES)`, ids uniques) donne **98 avant réconciliation** : le « 94 » vient d'un comptage par motif `"[a-z0-9_]+": C(` qui manque les 4 ids à majuscules `part_zone_U/AU/A/N_pct` (bien déclarés, bien servis). Option la plus sûre : ne PAS supprimer 4 ids vivants pour coller à un compte erroné — le compte-rendu CIRCUIT-1 (« 98 chiffres ») était exact, le bandeau de la page Circuit compte depuis le miroir (aucun nombre en dur, vérifié par grep) : rien à corriger là. Après 0-bis : **104** (scission du neuf +1 net, potentiel_verdict, mixite_clause, 3 saisies projet).
2. **(0-bis, conflit de merge)** Un seul conflit (`api/app.py`, bloc marche_synthese du PDF premium) : résolu en gardant le code de main (EXPORTS-1 1.3 — synthèse sector_price parcelle déjà posée par `_q_v2_fiche`, repli tendance commune), conformément à la règle « code de main pour les moteurs d'EXPORTS-1/ZONE-1 ».
3. **(0-bis, sonde scoring/bilan)** « La sonde vérifie que le scoring lit le premier et le bilan le second » : le scoring (score_e) ne stocke pas le prix neuf brut en base — la vérification est double : (a) donnée : `verifier_scission_neuf` compare la chaîne bilan servie (`resolve_prix_sortie_servi`) au moteur observé (`resolve_prix_neuf_marche`) sur les témoins et refuse tout `niveau_prix='secteur'` dans `score_e` servi (le grain secteur n'existait que dans le précalcul divergent) ; (b) code : test qui verrouille que `score_e.py` lit `neuf_vefa_commune` et `bilan.py` lit `resolve_prix_neuf_marche`. Alternative écartée : reconstruire score_e dans la sonde (des heures, hors passage).
4. **(0-bis, exports nocturnes)** Le cas recette_exports1 est joué quand `declencheur == "cron"` (le job wrapper `coherence-robinets`), en sous-process isolé (WeasyPrint/pdftotext, env `DYLD_FALLBACK_LIBRARY_PATH` posé) ; timeout du job élargi 900 → 3600 s. Au bouton et à la bascule : sauté et DIT (`exports: {saute}` dans le verdict).
5. **(0-bis, saisies projet)** Les trois saisies client du Financier (coût de construction, marge et frais, prix demandé) sont déclarées dès 0-bis (portée `projet`, réservoirs vides, tampon « saisi par le client le … ») et rattachées aux robinets `outil_faisabilite` + `pdf_banquier` — la règle `verifier()` exige qu'un chiffre soit servi. L'affichage ambre (DA v3) reste au lot 1.7.

## Non fait (avec raison)

- (rempli au fil des lots)

---

## 0-bis — Réconciliation avec EXPORTS-1 et ZONE-1

### Merge

`git merge origin/main` (`207f44b2` = merge EXPORTS-1) dans la branche → commit `f32f23ef`. Un conflit (`api/app.py`), résolu côté main (décision n° 2). **Suite verte après merge : 2356 passed · 1 failed pré-existant · 36 skipped** (le rouge `test_r5` est LE pré-existant admis, stash-prouvé en CIRCUIT-1).

### Tableau id → moteur (avant → après)

| id | avant | après |
|---|---|---|
| `tranche_prix_vefa` | moteur `marche_communes` | moteur **`marche_service`** |
| `prix_ancien_median_eur_m2` | moteur `marche_communes` | moteur **`marche_service`** |
| `prix_terrain_zone_eur_m2` | moteur `marche_communes` | moteur **`marche_service`** |
| `prix_neuf_vefa_eur_m2` | moteur `marche_communes` (UNE ligne, deux définitions) | **SCINDÉ** : `prix_neuf_vefa_acte_eur_m2` (marche_service — usage réservé SCORING) + `prix_neuf_observe_eur_m2` (marche_service — usage réservé BILAN/EXPORTS) ; alias de transition `ALIAS_TRANSITION` (un lot, puis retiré) |
| `prix_sortie_bati_eur_m2` | `sector_price` mais fonction FRONT (`marche.tsx`) | `sector_price` **servi au serveur** (`_q_v2_fiche`, EXPORTS-1 1.3) |
| `sdp_residuelle_m2` | `residuel` (residuel.py:80) | **`potentiel`** (bloc au sol, garde zone dominante ZONE-1) |
| `capacite_logements` | `residuel` (modules.py:faisabilite_sens1) | **`potentiel`** (table_rase.logements) |
| `classe_residuel` | `residuel` (residuel.py:80) | **`potentiel`** (au_sol) |
| `potentiel_verdict` | — | **NOUVEAU** — le verdict du bloc reçoit son id (`potentiel`) |
| `zone_plu_famille` | passe_plat (app.py:map_layers_geojson) | moteur **`zone_servie`** (`zone_dominante` — dominante par surface, a_cheval, zone_parts) ; ≠ `zonage_commune` (parts d'une commune, registre/moteurs/zonage.py) |
| `mixite_clause` | — | **NOUVEAU** — `bilan_promoteur` (`_clause_mixite`, EXPORTS-1 5.1) |
| saisies projet ×3 | — | **NOUVEAUX** — `cout_construction_saisi_eur_m2`, `marge_frais_saisie_pct`, `prix_demande_saisi_eur` (portée `projet`) |

Moteurs au registre (`moteurs.csv`) : `marche_communes` renommé **`marche_service`** (libellé « Prix : point d'appel unique (fiche, outils, PDF, Copilote) »), lignes **`potentiel`** et **`zone_servie`** ajoutées (avec la mise en garde zone_servie ≠ zonage_commune).

### Fonctions corrigées (le registre pointait du code mort — attrapé puis verrouillé par test)

- `surface_parcelle_m2` : `modules.py:scoreur_adresse` (disparu) → `api/scoreur.py:scoreur_adresse`
- `n_vigilances` : `modules.py:risques_audit` (disparu) → `api/anti_fiche.py` (motifs de la cascade)
- `n_densifiables` : `modules.py:renouvellement` (disparu) → `api/app.py:renouvellement_liste`
- `assemblage_parcelles_n` / `assemblage_surface_m2` : `moteurs.py:moteurs_assemblage` (disparu) → `moteurs.py:assemblage`
- `ventes_100m_n` : app.py:3283 → `api/site_voisinage.py:voisinage_proche` (100 m · 36 mois, profil `voisinage_100m`)
- `depots_secteur_n` : app.py:3283 → `ingestion/permits.py:depots_recents` (36 mois, profil `fiche_36m`)
- `type_proprietaire` : fichier PM `parcelle_personne_morale` + garde de lecture EXPORTS-1 5.4
- **Verrou** : `test_aucune_fonction_ne_pointe_du_code_mort` — toute `fonction` du registre doit pointer un fichier existant, une fonction présente, une ligne dans le fichier.

### Permis — les libellés disent fenêtre et rayon (arbitrage Q7)

`n_permis_proximite` = « **Permis à 500 m sur 24 mois** » (LE profil client `flash_500m`, paramètres TRANSMIS au moteur — EXPORTS-1 4.1), fonction `marche_service.permits`. `permis_12m_n` → « Permis de la commune sur 12 mois », `permis_5a_n` → « Permis de la commune sur 5 ans », `depots_secteur_n` → « Déposés sur le secteur (36 mois) », `ventes_100m_n` → « Ventes à moins de 100 m (36 mois) ».

### La scission du neuf (arbitrage Q3)

- `prix_neuf_vefa_acte_eur_m2` = VEFA à l'acte (`neuf_vefa_commune`, live) — **le scoring lit CET id** ; affiché comparateur/communes/fiche commune sous libellé VEFA.
- `prix_neuf_observe_eur_m2` = neuf observé ≤ 3 ans (`resolve_prix_neuf_marche`) — **bilan et exports lisent CET id** (fiche constructibilité, Dossier banquier).
- Robinets : plus AUCUN ne sert l'ancien id ; le VEFA à l'acte est SORTI de la fiche parcelle (EXPORTS-1 1.4) ; l'observé entre à `fiche_parcelle_constructibilite` + `pdf_banquier`.
- Fuite `prix_neuf_vefa_eur_m2` de `fuites_mesurees.csv` : **soldée** (colonne `statut` ajoutée, ligne conservée, motif « deux définitions, deux ids »).
- Sonde : `verifier_scission_neuf` (décision n° 3) + tests code-niveau.
- Alias `ALIAS_TRANSITION`/`resoudre()` : transition UN lot, retrait au prochain.

### Structure du registre (point 4)

- `Valeur.couverture` ({n, non_couvert}) : la garde de couverture d'EXPORTS-1 5.5 devient une règle — `probleme_couverture()` refuse tout COMPTEUR (unité « nombre ») sans couverture ; la sonde s'en servira quand les Valeurs couleront (lot 6).
- Portée **`projet`** (3e portée) : pas de réservoir, tampon `saisi_par_le_client_le` — servie par `tampons_pour`, testée.
- Compte des chiffres : voir décision n° 1 — **98 avant 0-bis (le « 94 » du mandat était un artefact de comptage), 104 après** ; le bandeau compte depuis le miroir, rien en dur.

### Sonde (point 5 — le dû du 4.1)

- Les 4 témoins d'EXPORTS-1 (`97415000BO0852`, `97401000AD0554`, `97416000DY0106`, `97411000AV0110`) entrent dans la sonde : `sonde_circuit.TEMOINS_PARCELLES` (test : même jeu que la recette, jamais deux listes).
- **Vrais chemins** : `verifier_chemins_reels` appelle l'endpoint HTTP `/parcels/{idu}` (TestClient in-process) et l'outil Copilote `fiche_parcelle` sur les témoins (surface HTTP=SQL=Copilote, SDP au sol HTTP=moteur potentiel, « Neuf VEFA » absent de la fiche) ; la famille **PDF** est portée par le cas recette (ci-dessous) — « non_couverts » n'est plus le verdict d'aucune des trois familles.
- **`scripts/recette_exports1.py` devient un cas de la sonde** : `verifier_exports` le joue en sous-process (`--json`) au passage NOCTURNE `coherence-robinets` uniquement (24 PDF des 4 témoins par les vraies routes, extraction pdftotext, comparaison à fiche.json) ; divergences → `circuit_ecarts`.
- **Mots interdits** : liste VERSIONNÉE `config/mots_interdits.yaml` (16 mots, celle du 56 → 0 d'EXPORTS-1), lue par la recette, verdict DISTINCT dans la sonde (`n_mots_interdits` séparé des divergences de grandeurs).

### Note pour le lot 1.6

47 chiffres restent en `sql_propre` et 15 en `passe_plat` (recompte post-0-bis, mesuré ; le mandat disait 43/13 sur un état antérieur) : un chemin unique, pas encore un moteur nommé — traité au lot 1.6 de CIRCUIT-2. Répartition post-0-bis : moteur 39 · sql_propre 47 · passe_plat 15 · constante 3.

### Suite

- Tests du lot : `tests/test_circuit2_lot0bis.py` — **19 verts** (fonctions vivantes, moteurs réconciliés, scission complète, portée projet, couverture, sonde témoins/nocturne).
- Suite complète post-0-bis : **2375 passed · 1 failed (`test_r5`, pré-existant admis) · 36 skipped** — aucun rouge nouveau, +19 verts vs post-merge (2356).
