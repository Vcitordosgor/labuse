# Pièges et risques

Clé interne : `risques` (num M10) · composant : `frontend/src/components/outils/ModulePanel.tsx:1862` (`function Risques`) → `frontend/src/components/outils/blocB.tsx:39` (`O5Servitudes`) · endpoint : `GET /servitudes-invisibles/{idu}` (back : `src/labuse/api/servitudes.py:452`)

> Outil issu de la fusion de « Contrôle avant achat » (M10) et « Servitudes invisibles » (O5). Le mode « un lot » (jusqu'à 60 parcelles) a été **retiré** du menu (`ModulePanel.tsx:1864-1866`) ; il ne reste plus qu'une seule voie : **« une parcelle »**. La fonction `M10`/`duediligence` reste exportée pour son test unitaire mais n'est plus câblée. La fiche décrit donc UNE voie.

---

## 1. À quoi il sert, et pour qui
Pour un acheteur/promoteur qui veut savoir « qu'est-ce qui peut bloquer un projet sur cette parcelle ? » : l'outil révèle les servitudes et contraintes **dormantes** (celles qui n'apparaissent pas spontanément sur une fiche) qui intersectent la parcelle — PPR, 50 pas, préemption, zones humides, prescriptions PLU, aléas, etc. Il est 100 % lecture (couches déjà ingérées), chaque ligne portant sa source et sa date, et il **dit explicitement** ce qui n'est PAS couvert plutôt que de montrer un faux « rien à signaler ».

## 2. Le parcours
Un seul écran, dans le panneau « Outils » :
1. **Entrée parcelle** (`blocB.tsx:68`, composant `EntreeParcelle`) : l'utilisateur tape une adresse / un IDU / une référence courte, OU clique une parcelle sur la carte. La saisie zoome + surligne le contour SANS ouvrir la fiche (`allerA`, `blocB.tsx:56`) ; le clic carte (`selectedIdu`) déclenche l'analyse. La requête part quand l'IDU fait exactement 14 caractères (`blocB.tsx:60`).
2. **Résultat** (`blocB.tsx:72-154`) :
   - un compteur « **N contrainte(s) relevée(s) sur la parcelle** » (N = nombre de catégories, après regroupement — `blocB.tsx:90-93`) ;
   - éventuellement une carte « **Procédure PLU en cours** » (révision/élaboration active, lue du radar PLU — `blocB.tsx:96-104`) ;
   - **une carte par catégorie** de contrainte : titre, badge (« sourcé » ou, si rédhibitoire, « Inconstructible (partie rouge) » en rouge), la ou les phrases d'effet, la source + le millésime (`blocB.tsx:108-120`). Les cartes rédhibitoires remontent en tête (`blocB.tsx:87`) ;
   - un bloc « **Vérifié, rien à signaler** » : les familles de contraintes réellement examinées qui n'ont rien remonté (puces — `blocB.tsx:126-138`) ;
   - une ligne « **Non couvert** » fixe, avec un « i » inline qui détaille les couches non ingérées (`blocB.tsx:146-153`) ;
   - un avertissement général (« l'absence ici ne vaut pas absence réelle… vérifiez le certificat d'urbanisme »).

## 3. Les données lues
L'endpoint lit les couches intersectant la parcelle dans la table **`spatial_layers`** (clé géométrique `geom_2975`, filtre `ST_Intersects`), chaque ligne étant jointe à **`data_sources`** pour sa source et son millésime. Les kinds lus sont listés dans `_KINDS` (`servitudes.py:33-56`). Le PPR/aléas est lu à part, en direct, par `aleas_parcelle` (`servitudes.py:280`) qui peut lire **`tuyau_subdivise`** (partition subdivisée, plus rapide, présente en base) au lieu de `spatial_layers` — mêmes %, mêmes résultats (`_table_aleas`, `servitudes.py:259`). Une 2ᵉ source est **`parcel_au_statut`** (zone AU fermée — `servitudes.py:435`) et une 3ᵉ est **`labuse.veille_plu`** (procédure PLU — `servitudes.py:467`).

| Catégorie affichée | kind `spatial_layers` | Source (`data_sources.name` du catalogue) | Millésime servi | Cadence |
|---|---|---|---|---|
| 50 pas géométriques | `cinquante_pas` (163) | `50 pas géométriques — limite haute (DEAL)` | cadastre 1877 (géoréf. 2012/1950) | (vide) |
| Classement sonore des voies | `bruit_route` (1004) | `Classement sonore ITT (Cerema)` | arrêtés déc. 2023 | (vide) |
| Secteur d'information sur les sols / CASIAS | `sol_pollue` (531) | `Géorisques — CASIAS` / `Géorisques — SIS` | 453 CASIAS / 4 SIS (07/09/2026) | (vide) |
| Recul du trait de côte | `trait_de_cote` (24168) | `Cerema / GéoLittoral — indicateur d'érosion côtière` | millésime 2018 | (vide) |
| Assainissement non collectif (ANC) | `zonage_assainissement` (258) | `GPU — zonages d'assainissement` | SIG 4/24 au 11/07/2026 | (vide) |
| ZNIEFF | `znieff` (162) | `ZNIEFF (INPN/MNHN)` | mise à jour 29/08/2025 | (vide) |
| Droit de préemption (DPU) | `dpu` (202) | `GPU — droit de préemption urbain (info-surf)` | GPU typeinf 04 — partiel | (vide) |
| Ravines / domaine public fluvial | `dpf` (281) | `Ravines — domaine public fluvial (DEAL Carmen)` | DPF arrêté 06-3077 du 21/08/2006 | (vide) |
| Zone humide | `zone_humide` (3122) | `Zones humides — inventaires DEAL (Carmen)` | inventaires 2003/2009/2011/2019 (partiels) | (vide) |
| Espace naturel protégé | `ens` (411) | `Espaces protégés complémentaires…` / INPN | (variable par entité) | (vide) |
| Prescription PLU (constructibilité) | `plu_gpu_prescription` (10490) | `GPU — emplacements réservés` / `GPU — espaces boisés classés` / `Urbanisme PLU/GPU (API Carto)` | GPU/PLU par commune (révisions) | (vide) |
| Plan d'exposition au bruit (PEB) | `peb` (12) | `PEB — plans d'exposition au bruit (DGAC via annexes GPU)` | Roland-Garros B/C/D (GPU) | (vide) |
| Mesure compensatoire (ERC) | `mesures_compensatoires` (24) | `GéoMCE — mesures compensatoires` | géoportail national | (vide) |
| SUP (servitude d'utilité publique) | `sup` (417) | `SUP — assiettes GPU (API Carto)` + décodage interne (`_SUP`) | (pm1/pm2/pm3/ac1-4/el10…) | (vide) |
| PPR zoné rouge/bleu + aléas par niveau | `ppr` (164) / `georisque_alea` (1093), via `tuyau_subdivise` | `DEAL Réunion — PPR / aléas` | PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Réunion) | (vide) |
| Zone AU fermée/statut inconnu | table `parcel_au_statut` (pas `spatial_layers`) | `LABUSE — moteur d'ouverture AU (règlement PLU calibré)` | pas de millésime (calculé) | — |
| Procédure PLU en cours | table `labuse.veille_plu` (radar) | `Sudocuh (procédures d'urbanisme)` | Sudocuh état au 31/12/2024 | (vide) |

*(Comptages réels issus de `psql ... spatial_layers GROUP BY kind` — voir §9. La colonne `source_cadence` est VIDE pour toutes ces sources en base : aucune cadence n'est servie.)*

Le millésime affiché n'est pas brut : il passe par `millesime_source.libelle_date_source` (`servitudes.py:21`, appelé `servitudes.py:318/361/418`). Règle : « millésime \<X\> » si la source a un `source_millesime` publié, sinon « ingéré le JJ/MM/AAAA » (date de dernier sync).

## 4. Les calculs
L'outil ne « calcule » presque rien — il lit des intersections géométriques. Les seules opérations numériques :

- **% de parcelle touché** (PPR et aléas) : `round(100 * ST_Area(ST_Union(ST_Intersection(couche, parcelle))) / ST_Area(parcelle))` en entier (`servitudes.py:306` et `:343`). Un `pct <= 0` (intersection au bord, aire arrondie à 0) est **ignoré** comme bruit (`servitudes.py:314`, `:351`).
- **Classification PPR rouge/bleu** : via la fonction SQL `labuse_ppr_couleur(subtype, attrs)` (présente en base). « bleu » = prescription ; tout le reste (interdiction OU code non classé) = **rouge** par prudence (`servitudes.py:303`). La part rouge est déclarée **inconstructible quelle que soit la surface** (`redhibitoire=True`, `servitudes.py:327`) — plus de seuil 50 % (doctrine Vic, commentaire `servitudes.py:298-300`).
- **Seuils PPR** (`_risque_seuils`, `servitudes.py:224`) : `ppr_red_marginal_pct=2`, `ppr_red_exclude_pct=50`, `min_coverage_pct=10`. **Origine** : lus de la config partagée `cascade_rules.yaml` couche `risques` ; repli codé en dur `(2.0, 50.0, 10.0)` si config absente. *(Dans le code actuel ces seuils sont définis mais `_risque_seuils` n'est PAS appelé dans `aleas_parcelle` — la décision rouge = inconstructible est prise sans seuil ; voir §10.)*
- **Rang des niveaux d'aléa** (`_NIVEAU_RANK`, `servitudes.py:220`) : faible=1, moyen/modéré=3, élevé=4, fort=5, très fort=6 — sert à **trier** les niveaux par type décroissant, pas à masquer (tous les niveaux sont affichés).
- **Exposition totale** par type d'aléa = somme des % de ses niveaux, plafonnée à 100, notée sur la ligne du niveau le plus fort si ≥ 2 niveaux (`servitudes.py:357,363`).
- **Dédoublonnage** : clé `(kind, détail)` (`servitudes.py:412`), et côté front regroupement par catégorie (`blocB.tsx:77-87`). Deux enveloppes SUP identiques = une ligne.

Filtres appliqués (une contrainte n'est servie que si pertinente) :
- assainissement : **seul le non-collectif** `anc` passe ; le collectif (raccordé) est le cas favorable, filtré (`servitudes.py:406`) ;
- prescriptions PLU : seuls les typepsc « pièges fonciers » `_PRESCRIPTION_PIEGE = {01,05,08,15,17,18,19,22}` (`servitudes.py:66`, `servitudes.py:409`) ;
- SUP `pm1` (enveloppe PPR) **masquée** si le PPR zoné rouge/bleu est déjà servi, pour éviter le double comptage (`servitudes.py:401`).

« Vérifié, rien à signaler » (`familles_verifiees`, `servitudes.py:139`) : les 10 familles de `_FAMILLES_VERIFIEES` (`servitudes.py:125-136`) sont testées par **sous-chaîne** dans le texte des contraintes remontées ; une famille sans correspondance = examinée et claire → listée en puce.

## 5. Chaque chiffre / élément affiché
| Libellé à l'écran | D'où il vient | Sourcé / estimé |
|---|---|---|
| « N contrainte(s) relevée(s) » | `groupes.length` = nb de catégories après regroupement front | sourcé (dérivé du nb de couches intersectées) |
| Nom de catégorie (ex. « 50 pas géométriques ») | `_KINDS` (`servitudes.py:33`) | sourcé (libellé fixe mappé au kind) |
| Effet / phrase (ex. « Emplacement réservé — … ») | `_detail()` (`servitudes.py:151`) à partir de `subtype`/`name`/`attrs` de la couche | sourcé (texte composé à partir des attributs de la donnée) |
| « zone rouge sur X % de la parcelle » / « X % » | calcul SQL d'intersection (`servitudes.py:306`) | sourcé (mesure géométrique) |
| « niveau fort / moyen / faible » | `attrs->>'niveau'` de `georisque_alea` | sourcé |
| Badge « Inconstructible (partie rouge) » | `redhibitoire` = couleur rouge PPR (`servitudes.py:327`) | estimé (règle interne : rouge ⇒ interdiction) |
| Badge « sourcé » | fixe sur toute carte non rédhibitoire (`blocB.tsx:115`) | — (libellé UI, pas une donnée) |
| Source (ex. « DEAL Réunion — PPR / aléas ») | `data_sources.name` | sourcé |
| Millésime / « millésime … » / « ingéré le … » | `libelle_date_source` (`source_millesime` ou `last_sync_at`) | sourcé |
| Carte « Procédure PLU en cours » (libellé, stade, date) | `veille_plu.entry()` (radar Sudocuh) | sourcé |
| Puces « Vérifié, rien à signaler » | `familles_verifiees` (déduites par absence) | estimé (c'est une déduction « rien trouvé », pas une donnée positive) |
| Ligne « Non couvert » + « i » | `NON_COUVERT` (`servitudes.py:109`), texte fixe | estimé (constat de lacune codé en dur) |

## 6. Les limites
- **Non couvert explicite** (`NON_COUVERT`, `servitudes.py:109-116`) : canalisations de transport de matières dangereuses (non ingérées) ; SUP non publiées au Géoportail de l'urbanisme. Le certificat d'urbanisme reste indispensable.
- **Faux RAS évité mais non garanti** : l'outil ne déclare « rien à signaler » que sur des familles dont la couche est **réellement peuplée** (anti-« couvert-vide », commentaire `servitudes.py:28-32`). Mais si une couche est **incomplète géographiquement** (ex. DPU « partiel », zones humides « partiels », GPU 4/24 communes pour l'assainissement), une parcelle réellement concernée peut passer « clair » sans que l'outil le signale par parcelle.
- **Dépend du GPU** : prescriptions PLU, DPU, EBC, ER, PEB viennent du Géoportail de l'urbanisme — une commune mal publiée = données manquantes silencieuses.
- **PPR rouge = inconstructible dès 1 %** : la part rouge est marquée rédhibitoire quelle que soit sa surface ; un bord de zone rouge à 1-2 % affichera « Inconstructible (partie rouge) » (choix doctrinal assumé, peut surprendre).
- **Codes non reconnus** : un SUP ou typepsc inconnu est affiché brut (« SUP ZZ9 ») — honnête mais peu lisible.
- **Pas d'exhaustivité** : le nom « Pièges et risques » ne promet pas un contrôle complet ; cavités, ICPE Géorisques, mouvements de terrain hors PPR, etc. ne sont lus que s'ils existent comme kind ingéré (ICPE/cavités/mouvements **ne figurent pas** dans `_KINDS` sauf via `georisque_alea`/SUP pm2 — voir doute §10).

## 7. Les tests
`tests/test_servitudes.py` (203 lignes) :
- décodage `_detail` par kind : SUP pm1/i3/inconnu (`:15-34`), sol pollué SIS (`:24`), bruit catégorie (`:28`), ZNIEFF type I/II (`:41`), PEB (`:52`), nouveaux kinds dpu/dpf/zone_humide/ens/prescriptions (`:67-85`) ;
- `_PRESCRIPTION_PIEGE == {01,05,08,15,17,18,19,22}` figé (`:80`) et 07/16 exclus ;
- `NON_COUVERT` liste bien les manques, et RNIC/copropriété/PEB en SONT sortis (`:37-64`) ;
- flux complet `servitudes_invisibles` : dédup gen1+gen2 = 1 ligne, source+date présentes (`:94-117`) ;
- `test_flux_ras_honnete` : parcelle vide → `n=0`, « Aucune servitude », avertissement présent (`:191-203`) ;
- `test_lotB_ppr_gradue_alea_deux_modes_et_fiche` : PPR bleu + aléa par niveau remontent, et **la fiche §Pièges & risques rend EXACTEMENT la même liste** (`_aleas_block == contraintes`, `:160-185`) ;
- garde-fou : l'outil « un lot » ne lit plus la cascade et partage `contraintes_parcelle` (`:140-158`).

**Ce qu'aucun test ne vérifie** : le composant front `O5Servitudes` (aucun `.test.tsx` trouvé) — regroupement par catégorie, tri rédhibitoire, carte procédure PLU, « i » non couvert ne sont pas testés. `familles_verifiees` n'a pas de test dédié. Le choix `tuyau_subdivise` vs `spatial_layers` et l'égalité des % entre les deux ne sont pas testés ici (couverts ailleurs, selon le commentaire). La classification `labuse_ppr_couleur` (fonction SQL) n'est pas testée dans ce fichier.

## 8. Les documents liés (PDF, exports)
L'outil « une parcelle » n'a **pas de PDF propre**. La donnée est toutefois **partagée** : `contraintes_parcelle` et `aleas_parcelle` sont le **point de vérité unique** utilisé aussi par la fiche parcelle §Pièges & risques et par l'ancien export « un lot » (`modules.duediligence`, docstring `servitudes.py:373-380`). Le test `test_lotB_...` prouve que `app._aleas_block` (bloc de la fiche/PDF) rend la **même liste de libellés** que l'outil. Donc le PDF de la fiche lit **les mêmes valeurs** que cet écran — c'est garanti par construction et par test.

## 9. Trois cas rejoués
Entrées = IDU des 3 parcelles témoins ; sorties = `curl http://127.0.0.1:7300/servitudes-invisibles/{idu}` (bruts résumés).

**97415000DH0076 (Saint-Pierre/Joseph, littoral) — n=10** (témoin « 10 servitudes » confirmé) :
- 50 pas géométriques (Étude documentaire Février 2026) ;
- DPU (préemption urbaine) ;
- Prescription PLU : OAP 2.2 L'Ermitage-les-Bains ; Clause logements aidés (mixité sociale) ;
- Recul trait de côte ×2 (taux −0.116 et −0.253 m/an, Cerema 2018) ;
- PPR inondation+mouvement : zone **rouge 2 %** (`redhibitoire:true`, inconstructible) + zone bleue 98 % ;
- Aléa inondation : fort ~2 % (exposition totale ~100 %) + moyen ~98 %.
- `verifie` = [Sols pollués, Bruit, Assainissement, ICPE, Monuments et sites, ER/EBC, Espaces naturels] ; `procedure_plu`=null ; `non_couvert` = 2 lignes.

**97411000BZ1065 (Saint-Denis) — n=3** :
- Assainissement non collectif (ANC) ; DPU ; PPR inondation+mouvement zone **bleue 100 %** (sous prescriptions, non rédhibitoire).
- `verifie` = [Sols pollués, Bruit, ICPE, Monuments et sites, ER/EBC, Eau et zones humides, Espaces naturels] ; `procedure_plu`=null.

**97409000AK0804 (Saint-André) — n=6** :
- PPR inondation+mouvements : zone **rouge 12 %** (rédhibitoire) + zone bleue 88 % ;
- Aléa inondation : fort ~12 % (expo totale) + faible ~88 % ; Aléa mouvement de terrain : moyen ~12 % + faible ~88 %.
- `verifie` = 9 familles ; **`procedure_plu` renseignée** : « Révision générale du PLU — prescrite », source « Sudocuh 31/12/2024 (prescription) », date 2022-06-22, constat 2026-08-06. *(Montre bien le chemin radar PLU actif.)*

*(Note : le backend était par moments injoignable — HTTP 000 ; une boucle d'attente a été nécessaire avant d'obtenir ces sorties, mais les trois ont bien été rejouées.)*

## 10. Tes doutes (par gravité)
1. **Couverture incomplète non signalée par parcelle (le plus grave).** Plusieurs couches sont partielles (DPU « partiel non-publiées listées », zonage assainissement GPU « 4/24 communes », zones humides « inventaires partiels »). L'outil affiche ces familles dans « Vérifié, rien à signaler » même quand **aucune donnée n'existe pour la commune** de la parcelle. C'est un faux RAS par zone blanche que le mécanisme anti-« couvert-vide » (qui vérifie seulement que la couche a ≥ 1 ligne **sur l'île**) ne détecte pas.
2. **ICPE / cavités / mouvements de terrain (hors PPR) absents de `_KINDS`.** La fiche demande explicitement ces catégories. Elles ne sont lues qu'indirectement : ICPE via SUP `pm2`, mouvements via `georisque_alea`/PPR. Les cavités souterraines Géorisques n'ont **aucun kind** dans `_KINDS` — pas de ligne « cavités » possible, alors que la famille « ICPE » apparaît en puce « vérifié » même sans couche ICPE dédiée.
3. **Seuils PPR définis mais inutilisés dans la décision.** `_risque_seuils` (2/50/10 %) est lu de la config mais `aleas_parcelle` ne l'appelle pas : la règle « rouge ⇒ inconstructible dès 1 % » ignore `ppr_red_marginal_pct=2`. Une zone rouge à 1 % (potentiellement du bruit d'intersection) est donc affichée « Inconstructible » — incohérence avec le commentaire qui annonce les seuils « mêmes valeurs que le moteur ».
4. **Millésime « cadastre 1877 » pour les 50 pas affiché tel quel.** Le libellé composé donne « millésime cadastre 1877 (géoréf. 2012/1950) » — exact mais trompeur pour un non-codeur (donnée réactualisée par étude documentaire 2026, visible dans l'effet mais pas dans le millésime).
5. **Dépendance à une fonction SQL (`labuse_ppr_couleur`) non testée côté Python.** La classification rouge/bleu (et donc le drapeau rédhibitoire qui pilote tout l'affichage critique) repose sur une fonction SQL en base ; si elle est absente ou modifiée, la requête échoue ou reclasse — aucun test de `test_servitudes.py` ne couvre cette fonction directement.

---

## Synthèse INDEX
- Fiche écrite : `docs/audit-2026-11/outils-fiches-1/risques.md`.
- Outil « Pièges et risques » (clé `risques`, M10) = fusion Contrôle avant achat + Servitudes invisibles ; **mode « un lot » retiré**, il ne reste que « une parcelle ». Front `blocB.tsx:39` (`O5Servitudes`), back `servitudes.py:452`, endpoint `GET /servitudes-invisibles/{idu}`.
- Données : tout vient de `spatial_layers` (∩ parcelle, `ST_Intersects`) joint à `data_sources` ; 16 kinds (PPR, aléas via `tuyau_subdivise`, 50 pas, DPU, DPF/ravines, zones humides, ENS, prescriptions PLU, PEB, ERC, SUP, bruit, sol pollué, trait de côte, ZNIEFF) + `parcel_au_statut` (AU) + `labuse.veille_plu` (procédure PLU). Comptages réels vérifiés en base.
- Calculs minimes : % de parcelle touché (ST_Intersection/ST_Area), classification PPR rouge/bleu via fonction SQL `labuse_ppr_couleur`, tri niveaux d'aléa, dédup (kind, détail).
- Part sourcé vs estimé : ~85 % **sourcé** (chaque ligne = couche réelle + source + millésime datés). Estimé : le drapeau « Inconstructible/rédhibitoire » (règle interne rouge⇒interdiction), les puces « Vérifié, rien à signaler » (déduction par absence) et le bloc « Non couvert » (constat codé en dur).
- 3 témoins rejoués (curl réel) : DH0076 n=10 (dont PPR rouge 2 %), BZ1065 n=3 (PPR bleu 100 %), AK0804 n=6 (PPR rouge 12 % + procédure PLU « Révision prescrite » active).
- Tests : `tests/test_servitudes.py` solide sur back (décodage, dédup, RAS honnête, fiche==outil) ; **aucun test front**, pas de test de `familles_verifiees` ni de `labuse_ppr_couleur`.
- Doute le plus grave : **faux RAS par zone blanche** — les couches partielles (DPU, assainissement 4/24 communes, zones humides) apparaissent en « Vérifié, rien à signaler » même là où aucune donnée n'existe pour la commune ; l'anti-« couvert-vide » ne vérifie la présence qu'à l'échelle de l'île, pas de la parcelle.
