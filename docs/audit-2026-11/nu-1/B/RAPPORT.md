# AUDIT-NU-1 — Lot B : Fiche commune, carte, recherche

Branche `audit/nu-1-b` · worktree `~/Desktop/labuse-nu-b` · API 9060 · front 6260 · run servi **q_v20** · lecture seule (0 écriture base, 0 prod).
Date : 2026-10-31. Auditeur : développeur senior (foncier / urbanisme / fiscalité).

## Chiffres en tête

| | |
|---|---|
| **Scénarios joués** (API + navigateur Playwright) | **~35** sur 24 communes, 12 parcelles témoins, 2 communes contrastées (Saint-Denis / Cilaos), recalcul indépendant de 3 communes (Saint-Denis, Saint-Paul, Cilaos) — à froid puis à chaud |
| **Bloquant** | **0** |
| **Majeur** | **4** |
| **Mineur** | **10** |
| **Dette** | **10** |

**Verdict.** Comme au Lot A, **l'arithmétique élémentaire est juste** : tous mes recalculs indépendants depuis les tables sources tombent sur le chiffre servi, au m² et à l'unité près — logements 76 819 ✓, vacance 8,8 % ✓, mutations 12 m 1 323 ✓, prix neuf VEFA 4 889 vs 4 878 ✓, SRU 38,62 ✓, permis Saint-Paul 329/1 953 ✓, Cilaos logements 2 926 / vacants 325 ✓, zonage U/A/N/AU 308 989 / 74 166 / 36 458 / 10 707 ✓, médiane terrain nu reproduite (naïf 1 356 → dédupé 482, dédup correcte). **La console reste à 0 erreur / 0 warning** sur tout le parcours. Le danger n'est pas dans le calcul : il est dans **l'assemblage, les libellés et les périmètres** — un compteur qui annonce deux fois ce que la carte peint, un filtre « partition » qui laisse 41 % du cadastre dans un angle mort, deux chiffres du « neuf » côte à côte, et deux requêtes d'autocomplétion à 2,6 s / 4,5 s.

**Note exports (§4 du mandat).** Il n'existe **aucun PDF ni document propre à la fiche commune** : le contexte commune n'apparaît que dans une *section* du PDF de parcelle (`pdf_premium.py:505`) — c'est le périmètre du Lot A. Rien à exporter/relire ici.

---

## MAJEUR

### NU-B-001 — Le compteur « Voir les N parcelles » annonce deux fois ce que la carte peint
- **Gravité** : majeur.
- **Où** : panneau Filtres, bouton « Voir les N parcelles » ; carte. `FiltreLabuse.tsx:963-965` (texte bouton = `compte`), `app.py:3084` `/filtre` (compteur), `app.py:~3154` (liste d'IDU peinte).
- **Repro** : filtrer sur Cilaos (`/filtre?communes=Cilaos&source=q_v20&limit=0` → `compte:6576` ; `…&idus=1` → `nb_idus:3107`). En mode factuel (Analyse LABUSE **éteinte**, défaut), le compteur additionne la tranche `ecartee` (3 469 parcelles = étage 0 `status IN ('exclue','faux_positif_probable')`), mais la carte ne peint QUE le hors-étage-0 (`AND NOT _ETAGE0_SQL`).
- **Affiché vs juste** : bouton « Voir les **6 576** parcelles » → la carte en allume **3 107**. Écart = 3 469 (53 %). Recalcul SQL direct : total q_v19_sources Cilaos ≥ 2 m² = 6 576 ✓ ; hors étage 0 = 3 107 ✓. Les deux chiffres sont exacts — c'est le **même mot (« parcelles ») sur deux périmètres**.
- **Cause probable** : le compteur (`_q_v2_stats.total`) inclut l'étage 0 ; la liste d'IDU l'exclut par défaut (commentaires C-12 `app.py:3160-3179`). Choix documenté, mais invisible pour l'utilisateur.
- **Amélioration** : soit le bouton annonce le nombre **réellement peint** (hors étage 0), soit il scinde « 3 107 à instruire · 3 469 écartées ». Un client qui clique « 6 576 » et voit 3 107 pastilles croit à un bug de chargement et perd confiance dans tout le reste.

### NU-B-002 — « État du sol » (terrain nu / bâti) n'est PAS une partition : 41,5 % du cadastre dans un angle mort
- **Gravité** : majeur.
- **Où** : panneau Filtres, groupe « État du sol » (ChipGroup `partition`). `FiltreLabuse.tsx:814-816` + commentaire E3 `:811-814` ; prédicats `app.py:1826-1853` ; sérialisation `api.ts:105`.
- **Repro** : `/filtre?source=q_v20&limit=0` = **432 350** ; `…&etat_sol=nu` = **27 536** ; `…&etat_sol=bati` = **225 368** ; `…&etat_sol=nu,bati` = **252 904**. Or 27 536 + 225 368 = 252 904 ≠ 432 350 → **179 446 parcelles (41,5 %)** ne tombent dans aucun des deux seaux (aucune ligne `parcel_residuel` / `taux_emprise_pct` NULL).
- **Affiché vs juste** : le commentaire du code dit « nu + bâti **PARTITIONNENT** les parcelles » et l'UI coche tout par défaut (= « tout », 432 350, car `etatSol:[]` → param omis `api.ts:105`). Mais l'état « les deux cases explicitement cochées » envoie `nu,bati` = **252 904** — **visuellement identique au défaut, 179 446 parcelles de moins**. La partition est fausse de 41,5 %.
- **Cause probable** : les deux prédicats exigent `taux_emprise_pct IS NOT NULL` (CHASSE-DONNEES-FIX-1 `app.py:1838-1840`) ; les parcelles jamais mesurées sont exclues des DEUX côtés, mais l'UI les présente comme couvertes.
- **Amélioration** : ajouter un 3ᵉ état explicite « non mesuré » (ou compter les NULL dans « nu » tant que rien ne prouve le bâti), et faire que « tout coché » = base complète. Sinon un promoteur qui filtre « terrain nu » lit « 27 536 » comme la population des terrains nus de l'île alors que c'est un plancher amputé de 41 %.

### NU-B-003 — Deux prix « neuf » différents sur la même carte Prix (VEFA 4 878 « neuf » vs « Neuf observé » 4 275)
- **Gravité** : majeur.
- **Où** : fiche commune, carte « Prix ». Ligne résumée `ContextePanel.tsx:516` (`neuf {neuf_eur_m2}`) ; détail `:521` (« Prix VEFA commune ») et `:524` (« Neuf observé ≤ 3 ans après achèvement »). Sources : `comparable.neuf_eur_m2` = `neuf_vefa_commune` (VEFA à l'acte) ; `prix_neuf_observe` = `dvf_prix_sortie_neuf` (`fiche_commune.py:367`).
- **Repro** : Saint-Denis → carte Prix repliée affiche « ancien 2 469 · **neuf 4 878** €/m² » ; dépliée affiche « Prix VEFA commune **4 878** » ET « Neuf observé **4 275** ». Le comparateur des 24 communes sert aussi 4 878 (VEFA, `comparateur.py:62`) tandis que l'outil Marché sert `prix_sortie_neuf` = 4 275 (`/moteurs/marche/Saint-Denis`).
- **Affiché vs juste** : les deux chiffres sont exacts (VEFA recalculée 4 889 ≈ 4 878 ✓ ; sortie-neuf 4 275 ✓), mais **ce sont deux notions** (vente sur plan vs revente d'un neuf ≤ 3 ans) que l'app étiquette toutes deux « neuf » — 14 % d'écart. Le résumé en tête ne dit que « neuf 4 878 ».
- **Cause probable** : le libellé condensé `:516` appelle le VEFA « neuf » sans qualificatif, juste au-dessus d'un « Neuf observé » différent.
- **Amélioration** : étiqueter le résumé « neuf (VEFA sur plan) » et harmoniser le vocabulaire entre comparateur / fiche / outil Marché. Un acheteur qui compare le « neuf » d'une commune ne doit pas trouver 4 878 ici et 4 275 là sans explication.

### NU-B-004 — Omnibox : l'autocomplétion met 2,6 s sur un mot courant (« rue »)
- **Gravité** : majeur (chemin chaud, à chaque frappe).
- **Où** : `GET /api/recherche/suggest` ; SQL adresse `recherche.py:144-204` (match token-AND sur colonne étendue de `adresses`).
- **Repro (à chaud, 3 mesures)** : `?q=rue` = **2,60 / 2,72 / 2,59 s**. À l'inverse `?q=cheminvalmy` = 0,14 s, `?q=bellepierre` = 0,07 s, `?q=97411` = 0,015 s. La lenteur est systématique sur les **tokens courts très fréquents** (« rue », « saint »…) qui touchent un très grand nombre de lignes.
- **Affiché vs juste** : un utilisateur qui tape « rue … » (le mot le plus banal d'une adresse) attend ~2,6 s par rafraîchissement debounce — l'autocomplétion paraît cassée.
- **Cause probable** : pas de garde de sélectivité ni de plafond serveur sur les tokens à très forte cardinalité ; l'index ne discrimine pas « rue ».
- **Amélioration** : seuil de longueur/sélectivité (ignorer les stop-words type « rue/chemin » seuls), ou `LIMIT` serré avec tri indexé, ou trigram GIN sur la colonne étendue. Objectif < 300 ms, sinon le debounce de 200 ms ne sert à rien.

---

## MINEUR

### NU-B-005 — « PPR sur 72,2 % » divise par les parcelles disparues, pas par les 38 295 affichées
- **Gravité** : mineur.
- **Où** : carte Risques fiche commune ; chip Signaux. `fiche_commune.py:85,120` (`risques`) → `commune.py:127 pct_parcelles_couche('ppr')`, dénominateur `count(*) FROM parcels WHERE commune` ; en-tête « parcelles » = `commune.py:102` (filtre vivant).
- **Affiché vs juste** : UI « 72,2 % en PPR » = 27 849 / **38 557** (inclut 262 parcelles `cadastre_disparue`). Avec le dénominateur affiché en en-tête (38 295 vivantes) : 27 849 / 38 295 = **72,7 %**. Recalcul numérateur 27 849 ✓, dénominateurs 38 557 / 38 295 ✓.
- **Cause probable** : deux dénominateurs pour « nombre de parcelles » sur la même fiche.
- **Amélioration** : utiliser partout le compte vivant (`cadastre_disparue_le IS NULL`). Même écart se propage à « mouvement de terrain % » et au chip Signaux PPR.

### NU-B-006 — Omnibox : libellés cryptiques « 6 N 1 » et quasi-doublons quand on tape un nom de commune
- **Gravité** : mineur.
- **Où** : dropdown adresse ; label = `numero rep voie` seul `recherche.py:190`, match sur colonne étendue (qui inclut la commune).
- **Repro** : `?q=saint` → 4 items adresse « **6 N 1** », « **8 N 1** », « **10 N 1** », « 16 N 1 » (sub « 97410 Saint-Pierre »), dont deux pointant le même IDU `97416000CO0364`. La voie est « N 1 » (RN1) → le libellé paraît du code brut.
- **Affiché vs juste** : un utilisateur qui tape « saint » voit quatre stubs quasi identiques « N 1 » au lieu d'adresses lisibles (à comparer : « rue » et « le port » rendent des libellés propres — « 1 Rue Valmy », « Rue Jacquot », propriétaires).
- **Amélioration** : afficher « voie, commune » (ou dérouter les noms de commune vers la grammaire commune, désactivée dans l'en-tête) et dédoublonner par IDU.

### NU-B-007 — Code postal Saint-Leu figé à 97424 (code secondaire) au lieu de 97436
- **Gravité** : mineur.
- **Où** : table en dur `CP_COMMUNES` `FiltreLabuse.tsx:72` (`['97424', 'Saint-Leu']`), réutilisée par le sélecteur Fiche commune (`Header.tsx:79`) et les chips Filtres.
- **Affiché vs juste** : l'infobulle/chip affiche « 97424 — Saint-Leu ». 97424 est le CP d'une localité (Piton Saint-Leu) ; le CP **principal** de la commune est **97436**. Les 23 autres CP sont corrects.
- **Amélioration** : corriger la paire, ou lire le CP principal depuis le référentiel communes plutôt qu'une constante front.

### NU-B-008 — Le prix du terrain nu exclut « Vente terrain à bâtir » (1 310 ventes, la plus pertinente pour un promoteur)
- **Gravité** : mineur.
- **Où** : `marche_commune.py:ligne2_terrain_zone` — `WHERE m.nature_mutation = 'Vente'`.
- **Repro** : `dvf_mutations_parcelle` contient 1 310 mutations `nature_mutation = 'Vente terrain à bâtir'`, toutes écartées par le filtre strict `= 'Vente'`. Saint-Denis zone U : 1 254 « Vente » (médiane servie **482 €/m²**) ; en incluant les 33 « terrain à bâtir » de la zone → 1 287 ventes, médiane **468 €/m²** (−2,9 %).
- **Affiché vs juste** : impact numérique modéré ici, mais le sens est inversé : la transaction la plus représentative du « prix du terrain constructible » est exclue.
- **Amélioration** : inclure `'Vente terrain à bâtir'` (ou les servir en sous-ligne dédiée « terrain à bâtir »), tout en gardant l'exclusion VEFA/échange/adjudication/expropriation qui, elle, est correcte.

### NU-B-009 — `/map/couches-info` met 4,5 s (le « i » des couches)
- **Gravité** : mineur.
- **Où** : `app.py:7411 map_couches_info` (jointure `spatial_layers → data_sources`).
- **Repro (à chaud)** : 4,92 / 3,57 / 4,46 s. Alimente la ligne « source » du « i » de chaque couche.
- **Amélioration** : agréger/mettre en cache par `kind` (la liste est stable) ; 4,5 s pour une table d'infos quasi constante est injustifié.

### NU-B-010 — Deux légendes carte dans le même coin (chevauchement possible)
- **Gravité** : mineur.
- **Où** : `Legend.tsx` (verdict/zonage, `bottom-4 right-4`) et `TuyauLegend` (`CouchesTuyau.tsx:617`, `bottom-10 right-4`).
- **Affiché vs juste** : si une peinture verdict/zonage ET une couche tuyau sont actives, les deux boîtes se superposent bas-droite.
- **Amélioration** : une seule pile de légende, ou décalage dynamique.

### NU-B-011 — Textes « i » de couche avec comptes figés (« 305 objets », « 24 communes »)
- **Gravité** : mineur.
- **Où** : YAML `declarations/couches/*` et `tuyau_hors_registre.yaml:55,63` ; front `CouchesTuyau.tsx` (`construction_surfacique.i`, `limites_communes.i`).
- **Affiché vs juste** : le « i » annonce « 305 objets sur l'île » / « 24 communes » en dur — si la donnée bouge, le « i » ment sans alerte.
- **Amélioration** : dériver les comptes de la table (déjà lus par `couches-info`) plutôt que du texte.

### NU-B-012 — Dropdown omnibox : indicateur de chargement « … » au lieu des trois points verts
- **Gravité** : mineur (règle transversale Vic).
- **Où** : `AddressAutocomplete.tsx:226-227` (caractère `…`). Le reste de l'app utilise bien le composant `Chargement` 3 points menthe (`Loading.tsx`, vérifié conforme sur la carte « ● ● ● Carte… » et le bouton loupe).
- **Amélioration** : utiliser `<Chargement variant="inline" />` dans le dropdown.

### NU-B-013 — Un clic sur la carte n'alimente pas l'adresse dans l'omnibox d'en-tête
- **Gravité** : mineur (règle transversale Vic « clic carte met l'adresse dans la barre »).
- **Où** : les clics carte appellent `select(idu)` directement (`MapView.tsx:983,1060,1124`) ; l'omnibox d'en-tête ne reçoit pas de `seed` (contrairement aux `ParcelInput` des outils).
- **Affiché vs juste** : après un clic parcelle, la barre reste vide — la règle est tenue par les barres outils mais pas par l'omnibox d'en-tête.
- **Amélioration** : passer l'adresse résolue en `seed` de l'omnibox d'en-tête sur clic carte.

### NU-B-014 — `/map/permits.geojson` : fuseau non normalisé (date ±1 j), bbox ignoré, sans source/millésime
- **Gravité** : mineur.
- **Où** : `app.py:7976-7989`. `s.date.date().isoformat()` sans normalisation TZ ; seul `commune` filtre (le `bbox` de l'URL est ignoré → 50 075 features tirées d'un coup lors du test) ; aucun champ source/millésime dans le payload.
- **Amélioration** : normaliser la date en heure Réunion (cf. RADAR-COUVERTURE-1), honorer le bbox, porter la source dans le payload.

---

## DETTE

- **NU-B-015** — **Tendance 12 m par deux chemins** : la carte/bandeau lisent `delta_pct` via `/moteurs/marche` (`ContextePanel.tsx:319`), le chip Signaux « marché » recalcule `ligne4_tendance` serveur (`app.py:2602`) → si `/moteurs/marche` échoue, la carte montre « — » mais le chip peut encore afficher le %.
- **NU-B-016** — **Faits dupliqués** : population (pop légale vs repli Sudocuh, millésime plus ancien en silence, `fiche_commune.py:158-166`) ; loyer (OLL puis DHUP) ; `logements`/`vacants` portés à la fois par l'objet `marche` et l'objet `population` (même table `commune_insee_logement`, deux clés).
- **NU-B-017** — **Nombres dérivés côté client, jamais vérifiés serveur** : base SRU `round(nb_lls/(taux/100))` (`ContextePanel.tsx:494`), SDP résiduelle ha (`:639`), regroupement acquéreurs PM (`:177-184`), repli `autres_loges_pct` qui duplique le calcul serveur (`:472-473`).
- **NU-B-018** — **Cache `commune_contexte` peut servir périmé** : servi sans recalcul tant que la clé de fraîcheur `empreinte_attendue` n'a pas bougé (`app.py:2463`) ; un sous-ensemble est live-rafraîchi (comparable, SRU, fiscalité, zonage_abc, parc_social, prix_neuf_observe, permis_5a), le reste provient du gel nocturne.
- **NU-B-019** — **Omnibox « Entrée » sans sélection auto-choisit `owners[0]` / `parcelles[0]`** (`Header.tsx:164`, step 1) — contredit la doctrine du dropdown « ne jamais deviner pour l'utilisateur ».
- **NU-B-020** — **Omnibox « Entrée » : `.catch(() => [])`** sur chaque appel (`Header.tsx:133,147,163,178,183`) → un 500 backend est indistinguable d'« aucun résultat ».
- **NU-B-021** — **Cache tuiles périmé** : `/map/tiles/meta` → `perime:true`, `carte_le:2026-10-21` (bannière honnête « Carte pas à jour » affichée, vérifiée en direct) ; `/map/renouvellement.geojson` n'expose PAS de flag `perime` (le calque se vide en silence si le précalcul retarde).
- **NU-B-022** — **Slugs millésime IGN ortho en dur** (`ortho_proxy.py:52-61`, `ORTHO-EXPRESS.2025`…) → à la prochaine publication IGN, le fond « Actuelle » répond 404 en silence sans que le front distingue offshore / WMTS down / slug faux.
- **NU-B-023** — **« E-mail Absent » imprimé** (carte Identité mairie, `ContextePanel.tsx:431-443`) — tension avec la règle Vic « un champ vide ne s'imprime jamais » (ici « Absent » plutôt qu'omis ; honnête mais la ligne pourrait disparaître).
- **NU-B-024** — **Incohérences de nommage/largeur** : `CP_COMMUNES` porte « Les Trois-Bassins » quand `/communes` et la carte rendent « Trois-Bassins » (articles variables « Les/La/L' » entre table en dur et libellés carte) ; `mvt_tile_cache.layer varchar(32)` (`tiles.py:699`) casserait en silence un futur `kind` > 32 car.

---

## Les 5 trouvailles les plus graves du lot

1. **NU-B-001** — « Voir les 6 576 parcelles » → la carte en peint 3 107. Le compteur compte les écartées, la carte ne les peint pas : même mot, deux périmètres. C'est la fonction la plus visible du panneau Filtres, fausse d'un facteur 2.
2. **NU-B-002** — « État du sol » prétend partitionner (nu + bâti = tout) mais laisse **179 446 parcelles (41,5 %)** hors des deux seaux. Un promoteur qui filtre « terrain nu » lit un plancher amputé de 41 % comme s'il était la population complète.
3. **NU-B-003** — Deux « neuf » (VEFA 4 878 / observé 4 275, 14 % d'écart) étiquetés tous deux « neuf », sur la même carte et entre comparateur et outil Marché. L'acheteur ne peut pas réconcilier « le prix du neuf » d'une commune.
4. **NU-B-004** — L'autocomplétion met **2,6 s** sur « rue » (et « saint »), les tokens les plus fréquents d'une recherche d'adresse. Le debounce de 200 ms ne sert à rien devant une requête de 2,6 s.
5. **NU-B-005** — Le « 72,2 % en PPR » divise par 38 557 (parcelles disparues incluses) alors que la fiche affiche 38 295 juste au-dessus. Petit écart (72,2 → 72,7), mais c'est **deux dénominateurs pour "nombre de parcelles" sur une seule fiche** — le symptôme typique de l'assemblage.

## Ce que je changerais en premier si j'étais le développeur

**NU-B-001 et NU-B-002 d'abord**, parce qu'ils cassent le cœur du produit (« tout le foncier au même endroit, filtrable ») et qu'ils sont **silencieux ou trompeurs**, pas plantants. Concrètement :
1. **Un seul périmètre** pour le compteur, la liste et la carte. Le bouton annonce ce qui sera peint ; si l'on tient à montrer les écartées, on les nomme à part (« 3 107 à instruire · 3 469 écartées »). Un seul `_q_v2_stats` + une seule liste d'IDU, même gate `_ETAGE0_SQL`.
2. **Rendre « État du sol » honnête** : trois états (nu mesuré / bâti mesuré / non mesuré), « tout coché » = base complète, et retirer du code le commentaire « partitionnent » qui ne tient pas sur la donnée.
3. Ensuite **unifier le vocabulaire du "neuf"** (VEFA sur plan vs sortie-neuf observé) entre fiche, comparateur et outil Marché — un libellé, une définition, partout.
4. Puis **le point unique pour "nombre de parcelles"** (`cadastre_disparue_le IS NULL` partout) et **la perf de l'omnibox** (garde de sélectivité / trigram) — deux corrections ciblées à fort rendement.

La règle d'or confirmée par ce lot, comme par le Lot A : **le calcul est bon, c'est l'assemblage qui ment**. Chaque fois qu'un même fait vit à deux endroits (deux périmètres, deux dénominateurs, deux définitions du « neuf », deux chemins pour la tendance), un écart finit par s'afficher à un client qui paie 349 €/mois pour décider d'un achat.

---

### Hors lot (croisé, non instruit)

- **Radar en pause depuis le 06/10** : « biens en vente », « écart demandé/acté +23,9 % » et « dernier relevé » de la carte Activité comparent des annonces potentiellement anciennes à des ventes DVF (honnête via la date de relevé, mais à surveiller). Domaine Radar/Veille.
- **Score V2 / tiers** : le mode factuel expose la ventilation par tier (brûlante/chaude/…) dans le compteur Filtres — cohérence avec la doctrine « le scoring ne s'affiche que là où le client l'a demandé » à vérifier côté Lot transversal.
- **`etat_bien` sur base locale** : `parcel_residuel` absent pour 41,5 % des parcelles (cf. NU-B-002) — possible spécificité de la base Mac ; à reconfirmer en prod.

*Captures : `docs/audit-2026-11/nu-1/B/captures/` (non versionnées — `.gitignore **/captures/`). nub-01 accueil (3 points verts + bannière périmé), nub-02 fiche Saint-Denis, nub-03 panneau Filtres.*
