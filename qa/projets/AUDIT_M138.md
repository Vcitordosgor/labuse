# AUDIT M138 — La tuyauterie « projets », de bout en bout (`audit/projets`)

Lecture seule, **aucune correction**. Branché sur `origin/main` @ `81daf718` (avance
depuis M137 = un `.gitignore`, hors périmètre). Chaque constat porte sa `fichier:ligne`
et sa **gravité** : *faux positif (cardinal)* · *faux négatif* · *décoratif* · *dette* ·
*cosmétique*. Fichiers : `api/projets.py`, `api/pdf_projet.py`, `api/app.py`,
`faisabilite/residuel_runs.py`, `models.py`. CC ne merge jamais.

**Verdict en une ligne : la tuyauterie est saine et cloisonnée ; deux vraies failles —
(1) `DELETE /projets/{pid}` détruit en DUR la shortlist et les tris (contredit
« aucune perte » de M137), (2) le PDF d'un projet figé RELIT les valeurs en LIVE sur le
run servi, non daté. Le reste = code mort inoffensif et un tag Sourcé/Estimé absent de
l'en-tête.**

---

## A — La tuyauterie, étape par étape

### 1. Création
- **Un seul endpoint** : `POST /projets` → `projet_create` (`projets.py:610`). Écrit la
  ligne `projets` (`nom, filtres=cadrage, identite, compte_id` — `projets.py:622`) puis
  fige la shortlist (`_figer_shortlist`, `projets.py:625`) qui remplit `projet_parcelles`.
- **Le sélecteur est bien `FiltreCriteres`, PAS un système parallèle.** `_cadrage_to_filtre`
  (`projets.py:232-246`) mappe les 44 facettes → `FiltreCriteres(**kw)` (importée de `.app`),
  et `_run_cadrage` applique `fc.where()` — le **même builder WHERE que la carte**
  (`app.py:857`). La **dette M133 D.2 (« système parallèle ») est résolue** : `derive_filtres`
  a disparu (docstring `projets.py:1-9`, grep négatif). ✔ **sain.**
- Dédup douce : `_find_doublon` (`projets.py:530`) propose la reprise d'un projet actif de
  mêmes filtres/nom, sans rien détruire. ✔

### 2. Cadrage — trois populations distinctes (à ne pas confondre)
| Fonction | Population comptée | Sliver <2 m² | Étage 0 | Usage |
|---|---|---|---|---|
| `_cadrage_total` (`projets.py:286`) | **d'où la shortlist est extraite** | exclu | **conditionnel** (inclus si filtre `tiers`) | `total` de l'en-tête PDF |
| `_vivier_figeable` (`projets.py:271`) | triable **hors exclusions dures** | non appliqué | **exclu inconditionnel** | dénominateur « top N sur M » |
| `_q_v2_stats.total` (`app.py:2298`) | **univers entier** | — | **inclus** (reclassé « ecartee ») | compteur `/compteur`,`/apercu` |

Clause décisive étage 0 : `_ETAGE0_SQL = (d.status IN ('exclue','faux_positif_probable'))`
(`app.py:728`) ; `_vivier_figeable` le retire toujours (`projets.py:282`), `_cadrage_total`
seulement hors filtre tiers (`projets.py:295-296`). ✔ **cohérent** — chaque en-tête sait
quelle population il cite.

### 3. Figeage — **la liste, pas les valeurs**
`_figer_shortlist` (`projets.py:541-607`) n'écrit dans `projet_parcelles` que
`projet_id, parcel_id, statut, rang, proposee_at` (`projets.py:574-578`) ; le modèle ne porte
rien de plus (`models.py:715-728`, docstring « on ne stocke qu'un statut » `models.py:711`).
**« Cadrage figé le JJ/MM » gèle donc l'ENSEMBLE D'IDU, jamais leurs valeurs** (SDP, zone,
score). Voir §B.1 pour la conséquence à la bascule de run.

### 4. Sélection — le rang caché
Le top-N figé est ordonné par `s2.rang ASC` (`app.py:2093,2210`), soit le **rang par
probabilité de mutation** du P-model (`parcel_p_score_v2.rang`, `p_v2/pipeline.py:301-312`,
`np.lexsort` sur `-p`), sur le **run servi** (`s2.run_id = :v2run`). C'est le « rang non
visible » que le PDF nomme sans le servir (§D). ✔ conforme.

### 5. Rendu — même liste figée pour l'écran et le PDF
- Écran : `GET /{pid}/parcelles` → `projet_parcelles` lit `FROM projet_parcelles`
  (`projets.py:844`). PDF : `_shortlist_pdf` lit la **même table** (`projets.py:1096`,
  docstring « JAMAIS un recalcul live » `projets.py:1082`). ✔ même source pour la LISTE.
- **Mais les VALEURS par parcelle sont relues live** (voir §B.1), point de nuance majeur.

### 6. Rattachement — cloison `compte_id` complète (SEC-IDOR)
**Les 15 routes qui lisent/mutent un projet précis passent toutes `compte_id`** via
`_projet_or_404(..., current_compte(request))` ou `_scope(...)`. Vérifié exhaustivement :
liste `GET ""` (`:523`), `POST ""` (`:618`), `/fusionner` (`:643`), `/pour-parcelle`
(`:683`), `GET/PATCH/DELETE /{pid}` (`:704/:713/:738`), `/rejouer` (`:750`), `/proposer`
(`:826`), `/parcelles` (`:836`), `/carte/{idu}` (`:914`), `PATCH /parcelle/{idu}` (`:938`),
`/chercher-plus` (`:978`), `/ajouter` (`:1013`), **`export.pdf` (`:1229`)**. Les routes 1-5
(`/types`,`/reperes`,`/compteur`,`/apercu`,`/derive`) ne touchent aucune donnée tenant. ✔
**aucune brèche IDOR.**

### 7. Liaison CRM — bidirectionnelle, réversible (M137)
- **Retenue → crée/restaure une carte pipeline** : `_sync_crm_retenue` (`projets.py:763-790`)
  `INSERT … ON CONFLICT DO UPDATE archived_at=NULL WHERE projet_id=:pid` (`:778-784`), colonne
  « Contact à préparer » (`:760`). ✔
- **Quitter retenue → ARCHIVE la carte** (soft, réversible, prospection conservée) :
  `UPDATE pipeline_entries SET archived_at=:now WHERE parcel_id=:pc AND projet_id=:pid`
  (`:788-789`). Ciblé `projet_id` : une carte manuelle/d'un autre projet est préservée. ✔
- `pipeline_entries.projet_id` : écrit par le sync (`:780`), **jamais éditable** (`PipelinePatchIn`
  ne l'expose pas, `app.py:4579`). ✔ **sain** — c'est le versant CRM que M137 a assaini.

### 8. Fin de vie — **DEUX chemins, dont un qui perd des données**
- **Doux (réversible)** : `PATCH /{pid}` `statut=archive` (`projets.py:708-722`) ne touche NI
  `projet_parcelles`, NI les cartes, NI le figeage ; les listes masquent `statut≠actif`
  (`:535`). ✔
- **Dur (irréversible)** : `DELETE /{pid}` → `db.delete(p)` (`projets.py:739`). Cascade :
  - `projet_parcelles` **SUPPRIMÉES EN DUR** (FK `ondelete="CASCADE"`, `models.py:719`) →
    **shortlist figée + tous les tris (retenue/écartée/à analyser) PERDUS**, sans retour ;
  - cartes CRM liées **ORPHELINÉES** (`projet_id→NULL`, FK `ondelete="SET NULL"`,
    `models.py:656`) — elles survivent mais perdent le lien (documenté `projets.py:736`).

**→ FINDING F1** (voir tableau) : c'est le pendant projet de ce que M137 a fermé côté CRM.

---

## B — Véridicité

**B.1 — Le PDF d'un projet figé RELIT les valeurs en LIVE (non daté).**
Le figeage ne gèle que les IDU (§A.3). Au rendu, la SDP et la cause viennent de
`LEFT JOIN parcel_residuel pr` (`projets.py:1098`), et `parcel_residuel` est une **VUE**
filtrée sur le run **servi courant** : `… WHERE run_seq = (SELECT run_seq FROM residuel_runs
WHERE is_served)` (`residuel_runs.py:66-69`). L'étage 0 et le `total` sont recomptés sur la
constante `RUN` = `Q_A_RUN_LABEL`, elle-même lue de `config/served_run.txt`
(`score_v_constants.py:53-70`). **Donc si Vic bascule le run servi après le figeage, la SDP /
zone / étage 0 / total d'un projet déjà figé CHANGENT au rendu** — pour les mêmes parcelles.
Le PDF ne porte que deux dates (cadrage figé + génération, `pdf_projet.py:144-151`), **jamais
la version du run résiduel servi**. Le corps AVERTIT en prose (« elle peut différer de l'état
actuel du cadrage si les critères ou les données ont changé depuis », `pdf_projet.py:311-317`),
ce qui atténue, mais **la valeur servie n'est pas datée**. **Gravité : dette** (choix assumé
« figé = quelles parcelles, pas quelles valeurs », mais véridicité incomplète tant que le run
résiduel n'est pas daté au rendu).

**B.2 — Les chiffres du PDF → leur source.** Le `~ {total}` de l'en-tête = `_cadrage_total`
(recompte live sur `RUN`, `projets.py:1205`). Le **285 781** est l'**univers entier** du run
servi (documenté `app.py:2134`) ; **10 725** n'est qu'un exemple de formatage
(`pdf_projet.py:52`) ; **839** n'existe pas comme constante du pipeline (counts runtime). Aucun
nombre fabriqué. ✔

**B.3 — `capacite_estimee` (flag corrigé par la bascule) n'atteint PAS le dossier.** Il est
`SELECT`é (`pr.capacite_estimee`, `projets.py:1094`) mais **jamais lu** dans la boucle de
construction (`projets.py:1129-1201`, grep : seule occurrence = le SELECT). Il ne peut donc ni
mentir ni informer — colonne morte au SELECT. **Gravité : cosmétique** (code mort ; par
ricochet, le « second consommateur du flag stale » n'en est pas un ici). Ce qui atteint bien le
PDF depuis la vue live : `sdp_residuelle_m2`→SDP (`:1155`) et `cause`→indispo (`:1181`).

**B.4 — Sourcé/Estimé tenu par ligne, ABSENT de l'en-tête de cadrage.** Chaque ligne de donnée
est taguée (`Sourcé — cadastre` `pdf_projet.py:366`, SDP `(Estimé)` `:374`, hauteur
`Sourcé — PLU calibré`/`Estimé — générique` `:351`, zone `Sourcé — GPU` `:385`). Mais la
**fiche de cadrage / en-tête** (`pdf_projet.py:127-193`) ne porte **aucun** tag. **Gravité :
cosmétique** (le mandat B.4 demande « y compris l'en-tête de cadrage » — c'est le seul endroit
qui ne le tient pas).

---

## C — Solidité

**C.1 — Idempotence : par NOM, pas à pid constant.** Le seed QA (`qa/m130/generer_pdf_qa.py`)
nettoie par nom (`DELETE … WHERE id = ANY(ids-trouvés-par-nom)`, `:68-74`) puis réinsère
(`:77`) → **les pids CHANGENT à chaque run** (SERIAL). L'idempotence porte sur le préfixe de
nom, pas l'id (la prémisse « pid constant » du mandat est inexacte). `_figer_shortlist` est
lui non destructif sur les décisions (`ON CONFLICT … WHERE statut='proposee'` `:576`, hors-cadrage
marqués `hors_criteres` `:584`). **Gravité : cosmétique** (idempotence réelle, juste par nom).

**C.2 — Volume borné.** Un cadrage à fort vivier (« 10 725 ») n'est **jamais matérialisé** :
`lim = min(limit or 60, shortlist_max=200)` (`projets.py:550`), la boucle d'INSERT itère au plus
`lim` (`:569`), le vivier n'est que **compté** (`_vivier_figeable`). Pas de create lent en masse.
✔ (recoupe M138 P1).

**C.3 — Concurrence : aucun verrou applicatif.** `_figer_shortlist` et `chercher-plus` n'ont ni
`FOR UPDATE` ni SAVEPOINT ; ils s'appuient sur la contrainte d'unicité `uq_projet_parcelle`
(`models.py:716`) + `ON CONFLICT`. Deux figeages concurrents du même projet ne sont pas
sérialisés par un lock, mais la contrainte empêche les doublons. **Gravité : dette (mineure)**
— risque faible (verrou DB de facto), à surveiller si le multi-utilisateur/projet monte.

**C.4 — Chemins hors utilisateur.** `demo.py` **ne crée AUCUN projet** (que `pipeline_entries`,
`demo.py:99-129`). Seul `qa/m130/generer_pdf_qa.py:72-77` crée/supprime des projets (seed QA,
par nom). Aucun autre `DELETE FROM projets` hors API. ✔ propre.

---

## D — Doctrine (M133 B.6 : zéro verdict/score/rang hors application)

- **Le PDF exportable est PROPRE** : `_shortlist_pdf` ne sert que `figee, figee_le, n, total,
  total_etage0, etage0_count, parcelles[]` (`projets.py:1206`) ; aucune parcelle ne porte rang,
  q_score, a_score, tier, verdict ni probabilité (`:1175-1201`). Rendu en ordre géographique
  (`:1101`), `etage0` servi comme « état de donnée, pas un rang » (`:1184`). La phrase
  « sélectionnées par probabilité de mutation — un rang non visible » (`pdf_projet.py:229-234`)
  **nomme** le critère sans **servir** la valeur. ✔ **conforme.**
- **Frontière** : les payloads d'**écran** JSON exposent `tier`/`rang`/`q_score`/`a_score`
  (`projets.py:840-841,922-924`) — mais c'est **dans l'application** (M133 B.6 vise « hors
  application »), donc conforme. À connaître comme la ligne de partage. **Gravité : décoratif**
  pour un cas précis : `projet_apercu` sert `"q_score"` (`projets.py:446`) qui **vaut toujours
  `None`** (jamais peuplé par `_q_v2_list`, commentaire `:366`) — clé servie inutile.
- **Aucun `MAX(run_id)` ni tri lexical de run** dans `projets.py` (grep négatif) : le choix de
  run passe partout par `RUN`/`_score_v2_run_id` (flag `is_served`), jamais par un tri. ✔

---

## E — Verdict d'utilité, franc

**Ce que le module rend vraiment** : un dossier PDF daté, cloisonné par compte, doctrine-propre
(aucun rang/score fuité), d'une shortlist de parcelles ordonnée géographiquement, chacune enrichie
de SDP résiduelle / hauteurs / zone PLU avec tag Sourcé/Estimé. Pour un promoteur, c'est un
livrable réel et défendable — pas un gadget.

**Ce qu'il promet de plus qu'il ne tient** :
1. **« Figé le JJ/MM » suggère un instantané ; ce n'est vrai que des IDU.** Les valeurs (SDP,
   zone, total) sont relues live et **non datées** au run résiduel (§B.1). Un promoteur qui
   ré-exporte après une bascille peut voir d'autres chiffres sans comprendre pourquoi. **C'est le
   principal écart de véridicité** (mitigé par l'avertissement en prose, non fermé).
2. **La complétude est plafonnée** (M138 P1) : top-60 par un rang caché. L'en-tête est honnête,
   mais le module « répond » sur 60 parcelles quand le cadrage en retient des centaines/milliers.
3. **`DELETE` détruit le travail de tri** (§A.8 / F1) alors que tout le reste est « sans perte ».

**Améliorations, ordonnées valeur/coût** :
- **(fort / faible)** Dater le run résiduel dans le PDF (une ligne d'en-tête) → ferme B.1.
- **(fort / moyen)** Aligner `DELETE` sur M137 : archiver le projet au lieu de le hard-delete,
  ou au minimum archiver les cartes plutôt que les orphaliner → ferme F1.
- **(faible / trivial)** Retirer le `SELECT pr.capacite_estimee` mort (`:1094`) et la clé
  `q_score` toujours `None` de `projet_apercu` (`:446`).
- **(faible / faible)** Tag Sourcé/Estimé dans l'en-tête de cadrage (B.4).

**Défauts vs manques** : ce ne sont pas des bugs de calcul (les chiffres sont sourcés, la cloison
tient, la doctrine est respectée à l'export). Ce sont des **manques de véridicité temporelle**
(figé non daté) et une **incohérence de cycle de vie** (un chemin de perte dure subsiste). Aucun
pan n'est un gadget ; le maillon faible est la fin de vie et la re-lecture live non datée.

---

## Tableau des constats (gravité)

| # | Constat | `fichier:ligne` | Gravité |
|---|---|---|---|
| **F1** | `DELETE /projets/{pid}` = hard-delete : `projet_parcelles` (shortlist+tris) supprimées en dur, cartes CRM orphelinées — contredit « aucune perte » (M137) | `projets.py:739` · `models.py:719,656` | **faux négatif** |
| **F2** | PDF d'un projet figé relit SDP/zone/total en LIVE sur le run servi, **non daté** (figé = IDU seulement) | `projets.py:1098` · `residuel_runs.py:66-69` · `pdf_projet.py:144-151` | **dette** |
| F3 | `capacite_estimee` `SELECT`é mais jamais consommé (code mort au SELECT) | `projets.py:1094` | cosmétique |
| F4 | `projet_apercu` sert `q_score` toujours `None` (clé inutile) | `projets.py:446,366` | décoratif |
| F5 | Concurrence : aucun verrou applicatif au figeage/chercher-plus (unicité DB seule) | `projets.py:541,974` · `models.py:716` | dette (mineure) |
| F6 | Tag Sourcé/Estimé absent de l'en-tête de cadrage (présent par ligne) | `pdf_projet.py:127-193` | cosmétique |
| F7 | Idempotence QA par NOM, pids non constants (prémisse « pid constant » inexacte) | `qa/m130/generer_pdf_qa.py:68-77` | cosmétique |
| — | SEC-IDOR : cloison complète, 15 routes `/{pid}` bornées — **aucune brèche** | `projets.py:704,738,978,1013,1229…` | ✔ conforme |
| — | Doctrine : PDF exportable sans rang/score/verdict ; pas de `MAX(run_id)` | `projets.py:1206` · grep | ✔ conforme |
| — | Sélecteur unique `FiltreCriteres` (dette M133 D.2 résolue) | `projets.py:232-246,1-9` | ✔ conforme |

---

*Fin d'audit. Aucune ligne corrigée. Push `audit/projets`. Vic arbitre le périmètre M139
(F1 et F2 sont les deux candidats prioritaires). CC ne merge jamais.*
