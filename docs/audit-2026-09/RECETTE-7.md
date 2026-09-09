# RECETTE-7 — CIRCUIT d'abord, puis la recette

Branche `fix/recette-7` (depuis `fix/recette-6`, non mergée). Worktree `~/Desktop/labuse-recette6`.
**Aucun merge, aucune bascule, aucun rescoring.** Seule exception d'ingestion autorisée : le RGE ALTI (lot D).

## Étape 0 — gardes

- `pwd` = `/Users/openclaw/Desktop/labuse-recette6` ✓
- branche de départ = `fix/recette-6`, arbre **propre** ✓ ; branche de travail `fix/recette-7` créée ✓
- `.env` présent ✓ ; DB locale `labuse` accessible (431 663 parcelles) ✓
- `:8020` occupé par un process Python (l'API + le run de Vic) — **non touché** (SIGTERM only, jamais ce port) ✓
- `origin/fix/recette-6` absent (RECETTE-6 non poussée) — on continue en local dessus, conforme au mandat.

---

# LOT 0 — CIRCUIT : un chiffre imprimé, une donnée déclarée

## Z1 — D'où sortent les 458 m² ?

**Réponse : ce sont deux données distinctes, pas un même chiffre en deux valeurs.**

| | « 97 m² » (page 3) | « 458 m² » (page 5, assiette taxe) |
|---|---|---|
| Concept | SDP **résiduelle** (potentiel au sol) | SDP **créée en table rase** (assiette de la taxe d'aménagement) |
| Formule | `max(0, SDP_max − SDP_existante)` | `emprise constructible × coef. occupation × niveaux` |
| Producteur | `faisabilite/residuel.py:121` → `parcel_residuel.sdp_residuelle_m2` | `faisabilite/engine.py:364` (`sdp = footprint * niveaux`), empaqueté `fourchette["surface_plancher_m2"]` (engine.py:503) |
| Chemin servi | `potentiel.py:bloc_potentiel` → `au_sol.sdp_residuelle_m2` | `potentiel.py:bloc_potentiel` → `table_rase.plancher_m2` → `app.py:_taxe_amenagement_block:4084-4098` (`assiette_m2`) → `taxe_amenagement.calculer(surface_taxable_m2)` |
| Donnée du registre | `sdp_residuelle_m2` ✓ | **AUCUNE** — la valeur imprimée n'est rattachée à rien (fuite) |

**Pourquoi ce n'est pas la SDP résiduelle** : la taxe d'aménagement porte, en droit, sur la surface de
plancher **créée** par le projet (art. L331 c. urb.) ; le scénario table rase reconstruit toute la parcelle,
donc son plancher créé (458) est bien supérieur au résiduel après bâti existant (97). Les deux chiffres sont
**justes chacun dans leur définition** — le défaut est qu'ils s'impriment sous des libellés voisins
(« surface de plancher ») sans que le 458 soit une donnée déclarée du registre, et que la sonde ne peut pas
voir un producteur non déclaré.

Le mandat (Z3) tranche ce cas : deux définitions légitimes ⇒ **deux données distinctes du registre**.

## Z2 — L'inventaire des nombres imprimés

**Méthode.** Plutôt que deviner à la lecture du code, l'inventaire est **mesuré** :
`scripts/_recette7_inventaire.py` génère les documents des 4 témoins, `exports.provenance.inventaire`
extrait CHAQUE nombre du HTML rendu et le rattache à l'identifiant de la donnée du registre qui le
porte (récursivement dans les `Valeur`, le contexte Financier/Apporteur, et les millésimes de source
du pied). Un nombre sans identifiant = FUITE. **Le crible EST l'inventaire ET le verrou (Z5).**

**Résultat sur dossier + flash + apporteur (12 documents, 4 témoins) : 0 fuite** après correction.
Rattachements mesurés (nombre d'occurrences → donnée du registre), les plus fréquents :

| occ. | donnée du registre | occ. | donnée du registre |
|---|---|---|---|
| 150 | `dvf_parcelle_liste` | 18 | `emprise_batie_m2` |
| 131 | `aleas_parcelle_liste` | 16 | `surface_libre_sol_m2` |
| 122 | `iris_quartier` | 10 | `pente_deg` · `marge_surelevation_m` |
| 88 | `distance_arret_m` | 9 | `hauteur_bati_m` · `fibre_parcelle` |
| 66 | `perimetres_dispositifs_liste` | 8 | `prix_terrain_secteur_eur_m2` · `part_logements_egout_pct` · `viabilisation_verdict` · `parc_social_rpls_logements` |
| 50 | `prix_sortie_bati_eur_m2` | 7 | `surface_parcelle_m2` |
| 38 | `run_label_servi` (sources+millésimes) | 6 | `potentiel_verdict` · `er_emplacement_reserve` |
| 37 | `reglement_plu_bloc` | 4 | `type_proprietaire` · `taxe_amenagement_estimee_eur` |
| 23 | `adresse_ban` | 3 | `assemblage_surface_m2` |

**Les fuites trouvées puis résolues (le but de Z2 : « il y en aura d'autres que les 458 m² ») :**

| # nombre | endroit | diagnostic | résolution |
|---|---|---|---|
| assiette taxe (458, 794, 177…) | Dossier §8, taxe | **imprimée « … m² de plancher »** → collision de libellé avec la « SDP résiduelle » du §3 ; portée par le sous-champ `assiette_m2` du dict `taxe_amenagement_estimee_eur`, SANS identité propre | Z6 : libellé « m² de **surface de plancher créée (reconstruction totale)** » ; Z3/Z7 : la donnée `surface_plancher_m2` EST cette assiette (même producteur, même valeur) — registre corrigé |
| `330 051 immeubles` | Dossier §6, pied fibre | descripteur de COUVERTURE de la source Arcep, dans la chaîne `source_millesime` | rattaché : les nombres des millésimes de source (`Valeur.reservoirs`) décrivent la source, pas la parcelle |
| `60` (« 60 ans et plus »), `1990` (« bâti avant 1990 ») | Dossier §7, quartier | libellés de tranche INSEE | liste blanche (définition, pas une mesure) |
| `974`, codes postaux `974xx` | partout | code du département / codes postaux | neutralisés comme références structurelles |
| composantes du bilan en k€ (`1 618 k€`…), TVA `8,5 %`/`2,1 %`, pas `±5 %` | Financier | dérivés du bilan (rattachés à `charge_fonciere_eur` et aux hypothèses `*_saisi_*`) ou taux de droit cités | anchrage argent (€/k€/absolu) + liste blanche des taux légaux |

**Le scanner a d'abord trouvé 119 « fuites »**, dont l'écrasante majorité étaient des faux positifs de mon
extracteur (CSS `@font-face`, dates, n° de rapport, références cadastrales `DH 1880`, articles de loi) —
durcis un à un jusqu'aux **fuites réelles**, toutes rattachées ou fixées ci-dessus.

## Z3 — Un producteur par donnée (la surface de plancher)

La SDP a **deux définitions légitimes** — le mandat tranche : deux données distinctes, jamais deux chiffres
pour un même nom.

| donnée | définition | producteur UNIQUE | lecteurs |
|---|---|---|---|
| `sdp_residuelle_m2` | `max(0, SDP_max − SDP_existante)` — ce qu'on peut AJOUTER sans démolir | `faisabilite/potentiel.py:bloc_potentiel` (au_sol) ← `residuel.py:121` | fiche, Dossier §3, Apporteur, faisabilité |
| `surface_plancher_m2` | SDP **créée** par le scénario table rase (emprise × occupation × niveaux) | `faisabilite/potentiel.py:bloc_potentiel` (table_rase.plancher_m2) ← `engine.py:364` | **assiette** de `taxe_amenagement_estimee_eur`, programme du Financier |

Les deux passent par le **même producteur** (`bloc_potentiel`) : un seul point de vérité, deux sorties
nommées. La taxe d'aménagement, la faisabilité, l'Apporteur, le Financier et la fiche lisent ces deux
sorties — jamais un troisième calcul dans leur coin. `capacite_logements` et `surface_vendable_m2` sont les
autres sorties de la même table rase, déjà distinctes au registre.

## Z4 — La sonde apprend à voir les producteurs

Deux nouvelles vérifications dans `sonde_circuit.py`, câblées dans `controle()` (nuit + bouton) :

- **`verifier_provenance(db)`** — génère dossier/flash/apporteur des témoins et passe chaque nombre au
  crible `exports.provenance` ; tout nombre hors registre devient un écart `nombre_hors_registre`. C'est la
  face DOCUMENTS du trou : un producteur non déclaré qui imprime un chiffre est désormais VU. Mesuré :
  **0 écart sur 12 documents.**
- **`verifier_synonymes()`** — échoue si deux données du registre portent le **même libellé** (le piège
  d'où sortait 97/458 avant qu'on nomme distinctement les deux SDP). Mesuré : **0 collision.**

**Ce qu'elle sait détecter désormais** : (1) un nombre imprimé qu'aucune donnée servie ne porte
(producteur hors registre) ; (2) deux identifiants sous un même libellé.
**Ce qu'elle ne saura toujours pas** : (a) qu'un nombre RATTACHÉ est FAUX — elle vérifie la provenance,
pas la justesse (rôle des règles CIRCUIT-4 et de la recette) ; (b) un nombre qui coïncide par hasard avec
une valeur servie (rattachement par VALEUR, faute d'un tag de provenance au rendu — c'est le prix d'un
crible non intrusif sur les blocs existants) ; (c) deux concepts identiques sous des libellés DIFFÉRENTS
(il faudrait un dictionnaire de synonymes).

## Z5 — 🔴 Le verrou

`tests/test_circuit_provenance.py` (marque `local` — base réelle, joué par `pytest -m local`, la sonde de
nuit et la porte de déploiement). Il génère dossier/flash/apporteur sur les 4 témoins **+ le Financier avec
un questionnaire synthétique complet** (prix de sortie 4 500 €/m², régime TVA, 6 logements T3) et
**échoue si un seul nombre imprimé n'est pas rattaché au registre**. Un test de contre-preuve
(`test_le_crible_casse_bien_sur_un_nombre_invente`) prouve que le verrou **mord** (un « 123 456 € au doigt
mouillé » est bien attrapé, un « 1 018 m² » ancré ne l'est pas). **6 tests verts** ; il ne rend pas le PDF
(WeasyPrint) — il lit le HTML de `builder.construire`, donc tourne partout où la base est là.

## Z6 — Les incohérences corrigées

Preuve avant/après, Dossier régénéré :

- **avant** — `De l'ordre de 22 469 € (taux communal 3,0 %) pour 458 m² **de plancher**`
- **après** — `De l'ordre de 22 469 € (taux communal 3,0 %) pour 458 m² **de surface de plancher créée (reconstruction totale)**`

**Arbitrage E2 (« prouver que les deux pages disent le même chiffre »).** Mesuré sur trois parcelles :
`97401000AD0554` (terrain **nu**, 0 bâtiment) → assiette 177 m² **=** SDP résiduelle 177 m² (elles
coïncident quand il n'y a rien à démolir) ; `97411000EL0157` (constat, **3 bâtiments**) → assiette 458 m²
(reconstruction totale) **≠** SDP résiduelle 97 m² (ce qu'on peut ajouter sans démolir). Les deux
coïncident sur terrain nu et **divergent légitimement** sur parcelle bâtie — forcer l'égalité sur une
parcelle bâtie serait FAUX (une démolition-reconstruction crée réellement 458 m²). Le défaut n'était donc
pas la valeur mais le **libellé partagé** ; il est levé. (E2 est donc traité ici ; E9 « 3.0 % » et E4
« 181 m² » sont notés au lot E.)

## Z7 — Le registre à jour

Deux fiches corrigées dans `registre/donnees.py` :
- `surface_plancher_m2` : libellé « **Surface de plancher créée (table rase)** », définition explicite
  (assiette de la taxe ; distincte de `sdp_residuelle_m2` ET de `capacite_logements`).
- `taxe_amenagement_estimee_eur` : la définition dit que **l'assiette EST `surface_plancher_m2`** (même
  producteur, même valeur), jamais la SDP résiduelle. `registre.verifier()` = **0 problème**.

---

# LOT A — Carte et segments

**Note de vérification.** Les points VISUELS de ce lot (A1/A5) demandent une capture au navigateur ;
les serveurs de dev (`:5173`/`:8000`) sont squattés par d'autres worktrees et je ne tue QUE mes propres
process (garde SIGTERM). Les changements de code sont vérifiés par `tsc` (0) + `vitest` (202) ; les
captures au cadrage de Vic restent à faire sur un poste où les ports sont libres.

- **A2 🔴 (paliers) — FAIT (non-rescoring) + ARBITRAGE.** Le registre de scoring PALIERS-1
  (`scoring/p_v2/statuts.py:PALIERS`, `PALIER_META`) a EXACTEMENT **4 paliers**
  (priorite/a_suivre/sans_signal/ecartee) — « faible » n'y est PAS. RECETTE-6 (B3) avait retiré le mot
  « faible » (à juste titre : hors vocabulaire PALIERS-1, c'était le libellé en dur de « potentiel
  épuisé »). **Ré-ajouter un palier « faible » = un nouveau seuil sur p_raw = un RESCORING**, interdit
  par le garde-fou. Je ne l'ai donc pas fait. **Le vrai défaut** que le mandat pointe est réel :
  RECETTE-6 avait FONDU les 280 658 « potentiel épuisé » (bâti saturé — un état CONNU) sous « sans
  signal ». Fix SANS rescoring : la ventilation SURFACE désormais « (dont N à potentiel épuisé) » —
  `epuise` est déjà dérivé (retenues − 4 tiers), aucun seuil touché. Le « doublon » (réserve + à creuser
  = deux « sans signal ») reste corrigé. **Le doublement à suivre 631→1 367 : aucun seuil déplacé** par
  RECETTE-6 (B3 ne touchait QUE l'affichage — commit `d632e6ae`) ; le changement de compte est une
  re-bucketisation d'affichage, pas un rescoring. **Flag Vic** : si un palier « faible » distinct est
  VRAIMENT voulu, c'est une décision de registre de scoring (nouveau seuil dans `statuts.py`) = un
  rescoring à trancher explicitement.
- **A3 (barre de répartition) — FAIT.** La barre reprend les COULEURS DES PALIERS (rouge priorité ·
  orange à suivre · pâle sans signal · sombre écartées), proportionnelle au TOTAL, alignée sur la
  ventilation (couleurs `PALIER_META`) — plus la barre uniforme et pâle qui suivait `reserve_fonciere`/
  `a_creuser` (tous deux résolus en `sans_signal` pâle).
- **A4 (« Voir tout » → carte « Tout ») — FAIT.** La case à cocher flottante est retirée ; une carte
  « Tout » ferme la liste des segments (même forme, son compte à droite), la cliquer ouvre/referme les
  quatre segments.
- **A6 (pastille « Toute l'île ») — FAIT.** La pastille ronde avant « Toute l'île » (`Header.tsx`) est
  retirée.
- **A1 (le gris = les parcelles hors sélection) — NON FAIT, diagnostiqué.** RECETTE-6 (A2) a traité une
  surcouche ; le mandat dit que le gris vient des parcelles hors sélection peintes en gris sale. Le
  correctif vit dans `MapView.tsx` (peinture des parcelles en mode Analyse) : une parcelle doit porter la
  couleur de son palier ou RIEN, jamais un gris de fond. Changement de style de couche à faire + capture
  pleine île + commune — reporté faute de vérification visuelle possible ici.
- **A5 (comptes par commune + `i`) — NON FAIT, à vérifier après A2.** Vérifier les comptes Saint-Pierre
  (11/127/31 441/10 725) une fois A2 servi ; si ça tient, écrire dans le `i` pourquoi l'immense majorité
  d'une commune n'a aucun signal. Lecture-seule + rédaction, à faire sur un poste avec les ports libres.

# LOT B — Fiche parcelle

- **B3 (« SDP restante » libellé tronqué) — FAIT.** `.stat-s` (index.css) ne coupe plus
  (« pas de potentiel résid… ») : passage à la ligne (2 lignes max, sans coupure de mot). Décision
  respectée : on garde **SDP restante**, pas Exposition (elle viendra à la fin du lot D via le MNT).
- **B4 (respiration + CRM/+ Projet ↔ 6 boutons) — FAIT.** Un espace de 10 px sépare la rangée d'actions
  de la grille des 6 boutons (`Fiche.tsx`).
- **B1 (les `i` de la tête de fiche) — NON FAIT, diagnostiqué.** Les six tuiles rendent bien un `<Tip>`
  avec `c.i` (`Fiche.tsx:878-883`) ; le mandat dit qu'aucun ne fonctionne (E1 de RECETTE-6 n'a branché
  que le questionnaire Financier). À vérifier au navigateur : soit `Tip` ne se déclenche pas dans la
  tête (z-index/overflow de la carte d'en-tête), soit l'`i` n'est pas câblé sur toutes les tuiles.
  Correctif probable = même mécanisme fiable que le questionnaire (popover positionné), à valider
  visuellement — reporté (ports occupés).
- **B2 (tête collée au défilement) — NON FAIT, diagnostiqué.** Architecture M68 P1a : `<aside flex-col>`
  = bandeaux `shrink-0` + carte d'en-tête (wrapper FIXE) + corps `overflow-y-auto flex-1`. Pour que la
  tête défile AVEC le reste, il faut fusionner la carte d'en-tête DANS le conteneur défilant (un seul
  `overflow-y-auto`). Changement structurel du layout de la fiche — je ne le livre pas à l'aveugle (risque
  de casser la mise en page, vérification visuelle indispensable). Fix précis ci-dessus, à appliquer+voir.
- **B5 (contour blanc de la parcelle, Remonter le temps) — NON FAIT, diagnostiqué.** Le contour blanc de
  la parcelle a disparu des deux millésimes du curseur temporel. Le correctif vit dans l'outil « Remonter
  le temps » (couche de contour de la parcelle sur les deux fonds d'époque) — rétablir le contour des deux
  côtés du curseur. Visuel, reporté.

# LOT C — Financier

# LOT C — Financier (application)

- **C1 🔴 (le Dossier ne se génère pas toujours) — FAIT (message + robustesse).** Deux corrections :
  1. **Le message.** Avant : tout échec (technique OU réseau) atterrissait dans le bandeau « il manque : »
     avec « Le document n'a pas pu être généré » — un échec technique déguisé en donnée manquante.
     Désormais deux états DISTINCTS (`FinancierQuestionnaire.tsx`) : `docErr` (422 → NOMME les champs, « il
     manque : … ») et `docTech` (500/réseau → bandeau rouge « erreur technique », jamais sous « il
     manque : »).
  2. **La génération.** Côté route (`documents.py`), les exceptions de `construire` et de `render_pdf`
     sont désormais CAPTURÉES, la trace LOGUÉE (`log.exception` — lisible pour corriger la cause) et
     rendues en 500 « erreur_technique » distinct des manques. La cause exacte de l'échec de Vic n'était
     pas dans la trace fournie ; le Financier se génère correctement ici (questionnaire complet, prix
     4 500 €/m²). La robustesse ci-dessus fait qu'un futur échec technique est tracé et dit honnêtement.
- **C2 (doublon d'aide) — FAIT.** La bulle « i » ne s'affiche plus quand une explication est déjà
  imprimée sous le champ (source d'un pré-remplissage non touché, explication du régime de TVA) ; elle
  reste sur les champs sans texte dessous. tsc vert.
- **C3 (servir « Revente en l'état ») — DESIGN LIVRÉ, non bâti (arbitrage budget).** Ce n'est pas un
  correctif mais une FEATURE (nouveau parcours), qui touche ~5 fichiers : (a) `financier_questionnaire.py`
  — passer `USAGES['revente'].servi=True` + un jeu de champs `REVENTE_ECRANS` (prix d'achat, frais
  d'acquisition %, travaux éventuels, délai de portage, prix de revente) + `manques_revente` ; (b) stocker
  l'usage choisi dans le questionnaire (`reponses['_usage']`) ; (c) l'endpoint sert les écrans PAR usage
  (payload `ecrans_par_usage`, le front choisit) ; (d) `financier_bilan.py` — un calcul SIMPLE
  `calculer_revente` : `marge = revente − achat − frais_acq − travaux − coût_portage` (portage =
  achat × taux × durée/12, ou 0), `taux_marge = marge / revente` — pas de bilan à rebours ; (e)
  `blocs/financier.py` — un rendu revente (marge, taux, les 5 postes) sous garde de vraisemblance
  (réutilise `_hors_marche`) et couvert par le crible provenance (Z5) via des données `*_saisi_*`. Les
  trois autres usages restent grisés avec leur raison. **Non bâti ce tour** pour ne pas livrer une
  feature à moitié câblée ; la spec ci-dessus est directement implémentable.

# LOT D — Le MNT : RGE ALTI

Vic a tranché : le RGE ALTI ouvre la vue mer. **Exception d'ingestion autorisée — la seule.** Le
raster de PENTE (`rgealti_pente_5m`, 2 793 tuiles, SRID 2975) était déjà en base ; il manquait le MNT
d'ALTITUDE (le viewshed a besoin de l'altitude, pas de la pente). Environnement : `rasterio`,
`gdal_viewshed`, `postgis_raster` tous PRÉSENTS ; IGN Géoplateforme joignable (http 200).

- **D1 (migration + ingestion) — ÉCRIT + PROUVÉ.** `ingestion/rgealti_mnt.py` : table raster
  `rgealti_mnt_5m` (SRID 2975) + tuilage `mnt_tiles` (point de reprise `statut`, REJOUABLE), fetch
  WMS `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES` (GeoTIFF Float32, altitude m, NoData −99999). **Deux
  pièges rencontrés et corrigés** : (a) `xmin`/`xmax` sont des colonnes SYSTÈME Postgres → renommées
  `x0/y0/x1/y1` ; (b) PostGIS restreint les drivers GDAL (`postgis.gdal_enabled_drivers`='DISABLE_ALL')
  → `SET LOCAL … = 'GTiff'` avant `ST_FromGDALRaster` (sinon « Could not open bytea with GDAL »). Le
  piège SRID du mandat (raster 2975 vs `parcels.geom` 4326) est tenu : tout se fait en 2975
  (`geom_2975`).
- **D2 (lancer l'ingestion) — PROUVÉ BORNÉ (2 tuiles), île STAGÉE.** Ingestion end-to-end vérifiée :
  planifié 66 tuiles Saint-Pierre, ingéré **2 tuiles** → 2 rasters Float32 (32BF) en base. L'ÎLE
  entière (≈ 2 793 tuiles, comme la pente) n'est PAS lancée : le mandat l'interdit avant validation
  des 10 témoins. Elle se lance par `rgealti_mnt.planifier()` + `ingerer()` (rejouable), bornée d'abord
  au littoral.
- **D3 (moteur de viewshed) — `gdal_viewshed`, CHOISI + JUSTIFIÉ + MESURÉ.** (1) lit le raster hors
  base, en C, algorithme de visée standard ; (2) DÉJÀ présent (aucune dépendance nouvelle vs
  WhiteboxTools/GRASS) ; (3) **mesuré : 0,46 s** pour une fenêtre 400×400 (2 km, rayon 5 km) sur la côte
  de Saint-Pierre → ~2 parcelles/s. Conséquence : une commune littorale ≈ 1–4 h ; l'île bornée aux
  ~100 k parcelles littorales ≈ 13 h → **on borne au littoral**, jamais l'île en aveugle (le SQL était
  à ~89 pts/s, inutilisable — confirmé).
- **D4 (10 témoins) — MOTEUR PROUVÉ sur 5 parcelles, seuils à caler avec Vic.**
  `faisabilite/vue_mer.py` : par parcelle, fenêtre MNT (fetch WMS) → `gdal_viewshed` (observateur =
  centroïde + hauteur d'œil, toit si bâti) → part de cellules VISIBLES qui sont de la MER (altitude ≤
  2 m / NoData) → `degagee`/`partielle`/`aucune`. Prouvé sur 5 parcelles côtières de Saint-Pierre
  (part_mer 2,5–3,5 %, classées `aucune`/`partielle` — ça DISCRIMINE). Les SEUILS
  (`SEUIL_DEGAGEE`/`SEUIL_PARTIELLE`) sont un premier jet à CALER sur les 10 témoins que Vic vérifie à
  l'œil sur l'ortho — c'est exactement le geste D4 (« ne pas lancer l'île avant validation »). Le rendu
  des 10 sur ortho + l'état 4 « menacée » (permis SITADEL coupant la visée — 2e passage) sont câblés
  après validation.
- **D5 (tuile Vue mer + `i` + exposition) — STAGÉ.** La tuile « Vue mer » sert « — · à venir »
  aujourd'hui (fiche) ; elle servira la vraie valeur sur la commune calibrée, « — · à venir » ailleurs.
  Le `i` dira ce que le calcul ne voit pas (végétation, hauteurs approximatives BD TOPO, permis non
  déposés). L'EXPOSITION entre en fiche À LA PLACE de « SDP restante » (décision B3) une fois le batch
  complet passé — pas avant. À câbler après D4 validé.

**Recommandation franche (rappel du lot F2).** Le viewshed RGE ALTI fonctionne, mais le **LiDAR HD
MNS** (couche `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS`, même WMS) couvre l'île, est ouvert, déjà
streamé, et donnerait des hauteurs MESURÉES (faîtage/égout) qui règlent E1 pour de bon — un meilleur
ROI que la vue mer. À arbitrer par Vic : vue mer (argument commercial, fragile sur la végétation) vs
justesse des hauteurs (corrige une erreur de fond). Le moteur ci-dessus sert les deux (même MNT/MNS).

# LOT E — Les trois documents

Recette Vic sur `97411000EL0157` (Saint-Denis). Fixes vérifiés par régénération réelle (TestClient
base réelle + WeasyPrint + pdftotext) ; le verrou provenance (Z5) reste vert après chaque change.

- **E1 🔴 (faîtage contre égout) — FAIT.** Le bâti BD TOPO est un FAÎTAGE ; on le comparait à la
  règle d'ÉGOUT → « surélévation non identifiée » faux. Désormais faîtage↔faîtage (`hf_m` prioritaire,
  `potentiel.py:surelevation`), l'égout n'est qu'un repli converti (+ toiture type) AVEC incertitude ;
  on ne conclut « pas de marge » que si la marge est nulle sur la BONNE règle (sinon `possible=None`,
  « à confirmer »). Rendu, collecte, registre (`marge_surelevation_m` « au faîtage ») et le témoin
  `test_surelevation` mis à jour. Constaté : « Hauteur max 10 m au faîtage · 7 m à l'égout ».
- **E2 (contradiction 97/458) — FAIT au Lot 0 (Z6).** Régénéré : nu → assiette = résiduelle (177=177) ;
  bâti → 458 créée ≠ 97 résiduelle, chacun nommé. Arbitrage détaillé en Z6.
- **E3 🔴 (Zone U ou Um) — FAIT.** Le verdict affiche le CODE réel (« Zone Um (famille U) », « Zone
  Ud3 (famille U) ») pour coller aux articles cités — plus de « Zone U » tronqué. Vérifié fiche+docs.
- **E4 (181 m² d'emprise) — INVESTIGUÉ, rien à corriger + flag.** La requête `le_bien_block`
  (`bati.py`) est correcte : `ST_Area(ST_Union(ST_Intersection(bâti, parcelle)))`, bornée, sans
  constante. `EL0157` mesure réellement 181 m² (4 bâtiments intersectants). `BI0585` (Saint-Benoît)
  est ABSENT de la base locale — la coïncidence des deux « 181 » ne peut pas être reproduite ici. Aucune
  constante ni mauvais rattachement trouvé. **Flag Vic** : re-mesurer `BI0585` sur la base servie ; si
  identique au m², fournir les deux IDU pour comparer les géométries (probable coïncidence).
- **E5 (viabilisation) — FAIT.** Plus de phrase qui se dément : CONSTAT (verdict) · ce qui n'est pas
  relevé (tracé/capacité exacts) · ACTION (DT-DICT), le tout cohérent selon la bande.
- **E6 (ventes retenues) — FAIT.** Les trois valeurs portent « min / médiane / max ».
- **E7 (SaintDenis) — FAIT, PDF-vérifié.** Cause trouvée : le h1 long du Financier (24 pt) COUPAIT
  « Saint-Denis » à la ligne (« Saint-\\nDenis » → « SaintDenis » à la copie). Le trait insécable U+2011
  s'exporte en caractère parasite (confirmé : le glyphe casse pdftotext — c'est ce que F2 avait
  rencontré). Fix : `esc_noms` enrobe les noms composés d'un `white-space:nowrap` (.nb) en gardant le
  trait ORDINAIRE (extractible). pdftotext du Financier régénéré : « Saint-Denis » d'un seul tenant.
- **E8 (message répété) — FAIT.** La raison ne répète plus la valeur (le message l'imprime déjà).
- **E9 (pluriels/formats) — FAIT.** Accord « 1 commerce » / « 3 commerces » (autour) ; taux « 3,0 % »
  à la française (commune, `fmt_pct`).
- **E10 (édition non enregistrée) — FAIT.** BD TOPO / RGE ALTI : l'IGN (WFS/Géoplateforme) ne publie
  pas de millésime versionné → la sentinelle (dernier vu) ou la date d'ingestion le couvre désormais,
  en disant pourquoi (« millésime amont non versionné par l'IGN ») — plus jamais un libellé mort.
- **E11 (Financier avec prix juste) — PARTIEL.** Le Financier se génère avec un questionnaire complet
  (prix 4 500 €/m², régime TVA, 6 logts T3) et le bilan s'établit (PDF régénéré, régime unique). Le
  reste (poste « Taxe foncière (portage) », robustesse de génération) est traité au **Lot C (C1)** dont
  E11 dépend.


# LOT F — Rendre la 3D plus juste

Deux axes chiffrés (jamais branchés), + le `i` du bouton 3D.

**F1 — la fraîcheur (BD TOPO Express, hebdomadaire). Chiffrage.** BD TOPO® Express publie un delta
hebdomadaire du bâti. Pour ne servir que les constructions récentes manquantes : (1) s'abonner au
delta (petit volume — seulement les objets changés), (2) marquer « sales » les parcelles dont une
empreinte bâtiment a bougé (jointure spatiale delta ⋈ `parcels`), (3) ne RE-calculer que celles-là
(emprise `le_bien`, hauteur, bloc potentiel — la chaîne existe déjà, on la scope). **Coût** : un job
incrémental réutilisant l'ingestion bâti + le recompute potentiel, borné aux parcelles sales (quelques
centaines/semaine à l'échelle 974) ; **aucune dépendance nouvelle**. **Ce que ça règle** : le bâti
récent manquant, RIEN d'autre (la hauteur reste approximative, sans forme de toit).

**F2 — la justesse des hauteurs (LiDAR HD). Chiffrage + recommandation FRANCHE : OUI.** La Réunion est
**intégralement couverte** par le LiDAR HD IGN depuis le 25/06/2025 (MNT/MNS/MNH 50 cm, 2 665 dalles —
constat déjà VÉRIFIÉ dans ce dépôt, `RAPPORT_WAVE_ANC_VEGETATION.md`), sous **licence ouverte**
(etalab), **déjà streamé par tuile via WMS-R** et **déjà consommé** par l'app (canopée NDVI×MNH, et la
forme de toiture simple/double pente — `solaire_toiture.py`, vérifié 05/09/2026). Donc :
- **Ce qu'un MNS/MNH apporte** : des hauteurs MESURÉES (au lieu de la hauteur approximative BD TOPO),
  le **faîtage** (max MNS sur l'empreinte) ET l'**égout** (bord de toit) distingués, la **forme de
  toit** (déjà calculée). C'est **exactement ce qui règle E1 pour de bon** (faîtage vs égout mesurés,
  fin de la conversion incertaine).
- **Coût** : une statistique zonale MNS par bâtiment (max/percentiles sur l'empreinte), **réutilisant
  l'infra de streaming WMS-R existante** (comme le batch végétation MNH déjà passé) — pas de
  téléchargement massif, pas de licence à acquérir, pas de dépendance nouvelle. Un batch borné
  (parcelles bâties) + un cache hauteur.
- **Recommandation** : y aller. Le ROI est bien meilleur que le viewshed RGE ALTI (lot D) : la donnée
  est déjà là, ouverte, streamée, et elle corrige une ERREUR de fond (les hauteurs) plutôt que d'ajouter
  un argument commercial fragile. Commencer par le MNS pour la hauteur de faîtage (fixe E1), l'égout
  ensuite (analyse de bord de toit).

**F3 — le `i` du bouton 3D. FAIT.** `MapToolbar.tsx` : « Relief 3D (MNT) + bâti extrudé à sa hauteur
BD TOPO — hauteurs APPROXIMATIVES, sans forme de toit ni faîtage/égout distingués, et les constructions
très récentes peuvent manquer (mesure précise à venir via LiDAR HD) ». Une phrase, honnête.

Sources F2 : [MNH LiDAR HD IGN 2025 (data.gouv.fr)](https://www.data.gouv.fr/datasets/mnh-lidar-hd-ign-2025) ·
[MNS LiDAR HD IGN 2025](https://www.data.gouv.fr/datasets/mns-lidar-hd-ign-2025) ·
[Programme LiDAR HD (IGN)](https://www.ign.fr/institut/programme-lidar-hd-vers-une-nouvelle-cartographie-3d-du-territoire).

