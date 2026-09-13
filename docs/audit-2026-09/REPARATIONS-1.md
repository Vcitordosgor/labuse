# REPARATIONS-1 — réparer ce que l'audit a trouvé, puis les deux sources qui manquent

Branche `fix/reparations-1` depuis `main` (`a4d770b8`, CIRCUIT-6 mergé). Worktree `~/Desktop/labuse-etat`.
Base locale `labuse:5432` (431 663 parcelles). Ports de preuve : API `:8032`, front `:5200`. Rien n'est mergé, rien n'est basculé, le run servi (`q_v11_m137`) n'a pas bougé.

État des verrous à l'ouverture : **V3a seul rouge** (tuiles fabriquées pour `q_v14`, manifeste sert `q_v11_m137`) — attendu, objet du lot 1.

---

## LOT 0 — La fuite aléa (prioritaire absolu)

### Ce que l'enquête a montré (différent du constat du mandat)

Le mandat disait : « le correctif dort sur `fix/retours-12`, jamais mergée ». **La réalité sur cette base est en avance sur le mandat** :

1. **Le correctif code + donnée est déjà sur `main` ET déjà exécuté ici** : commit `b5009d4f` (« RETOURS-21 A — aléa mouvement de terrain servi au bon niveau », 06/09) — `reclassifier_alea_niveau()` + CLI `alea-reclassifier` + `tests/test_retours21_lotA.py`. Il a réaligné les 484 zones le 06/09.
2. **La quarantaine `georisques_mvt` est déjà levée** : filtre rejoué le 06/09, tous contrôles `ok` (dont `d_alea_non_retrograde` bloquant = 0), `dernier_verdict` = ok.
3. **La garde pompe est déjà vide** : `filtres.garde_pompe()` → `[]` (aucune source `run` en quarantaine).

**Ce qui restait réellement ouvert** : l'écart sonde `circuit_ecarts` id=2 (`alea_inondation_couche` / `distribution`), ouvert le 06/09 à 01:20 — **avant** l'exécution du correctif le même jour à 12:48 — et **jamais soldé depuis**, alors que la sonde est repassée (13/09 18:00 : la mesure était saine). Cause : `sonde_circuit.verifier_categorielle()` **ouvre** des écarts mais n'a pas de passe de solde — contrairement à `verifier_robinets()` qui a sa passe 4.4. Un écart guéri restait donc « ouvert » à vie : ligne rouge fantôme sur la page Circuit, fuite comptée par G7, et le mot « fuite aléa ouverte » dans toutes les dettes. Le test existant (`test_distribution_aleas_attrape_retours13`) avouait la faille : son assertion de solde se terminait par `or True` (toujours vraie) avec le commentaire « la ligne reste (historique) ».

### Le correctif (celui de cette session)

- `src/labuse/sonde_circuit.py` — `verifier_categorielle()` tient désormais un jeu `verifies` (chiffre_id, clé, robinet_a, robinet_b) des couples **mesurés** à ce passage (4.1 zonage par témoin, 4.2 aléas, 4.3 permis approximatifs, 4.7 paliers), et **solde** (miroir exact de la passe 4.4 des robinets) tout écart ouvert re-mesuré sain : `statut='solde'`, `solde_le=now()`. Le compteur `soldes` entre dans le retour.
- `tests/test_circuit2_lot4.py` — l'assertion `or True` remplacée par de vraies assertions : après correction de la donnée, `res2["soldes"] >= 1`, **0** écart `ouvert` restant sur `alea_inondation_couche/distribution`, la ligne porte `statut='solde'` et un `solde_le`. C'est le test qui aurait attrapé la ligne rouge fantôme.

### Preuves sur les 484 zones — avant / après, effectifs par degré

Avant (état documenté par RETOURS-21 A, ingestion pré-correctif R6) : 360 ELEVE + 124 TRES_ELEVE servis `niveau='moyen'` = **484 zones**.

Après, mesuré sur cette base le 13/09 (`spatial_layers`, kind `georisque_alea`, 993 zones) :

| degré (DEAL brut) | niveau servi | classe | zones |
|---|---|---|---|
| ELEVE | **fort** | eleve | 360 |
| TRES_ELEVE | **fort** | tres_eleve | 124 |
| FORT / RESIDUEL_FORT / RESIDUEL_FORT_AGGRAVE | fort | fort | 29 |
| MOYEN / MODERE / MOYEN_B2U / MOYEN_SECURISABLE / RESIDUEL_MOYEN | moyen | moyen | 334 |
| FAIBLE / FAIBLE_A_MODERE / RESIDUEL_FAIBLE | faible | faible | 146 |

Idempotence prouvée : `reclassifier_alea_niveau()` rejoué → **0 zones réalignées, 0 degrés** (la donnée est alignée sur le mapping, source de vérité).

### La ligne rouge passe au vert, la pompe accepte — au navigateur, sans lancer de calcul

- Sonde rejouée (passage complet, 25 mesures, déclencheur `reparations-1-lot0`) : écart id=2 → `statut='solde'`, `solde_le=2026-09-13 19:04`. `circuit_controles` : `fuites_ouvertes=0` (les 4 passages précédents disaient 1).
- G7 : « dernier passage sonde 13/09 19:04 ; **0 fuite(s) ouverte(s)** ».
- **Au navigateur** (`:8032`/`:5200`, chromium) : page Circuit → bouton « Vérifier que tout coule » cliqué (un contrôle, jamais un calcul) → bandeau « **Contrôle terminé : 0 fuite(s), 0 eau ancienne, 0 écart(s) ouverts.** » (`captures/lot0-04-verifier-bandeau.png`). Détail de la pompe : bouton « **Faire tourner la pompe** » actif (vert), aucune quarantaine, « Basculer sur q_v14 » présent mais non touché (`captures/lot0-03-pompe.png`).

### Verrous après lot 0

23 joués : **22 verts**, 1 cassé = **V3a seul** (identique à l'ouverture — objet du lot 1). G7 est passé de « 1 fuite ouverte » à « 0 ».

### Noté au passage (traité au lot 1)

La LED du rail admin affiche « Run servi q_v14 » : elle lit `mvt_meta.run_label` (le run des **tuiles**) en l'étiquetant « Run servi » — c'est la même confusion candidat/servi que V3a mesure.

---

## LOT 1 — V3a ne bloque plus un candidat assumé

### Le geste

Nouveau module `src/labuse/circuit_candidat.py` + table `circuit_candidat_assume` (déclarée à la carte des tables, rôle écrit) :

- **`declarer(run_label, par, motif)`** — le marquage explicite. Motif **obligatoire** (on écrit pourquoi). **Journalisé** : geste `candidat` au `circuit_journal` (catégorie « bascule » dans la barre du journal). Idempotent (re-déclarer met à jour le motif).
- **`retirer(run_label, par)`** — le geste inverse. **Réversible et sans perte** : rien n'est supprimé, la ligne est tamponnée `retire_le`/`retire_par`, l'historique reste, on peut re-déclarer.
- CLI : `labuse circuit candidat [--assumer X --motif "…" | --retirer X] [--par …]` ; sans option, il montre l'état + l'historique.

### V3a fait la part des choses

`verrou_versions_generations` : quand les tuiles servent un autre run que le manifeste,

- **candidat déclaré et assumé** (la déclaration active porte exactement ce run) → verrou **VERT**, et la preuve **nomme** le candidat : « … ; tuiles du candidat DÉCLARÉ q_v14 (assumé par mandat REPARATIONS-1 le 2026-09-13), manifeste sert q_v11_m137 » ;
- **génération non déclarée** (le vrai danger) → **rouge**, comme avant, avec le chemin du geste dans le détail (« candidat NON déclaré (labuse circuit candidat --assumer) »). Assumer `q_v14` ne blanchit pas des tuiles `q_v15` : la déclaration est par run (testé).

### deploy.sh accepte ce cas précis — sans chemin de contournement

La porte de `deploy.sh` est inchangée : le code retour de `labuse circuit verrous` (la même commande, le même verdict). Avec la déclaration posée, la porte rend **0** (prouvé : `circuit verrous --par deploy` → « tout va bien », exit 0). Aucun bypass n'a été ajouté à `deploy.sh` : une génération non déclarée continue de refuser le déploiement.

### Exécuté sur la base

`q_v14` déclaré assumé le 13/09 (motif : « Vic refond l'algorithme — le prochain run sera q_v15 ; q_v14 reste en base comme point de comparaison, jamais basculé »). **Le candidat n'est ni purgé ni basculé** — il est en base, nommé, comparable au futur `q_v15`.

### La LED admin cesse de mentir

Le rail admin affichait « Run servi q_v14 » : `admin_pilotage` lisait `mvt_meta.run_label` (le run des **tuiles**) sous l'étiquette « Run servi ». La LED lit désormais `runs.current()` (le manifeste, la vérité de la bascule) — capture : « Run servi q_v11_m137 », « Verrous 16/16 », candidat q_v14 nommé sur le Circuit (`captures/lot1-01-led-et-candidat.png`).

### Tests et verrous

`tests/test_reparations1_lot1.py` (4 tests : non-déclaré rouge, déclaré vert et nommé, déclaration par run, journalisé + réversible) ; `tests/verrous` 99 passed. **Verrous après lot 1 : 23/23 « tout va bien » — V3a compris.**

---

## LOT 2 — La dette G6 et le palier

### 2a — Les 213 arêtes source → lecteur, déclarées finement

La dette CIRCUIT-6 (« 203 » au mandat, **213** mesurées à l'ouverture) : des fichiers qui lisent une table de réservoir sans que le registre dise quel champ ni quel robinet. Chaque arête a été **instruite en lisant le code du fichier** (6 volées d'agents, chiffres et robinets contraints aux candidats du registre — jamais inventés), et vit désormais dans **`src/labuse/registre/lectures.py`** : **224 lectures fines sur 213 arêtes** (certaines arêtes servent 2 chiffres) = **96 chiffre + robinet** (la donnée lue, le robinet qui la sert) **+ 128 machineries motivées** (jointure technique, batch producteur, état interne — raison écrite, jamais un robinet de complaisance).

**Le graphe est exact dans les deux sens**, et G6 le tient : toute arête du scan absente des déclarations = dette (0 aujourd'hui) ; toute déclaration dont le fichier ne lit plus la table = **déclaration périmée qui CASSE le verrou** en nommant la ligne (`lectures_perimees()`, 0 aujourd'hui). Preuve G6 : « dette fine : 0 ; lectures fines déclarées : 96 chiffre+robinet + 128 machineries motivées ; déclarations périmées : 0 ».

Les notes des lectures consignent aussi les **cas limites** (écran réel sans robinet au registre — Étude de zone marché, PDF Flash ZAN/SRU, Mon secteur, veille promoteurs, notifications ventes/permis, extrusion 3D du faîtage LiDAR à la carte) : matière écrite pour les prochains mandats, plus du silence.

### 2b — Le palier « Priorité » cesse d'être servi (décision Vic, réversible)

Un seul drapeau des deux côtés du miroir : **`tiers_client.PRIORITE_SERVIE = False`** (back) / **`status.ts PRIORITE_SERVIE = false`** (front), avec la raison écrite (×0,52 mesuré en marche avant, 1 vente sur 111, définition mécanique sur une seule variable). `code_palier()`/`codePalier()` — le point unique de résolution — projettent `priorite` (et donc `brulante`) sur `a_suivre` : **« À suivre » porte toute la tête classée**. Repasser le drapeau à True restitue le palier tel quel (testé) — **aucun rescoring, les tiers stockés ne bougent pas, le run servi non plus**.

Ce qui suit (tout par le point unique ou corrigé à la surface) :
- **Libellé** : chips, fiche, PDF, notifications, Copilote — tout ce qui passe par `tiers_client`/`status.ts` dit « À suivre ». Fiche d'une parcelle stockée `brulante` : chip **« À suivre »**, rang et fraction conservés, zéro « Priorité » (capture `lot2-01-fiche-ex-brulante.png`).
- **Compteur et barre** (zone résultats) : tête fusionnée (`brulante + chaude`) sous À suivre ; la note « zéro Priorité » d'une commune devient « zéro À suivre » sur la tête entière.
- **Légende et carte** : `LEGEND_V2_ORDER` = 3 paliers ; la tête peint la teinte À suivre (sombre via `TIER_V2_META`, clair via `contourBrulante` conditionnel).
- **Info classement / Info scoring** : la modale des paliers liste 3 paliers ; `defTiers.a_suivre` couvre l'éventail (« jusqu'à une chance sur cinq — la fraction précise est sur chaque parcelle »).
- **Phrase du modèle** : **« Mesuré en marche avant sur l'année 2025, tenue à l'écart de l'apprentissage : la tête du classement (« À suivre ») se vend ~6,7× plus que la moyenne de l'île… »** — le ×6,7 vient de `config/qualite_commune.yaml` (fold 2025 out-of-sample, gelé à l'audit RR) ; le lift 12 mois (~13,3×, contaminé : 2025 est à la fois cible de recalage et fenêtre de mesure) **ne sort plus jamais** — il reste le garde-fou interne (≥ 2× le filtre réaliste, sinon aucune phrase).
- **Filtres/chips** (Projets, fiche Marché, outils) : le chip « À suivre » filtre les 4 codes stockés de la tête (`codes_stockes()`, étendu côté serveur).

### Tests et verrous du lot 2

`tests/test_reparations1_lot2.py` (intégrité des 224 lectures contre le registre, graphe exact deux sens, palier non servi + réversibilité, phrase ×6,7 jamais ×13,3) ; 2 tests existants mis à jour au nouveau contrat (`test_recette10_backtest`, `test_m137_vocabulaire`) ; vitest **207/207**, tsc 0 ; pytest ciblé 112+50 passed (1 fail pré-existant documenté `test_r5`, fichier non touché — CIRCUIT-3). **Verrous : 23/23 « tout va bien », G6 avec dette 0.**

---

## LOT 3 — Les 24 sources partielles et les 13 en attente de partenariat

### Les 13 « non disponible — partenariat requis »

Nouveau statut de première classe **`partenariat_requis`** (enum + colonne élargie varchar(8)→24, migration idempotente dans `ensure_data_sources_millesime`) :

- **Appliqué aux 13** : les 10 « à demander » (Réunion Express 95, ZPPA 110, SAR 118, assainissement SIG 134, ZAE 135, ZAC 136, OPAH/PIG 137, ORT infra 138, ENS 139, OLL 140) + les 3 sous convention Cerema (Fichiers fonciers 27, LOVAC 141, DV3F 142). Base ET seed (`seed_sources.py`) — un re-seed ne revient pas en arrière.
- **Invisible client** : hors vitrine par construction (`WHERE_AFFICHEES`) — la page Sources passe de 95 à **92** lignes, LOVAC/DV3F/Fichiers fonciers n'y figurent plus (capture `lot3-01`).
- **Visible admin** : le détail du compteur liste les 13 avec la raison « **non disponible — partenariat requis** » (capture `lot3-02-admin-partenariat.png`).
- **Discipliné** : V2b exige le partenaire nommé en note (testé) ; G1 liste fermée étendue ; les notes existantes nomment déjà Région/EPCI/Département/Cerema. **Le courrier et la convention restent le geste de Vic** — rien n'est effacé, tout est conservé en base.

### Les 13 « couverture incomplète » — le trou est chez qui, et l'app le dit

Chaque source instruite (fiche d'audit + base) : verdict **chez nous (5)** — Potentiel foncier Région 15, DINUM 45, Office de l'eau 68, BD ORTHO IRC 69, LiDAR HD 70 — ou **chez le producteur (8)** — SUP 44, assainissement GPU 63 (4 communes sur 24 publient), DPU 107 (4/24 — « l'absence d'un périmètre publié ne veut pas dire pas de DPU »), PEB 108 (Pierrefonds non publié), zones humides 112, SIS 115, CBS 117, ACV/PVD/ORT 128.

**L'app le dit désormais** : nouvelle colonne servie `data_sources.couverture_note`, affichée sur la page Sources client sous chaque ligne (13 notes posées — capture `lot3-01-sources-couverture-dpu.png`). Détail par source : `LOT3-COUVERTURE.md`. Les réingestions « chez nous » NON faites sont écrites avec leur raison : 45/68/69 sont sous **retrait en attente** (mandats C1/C2/C4 — compléter avant l'arbitrage serait contradictoire), 15 attend l'arbitrage du doublon 9↔15 et sa licence, 70 a sa hauteur complète (303 452 parcelles ; le retard réel = verdict de toiture, batch dédié, mandat à part).

### Les 10 « champs manquants » — champ par champ, écrit

Les fiches d'audit disaient toutes « champs non pris : non vérifié » : l'instruction a **sondé les endpoints producteurs en direct** (ODS Région, WFS Géoplateforme, WFS Carmen DEAL) et comparé au schéma en base. **40 champs instruits : 21 utiles (dont 12 faisables en session, 5 mandats, 2 producteur) / 19 inutiles, chacun avec sa raison** — détail par source dans `LOT3-CHAMPS.md`. Trouvaille transverse : le **WFS Carmen DEAL répond** (la sentinelle le disait injoignable) et porte `ms:ENS` — le zonage ENS départemental que la fiche 25 croyait introuvable en open data.

**Non atteint dans ce mandat** (garde son rang dans REPARATIONS.md §E) : les 12 ingestions de champs « session » (chacune = ingérer + déclarer au registre + une place + un `i`) — la priorité du mandat allait aux lots 4 et 5 (« les lots 4 et 5 ingèrent ; ce qui est fait est ce qui compte le plus »). Rien n'est sauté : chaque champ a son verdict écrit.

### Tests et verrous du lot 3

`tests/test_reparations1_lot3.py` (invisible client, liste fermée, V2b exige le partenaire, colonne servie) ; 3 tests existants mis au nouveau contrat (liste fermée G1, décisions lot 7 remplacées par le mandat). tsc 0, vitest 207/207. **Verrous : 23/23 « tout va bien »** (V2a 92=92=92, G1 116 = 92 + 24).

---

## LOT 4 — RNB, l'identité des bâtiments

### L'ingestion (API officielle, jamais de scraping)

- **Endpoint réel** : `https://rnb-api.beta.gouv.fr/api/alpha/buildings/?insee_code=<insee>&limit=100` (pagination par curseur), une passe par commune — **filtrage 974 au plus tôt, côté API**. Module `src/labuse/ingestion/rnb.py`, CLI `labuse rnb --ingerer/--rattacher`.
- **Licence (textuelle)** : Licence Ouverte 2.0 (Etalab) — attribution « RNB — Référentiel National des Bâtiments » (beta.gouv / ADEME / IGN / DGALN). Réutilisation libre, y compris commerciale, avec mention.
- **CRS inspecté, pas supposé** : l'API sert du GeoJSON WGS84 et le flux diff écrit `SRID=4326` explicitement (constaté sur la réponse du 13/09/2026) → stocké en 4326 + `shape_2975` (RGR92/UTM 40S) pour le rattachement métrique.
- **Volume 974 / temps** : **414 081 bâtiments**, 24/24 communes, **~20 min** (pagination 100/page). Millésime : flux continu (pas de millésime nommé — ingéré par commune le 13/09/2026).
- **Ce qu'on prend** : `rnb_id`, statut, actif, point + emprise, adresses BAN liées, `ext_ids` BD TOPO (traçabilité). **Rien d'énergétique**, rien que BD TOPO ou le LiDAR servent déjà.

### Le rattachement — taux mesurés, non-rattachés par cause

Rattachement **spatial** (recouvrement d'emprises en 2975 — nos bâtiments BD TOPO locaux ne stockent pas leur cleabs ; l'`ext_id` RNB est gardé pour une passe exacte future) :

| Cible | Total | Rattachés | Taux | Non-rattachés, par cause |
|---|---|---|---|---|
| Bâtiments BD TOPO servis (`spatial_layers` kind=batiment) | 817 506 | 607 532 | **74,3 %** | 166 851 recouvrement < 30 % · 43 123 aucun RNB intersectant |
| Hauteurs LiDAR (`batiment_hauteur_lidar`, par parcelle) | 303 452 | 299 182 | **98,6 %** | 4 270 aucun bâti RNB sur la parcelle |

Le taux BD TOPO reflète l'écart de millésimes (notre BD TOPO WFS vs les emprises RNB) et les doublons frontaliers par commune — chaque non-rattaché porte sa cause en table (`rnb_rattachement_bdtopo`), rien n'est silencieux. **Trois sources parlent désormais du même bâtiment.**

### Où ça se voit, et le registre

- **Fiche parcelle « Ce qu'il y a dessus »** (tiroir Le bien) : bloc « Identifiant national du bâtiment (RNB) » — un identifiant discret par bâtiment, lien officiel `rnb.beta.gouv.fr/batiments/<id>`.
- **Registre complet** : source au catalogue (118ᵉ, Licence Ouverte, vitrine), réservoir `rnb` (tables déclarées), donnée `rnb_batiments_liste` (robinet `fiche_parcelle_le_bien`), **sentinelle** témoin double (2 bâtiments 974 figés ; le canal incrémental réel est `GET /buildings/diff/?since=` — documenté et outillé `version_diff()`), **filtre** (volume, géométries, 24 communes, inactifs jamais rattachés), G2 (remplissage mesuré par insee).
- G1 : la phrase du verrou ne grave plus « 116 » — elle porte le total mesuré. **Au passage, durci** : les arbitrages de doublons G1 vivaient en NOTES EN BASE seulement — un re-seed les écrasait (constaté : G1 recassé après seed). Ils sont désormais en CODE (`ARBITRAGES_DOUBLONS`, appliqués par `seed()`) — durable.

`tests/test_reparations1_lot4.py` (registre complet, cause écrite, rattachement spatial ≥ seuil, tiroir jamais cassé).

---

## LOT 5 — OCS GE, l'usage du sol et l'artificialisation

### Le téléchargement (IGN officiel) et les millésimes

- **Endpoint réel** : catalogue `https://data.geopf.fr/telechargement/resource/OCSGE` — produits départementaux D974 : **DEUX MILLÉSIMES** publiés (`OCS-GE_2-0__GPKG_RGR92UTM40S_D974_2017-01-01` et `…2022-01-01`, livraisons 2025-04) + le produit **DIFF artificialisation officiel** (`OCS-GE-ARTIFICIALISATION_2-0_DIFF-2017-2022_…D974_2025-09-16`). Archives 7z (73 + 77 Mo), md5 publiés.
- **Licence (textuelle)** : Licence Ouverte 2.0 (Etalab) — attribution « © IGN — OCS GE ».
- **CRS inspecté** : `gpkg_spatial_ref_sys` des trois GPKG déclare **2975 « RGR92 / UTM zone 40S »** (lu dans les fichiers, garde d'ingestion qui REFUSE un autre SRID) — chargé tel quel.
- **Volumes 974 / temps** : 2017 : **195 068** polygones · 2022 : **196 735** · évolution officielle : **10 633 zones** — ingestion **40 s** (`ingestion/ocsge.py`).

### L'artificialisation : la méthode officielle, dite

Le flag par polygone suit la **méthode du portail de l'artificialisation** (fiche indicateur, décret n° 2023-1096, étape 1 — affectation couverture × usage : anthropisé CS1.1.* sauf minéraux/extraction ; végétation non ligneuse CS2.2.* à usage résidentiel/mixte/secondaire/tertiaire/transport/transition/abandonné). Les étapes 2-3 (regroupement + seuils d'enclaves 2 500 m²) ne sont pas rejouées par parcelle — **dit à l'écran** ; le **changement** servi vient du produit DIFF officiel IGN (qui applique tout). **OCS GE ne nourrit pas le score** (affichage seul, conforme au mandat).

### Par parcelle, précalculé — et où ça se voit

- `parcel_ocsge` : part artificialisée, couverture + usage dominants (par aire), changement 2017→2022 (m² artificialisés / renaturés du produit officiel) — précalcul ensembliste à l'ingestion.
- **Couche carte « Artificialisation (OCS GE) »** : désactivée par défaut, rampe DISTINCTE (violine/rouge/vert), trois classes en légende — artificialisé 2022 dissous (pièces ≥ 2 500 m², le seuil réglementaire, dit dans le « i »), artificialisé 2017→2022, renaturé 2017→2022.
- **Fiche parcelle** : une ligne « Sol artificialisé : N % — d'après OCS GE 2022 » (donnée d'îlot, jamais la précision cadastrale).
- **Fiche commune / Étude de zone (ZAN)** : l'indicateur ZAN porte désormais, à côté du dérivé Cerema (ENAF), le bloc **OCS GE officiel** par commune (`zan_ocsge_commune` : artif 2017→2022 en ha, renaturé, part artificialisée — sur l'assiette cadastrale, dit). **La pression ZAN a sa source officielle.**
- **Dossier PDF** : la couche est nommée dans les libellés du Dossier.
- **L'étiquette qui mentait** : la couche « OCS GE (IGN) » servait BD CARTO V5 — son libellé dit désormais partout « Occupation du sol (BD CARTO V5 — grain grossier) », et la **vraie** OCS GE est une source distincte au catalogue (la 118ᵉ). BD CARTO redevient ce qu'elle est.
- **Registre** : source, réservoir `ocsge`, données (`part_artificialisee_pct`, `usage_sol_dominant`, `zan_evolution_commune`), robinets (le bien, couche, fiche commune ZAN), sentinelle (témoin sur les pages catalogue IGN des deux produits), filtre (deux millésimes pleins, géométries), raison V5c écrite (fiche + couche lisent le même précalcul).

### Les chiffres du précalcul, et les preuves

- `parcel_ocsge` : **431 663 parcelles** calculées en **349 s** (après réécriture : la première version à trois LATERAL tournait encore après 1 h et verrouillait `parcels` — annulée, dit dans le code). **306 145 parcelles majoritairement artificialisées** (≥ 50 %) — cohérent avec la définition du décret (les jardins résidentiels CS2.2.1×US5 sont artificialisés) ; **268 km² artificialisés sur l'assiette cadastrale (~10,7 % de l'île)**.
- Couche : **1 474 zones artificialisées dissoutes (≥ 2 500 m²) + 10 633 zones d'évolution officielles** ; `geom_simple` matérialisée (leçon RETOURS-14 appliquée : l'endpoint répond en 0,4 s au lieu de bloquer).
- **Captures** : fiche « Le bien » avec le bloc RNB (identifiant + lien officiel) ET la ligne « Sol artificialisé 100 % — d'après OCS GE 2022 » (`lot45-01-fiche-rnb-ocsge.png`) ; la couche « Artificialisation (OCS GE) » cochée, aplat violine sur la zone urbaine de Saint-Denis (`lot45-02-couche-artificialisation.png`).

`tests/test_reparations1_lot5.py` (matrice du décret, CRS refusé si ≠ 2975, registre complet, fiche jamais cassée). **Verrous après lots 4-5 : 23/23 « tout va bien »** (117 puis 118 sources, G1 à phrase dynamique).
