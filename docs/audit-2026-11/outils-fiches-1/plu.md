# PLU

Clé interne : `plu` (num O13) · composant : `frontend/src/components/outils/Plu.tsx` → `frontend/src/components/outils/PluAnnuaire.tsx` · endpoint(s) : `GET /modules/plu-annuaire/communes`, `GET /modules/plu-annuaire/search`, `GET /modules/plu-annuaire/pack/{insee}`

> Audit lecture seule. Chemins relatifs à `/Users/openclaw/Desktop/labuse-fiches`, lignes réellement ouvertes. Chiffres « rejoués » = sorties `curl`/`psql` copiées telles quelles (backend `:7300`).

---

## 1. À quoi il sert, et pour qui
L'outil PLU est un **annuaire de règlements d'urbanisme** : il laisse l'utilisateur choisir une des 24 communes de La Réunion, télécharger le PLU intégral (pack officiel GPU) et surtout **chercher du verbatim opposable** (article, page PDF, lien) dans le règlement écrit. Il s'adresse à un porteur de projet ou un professionnel qui veut lire le texte exact d'une règle (hauteur, clôture…) sans ouvrir un PDF de 300 pages ni se fier à un résumé.

## 2. Le parcours

### Chemin unique : l'Annuaire
L'outil n'a **qu'une voie** (`Plu.tsx:5-16` : la voie « Procédure & changement » a été **décâblée**, voir §6).

- **Écran 1 — les 24 communes** (`PluAnnuaire.tsx:70-123`). Un bandeau dit « N PLU en vigueur (24 communes, N au RNU) » puis la liste cliquable des 24. Chaque carte porte le nom de commune ; un badge ambre dit « révision » (procédure en cours), « RNU » ou « non servi » selon le cas. Aucune carte n'est éteinte : une commune sans règlement servi reste cliquable.
- **Écran 2a — commune servable** (`PluAnnuaire.tsx:157-170`). Deux voies : *« Télécharger le PLU intégral (.zip) »* (lien direct vers le pack GPU, `cur.source_url`) ou *« Rechercher dans le PLU »*.
- **Écran 2b — recherche** (`PluAnnuaire.tsx:173-253`). Champ texte (min. 2 caractères, `PluAnnuaire.tsx:35`), bouton « Chercher ». Le résultat est une liste de cartes d'extrait : numéro d'article (vert), zone + commune en puces, titre « en clair », aperçu 3 lignes dépliable (« Lire tout ▾ »), pied « Règlement du jj/mm/aaaa · p. N · PDF ↗ ». Si la page est plafonnée : « N extraits affichés sur M ».
- **Écran 2c — commune non servable** (`PluAnnuaire.tsx:137-154`). RNU → lien Légifrance (règlement national). Révision → tentative de résoudre le PLU **en vigueur** en direct sur le GPU (`PackVigueur`, `PluAnnuaire.tsx:310-344`), avec 3 issues distinctes : trouvé (lien .zip), GPU vide (on le dit + coordonnées mairie), GPU injoignable (dit comme tel).

Deep-link : ouvert depuis une fiche parcelle / le Copilote avec `pluPrefill {insee, zone}`, l'outil entre **directement en mode recherche** sur la commune et filtre sur la zone (`PluAnnuaire.tsx:38-45`).

## 3. Les données lues

| Source (catalogue `data_sources.name`) | Table SQL / fichier réellement lu | Millésime servi | Cadence |
|---|---|---|---|
| **Urbanisme PLU/GPU (API Carto)** — « GPU/PLU par commune (révisions — détail en fiche) » | Règlements PDF ingérés → table **`plu_reglement_extrait`** (`plu_ingest.py:17-34`) ; recherche FTS `plu_ingest.py:206-229` | par commune (ex. Saint-Denis 2026-08-05, Saint-Paul 2025-12-17) | révisions (pas de fréquence fixe) |
| **Urbanisme PLU/GPU (API Carto)** (idem, résolution live) | API GPU `.../api/document?grid=<insee>` appelée **en direct** pour le pack .zip (`modules.py:2864-2891`) | version EN_VIGUEUR / plus récente, lue à l'instant | temps réel (au clic) |
| **Sudocuh (procédures d'urbanisme)** — « état au 31/12/2024 » | `config/veille_plu.yaml` via module `labuse.veille_plu` (`commune.py:234, 273-279`) | 31/12/2024 + curation trimestrielle | annuelle (Sudocuh) / curation trimestrielle |
| (vérité millésime/statut par commune) | `config/plu_millesimes.yaml` via `_plu_millesimes()` (`modules.py:2819-2826`) | relevé 13/07 + ré-extractions M32 (05/08) + M40 (06/08) | révisions |
| **Annuaire de l'administration (service-public.fr / DILA)** — « 24 mairies (OUTILS K2) » | table **`mairies`** (`modules.py:2861-2863`), repli quand le GPU est vide | — | — |
| (zone contextuelle, enrichissement) | `config/plu_destinations/<insee>_*.yaml` via `faisabilite.zonage.resolve_zone` (`modules.py:2997-2999`) — seulement si `zone` fourni | par commune | — |

Remarques :
- Le texte des règles n'est **pas** stocké en PDF : seuls des **extraits article** (verbatim brut) sont rangés en base par `plu_ingest.py`. Le « PLU intégral » téléchargeable renvoie au pack officiel GPU (aucun PDF hébergé par LABUSE, `commune.py:247-249`).
- Le statut d'une commune (`servable` / `revision` / `rnu` / `non_ingere`) est calculé en croisant `plu_reglement_extrait` (ce qui est ingéré) avec `plu_millesimes.yaml` (`commune.py:238-262`).
- En base : **3258 extraits**, **21 communes** ingérées, **11 avec doute** (`psql` sur `plu_reglement_extrait`).

## 4. Les calculs
L'outil ne fait **aucun calcul d'urbanisme** (pas de hauteur, pas de densité, pas de surface) : il sert du texte sourcé. Les seuls traitements sont de la recherche et de la mise en forme.

- **Recherche plein texte** (`plu_ingest.py:206-229`). Requête `websearch_to_tsquery('french', q)` sur la colonne `tsv` (index GIN). Tri `ts_rank DESC, insee, page_pdf`. Plafond `limit` (défaut 25, max 200, `modules.py:2957`). `n_total` = `count(*)` **sans** plafond (`plu_ingest.py:232-246`) → l'écran dit « N affichés sur M ».
- **Titre « en clair »** (`modules.py:2921-2952`, `plu_titre_corps`). Heuristique PURE (aucune ré-ingestion) : retire la référence d'article en tête, détecte un en-tête TOUT EN MAJUSCULES comme titre, remet en casse de phrase si > 70 % des lettres sont capitales (`modules.py:2916`), coupe au sous-article (regex `\d{1,2}\.\d{1,2}`). `corps` = verbatim privé du titre (aperçu 3 lignes).
- **Doute** (`plu_ingest.py:109-114`). Drapeau posé à l'**ingestion** si le texte de l'article fait < 25 caractères non-blancs (« page peut-être illisible/scannée »). Constante `25` codée en dur.
- **Pagination ambiguë** (`plu_ingest.py:58-73`). Heuristique document : vrai si la suite des numéros imprimés ré-décroît franchement (pic ≥ 8 puis retombe ≤ 3 au-delà du 1er quart) → une « p. N » peut désigner deux endroits. Constantes `8`, `3`, `len/4` codées en dur.
- **Pack en vigueur** (`modules.py:2881-2891`). Tri des documents GPU : EN_VIGUEUR d'abord, sinon `originalName` le plus récent ; le millésime est extrait du suffixe `AAAAMMJJ` de l'`originalName` (`modules.py:2886`).

Pas d'arrondi, pas de barème légal appliqué. La seule constante de barème (seuils de doute/pagination) vient du **code**, pas d'une config servie ni d'un texte réglementaire.

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| « N PLU en vigueur (24 communes, N au RNU) » | `n_plu_vigueur` = `n_communes − n_rnu` (`modules.py:2843`), comptés sur statut réel (`commune.py:280-284`) | sourcé |
| Badge « révision » sur une carte | `procedure_active` lu dans `veille_plu.yaml` (Sudocuh) si procédure active (`commune.py:273-279`) | sourcé |
| Badge « RNU » / « non servi » | `statut` calculé (`commune.py:250-262`) | sourcé |
| « PLU du jj/mm/aaaa » (en-tête commune) | `cur.millesime` = `max(millesime)` des extraits en base (`plu_ingest.py:255`) | sourcé |
| « N extraits affichés sur M » | `n` = `len(resultats)`, `n_total` = `count(*)` FTS (`modules.py:3009`) | sourcé (compte DB) |
| Numéro d'article (vert) | `article_ref` extrait du PDF à l'ingestion (`plu_ingest.py:100`) | sourcé |
| Zone (puce) | `zone` déduite de l'en-tête article/zone à l'ingestion (`plu_ingest.py:103-106`) | sourcé, mais **heuristique** (voir §6) |
| Titre « en clair » | `plu_titre_corps` sur le verbatim (`modules.py:2921`) | **estimé** (reformatage heuristique du verbatim) |
| Corps / aperçu / « Lire tout » | `texte_verbatim` brut du PDF (`plu_ingest.py:102`) | sourcé (verbatim) |
| « Règlement du … · p. N » | `millesime` + `page_pdf` (PAGE PDF, pas page imprimée) de l'extrait (`plu_ingest.py:111`) | sourcé |
| « doute — vérifier au PDF » | drapeau `doute` posé à < 25 car. non-blancs (`plu_ingest.py:109`) | **estimé** (heuristique) |
| « ⚠ pagination … » | `pagination_ambigue` (heuristique document, `plu_ingest.py:58`) | **estimé** (heuristique) |
| Pack « version du jj/mm/aaaa » | suffixe `AAAAMMJJ` de l'`originalName` GPU (`modules.py:2886-2889`) | sourcé (live GPU) |
| Exception « zone N — … » | `resolve_zone(...).exceptions` lu dans `plu_destinations/*.yaml` (`modules.py:2997-3004`) | sourcé (config calibrée) |

## 6. Les limites
- **La voie « Procédure & changement » est retirée** (`Plu.tsx:5-16`, décision Vic RECETTE-OUTILS-2 R4). Le simulateur d'ouverture d'une zone AU (densité médiane des zones U appliquée à une AU) était une **analogie jugée non fiable**. Le composant `ProcedureChangement.tsx` et ses endpoints **existent toujours au dépôt mais ne sont plus montés** par l'outil PLU ; les anciens deep-links (`pluVue` procedure/changement) retombent sans 404 sur l'Annuaire. Les tests front `PluPagination.test.tsx` testent encore ce chemin retiré (via `M15` de `moteurs.tsx`), pas l'Annuaire servi.
- **Couverture incomplète du corpus** : 21/24 communes ingérées. Saint-André (97409) et Saint-Leu (97413) sont en révision et **non servis** (0 extrait) ; Saint-Philippe (97417) est au RNU (pas de PLU). La recherche sur ces communes renvoie un message honnête, jamais un résultat vide trompeur.
- **Profondeur très inégale** : le nombre d'extraits va de **8** (Saint-Benoît) à **434** (Saint-Paul). Saint-Benoît n'a que 8 extraits alors que son PLU existe — l'ingestion a manifestement raté la majeure partie du document (découpage article par regex défaillant), mais rien à l'écran ne l'indique. Une recherche à Saint-Benoît peut donc « ne rien trouver » sur un texte qui existe.
- **Zone, titre, doute, pagination = heuristiques** (regex / seuils codés en dur). Une zone mal détectée, un titre mal coupé ou un faux « doute » sont possibles. Le `doute` ne couvre que le cas « page quasi vide », pas une mauvaise OCR d'un texte dense.
- **Le verbatim dépend du PDF d'origine** : page citée = **page PDF**, pas page imprimée (dit explicitement en cas de double numérotation). Aucun surlignage de l'occurrence (le backend ne renvoie pas d'offset, `PluAnnuaire.tsx:242-245`).
- **Le pack en vigueur dépend du GPU en ligne** (`modules.py:2864`) : si le GPU est injoignable au clic, pas de téléchargement — dit comme tel, repli coordonnées mairie.

## 7. Les tests
Backend (`tests/`) :
- `test_plu_annuaire_integral.py` : garantit que chaque commune **servable porte un `source_url` réel** (pack GPU, jamais un bouton mort) et que chaque non-servable porte un `message` ; invariant `n_communes == 24`.
- `test_plu_titre.py` (8 cas) : le reformatage de titre (majuscules → casse de phrase, coupe au sous-article, puces PDF retirées, corps ne répète pas le titre, accents conservés).
- `test_plu_ingest_millesime.py` : la ré-ingestion est **idempotente** (purge par insee/document, pas d'orphelin au changement de millésime), garde-fou « 974 ».
- `test_retours12_o4_plu.py` : le compteur de procédures réconcilié (source unique `veille_plu`) inclut bien Les Trois-Bassins.
- Autres (`test_plu_calibrage*`, `test_plu_exceptions_1`, `test_plu_destinations`, `test_simulplu`, `test_veille_plu`) : couvrent le **calibrage des zones et la veille**, c.-à-d. des couches voisines, pas l'annuaire de recherche en soi.

Non vérifié par aucun test :
- **La recherche FTS elle-même** (`search_reglement` / `count_reglement`) — aucun test ne rejoue une requête et ne vérifie le tri `ts_rank`, le plafond ou le `n_total`.
- **Le composant `PluAnnuaire.tsx`** — aucun test front (`PluPagination.test.tsx` teste l'ancien chemin décâblé).
- **La complétude d'ingestion** — rien ne garde qu'un PLU a été ingéré « en entier » (Saint-Benoît à 8 extraits passerait tous les tests actuels).
- **Le pack live GPU** (réseau) — non testé de bout en bout.

## 8. Les documents liés (PDF, exports)
L'outil **ne produit aucun PDF ni export** : LABUSE n'héberge pas de document. Les deux liens « document » renvoient au **pack officiel GPU** (`source_url` = pack .zip de `plu_reglement_extrait.source_url`, `plu_ingest.py:259` ; pack en vigueur = URL construite en direct, `modules.py:2891`). Le verbatim affiché et le lien « PDF ↗ » de chaque carte pointent vers **la même source** que celle dont l'extrait a été tiré (même `source_url` par commune). Il n'y a donc pas de divergence écran/document : l'écran est une vue indexée du document officiel, avec renvoi systématique vers lui (« Vérifiez toujours au document »).

## 9. Trois cas rejoués
Témoins : les parcelles sont par parcelle, mais l'outil PLU est **par commune**. J'ai donc rejoué sur les 3 communes des parcelles témoins. La parcelle `97415000DH0076` a pour INSEE **97415 = Saint-Paul** (confirmé par `plu_millesimes.yaml`), pas Saint-Pierre.

**a) Saint-Denis (97411) — `search?q=hauteur` (parcelle BZ1065)**
```
query=hauteur insee=97411  n=2  n_total=54  tronque=True
→ Article Uj.10 | zone UJ | p. 62 | mil 2026-08-05 | doute False
  titre: « Hauteur maximale des constructions … »
  corps: « … La hauteur des constructions n'excèdera pas : - 13 m pour la hauteur maximale H - 10 … »
  source_url: .../PACK_DU_97411_.../97411_PLU_20260805.zip
→ Article Ud.10 | zone UD | p. 44 | mil 2026-08-05
avis: « Verbatim du règlement opposable (source GPU)… ceci n'est pas un conseil juridique. »
```
Commune servable, PLU du 05/08/2026, 54 correspondances dont 2 servies.

**b) Saint-André (97409) — `search?q=hauteur` (parcelle AK0804)**
```
n=0
message: « Saint-André : révision en cours — règlement non servi par le GPU, vérifier
           en mairie (complétion auto à l'approbation, veille M41). »
```
Et `pack/97409` (résolution live GPU) :
```
disponible=False  erreur=null
message: « Le Géoportail de l'Urbanisme ne publie aucun document pour cette commune
           (vérifié à l'instant). Le PLU en vigueur reste applicable — demandez-le en mairie. »
```
Commune en révision, non servie → message honnête, pas de bouton mort. (Repli mairie : `mairies` porte « Mairie - Saint-André · 02 62 58 88 88 · communication@saint-andre.re ».)

**c) Saint-Paul (97415) — `search?q=clôture` (parcelle DH0076)**
```
query=clôture insee=97415  n=1  n_total=82  tronque=True
→ Article 11- | zone N | p. 25 | mil 2025-12-17
  titre: « Aspect extérieur des constructions et aménagement de leurs abords »
```
Commune servable (434 extraits en base), PLU du 17/12/2025, 82 correspondances.

Contrôles complémentaires : `q` vide → **HTTP 400**. RNU (97417, `q=hauteur`) → `n=0`, message « Saint-Philippe : RNU — pas de règlement communal à interroger. »
*(Non obtenu : la variante `search?...&zone=N` avec `exceptions_zone` — le backend `:7300` est tombé pendant l'audit, après tous les appels ci-dessus ; le chemin est lu dans le code `modules.py:2991-3006` mais sa sortie live n'a pas pu être capturée.)*

## 10. Tes doutes
1. **Saint-Benoît ingéré à 8 extraits seulement** (vs 109–434 ailleurs) : le règlement existe mais l'ingestion l'a quasi entièrement raté, et **rien à l'écran ne le signale** — une recherche y renverra « rien trouvé » sur un texte réel. C'est le trou le plus grave : l'outil peut être silencieusement incomplet sur une commune marquée « servable ».
2. **Aucun test ne couvre la recherche FTS ni le composant servi** : le seul test front (`PluPagination.test.tsx`) teste le chemin **décâblé**. Le cœur de l'outil (requête, tri, `n_total`, affichage) n'a aucun filet.
3. **Titre/zone/doute sont des heuristiques codées en dur** présentées comme des faits : un titre mal coupé ou une zone mal déduite est affiché sans réserve, alors que seul le `corps`/verbatim est réellement sourcé.
4. **Pas de contrôle de fraîcheur côté outil** : le millésime affiché vient de la base ; si une commune a révisé son PLU et que l'ingestion n'a pas suivi, l'outil sert l'ancien texte sans alerte (la veille `veille_plu` ne couvre que la *procédure*, pas la *complétude* de l'ingestion).
5. **Dépendance réseau au GPU non testée** pour le pack en vigueur et fragilité observée du backend local (chute en cours d'audit) : la robustesse réelle de la résolution live (`/pack/{insee}`) n'est garantie par aucun test d'intégration.

---

### Synthèse pour l'INDEX (~12 lignes)
- Fiche : `docs/audit-2026-11/outils-fiches-1/plu.md`.
- Outil **PLU** (clé `plu`, O13) : annuaire de règlements d'urbanisme, **une seule voie** (`Plu.tsx` → `PluAnnuaire.tsx`) ; endpoints `/modules/plu-annuaire/{communes,search,pack/{insee}}` (`modules.py:2829-3013`).
- Données principales : table **`plu_reglement_extrait`** (3258 extraits, 21/24 communes, verbatim indexé FTS french) ; configs `plu_millesimes.yaml` + `veille_plu.yaml` (Sudocuh 31/12/2024) ; API GPU **live** pour le pack .zip ; table `mairies` en repli.
- Il ne fait **aucun calcul d'urbanisme** : il sert du verbatim opposable (article, page PDF, lien). Seuls traitements : recherche FTS + reformatage de titre + drapeaux doute/pagination.
- Part **sourcée ≈ 85 %** (verbatim, millésime, page PDF, statut commune, compteurs = DB/config traçables) ; part **estimée ≈ 15 %** (titre « en clair », doute, pagination = heuristiques codées en dur, seuils 25 car. / pic 8).
- La voie « Procédure & changement » (`ProcedureChangement.tsx`) est **décâblée** (simulateur AU jugé non fiable) mais reste au dépôt ; le seul test front teste ce chemin mort.
- 3 cas rejoués (curl réels) : Saint-Denis `hauteur` 2/54, Saint-André `hauteur` → message révision (0, pack GPU vide), Saint-Paul `clôture` 1/82.
- **Doute le plus grave** : Saint-Benoît est « servable » mais ingéré à **8 extraits** (vs 109–434 ailleurs) — l'ingestion a raté l'essentiel du règlement et **rien ne le signale** ; l'outil peut être silencieusement incomplet, sans aucun test gardant la complétude ni couvrant la recherche FTS.
