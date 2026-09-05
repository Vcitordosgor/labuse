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

- **(lot 1.5)** Le test de couverture qui rejoue l'endpoint réel `/parcels/{idu}` saute sur la base de TEST (aucune parcelle seedée) — il tourne en entier sur la base réelle et la carte `FICHE_PARCELLE_CLES` est verrouillée à sec (ids existants, internes motivés). Ce qu'il faudrait : une parcelle golden seedée dans labuse_test (petit chantier de fixtures).
- **(lot 1.7)** L'ambre couvre les saisies de la calculette (HypInput — les trois hypothèses du Financier) ; démolition et VRD saisis n'existent pas encore comme champs (déclarés `en_attente`, chantier EXPORTS).

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

---

## Lot 1 — Le registre élargi

### Livré

- **1.1 `registre/donnees.py`** (ex-`chiffres.py`, git mv ; `chiffres.py` = alias de réexportation, AUCUN import ne casse) : dataclass `Donnee` (= `Chiffre`, alias) avec `type` ∈ {nombre, classe, texte, liste, geometrie, couche}, `domaine`/`domaine_source` (classe), `table`/`fabrication` (couche/géométrie/passe-plat), `en_attente` (donnée déclarée pour un chantier nommé, jamais servie tant que posé). Type dérivé de l'unité pour les déclarations historiques (`verdict` → texte : une phrase composée n'a pas de domaine énumérable) ; domaines posés sur les vraies classes : tiers du scoring (statuts.py), familles GPU U/AU/A/N, tranches VEFA (TRANCHE_LIBELLE), statuts PLU (_PLU_STATUT), sous-densité, division, type de propriétaire, niveaux d'aléa DEAL (verrou RETOURS-13 : « élevé/très élevé » ne peut plus s'ingérer en « moyen » sans écart de domaine).
- **1.2 hors_registre VIDÉ** : les 25 entrées de CIRCUIT-1 → 23 déclarées (8 fonds IGN, 12 couches sans chiffre, mairie, réponse web Copilote), **2 reclassées « décor »** (fond Sombre / fond Clair : mode de rendu canvas, aucune source externe). `verifier()` refuse désormais tout hors_registre non préfixé « décor ».
- **1.3 les 16 couches et 10 fonds** : chaque couche a sa donnée type `couche` (table/tuilage + fabrication : `build-mvt` pour le verdict, `vue` pour tcsp/vefa/densifier, `requete` pour les spatial_layers) ; les 8 fonds IGN déclarent le SERVICE et la VERSION de tuiles (`WMTS data.geopf.fr — LAYER=… VERSION=1.0.0, PM`), fabrication `wmts_distant` (sonde de disponibilité, pas de contenu).
- **1.4 tampon non numérique** : `Valeur.etat` (`servie` · `non_determinee` · `non_calculee` — règle 4, un échec ne se déguise jamais en absence) ; `tampons_pour` renvoie type, table, fabrication et domaine avec la trace `?trace=1`.
- **1.5 couverture élargie** : `registre/couverture.py` — CHAQUE clé de premier niveau du payload `/parcels/{idu}` est rattachée à ses données du registre ou classée `interne` avec raison (méta LABUSE, dérivations sans source propre) ; le test rejoue l'endpoint réel et échoue sur toute clé non rattachée. Blocs jusqu'ici sans id DÉCLARÉS : adresse (BAN), géométrie de la parcelle (cadastre), règlement PLU, historique permis, voisinage 100 m, mutations DVF, copropriétés (RNIC), viabilisation, équipements à proximité, événements propriétaire (BODACC), timeline PM, périmètres de dispositifs. Trois robinets de fiche ajoutés : en-tête, règlement d'urbanisme, dispositifs.
- **1.7 portée `projet` en ambre (DA v3)** : `HypInput` (calculette du bilan) — une valeur SAISIE prend bord + texte ambre et `data-saisie-client` ; vide (défaut serveur en placeholder), rendu neutre inchangé. Vitest 2 verts ; tsc OK.
- **1.6 un moteur nommé pour chaque chiffre — `calcul=sql_propre` = 0** (objectif du mandat atteint, sous-chantier mené par agent). **9 moteurs nommés** ajoutés à moteurs.csv : `zonage_commune` (zonage.py enfin nommé — parts + compte de zones), `commune_compteurs` (`registre/moteurs/commune.py`, EXTRACTIONS réelles : composite/indicateurs du comparateur, mutations 12 mois, ppr_pct, vacance, QPV, logés gratuitement, couverture sources, corpus PLU, permis commune, point mort, piscines), `parcelle_proximites` (`plus_proche` extrait d'app.py ; assemblage en délégation — bloc intriqué HTTP/config/privacy), `plateforme_compteurs` (comptes plateforme : parcelles île, bascules 7 j, comptes actifs, conso IA, usage outils, notifications, kanban, dépôts Radar…), `anc`, `bati_revele`, `flux`, `golden_ops`, `copilote_outils` (délégations vers les producteurs nommés — jamais une copie, une seule vérité). Les 3 ids permis/ventes déjà justes → `marche_service` ; n_parcelles_pm → `proprietaire_historique` (délégation patrimoine : un count parallèle = deux assiettes, refusé). Les passe-plats déclarent leur table.colonne ; les 3 saisies calculette = « corps de requête, aucune table » ; les 5 réglementaires `en_attente` restent sans table (pas d'invention). Corrections attrapées au passage : `n_bascules_7j` (la réf. events.py:1086 était périmée — c'est accueil/brief aujourd'hui) et `n_depots_a_verifier` (la file = `pige_faits.valide_at NULL`, pas pige_depots). Tests du sous-chantier : `tests/test_circuit2_lot16.py` 8/8.
- **1.8** : ids des maquettes d'exports déclarés — servis quand le producteur existe (surface vendable/plancher, marge de surélévation, postes du bilan, ventes retenues/écartées, part égout EGOUL, écart au prix demandé) ; `en_attente` sinon (emprise/hauteur/nb bâtiments, sensibilité au coût, démolition) ; réglementaires ER/EBC/DPU/PEB/A-B-C déclarées `en_attente="réservoir CIRCUIT-3 lot 6"` — verrou : une donnée en_attente servie par un robinet fait échouer `verifier()`.

### Compte-rendu du lot (chiffres demandés par le mandat)

- **164 données** (mesuré) — par type : nombre 107 · couche 24 · classe 13 · texte 10 · liste 9 · geometrie 1 ; par calcul : **moteur 113 · passe_plat 48 · constante 3 · sql_propre 0**.
- Robinets **123/123 déclarés** — 121 avec données, 2 « décor » (fonds Sombre/Clair). **Exceptions = 0.**
- Données `en_attente` (jamais servies, verrouillé par test) : **10** (5 réglementaires CIRCUIT-3 + emprise/hauteur/nb bâtiments, sensibilité coût, démolition — chantier EXPORTS).

### Attrapé en cours de lot

- Deux pytest lancés en parallèle sur labuse_test (le mien + la suite de fond) → 7 erreurs de fixtures fantômes ; tués, relancé SEUL → tout vert. La leçon CIRCUIT-1 (« jamais deux pytest en parallèle ») reste la règle de la session.

### Suite

- Tests du lot : `test_circuit2_lot1.py` 13 verts (+1 skip base de test sans parcelle, dit) · `test_circuit2_lot16.py` 8 verts · `test_registre.py` 9 verts adaptés · vitest HypInput 2 verts · tsc OK.
- Suite complète post-lot 1 : **2398 passed · 1 failed (`test_r5`, pré-existant admis) · 37 skipped** — aucun rouge nouveau, +23 verts vs 0-bis.

---

## Lot 2 — La fiche, donnée par donnée

### Livré

- **`labuse registre fiche parcelle` / `autres`** (`registre/fiche_doc.py` + sous-commande CLI) : les documents sont GÉNÉRÉS du registre — jamais saisis deux fois. Chaque ligne : id, type (et domaine d'une classe), libellé, source(s) avec le MILLÉSIME réellement servi (lu de data_sources à la génération), chemin (moteur nommé ou passe-plat + table lue), portée, états possibles, et « où ailleurs » (dérivé des robinets — couches, outils, PDF, Copilote, mails).
- **`docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md`** — 13 tiroirs de la fiche parcelle, 41 données, générés sur la base locale (millésimes réels : CoSIA 2025, Sitadel 2026-07, Filosofi 2021…), RELU : lisible sans le code, une ligne par donnée en français.
- **`docs/CIRCUIT/FICHES-DONNEES.md`** — fiche commune (16 tiroirs), fiche annonce, fiche propriétaire, fiche soleil (34 données), même format, plus court.
- **Verrou** `tests/test_circuit2_lot2.py` (3 verts) : chaque donnée de chaque tiroir est dans le document ; les fichiers COMMITÉS contiennent chaque id du registre — un registre qui bouge sans régénération = rouge (jamais d'édition à la main).

### Suite

- Tests du lot 3/3 ; documents générés puis relus. (Suite complète au prochain passage de lot — aucun code de service touché par ce lot : générateur + CLI seuls.)

---

## Lot 3 — Un concept, une source

### Livré

- **3.0** : `zone_servie` et `potentiel` étaient au registre depuis le 0-bis (testé) — confirmé en tête de `CONCEPTS-CANONIQUES.md` ; `zone_servie` ≠ `zonage_commune`, les deux nommés.
- **3.1/3.2 `docs/CIRCUIT/CONCEPTS-CANONIQUES.md`** : les 19 concepts du mandat, une ligne chacun — ce qui existe au registre, la source canonique (règle de défaut : celle que la fiche sert par le moteur), et le devenir des autres (`derivee` : TVA primo buffer des QPV ; `nommee_a_part` : GPU brut, OCS grain grossier, Papang OSM, BPE vs OSM, aléa vs PPR ; **`retiree` : aucune** — rien n'est supprimé sans Vic).
- **Le doublon d'affirmation trouvé et corrigé** : le « i » de la couche « Équipements (OSM) » prétendait encore alimenter les distances de la fiche — c'est la BPE depuis RETOURS-7 Z5 (le payload le dit). Les deux « i » (OSM et BPE) disent désormais qui nourrit quoi : BPE → ligne « À proximité » de la fiche, OSM → amenités du modèle. Rien de supprimé, deux libellés clarifiés.
- **3.3 doublons de définition, MESURÉS sur les 4 témoins** : prix secteur (3 811/2 308/3 103/3 118 €/m²) ≠ ancien commune (4 278/3 041/3 015/2 469) ≠ VEFA acte (4 742/—/4 916/4 998) — trois définitions réelles, 0 fusion ; le seul vrai doublon (le neuf) était déjà soldé par scission au 0-bis. Verrou : `test_jamais_le_meme_libelle_pour_deux_origines` (0 libellé partagé sur 164 données).

### Suite

- Tests du lot 3/3 ; tsc OK. (Le seul code touché : deux textes « i » de layers.ts.)
