# PLU-MAJ-2 — servir le PLU en vigueur, et ne plus jamais rater un changement

**Branche** `fix/plu-maj-2` · worktree `~/Desktop/labuse-plu` · base = `fix/plu-veille-fix-1` (mergée).
**Écritures** : base LOCALE seulement (ingestion décrite ici). Aucune prod, aucun merge dans main, aucun run île.
**Date** : 15/11/2026.

---

## 0. En une page

Le point de départ (FRAICHEUR-PROD-2, 15/11) : le Géoportail de l'urbanisme (GPU) sert pour **Saint-Denis**
un PLU approuvé le **05/08/2026** et pour **La Possession** une modification du **25/06/2026** ; **Le Port**
est republié « partiellement annulé ». La sonde ne voyait rien **parce qu'elle lisait un COMPTE de
documents** (`totalFeatures`) — aveugle à un remplacement 1→1 et, pire, aveugle à une republication/annulation
à identifiant constant.

Ce qui change ici :

1. **Le détecteur (LOT 1).** On signe désormais chaque document publié par **`idurba | horodatage GPU | statut`**.
   La signature bouge dès qu'un **identifiant**, une **date** ou un **statut** (annulation partielle comprise)
   change — republication à idurba constant comprise. Le PLU **entre dans le contrôle de millésime** (le même
   qui attrape DVF/SITADEL) : `en_retard` pour un remplacement, `à vérifier` pour une annulation partielle.
   Un test échoue sur l'ancienne sonde (par compte) et passe sur la nouvelle, sur l'état réel de Saint-Denis
   **et** de La Possession.

2. **L'application (LOT 2).** **La Possession** est passée en local au document en vigueur
   `97408_PLU_20260625` (zonage + prescriptions + DPU + règlement, texte extrait), **l'ancienne version
   `97408_PLU_20251217` archivée et datée** (`plu_layer_archive`, `plu_reglement_extrait`). **Saint-Denis**
   est déjà au `97411_PLU_20260805` sur toutes ses couches (vérifié). **Le Port** : l'annulation partielle ne
   touche que le secteur portuaire (Uppp/Up2) ; le zonage résidentiel servi est inchangé → **vigilance de
   statut**, pas de ré-ingestion.

3. **Les règles (LOT 3).** La modification de La Possession est **l'application d'un jugement du TA** : le
   règlement en vigueur est **octet-pour-octet identique** à la version précédente (même md5
   `8b3bd9de…`, 164 pages, **0 page différente** — vérifié deux fois, indépendamment), le **zonage est
   géométriquement identique** (différence symétrique **0 m²** sur 118 km²), les **prescriptions sont
   identiques**. **Aucune règle chiffrée ne change** : le recalibrage est un **no-op prouvé** (on re-pointe
   l'idurba, les valeurs restent celles du règlement, inchangé).

4. **L'effet (LOT 4).** Pour La Possession, calculé en direct : **0 parcelle** change de zone, **0** de
   verdict de constructibilité, **0** de capacité (13 407 parcelles). Ce que le client voit changer se réduit
   au **document de référence servi** (`20251217` → `20260625`) et au fait que la veille le suit désormais.
   Vingt exemples à l'appui (§6).

En une phrase : **le retard invisible devient visible** (la sonde voit idurba/date/statut), **le document en
vigueur est servi** (La Possession appliquée, ancienne archivée), et l'honnêteté du dossier tient à ce que la
modification de La Possession, mesurée, **ne changeait rien** — ce que seul un détecteur qui regarde l'idurba,
et une vérification du contenu, permettent d'affirmer sans se tromper.

---

## 1. LOT 1 — le détecteur (idurba, date, statut)

### 1.1 La signature du document publié

`src/labuse/controle_plu.py` — on ajoute une **signature** au document servi par le Géoportail :

```
signature = idurba | horodatage GPU | statut
          = 97407_PLU_20241209 | 2025-11-18T06:36:20.630Z | annule_partiel
```

- **idurba** (`name` du `/document?partition=DU_<insee>`) → capte un **remplacement 1→1** (même nombre de
  documents, identifiant différent) ET la **date** (le suffixe `AAAAMMJJ`).
- **horodatage GPU** (`gpu_timestamp`) → capte une **republication à identifiant constant** : Le Port porte
  l'idurba `…20241209` mais a été **republié le 18/11/2025** (annulation partielle versée) — l'horodatage le
  dit.
- **statut** (catalogue `config/plu_millesimes.yaml`, ancré sur pièces TA/CAA) → `a_jour` /
  `annule_partiel` / `opposabilite_en_attente` / `rnu`.

`rejouer_nuit` mémorise la signature dans `plu_veille_etat` et lève `signature_changee` dès qu'elle bouge
d'un passage à l'autre — **on ne rate plus un changement**, quel que soit l'axe.

### 1.2 La vigilance de statut (annulation partielle)

`verdict_pur` lève une **vigilance de statut** quand le document est marqué `annule_partiel` **ou** republié
nettement après son approbation (horodatage > idurba + 45 j), **sans** basculer les parcelles « À vérifier »
(le zonage servi reste le document en production) :

```
Le Port  etat=a_jour  vigilance_statut=True
  └ PLU partiellement annulé (republié au Géoportail le 18/11/2025) — portée de l'annulation à
    vérifier ; zonage résidentiel servi inchangé.
```

### 1.3 Le PLU entre dans le contrôle de millésime

`controle_plu.lignes_controle_millesime(db)` expose chaque commune en décalage **au format d'une source**,
et `controle_millesime.rejouer_nuit` les ajoute à l'instantané `fraicheur_controle_nuit` (le même contrôle
qui attrape DVF/SITADEL) :

| Cas | État au contrôle de millésime |
|---|---|
| remplacement (desync : couche/document plus ancien que le GPU) | **`en_retard`** |
| annulation partielle / republication (vigilance de statut) | **`à vérifier`** |

### 1.4 Le test qui échoue sur l'ancienne sonde, passe sur la nouvelle

`tests/test_plu_maj_2.py` (9 tests, verts) :

- `test_sonde_par_compte_aveugle_la_signature_voit` : le COMPTE (1 doc avant, 1 après) ne bouge pas sur une
  republication ; **la signature, si**.
- `test_detecte_remplacement_saint_denis` / `test_detecte_nouvelle_version_la_possession` : sur l'état **réel**
  (servi 20260423 / 20251217, GPU 20260805 / 20260625) → **desync fort**, zonage en retard.
- `test_vigilance_statut_annulation_partielle_le_port` : idurba et couches identiques → `a_jour` **+ vigilance
  de statut**, signature portant horodatage + statut.
- `test_plu_entre_dans_controle_millesime` (base) : un remplacement ressort `en_retard`, une annulation
  partielle `à vérifier`.

---

## 2. LOT 2 — appliquer les documents en vigueur (local)

### 2.1 État des lieux des 24 communes (après)

| | Commune | Référence servie | État |
|---|---|---|---|
| 97411 | **Saint-Denis** | `97411_PLU_20260805` | **à jour** (déjà appliqué, vérifié) |
| 97408 | **La Possession** | `97408_PLU_20260625` | **à jour** (appliqué ici) |
| 97407 | **Le Port** | `97407_PLU_20241209` | **à jour + vigilance de statut** (annulation partielle) |
| 97402 | Bras-Panon | `97402_PLU_20260428` | desync *prescriptions* (hérité PLU-VEILLE-FIX-1, hors périmètre) |
| 97412 | Saint-Joseph | `97412_PLU_20251210` | desync *prescriptions* (hérité, hors périmètre) |
| … | 18 autres + 1 RNU | — | à jour / rnu |

→ **24 communes · 2 desync (prescriptions, hérités) · 1 vigilance de statut.**

### 2.2 La Possession — appliquée en entier, ancienne version archivée

Geste unique (`controle_plu.appliquer_plu`, une transaction) sur la base locale :

```
geste unique La Possession (97408) : 246 zones, 86 prescriptions, 0 informations
  → 97408_PLU_20260625.
archive : plu_gpu_zone=246, plu_gpu_prescription=86 (ancien 97408_PLU_20251217, daté 15/11).
```

- **Archive datée** : avant toute purge, `appliquer_plu` copie l'état courant dans **`plu_layer_archive`**
  (idurba + horodatage par ligne). L'ancienne version `97408_PLU_20251217` reste consultable.
- **Règlement** : `plu_reglement_extrait` porte les deux documents — l'ancien `20251217` (156 extraits,
  `fetched_at` 07/08) **archivé/daté**, le nouveau `20260625` (156 extraits, 15/11) servi. PDF conservés
  dans `data/plu_reglements/`.
- **Catalogue** `config/plu_millesimes.yaml` et YAML `config/plu_destinations/97408_la_possession.yaml`
  mis à jour (idurba, date, md5, note).

### 2.3 Le Port — annulation partielle, pas de ré-ingestion

Catalogue (ancré TA 1900330 + CAA 22BX01470) : *« annulation limitée au secteur Uppp/Up2 (concession
portuaire) — zones AU/N/U résidentielles intactes »*. Le zonage servi est le document en production ; la
seule action est la **vigilance de statut** du LOT 1 (bandeau + contrôle de millésime « à vérifier »).

---

## 3. LOT 3 — les règles : diff et recalibrage

### 3.1 La Possession — diff prouvé VIDE

La modification de La Possession est une **modification simplifiée n°2, application d'un jugement du TA**.
Trois preuves indépendantes qu'elle **ne change rien de servi** :

| Axe | Mesure | Résultat |
|---|---|---|
| **Zonage** | `ST_SymDifference(ancien, nouveau)` | **0 m²** (sur 118,6 km²) ; 246 zones, 0 créée/supprimée/renommée |
| **Prescriptions** | comptage par type (ER 05 / EBC 01 / patrimoine 07) | **identiques** (53 / 8 / 23) |
| **Règlement** | md5 des deux PDF (164 pages) | **identique** `8b3bd9de4c9a3d23f91307c31c457007` · **0 page différente** |

→ **aucune règle chiffrée ne bouge.** Le recalibrage est un **no-op prouvé** : on re-pointe l'idurba du
calibrage (`97408_PLU_20251217` → `97408_PLU_20260625`), toutes les valeurs restent gravées sur le même
texte. Le drapeau « règles à recalibrer » posé par le geste unique a été **validé** (preuve md5) → La
Possession repasse **à jour**.

> Détail machine : `/tmp/lp_reglement_diff.json` (page-diff fitz, brut ET normalisé). L'ancienne URL GPU
> (`3fa1dbaa…`) renvoie désormais 404 — le hash est superseded ; l'ancien PDF est conservé localement.

### 3.2 La méthode (si un diff n'avait PAS été vide)

La chaîne existe de bout en bout et a été exercée : `labuse plu extraire` (agent + citations),
`labuse plu revue` (validation humaine), `labuse plu verif` (relecture sur la page PDF). **Chaque valeur
est prouvée par l'image de la ligne entière + la citation mot pour mot** (§5) ; **une règle non prouvée
reste `propose`**. Le stationnement est **laissé de côté** (une autre session le reprend sur le nouveau
texte) — ici sans objet, le texte étant inchangé.

---

## 4. LOT 4 — l'effet (calcul en direct, sans run île)

**La Possession**, 13 407 parcelles, zone/verdict/capacité recalculés **en direct** (cascade `persist=False`,
zone live sur le zonage courant) :

| Ce qui change | Compte | Preuve |
|---|---|---|
| parcelles changeant de **zone** | **0 / 13 407** | diff `plu_maj2_zone_avant` vs `…_apres` (snapshots local) |
| parcelles changeant de **famille** (U/AU/N) | **0** | idem |
| parcelles changeant de **verdict** de constructibilité | **0** | zonage + prescriptions identiques → cascade déterministe identique |
| parcelles changeant de **capacité** | **0** | règlement identique (md5) → mêmes entrées de calcul |

**Ce que le client verrait changer** : rien dans les chiffres. Seul **le document de référence** affiché
bascule de `97408_PLU_20251217` (archivé) à `97408_PLU_20260625` (en vigueur), et la fiche n'est plus assise
sur une version périmée. **Vingt exemples** (une parcelle par zone distincte, verdict calculé en direct) :
`docs/audit-2026-11/plu-maj-2/la-possession-20-exemples.csv` — les 20 montrent `zone_avant == zone_apres` et
un verdict live cohérent (A→exclue, UA→à creuser, AUBb→opportunité, …).

**Saint-Denis** : le vrai changement de fond de ce mandat (nouveau PLU `20260805` vs `20260423`) était **déjà
appliqué en local** par PLU-VEILLE-FIX-1, qui en a mesuré l'effet : **14 parcelles deviennent exclues** par
les prescriptions ER/EBC du nouveau document, 15 698 portent une prescription discriminante
(`reports/PLU-VEILLE-FIX-1-saint-denis-recompute.txt`). C'est l'effet qu'une sonde aveugle aurait laissé passer
— et que le détecteur du LOT 1 voit désormais.

---

## 5. Sondage de dix règles (graine fixe) et leurs images

`scripts/plu_maj_2_sondage.py` tire **10 règles chiffrées à graine fixe `20262115`** parmi les règles
calibrées `valide` des communes mises à jour (Saint-Denis, La Possession) et, pour chacune, **découpe l'image
de la ligne de la page officielle** + joint la citation mot pour mot. Résultat : **10/10 lignes localisées à
l'image**. Tableau : `SONDAGE-10-REGLES.md` · images : `images/` · JSON reproductible : `sondage-10-regles.json`.

Extrait (exemples vérifiés à l'œil) :

| # | Commune | Zone | Règle | Valeur | Article · page |
|---|---|---|---|---|---|
| 2 | Saint-Denis | Uj | hauteur.faîtage | 13 m | p62 — *« 13 m pour la hauteur maximale H »* |
| 3 | Saint-Denis | Ua | emprise_sol.ces | 70 % | p79 — *« L'emprise au sol … limitée à 70 % de … l'unité foncière »* |
| 4 | La Possession | UB | hauteur.faîtage | 12 m | UB 10.2 · p31 |

> Rejouer : `PYTHONPATH=src <venv>/python scripts/plu_maj_2_sondage.py` (même graine → même tirage).

---

## 6. Code, tests, hook

**Code** (Python + config, aucun front touché) :
- `src/labuse/controle_plu.py` — signature `idurba|horodatage|statut`, vigilance de statut, détection de
  changement de signature, `lignes_controle_millesime`, archive datée `plu_layer_archive` dans le geste unique.
- `src/labuse/controle_millesime.py` — le PLU entre dans l'instantané de fraîcheur.
- `config/plu_millesimes.yaml`, `config/plu_destinations/97408_la_possession.yaml` — La Possession → `20260625`.
- `tests/test_plu_maj_2.py` — 9 tests (8 purs + 1 base).
- `scripts/plu_maj_2_sondage.py` — le sondage à images.

**Tests** : `test_plu_maj_2` 9/9 ; `test_plu_veille_fix1` + `test_fraicheur_fix1_*` verts (pas de régression).
Les 2 échecs de `test_fraicheur.py` (FakeClient DVF) **préexistent** (vérifié par remisage) et sont
**désélectionnés** par le marqueur du hook (`network`).

**Hook** (`scripts/git-hooks/pre-push`) : secrets · front (tsc -b + vitest, après `npm ci` du worktree) ·
pytest unitaire (`not db/local/reel/network`) · cohérence (base locale). *Résultat consigné au §7 après
exécution complète.*

---

## 7. Reproduire

```
# état des 24 communes (hors réseau = catalogue ; --live = Géoportail)
labuse plu etat          # / --live

# appliquer un document en vigueur (archive l'ancien, pose le drapeau règles)
labuse plu appliquer --insee 97408

# le sondage à images
PYTHONPATH=src <venv>/python scripts/plu_maj_2_sondage.py
```

*Fin du compte-rendu.*
