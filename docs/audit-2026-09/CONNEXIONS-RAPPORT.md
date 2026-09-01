# CONNEXIONS-1 — Rapport d'audit des connexions et interconnexions

**Nature : audit EN LECTURE SEULE.** Aucune modification de code. Branche `audit/connexions-1` (depuis `main`).
**Run servi vérifié : `q_v11_m137`** (`config/served_run.txt`, lu par `Q_A_RUN_LABEL` — `src/labuse/scoring/score_v_constants.py:53-70`).
**Méthode** : chaque connexion tracée bout en bout front → `frontend/src/lib/api.ts` → endpoint → module → table, en lisant le code. `OK` = branché et juste · `KO` = branché mais faux/cassé/dupliqué · `ABSENT` = rien n'existe · `DOUTE` = indéterminable sans exécution. Tout calcul métier trouvé au front = KO même juste. Deux chemins pour une même donnée = signalé même si les deux marchent.

---

## Synthèse — nombre de lignes par état

Sur **~213 connexions examinées** (A→P) :

| état | nombre | lecture |
|---|---|---|
| **OK** | ~160 | branché bout en bout, juste, source unique |
| **KO** | **17** | branché mais faux / cassé / dupliqué / promesse non tenue |
| **ABSENT** | 14 | fonction non livrée (dont 10 côté dashboard/admin/comptes) |
| **DOUTE** | 22 | à trancher par exécution ou décision produit |

**Le socle métier est sain** : `sector_price`, tiers, SDP/résiduel, prix neuf/ancien = **source unique, run épinglé, zéro recalcul au front** (vérifié exhaustivement sur les 15 outils, section L). Les KO ne sont **jamais** dans le moteur de score/prix — ils sont concentrés sur (1) la **cascade servie aux exports** (run périmé), (2) la **boucle CRM↔Courrier** (jamais refermée), (3) les **remontées vers le dashboard** (plusieurs promesses UI non tenues), et (4) quelques **gestes de fiche** cassés.

---

## LES KO CLASSÉS PAR IMPACT (du plus grave au plus bénin)

### 🔴 Gravité haute — l'utilisateur voit un chiffre faux ou contradictoire

**KO-1 · Exports « experts » servis sur un run PÉRIMÉ (`q_v8_calibre`)** — *le plus matériel.*
`src/labuse/api/served_cascade.py:20` fige `_DEFAULT_RUN = "q_v8_calibre"` (le run servi est `q_v11_m137`). Les 3 seuls appelants `src/labuse/flash/data.py:150,367,410` appellent `served_cascade_lines(db, idu)` **sans passer de run** → repli sur le vieux run. `collect_report_data` alimente **le Dossier** (`flash/report.py:77`), **la Lettre de zonage** (`api/lettre_zonage.py:366`), **le Pré-dossier PC** (`api/pre_dossier.py:177,530`), les briques (`api/briques_pdf.py:241`) et le banquier. Le commentaire (served_cascade.py:1,19) prétend « le dryrun servi fait foi / aligné sur `Q_A_RUN_LABEL` » — **faux**.
*Impact* : les lignes **risques / zonage / règles / ABF** de documents que le client remet à un banquier ou un notaire sortent d'une cascade **3 runs en arrière**, en contradiction silencieuse avec l'écran (q_v11_m137). Correctif trivial (`run = run or Q_A_RUN_LABEL`) mais à faire dans CONNEXIONS-2. *Le PDF fiche principal `/export.pdf` n'est PAS touché* (il passe par `_q_v2_fiche`).

**KO-2 · Deuxième source de vérité cascade : table LIVE `cascade_results` encore lue.**
`src/labuse/api/served_cascade.py:6` affirme « aucun générateur ne lit plus `cascade_results` (rail legacy, mort) ». **Faux** : la table LIVE non-run-scopée (`models.py:151`, DELETE+INSERT par parcelle, `cascade/pipeline.py:173`) est lue par deux endpoints vivants — `src/labuse/api/anti_fiche.py:52` (`/anti-fiche/{idu}`, la fiche « pourquoi pas ») et `src/labuse/api/app.py:4428` (déclassement). La fiche principale, elle, lit `dryrun_cascade_results` (run épinglé + arbitré).
*Impact* : la fiche « pourquoi cette parcelle n'est pas retenue » peut **contredire** la fiche, car elle sert le dernier calcul par parcelle, pas le run servi arbitré.

**KO-3 · Quota Copilote édité au dashboard, IGNORÉ par le Copilote réellement servi.**
Le dashboard écrit `comptes.copilote_quota_jour` (`api/dashboard.py:551-565`) et l'UI promet « le `/ask` le lit » (`admin/Ia.tsx:110`). Or seul l'ancien chemin NL `/ia` lit cet override (`api/ia.py:340-341`). Le Copilote conversationnel v2 `/ask` plafonne sur `s.copilote_v2_missions_jour` (**config globale**, `api/copilote_v2.py:76`).
*Impact* : l'admin croit relever la limite d'un client, il ne relève rien sur le Copilote v2. Deux plafonds distincts pour deux chemins.

### 🟠 Gravité moyenne — geste cassé, promesse produit non tenue, sur-alerte silencieuse

**KO-4 · « Signaler une erreur » depuis la fiche N'ARRIVE PAS au dashboard admin.**
`postSignalement` (`api.ts:866`) → `/signalements` → table `signalements`, **revue CLI-only**. Le compteur admin `signalements_en_attente` écoute l'AUTRE « signaler » (annonce Radar, `event_log kind='pige.signalement_client'`). Deux homonymes, tables disjointes.
*Impact* : exactement le trou N3 du mandat — un client signale une donnée fausse, **personne ne le voit** à l'écran (file QA privée, CLI seulement).

**KO-5 · Tuile « Courrier » de la fiche s'ouvre VIDE.**
La tuile et la porte propriétaire font `setModule('courriers')` **sans poser de prefill** (`Fiche.tsx:2514,2658`) ; le module ne s'amorce que via `courrierPrefill`/`courrierPrefillIdus` (`ModulePanel.tsx:852-861`), et `setCourrierPrefill(` n'est **appelé nulle part** (0 émetteur mono-parcelle). Seuls Assemblage/Pièges posent `courrierPrefillIdus`.
*Impact* : le libellé promet « cette parcelle pré-remplie », le Courrier s'ouvre vide.

**KO-6 · Boucle CRM ↔ Courrier jamais refermée (I4/J3/J4).**
`courrier_demandes` n'a **aucun** `projet_id` ni FK `pipeline_entries` (`courrier.py:52-62`). Conséquences : (a) demander un courrier depuis une piste **re-saisit** les IDU (`ModulePanel.tsx:912`) ; (b) le statut courrier (`demande→imprime→poste`, `courrier.py:86`) ne remonte **jamais** dans la carte CRM ni dans une colonne Kanban ; (c) trois vocabularies disjoints (colonnes Kanban `reperee…abandonnee` vs statuts courrier vs buckets dashboard `Courrier.tsx:22-24`) ; (d) **« Répondu » n'existe nulle part** — le cycle s'arrête à `envoye`. Le statut n'est visible que par la **cloche**, jamais dans « Mes courriers » (`ProjetsPanel.tsx:235-244`).
*Impact* : la boucle « retenue → piste → courrier → réponse → statut » ne se ferme pas end-to-end ; décision produit assumée côté Vic, mais I4 littéral non tenu.

**KO-7 · « Créer une veille sur cette recherche » : sur-alerte silencieuse (lossy).**
Le bouton persiste et se déclenche réellement (≠ veille fantôme) : `FiltreLabuse.tsx:578` → `saveSearch(filtersToHash)` → `saved_searches` → `_veilles_match`. Mais `filtersToHash` sérialise ~35 dimensions (`filters.ts:206-217`) et `_veilles_match` n'en évalue que 5 (tier, commune, événement, surface, SDP — `events.py:587-598`) ; zonage, état-sol, signaux (`fl` parsé mais **jamais utilisé**), propriétaire, marché, charge sont **ignorés**.
*Impact* : une veille « friches zone U St-Pierre » alerte sur **toute** parcelle St-Pierre du bon tier+surface. Bruit silencieux.

**KO-8 · « Ajouter au CRM » depuis la fiche ne choisit pas de piste.**
`addToPipeline(idu)` n'envoie que `{idu}` (`api.ts:860-863`) → `/pipeline` pose toujours la 1ʳᵉ colonne (`default_status`, `app.py:5657`).
*Impact* : atterrit toujours dans la colonne par défaut (déplaçable ensuite) ; le mandat demande « la piste choisie » — non tenu depuis la fiche. (Gravité faible.)

**KO-9 · Passerelle fiche commune « Annonces-Radar » ouvre le Radar NON filtré.**
`ContextePanel.tsx:98` fait `setCommunesFilter([commune]) + openRadar()`, mais `RadarView.tsx:342` initialise son filtre `f` à `{}` et **ne lit jamais** `communesFilter` (vérifié directement). Les autres passerelles (PLU, Permis, Densifier…) pré-remplissent, elle non.
*Impact* : « Voir les annonces dans le Radar » ouvre le Radar de toute l'île, pas de la commune.

**KO-10 · « Scan patrimoine — actionnables hors écartées » : faux ami.**
`/modules/patrimoine` (`modules.py:255`) ne joint NI `projet_parcelles` NI `pipeline_entries` : « hors écartées » = exclusions **cascade** (`etage0`), pas le geste utilisateur « écarter » d'un projet.
*Impact* : le libellé laisse croire à une reprise des décisions Projet ; ce n'en est pas une. Aucune fuite, vocabulaire trompeur.

### 🟡 Gravité basse — infrastructure, doctrine, dette connue

**KO-11 · « Toutes les données sont à jour » = texte figé.**
`LeftPanel.tsx:466` est une chaîne littérale, aucun fetch. Le seul endpoint qui mesure la fraîcheur réelle (`/accueil/cette-semaine`, `accueil.py:111-154`) n'est plus consommé.
*Impact* : affirmation de fraîcheur non adossée à l'état réel des sources — peut mentir.

**KO-12 · Transport mail non unique (doctrine « transport UNIQUE » fausse).**
`mail.py:1-4` se dit transport unique, mais deux coexistent : SMTP (`mail.py` : reset, courrier, digest events) **et** API Brevo (`brevo.py` : essai/onboarding/suspension + **digests Radar** `pige/digests.py:248`).
*Impact* : deux canaux/configs à maintenir ; la promesse doctrinale est fausse.

**KO-13 · Rattachement adresse→IDU dupliqué.**
Deux implémentations BAN + `ST_Contains` : `audit.py:162` (`audit_by_address`, `BAN_URL:26`) et `scoreur.py:47,125` (`_geocode`, `BAN_URL:28`), plus une 3ᵉ voie autocomplete (`copilote_v2/outils.py`, table `ban_adresses`). Le docstring `scoreur.py:8` prétend « réutilise audit » mais réimplémente.
*Impact* : deux clients HTTP + deux SQL pour la même question ; marchent tous deux aujourd'hui, à unifier (A1 : une seule vérité).

**KO-14 · Un échec d'ingestion ne devient pas un état « en erreur » sur la page Sources.**
Le job ne connaît que `a_jour/en_retard/en_panne/sans_echeance` (`jobs_impl.py:88,98`) et `/sources` ne compte que les runs `status IN ('ok','success')` (`app.py:928`). Un run **échoué** n'est surfacé que dans le panel CRON admin, pas sur la vitrine Sources.
*Impact* : l'ancienneté est visible, l'échec non — une source « plantée mais récente » paraît saine.

### KO front (calcul métier — borderline)

**KO-15 · Ratio de gain d'assemblage re-divisé au front.**
`assemblage.py:216` sert `round(sdp/sdp_max_seule, 1)` (« ×1,0 » trompeur) ; `moteurs.tsx:152-155` **re-divise** `sdp_combinee_m2 / sdp_max_seule_m2` à 2 décimales.
*Impact* : deux expressions du même ratio ; le back devrait servir le ratio non arrondi. Dette de précision, pas de faux chiffre matériel.

*(KO-16 et KO-17 = les deux facettes de KO-6 comptées séparément dans les tables I4-CRM et J4 : absence de FK courrier↔pipeline, et « répondu » inexistant.)*

### ABSENT structurants (fonctions non livrées) — repris intégralement en section « Ce que le dashboard écoute »
Agent de détection de nouvelle version amont (M2) · action « désactiver une source » au dashboard (M2/N2) · « ajouter des crédits IA » (N2) · toggle « ouvrir/fermer dépôt agence » au dashboard (N2, aujourd'hui flag env `config.py:70`) · action « révoquer une session » (N2, par doctrine SESSION-1) · **monitoring des endpoints métier** (N3, le cas `/accueil/chiffres`) · compteur « N courriers à déposer » (N1) · multi-licences / sièges / structure (O2, produit mono-siège) · recherche omnibox par propriétaire / SIREN / annonce / projet (C1, vivent dans leurs surfaces dédiées).

---

## A — Un seul moteur, une seule vérité

### A1 · Inventaire des moteurs
| connexion | état | preuve | impact |
|---|---|---|---|
| `sector_price` (valorisation €/m²) | OK | `faisabilite/bilan.py:204` — 1 def, ~12 callers backend, 0 front | source unique |
| `prix_ancien_communes` (baromètre) | OK | `api/moteurs.py:396`, distinct documenté `bilan.py:399` | pas un doublon de sector_price |
| `prix_sortie_neuf` | OK | `bilan.py:289` `resolve_prix_sortie_servi`, 6 consommateurs | point unique |
| scoring/tiers → `parcel_p_score_v2.tier` | OK | `scoring/p_v2/statuts.py:73`, écrit `pipeline.py:447`, traduit `verdict_servi.py:169` | 1 producteur, 1 table, 1 traduction |
| capacité résiduelle / SDP | OK | `faisabilite/residuel.py:80`→`parcel_residuel` ; `bilan.py:393` `compute_bilan` (1 def) | moteur unique |
| **rattachement adresse→IDU** | **KO** | 2 impl. BAN+ST_Contains : `audit.py:162` et `scoreur.py:47,125` (2 `BAN_URL`) ; 3ᵉ voie `copilote_v2/outils.py` | **KO-13** — même question, 2 chemins |
| valorisation foncier nu | OK | `score_v_constants.py:150` + filtre `app.py:1380` lisent `parcel_residuel.taux_emprise_pct` | pas de 2ᵉ formule |

### A2 · Aucune réimplémentation partielle (front / back)
| connexion | état | preuve | impact |
|---|---|---|---|
| calcul prix/valorisation en front | OK (aucun) | `moteurs.tsx:154` ratio affiché, `EtudierBien.tsx:96` prix SAISI, tri `ResultsSection.tsx:178` | rien de métier |
| SDP/résiduel en front | OK (aucun) | grep arithmétique SDP front = vide | — |
| tier re-dérivé front | OK (aucun) | `lib/status.ts` mapping pur ; `MapView Math.log10` = taille marqueur | — |
| signal permis : filtre vs Score-V | OK | filtre `app.py:1373` lit `parcel_signaux_vie` ; Score-V ne score pas le permis | 1 déf |
| signal succession : filtre vs Score-V | OK | `score_v.py:586` ÉCRIT `parcel_veille_succession` ; filtre `app.py:1401` le LIT | source unique |

### A3 · Tiers identiques partout
| écran | état | preuve |
|---|---|---|
| Projets | OK | `projets.py:288,318` `s2.tier`, run `_score_v2_run_id` |
| Scan patrimoine + Densifier | OK | `app.py:4549` `s2.tier`, run `Q_A_RUN_LABEL` `app.py:4556` |
| Radar | OK | `pige/api.py` ne surface pas de tier → ne peut diverger |
| Fiche parcelle | OK | `app.py:3199` `verdict_servi()` + premium `app.py:2286` |
| Exports | OK | `export.py:150,272` via `TIER_LABELS`, hérite du run fiche |
| Carte/tuiles | OK | `tiles.py:163` `s2.tier`, run `Q_A_RUN_LABEL` |

Tous lisent `parcel_p_score_v2.tier` du run `q_v11_m137`. **Aucun KO.**

### A4 · Dates de valeur
| surface | état | preuve |
|---|---|---|
| Projets Kanban/panel | OK | `ProjetKanban.tsx:328` `etat.valeurs_run`, `ProjetsPanel.tsx:52` (servis backend) |
| Fiche / sources / couches | OK | `millesime`, `source_millesime` servis |
| Copilote / accueil | OK | `accueil.py:102` `run_label` dynamique |
| Calendrier DPE DOM | OK | `score_v_constants.py:117` source unique, labels dérivés |

Aucune date métier codée au front.

### A5 · Run courant
| connexion | état | preuve | impact |
|---|---|---|---|
| point de vérité run servi | OK | `config/served_run.txt=q_v11_m137`, `score_v_constants.py:53-70` | source unique versionnée |
| tuiles carte | OK | `tiles.py:24` `Q_A_RUN_LABEL as RUN` | aligné |
| verdict_servi | OK | `verdict_servi.py:169` défaut `Q_A_RUN_LABEL` | aligné |
| **`served_cascade.py` (fiche flash + exports)** | **KO** | `served_cascade.py:20 _DEFAULT_RUN="q_v8_calibre"` ; appelants `flash/data.py:150,367,410` sans run | **KO-1** — cascade servie sur run périmé |
| `bascule_gardes.py:31 TARGET="q_v8_calibre"` | DOUTE | outil de bascule, pas un chemin servi | probablement inerte, à confirmer |
| `scoring/lignee_tete.py:25` défaut `"q_v8_calibre"` | DOUTE | `build_parcel_entree_tete` (badges M28, gatés OFF) | inerte tant que M28 OFF |

### A6 · Caches et invalidation
| cache | état | preuve | impact |
|---|---|---|---|
| tuiles `_CACHE` LRU | OK | `tiles.py:357` clé = `_mvt_version` = `mvt_meta.updated_at`, TTL 10s cross-process | seul cache **auto-invalidé sur rebuild** |
| accueil `_cache` chiffres | DOUTE | `accueil.py:31` TTL 3600s, clé temps seul | jusqu'à 1h de retard après bascule (borné) |
| accueil `_cs_cache` | DOUTE | `accueil.py:108` TTL 300s | idem borné |
| projets `_COMPTEUR_CACHE` | OK | `projets.py:504` clé inclut `RUN`, TTL 600s ; purge au restart | invalidé au redémarrage |
| banquier `_PDF_CACHE` | OK | `banquier.py:242` clé `(idu,_RUN)` import-time | effectif au redémarrage |
| protection `_gels_cache` | DOUTE | `protection.py:141` TTL 30s | faible portée |

### A7 · Tables gelées / *_old / *_v1 encore lues
| table | état | preuve | impact |
|---|---|---|---|
| **`cascade_results` (LIVE, non run-scoped)** | **KO** | `models.py:151` sans `run_label` ; lue par `anti_fiche.py:52` et `app.py:4428` | **KO-2** — 2ᵉ source cascade |
| `cascade_results` via Copilote v1 | DOUTE | `copilote/moteurs.py:124-131,343`, router monté `app.py:5799` | 3ᵉ lecteur si v1 encore joignable |
| `dvf_mutations_histo` | OK | `dvf_histo.py`, `defisc_fenetres.py` | archive légitime 2014-2020 |
| `parcel_veille_succession`, `parcel_signaux_vie`, `pc_caducs` | DOUTE | non run-scopées (`models.py:281`), réécrites par leur passe | reflètent le dernier passage, pas forcément le run scoring servi (alignées en pratique) |

---

## B — Accueil et rail

| connexion | état | preuve | impact |
|---|---|---|---|
| B1 · Carte « Explorer » → carte + Filtres | OK | `LeftPanel.tsx:448` `onCommencer`→`setAccueilVu();openFiltres()` | — |
| B1 · Radar → vue Radar | OK | `LeftPanel.tsx:451` `setView('radar')`, `App.tsx:398` | — |
| B1 · Copilote → vue Copilote | OK | `LeftPanel.tsx:453`, `App.tsx:412` | — |
| B1 · Outil → tiroir Outils | OK | `LeftPanel.tsx:456` `toggleOutils()` (`useApp.ts:585`) | — |
| B2 · Compteur outils = registre (15) | OK | `LeftPanel.tsx:456` / `Rail.tsx:219` `MODULES.filter(!hidden).length` = 20−5 = **15** | dynamique, cohérent tiroir/accueil |
| **B3 · « Toutes les données sont à jour »** | **KO** | `LeftPanel.tsx:466` chaîne littérale ; `/accueil/cette-semaine` (`accueil.py:111`) non consommé | **KO-11** — fraîcheur non adossée au réel |
| B4 · « voir les données → » → Sources | OK | `LeftPanel.tsx:467` `setView('sources')` | — |
| B5 · Rail → surfaces | OK | `Rail.tsx:177-201` chaque `key`→`setView`/`toggle`/`openSources` | navigation complète |
| B5 · Admin réservé rôle admin | OK | `Rail.tsx:121-126` `if(!admin)return null` + garde serveur `exiger_admin` (`dashboard.py:126`) | UI = confort, sécurité backend (403) |
| B5 · État actif suit la route | OK | `Rail.tsx:178` classe `.active` **dérivée** de `view===key` | surbrillance = état réel |

---

## C — Recherche globale (omnibox)

| connexion | état | preuve | impact |
|---|---|---|---|
| C1 · IDU → fiche | OK | `Header.tsx:83-90` match local puis repli `searchParcels`→`/parcels/search` | atteint la fiche |
| C1 · adresse → parcelle | OK | `Header.tsx:64-69` suggestion `idu`→`select`, repli `parcelAt` | fiche directe |
| C1 · commune → périmètre | OK | `Header.tsx:77-81` `setCommune;setView('cartes')` | zoome commune |
| C1 · nom de propriétaire | ABSENT | jamais testé dans `onEnterRaw` ; `/proprietaires/autocomplete` existe mais non câblé | tombe sur toast « rien trouvé » (vit dans Scan patrimoine) |
| C1 · SIREN | ABSENT | aucun branchement ; part en `searchParcels`→0 résultat | non résolu depuis l'omnibox |
| C1 · annonce Radar | ABSENT | aucun handler | pas de recherche annonce par la barre |
| C1 · projet | ABSENT | aucun handler | pas de recherche projet par la barre |
| C2 · adresse→IDU via moteur partagé (pas de géocodage nav parallèle) | OK | `banAutocomplete`→`/adresses/autocomplete` = **table interne `adresses`**, `idu` porté (`app.py:2243`) ; aucun appel BAN externe navigateur | rattachement interne cohérent ; ⚠ docstring `AddressAutocomplete.tsx:8` périmé (dit « api-adresse.data.gouv.fr ») |
| C3 · adresse ambiguë propose des choix | DOUTE | autocomplétion liste 6 choix (OK) ; MAIS Entrée sans surlignage → `pick(items[0])` (`AddressAutocomplete.tsx:132`) et `onEnterRaw`→`feats[0]` (`Header.tsx:92`) prennent le 1er en silence | sur Entrée/loupe, 1ʳᵉ adresse prise sans désambiguïsation |

Placeholder honnête (`Header.tsx:130`) : ne promet pas propriétaire/SIREN/Radar/projet. 3/7 types branchés, 4/7 absents **par conception**.

---

## D — Carte

| connexion | état | preuve | impact |
|---|---|---|---|
| D1 · couche → source + millésime | OK | `/map/layers.geojson` `app.py:4268-4320` renvoie `source_millesime` + `millesime_integration` ; libellés `layers.ts:6,60` ; parcelles = MVT run-épinglé `tiles.py:24,149` | chaque couche datée à sa source |
| D2 · filtres = mêmes données que couches | OK | `/filtre` `app.py:2428` `_q_v2_where` ; `_q_v2_list` `app.py:2762` joint EXACTEMENT les tables que `build_mvt_table` bake (`tiles.py:169`) ; compteur==liste | source unique couches↔filtres, run épinglé |
| **D3 · « créer une veille sur cette recherche »** | **KO** | `FiltreLabuse.tsx:578`→`saveSearch(filtersToHash)`→`saved_searches`→`_veilles_match` ; mais 35 dims sérialisées (`filters.ts:206`) vs 5 évaluées (`events.py:587`), `fl` signaux parsé jamais utilisé | **KO-7** — persiste et déclenche mais sur-alerte (dimensions ignorées) |
| D4 · clic → bon IDU ; chip + sélecteur = même fiche commune | OK | clic `MapView.tsx:1078`, repli `parcelAt` `:1114` ; chip `Fiche.tsx:2289` + header + Communes + Vefa → un seul `/communes/{c}/contexte` | IDU correct, source commune unique |
| D5 · fond/cadastre/zoom source unique | OK (1 doute) | `BASEMAP_SOURCES` unique IGN WMTS (`basemaps.ts:10`) partagé MapView+TimeMachine ; export plan situation même layer (`flash/carte.py:67`) | pas de divergence de tuile — **DOUTE** : `ingestion/ortho_tiles.py:28 MILLESIME="2025"` en dur (parallèle à `data_sources`) |

---

## E — Fiche parcelle

| connexion | état | preuve | impact |
|---|---|---|---|
| E1 · chaque section : source + moteur + date | OK | builder unique `_q_v2_fiche` (`app.py:3161`) scopé `run_label` ; lignes cascade portent `source`+`source_table`+`millesime_amont` (`app.py:3223`) ; verdict `verdict_servi` (`app.py:3199`) | écran = 1 requête, 1 run, chaque ligne datée |
| E2 · « + Projet » → projet CHOISI | OK | `ProjetButton` menu, `ajouterParcelle(pid,idu)` (`Fiche.tsx:543`, « rien mémorisé »), scopé compte `app.py:5667` | rattachement au projet choisi |
| **E2 · « CRM » → piste choisie** | **KO (faible)** | `addToPipeline(idu)` envoie `{idu}` seul (`api.ts:860`)→`default_status` (`app.py:5657`) | **KO-8** — toujours colonne par défaut |
| E2 · cloche → veille parcelle | OK | `toggleWatch(idu)` (`Fiche.tsx:468`)→`watched_parcels`→`/suivis` | suivi privé OK |
| **E2 · « Signaler » → dashboard admin** | **KO** | `postSignalement`→`/signalements` (revue CLI-only) ; compteur admin écoute l'AUTRE signaler (Radar `event_log`) | **KO-4** — n'arrive pas au dashboard |
| E3 · adresse exacte abonnés-seuls (exports/mails inclus) | KO/DOUTE | `_q_v2_fiche` sert `adresse` sans garde de plan (`app.py:3398`), `/parcels/{idu}` idem (`app.py:3972`), PDF idem ; gating = **stub `plans.py` Phase 0** ; l'« abonnés-seuls » réel ne vise que la pige/Radar (`pige/depot_agence.py`) | adresse cadastrale BAN non différenciée par abonnement (wave-adresses non implémenté) — **dette connue** |
| E4 · PDF fiche = même fiche/run que l'écran | OK | `parcel_export_pdf` build depuis `_q_v2_fiche` défaut q_v11_m137 (`app.py:4161`) | PDF principal = mêmes chiffres/date |
| **E4 · Dossier/Finance/Argumentaire/Lettre zonage/Pré-dossier PC** | **KO** | (a) run périmé via `served_cascade` (KO-1) : `flash/data.py:150,367,410` → Dossier (`flash/report.py:77`), Lettre (`lettre_zonage.py:366`), Pré-dossier (`pre_dossier.py:177,530`), briques (`briques_pdf.py:241`) ; (b) 2ᵉ builder : Finance/Argumentaire via `bq.collect` (`banquier.py:216`, `argumentaire.py:77`) cache séparé `_PDF_CACHE`, pas `_q_v2_fiche` | **KO-1** — risques/zonage du vieux run, contradiction silencieuse écran vs export |
| **E4 · « Courrier » ouvre pré-rempli** | **KO** | tuile+porte font `setModule('courriers')` sans prefill (`Fiche.tsx:2514,2658`) ; `setCourrierPrefill(` appelé nulle part | **KO-5** — Courrier s'ouvre vide |
| E4 · Cadastre / Maps au bon point | OK | `f.coords` centroïde `_q_v2_fiche` ; Cadastre `z=19` (`Fiche.tsx:2646`), Maps (`:2654`) | bon point |
| E5 · passerelles pré-remplies IDU courant | OK | `setParcelPrefill(idu)` Faisa/Programme/Assemblage/Temps (`Fiche.tsx:2160,2170,2328`), `setPluPrefillF` (`:2118`), `setM02Prefill(siren)` (`:2506`) | toutes câblées IDU/SIREN |
| E6 · « Autour de cette parcelle » = moteur Étude de zone | OK | `/parcels/{idu}/zone` (`app.py:3987`) et outil (`app.py:4062`) appellent tous deux le module `..zone` (isochrone/population/équipements) | même moteur, sous-ensemble volontaire |

---

## F — Fiche commune

Endpoint `/communes/{commune}/contexte` (`app.py:2024`) sert un cache nocturne `commune_contexte_cache`, sinon calcul direct via `_compute_commune_contexte` + `fiche_commune.build`. **Aucun chiffre en dur ; chaque bloc porte sa source ; introuvable = null.**

| connexion | état | preuve | impact |
|---|---|---|---|
| F1 · Terrain nu (zone U/AU) | OK | `_foncier_commune` `app.py:1944`→`ligne2_terrain_zone` (M79), seuil n=10 | DVF par zone PLU, motif servi |
| F1 · Marché (ancien/neuf/tendance/mutations) | OK | `comparable` `fiche_commune.py:17` lit `comparateur.raw_rows` ; `mutations_12m` `app.py:1940` | même moteur/run que le comparateur |
| F1 · Annonces-Radar (biens/écart) | OK | `marche_annonces` `fiche_commune.py:40` lit `pige.marche.stats()` ; écart demandé/acté backend | seuil n=5 honnête |
| F1 · Loyers | OK | `loyer` `fiche_commune.py:196` `loyer_median` (DHUP) | sourcé, None si non calculable |
| F1 · Foncier repéré / Densifiables | OK | `stock_opportunites` `app.py:1949` `parcel_p_score_v2 run_id=Q_A_RUN_LABEL` ; `densifiables` `fiche_commune.py:184` | run servi, même déf que comparateur |
| F1 · Zonage (parts surface) | OK | `app.py:1920` agrégat surface `parcel_zone_plu` (PK idu), somme 100 % | base surface documentée |
| F1 · Risques | OK | `risques` `fiche_commune.py:67` `spatial_layers`+`catnat_arretes` | mêmes couches que Pièges |
| F1 · Population & logement | OK | `population` `fiche_commune.py:98` Filosofi + `commune_insee_logement` | « niveau de vie MOYEN » nommé |
| F1 · Quartiers prioritaires | OK | `app.py:2102` `anru_quartiers`+`spatial_layers kind=qpv` | source ANCT |
| F1 · Rareté ZAN | OK | `_zan_horizon_ans` `app.py:2048` (`commune_conso_enaf`), même formule que `rarete.py` | signal < 5 ans nommé |
| F1 · Rythme d'instruction / Permis | OK | `permis_bloc` `fiche_commune.py:162` SITADEL + délai + `pc_caducs` | point mort « Estimé » |
| F1 · SRU / PLH | OK | `app.py:2100,2111` `commune_contexte_sru`+`plh_epci` | source DHUP/EPCI |
| F2 · carte PLU → PLU commune | OK | `ContextePanel.tsx:97` `setPluPrefill({insee})`→`PluAnnuaire.tsx:31` | pré-rempli |
| F2 · carte Permis → Permis commune | OK | M03 lit `commune` du store, posé `setCommune` (`ContextePanel.tsx:95`) | filtré commune |
| F2 · Densifier/Étude-zone/Solaire/Scan/Comparer | OK | cibles résolvent (`ModulePanel.tsx:1201`), commune posée | ouvre avec commune |
| **F2 · Annonces-Radar → Radar filtré commune** | **KO** | `ContextePanel.tsx:98` `setCommunesFilter+openRadar` MAIS `RadarView.tsx:342` `f={}` ne lit jamais `communesFilter` (vérifié) | **KO-9** — Radar ouvert non filtré |
| F3 · chiffres identiques à outil Communes | OK | fiche et Communes lisent tous deux `comparateur.raw_rows` (`fiche_commune.py:22`) | identiques par construction |

---

## G — Veille (surface) et déclenchement

| connexion | état | preuve | impact |
|---|---|---|---|
| G1 · type annonces (Radar) | OK | `SurveillancePanel.tsx:247`→`creerRadarVeille`→`/radar/veille`→`veilles(type='radar')` | end-to-end |
| G1 · type filtre (recherche carte) | OK | `SurveillancePanel.tsx:164`→`saveSearch`→`/events/searches`→`saved_searches` | end-to-end (mais lossy, cf KO-7) |
| G1 · type parcelle (cloche) | OK | `toggleWatch`→`/events/watch/{idu}`→`watched_parcels`, évalué `events.py:346` | end-to-end |
| G2 · évaluation Radar | OK | job `radar_digests` (`jobs_impl.py:139`) quotidien → `pige.digests.envoyer` | évalue sur biens du jour |
| G2 · évaluation permis/parcelle | DOUTE | `evaluer_suivis`/`_veilles_match` déclenchés **à l'ingestion** (SITADEL mensuel, bascule), pas de cron dédié « évaluer veilles » | cadence dépend de l'ingestion |
| G3 · un event → 4 chemins | OK | écrivain unique `creer_notification` (`events.py:160`)→`event_log` ; cloche `/events` (`:673`), dashboard `/events/count` (`:701`), historique + mail digest (`:992`) lisent tous `event_log` | **zéro divergence** — source unique confirmée |
| G5 · désactivation/suppression | OK | Radar soft `actif=false` ; `saved_searches` hard-delete (`events.py:954`) ; watch toggle | toutes supprimables |
| G5 · cloisonnement par compte | OK | tous reads `compte_id IS NOT DISTINCT FROM :cid` (`events.py:770`, `pige/api.py:33`, `alertes.py:53`) | propriétaire seul, pilote NULL isolé |

G4 (mail) : OK global — SMTP Brevo gaté config, `contact@labuse.immo`, désabonnement RFC 8058 one-click (`events.py:1245`), `last_digest_at` avancé seulement sur succès (`events.py:1249`), corps sans adresse exacte ni contenu d'annonce (marché exclu du mail).

---

## H — Radar

| connexion | état | preuve | impact |
|---|---|---|---|
| H1 · annonce→parcelle + certitude | OK | `rattachement_niveau/confiance` (`pige_biens`), servi `client.py:114`, badge front | degré affiché, jamais pin faussement sûr |
| H2 · filtres = mêmes annonces que carte & fiche commune | OK | `_where` `client.py:26` `pige_biens JOIN pige_faits WHERE valide_at NOT NULL` ; `marche.stats()` même FROM ; fiche `marche_annonces` lit `stats()` | source unique partout |
| H3 · « sous le marché » = sector_price backend | OK | `badges_pour_biens` (`signaux.py`) calcule le référentiel côté Python ; front affiche `sous_le_marche` rempli backend (`client.py:126`) | pas de calcul local front |
| H4 · veille annonces → cloche + mail + dashboard | DOUTE | radar veille → mail `radar_alerte` (`digests.py:316`) + `journaliser(EV_DIGEST)` dans `event_log` scopé compte (`digests.py:250`) → visible cloche/dashboard ; MAIS event « digest envoyé » agrégé, pas par annonce ; succès n'appelle pas `creer_notification` (seul l'échec, `:258`) | 4 chemins atteints en mode dégradé (récap), pas un event unique par annonce |
| **H5 · dépôt agence : flag & invisibilité clients** | **DOUTE** | colonne `depose_par_agence` (`tables.py:248`) ; écriture `publier` gardée admin-ou-drapeau-ouvert (`_depot_admin_ou_ouvert` `api.py:512`, 404 si fermé non-admin) ; MAIS lectures clients (`_where` `client.py:26`) **ne filtrent PAS le drapeau** | brèche ciblée : un dépôt admin « pour tester » pendant flag fermé (`api.py:513`) devient visible aux clients (Radar, fiche commune « N biens », Mon secteur) |
| H6 · aucun contenu d'annonce stocké | OK | seul `depot_agence.publier` écrit `photos`/`description` (`depot_agence.py:73`) ; collecte/intake/html_ingest n'écrivent NI l'un NI l'autre (grep vide) ; collecté `photos=[]`/`description=NULL` (`client.py:139`) | doctrine respectée : contenu collecté jamais stocké ; déposé = confié par l'agence |

---

## I — Projets

| connexion | état | preuve | impact |
|---|---|---|---|
| I1 · cadrage → même run partout | OK | un seul `RUN` (`projets.py:21`) dans `_cadrage_to_filtre`/`_cadrage_total` ; wizard `/compteur` et projet `/parcelles` appellent le MÊME `_cadrage_total` (`:492,1125`) | wizard ne peut annoncer un nombre que le projet dément |
| I1 · compteurs lus du back | OK | `counts.proposee=_cadrage_total−décidées` (`:1129`) ; ProjetKanban lit `etat.counts`, n'affiche que | chiffres serveur |
| I2 · bandeau = chiffres de la liste | OK | bandeau + chips servis par `_analyse_cadrage` sur `p.filtres` (`:1209`), même population que `_cadrage_total` | cohérent |
| I3 · retenir/écarter → écrit + relu (parcours, Kanban) | OK | PATCH `/projets/{pid}/parcelle/{idu}`→`projet_parcelles` (`:1266`) ; `_sync_crm_retenue` crée pipeline `contact_a_preparer` (`:1271,891`) ; front invalide `parcours+projets+pipeline` | décision persistée, relue |
| **I3 · Scan patrimoine « hors écartées » = décisions user** | **KO** | `/modules/patrimoine` (`modules.py:255`) ne joint ni `projet_parcelles` ni `pipeline_entries` ; « écartée » = `etage0` cascade | **KO-10** — faux ami, aucune reprise des décisions Projet |
| **I4 · Mes courriers → Courrier → dashboard → statut relu** | **DOUTE/KO** | chaîne demande réelle (`courrier.py:86`→`courrier_demandes`+cloche+Brevo→admin `Courrier.tsx:41`) MAIS statut jamais affiché dans « Mes courriers » (`ProjetsPanel.tsx:235`) ni dans l'outil | **KO-6** — boucle fermée côté notification seulement |
| **I4 · statut courrier relu dans CRM/Kanban** | **KO** | `courrier_demandes` sans `projet_id` ni FK `pipeline_entries` (`courrier.py:52`) ; colonnes Kanban ≠ statuts courrier | **KO-6** — silo courrier déconnecté du CRM |
| I5 · projet = un compte, invisible ailleurs | OK | `_scope` (`:38`) + `_projet_or_404` sur les 12 endpoints `/{pid}*` ; `pour-parcelle` filtre `p.compte_id` (`:808`) | cloison solide, 404 (jamais 403) |

---

## J — CRM

| connexion | état | preuve | impact |
|---|---|---|---|
| J1 · retenue → piste CRM (auto/manuel cohérent) | OK | AUTO `_sync_crm_retenue`→`contact_a_preparer` (`:891`) ; MANUEL POST `/pipeline` (`app.py:5636`) ; dédup `ON CONFLICT(compte_id,parcel_id)` ; quitter retenue archive l'entrée AUTO ciblée (`:919`) | cohérent, non destructif, réversible |
| J2 · piste → contact (nom/adresse), courrier, relance, statut | OK (partiel by design) | contact `_proprietaire_public` (`app.py:5540`, particulier JAMAIS nommé) ; saisie manuelle `prospection` jsonb ; relance `reminder_date` (`app.py:5699`) | PII particulier jamais auto ; courrier ≠ relié (J4) |
| **J3 · Kanban = statuts Courrier + dashboard** | **KO** | colonnes `crm_columns`/pipeline.yaml (`reperee…abandonnee`) vs statuts courrier (`demande…poste`, `courrier.py:86`) vs buckets dashboard (`Courrier.tsx:22`) | **KO-6** — 3 vocabularies disjoints |
| **J4 · boucle retenue→piste→courrier→réponse→statut sans re-saisie** | **KO** | retenue→piste OK ; piste→courrier **RE-SAISIE** (`ModulePanel.tsx:912`) ; courrier→CRM **absent** (pas de FK) ; « répondu » **inexistant** (`STATUTS_DEMANDE` s'arrête à `envoye`) | **KO-6** — la boucle ne se ferme pas |
| J5 · CRM strictement par compte | OK | `/pipeline*` (7 endpoints) + `/pipeline/columns*` (`_own_column` 404) + `courrier_demandes` (`demandes_de` + `exiger_admin`) tous `compte_id` | cloison solide |
| J5 · exception `courrier_envois` scopé session/IP | DOUTE | `/courrier/envois` (`api/courrier.py:230`) filtre `sujet`=hash(session)/IP, pas `compte_id` ; chemin DIRECT stub (bouton masqué provider=stub) | dormant ; à re-scoper compte avant activation Merci Facteur |

---

## K — Copilote

Deux systèmes coexistent : **v2** (`/api/copilote-v2/*`, conversationnel, entrée principale) et **v1** (`/api/copilote/runs*`, mission lourde).

| connexion | état | preuve | impact |
|---|---|---|---|
| K1 · modèle raisonnement | **OK** | `ai_models.py:19 MODEL_REASONING="claude-sonnet-4-6"`, listé ACTIVE (`:36`), non RETIRED — **ID Sonnet 4.6 valide** (registre modèles courant) | *(corrige une alerte « ID non standard » d'un sous-agent à connaissance périmée : l'ID est bien valide)* |
| K1 · modèle factuel | OK | `ai_models.py:18 "claude-haiku-4-5-20251001"` ; classify `router.py:259` | ID daté valide |
| K1 · clé / client / timeout / retries | OK | `core.py:42` `ANTHROPIC_API_KEY` ; `:49` timeout 25s retries 2 ; web `outils.py:488` client dédié | centralisé |
| K1 · error handling / fallback | OK | `core.py:458` `except`→`degraded=True` ; garde `/ask` `copilote_v2.py:115` (jamais 500) | échec → réponse honnête dégradée |
| K2 · lit les moteurs A1, ne recalcule rien (v2) | OK | `copilote_v2/outils.py:334` `_q_v2_fiche` (verdict/tier LUS) ; réutilise `patrimoine`/`commune_contexte`/`velocite`/`marche`/`piscines`/`permis` ; run `Q_A_RUN_LABEL` | mêmes valeurs/date que la fiche |
| K2 · `sector_price`/`compute_bilan` (v1) | OK | `copilote/moteurs.py:366-406` importe et appelle les fonctions de la fiche | bilan Copilote = bilan fiche à l'euro |
| K3 · missions donnée/web/notion/script | OK | `answering.py:382,388,391` routes ; web `outils.py:487` `web_search_20250305` natif ; base-d'abord | chacune branchée sur sa source |
| K4 · conso comptée PAR COMPTE + dashboard | OK | `core.py:120` `ia_log.compte_id` ; dashboard GROUP BY compte_id (`dashboard.py:260`) + édition quota (`:551`) | coût attribué au compte |
| K4 · quota appliqué par compte | OK (nuance) | `/ia` lit `copilote_quota_jour` per-compte (`ia.py:340`) ; `/ask` v2 borne sur `copilote_v2_missions_jour` **global** (`copilote_v2.py:76`), compteur scopé `c:<id>` | **deux plafonds distincts** (cf KO-3 pour l'écart avec l'UI) |
| K5 · mémoire par compte (liste « Reprendre ») | OK | `historique.py:104` `lister` WHERE `compte_id IS NOT DISTINCT FROM :c` | pas de fuite inter-comptes |
| K5 · lecture d'une conversation (ownership) | OK | `historique.py:114` `charger` scopé → None → 404 (`copilote_v2.py:193`) ; runs v1 `_run_or_404` (`api/copilote.py:70`) | **pas d'IDOR** |
| K6 · réponse propose outil / parcelle | OK | `ReponseInline.tsx:38-46` `ouvrir`/`ouvrirCarte`/idu→`select` ; pont carte au bon compte (FIX-PONT-TIER) | jamais un cul-de-sac |

---

## L — Les 15 outils

**Zéro KO de recalcul métier au front sur les 15 outils.** Les seuls `Math.*` en front sont de la mise en page. Toutes les grandeurs viennent du backend.

| outil | état | preuve | impact |
|---|---|---|---|
| L1 Étudier — entrée + bloc secteur `sector_price` | OK | `EtudierBien.tsx:111` ParcelInput ; `mon_secteur.py:79` sector_price ; prix demandé SAISI ; `scoreur.py:161` compute_bilan_servi ; prefill IDU | moteur unique, ponts pré-remplis |
| L2 Faisabilité = moteur fiche | OK | `M22Programme.tsx:212` réutilise `FaisabiliteTab` ; `/faisabilite/{idu}` `modules.py:1239` `compute_bilan_servi`+`sector_price` | 0 recompute front |
| L3 Taxe d'aménagement — 100 % backend | OK | `taxe_amenagement.py:29` `calculer` (None si taux absent) ; front « aucun montant en dur » | taux communal jamais inventé |
| L4 Pièges et risques | OK | `modules.py:1103` checklist + `servitudes.NON_COUVERT` | pas de re-scoring |
| L5 PLU — source/millésime | OK | `plu_reglement.py:29` `resolve_reglement` ; `PluAnnuaire.tsx:94` affiche `millesime`/`source_url` | front = lecture |
| L6 Comparer = fiche partagée | OK | `/compare` `app.py:5230` re-lit `_q_v2_fiche` par parcelle | aucun recompute |
| L7 Assemblage — SDP/charge cumulées backend | OK | `assemblage.py:119` `aggregate_assiette`+`compute_bilan` | agrégation des fiches |
| **L7 · ×gain re-divisé au front** | **DOUTE** | back `assemblage.py:216` `round(sdp/sdp_max_seule,1)` ; front `moteurs.tsx:152` re-divise à 2 déc. | **KO-15** — dette de précision, 2 expressions du même ratio |
| L8 Scan patrimoine — recherche par NOM | OK | `ScanPatrimoine.tsx:74` (SIREN/IDU/nom/repli BAN) ; `modules.py:196` SQL `parcelle_personne_morale.denomination` | recherche DB réelle |
| L8 · onglets possèdent/construisent + moteur | OK | `modules.py:232` `parcel_p_score_v2.tier`+`parcel_residuel`+`dryrun` (run q_v11_m137) ; onglet « construit » = `VeillePromoteurs` SIREN partagé | tier/résiduel du run servi |
| L8 · pont fiche (IDU) | OK | items portent `idu` ; `select(idu)`/`m02Prefill` | clic → fiche |
| L8↔L11 · pont Scan↔Permis | DOUTE | rattachement SIREN/opération partagés + liens `programme/site` ; **pas** de deep-link « ouvrir Permis sur cette opération » | intégration par la donnée, pas navigation |
| **L9 Courrier — transport d'envoi** | **DOUTE** | `/statut` « envoi postal pas encore disponible » ; `/demande`→INSERT+notif Vic ; statuts avancés manuellement ; registry promet « LABUSE se charge de l'envoi » (`registry.ts:95`) | workflow HUMAIN, pas auto-send — promesse produit optimiste |
| L9 · statut écrit/relu + anti-double | OK | écrit `courrier.py:96` ; relu `getCourrierDemandes` + admin ; dédup FIX-GB-013 | statut persisté, pas de double mail |
| L10 Remonter le temps | OK | `ortho.py:43` millésimes « © IGN Licence Ouverte » ; display-only ; clic→`parcelPrefill` | aucun calcul métier |
| L11 Permis — Sitadel + millésime | OK | `modules.py:370` `FROM sitadel_permits`, fenêtre `max(date)`, source « SITADEL (SDES/Dido) 974 » | fenêtre honnête |
| L11↔L8 · lien opérations | DOUTE | `permit_id`/`siren` portés ; rattachement SIREN, pas deep-link | symétrique de L8↔L11 |
| L12 Densifier = même résiduel que la fiche | OK | `renouvellement.py:164` `sdp_residuelle_m2`←`dryrun` (`Q_A_RUN_LABEL`) = même run/table que la fiche | source unique — nuance : chaîne figée au run |
| L13 Prospection solaire — sources | OK | `modules.py:585` `parcel_solar` (PVGIS Sourcé) + `parcel_equipements.piscine` (BD ORTHO Estimé) ; front « aucun recalcul » | sourcé/daté, lecture seule |
| L14 Communes = mêmes chiffres que fiche commune | OK | `fiche_commune.py:17` `comparable` = même `comparateur.raw_rows`, même run | source unique |
| L15 Étude de zone = moteur « Autour de cette parcelle » | OK | `/parcels/{idu}/zone` et `/outils/etude-zone` appellent tous deux le module `..zone` (`app.py:3987,4062`) | moteur partagé |

---

## M — Sources

### M1 · Matrice source → consommateurs
| connexion | état | preuve | impact |
|---|---|---|---|
| registre canonique (statut connecte∪manuel, hors DOUBLON/RETIRÉ/masquées) | OK | `sources_catalog.py:16,32,44` (`STATUTS_AFFICHES`, `WHERE_AFFICHEES`, `est_affichee`) lu par SQL ET Python | ne peuvent diverger |
| comptage accueil ∧ /sources | OK | `accueil.py:78` et `app.py:918-923` lisent tous deux `WHERE_AFFICHEES` | chiffre == liste |
| source→fiche (join cascade→data_sources) | OK | `app.py:2682` `data_source_id JOIN data_sources` | mapping réel des sources servies |
| source→fraîcheur (table par source) | OK | `ingestion/fraicheur.py:32-101` (sitadel→`sitadel_permits`, dvf→`dvf_mutations_parcelle`, dpe→`dpe_records`, ban→`adresses`…) | 11 sources bornables |
| millésime amont centralisé | OK | `data_sources.source_millesime` lu par /sources, fiche, layers, ortho | pas de date en dur |
| date dernier rafraîchissement | OK | `app.py:926-943` depuis `ingestion_runs` | jamais en dur |

### M2 · Dashboard : état / agent version / désactivation
| connexion | état | preuve | impact |
|---|---|---|---|
| état par source (à jour/en retard/en panne) | OK | job `sources-fraicheur` (`jobs_impl.py:67`) écrit `fraicheur_statut`, rendu `SourcesPage.tsx:40` | staleness visible |
| **échec d'ingestion → « en erreur » (vitrine)** | **KO** | job ne connaît que `a_jour/en_retard/en_panne/sans_echeance` ; `/sources` compte seulement `status IN('ok','success')` (`app.py:928`) | **KO-14** — un run échoué n'apparaît pas « en erreur » côté public |
| agent vérifiant une nouvelle version amont | ABSENT | panneau « Agent de veille des sources » grisé V2 (`admin/Sources.tsx:122`) ; seul `sentinelle-dvf-cadastre` (`jobs.py:264`) couvre DVF/cadastre | pas d'agent généralisé |
| admin désactive une source depuis le dashboard | ABSENT | D6 n'expose que `/cadence` et `/relancer` (`dashboard.py:663,681`) ; `SOURCES_MASQUEES=frozenset()` en dur | l'action n'existe pas |
| propagation « source désactivée » aux consommateurs | ABSENT | consommateurs lisent `data_sources` par id **sans vérifier `est_affichee`/status** | même taguée « retirée », les consommateurs continueraient de lire |

### M3 · Page Sources = millésimes réellement lus
| connexion | état | preuve | impact |
|---|---|---|---|
| millésime page == millésime lu | OK | tous lisent `data_sources.source_millesime` (SourcesPage, fiche, layers, ortho) | champ unique |
| licence dérivée serveur de `legal_notes` | OK | `app.py:1033` `_source_licence` | corriger la base suffit |

---

## N — Dashboard admin

### N1 · Chaque tuile écoute la bonne source
| connexion | état | preuve | impact |
|---|---|---|---|
| Licences / Actifs 24h / Conso IA / Backup | OK | `dashboard.py:165-178,133` → `AdminView.tsx:164` ; Conso IA = même requête que /admin/ia | LU, pas recalculé |
| Tuile « Santé serveur » | DOUTE | `schema_heal` posé au **boot** (`app.py:211`), relu `dashboard.py:194` | reflète le schéma au démarrage, pas le runtime ; libellé « /readyz » sur-promet |
| « Courrier à déposer » (compteur) | ABSENT | `dashboard.py` n'agrège aucun `courrier_demandes` ; seul le fil montre l'event ponctuel | pas de KPI « N à déposer » |
| Sources / IA par licence / CRON | OK | `dashboard.py:628,512,273` (même `est_affichee` que /sources) ; CRON via `/healthz/crons` | agrégats directs |

### N2 · Actions admin effectives et re-lues
| connexion | état | preuve | impact |
|---|---|---|---|
| « Ajouter des crédits IA » | ABSENT | aucun endpoint ; `admin/Ia.tsx:42` = lien console Anthropic externe | solde IA non pilotable (assumé) |
| éditer quota Copilote (écriture) | OK | `dashboard.py:551` UPDATE `copilote_quota_jour` ; re-lu `Ia.tsx:18` | l'écriture part |
| **quota édité lu par le Copilote servi** | **KO** | override lu par NL `/ia` (`ia.py:340`) seulement ; `/ask` v2 borne global (`copilote_v2.py:76`) ; UI promet « le /ask le lit » | **KO-3** |
| « ouvrir/fermer dépôt agence » (toggle) | ABSENT | flag = `config.radar_depot_agence_actif` (env, `config.py:70`) ; `/etat`,`/ouvert` lecture seule (`pige/api.py:572,584`) | change par config/redéploiement |
| désactiver une source | ABSENT | cf M2 | idem |
| révoquer une session | ABSENT | sessions OBSERVÉES (`comptes.py:302`) ; coupe globale via suspend (`:558`) | par doctrine SESSION-1 |
| invitation/convertir/suspendre/rétablir/cadence/relancer/dégeler | OK | `dashboard.py:361-490,663-719` ; fronts invalident les queries | effectifs + re-lus |

### N3 · Santé technique
| connexion | état | preuve | impact |
|---|---|---|---|
| **monitoring des endpoints métier des écrans** | **ABSENT** | seule sonde `healthcheck` (`jobs_impl.py:148`) teste `GET /health` (`app.py:390`, `{status:ok}` **sans DB**) + disque | **le cas `/accueil/chiffres` vivant/écran vide ne serait PAS capté** |
| tuile « Santé serveur » = runtime | DOUTE | `schema_heal` boot-only | mesure le schéma au boot |
| `/healthz/crons` (crons morts) | OK (crons seulement) | `api/ops.py:48` via `ingestion_runs` | un cron mort se voit |
| liveness process | OK (niveau 1) | `app.py:390,394` | prouve que le process tourne |

---

## O — Comptes, licences, sessions, mails

### O1 · Invitation → essai 48h → conversion → licence
| connexion | état | preuve | impact |
|---|---|---|---|
| invitation (compte+user `invite`, token 7j, lien à la main) | OK | `comptes.py:169` ; `dashboard.py:361` | envoi manuel (décision Vic) |
| activation (argon2id + CGV horodatée) | OK | `comptes.py:225` ; `onboarding.py:219` | CGV consignée |
| conversion = webhook Stripe + filet reconcile | OK | `facturation.py:392,282` | « a payé ⇒ a accès » même si webhook manqué |
| essai 48h paramétrable | OK | `config.py:178` ; `dashboard.py:385` | conforme |
| expiry essai → suspension AUTO (accès coupé, **données conservées**, réversible) | OK | `comptes.py:328-338,555` | « à régulariser », aucune donnée détruite |
| chaque étape visible au dashboard | OK | `dashboard.py:260-326` (statut, essai_expire_at, mails, rappels) | origine unique |

### O2 · Multi-licences
| connexion | état | preuve | impact |
|---|---|---|---|
| sièges / rattachés à une structure | ABSENT (par conception) | `comptes.py:71` `sieges` défaut 1 (toujours 1) ; CGV art.3 « 1 licence = 1 utilisateur » | **fonction non livrée** (mono-siège) |
| multi-users sous un compte (capacité) | DOUTE | FK `utilisateurs.compte_id` ; aucun parcours ne crée un 2ᵉ user | capacité dormante |

### O3 · SESSION-1
| connexion | état | preuve | impact |
|---|---|---|---|
| partage OBSERVÉ, jamais bloqué | OK | `comptes.py:302-325,110` (IP/UA hachées RGPD) | aucune déconnexion |
| éviction visible dashboard comme signal | OK | `dashboard.py:329-353` (« AUCUN blocage » `:332`) | signal, pas barrage |

### O4 · Mails
| connexion | état | preuve | impact |
|---|---|---|---|
| **transport UNIQUE** | **KO** | SMTP `mail.py` (reset/courrier/digest events) ET API Brevo `brevo.py` (essai/onboarding/suspension + digests Radar `pige/digests.py:248`) ; `mail.py:1-4` se dit « unique » | **KO-12** |
| sender unique (par canal) | OK | SMTP `contact@labuse.immo` (`mail.py:71`) ; Brevo sender par template | jamais Gmail brut |
| DA / templates centralisés | OK | `emails.py:107` ; Brevo par ID (`brevo.py:22`) | réécriture sans code |
| E3 · envoi à l'abonné seul | OK | reset `onboarding.py:405` ; digest `digests.py:234` ; courrier admin seul | pas de masse hors abonné |
| H6 · pas de contenu d'annonce dans les mails | DOUTE | digest Radar rend `titre`(type+commune), `prix`, `prix_m2`, `surface`, `url` portail (`digests.py:107-179`) ; adresse exacte NON rendue (commune seule) | faits d'annonce + lien portail dans mail opt-in — à arbitrer vs H6 |
| échec d'envoi non silencieux | OK | SMTP→event admin (`mail.py:106`) ; Brevo `{envoye,raison}` ; Radar bruyant (`digests.py:254`) | aucun « envoyé » à tort |

### O5 · Cloisonnement strict par compte
| connexion | état | preuve | impact |
|---|---|---|---|
| socle multi-tenant | OK | `api/tenant.py:33-137` (`SCOPED_TABLES`, `current_compte`, `compte_ou_401`) | 20+ tables scopées |
| Projets / CRM / Veilles / Copilote / Courriers / Crédits | OK | `projets.py:630` + `_projet_or_404` ; `copilote_v2.py:149,184` ; `courrier.py:133` ; quota clé `c:<id>` (`protection.py:113`) | chaque liste scopée |
| endpoint LIST sans filtre owner | (aucun trouvé) | balayage projets/events/ia/copilote_v2/courrier : tous `current_compte` ; `/admin/*` gatés `exiger_admin` | pas de list-all non scopé |

---

## P — Doctrine, vérifiée comme des connexions

| connexion | état | preuve | impact |
|---|---|---|---|
| P1 · aucun contenu d'annonce en base/export/cache/log | OK | `pige/__init__.py:6`, `pige/tables.py:241`, `pige/html_next.py:278` (faits déclarés, aucun texte) ; `client.py:106` | faits + lien seulement ; photos/description seulement pour biens **déposés** (confiés) |
| P1-bis · dans les MAILS | DOUTE | cf O4/H6 : faits d'annonce (prix/commune/lien) dans le digest | à arbitrer |
| P2 · adresse exacte : abonnés seulement, partout | OK (coarse) | `adresse_exacte` derrière le garde global `_auth_guard` (`app.py:351-381`, toute route métier exige session) ; `pige/client.py:138` | aucune adresse exacte publique — mais gating **par plan** non implémenté (cf E3) |
| P3 · aucun robot sur portails (dépôt one-shot seul appel sortant) | OK | seule sortie `_fetch_page_oneshot` (1 requête, 8s, **aucun retry**, `pige/api.py:542`) à la demande admin ; `pige/portails.py:4` ; cron list (`jobs.py:238`) = backup/fraîcheur/radar-cycle(ne fetch RIEN)/digests/health — aucun fetch portail | doctrine respectée |
| P4 · rien n'entre sans validation humaine | OK | `/admin/radar/deposer-html` crée un **brouillon** (`valide_at NULL`, `pige/api.py:64`) ; `/valider` = étape humaine (`:85`) ; clients ne voient que `valide_at NOT NULL` | écriture après passage admin |

---

## Connexions NON PRÉVUES par le mandat, trouvées en chemin

1. **Deux systèmes Courrier** : `courrier_demandes` (flux VIVANT, scopé compte, cloche+Brevo+admin) et `courrier_envois` (envoi direct stub, scopé `sujet` session/IP, dormant). Le front n'utilise que `demande`. À unifier avant activation Merci Facteur.
2. **`cascade_results` LIVE encore lue** (KO-2) par `anti_fiche.py:52` et `app.py:4428` **malgré** le commentaire `served_cascade.py:6` qui la déclare morte.
3. **Copilote v1 ET v2 coexistent** — deux routers montés (`app.py:5799`/v2), deux chemins de quota (KO-3), v1 lit encore `cascade_results`.
4. **Deux builders de fiche PDF** : `_q_v2_fiche` (fiche/PDF principal) vs `bq.collect` (banquier/argumentaire, cache séparé `_PDF_CACHE`) — surface de divergence.
5. **Deux transports mail** (KO-12) et **deux plafonds Copilote** (KO-3) — doctrines « unique » démenties par le code.
6. **`ingestion/ortho_tiles.py:28 MILLESIME="2025"` en dur**, parallèle à `data_sources.source_millesime` (chemin raster flash).
7. **Trois constantes de run en dur** hors du fichier versionné : `served_cascade.py:20`, `scoring/lignee_tete.py:25`, `bascule_gardes.py:31` (toutes `q_v8_calibre`). Seule la 1ʳᵉ est servie (KO-1) ; les deux autres probablement inertes.
8. **Commentaires périmés** : `api.ts:926` (« /courrier/demande retiré » — faux, wiré) et `AddressAutocomplete.tsx:8` (« api-adresse.data.gouv.fr » — c'est la table interne).
9. **`SOURCES_MASQUEES = frozenset()`** (`sources_catalog.py:20`) : le mécanisme de masquage de source existe mais est vide et n'est de toute façon pas consulté par les consommateurs (M2).

---

## Ce que le dashboard écoute (remontées attendues — E2, G3, H5, I4, K4, M2, N1–N3, O1, O3)

| remontée attendue | vers le dashboard | état | preuve | ce que voit l'admin si KO |
|---|---|---|---|---|
| **E2** · Signalement d'erreur de fiche (client) | tuile signalements admin | **KO** | `postSignalement`→`/signalements` (revue **CLI-only**) ; compteur `signalements_en_attente` écoute l'AUTRE signaler (annonce Radar, `event_log kind='pige.signalement_client'`) | un client signale une donnée fausse → **rien** au dashboard (file QA privée) |
| **G3** · Veille déclenchée (compteur d'events) | `/events/count` (cloche + dashboard) | **OK** | event unique `creer_notification`→`event_log` ; les 4 chemins lisent `event_log` (`events.py:701`) | — |
| **H5** · Dépôt agence (drapeau + fil) | état du flag + events dépôt | **DOUTE** | flag `config.radar_depot_agence_actif` **lecture seule** (`pige/api.py:572`), pas de toggle dashboard (N2 ABSENT) ; dépôts admin « test » visibles clients même flag fermé | admin ne peut pas ouvrir/fermer le dépôt depuis l'écran ; un test fuit aux clients |
| **I4** · « Courrier à déposer » (une cliente veut que Vic dépose) | demande visible admin | **OK (demande)** / **KO (KPI + statut retour)** | demande arrive : cloche+Brevo+section Courrier admin (`api/courrier.py:41`, `Courrier.tsx:41`) ; MAIS **pas de compteur** « N à déposer » (N1 ABSENT) et statut retour **jamais relu** dans Projets/CRM (KO-6) | Vic voit la demande dans la section, mais aucun KPI ni retour de statut vers le client |
| **K4** · Crédits IA (conso par compte, ajout de crédits) | tuile Conso IA + licences | **OK (conso)** / **KO (quota)** / **ABSENT (ajout)** | conso GROUP BY `compte_id` (`dashboard.py:260`) OK ; quota édité **ignoré par /ask v2** (KO-3) ; « ajouter des crédits » = lien Anthropic externe (N2 ABSENT) | admin voit qui dépense, mais ne peut ni ajouter de crédits ni relever réellement le plafond Copilote v2 |
| **M2** · État des sources (à jour / en retard / en erreur) | synthèse Sources | **OK (retard)** / **KO (erreur)** / **ABSENT (désactiver, agent version)** | staleness OK (`jobs_impl.py:67`) ; échec d'ingestion **non surfacé** en « erreur » (KO-14) ; pas d'agent de nouvelle version ni d'action désactiver (M2 ABSENT) | une source « plantée mais récente » paraît saine ; impossible de la désactiver depuis l'écran |
| **N1** · Tuiles (comptes/crédits/veilles/signalements/courriers/dépôts/sources/sessions/santé) = même donnée que la surface | agrégats directs | **OK sauf 2** | comptes/IA/sources/CRON/licences = requêtes directes des tables d'origine ; **« courriers à déposer » ABSENT** (pas de compteur) ; **« Santé serveur » DOUTE** (schema boot-only) | deux tuiles manquent/trompent, le reste est fidèle |
| **N2** · Actions admin effectives et re-lues immédiatement | écritures propagées | **partiel** | invitation/suspend/rétablir/cadence/relancer/dégeler **OK** ; **ABSENT** : ajouter crédits, toggle dépôt, désactiver source, révoquer session ; **KO** : quota Copilote (KO-3) | 4 actions du mandat n'existent pas ; 1 écrit mais n'a pas d'effet réel |
| **N3** · Santé technique — endpoints des écrans surveillés | sonde de santé | **ABSENT** | seule sonde teste `GET /health` **sans DB** (`jobs_impl.py:148`, `app.py:390`) | un endpoint métier mort (type `/accueil/chiffres`) reste invisible — **le trou exact cité par le mandat** |
| **O1** · Invitation → essai → conversion → licence, chaque étape visible | pipeline licences | **OK** | `dashboard.py:260-326` (statut app+Stripe, essai_expire_at, mails, rappels J+3/J+10) | — |
| **O3** · Éviction de session = signal commercial, jamais blocage | sessions observées | **OK** | `dashboard.py:329-353` (partage observé, IP/UA hachées, « AUCUN blocage ») | — |

**Lecture d'ensemble du dashboard** : les remontées **passives de lecture** (G3 events, K4 conso, O1 licences, O3 sessions, N1 comptes/sources) sont fidèles et branchées sur la source d'origine. Les remontées qui exigent une **action** (N2) ou une **surveillance active** (N3 endpoints, M2 erreurs/désactivation, E2 signalements, I4 statut retour) sont **majoritairement absentes ou cassées** — c'est le point faible structurel du dashboard : il **observe bien** mais **agit peu et ne se surveille pas**.

---

*Fin du rapport. Aucun correctif dans ce mandat — les corrections feront l'objet de CONNEXIONS-2, écrit à partir de ce rapport.*
