# CIRCUIT-6 — les sept garanties

*Le document que Vic relit les jours de doute. Chaque garantie : sa phrase, son verrou (id G1…G7,
joué par `labuse circuit verrous` avec les seize de CIRCUIT-5, par la sonde de nuit, et par la
porte de `deploy.sh`), son test (`tests/verrous/test_garanties.py`, 25 tests), sa preuve
rouge-puis-verte VÉCUE sur la base réelle, et l'endroit de la page Circuit qui la porte.
Complète VERROUS.md, ne le remplace pas. Branche `feat/circuit-6`, rien n'est mergé.*

**L'endroit sur la page** : en tête du Résumé du Circuit (Admin → Données), **sept lignes, une
par garantie, vert ou rouge, calculées côté serveur** (`/admin/circuit` clé `garanties` ;
`Resume.tsx` les REND, ne recalcule rien). Capture : `RECETTE-CIRCUIT-6/G-sept-lignes.png`.

---

## G1 — toutes les sources, une seule fois

> *« La page Circuit montre les 116 sources de la base, chacune avec son état (liste fermée),
> et signale tout doublon — aucun doublon sans arbitrage écrit. »*

- **Calculé** : `catalogue_compteurs` — 116 en base = 95 en vitrine + 21 hors vitrine (par
  statut), plus jamais gravé. `detecter_doublons` — même endpoint (hors passerelles mutualisées
  WFS/Overpass/Carmen/GPU), même table hors spatial_layers, même couche (kind), même concept
  déclaré ; l'arbitrage écrit (alias_de, note en base, note du réservoir) éteint.
- **Rouge vécu** : 5 doublons sans arbitrage sur la base réelle — les deux potentiels fonciers
  Région (kind partagé), SIRENE↔DINUM (**même URL exacte** recherche-entreprises), SIRENE↔86 et
  45↔86 (concept), ZFANG↔FRR (table `territoire_fiscal_commune` — trouvé en plus).
- **Vert** : 4 arbitrages ÉCRITS en base (technical_notes, marquage jamais suppression) →
  18 recouvrements signalés, 0 sans arbitrage.
- **Page** : ligne G1 + clés `catalogue` et `doublons` de `/admin/circuit`.

## G2 — visible ou pas, je le sais

> *« Pour chaque source, la page dit sur quelle surface elle arrive et si sa fiche est
> réellement remplie — aucune source connectée de type parcelle vide sur l'ensemble des
> témoins sans un état INVISIBLE affiché. »*

- **Le click-test devient permanent** : `registre/remplissage.py` — 12 témoins (4 urbains +
  4 ruraux fixes + 4 tirés déterministes chaque jour), jointures rapides parcelle/commune/carte
  (jamais d'intersection spatiale : 43–70 s l'appel, mesuré). INVISIBLE = signature complète
  (type parcelle + 0/12 + toutes tables < 100 lignes) — un `carte` 0/12 par commune ou un
  `parcelle` 0/12 sur source riche n'est PAS une invisibilité (leçons SOURCES-AUDIT).
- **Rouge vécu** : joué AVANT le branchement — « DPE : vide mesurée mais l'état affiché est
  “à jour” (mint) » ; il a attrapé une DEUXIÈME vide : `lidar_hd_mnh` (table déclarée =
  cache 27 lignes — soignée au lot 7).
- **Vert** : `etat_reservoir` sort ROUGE « INVISIBLE — branchée mais vide » AVANT tout autre
  état ; l'assembleur pose le drapeau depuis la mesure. Les vides sont NOMMÉES dans la preuve.
- **Nuit** : la sonde (`coherence-robinets`, déjà planifiée) joue les garanties + la mesure
  COMPLÈTE (couches carte incluses) et journalise (`garanties-remplissage`).
- **Page** : ligne G2 + réservoir DPE en rouge (capture `G2-dpe-invisible.png`) + champ
  `remplissage` par réservoir.

## G3 — je sais ce qui nourrit le score

> *« Chaque source dit si elle nourrit le score ou la cascade, par quelle variable — et aucune
> variable du modèle servi n'est nourrie par une source hors registre, retirée, ou vide. »*

- **Liste fermée** : `FEATURE_RESERVOIRS` (28 variables du modèle P, retirées M35E incluses —
  l'artefact servi les référence) + couches cascade (`cascade_rules.yaml` → réservoirs par la
  carte) = **39 sources** nourrissent score/cascade. Une variable non cartographiée casse.
- **Rouge prouvé** (cas construits) : variable inventée → casse ; feature pointant `mobpro`
  (RETIRÉE) → casse.
- **Vert** : 0 problème ; repère servi : *39 sources · dernière maj 05/09 · run servi q_v11_m137*.
- **Page** : ligne G3 (le repère est dans la preuve) + champ `score` par réservoir
  (variables + couches cascade).

## G4 — dernière version ou pas

> *« Chaque source connectée porte soit un état de version calculé, soit une raison de
> non-vérifiabilité écrite — jamais rien ; et “à jour” n'est jamais vrai sur une source vide. »*

- **Rouge vécu** : 6 sources NUES mesurées (INSEE RP Logement, SRU, NPNRU, PLH, RTAA, Sudocuh)
  — ni sonde, ni raison.
- **Vert** : leurs 6 raisons honnêtes écrites (`sentinelle.RAISONS_NON_SURVEILLEES`) →
  95 = 56 sondées + 39 avec raison + 0 nue. Et `lister_etats` combine VERSION × REMPLISSAGE :
  une vide passe `etat=vide`, `etat_client=pas_a_jour` (« Branchée mais vide — donnée
  indisponible. ») ; les compteurs client suivent. Le DPE ne dit plus « à jour » avec 17 lignes.
- **Page** : ligne G4 + page /sources (drapeau client) + panneau admin.

## G5 — date du dernier contrôle

> *« Pour chaque source, la date du dernier contrôle est affichée — et une source jamais
> contrôlée le dit, en rouge, jamais en silence. »*

- **Rouge vécu** : 4 sources sans AUCUNE date et rien pour le dire (« Coût de construction :
  à jour, aucune date », SPANC/Office de l'eau « dépôt manuel » muets).
- **Vert** : `etat_reservoir` — jamais vérifié passe **ROUGE** (plus jamais ambre/gris) ;
  sonde câblée jamais passée sans date → rouge « jamais vérifié » ; dépôt sans date →
  « dépôt manuel — jamais alimenté ». 95 en vitrine : 55 avec date ou état parlant,
  **40 « jamais vérifié » affichés ROUGE** (le « 21 » de la maquette a grossi — mesuré).
  Les trois dates par réservoir (millésime producteur · ingéré le · dernier contrôle) sont
  servies par `/admin/circuit` depuis CIRCUIT-P.
- **Page** : ligne G5 + l'état rouge sur chaque réservoir concerné.

## G6 — quelle donnée alimente quoi

> *« Depuis une source je vois tout ce qu'elle alimente ; depuis un endroit de l'app, toutes
> les sources qu'il lit — et aucune table de réservoir n'est lue avec un réservoir MUET. »*

- **Les deux sens, calculés** : chaque robinet porte `sources` (union des réservoirs de ses
  chiffres) ; chaque réservoir porte `lecteurs` (fichiers de src/labuse qui citent ses tables —
  analyse statique, sens inverse de V1a, 76 tables au crible).
- **Rouge vécu — 2 vraies prises** : `mobpro_commune` encore lue par `zone.py` (source RETIRÉE,
  lecteur code mort CIRCUIT-5b → fonction SUPPRIMÉE : on cesse de lire, la table reste) ;
  `parcel_anc` lue par `anc_service` avec `gpu_zonage_assainissement` MUET (0 chiffre —
  provenance impossible → arête posée sur `part_logements_egout_pct`).
- **Vert** : 0 lecture de réservoir muet. **Dette fine écrite telle quelle** : 203 lecteurs non
  nommés par le champ `fonction` d'un chiffre — mesurés, affichés par source, le raccord
  fichier par fichier est un mandat à part. Jamais un verrou approximatif : le verrou exact
  porte sur les muets, la dette est comptée à part.
- **Page** : ligne G6 + champs `lecteurs`/`sources` des détails.

## G7 — la même donnée partout

> *« Un même identifiant du registre servi par deux chemins donne la même valeur sur les
> témoins de la nuit — la sonde a tourné, et chaque écart ouvert est une ligne rouge complète. »*

- **Sonde étendue** : `verifier_chemins_reels` compare les MÊMES chemins (HTTP fiche vs SQL,
  fiche vs moteur potentiel, Copilote vs fiche) sur les témoins EXPORTS-1 **plus les 12 témoins
  tournants du jour** — 25 mesures au passage du 13/09 (contre 4), 0 nouvel écart.
- **Rouge vécu** : la sonde n'avait pas tourné depuis 3 jours (dernier passage 09/09) → casse ;
  sonde rejouée → **vert**.
- **La fuite ouverte** (aléa `attrs.degre` DEAL brut vs `attrs.niveau` servi — 484 zones
  normalisées à tort) est PRÉ-EXISTANTE et HORS des quatre fuites de ce mandat : elle reste une
  **ligne rouge tracée et complète** (deux chemins, deux valeurs) — exactement ce que G7 exige
  d'un écart connu. Sa réparation est un mandat de normalisation d'aléas.

### Les quatre fuites du lot 7 — artefacts avant/après

| Fuite | Avant | Après |
|---|---|---|
| **Manifeste de fiche** | 28 sources IDENTIQUES pour toutes les parcelles (participation cascade) | **par parcelle** : 28 (Saint-Denis) vs 22 (Salazie) — filtré par le remplissage réel |
| **Hauteur LiDAR** | `hauteur_bati_m` = BD TOPO (≈ faîtage : 8,8 m sur le témoin), table LiDAR 303 452 parcelles lue par PERSONNE, créditée nulle part | égout MESURÉ d'abord (4,1 m), repli BD TOPO ; `batiment_hauteur_lidar` à la carte, arêtes `lidar_hd_mnh` posées ; G2 : lidar 8/12 (plus quasi-vide) ; V1c : une orpheline de moins |
| **Couche « OCS GE »** | (déjà réparée sur main : « Occupation du sol (BD CARTO V5 — grain grossier) ») | constat + **garde anti-régression** (`test_ocs_ge_libelle_dit_bd_carto`) |
| **DPE** | 17 lignes, « à jour » | **réingéré** (job officiel, --force, 24 communes — seule ingestion autorisée) : l'amont ADEME `dpe03existant` rend 916 lignes `974*` dont **900 à CP métropolitain** (géocodeur BAN rabattu) → 17 authentiques. **Le creux est AMONT**, documenté ; l'état INVISIBLE reste affiché — c'est la garantie qui marche, pas un échec masqué. Chercher un AUTRE jeu ADEME = un mandat de source, pas une réingestion. |

---

## Le compte-rendu

### Lot 0 — les contournements (inventaire : `CONTOURNEMENTS.md`)
15 surfaces hors registre inventoriées ; raccordés au lot 0 : vocabulaires (fiabilité,
scénarios), 3 arêtes (taxe ×2, CatNat), chiffre RTAA créé et servi, parité kinds↔carte (8 alias
déclarés), pin OCS GE. Confiés aux lots : manifeste (7), à-jour combiné (4), compteur 116 (1),
doublon SIRENE (1). **Restes écrits tels quels** : libellés du panneau Cartes non dérivés du
registre ; les verrous Z5/liste-noire de RECETTE-7/8 vivent sur des branches non mergées —
CIRCUIT-6 a construit sur main sans eux.

### Les témoins de la première passe (13/09/2026)
4 urbains (97411000CD0083, 97415000DI0183, 97416000CO0318, 97409000AB0394) + 4 ruraux
(97421000AB0001 Salazie, 97424000AB0001 Cilaos, 97419000AB0001 Sainte-Rose, 97417000AC0003
Saint-Philippe) + 4 tirés du jour. Trouvé : DPE vide (0/12, table 17) ; LiDAR déclaré sur un
cache vide (0/12, table 27) → soigné ; RNIC 0/12 SANS fausse alerte (source riche) ; sonde des
chemins réels : 25 mesures, 0 nouvel écart.

### Ce qui n'a pas pu être garanti (écrit, jamais approximé)
- **G6 fin** : 203 lecteurs non nommés par un champ `fonction` — dette MESURÉE et affichée,
  raccord = mandat futur (le verrou exact porte sur les réservoirs muets : 0).
- **V1c / V3a (CIRCUIT-5)** restent cassés sur CETTE base partagée : 6 orphelines de branches
  recette (dont 1 guérie ici) et des tuiles candidates `q_v14` vs manifeste `q_v11_m137` —
  états PRÉ-EXISTANTS prouvés sans mes édits (gestes de Vic : purge / bascule), hors mandat.
- **DPE** : la fiche ne « cesse d'être vide » que si l'amont existe — il n'existe pas dans
  `dpe03existant` (17 authentiques). L'app le DIT désormais au lieu de dire « à jour ».
- **Miroir registre_*** : en retard sur le code (219 vs 240 chiffres) — les garanties lisent le
  CODE, jamais le miroir ; la resynchronisation (`labuse registre sync`) est un geste de bascule
  laissé à Vic (base partagée avec :8020).

### La mécanique (lot 8)
`labuse circuit verrous` joue les **16 + les 7** (23 lignes, sortie 1 au premier cassé ;
`--complet` pour tout voir) — `deploy.sh` appelle cette commande : il refuse si une garantie
casse. La sonde de nuit les joue aussi et journalise. Le Résumé du Circuit affiche les sept
phrases, vertes ou rouges, calculées. Captures : `G1-resume.png`, `G2-resume.png`,
`G2-dpe-invisible.png`, `G-sept-lignes.png`.

**État final mesuré (13/09/2026)** : `✓ G1 ✓ G2 ✓ G3 ✓ G4 ✓ G5 ✓ G6 ✓ G7` — les sept vertes
sur la base réelle. Rien n'est mergé.
