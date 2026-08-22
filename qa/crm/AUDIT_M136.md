# M136 Partie 2 — Audit de la page CRM (lecture seule, format M132)

Branche `audit/crm` @ `f3af830a`. **Aucune correction.** Gravités : **faux positif**
(cardinal) · **faux négatif** · **décoratif** · **dette** · **cosmétique**.

Page = `frontend/src/components/crm/Kanban.tsx` (composant `Kanban()`, carte `Card`).
Backend = `src/labuse/api/app.py` (`/pipeline*`), `crm_columns.py`, modèle
`models.PipelineEntry`.

---

## A — Cartographie

**Ce que c'est** : un **kanban de prospection**. Des colonnes (étapes) portant des
cartes-parcelles qu'on glisse d'étape en étape.

- **Colonnes / statuts** : `crm_columns` **PAR TENANT** (`crm_columns.py`), semées du
  kanban LABUSE par défaut (`config/pipeline.yaml`) au premier accès. Éditables
  (renommer / réordonner / ajouter / supprimer / réinitialiser). Le statut d'une
  carte = la `key` d'une colonne.
- **Actions offertes** (carte) : **glisser** (change de colonne → `PATCH {status}`),
  **✕ supprimer** (immédiat), **clic corps** → ouvre la fiche sur la carte. Actions
  colonnes : renommer, réordonner, ajouter, supprimer (avec déplacement obligatoire),
  réinitialiser.
- **Endpoints** : `GET /pipeline` (liste), `GET /pipeline/meta` (colonnes+priorités),
  `GET /pipeline/parcel/{idu}`, `POST /pipeline` (add), `PATCH /pipeline/{id}`,
  `DELETE /pipeline/{id}`, `crm_columns` (POST/PATCH/DELETE/reorder/reset).
- **Tables lues** : `pipeline_entries`, `crm_columns`, `parcels`,
  `dryrun_parcel_evaluations` + `parcel_p_score_v2` (scoring, via `_premium_head` /
  `verdict_servi`), `parcelle_personne_morale` (proprio public), `event_log`
  (compteur), `projets`, `parcel_residuel` (**VUE M135**, via `verdict_servi`).
  **Écrites** : `pipeline_entries`, `crm_columns`.
- **Qui crée une entrée** : l'utilisateur via la fiche **« + Pipeline »**
  (`Fiche.tsx:498` `PipelineButton` → `POST /pipeline`) ; un **projet/copilote**
  (`projet_id`). **Aucun import.**

---

## B — Branchements et véridicité

### B1 — Fraîcheur : LIVE, pas figé — **conforme (RAS)**

`pipeline_entries` ne stocke **aucune** donnée parcelle (que `parcel_id` + un
`relationship` live, `models.py:647,658`). `_entry_dict` (`app.py:4451-4476`) relit
tout **à chaque `GET /pipeline`** : `p.surface_m2`/`p.commune` live, `_ban_adresse`
live, `_premium_head` (scoring) live, `verdict_servi` live (lequel lit la **VUE M135**
`parcel_residuel` du run servi). **Une carte ne peut pas afficher une donnée périmée**
— rien n'est gelé. *La bascule M135 d'hier soir est donc vue en direct.* **RAS.**

### B2 — Compteurs vs contenus — **conforme (RAS)**

Le nombre en tête de colonne = `items.length` (`Kanban.tsx:360`), où
`items = byCol(key)` filtre `entries.data` (`Kanban.tsx:220`). Compteur et contenu
viennent de **la même source client** → **toujours cohérents**, aucun écart possible.
(Le compteur d'en-tête de page = `entries.data.length`, même source.)

### B3 — `created_at` figé à côté de données live — **cosmétique**

`created_at` est figé à l'ajout (`app.py:4464`) tandis que le scoring/surface sont
d'aujourd'hui (B1) → incohérence théorique (« ajoutée le 12/06 » + rang recalculé au
run du 21/08). **Mais `created_at` n'est PAS affiché sur la carte** (`Kanban.tsx`
n'affiche ni date d'ajout, ni SDP/zone/prix figés). L'écart n'est pas exposé.
**Gravité : cosmétique.**

### B4 — Liens — **conforme / cosmétique**

Clic corps de carte ou IDU → `select(idu)` + `setView('cartes')` → ouvre la **bonne
fiche** (`Kanban.tsx:38-42,47-53`). ✕ → delete. Le label **« ▸ projet »**
(`Kanban.tsx:74-77`) est **décoratif, PAS un lien** (aucun `onClick`) — on ne peut pas
ouvrir le projet d'origine depuis la carte. **Gravité : cosmétique** (lien projet
manquant).

### B5 — Sourcé/Estimé — **dette doctrinale**

Les chiffres de carte (surface, rang `#N`, tier) sont **nus** — pas d'étiquette
Sourcé/Estimé (doctrine M133 B.5). Le seul tooltip du rang est `SCORE_TIP.q`
(définition de « Q »), pas une provenance. **Nuance** : aucune valeur *estimée* (SDP,
capacité) n'est servie sur la carte → pas de mensonge, juste l'étiquette absente.
**Gravité : dette doctrinale (nu mais non trompeur).**

---

## C — Solidité des mécanismes

### C1 — Échec d'écriture silencieux — **faux négatif**

Le drop appelle `move.mutate` **sans optimistic update** (bon choix : la carte ne
bouge qu'après confirmation serveur via invalidation, `Kanban.tsx:179-182,331-336`) —
donc **jamais d'état menteur**. **Mais `move` (et `del`) n'ont AUCUN `onError`** : sur
un 500/coupure, l'échec est **totalement silencieux** (pas de toast, la carte « ne
prend pas » sans explication ; retry global = 1 seule fois, `main.tsx:45`).
**Gravité : faux négatif** (un échec d'écriture est masqué).

### C2 — Concurrence : last-write-wins, sans verrou ni rafraîchissement — **dette / faux négatif**

`PATCH /pipeline/{id}` (`app.py:4619-4652`) n'a **aucun verrou optimiste** (pas de
`version`/`updated_at` comparé) → dernier PATCH gagne en silence. L'autre onglet **ne
converge pas** : la query `['pipeline']` n'a **pas de `refetchInterval`** (contrairement
à `events-count`), et `refetchOnWindowFocus:false` (`main.tsx`) → état périmé jusqu'à
60 s sans signal. **Gravité : dette + faux négatif** (acceptable en mono-poste, à
qualifier en multi-poste).

### C3 — Double drop — **cosmétique**

Idempotent par construction (`setDragId(null)` + `PATCH e.status=cible` → même état ;
`UniqueConstraint` empêche tout doublon). Pas de fantôme. **Gravité : cosmétique**
(correct par idempotence, pas par garde explicite).

### C4 — Volume : pas de LIMIT + N+1 serveur — **dette**

`GET /pipeline` renvoie **tout** sans `LIMIT` (`app.py:4552-4560`) ; le front filtre
tout côté client, O(colonnes × entrées) par render, non mémoïsé. Surtout,
`_entry_dict` fait **~5-6 requêtes SQL PAR carte** (`_latest_eval`, `verdict_servi`,
`_premium_head`, `_ban_adresse`, `_proprietaire_public`, `_projet_ref`) = **N+1
franc**. Borné par le volume de conception (« pipeline = volume faible »,
`app.py`), dangereux s'il grossit. **Gravité : dette.**

### C5 — Suppression carte : dure, immédiate, sans filet — **faux négatif / dette (cardinal produit)**

Le ✕ appelle `del.mutate()` **directement au clic** (`Kanban.tsx:61-68`), **aucune
confirmation**, DELETE **dur** irréversible (`app.py:4655-4663`). Il détruit la
**prospection manuelle** (JSONB : statut proprio, contact — saisie utilisateur,
`models.py:654`), les notes et le reminder, **sans avertissement**. Contradiction de
doctrine flagrante : le module se réclame de « **on ne perd JAMAIS une carte** »
(`crm_columns.py:8`, `Kanban.tsx:112`) et l'applique aux **colonnes** (déplacement
obligatoire) — **mais pas à la carte**. Et `del` n'a pas d'`onError` (C1).
**Gravité : faux négatif de doctrine / dette.**

### C6 — Doublons — **conforme (RAS)**

Impossible : `UniqueConstraint(compte_id, parcel_id)` (`models.py:643`) + garde
applicative (`existing` avant insert, `app.py:4586-4591`). Double verrou. **RAS.**

### C7 — Cloisonnement `compte_id` — **conforme (RAS)**

**Tous** les endpoints pipeline filtrent par compte (SEC-IDOR) : `pipeline_list`
(`app.py:4557`), `pipeline_add`/`patch`/`delete`/`parcel` (contrôle
`e.compte_id == cid`), `pipeline_meta` (colonnes par cid), rattachement projet vérifié
(`app.py:4609`). **Aucune requête CRM sans filtre compte.** **RAS.**

### C8 — Drop hors fenêtre paginée — **dette (ergonomie)**

Les colonnes hors de la fenêtre de 5 (`COLS_PAR_VUE`) sont absentes du DOM → pas de
cible de drop : il faut relâcher, paginer, re-glisser. Documenté/assumé, aucun effet
de bord. **Gravité : dette ergonomique.**

---

## D — Doctrine

### D1 — Fuite de rang/score dans le payload — **dette / décoratif**

`GET /pipeline` (via `_entry_dict`) transporte : `verdict.rang`,
`verdict.opportunity_score`, `premium.rang_v2`, `premium.tier_v2`,
`premium.completeness_score`, `premium.statut`, `etage0`. **`rang_v2` et `tier_v2`
sont AFFICHÉS** (`Kanban.tsx:95,100` — le « #234 » et le tier ; **retirés de l'écran
par la Partie 1**, mais **le payload les transporte toujours** → fuite du précédent
M133 B.6, à purger — décision Vic). Les autres (`opportunity_score`, `verdict.rang`,
`statut`) transitent **sans être rendus**. **Aucun export CSV/PDF du CRM n'existe**
(vérifié, 0 route/bouton) → pas de fuite par fichier côté CRM.

*Bug de type frontend* : `types.ts:130` déclare `premium: { q_score; a_score; … }`
alors que `_premium_head` ne renvoie **ni `q_score` ni `a_score`** — **type
mensonger** (`undefined` au runtime). **Gravité : dette (purge payload) / décoratif
(type mort).**

*Hors périmètre à signaler* : `/parcels/export.csv` (`app.py:1361-1382`, la **liste**,
pas le CRM) exporte `tier_v2`/`rang_v2`/`completeness` dans un fichier — **fuite
rang/score hors application** au regard de M133 B.6. Mérite un audit liste dédié.

### D2 — `MAX(run_id)` / tri lexical — **conforme (RAS)**

`_premium_head` (`app.py:4511-4513`) et `verdict_servi` s'épinglent au **run servi**
via `_score_v2_run_id` (`app.py:1835`, `WHERE run_id = :label`, `Q_A_RUN_LABEL`) —
**jamais un `MAX(run_id)` ni un tri de chaîne**. La dette §8 M133 (q_v9 > q_v10) est
**explicitement fermée ici**. **RAS.**

### D3 — Valeurs fabriquées / libellés sur-promettant — **cosmétique**

Aucune valeur-parcelle fabriquée : sans `premium`, la carte dit honnêtement « hors run
de référence » et rang vide (pas de `#—` inventé) ; `NON_EVALUEE` → `rang:None`. Seuls
défauts mineurs : `priority` par défaut « moyenne » codé en repli (`app.py:4596`,
champ de saisie, pas une donnée), accent couleur de repli (`Kanban.tsx:325`), et le
tooltip `SCORE_TIP.q` **mal apparié** au `rang_v2` (Q décrit, P×C survolé,
`Kanban.tsx:99`). **Gravité : cosmétique.**

---

## E — Verdict d'utilité (franc)

### 1. À quelle question la page répond-elle RÉELLEMENT ?

Le libellé promet un **« CRM — pipeline de prospection »** (relances, priorités,
historique). En réalité, la page répond à : **« dans quelle colonne ai-je rangé
chaque parcelle que j'ai ajoutée ? »**. C'est un **tableau de rangement** : on ajoute
(depuis la fiche), on **glisse** entre colonnes, on **supprime**. Rien de plus.

### 2. Un utilisateur qui suit 50 parcelles peut-il travailler avec ?

**Non — c'est un tableau qui s'admire.** Le backend (modèle + `PATCH`) supporte
`notes`, `reminder_date` (**relances**), `priority`, `prospection` — mais **AUCUNE UI
ne les câble** : `patchPipeline` n'est appelé QUE pour `{status}` (le drag,
`Kanban.tsx:180`). Concrètement :
- **Relances** : `reminder_date` est un **champ MORT** — aucune UI pour le poser,
  jamais affiché. Un CRM sans relance n'est pas un CRM.
- **Notes** : non éditables (le PATCH les accepte, rien ne les envoie).
- **Priorité** : figée à « moyenne » à la création, **jamais modifiable** à l'écran.
- **Historique** : seulement un badge « X nouveaux » (événements), aucune timeline.
- **Prospection** (contact, statut proprio) : détruite au ✕ sans filet (C5).

L'utilisateur peut donc **ranger** ses 50 parcelles en colonnes et rien d'autre : ni
noter un appel, ni programmer un rappel, ni prioriser, ni consulter un historique de
contacts. **Le maillon manquant, c'est le travail de suivi lui-même.**

### 3. Améliorations, par rapport valeur/coût

**Défauts (à réparer) :**
1. **Câbler l'édition (le cœur manquant)** — UI pour **relance/reminder**, **notes**,
   **priorité** : le backend est déjà prêt (PATCH), il ne manque que le front. *C'est
   ce qui transforme le tableau en CRM.* **Plus haute valeur.**
2. **C5 — suppression carte avec filet** : confirmation + archivage/soft-delete
   (honorer « aucune carte perdue » au niveau carte, pas seulement colonne) ; ne pas
   détruire la prospection en silence.
3. **C1/C5 — feedback d'échec** : `onError` sur `move`/`del` (un toast), sinon les
   écritures ratées sont invisibles.
4. **D1/B5 — purger le payload** (`rang_v2`, `opportunity_score`, `verdict.rang`) —
   M133 B.6 ; corriger le type front mensonger ; étiqueter Sourcé/Estimé si des
   valeurs estimées sont ajoutées un jour.

**Manques (à construire) :**
5. Lien « ▸ projet » cliquable (B4) ; timeline d'historique de contacts.
6. **Dettes** : N+1 `_entry_dict` + `LIMIT` (C4) et concurrence/`refetchInterval`
   (C2) — bornées par le faible volume, à traiter avant toute montée en charge.

### Franchise

**Le socle est sain et honnête** : fraîcheur live (B1), cloisonnement compte parfait
(C7), run servi épinglé sans `MAX` (D2), zéro doublon (C6), aucune valeur fabriquée
(D3). **Mais en l'état, la moitié « CRM » est un gadget** : la machinerie de suivi
(relances, notes, priorités) existe en base et **n'est branchée à aucune UI** — la
page ne fait que déplacer des cartes entre colonnes. Ce n'est pas un défaut de
calcul, c'est un **produit inachevé** : le plus dur (le modèle, les endpoints, le
cloisonnement) est fait ; le geste qui manque est l'**écran d'édition d'une carte**.

---

*Fin d'audit. Aucune correction appliquée. Branche `audit/crm` — CC ne merge pas.
Vic arbitre le périmètre du mandat de correction (M137).*
