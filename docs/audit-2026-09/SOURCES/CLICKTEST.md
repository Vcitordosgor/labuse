# Test client — combien de clics pour trouver la donnée (vrai navigateur)

*SOURCES-AUDIT-1, 2ᵉ passe. Réponse à la critique juste : « 0 invisible » de la 1ʳᵉ passe était
un **artefact de méthode** — dériver la visibilité du graphe du registre garantit par
construction que tout a un robinet. Ici le test est refait **au vrai navigateur** (Playwright /
chromium headless-1217) sur l'app réelle servie en local : back `:8032`, front `:5200`
(`/socle/`), base `postgresql://openclaw@localhost:5432/labuse`. `:8020` n'a pas été touché.*

Rejouable : `node docs/audit-2026-09/SOURCES/scripts/clictest_capture.mjs` (surfaces) puis
`clictest_30.mjs`. Captures : `captures/*.png` (accueil, COUCHES, Outils, page Sources, fiche,
outils Taxe/Scan/Pièges/Communes/Faisabilité).

## Ce que le navigateur montre (preuves)

- **Accueil** (`captures/01-accueil.png`) — bandeau « **95 sources · 431 663 parcelles** »
  (confirme le compteur du S1) et un lien **« voir les données → »**.
- **Trois surfaces où un pro trouve la donnée** :
  1. **La carte + panneau COUCHES** (`02-couches.png`) — ~28 couches **nommées**, groupées
     (REPÈRES, URBANISME, RISQUES, NATURE, DOMANIALITÉ, USAGE DU SOL, RÉSEAUX, DISPOSITIFS),
     **chacune avec un `i`**. 1 clic pour ouvrir le panneau.
  2. **Les 17 outils** (`03-outils.png`) — PLU, Permis, Communes, Étudier, Scan patrimoine,
     Assemblage, Comparer, Pièges, Étude de zone, Remonter le temps, Faisabilité, Taxe
     d'aménagement, Prospection solaire, Densifier, Blocs… 1 clic pour la liste, 2 pour l'outil.
  3. **La fiche parcelle** (`05/06/07`) — sections en tiroirs (Le terrain, Le bien, Réseaux,
     Solaire, Propriétaire…). Le `i` **nomme la source et le millésime** — mesuré, ex. tooltip
     capturé : *« INSEE BPE (millésime 2025) · arrêts BD TOPO/GTFS — distance à vol d'oiseau »*.
- **La page Sources & fraîcheur** (`04-sources-page.png`, nav « Sources », 2 clics) — surface
  de **transparence** : les **95** listées par thème, **chacune avec producteur + licence + lien
  ↗**, une **date de publication** pour beaucoup (BAN 11/07/2026, Sitadel 30/06, DPE 03/07, DVF
  31/12/2025, CoSIA/BD ORTHO 01/01/2025…), et des drapeaux honnêtes : **PROXY**, **FIABILITÉ À
  CONFIRMER**, **ACCÈS SOUS CONVENTION**, **MISE À JOUR EN COURS**. En-tête : « 95 sources · 94
  à jour · couvertes 24/24 · deux limites à connaître ».

## Deux notions de visibilité (le nœud)

- **Transparence** : la source est **listée** (page /sources). Les 30 testées y sont **toutes**
  — avec source + licence, souvent la date, et son drapeau de fiabilité. Bon point réel.
- **Usage fonctionnel** : la **donnée est utilisable** sur une parcelle / la carte / un outil.
  C'est le vrai test « en combien de clics ». Une source **listée mais dont la donnée
  n'atteint aucune surface fonctionnelle** est **INVISIBLE fonctionnellement** — un verdict à
  part entière, et il y en a.

## Le test — 30 sources, toutes familles

*Clics = depuis l'accueil jusqu'à voir la donnée (les outils rendent la donnée après sélection
d'une parcelle → +1 clic). « Sur /sources » = trouvable sur la page catalogue (source+licence).*

| id | Source | Surface fonctionnelle (données utilisables) | Chemin (accueil→…) | Clics | Sur /sources (source+licence) | Flag /sources | Visibilité |
|---|---|---|---|---|---|---|---|
| 1 | Cadastre (API Carto PCI) | fiche + carte (contour cadastral) | clic parcelle | 1 | oui | — | ✅ visible |
| 71 | DGFiP — parcelles des personnes  | outil Scan patrimoine | Outils→Scan→SIREN | 3 | oui | — | ✅ visible |
| 132 | DFI — documents de filiation inf | fiche Propriétaire | clic parcelle→Propriétaire | 2 | oui | — | ✅ visible |
| 3 | Urbanisme PLU/GPU (API Carto) | carte (Zonage PLU) + outil PLU + faisabilité | COUCHES→Zonage PLU | 2 | oui | MISE À JOUR EN COURS | ✅ visible |
| 44 | SUP — assiettes GPU (API Carto) | carte (couche SUP) | COUCHES→SUP | 2 | oui | — | ✅ visible |
| 107 | GPU — droit de préemption urbain | carte (couche DPU) | COUCHES→Droit de préemption | 2 | oui | — | ✅ visible |
| 62 | Sudocuh (procédures d'urbanisme) | outil PLU → Procédure | Outils→PLU→Procédure | 3 | oui | — | ✅ visible |
| 4 | Géorisques | carte (aléas) + outil Pièges | COUCHES→PPR/aléa | 2 | oui | — | ✅ visible |
| 97 | CatNat (arrêtés GASPAR / Géorisq | fiche commune + outil Pièges | Outils→Pièges→parcelle | 3 | oui | — | ✅ visible |
| 36 | Géorisques — mouvements de terra | carte (mvt) + Pièges | COUCHES→Aléa mvt de terrain | 2 | oui | — | ✅ visible |
| 76 | ZNIEFF (INPN/MNHN) | carte (couche ZNIEFF) | COUCHES→ZNIEFF | 2 | oui | — | ✅ visible |
| 24 | ABF / Monuments historiques | carte (couche ABF/SUP) | COUCHES→SUP/patrimoine | 2 | oui | — | ✅ visible |
| 5 | DVF / valeurs foncières | outils Communes/Comparer + carte VEFA | Outils→Communes | 2 | oui | — | ✅ visible |
| 16 | SITADEL (autorisations d'urbanis | outil Permis + Communes | Outils→Permis | 2 | oui | MISE À JOUR EN COURS | ✅ visible |
| 100 | RNIC — registre national des cop | fiche Le bien (copro) | clic parcelle→Le bien | 2 | oui | — | ✅ visible |
| 129 | Loyers OLL — ADIL Réunion / AGOR | fiche commune + Communes | Outils→Communes | 2 | oui | — | ✅ visible |
| 84 | Radar (pige d'annonces) | Radar (nav) | Radar | 1 | oui | FIABILITÉ À CONFIRMER | ✅ visible |
| 119 | DVF Réunion (Région, data.region | AUCUNE — témoin de filtre DVF | — jamais servi au client | ∞ | oui | — | 🔴 INVISIBLE (fonctionnel) |
| 48 | PVGIS (Commission européenne) | fiche Solaire + Prospection solaire | Outils→Prospection solaire | 2 | oui | — | ✅ visible |
| 93 | EDF Réunion — lignes moyenne ten | carte (lignes électriques) | COUCHES→Lignes électriques | 2 | oui | — | ✅ visible |
| 126 | Fibre Arcep — Ma connexion inter | fiche Réseaux (fibre) | clic parcelle→Réseaux | 2 | oui | — | ✅ visible |
| 68 | Office de l'eau Réunion — Chroni | fiche Réseaux (ANC, 6 communes) | clic parcelle→Réseaux | 2 | oui | FIABILITÉ À CONFIRMER | ✅ visible |
| 21 | SIRENE | outil Scan patrimoine + Copilote | Outils→Scan patrimoine | 2 | oui | — | ✅ visible |
| 20 | BPE INSEE | carte (Équipements BPE) + fiche | COUCHES→Équipements (BPE) | 2 | oui | — | ✅ visible |
| 52 | Filosofi INSEE (carreaux 200 m) | outil Étude de zone | Outils→Étude de zone | 2 | oui | — | ✅ visible |
| 74 | Transport public — GTFS (PAN, 7  | carte (Transport public) | COUCHES→Transport public | 2 | oui | — | ✅ visible |
| 17 | BD TOPO IGN | carte (bâti/voirie) + fiche | COUCHES→bâti BD TOPO | 2 | oui | — | ✅ visible |
| 83 | CoSIA (couverture du sol IA, IGN | fiche (bâti) + scoring | clic parcelle (bâti) | 2 | oui | — | ✅ visible |
| 70 | LiDAR HD — MNH 50 cm (IGN) | fiche Le bien (hauteur) — créditée BD TOPO | clic parcelle→Le bien | 2 | oui | — | ✅ visible |
| 141 | LOVAC (logements vacants) | AUCUNE — non ingérée (convention) | — catalogue /sources seul | ∞ | oui | ACCÈS SOUS CONVENTION | 🔴 INVISIBLE (fonctionnel) |

## Résultat

- **28 / 30 visibles fonctionnellement** en **1 à 3 clics** : couche carte (1-2), outil (2),
  section de fiche (2), Radar/Scan (1-2). Le `i` nomme la source et, sur la fiche, le millésime.
- **2 / 30 INVISIBLES fonctionnellement** — leur donnée n'atteint **aucune** surface parcelle /
  carte / outil ; elles n'existent que comme **ligne du catalogue /sources** :
  - **DVF Réunion (Région, 119)** — doublon de DVF Etalab, servi **uniquement** comme échantillon
    du filtre producteur. Le client voit DVF Etalab, jamais celui-ci. (Rejoint son verdict CSV
    *SERVIE HORS REGISTRE* + le doublon S3.)
  - **LOVAC (141)** — **non ingérée** (accès sous convention). Rien à afficher ; seule la ligne
    catalogue « ACCÈS SOUS CONVENTION » existe. (Idem **Fichiers fonciers (27)** et **DV3F
    (142)**, mêmes conventions non instruites — non tirées dans l'échantillon mais identiques.)

## Le verdict corrigé « invisible »

« 0 invisible » **était** un artefact : le graphe registre → robinet ne peut pas produire
d'invisible. Au vrai navigateur, deux visibilités se séparent :

- **Transparence — excellente** : les 95 sont sur /sources avec source, licence, fraîcheur et
  drapeau de fiabilité. Un pro *sait* qu'une source existe et d'où elle vient en 2 clics.
- **INVISIBLES fonctionnelles — au moins 5** (dont la donnée n'atteint aucune surface d'usage,
  seulement le catalogue) : **DVF Région (119)**, **LOVAC (141)**, **Fichiers fonciers (27)**,
  **DV3F (142)** — et, *en pratique*, **DPE ADEME (37)** : « connecté » mais `dpe_records = 17`,
  `v_passoire_thermique = 1` → la donnée n'apparaît sur quasi aucune fiche. C'est l'invisible le
  plus trompeur : listé, daté, drapeau « à jour », mais **vide**.

**À réparer** (REPARATIONS.md) : (1) trancher DVF Région (témoin discret hors vitrine, ou
retrait) ; (2) marquer clairement au client les 3 conventionnées comme « donnée non disponible,
en attente de convention » plutôt que simple ligne catalogue ; (3) réparer l'ingestion **DPE**
(17 records) — priorité, car c'est le seul « listé + daté + à jour » dont la donnée est absente.

## Limite du test

Échantillon de 30 (toutes familles) ; les chemins de clics sont les chemins canoniques observés,
pas une exploration exhaustive de chaque variante d'UI. Les captures par surface (11) couvrent
les 30 ; je n'ai pas produit 30 captures quasi-identiques de la même page /sources. La preuve
« la donnée s'affiche sur la parcelle » a été vérifiée sur les surfaces (fiche, COUCHES, outils
Taxe/Scan/Pièges/Communes/Faisabilité ouverts) — la sélection d'une parcelle dans chaque outil
pour chacune des 30 n'a pas été automatisée (les outils affichent « Cliquez une parcelle » puis
rendent la donnée).
