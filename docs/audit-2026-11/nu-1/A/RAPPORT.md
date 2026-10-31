# MANDAT AUDIT-NU-1 — Lot A : Fiche parcelle et ses exports

**Registre.** Audit LECTURE SEULE joué le 2026-10-31. Branche `audit/nu-1-a`, worktree `~/Desktop/labuse-nu-a`, API 9050 (venv PDF-capable, `PYTHONPATH` du worktree), front 6250 (`vite`, `npm ci` réel), run servi `q_v20`, base Mac `labuse` (434 582 parcelles, == prod données). Aucune écriture base, aucun merge, aucun accès prod.

> Note d'intendance : le fichier `~/Downloads/AUDIT-NU-1-A.md` était d'abord absent (seul le Lot F s'y trouvait) ; le bon mandat a été re-téléchargé avant de commencer. Rien n'a été audité hors du périmètre Lot A.
>
> Captures : `docs/audit-2026-11/nu-1/A/captures/fiche-maison-marche.png` est présente sur le disque mais **non versionnée** — le dépôt ignore `**/captures/` (politique MENAGE-1, binaires hors git) ; je n'ai pas forcé l'ajout pour respecter cette règle.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Scénarios joués** | **~60** : 12 parcelles témoins (fiche API froid+chaud), 9 familles de chiffres recalculées indépendamment depuis les tables sources sur les 11 parcelles servables, 6 exports générés + lus (`pdftotext`/`unzip`), 5 parcours navigateur (accueil → fiche maison → tiroirs Marché/Potentiel → fiche multi-bâti), 2 communes contrastées (Saint-Denis, Cilaos), + Salazie/Saint-Philippe. |
| **Bloquant** | **3** |
| **Majeur** | **10** |
| **Mineur** | **6** |
| **Dette** | **6** |

**Verdict de synthèse.** Les chiffres *élémentaires* sont, pris un à un, remarquablement justes : surface géométrique (11/11 = `ST_Area`), emprise au sol (union BD TOPO, proxy fidèle de R.420-1), part d'aléa (11/11 au millième), taux REI (au centime), forfaits taxe d'aménagement 2026, hauteurs LiDAR (au décimètre). **Le danger n'est pas dans l'arithmétique, il est dans l'assemblage** : deux sources de vérité pour un même fait (SDP, surface, prix, compteur de risques), une sélection qui masque (aléas, prix par type), un verdict déduit là où la doctrine exige une mesure (hauteur sur `nb_batiments=0`, pente moyenne vs falaise), et des scories de scoring/dates qui fuient vers un client à 349 €/mois.

---

## Les 12 parcelles témoins

| rôle | IDU | commune | note |
|---|---|---|---|
| nue zone U | 97411000IN0347 | Saint-Denis | 941 m², U, sans bâti |
| bâtie maison | 97411000IE0241 | Saint-Denis | 625 m² (contenance), maison DVF 2024 205 k€ — **parcelle de référence** |
| copropriété | 97411000HC0139 | Saint-Denis | 346 m², RNIC 16 lots |
| zone A/N | 97424000AE0050 | Cilaos | N, 1 720 m² |
| zone AU | 97424000AM0893 | Cilaos | AUb, 465 m² |
| PPR / aléa fort | 97421000AB0133 | Salazie | PPR rouge 15 % + bleue 21 %, inondation/mouvement fort |
| très petite < 150 m² | 97411000AO0753 | Saint-Denis | 149 m², U |
| très grande > 1 ha | 97411000EY0173 | Saint-Denis | 10 024 m², U, pente max 43,9° |
| RNU / sans PLU | 97417000BI0076 | Saint-Philippe | 5 730 m², sans zone opposable |
| plusieurs bâtiments | 97411000AB0785 | Saint-Denis | 1 846 m², 11 bâtiments |
| vente DVF récente | 97411000HN0074 | Saint-Denis | maison, vente 2025, 260 k€ |
| disparue du cadastre | 97411000DR0042 | Saint-Denis | 89 m², disparue 2026-09-01 |

Méthode : chaque chiffre servi par `GET /parcels/{idu}?source=q_v20` (builder `_q_v2_fiche`, `src/labuse/api/app.py:4434`) a été recalculé depuis les tables sources (PostGIS, SRID 2975) et comparé. Exports générés par leurs routes réelles. Parcours navigateur réel (Playwright).

---

## Trouvailles

### NU-A-001 — BLOQUANT — La SDP résiduelle se contredit elle-même sur la même fiche

- **Où** : tuile d'en-tête « SDP RESTANTE » et tiroir « Potentiel » ← `potentiel_transformation.sdp_residuelle_m2` (table `parcel_residuel`, servie LIVE, `app.py:6459/6481`) ; carte verdict « Demander à LABUSE » ← `analyse_labuse.sdp_residuelle_m2` (table `score_labuse`, run `q_v20`, `app.py:6968`, rendue par `AnalyseLabuseCard.tsx`).
- **Repro** : ouvrir `97411000AB0785` (multi-bâti). L'en-tête affiche **« SDP RESTANTE 850 m² »** et le tiroir **« Potentiel R+2 · calcul tracé · 850 m² SDP »**. Cliquer « Demander à LABUSE » : la carte verdict liste **« aucune SDP résiduelle exploitable »** + « bâti existant sur 71 % de la parcelle — démolition à prévoir ».
- **Affiché vs juste** : les deux valeurs viennent de deux tables calculées à **trois mois d'écart** — `parcel_residuel.computed_at = 2026-07-29`, `score_labuse` q_v20 `computed_at = 2026-10-21` — jamais réalignées. Recalcul sur les 5 témoins servables :

  | témoin | en-tête (parcel_residuel) | verdict LABUSE (score_labuse q_v20) | écart |
  |---|---|---|---|
  | multi_bati | **850** | **0** | 850 m² |
  | bâtie maison | **0** | **92** | 92 m² (sens inverse) |
  | copro | 0 | 84 | 84 m² |
  | grande | 444 | 461 | 17 m² |
  | zone_AU | 69 | 73 | 4 m² |

  L'écart change de sens selon la parcelle → ce ne sont pas deux notions différentes, ce sont deux instantanés désynchronisés du **même** calcul. Le commentaire `app.py:6515-6517` affirme explicitement « plus de contradiction intra-fiche » : l'invariant est violé sur **tous** les témoins servables.
- **Capture** : `captures/fiche-maison-marche.png` (tuile SDP) ; valeurs vérifiées depuis les payloads `/tmp/nu1a/fiche_*.json`.
- **Cause probable** : `parcel_residuel` est recalculée en place (non figée au run), `score_labuse` est figée au run q_v20 ; aucun des deux ne lit l'autre ; aucun contrôle de cohérence au build.
- **Amélioration** : servir UNE seule source de SDP sur toute la fiche (lire `score_labuse` du run servi partout, ou recalculer `parcel_residuel` dans la même passe que `score_labuse`). Ajouter une assertion de build « `potentiel_transformation.sdp == analyse_labuse.sdp` pour le run servi » qui casse la CI si l'écart dépasse l'arrondi.

### NU-A-002 — BLOQUANT — « Prix ancien médian » = un €/m² d'APPARTEMENT servi sur une MAISON

- **Où** : `sector_price` / `base_plans`, `src/labuse/faisabilite/bilan.py:271-274` ; servi en tête via `app.py:4758` (`DVF_BANQUIER_ADAPTATIF`) et `marche_service.py:120` ; imprimé dans le **Dossier PDF** (ligne « Prix ancien médian »).
- **Repro** : générer le Dossier de `97411000IE0241` (maison, dernière vente DVF 205 k€ en « Maison »). Le PDF imprime en tête de la section marché : **« Prix ancien médian 2 225 €/m² (76 ventes à moins de 500 m) »** — or « 76 ventes » est le comptage **appartement**. Plus bas dans le **même** PDF : « Maison 3 286 €/m² ». Le chiffre mis en avant est le prix de l'appartement.
- **Affiché vs juste** : 2 225 €/m² (appartement) au lieu de ~3 286 €/m² (maison du secteur) — **−32 %** sur un bien bâti maison, sur le document payant phare qui sert une décision d'achat. `base_plans` n'essaie que `appartement` → `mixte (appart+maison)` → commune ; **aucun plan maison-seule n'existe**. Le module a été conçu comme « prix de sortie d'un collectif neuf » (commentaire l.270) mais est câblé en tête générique de toute fiche. (Écho direct de l'audit [ESTIMATION-BANC-1] : « maison au prix d'appartement ».)
- **Nuance honnête** : le *tiroir* « Marché » de l'écran, lui, détaille correctement les trois types (Terrain nu 347 · **Maison 3 286** · Appartement 2 225) — le danger est le **chiffre unique** mis en avant (Dossier + champ `prix_ancien` consommé en aval par Copilote/Bilan), pas le tiroir.
- **Cause probable** : `bilan.py:271-274` — absence de plan `("maison",{"maison"},r,False)` prioritaire quand la nature de la parcelle est « bâti maison » (l'info `etat_bien` est déjà dans `head`, `app.py:4450`).
- **Amélioration** : ajouter au `base_plans` un plan maison-seule prioritaire selon `etat_bien`, et étiqueter honnêtement le type servi — ne jamais présenter un €/m² appartement comme « prix ancien médian » d'une maison.

### NU-A-003 — BLOQUANT — La fiche d'une parcelle disparue du cadastre renvoie HTTP 500

- **Où** : `info_disparue`, `src/labuse/cadastre_disparue.py:44-56`.
- **Repro** : `GET /parcels/97411000DR0042?source=q_v20` → **500 Internal Server Error** (idem 97416000CW2846, 97415000CX1355, 97409000AV0547 — testés). Trace : `psycopg.errors.UndefinedTable: relation "parcel_cadastre_remplacement" does not exist`.
- **Affiché vs juste** : une parcelle disparue doit servir une **fiche de courtoisie** (« Parcelle disparue du cadastre… », cf. l'intention écrite en tête de `cadastre_disparue.py`). Elle plante. Le garde est **asymétrique** : `colonne_presente()` vérifie bien que la colonne `parcels.cadastre_disparue_le` existe avant de l'interroger, mais la requête des parcelles de remplacement tape `parcel_cadastre_remplacement` **sans vérifier que la table existe**. 1 353 parcelles sont marquées disparues ; toutes tombent en 500 sur cette base.
- **Caveat** : la table existe peut-être en prod (elle est référencée comme table légitime, `flux_sens.py:31`). Mais `readyz` ne la liste pas dans le schéma requis (`missing: []`) : la prod est à **une erreur d'ordre d'ingestion** de voir toutes ses fiches disparues tomber en 500. Le marqueur colonne et la table de remplacement ne sont pas garantis posés ensemble.
- **Cause probable** : `cadastre_disparue.py:49` interroge la table sans le même `information_schema` guard que la colonne.
- **Amélioration** : protéger la requête de remplacement par un test d'existence de table (comme la colonne), repli « aucune remplaçante connue » si absente ; ajouter `parcel_cadastre_remplacement` à la liste des tables surveillées par `readyz`/doctor. Une disparue doit servir la courtoisie, jamais un 500.

### NU-A-004 — MAJEUR — Le badge « sources discordantes » compare l'égout LiDAR au faîtage BD TOPO (donc ne se déclenche jamais sur un immeuble)

- **Où** : `discordance_hauteur`, `src/labuse/faisabilite/hauteur_lidar.py:240-253` ; seuil `SEUIL_ECART_EGOUT_BDTOPO_M = 15.0` (ligne 213).
- **Repro** : copro `97411000HC0139` — LiDAR faîtage 13,7 m, LiDAR égout 4,0 m (p25), BD TOPO déclaré 15,2 m. Le code calcule `ecart_egout = 4,0 − 15,2 = −11,2`, teste `|−11,2| > 15` → faux → `hauteur_discordante = False`.
- **Affiché vs juste** : la fiche affiche un écart égout↔BD TOPO de −11,2 m **sans alerte**. Or BD TOPO 15,2 est manifestement le **faîtage** (il concorde avec le faîtage LiDAR 13,7 à 1,5 m près) ; on compare une gouttière à un faîte → mismatch garanti, jamais signalé. La vraie vérification (faîtage LiDAR ↔ hauteur BD TOPO, écart réel −1,5 m, cohérent) n'est jamais faite.
- **Cause probable** : le commentaire du code (`bati.py:368`) postule « BD TOPO ≈ égout », faux pour tout bâtiment R+2 et plus.
- **Amélioration** : comparer la **même** grandeur (faîtage LiDAR ↔ hauteur BD TOPO, champ `ecart_faitage_bdtopo_m` déjà disponible) ; n'exposer l'écart égout que comme info annexe non comparée au BD TOPO.

### NU-A-005 — MAJEUR — Une hauteur « mesurée / sourcée » est affichée là où la fiche déclare `nb_batiments = 0`

- **Où** : `hauteur_parcelle_lidar` prend le plus grand bâtiment intersectant sans seuil de surface (`hauteur_lidar.py:81-91`) ; `nb_batiments` compte les polygones ≥ 10 m² (`bati.py stats_batch`). Les deux ne sont pas réconciliés.
- **Repro** : petite `97411000AO0753` — 3 bâtiments BD TOPO intersectent (chacun < 10 m²) → `nb_batiments = 0`, mais une ligne `batiment_hauteur_lidar` existe (faîtage 4,1 m, 347 cellules) → la fiche sert `hauteur_bati_m = 4,1`, `hauteur_nature = "sourcé"`, source « LiDAR HD MNS (IGN), mesuré ».
- **Affiché vs juste** : le client lit simultanément « aucun bâtiment » et « hauteur mesurée 4,1 m ». La doctrine Vic « jamais un verdict déduit là où la doctrine demande une mesure » est inversée : une mesure est servie là où le produit déclare l'absence de bâti (bruit de sol / débord voisin).
- **Amélioration** : conditionner l'affichage de la hauteur LiDAR à `nb_batiments > 0` (ou à une emprise bâtie ≥ seuil) ; si mesure LiDAR mais `nb = 0`, le dire (« micro-emprise, bâti non significatif ») plutôt que « mesuré » net.

### NU-A-006 — MAJEUR — `pente_bande` classe la pente MOYENNE seule : une falaise à 43,9° est étiquetée « modérée »

- **Où** : `_pente_bande`, `src/labuse/api/app.py:4422-4431` (prend `pente_moy_deg`), appelé `app.py:4821` ; la tuile « Pente » n'affiche que la moyenne.
- **Repro** : grande `97411000EY0173` — `pente_moy = 14,9°` → bande « modérée » (seuil < 15°), alors que `pente_max = 43,9°` et `flag_terrassement_lourd = True`. Idem PPR `97421000AB0133` (max 33,1°, « modérée »), zone_AN `97424000AE0050` (max 25,4°, « modérée »).
- **Affiché vs juste** : « pente modérée » sous-vend un terrain qui comporte des pans à 44° — danger constructibilité/terrassement/mouvement de terrain pour un acheteur. Au-delà de ~30 % (≈ 16,7°) la construction exige des fondations spéciales ; les PPR mouvement de terrain traitent les pentes fortes. La valeur `pente_moy` elle-même est juste (11/11 = `parcel_terrain`), c'est l'**étiquette** qui trompe.
- **Amélioration** : dériver `pente_bande` d'une règle à deux entrées (moy ET max) ou ajouter un sur-badge « pente localement forte (max X°) » dès `pente_max_deg ≥ 25-30`. `flag_terrassement_lourd` existe déjà et était `True` sur ces trois cas — il devrait remonter dans la bande.

### NU-A-007 — MAJEUR — Aléas : seul le niveau le plus fort par type est gardé → « fort ~3 % » masque une exposition totale

- **Où** : `servitudes.py:298-316` (`best[typ]` ne garde que le `_NIVEAU_RANK` max par type d'aléa).
- **Repro / recalcul** : Salazie `97421000AB0133` — servi « Aléa mouvement de terrain — fort ~3 % ». Réel (recalcul `ST_Intersection` / `ST_Area`) : mouvement **fort 3 % + moyen 33 % + faible 64 % = 100 % de la parcelle**. RNU `97417000BI0076` : servi « fort 38 % » ; réel fort 38 + moyen 62 = **100 %**. Zone_AN `97424000AE0050` : servi « fort 14 % » ; réel fort 14 + moyen 86 = **100 %**.
- **Affiché vs juste** : « ~3 % » se lit « 97 % sûr » pour un acheteur, alors que la parcelle est intégralement exposée au mouvement de terrain. Les niveaux moyen/faible sont jetés sans trace.
- **Amélioration** : conserver (ou résumer) chaque bande de niveau par type — « fort 3 % · moyen 33 % · faible 64 % → 100 % exposé » — au lieu du seul plus fort sliver ; ne jamais laisser croire que la surface non montrée est sans risque.

### NU-A-008 — MAJEUR — Aucun aléa n'est jamais rédhibitoire ; une zone rouge PPR < 50 % n'est pas signalée inconstructible

- **Où** : `servitudes.py:322` (`redhibitoire: False` codé en dur pour tout aléa Géorisques, quel que soit le niveau) ; `servitudes.py:278-288` (zone rouge `red = True` seulement si `pct ≥ 50`).
- **Repro** : Salazie — `niveau = "fort"` + PPR rouge 15 % → tous `redhibitoire = false`. Grande `97411000EY0173` — **24 % de PPR zone rouge** → `red = False`.
- **Affiché vs juste** : sous le **C. env. L562-1**, une zone rouge PPR est une zone d'**interdiction de construire** — la surface rouge est inconstructible, qu'elle couvre 15 %, 24 % ou 60 %. Traiter < 50 % comme non-rédhibitoire est défendable *pour la parcelle entière* (il peut rester du constructible), mais le libellé actuel se lit comme une réassurance sur une emprise légalement interdite.
- **Amélioration** : garder le %, mais énoncer clairement « surface en zone rouge = inconstructible (interdiction, règlement PPR) » et lever un drapeau parcelle « partiellement inconstructible » dès que rouge > 0, indépendamment du seuil 50 %.

### NU-A-009 — MAJEUR — Le scoring brut (rang 122 462, percentile 71,5) fuit vers le client sur chaque fiche

- **Où** : `frontend/src/components/fiche/ScoreV2Block.tsx:116-119`, monté sans condition en `Fiche.tsx:1207` (`<ScoreV2Block idu={idu} />`), auto-fetch `GET /v2/score/{idu}` (`src/labuse/api/score_v2.py:112-128`).
- **Repro** : `GET /v2/score/97411000IE0241` → `{percentile: 71.51, rang: 122462, mult_base: 1.07}` ; la carte rend littéralement « percentile 71.5 » et « rang 122462 » sur une maison « sans signal ».
- **Affiché vs juste** : l'en-tête *inline* masque délibérément ces mêmes nombres derrière `montreMultiple = tier ∈ {priorite, a_suivre}` (`Fiche.tsx:633, 1124`) — l'équipe a donc **déjà décidé** que le rang brut ne doit pas s'afficher pour « sans signal » / « écartée ». `ScoreV2Block`, monté trois lignes plus bas, **contourne ce garde** et montre rang+percentile pour tous les paliers. Doctrine Vic « le scoring ne s'affiche que là où le client l'a demandé » violée ; fausse précision pour une parcelle non actionnable. Les valeurs elles-mêmes sont justes (cohérence fiche↔`parcel_p_score_v2` : 11/11 MATCH, `rang_total 429799` vérifié, percentile = dense-rank cohérent).
- **Amélioration** : garder `percentile`/`rang` dans `ScoreV2Block` derrière la même condition que l'inline (passer un prop `montreRang` depuis `Fiche`), en conservant la fraction + « pourquoi » + réglette verbale qui sont, eux, destinés au client.

### NU-A-010 — MAJEUR — « Surface libre » ignore COSIA (465 m² « libres » sur une parcelle imperméabilisée à 30 %)

- **Où** : `src/labuse/bati.py:284` — `surface_libre = contenance − emprise_BDTOPO`.
- **Repro** : zone_AU `97424000AM0893` — `le_bien` sert `emprise = 0`, `surface_libre_m2 = 465` (= 100 % de la contenance), alors que `cosia_detecte_m2 = 143` et `cosia_couverture.part_impermeabilisee_pct = 30,4 %`.
- **Affiché vs juste** : « 465 m² libres (100 %) » sur une parcelle que COSIA dit imperméabilisée à 30 %. Quand BD TOPO = 0, la parcelle paraît totalement constructible alors que du bâti révélé non cartographié existe.
- **Amélioration** : quand `cosia_detecte_m2 > emprise_bdtopo`, calculer `surface_libre` sur `max(emprise_bdtopo, cosia)` et signaler « bâti révélé non cartographié déduit » ; ne jamais présenter 100 % libre sous COSIA ≥ 30 %.

### NU-A-011 — MAJEUR — Le compteur « RISQUES » diverge selon l'endroit : tuile 3 / section 2 / PDF « 1 relevé »

- **Où** : tuile d'en-tête `Fiche.tsx:945` (`lines[onglet='risques' & result∈{SOFT_FLAG,HARD_EXCLUDE}]` = 3 : risques, bassin_versant, sup) ; section « Risques et environnement » `risques.tsx:30-32` (retire `bassin_versant` → 2) ; Dossier PDF (tuile « 1 relevé » = `aleas.n`).
- **Repro** : fiche `97411000IE0241` — tuile en-tête « **3 vigilances** », badge section « **2 vigilances** », Dossier PDF « **1 relevé** ». Trois nombres pour le même fait sur la même parcelle.
- **Affiché vs juste** : le sommaire (tuile) doit égaler le détail (section) et le PDF (règles Vic : un fait = une valeur partout ; PDF == écran). Le « doublon assumé » (sommaire vs section) est légitime **tant que le nombre est le même** — ici il ne l'est pas.
- **Amélioration** : une source unique pour « N vigilances » (par ex. le compte de la section, bassin_versant inclus ou exclu mais partout pareil), consommée par la tuile ET le PDF.

### NU-A-012 — MAJEUR — « Prix ANCIEN » inclut les ventes VEFA (neuf)

- **Où** : `_ventes_bati_dedup`, `src/labuse/faisabilite/bilan.py:218-246` (`nature_mutation ILIKE '%vente%'` capte « Vente en l'état futur d'achèvement »).
- **Repro** : copro `97411000HC0139` — en-tête « Prix **ancien** médian 2 443 €/m² » mais `comparables.n_vefa = 21`, `mediane_vefa = 5 660` : ces 21 VEFA sont **dans** l'échantillon. Ancien-seul = 2 396 ; le champ `comparables.mediane_ancien` (2 413) **contredit déjà** l'en-tête (2 443).
- **Affiché vs juste** : la doc DVF data.gouv distingue explicitement la VEFA (bien non encore construit, neuf) ; elle ne doit jamais entrer dans une médiane dite « ancien ».
- **Amélioration** : exclure `vefa` du calcul servi comme « ancien » (le flag `vefa` est déjà calculé l.227/243), ou renommer « prix bâti médian (ancien + neuf) ». S'aligner sur le bloc `comparables` qui sépare déjà les deux.

### NU-A-013 — MAJEUR — Loyers OLL « non disponible » sur toutes les fiches alors que la donnée existe

- **Où** : `oll_parcelle`, `src/labuse/ingestion/oll_loyers.py:186-195` — jointure `z.iris = right(coalesce(sl.attrs->>'code_iris', sl.name), 4)`.
- **Repro** : les 10 témoins servables → `loyers_oll.disponible = false`. Or `oll_loyers` (133 lignes) et `oll_zonage` (193) sont peuplés (millésime 2024). La jointure échoue car `spatial_layers.attrs->>'code_iris'` est vide et le repli `right(sl.name, 4)` prend 4 lettres d'un nom libre (« …XXIII » → « IIII »), jamais un code IRIS.
- **Affiché vs juste** : « Loyers OLL non disponible » partout vs un loyer médian €/m² réellement présent — fonctionnalité morte.
- **Caveat** : possiblement spécifique à cette base Mac (IRIS ingérés sans `code_iris`) — à confirmer sur prod.
- **Amélioration** : alimenter `attrs->>'code_iris'` à l'ingestion IRIS, ou joindre `oll_zonage` sur le code IRIS dérivé de l'INSEE plutôt que sur un `name` texte libre.

### NU-A-014 — MINEUR (majeur sur le RNU) — Comparateur et Gabarit affichent le dessin, la fiche la contenance

- **Où** : `ComparePanel.tsx:61`, `GabaritLine.tsx:74`, `Gabarit.tsx:272` lisent le `surface_m2` brut (dessin `ST_Area`) ; la fiche (`Fiche.tsx:965` via `surfaceTerrain()`) affiche la contenance cadastrale.
- **Repro** : la liste d'autocomplétion de l'omnibox montre « IE 241 — Saint-Denis **630 m²** » pendant que la tuile SURFACE de la fiche montre **625 m²** (même parcelle, deux surfaces simultanées à l'écran). RNU `97417000BI0076` : fiche **5 730 m²**, comparateur **5 955 m²** (+225 m² / **+3,9 %**).
- **Affiché vs juste** : la doctrine `surface.ts:8` (« plus personne ne lit `p.surface_m2` ») est violée en 3 endroits ; la contenance (acte) est la vérité servie dans la fiche.
- **Amélioration** : router ces 3 sites par `surfaceTerrain()` comme la fiche, ou servir `surface_terrain_m2` dans leurs payloads et retirer le `surface_m2` brut.

### NU-A-015 — MINEUR — `nb_batiments` : deux méthodes de comptage, seuil non dit

- **Où** : `nb_batiments` = polygones ≥ 10 m² (`bati.py stats_batch`), tandis que l'emprise est l'union de **tous** les intersectants.
- **Repro** : copro `97411000HC0139` — « 1 bâtiment · 169 m² » sur une copro de 346 m² (4 polygones unis) ; nue_U « 4 bâtiments » pour 10 polygones intersectants.
- **Affiché vs juste** : « 1 bâtiment » sous-compte pour une copro ; le client qui compare au cadastre/photo croit à une erreur. Le seuil 10 m² est raisonnable mais muet.
- **Amélioration** : libeller « N bâtiments ≥ 10 m² (BD TOPO) », ou servir la même base géométrique pour le compte et l'emprise.

### NU-A-016 — MINEUR — `dvf.prix_m2_terrain` = valeur ÷ max(surface_terrain) : choix arbitraire sur mutations multi-parcelles

- **Où** : vue `v_parcel_dvf_last`, CTE `terrain_parcelle`, `src/labuse/ingestion/dvf_marche.py:51-53` (`max(COALESCE(surface_terrain,0))`).
- **Repro** : `97409000AC0102` (mutation 2025) porte deux `surface_terrain` pour la même parcelle (323 et 1240) → la vue prend 1240 → terrain 202 €/m² ; avec 323 → 774 €/m² (×3,8). **1 292 parcelles (3,3 %)** ont des surfaces terrain conflictuelles > 20 % dans une même mutation.
- **Affiché vs juste** : `max()` minimise systématiquement le €/m² terrain affiché (dénominateur le plus grand).
- **Amélioration** : afficher l'incertitude quand min ≠ max, ou dénommer sur la contenance cadastrale réelle (`parcels.contenance_m2`).

### NU-A-017 — MINEUR — Un aléa < 1 % est arrondi à 0 puis supprimé sans trace

- **Où** : `servitudes.py:262/302` (`round(...)::int`) puis `:271/:310` (`if pct <= 0: continue`).
- **Repro** : latent (0 ligne entre 0 et 0,5 % sur les 7 parcelles testées) — mais sur une grande parcelle, 0,4 % de « fort » = plusieurs centaines de m² de risque qui disparaissent.
- **Amélioration** : garder une décimale (`round(.,1)`) ou afficher « < 1 % » au lieu de jeter ; filtrer sur une aire absolue (m²) plutôt que sur un pourcentage arrondi.

### NU-A-018 — MINEUR — Écran vs PDF : les comptages de ventes du secteur divergent

- **Où** : écran tiroir Marché (rayon adaptatif 500 m) vs Dossier PDF section « Le secteur » (secteur cadastral 2021-2025) — deux calculs sous les mêmes libellés.
- **Repro** : `97411000IE0241` — écran « Maison 3 286 €/m² · 23 ventes », « Appartement 2 225 €/m² · 76 ventes » ; PDF « Maison 3 286 · 25 ventes », « Appartement 2 035 · 13 ventes ». Le prix maison concorde mais le comptage non ; le prix appartement diverge (2 225 vs 2 035).
- **Affiché vs juste** : deux périmètres portant le même nom de ligne (« Maison », « Appartement ») sans dire lequel — le lecteur croit à une incohérence.
- **Amélioration** : nommer le périmètre dans chaque ligne (« < 500 m » vs « secteur cadastral ») et aligner écran/PDF sur la même définition par ligne.

### NU-A-019 — MINEUR — Le millésime des aléas Géorisques = un maximum global (mauvaise commune)

- **Où** : `servitudes.py:263-265 & 303-305` — PPR et Géorisques lisent `ds.source_millesime` de la même `data_source` ; les 1 093 couches `georisque_alea` + 164 `ppr` partagent une ligne unique `source_millesime = "PPR le plus récent approuvé le 2026-04-16"`.
- **Repro** : Salazie `97421000AB0133` — les lignes inondation/mouvement affichent « millésime PPR … 2026-04-16 » tandis que la citation PPR de la même fiche (`ppr[].approbation`, `app.py:5292`) dit correctement **2019-08-01** (PPR de Salazie). Deux dates contradictoires sur le même risque ; 2026-04-16 est le MAX global tous PPR confondus, et une carte d'aléa Géorisques n'est de toute façon pas un PPR.
- **Amélioration** : étiqueter les aléas Géorisques avec leur édition Géorisques, et les lignes PPR avec l'approbation de la commune (déjà calculée par `_ppr_reference_commune`) plutôt que le max global.

### NU-A-020 — DETTE — « SDP constructible restante » n'est pas une surface de plancher R.111-22

- **Où** : `residuel.py:207` (`sdp = emprise × niveaux × coef`) ; la règle `regles/sdp_residuelle_m2.py` cite R.111-22 mais admet dans son champ `ecart` qu'elle ne fait aucune des 8 déductions R.111-22 ni l'abattement 10 % habitation.
- **Affiché vs juste** : l'en-tête vend une « SDP constructible restante » (terme juridique) alors que c'est une enveloppe (emprise × niveaux), en général sur-estimée. C'est tagué « estimé » (honnête) mais le mot « SDP » est juridiquement fort.
- **Amélioration** : renommer « enveloppe constructible estimée » et sortir la réserve R.111-22 en clair dans la fiche, pas seulement dans le registre de règles.

### NU-A-021 — DETTE — Le régime ZFANG standard cite le mauvais décret

- **Où** : `territoire_fiscal.py:30, 50-51` — le libellé ZFANG **standard** porte `source_ref = "Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18)"`, qui ne régit que la liste **renforcée** (CIREST). Le régime 50 % standard relève de l'art. 44 quaterdecies CGI.
- **Amélioration** : donner au libellé standard sa propre `source_ref` (art. 44 quaterdecies CGI) et réserver le décret 2026 au renforcé. (Tous les taux REI et forfaits taxe d'aménagement 2026 sont, eux, justes au centime — vérifiés sur les 4 communes témoins.)

### NU-A-022 — DETTE — Le barème taxe d'aménagement (YAML) échappe au drapeau « périmé »

- **Où** : `taxe_amenagement.py:29` (`_PERIME_JOURS`) garde le *taux communal* (DB) mais pas les forfaits du `config/taxe_amenagement.yaml` (892 €/m² 2026).
- **Amélioration** : contrôler `meta.annee` du YAML vs l'année courante et lever un drapeau « barème à rafraîchir », comme pour les taux REI.

### NU-A-023 — DETTE — Une médiane fragile (n = 9, volatilité 95 %) servie comme « Prix ancien médian »

- **Où** : `marche_service.py:117-121` — zone_AN `97424000AE0050` sert un médian « mixte » n = 9 à 1 579 €/m² étiqueté `fiabilite = "fragile"` (honnête) mais toujours affiché comme « Prix ancien médian ».
- **Amélioration** : seuil plancher (ne rien servir sous n minimal) plutôt que servir un médian fragile qu'un client peut prendre pour référence.

### NU-A-024 — DETTE — Deux jeux de pente en base (degrés vs pourcent) — piège d'unité

- **Où** : `parcel_terrain.pente_*_deg` (source servie, RGE ALTI 5 m) coexiste avec `spatial_layers kind='pente'` (`slope_pct` en **pourcent**, grille grossière). La fiche lit bien `parcel_terrain` (11/11 MATCH), mais la couche vectorielle dormante en % pourrait être prise pour des degrés par un futur consommateur.
- **Amélioration** : documenter `parcel_terrain` comme source unique de pente ; annoter `slope_pct` pour éviter la confusion deg/%.

### NU-A-025 — DETTE / PERF — Exports lents

- **Mesuré** : Dossier PDF **8,5 s à froid / 2,4 s à chaud** (> 2 s même chaud) ; **Pré-dossier PC (ZIP CERFA) 31,9 s** ; Apporteur 1,8 s / 1,5 s. Les endpoints de la fiche elle-même sont tous < 1,1 s (fiche cachée), aléas en lecture brute 664 ms (mitigé par `tuyau_subdivise` ~30 ms).
- **Amélioration** : profiler la chaîne Dossier (WeasyPrint + endpoints) ; pour le Pré-dossier, paralléliser la génération des pièces CERFA/plans ou streamer le ZIP pièce par pièce — 32 s est hors budget d'attente d'un clic.

---

## Exports du lot — couverture

| Export (bouton fiche) | Route | État observé |
|---|---|---|
| Dossier expert | `GET /dossier/{idu}.pdf` | **200**, 10 p., formats FR OK, aucun champ vide / code brut / troncature — mais porte NU-A-002 (prix) et NU-A-011 (compteur risques) ; lent (NU-A-025). |
| Banquier | `GET /dossier-banquier/{idu}.pdf` → **308** → `/financier` | route consolidée (EXPORTS-2). |
| Argumentaire | `GET /argumentaire/{idu}.pdf` → **308** → `/financier` | route consolidée. |
| Financier (Bilan) | `GET /financier/{idu}.pdf` | **422** honnête (`document_non_etablissable`) sur parcelle bâti-saturée : « programme constructible » + « régime de TVA » manquants. Nécessite une saisie de projet (POST) → non généré (lecture seule). |
| Apporteur | `GET /apporteur/{idu}.pdf` | **200**, 4 p., propre. |
| Pré-dossier PC | `GET /pre-dossier/{idu}.zip` | **200**, 8 pièces (CERFA 13406 pré-rempli, PCMI1/2/4/7-8, règles-zonage, enveloppe-réglementaire, LISEZMOI) ; 31,9 s (NU-A-025). |
| Courrier | `POST /courrier/*` | mutation (envoi) → non exercé en lecture seule. |
| Remonter le temps | — | hors chiffres du lot (parcellaire historique). |

La « lettre de zonage » du mandat correspond à la pièce `…-regles-zonage.pdf` du Pré-dossier PC (générée, présente dans le ZIP).

---

## Ce qui est sain (à décharge)

- **Surface terrain** : 11/11 = `ST_Area(geom_2975)` ; contenance = acte, bien distinguée ; repli « dessin » masqué sous 1 % d'écart.
- **Emprise au sol** : union BD TOPO, proxy fidèle de R.420-1 (6/6 MATCH).
- **Part d'aléa** : arithmétique exacte (SRID 2975, union, ratio jamais > 100), 11/11 au millième.
- **Fiscalité** : tous les taux REI au centime (4 communes), forfaits taxe d'aménagement 2026 corrects (892 €/m² hors-IdF, départemental 2,5 %), ZFANG renforcé/standard et FRR « en partie » honnêtes.
- **Hauteurs LiDAR** : valeurs servies = table source au décimètre (dates de survol exactes, pas de risque TZ, borne ≤ 0 / > 60 m appliquée).
- **Score** : cohérence fiche ↔ `parcel_p_score_v2` 11/11 ; drapeau copro propre (régression CHASSE-4 C4-003 **non** réapparue : 0 parcelle RNIC avec `copro=false` à l'échelle de l'île).
- **DVF** : médiane/quartiles/trim 5 %/dédup par mutation exacts (copro MATCH à l'euro) ; la vente propre de la parcelle servie sur la bonne surface ; pas de double-comptage bâti.
- **Transversales Vic** : aucun défilement horizontal (viewport 1200, `scrollWidth` 1200) ; changer de parcelle via l'omnibox vide bien l'état ; contrôles groupés à 28/32/36 px (charte) ; **console 0 erreur / 0 warning** sur le parcours (les 10 erreurs 403 fontes initiales étaient un artefact du symlink `node_modules` de l'audit, corrigé par `npm ci` réel — **pas** un défaut produit).

---

## Les 5 trouvailles les plus graves

1. **NU-A-001** — la SDP résiduelle se contredit sur la même fiche (en-tête « 850 m² » vs verdict LABUSE « aucune SDP exploitable »). Le cœur de la proposition de valeur — la constructibilité — n'a pas de vérité unique.
2. **NU-A-002** — le « Prix ancien médian » du Dossier payant est un €/m² d'appartement servi sur une maison (−32 %), et se contredit dans le même PDF. Une décision d'achat s'appuie dessus.
3. **NU-A-003** — toute parcelle disparue du cadastre fait planter la fiche en 500 au lieu de servir la courtoisie prévue ; la prod est à une erreur d'ingestion du même sort.
4. **NU-A-007 + NU-A-008** — les aléas sont sous-vendus : « fort ~3 % » masque 100 % d'exposition, et une zone rouge PPR < 50 % n'est jamais signalée inconstructible (L562-1). Risque mal lu = sur-paiement ou projet mort-né.
5. **NU-A-006** — une falaise (pente max 43,9°) étiquetée « modérée » parce que seule la moyenne est classée.

## Si j'étais le développeur, ce que je changerais en premier

**Une source unique de SDP, gardée par une assertion de build (NU-A-001).** C'est le défaut le plus grave et le plus réparable : aujourd'hui l'en-tête lit `parcel_residuel` (vivante, non figée au run) et le verdict lit `score_labuse` (figé q_v20), calculés à 3 mois d'écart. Faire lire à toute la fiche la SDP du **run servi** (`score_labuse` q_v20), et ajouter au harnais de build une assertion « `potentiel_transformation.sdp == analyse_labuse.sdp` pour le run servi, à l'arrondi près » qui casse la CI sinon. Dans la foulée, protéger `info_disparue` contre l'absence de table (NU-A-003, deux lignes) et insérer un plan « maison-seule » dans `base_plans` (NU-A-002) — les trois bloquants tombent avec peu de code, et aucun ne touche l'arithmétique, déjà juste.
