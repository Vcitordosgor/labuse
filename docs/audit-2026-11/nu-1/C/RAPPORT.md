# AUDIT-NU-1 — Lot C : Outils 1 à 8 — RAPPORT

**Périmètre.** PLU · Permis · Communes · Scan patrimoine · Assemblage · Comparer des parcelles · Remonter le temps · Étude de zone.
**Branche** `audit/nu-1-c` · worktree `~/Desktop/labuse-nu-c` · API 9070 · front 6270.
**Posture.** Lecture seule. Aucune écriture métier émise par l'auditeur : toutes mes requêtes de recalcul tournent en `SELECT`. L'API a servi normalement (les seules écritures base pendant l'audit sont ses propres caches locaux idempotents — `commune_contexte_cache`, `fiche_cache`, caches ortho). Aucun accès prod, aucun merge, aucun push.
**Base.** `labuse` locale (Mac), 44 Go, run servi `q_v20` (manifeste `mvt_meta.run_label` = q_v20 au 21/10/2026).

---

## Les cinq chiffres

| | |
|---|---|
| **Scénarios joués** | **41** (≈ 30 appels API sur 13 parcelles témoins + 2 communes contrastées, 12 recalculs SQL indépendants, 2 PDF lus au `pdftotext`, 3 outils pilotés au navigateur Playwright) |
| **Bloquant** | **0** |
| **Majeur** | **3** |
| **Mineur** | **6** |
| **Dette** | **7** |

**Verdict d'ensemble.** Le cœur chiffré du lot est **remarquablement juste**. Tous les nombres décisifs de **Communes** (prix ancien, terrain nu par zone, rareté/ZAN, permis, délais), de **Permis** (totaux, géocodage, < 200 m) et de **Scan patrimoine** (invariant parcelles) tombent **à l'euro / à l'unité** sur mon recalcul depuis les tables sources. Les ennuis sont ailleurs : une **métrique de constructibilité à deux moteurs** qui se contredisent selon l'outil ouvert (NU-C-001), une **étiquette fausse sur un PDF payant** (NU-C-002), et des **temps de réponse** qui dépassent 2 s sur des outils à usage répété (NU-C-003).

---

## Jeu de parcelles témoins

Voir `TEMOINS.md`. Couverture : nue zone U (Saint-Denis `97411000AB0332`), bâtie maison (`97411000AB0015`), copropriété 860 lots (`97411000ES0054`), zone N Cilaos (`97424000AB0001`, 28 ha), zone AU (`97402000AH1714`), PPR rouge R1 (`97411000CZ0077`), < 150 m² (`97411000AB0018`), > 1 ha (`97411000CZ0021`, 206 ha), RNU Saint-Philippe (`97417000AE0010`), multi-bâti 79 emprises (`97411000CE1095`), DVF récente 31/12/2025 (`97411000HI0215`), disparue du cadastre (`97411000DT0120`), U Cilaos (`97424000AC0139`).

---

# Trouvailles

## NU-C-001 — MAJEUR — La « SDP constructible » d'une parcelle a deux moteurs qui divergent de 1,6× à 9× selon l'outil

**Où.** Comparer des parcelles · Assemblage · (recoupe la fiche parcelle et l'Étude de faisabilité — hors lot).

**Reproduction.**
1. Fiche de `97411000DH0203` (`GET /parcels/…`) → affiche « **SDP résiduelle 433 m²** — petit collectif / 2-4 lots » (ligne socle) ; `potentiel_transformation.sdp_residuelle_m2 = 419`.
2. `GET /compare?idus=…97411000DH0203…` → **deux lignes** : « SDP résiduelle, bâti conservé = 433 » **et** « SDP maximale réglementaire, terrain libéré = **732** ».
3. `POST /moteurs/assemblage {idus:[…DH0203…]}` → `sdp_max_seule_m2` et `items[].sdp_m2` = **732** ; c'est ce 732 qui sert de base « si on construit seul » au calcul de gain d'assemblage.

**Affiché vs juste (recalcul indépendant).** Les deux nombres viennent de deux chaînes distinctes :
- le **précalcul** `parcel_residuel.sdp_residuelle_m2` (servi par la fiche et la ligne « SDP résiduelle » de Comparer) ;
- le **moteur de faisabilité live** `faisabilite.db.fiche_payload → fourchette.surface_plancher_m2` (servi par la ligne « SDP max terrain libéré » de Comparer et la base d'Assemblage).

J'ai appelé directement les deux moteurs sur 8 parcelles U de Saint-Denis :

| IDU | `parcel_residuel` (fiche) | `fourchette` moteur (Assemblage) | ratio |
|---|---|---|---|
| 97411000AB0007 | 671 | *(moteur renvoie None)* | — |
| 97411000AB0015 | 152 | 325 | ×2,14 |
| 97411000AB0016 | 166 | 311 | ×1,87 |
| 97411000AB0025 | 103 | 443 | ×4,30 |
| 97411000AB0044 | 194 | 378 | ×1,95 |
| 97411000AB0045 | 203 | 507 | ×2,50 |
| 97411000AB0046 | 122 | 1116 | ×9,15 |
| 97411000AB0048 | 337 | 547 | ×1,62 |

Les deux grandeurs modélisent en partie des scénarios différents (garder le bâti vs raser) — Comparer a raison de les distinguer en deux lignes. **Mais** : (a) l'écart (jusqu'à ×9) dépasse la seule différence raser/garder et montre deux modèles non réconciliés ; (b) la **fiche** ne montre JAMAIS le grand nombre (terrain libéré) → un acheteur qui lit « 433 m² » sous-évalue le potentiel de redéveloppement jusqu'à 2×, ce qui est précisément le chiffre qui intéresse un promoteur ; (c) **Assemblage** ne montre QUE le grand nombre et ne dit nulle part que son « seul » suppose la démolition — l'utilisateur qui compare la base d'Assemblage (732) à la fiche (433) voit une contradiction non expliquée.

**Capture / preuve.** `comparatif.pdf` (lignes « SDP maximale réglementaire, terrain libéré » 325/732/879 vs « SDP résiduelle, bâti conservé » 161/433/841) ; tableau de recalcul ci-dessus.

**Cause probable.** `src/labuse/assemblage.py:255-266` (`aggregate_assiette` lit `fiche_payload().fourchette.surface_plancher_m2`) vs la fiche servie qui lit `parcel_residuel` ; les deux portent le mot « SDP » sans réconciliation. Le run de cascade lu par ces chemins est `q_v19` alors que le servi est `q_v20` (voir Hors lot).

**Proposition.** Sur Assemblage et dans toute vue qui affiche une « SDP seule », étiqueter explicitement l'hypothèse (« terrain libéré — démolition supposée ») et afficher aussi, comme Comparer, la variante « bâti conservé » ; à terme, faire du moteur de faisabilité la source unique et recalculer `parcel_residuel` avec lui pour que la fiche et les outils parlent du même chiffre.

---

## NU-C-002 — MAJEUR — Le PDF « Étude de zone » affiche « Revenu médian » là où c'est une moyenne, et contredit l'écran

**Où.** Étude de zone → bouton Exporter en PDF (`GET /etude-zone.pdf`).

**Reproduction.** `GET /etude-zone.pdf?idu=97411000AB0332&rayon_km=1` → section Population : « **Revenu médian  22 215 € (estimé)** ». L'écran, pour la même zone, affiche « **niveau de vie moyen / an** » (`22 215 €`).

**Affiché vs juste.** La valeur est calculée `round(sum(ind_snv) / NULLIF(sum(ind),0))` — c'est le **niveau de vie moyen par individu** (somme des niveaux de vie ÷ population), **ni une médiane ni un revenu**. Le libellé PDF est donc **doublement faux** (ce n'est pas médian, ce n'est pas un revenu) **et** il contredit l'écran, qui, lui, est honnête. Recalcul : `sum(ind_snv)/sum(ind)` sur les 30 carreaux Filosofi dont le centroïde tombe dans le cercle de 1 km = **22 215 €**, identique au servi (le *nombre* est bon, c'est l'*étiquette* qui ment).

**Capture / preuve.** `pdftotext` de `etudezone.pdf` (ligne « Revenu médian 22 215 € (estimé) ») vs snapshot écran (`EtudeZone.tsx:243` « niveau de vie moyen »).

**Cause probable.** `src/labuse/exports/blocs/etude_zone.py:40` — `_kv("Revenu médian", …)` ; l'alias SQL `revenu_median_eur` est lui-même trompeur (`src/labuse/zone.py:171`).

**Proposition.** Remplacer le libellé PDF par « Niveau de vie moyen / an » (aligné sur l'écran) et renommer l'alias SQL `revenu_median_eur` → `niveau_vie_moyen_eur` pour couper la source de confusion. Un chiffre juste sous une fausse étiquette reste un mensonge pour un client qui facture ses décisions dessus.

---

## NU-C-003 — MAJEUR — Temps de réponse : Étude de zone > 5 s à CHAQUE usage, fiche commune 6–18 s à froid, simulplu 22–60 s

**Où.** Étude de zone · Communes (fiche contexte) · PLU (endpoint simulplu, voir NU-C-004).

**Mesures (à froid puis à chaud, `curl -w %{time_total}`).**
- `POST /outils/etude-zone` (rayon 1 km, Saint-Denis) : **6,57 s à froid, 5,51 s à chaud** — aucun cache (sauf l'isochrone) : chaque ouverture repaie le plein calcul (nombreux `ST_Union`/`ST_Intersects` sur `spatial_layers`). Le PDF (`/etude-zone.pdf`) ré-appelle l'endpoint → **8,0 s**. Cilaos : 5,68 s.
- `GET /communes/{commune}/contexte` : **18,72 s à froid** (Saint-Denis), 6,74 s (Cilaos), puis **0,15 s à chaud** (table `commune_contexte_cache`). Le cache est vidé à chaque déploiement → la **première** visite de chaque commune après un déploiement coûte 6–18 s à un client.
- `GET /communes` : 3,48 s à froid (mémo 300 s) · fiche d'une parcelle > 1 ha : 5,84 s · fiche multi-bâti (79 emprises) : 2,88 s.

**Affiché vs juste.** Rien d'erroné dans les valeurs ; c'est de la latence. Aucune de ces requêtes ne devrait dépasser 2 s pour un outil à usage répété.

**Cause probable.** Étude de zone n'a pas de cache de résultat (`src/labuse/api/app.py:7218` + `src/labuse/zone.py` — recalcul intégral à chaque appel). Le contexte commune n'est caché qu'après le premier calcul et le cache est invalidé globalement au déploiement.

**Proposition.** Mettre en cache le résultat d'Étude de zone par (parcelle/point, rayon) comme pour l'isochrone, et pré-chauffer `commune_contexte_cache` pour les 24 communes à la fin du `deploy_app.sh` (le calcul est déterministe) plutôt que de le laisser se reconstruire sur le dos du premier client.

---

## NU-C-004 — MINEUR — PLU : le simulateur d'ouverture (`simulplu`) est débranché mais reste un endpoint vivant, lent (22–60 s) et faux pour tout code de zone

**Où.** PLU — endpoint `GET /moteurs/simulplu` (ancien composant `ProcedureChangement`).

**Reproduction.** `GET /moteurs/simulplu?zone=UAVAP&commune=Saint-Denis` → **22,5 s** (même à chaud) et renvoie `n_parcelles=0, bascules=0, sdp_totale=0` alors que Saint-Denis compte **1 590** parcelles UAVAP ≥ 300 m². `zone=U` → **timeout > 60 s**.

**Affiché vs juste.** La cascade ne stocke dans `detail` que la **famille** (« Zone PLU « U » (urbaine…) »), jamais le code précis ; or la requête filtre `cr.detail ILIKE '%« UAVAP »%'` → 0 pour tout code spécifique (UAVAP, UB, UC… = justement les seules valeurs que `/moteurs/simulplu/zones` offre). Le `LIKE`/`ILIKE` sur la colonne texte `detail` non indexée de 458 k lignes de cascade explique les 22–60 s.

**Atténuation.** Le composant est **volontairement non câblé** : `Plu.tsx:5-11` indique que la voie « Procédure & changement » a été supprimée (décision Vic : « le simulateur d'ouverture est une ANALOGIE, pas une information fiable »). L'outil PLU vivant = l'Annuaire seul (sain, voir plus bas). L'endpoint reste néanmoins atteignable par URL (réponse 60 s = risque ressource latent).

**Cause probable.** `src/labuse/api/moteurs.py:84-114` (requêtes `ILIKE` sur `dryrun_cascade_results.detail`).

**Proposition.** Retirer la route (ou la faire répondre 410) puisque l'UI ne l'ouvre plus, ou la réécrire sur `parcel_zone_plu.zone_lib` (indexé) au lieu du texte de cascade. Un endpoint mort qui répond en 60 s est une porte ouverte sur la charge serveur.

---

## NU-C-005 — MINEUR — Remonter le temps : 18 erreurs 404 en console à l'ouverture (tuiles ortho mer/no-data)

**Où.** Remonter le temps (comparateur ortho).

**Reproduction.** Ouvrir l'outil (vue île par défaut) → console : **18 erreurs** « Failed to load resource: 404 » sur `/map/tiles/ortho/1950/{z}/{x}/{y}` et `/map/tiles/ortho/express/{z}/{x}/{y}` (z 10-12). Après sélection d'une parcelle (zoom sur terre), l'imagerie se charge correctement (1950-1965 + Ortho Express 2025) et le compteur **n'augmente pas** — les 404 sont donc les tuiles de la vue large.

**Affiché vs juste.** Fonctionnellement l'imagerie est bonne sur terre (vérifié : IGN renvoie bien la tuile, `data.geopf.fr` joignable 200). Le proxy renvoie **404 par design** pour les tuiles entièrement en mer / no-data (`ortho_proxy.py:240-256`, pour afficher l'aplat bleu). Mais chaque 404 remonte comme **erreur console**, ce qui viole la règle « console à zéro » du mandat et masquerait de vraies erreurs.

**Cause probable.** `src/labuse/api/ortho_proxy.py:242/250/252/256` (HTTPException 404 pour tuile mer/absente) + maplibre qui journalise chaque tuile raster en échec.

**Proposition.** Pour les tuiles mer/no-data connues, répondre **204 No Content** (ou un PNG transparent 1×1) plutôt que 404 : le fond reste l'aplat, et la console reste propre.

---

## NU-C-006 — MINEUR — Permis : « 100 % géolocalisés » affiché alors que 2 permis sur 437 n'ont pas de position

**Où.** Permis (compteur de géocodage).

**Reproduction.** `GET /modules/permis?commune=Saint-Denis&months=24` → `total=437, geocodes=435, sans_localisation=2, pct_geocode=100`.

**Affiché vs juste.** Recalcul exact depuis `sitadel_permits` (fenêtre `dmax-24m`) : 437 / 435 / 2 — identiques. Le taux réel = 435/437 = **99,54 %**, arrondi à `round()` → **100 %**. L'écran dit donc « 100 % » tout en annonçant « 2 sans localisation » : contradiction d'un pouce.

**Cause probable.** `src/labuse/api/modules.py:648` — `round(100 * geocodes_total / true_total)` sans garde pour ne pas afficher 100 quand il reste des non-localisés.

**Proposition.** Plafonner l'affichage à 99 % tant que `sans_localisation > 0` (ou afficher une décimale : « 99,5 % »). Un « 100 % » faux érode la confiance sur le reste du tableau.

---

## NU-C-007 — MINEUR — Communes : deux « prix du neuf » coexistent (VEFA 4 878 €/m² vs neuf observé 4 275 €/m²)

**Où.** Communes — tableau comparateur (colonne « €/m² VEFA ») vs fiche commune (carte « prix du neuf observé ») ; les deux présents dans `GET /communes/{commune}/contexte`.

**Reproduction.** Saint-Denis : `comparable.neuf_eur_m2 = 4878` (comparateur, libellé « €/m² VEFA ») et `prix_neuf_observe.eur_m2 = 4275` (fiche, « neuf observé », n=77). `moteurs/marche/Saint-Denis` sert aussi 4275.

**Affiché vs juste.** Deux notions réellement distinctes (VEFA à l'acte, ventes sur plan, vs neuf observé = reventes ≤ 3 ans après achèvement) — pas une erreur de calcul. Le tableau les disambiguë bien par un tooltip explicite (« À NE PAS confondre avec l'ancien, ni avec le prix de sortie servi au bilan de la fiche »). Reste qu'un client voit deux « prix du neuf » à ~600 €/m² d'écart pour la même commune.

**Cause probable.** Deux sources : `commune.py:24` (`prix_neuf` = VEFA DVF) et `fiche_commune.py:367` (`prix_neuf_observe` = table `dvf_prix_sortie_neuf`).

**Proposition.** Nommer les deux colonnes de façon auto-portante partout (« Neuf sur plan (VEFA) » vs « Neuf revendu (≤ 3 ans) ») sans compter sur le survol, pour qu'un lecteur pressé ne les confonde pas.

---

## NU-C-008 — MINEUR — Fiche d'une parcelle disparue du cadastre : HTTP 500 (table absente) — impacte le clic-carte vers les outils

**Où.** Transversal, mais déclenché en testant le témoin « disparue du cadastre » `97411000DT0120` (clic-carte → fiche → ponts outils).

**Reproduction.** `GET /parcels/97411000DT0120` → **500 Internal Server Error**.

**Affiché vs juste.** Trace : `psycopg.errors.UndefinedTable: relation "parcel_cadastre_remplacement" does not exist`. **Réserve base locale** : la table existe probablement en prod (même famille que le constat CHASSE-4 C4-004) ; à confirmer sur la prod. Mais même avec la table présente, une parcelle disparue ne devrait pas pouvoir faire tomber la fiche en 500 non géré.

**Cause probable.** Requête `FROM parcel_cadastre_remplacement …` dans le chemin fiche sans garde `to_regclass`.

**Proposition.** Entourer la lecture `parcel_cadastre_remplacement` d'un garde d'existence (comme `parcel_blocs`/`etablissement_parcelle` ailleurs) et dégrader proprement (« parcelle retirée du cadastre le … ») au lieu d'un 500.

---

## NU-C-009 — MINEUR — Deep-link `#m=temps` (et autres) ignoré quand un overlay d'outil est déjà ouvert

**Où.** Navigation entre outils.

**Reproduction.** Communes ouvert avec l'overlay « Les 24 communes » affiché → naviguer vers `#m=temps` → l'overlay Communes reste affiché, Remonter le temps ne s'ouvre pas. Il faut d'abord fermer, puis passer par le menu Outils.

**Affiché vs juste.** La règle « changer d'outil vide tout » n'est pas honorée par le deep-link quand un overlay modal est présent. Par le menu Outils, le changement fonctionne correctement (Retour unique « ← Outils » vérifié, état vidé).

**Cause probable.** Le routeur de hash (App.tsx) ne force pas la fermeture des overlays plein écran (CommunesTablePanel) sur changement de `m=`.

**Proposition.** Sur changement de module par hash, fermer tout overlay ouvert avant de monter le nouveau module.

---

## Dette (à ranger, non bloquant)

- **NU-C-D1 — Permis, deux ancres de temps.** « Récent » est ancré sur `:dmax` (fin de flux, `modules.py:530`) tandis que « dormant » est ancré sur `now()` (`modules.py:539`). Le compteur « Autre » est une soustraction côté front (`tous − récent − dormant − achevé`) : si les fenêtres ne s'alignent pas, « Autre » absorbe silencieusement l'écart. Unifier sur `:dmax`.
- **NU-C-D2 — Alias SQL `revenu_median_eur`** (Étude de zone, `zone.py:171`) porte une moyenne ; commentaires contradictoires `EtudeZone.tsx:237` (« revenu médian… pas une estimation ») vs `:239` (« niveau de vie MOYEN… l'alias est trompeur »). Renommer, nettoyer le commentaire mort. (Cf. NU-C-002.)
- **NU-C-D3 — Assemblage `surface_totale_m2`** somme les surfaces **dessin** (geom) et non les contenances cadastrales : paire AB0332+AB0333 = 735 (536+199) alors que la fiche sert la contenance (539 pour AB0332). Écart de quelques m² par parcelle, mais « un fait, une valeur » : aligner sur la contenance comme la fiche.
- **NU-C-D4 — `HistoireFrise` importé mais jamais rendu** dans `App.tsx` (frise de faits datés retirée) ; `/moteurs/histoire/{idu}` reste vivant et **sans LIMIT** sur ventes/permis/propriétaires (`moteurs.py:425-481`). Retirer le code mort et borner la requête si l'endpoint survit.
- **NU-C-D5 — `moduleMap` tronqué à 4000 idus** silencieusement sur la couche carte (`MapView.tsx:1645`) : un assemblage/patrimoine très large afficherait moins de parcelles que le compteur ne l'annonce, sans le dire. `log()`/afficher le plafond.
- **NU-C-D6 — Caches partagés non invalidés au déploiement.** Comparer et Assemblage lisent `_FICHE_CACHE` (`app.py:8914`, TTL ~1 h) ; constat déjà noté côté `fiche_cache` (CORRECTIFS-2). Vérifier que le `deploy_app.sh` vide bien ces caches mémoire/table au changement de `code_sha`.
- **NU-C-D7 — Libellés de carte sans article** (« Avirons », « Trois-Bassins », « Étang-Salé », « Plaine-des-Palmistes ») sur les pastilles communes de la carte, alors que le nom officiel porte l'article. Cosmétique, mais incohérent avec le tableau Communes qui écrit « Les Avirons », « L'Étang-Salé ».

---

## Hors lot (croisé, non instruit)

- **Fiche parcelle — « SDP résiduelle » à deux valeurs internes.** Pour `97411000DH0203` la fiche sert **419** (`potentiel_transformation.sdp_residuelle_m2`, = vue `parcel_residuel`) **et 433** (`analyse_labuse.sdp_residuelle_m2`, ligne socle « SDP résiduelle 433 m² », et `renouvellement.sdp_residuelle_m2`). Deux nombres pour le même mot dans la même fiche — à instruire par le lot qui porte la fiche. (Alimente NU-C-001.)
- **Run de cascade en retard.** `dryrun_cascade_results` ne contient que `q_v18`/`q_v19` ; le run servi est `q_v20`. Les chemins qui lisent la cascade (simulplu, dormants permis) travaillent donc sur `q_v19`. Le bandeau carte affiche d'ailleurs « Carte pas à jour — elle affiche encore l'ancien run (reconstruction des tuiles en attente) » (probable état de reconstruction de la base locale, à confirmer en prod).
- **Notifications / cloche** affichent « 99+ » (badge) — transversal (lot F).
- **Table `parcel_cadastre_remplacement` absente** en base locale (cf. NU-C-008) — à vérifier côté prod.

---

# Les cinq trouvailles les plus graves

1. **NU-C-001** — Deux moteurs de « SDP constructible » qui divergent de 1,6× à 9× : la fiche montre le petit nombre (bâti conservé), Assemblage le grand (terrain libéré), sans réconciliation ni signalisation. Un acheteur lit un potentiel différent selon l'outil ouvert.
2. **NU-C-002** — Le PDF Étude de zone étiquette une **moyenne** « Revenu médian », contredit l'écran, et c'est un livrable payant.
3. **NU-C-003** — Étude de zone > 5 s à chaque usage (aucun cache de résultat) et fiche commune 6–18 s à froid après chaque déploiement.
4. **NU-C-004** — `simulplu` : endpoint mort mais vivant, 22–60 s, et renvoie 0 pour tout code de zone précis (la cascade ne stocke que la famille).
5. **NU-C-005** — Remonter le temps crache 18 erreurs 404 en console (tuiles mer renvoyées en 404 au lieu de 204).

# Ce que je changerais en premier (si j'étais le développeur)

**D'abord NU-C-001.** C'est le seul qui touche directement une décision d'achat : la constructibilité est le nerf du produit, et aujourd'hui elle dit deux choses selon la porte d'entrée. Je ferais du moteur de faisabilité la **source unique** (un seul `surface_plancher_m2`, deux scénarios explicitement nommés « bâti conservé » / « terrain libéré » servis **partout** — fiche, Comparer, Assemblage, Étude), et je recalculerais `parcel_residuel` avec ce moteur pour que la fiche cesse de sous-vendre le potentiel. Dans la foulée : la correction d'étiquette NU-C-002 (une heure de travail, gros gain de crédibilité) et un cache de résultat sur Étude de zone (NU-C-003).

**À noter pour la bonne nouvelle :** l'ossature chiffrée de Communes/Permis/Patrimoine est solide — médiane DVF ancien (2 469 €/m² Saint-Denis), terrain nu par zone (482/328), rareté/ZAN (horizon 1,1 an), permis 24 mois (437/435), scan patrimoine (2 618 parcelles) : tous recalculés à l'identique. Le lot ne souffre pas de ses nombres, il souffre de ses **doublons de source** et de ses **étiquettes**.
