# RECETTE-8 — les preuves, la recette de RECETTE-7, et le LiDAR

Branche `fix/recette-8` (depuis `fix/recette-7`, non mergée). Worktree `~/Desktop/labuse-recette6`.
**Aucun merge, aucune bascule, aucun rescoring.** Seule exception d'ingestion : le LiDAR/MNS (lot 5),
utilisé **par fenêtre** (mesure), sans ingestion massive en base. Ports imposés tenus : **API `:8031`,
front `:5199`**. SIGTERM uniquement ; l'API `:8020` de Vic et son run `q_v14` jamais touchés.

## Bilan des 25 travaux

| # | Travail | État | Preuve |
|---|---|---|---|
| W1 | Montrer la chaîne des 458 m² | ✅ fait | `RECETTE-8-preuves/W1-chaine-458.txt` (3 parcelles, étape par étape) |
| W2 | Taxe : aucun montant sans projet | ✅ fait | bloc taxe = taux seul ; §8/fiche/pré-dossier ; provenance verte ; tests |
| W3 | Un seul scénario par document | ✅ fait | prefill = reconstruction (le scénario chiffré) ; vérifié Financier |
| W4 | Régénérer Dossier 3 parcelles | ✅ fait | 3 PDF `W4-dossier-*.pdf`, aucun montant taxe |
| W5 | Verrou étendu aux libellés | ✅ fait | `provenance.libelles_hors_registre` + test Z5 (11 verts) |
| W6 | Paliers registre vs front | ✅ fait | `W6-paliers-registre.md` (identiques, 0 écart) |
| W7 | « Potentiel épuisé » 20 parcelles | ✅ fait | `W7-potentiel-epuise-20.txt` (20 + 123 066) |
| W8 | Limite du verrou écrite | ✅ fait | §W8 ci-dessous |
| W9 | A1 gris parcelles hors sélection | ✅ fait | `MapView.tsx` baseVisible=false ; tsc 0 |
| W10 | A5 le `i` des comptes par commune | ✅ fait | `FiltreLabuse.tsx` `i` garder ; tsc 0 |
| W11 | B1 les `i` de la fiche | ✅ fait | captures `W11-avant-hover`/`W11-apres-hover` |
| W12 | B2 tête de fiche défile | ✅ fait | captures `W12-avant-scroll`/`W12-apres-*` |
| W13 | B5 contour blanc Remonter le temps | ✅ fait | captures `W13-avant-temps`/`W13-apres-temps` |
| W13bis | C3 parcours « Revente en l'état » | ✅ fait | `W13bis-financier-revente.pdf` ; tests marge |
| W14 | « 1 bu » : accord pluriel | ✅ fait | `test_recette8_accord.py` (0/1/2 sur chaque compteur) |
| W15 | Zone Um dans l'Apporteur | ✅ fait | `verdicts.zone_libelle` partagé ; vérifié 2 docs |
| W16 | Millésime source : une vérité | ✅ fait | `millesime_source.composer` (pied ↔ §10 identiques) |
| W17 | « Les ventes retenues, une à une » | ✅ fait | titre honnête (distribution / un point par vente) |
| W18 | « Scénario surelevation » libellé | ✅ fait | `scenarios.libelle_scenario` ; vérifié Financier |
| W19 | 🔴 Saisie modifiée ne change pas le doc | ✅ fait | `W19-financier-prix-4500/6000.pdf` (2 PDF ≠) + `no-store` |
| W19bis | Saisie appartient à la parcelle | ✅ fait | `W19bis-isolation-parcelle.txt` + fix front |
| W20 | Segment annonce 27 affiche 5 | ✅ fait | « N sur M affichées — charger plus » ; tsc 0 |
| W21 | En-tête Financier casse l'adresse | ✅ fait | `W21-financier-adresse.pdf` (une ligne) |
| W22 | Ranger la vue mer, servir l'exposition | ✅ fait | `exposition.py` + endpoint + tuile ; §5 |
| W23 | LiDAR MNS par étapes | ✅ fait | `W23-lidar-mns-saint-denis.txt` (mesuré, comparé, branché) |

**25/25 traités.** Un commit par travail (26 commits, W2 et W3/W18 séparés, quelques suivis de tests).
Rien n'est mergé. Suite : registre 0 problème, provenance Z5 11 verts, vitest 202, tsc 0, tests
recette-8 22 verts, fiche1_taxe 3 verts. **Deux échecs pytest PRÉ-EXISTANTS** (prouvés RECETTE-7,
non touchés) : `test_m136`, `test_exports2_lot6`. **Deux verrous ROUGES PRÉ-EXISTANTS** : V1c (3
orphelines d'exploitation `mail_queue`/`prefs_carte`/`questionnaire_financier`) et V3a (tuiles `q_v14`
de Vic vs manifeste `q_v11_m137`) — hors mandat, jamais créés ici.

## Étape 0 — gardes

- `pwd` = `~/Desktop/labuse-recette6` ✓ ; branche de départ `fix/recette-7`, arbre **propre** ✓ ;
  branche `fix/recette-8` créée ✓ ; `.env` présent, DB locale `labuse` (431 663 parcelles) ✓.
- `:8020` = API + run `q_v14` de Vic — **non touché**. `:8031` portait un orphelin de moi (PPID 1,
  4 h 35) → SIGTERM, port repris proprement. API `:8031` + front `:5199` montés pour les captures.

---

# 1. Les 458 m²

## W1 — la chaîne, montrée à la main

`scripts/_recette8_w1_chaine458.py` (lecture seule) dump le moteur `estimate_capacity`
(`faisabilite/engine.py`) étape par étape. Sur `97411000EL0157` (Saint-Denis, zone Um, 1 019 m²) :

| étape | formule | valeur | `fichier:ligne` |
|---|---|---|---|
| Emprise reculs (géométrie réelle) | contour inseté du recul séparatif 4 m | ~545 m² | `engine.py:280` |
| Emprise % réglementé | `min(545, 1018×50%)` | ~509 m² | `engine.py:299-304` |
| Niveaux (hé 7 m ÷ 3) | | R+1 (2 niveaux) | `engine.py:327-331` |
| Emprise bâtie (occupation 45 %) | `509 × 45%` | ~229 m² | `engine.py:346-349` |
| **SDP brute (plancher créé)** | **`229 × 2 niveaux`** | **~458 m²** | `engine.py:364-366` |
| → assiette taxe (avant W2) | `458 × 3,0 %` (+ dép.) | 22 469 € | `app.py:_taxe_amenagement_block` |

On suit **1 018 → 545 → 509 → 229 → 458** à la main. Le résiduel au sol (`sdp_residuelle_m2` = 97 m²)
et la SDP créée en table rase (458 m²) sont **deux données distinctes** (Z3 de RECETTE-7) : 97 = ce
qu'on ajoute sans démolir, 458 = ce qu'une reconstruction totale crée. Les 22 469 € portaient sur
cette table rase **que personne n'a choisie** — corrigé en W2. Parcelle nue (177=177, coïncident) et
bâtie dense (3 190 m²) au fichier de preuve.

## W2 — trancher : aucun montant sans projet

La taxe d'aménagement se paie, en droit (art. L331 c. urb.), sur la surface de plancher **créée par un
projet**. Sur la fiche, le Dossier, le pré-dossier PC : aucun projet n'est saisi → LABUSE ne l'invente
plus. `_taxe_amenagement_block` (`app.py`) ne sert QUE le taux communal public (daté) + la part
départementale + la phrase « se calcule sur la SDP du projet ». **Plus de `total_eur`, plus d'assiette
table rase.** Conséquence vérifiée : Dossier §8, tuile fiche (`constructibilite.tsx`), pré-dossier
(`pre_dossier.py`) — taux + phrase, jamais un €. Registre (`taxe_amenagement_estimee_eur`) et type TS
alignés. **Avec projet** : le montant est chiffré AU FINANCIER, sur `program.surface_plancher`
(`builder._financier_contexte`), pré-rempli sauf si le porteur l'a saisi ou vidé (règle 2).

## W3 — un seul scénario par document

Le bilan du Financier chiffre la SDP créée en **table rase** ⇒ une **reconstruction**. Avant, le
questionnaire pré-remplissait « surélévation » quand elle était possible → le Financier CITAIT
surélévation en FACTURANT une reconstruction (les « deux lectures contradictoires » du constat). Le
scénario pré-rempli est désormais **reconstruction** (celui que le bilan chiffre) ; la surélévation
reste une OPTION présentée au Dossier (une marge en mètres), sans bilan chiffré propre.

## W4 — Dossier régénéré, 3 PDF joints

`W4-dossier-nue-97401000AD0554.pdf`, `-batie-EL0157-97411000EL0157.pdf`, `-batie-dense-97411000BD0527.pdf`.
pdftotext §8 : « Taux communal X % … Se calcule sur la surface de plancher créée par le projet » —
**aucun « 22 469 € »**, aucune assiette table rase. `taxe.total_eur = None` partout.

---

# 2. Les paliers et les libellés

## W5 — le verrou étendu aux libellés

`provenance.libelles_hors_registre()` attrape un identifiant technique servi au client (« Scénario
surelevation » sans accent, un code de palier/verdict de cascade). **Denylist** des identifiants des
vocabulaires contrôlés, restreinte aux formes NON AMBIGÜES (snake_case, MAJUSCULES, sans-accent) pour
ne jamais confondre avec un mot de prose (« reconstruction », « chaude », « faible » restent des mots
français). Câblé dans le test Z5 (sweep des 4 témoins + contre-preuve que le verrou mord :
`surelevation`/`sans_signal`/`HARD_EXCLUDE` attrapés, « Surélévation »/« Sans signal »/« reconstruction »
non) et dans la sonde (`verifier_provenance` → écart `libelle_hors_registre`). **0 fuite libellé** sur
les témoins ; **11 tests provenance verts**.

## W6 — paliers registre vs front

`W6-paliers-registre.md` : les 4 paliers (`priorite`/`a_suivre`/`sans_signal`/`ecartee`), leur libellé
court/long et leur seuil (`scoring/tiers_client.py::PALIERS_CLIENT` + `scoring_client.yaml → paliers`)
sont **RIGOUREUSEMENT IDENTIQUES** au front (`frontend/src/lib/status.ts::PALIER_META`). **Aucune
différence à corriger.** Un test anti-dérive garde déjà l'égalité.

## W7 — « potentiel épuisé » vérifié avant d'affirmer

Tirage reproductible de **20** parcelles du palier (run servi `q_v11_m137`) + ventilation des **123 066**
(`W7-potentiel-epuise-20.txt`). Résultat :

- **86,7 %** REEL — SDP résiduelle CALCULÉE = 0, cause NULL → bâties à leur densité autorisée ;
- ~8,7 % `terrain_exigu` (bâtie ET trop exigüe pour ajouter) ; ~2,8 % zone non constructible / habitat
  interdit / redhibitoire (bâtie ET zone l'interdit) — raisons **calculées**, pas des trous de donnée ;
- **0,04 %** (51 parcelles) `zone_non_resolue` — le SEUL vrai « manque de donnée ».

**Verdict : le libellé n'est PAS faux** (critère W7 : « une part notable par manque de donnée » →
0,04 %, négligeable). Nuance remontée à Vic : pour les ~13 % « autre raison », un libellé plus fin
(« sans potentiel constructible ») serait plus juste — mais c'est une décision de vocabulaire de
scoring, pas un manque de donnée. Aucun rescoring (lecture seule).

## W8 — la limite du verrou, écrite noir sur blanc

**Le verrou de provenance (Z5) attrape les nombres NON ANCRÉS, pas les nombres FAUX.** Il vérifie
qu'un nombre imprimé se rattache à une donnée SERVIE par le registre (par valeur), et — depuis W5 —
qu'aucun identifiant technique ne fuit comme libellé. **Ce qu'il ne voit pas :**

1. **Un nombre RATTACHÉ mais FAUX.** Les 458 m² passent le crible sans problème : ils sont bien
   produits par le moteur et servis. Le verrou ne dit rien de leur JUSTESSE ni de leur PERTINENCE
   (une taxe sur un scénario que personne n'a choisi était « ancrée » et pourtant trompeuse — c'est
   W2, pas Z5, qui l'a corrigée). La justesse est le rôle des **règles CIRCUIT-4** et de la **recette**.
2. **Un nombre qui coïncide par hasard** avec une valeur servie (rattachement par VALEUR, faute d'un
   tag de provenance au rendu — prix d'un crible non intrusif sur les blocs existants).
3. **Deux concepts identiques sous des libellés DIFFÉRENTS** (il faudrait un dictionnaire de synonymes) ;
   et un libellé faux qui n'est PAS un identifiant technique (une phrase trompeuse en bon français
   passe — cf. W15/W16, corrigés à la main, pas par le verrou).

**Conséquence à retenir : un test vert de provenance prouve que chaque nombre a une SOURCE au registre,
JAMAIS qu'il est exact.** Ne pas prendre Z5 pour une garantie d'exactitude.

---

# 3. Ce que RECETTE-7 n'avait pas livré — livré (ports :8031 / :5199)

Captures avant/après dans `RECETTE-8-preuves/captures/` (deep-link `window.__labuse`, helper
`scripts/_recette8_capture.mjs`).

- **W9 (A1) — gris hors sélection.** `MapView.tsx` : la trame grise `parcels-base`/`ile-base`
  (#22302A/0,28) peignait « le reste » en mode Analyse restreinte → `baseVisible=false`. Une parcelle
  porte sa couleur de palier ou RIEN ; les hors-sélection gardent leur contour (couche « Limites
  parcelles »). tsc 0. *(Le gris hors-sélection n'apparaît qu'en analyse restreinte multi-étapes ;
  fix vérifié en source + tsc.)*
- **W10 (A5) — le `i` des comptes par commune.** `FiltreLabuse.tsx` : `i` (garder) expliquant pourquoi
  l'immense majorité d'une commune n'a aucun signal (déjà bâtie à sa densité, zone A/N, sans signal de
  vente) — cohérent avec W7. tsc 0.
- **W11 (B1) — les `i` de la fiche.** Cause : `Tip` n'affiche sa bulle qu'avec `garder` (S10). Les six
  `i` de la tête + le `i` d'adresse absente appelaient `<Tip>` sans `garder` → muets. Ajout de `garder`.
  Captures : avant = rien au survol ; après = « Contenance cadastrale de la parcelle (DGFiP) » s'affiche.
- **W12 (B2) — la tête défile.** La carte d'en-tête vivait dans un wrapper `flex-shrink:0` fixe qui
  recouvrait le contenu. Le conteneur `overflow-y-auto` s'ouvre désormais AVANT la tête → un seul corps
  qui défile. Captures : avant = tête fixe ; après (défilé) = la tête a disparu vers le haut.
- **W13 (B5) — le contour blanc de Remonter le temps.** Contour de la parcelle désignée passé de vert
  (#4ADE80) à BLANC (#ECF5EF), casing sombre : lisible sur les deux fonds d'époque, des deux côtés du
  curseur. Captures : avant (non désignée, aucun contour) / après (contour blanc, deux volets).
- **W13bis (C3) — « Revente en l'état ».** Parcours bâti de bout en bout (spec RECETTE-7 C3), calcul
  SIMPLE (pas de bilan à rebours) : `marge = revente − achat − frais − travaux − portage` ;
  `taux_marge = marge / revente`. Portage non chiffré → marge « maximum ». `financier_bilan.calculer_revente`
  (testé : 250 k → 340 k ⇒ marge 40 k, taux 11,8 %). USAGES['revente'].servi=True, `REVENTE_ECRANS`,
  `manques_revente`, `_usage` persisté, endpoint `ecrans_par_usage`, front sert le parcours choisi, 3
  données registre + robinet, bloc de rendu dédié, provenance ancre les nombres. Les 3 autres parcours
  restent grisés avec leur raison. PDF `W13bis-financier-revente.pdf`.

---

# 4. Ce que la recette de RECETTE-7 a trouvé

- **W14 — « 1 bu ».** Le `rstrip('s')` naïf mangeait le « s » de « bus » (invariable). Table explicite
  singulier/pluriel par catégorie (`autour.py::_EQUIP_ACCORD`) : « bus »→« arrêt de bus »,
  « commerces »→« commerce ». Testé 0/1/2 sur chaque compteur (`test_recette8_accord.py`).
- **W15 — Zone Um dans l'Apporteur.** L'Apporteur imprimait « Zone U » (famille) pendant que le Dossier
  disait « Zone Um » (E3). Libellé PARTAGÉ `verdicts.zone_libelle()` (« Zone Um (famille U) ») lu par
  les deux. Vérifié : les deux documents disent « Zone Um (famille U) ». *(exactement le cas que W5
  cible : une donnée, deux documents, une seule réponse.)*
- **W16 — deux vérités pour un millésime.** Le pied imprimait « BD TOPO — édition non enregistrée »
  pendant que §10 disait « … vue le 31/07/2026 (sentinelle) » : la composition E10 vivait dans
  `_data_sources_fiche` mais pas dans `valeur._millesimes` (qui lisait le brut). Producteur UNIQUE
  `millesime_source.composer()` appelé par les deux. Vérifié : pied et §10 disent le MÊME « … édition
  courante, vue le 31/07/2026 (sentinelle) » ; plus aucune « édition non enregistrée ».
- **W17 — « Les ventes retenues, une à une ».** Le titre annonçait une liste ligne à ligne inexistante
  (le bloc montre un nuage). Titre honnête : « Les ventes retenues — distribution des prix au m² (un
  point par vente) ».
- **W18 — « Scénario surelevation ».** L'identifiant technique s'imprimait au client. `scenarios.py`
  (code → libellé humain) ; le Financier rend « Reconstruction (démolition-reconstruction) », jamais
  l'id. Couvert par le verrou W5.
- **W19 — 🔴 saisie modifiée ne change pas le doc.** Le back RÉGÉNÈRE à chaque appel (prouvé : deux prix
  4 500 vs 6 000 €/m² ⇒ deux HTML puis deux PDF DIFFÉRENTS, 29 828 vs 29 843 o, joints). Le bug était
  100 % le **cache de transport** : URL stable `/financier/{idu}.pdf` sans `Cache-Control` → le
  navigateur resservait la 1re réponse. Fix : `Cache-Control: no-store` sur les réponses document
  (financier/apporteur/dossier). Débloque le cul-de-sac de la garde E2.
- **W19bis — la saisie appartient à la parcelle.** Backend : questionnaire clé par `(compte_id, idu)`
  → aucune valeur d'une parcelle ne resservira sur une autre (prouvé : A={4500,999999}, B vierge,
  aucune fuite). Front : le garde `seeded` gardait les réponses de la 1re parcelle si le composant
  n'était pas démonté → re-semis PAR IDU (`seededIdu`). Preuve `W19bis-isolation-parcelle.txt`.
- **W20 — segment annonce 27 affiche 5.** L'en-tête portait le total serveur (27) mais la liste dépliée
  n'affichait que les parcelles chargées (5). Désormais : « 5 sur 27 affichées — charger plus de
  résultats → ». Jamais un compte qui ne correspond pas à ce qu'on voit.
- **W21 — l'en-tête du Financier casse l'adresse.** L'adresse vivait dans un h1 à 24 pt → cassait entre
  code postal et commune. Classe `.addr-compacte` (15 pt) + code postal LIÉ à la commune par une espace
  insécable U+00A0 (extraite proprement, contrairement à U+2011). PDF `W21-financier-adresse.pdf` :
  « 8 Chemin Charles Ollivier Manès, 97417 Saint-Denis » sur une ligne.

---

# 5. La vue mer abandonnée — le LiDAR à sa place

## W22 — ranger la vue mer, servir l'exposition

**Décision de Vic tenue : la vue mer est abandonnée** (55 h de calcul pour l'affirmation la moins
fiable). La tuile « Vue mer » de la tête de fiche devient **« Exposition »**.

`faisabilite/exposition.py` : orientation du versant (moyenne vectorielle des aspects `gdaldem`,
pondérée par la pente) + pente moyenne, sur une **petite fenêtre MNT (200 m) RGE ALTI**, **sans ligne
de vue**. Terrain quasi plat → « plat » (jamais une orientation inventée sur du bruit). Endpoint
`/parcels/{idu}/exposition` (lazy) ; la tuile affiche « … » puis la valeur. **Mesuré ~0,4–1 s/parcelle**
(vs viewshed ~100× plus cher). Discrimine (EL0157 → Nord-Ouest 16°, d'autres Nord/Sud-Est…).

**Le code de viewshed** (`faisabilite/vue_mer.py`, RECETTE-7) **n'est plus servi** (tuile remplacée) ;
aucun nouveau code de viewshed commité. **Mesure & décision (5 lignes) :** le viewshed RGE ALTI
fonctionnait (0,46 s/fenêtre 400×400) mais l'île bornée au littoral ≈ 13 h et l'affirmation « vue
dégagée » dépend d'une végétation et de hauteurs BD TOPO approximatives — non défendable dans un
document client. On s'arrête là ; le RGE ALTI reste en base et sert l'exposition + l'altitude.

**Arbitrage (tranché, appliqué) :** l'exposition se calcule PAR PARCELLE sur un petit MNT local
(RGE ALTI, la source déjà en base) plutôt que d'attendre l'ingestion MNT de toute l'île (~13 h mesurées
RECETTE-7 D3) — même source, disponible partout tout de suite, sans le goulot d'ingestion. Les 2 tuiles
MNT ingérées restent en base.

## W23 — le LiDAR, par étapes

`scripts/_recette8_w23_lidar_mns.py` — `W23-lidar-mns-saint-denis.txt`.

- **Étape 1 (une commune, mesuré).** 20 bâtiments de Saint-Denis, MNS LiDAR HD (WMS-r IGN
  `…HIGHRES.MNS`, GeoTIFF Float32 0,5 m) + MNT sur la même fenêtre. **Coût mesuré : ~1,0 s de
  téléchargement (36 ko) + 33 ms de calcul par bâtiment.** Aucune ingestion massive.
- **Étape 2 (faîtage/égout vs BD TOPO).** Hauteur = MNS − MNT sur l'emprise ; **faîtage** = p99,
  **égout** = p25 — **distingués** (ce que BD TOPO ne fait pas). Comparé à la hauteur BD TOPO :
  **écart médian faîtage +0,57 m, écart absolu médian 1,11 m**, moyen +0,78 m (min −1,5, max +4,4 —
  végétation sur toit / structure haute).
- **Étape 3 (décision).** **Les chiffres TIENNENT l'estimation** (~1,1 m médian) et le MNS distingue
  faîtage/égout — répare la cause de fond de E1 (on comparait un faîtage à une règle d'égout).
- **Étape 4 (capacité branchée).** `faisabilite/hauteur_lidar.py` + endpoint `/parcels/{idu}/hauteur-lidar`
  (lazy) : ex. `97411000EL0157` → **faîtage 6,9 m · égout 3,0 m · BD TOPO 6,6 m · écart +0,3 m**. Servi
  par parcelle à la demande (même arbitrage que W22 : pas de batch île bloquant).

**Ce qui reste (staged, sous go de Vic) :** l'ingestion précalculée de toute l'île pour remplacer BD
TOPO PARTOUT — extrusion 3D ; surélévation du Dossier (« 3,4 m disponibles » devient une mesure et non
une soustraction sur une estimation) ; étiquette de nature de l'Apporteur `estimé → sourcé`. Le point
de branchement (helper + endpoint) est prêt ; le câblage des 4 consommateurs se fait sur la hauteur
servie par ce point unique. Coût extrapolé : ~1 s/bâtiment (Saint-Denis quelques heures, l'île
plusieurs dizaines d'heures de WMS — à ne pas lancer en aveugle, doctrine RECETTE-7 D).

---

# Vérification

- pytest touché (exports/financier/taxe/provenance/circuit/apporteur/commune/millesime) : **463 passed**,
  2 pré-existants (`test_m136`, `test_exports2_lot6`) ; provenance Z5 `-m local` **11 passed** ;
  registre + exports2_lot0 + verrous concepts **101 passed** ; recette-8 **22**, fiche1_taxe **3**.
- Verrous base réelle : 2 ROUGES **pré-existants** (V1c orphelines d'exploitation, V3a tuiles `q_v14`).
- Front : **vitest 202 passed, tsc 0**.
- 12 PDF/artefacts + 6 captures avant/après (W11, W12, W13) dans `RECETTE-8-preuves/`.

**Rien n'est mergé.** 26 commits sur `fix/recette-8`, `main`/`fix/recette-7` intactes.
