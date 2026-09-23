# PLU-RACCORD-1 — L'outil PLU est-il branché sur le bon PLU, pour les 24 communes ?

**Mandat** : vérifier que chacune des 24 communes est reliée à SON PLU, et que les deux actions
de l'outil (Annuaire/ZIP · Procédures) tapent bien sur le PLU de la commune choisie.
**Lecture seule** — aucune modif, aucun merge.
Branche `audit/plu-raccord-1` · worktree `~/Desktop/labuse-pluraccord` · base main `00106a19` (arbre propre).
API de contrôle sur `:8115` (base `labuse` réelle) · front sur `:5315`.

Livrables joints : [`reports/plu-raccord-1/TABLE-24.csv`](../../reports/plu-raccord-1/TABLE-24.csv)
· scripts reproductibles `gpu_pack_check.py` / `build_table24.py` · capture `captures/plu-annuaire-grille-24.png`.

---

## 0. Ce qu'est « l'outil PLU » (le code qui sert les deux actions)

Hub unifié `frontend/.../outils/Plu.tsx` → 2 voies : **Annuaire PLU** (`PluAnnuaire.tsx`) et
**Procédure & changement** (`ProcedureChangement.tsx`). Trois endpoints, tous sous le préfixe
`/modules` (`src/labuse/api/modules.py`) :

| Endpoint | Fichier:ligne | Rôle |
|---|---|---|
| `GET /modules/plu-annuaire/communes` | `modules.py:2267` → `registre/moteurs/commune.py:etat_corpus_plu:188` | liste des 24 + statut + compteurs |
| `GET /modules/plu-annuaire/pack/{insee}` | `modules.py:2286` | ZIP du PLU en vigueur, **résolu en direct sur le GPU** (`grid=insee`) |
| `GET /modules/plu-annuaire/search` | `modules.py:2332` → `ingestion/plu_ingest.py:search_reglement:156` | recherche verbatim, **filtrée `insee = :insee`** |

**Comment la commune est reliée à son PLU — deux mécanismes, aucun « fichier → commune » en dur :**

1. **Sélection = code INSEE.** Le front rend un bouton par commune avec `data-plu-commune={insee}`
   (`PluAnnuaire.tsx:83`) ; cliquer pose `insee` dans l'état, tout part de là.
2. **ZIP servi selon le statut :**
   - commune **servable** → bouton `href = cur.source_url` (`PluAnnuaire.tsx:140`), où `source_url`
     vient de la table ingérée `plu_reglement_extrait` (`corpus_status` → `min(source_url)`, 1 pack GPU
     par commune). Format : `data.geopf.fr/…/PACK_DU_{insee}_…/{idurba}.zip`.
   - commune en **révision** → composant `PackVigueur` (`PluAnnuaire.tsx:260`) qui appelle le pack
     **live GPU** `grid=insee` — trois issues distinctes (trouvé / GPU vide / injoignable).
   - commune **RNU** → pas de ZIP, lien Légifrance RNU (`PluAnnuaire.tsx:124`).
3. **Recherche** : `search_reglement` ajoute `insee = :insee` au WHERE si un insee est fourni
   (`plu_ingest.py:164-166`) → structurellement impossible de renvoyer une autre commune.

**Source des statuts (Chemin B)** : `config/plu_millesimes.yaml` (statut GPU/mairie, campagne M40) pour
la disponibilité du règlement, et `config/veille_plu.yaml` (squelette Sudocuh 31/12/2024 + curation,
lu par `src/labuse/veille_plu.py`) pour la **procédure active** (`procedure_active` = confiance `SOURCE`
+ `revision_plu`/`elaboration_plu` + non dormante). Rien n'est inventé ni en dur ailleurs.

---

## 1. Chemin A — Annuaire / ZIP : les 24 communes pointent-elles sur LEUR fichier ?

Vérifié **sans 24 clics**, en croisant trois sources indépendantes :

- **A. `source_url` servi en base** (`plu_reglement_extrait`, base `labuse` réelle — 3 258 extraits,
  21 communes ingérées) : pour les 21 communes servables, le `source_url` porte le bon INSEE **partout**
  (`PACK_DU_{insee}` ET `{idurba}.zip`), 0 écart. idurba en base = idurba de la config.
- **B. Pack live GPU** rejoué pour les 24 (`gpu_pack_check.py`, réplique exacte de l'endpoint) :
  l'`originalName` du document EN_VIGUEUR **commence par l'INSEE** pour les 20 communes qui publient
  au GPU — `own_ko = []` (aucune ne sert le PLU d'une autre commune). 3 renvoient `[]` (voir écart ci-dessous).
- **C. Recherche bornée** : pour chaque commune servable, `search insee=X` renvoie du **non-vide**
  (terme « hauteur » : 2 à 86 extraits) et **uniquement X** (test `insee=97415` → 1 seul insee distinct,
  86 résultats, tous 97415). RNU/révision → message honnête, 0 résultat (jamais de fuite).

Détail des 24 : voir `TABLE-24.csv`. Colonne `zip_ok_ecart` = **OK** ×24, `recherche_bornee` = **OK** ×24.

### Le seul écart trouvé — Saint-Denis (97411) : millésime périmé, PAS mauvaise commune

Le GPU marque aujourd'hui `97411_PLU_20260805` **EN_VIGUEUR** ; toutes les versions antérieures, dont
`97411_PLU_20260423`, sont passées **ARCHIVE**. Or l'app sert `97411_PLU_20260423` (config
`plu_millesimes.yaml` + corpus ingéré + bouton de téléchargement). **C'est bien un PLU de Saint-Denis**
(le raccordement commune→document est correct), mais un millésime en retard d'une révision.
Cause : lag entre le corpus ingéré / la config M40 (relevé 06/08) et une republication GPU postérieure.
Asymétrie à noter : une commune servable sert le pack **ingéré** (peut vieillir), une commune en révision
sert le pack **live** (toujours à jour) — c'est Saint-Denis qui tombe du mauvais côté ici.
**Ni un mauvais branchement, ni du vent** : c'est exactement ce que la veille trimestrielle M41/M40 doit
rattraper. Classé écart de **fraîcheur**, sévérité faible.

### Les 3 communes sans ZIP direct (comportement voulu, honnête)

- **Saint-André (97409)** et **Saint-Leu (97413)** — en révision : le GPU `grid=insee` renvoie `[]`
  (mesuré à l'instant, conforme au cas documenté du 05/09). L'UI le **dit** et propose **la mairie de
  la commune** (Saint-André → « Mairie - Saint-André · 02 62 58 88 88 » ; Saint-Leu → sa propre mairie).
  Aucun ZIP d'une autre commune n'est servi.
- **Saint-Philippe (97417)** — RNU : pas de PLU, pas de ZIP, lien Légifrance RNU. Correct.

---

## 2. Chemin B — Procédures / changements : d'où vient le statut, colle-t-il au réel ?

**Source réelle, pas en dur** : la disponibilité du règlement vient de `config/plu_millesimes.yaml`
(confronté GPU↔mairie, M40) ; la **procédure en cours** vient de `config/veille_plu.yaml`
(squelette Sudocuh + curation, champ `confiance` obligatoire, lint strict `veille_plu.lint`).
`etat_corpus_plu` réconcilie les deux et attache à chaque commune sa `procedure_active`
(`commune.py:233-239`). Une note de config n'est jamais servie comme un fait (doctrine inscrite dans le YAML).

Compteurs servis en live par `/modules/plu-annuaire/communes` :

```
n_communes = 24 · n_plu_vigueur = 23 · n_rnu = 1 · n_procedures = 3 · procedures_par_etat = {révision générale: 3}
non_servis = [Saint-André, Saint-Leu]
```

**Colle au réel connu (doctrine 05/09 : 23 PLU / 1 RNU / 3 procédures)** — exact.

| Axe | Communes | Source |
|---|---|---|
| **RNU** (1) | Saint-Philippe (97417) | `plu_millesimes` statut `rnu` + `veille_plu` élaboration `prescrite_dormante` (hors radar) |
| **Procédure active** (3) | Saint-André (97409), Saint-Leu (97413), **Trois-Bassins (97423)** | `veille_plu` `revision_plu` `prescrite` confiance `SOURCE` |
| **En vigueur** (23) | les 23 autres | `plu_millesimes` `a_jour` / `annule_partiel` (Le Port) |

Point de vérité : Trois-Bassins est **en vigueur ET en procédure** (son règlement est servi, mais une
révision est prescrite) — c'est la réconciliation RETOURS-12 O4 qui l'attrape ; l'ancien compteur
« disponibilité GPU » le ratait. Le Port porte `annule_partiel` (annulation contentieuse limitée au
secteur portuaire) — affiché « en vigueur », zones résidentielles intactes. Aucune commune n'affiche du vent :
les 20 restantes portent « en vigueur » sans procédure, sourcé `veille_plu` `aucune`/`cloturee`.

La voie UI « Procédure & changement » liste bien, et seulement, les **3** communes en procédure
(Saint-Leu, Saint-André, Trois-Bassins) — vérifié à l'écran.

---

## 3. Les 3 clics de contrôle au navigateur (`:5315` → API `:8115`, base réelle)

La grille rend les **24** communes (INSEE→nom exacts), bandeau « 23 PLU en vigueur (24 communes,
1 au RNU) », note ambre « Règlement de 2 communes non servi… (Saint-André, Saint-Leu) », badges
« révision » sur Saint-André / Saint-Leu / Trois-Bassins. Capture : `captures/plu-annuaire-grille-24.png`.

| # | Commune (type) | Clic → ce que l'UI sert | Verdict |
|---|---|---|---|
| 1 | **Saint-Paul 97415** (Géoportail, servable) | bouton « Télécharger le PLU intégral » → `href = …/PACK_DU_97415_…/97415_PLU_20251217.zip` ; fil « Saint-Paul · PLU du 2025-12-17 » | ZIP qui part = celui que la table annonce (source_url base) ✓ |
| 2 | **Saint-André 97409** (en révision) | « Révision en cours… » + PackVigueur → « GPU ne publie aucun document… demandez-le en mairie » + **Mairie - Saint-André** (02 62 58 88 88). Aucun ZIP. | repli honnête sur SA mairie, zéro PLU d'une autre commune ✓ |
| 3 | **Saint-Philippe 97417** (RNU) | « RNU — pas de règlement communal » + lien Légifrance RNU ; **aucun** bouton de téléchargement | correct, pas de PLU inventé ✓ |

Les 3 clics confirment que l'UI câble chaque commune sur son propre INSEE et sert le bon document /
le bon repli. La table couvre les 24 ; les clics prouvent qu'elle dit vrai.

---

## 4. Verdict

**Les 24 communes sont correctement raccordées à LEUR PLU, et les deux actions de l'outil tapent bien
sur le PLU de la commune choisie.**

- **Chemin A (ZIP)** : 24/24 pointent sur leur propre commune. Aucune ne sert le PLU d'une autre
  (`own_ko = []` en live, `source_url` porte le bon INSEE pour les 21 servables, repli mairie de la
  bonne commune pour les 2 révisions, Légifrance pour le RNU).
- **Chemin A (recherche)** : bornée à la commune par SQL (`insee = :insee`), non vide pour les 21
  servables, message honnête pour révision/RNU. 0 fuite.
- **Chemin B (procédures)** : statut issu de vraies données (`plu_millesimes` + `veille_plu`/Sudocuh),
  pas en dur. 23 en vigueur / 1 RNU / 3 procédures — conforme à la doctrine du 05/09. Aucune commune
  n'affiche du vent.

**Écarts (1, à ne pas corriger dans ce mandat) :**

1. **Saint-Denis (97411) — fraîcheur** : l'outil sert `97411_PLU_20260423` (désormais ARCHIVE au GPU)
   alors que le GPU a `97411_PLU_20260805` EN_VIGUEUR. Bon raccordement (PLU de Saint-Denis), mais
   millésime en retard d'une révision, sur le bouton de téléchargement, le corpus de recherche et le
   millésime affiché. Relève du geste de veille M40/M41 (re-ingestion), pas d'un défaut de branchement.

Rien d'autre : pas de commune muette, pas de PLU croisé, pas de statut fabriqué.

---

### Reproductibilité
- `reports/plu-raccord-1/gpu_pack_check.py` → `gpu_pack_check.csv` (24 lignes, pack live GPU + croisement config).
- `reports/plu-raccord-1/build_table24.py` → `TABLE-24.csv` (config + base `labuse` + bornage recherche).
- API : `PYTHONPATH=…/labuse-pluraccord/src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse uvicorn labuse.api.app:app --port 8115`.
- Front : `LABUSE_API_DEV=http://127.0.0.1:8115 vite --port 5315` (code PLU identique à main `00106a19`).
