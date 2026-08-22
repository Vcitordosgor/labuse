# M137 — CRM : le filet, la purge, l'écran de carte (`feat/m137-crm`)

Branche `feat/m137-crm` @ `657a1adb` (origin/main portait bien les merges M136 —
badges de coin retirés confirmé). Quatre lots dans l'ordre imposé.

## Lot 1 — Le filet (C5 archivage + C1 rollback)

### C5 — plus aucune suppression dure de carte

- **Modèle** : colonne `archived_at` (`models.PipelineEntry`) + `ensure_pipeline_archived`
  (ADD COLUMN IF NOT EXISTS + index). NULL = active.
- **API** : `DELETE /pipeline/{id}` **reconverti en ARCHIVAGE** (pose `archived_at`,
  ne supprime plus). Ajout de `POST /pipeline/{id}/restore` et `GET /pipeline/archived`.
  `pipeline_list` / `pipeline_for_parcel` filtrent `archived_at IS NULL` ; `pipeline_add`
  **restaure** une archivée (garde notes + prospection saisie).
- **Synchro projet** (`projets.py`) : quitter « retenue » **archive** l'entrée auto-liée
  (plus de `DELETE`) ; y revenir la **restaure** (`ON CONFLICT DO UPDATE archived_at=NULL`,
  ciblé `projet_id`). C'était un second chemin de perte dure — fermé.
- **Reste** : `demo.py:122` (seed démo, `DELETE FROM pipeline_entries`) — **hors chemin
  utilisateur** (setup de données de démo), signalé, non touché.
- **Front** : le `✕` ouvre une **confirmation d'archivage** (la carte n'est pas perdue) ;
  bouton **« Archivées »** → panneau pour consulter et **restaurer**.

**Devenir de l'endpoint de suppression** : `DELETE /pipeline/{id}` **existe toujours**
mais **archive** désormais (soft), documenté dans sa docstring. Aucun appelant front
ne fait de suppression dure (`deletePipeline` renommé `archivePipeline`).

### C1 — plus d'échec silencieux

`move`, `archive`, `restore`, `patch` (édition) : **optimistic update + snapshot ;
`onError` = rollback du snapshot + `setToast`** (message visible). Un état affiché non
confirmé par le serveur ne persiste jamais. Mutations de colonnes : `onError` → toast.

## Lot 2 — Purge du payload (D1)

Grep front préalable : `rang_v2`/`opportunity_score`/`verdict`/`premium`/`tier_v2`/
`q_score`/`a_score`/`completeness_score`/`etage0` = **0 usage** hors `types.ts` (les
usages `ResultsSection`/`sortRows` sont le panneau **liste**, `ParcelProps`, pas le CRM).
Purge sûre. `_entry_dict` : blocs **`verdict` et `premium` RETIRÉS** ; type front
`premium` supprimé (`q_score`/`a_score` étaient **mensongers**). **Contrôle** : payload
`/pipeline` (40 entrées) = **0** occurrence des champs interdits. `tsc` vert.

## Lot 3 — L'écran de carte (câblage)

Le modèle + le `PATCH` portaient déjà note / priorité / relance / prospection ; **aucune
UI ne les exposait** (audit E). Câblé :
- **clic sur le corps de la carte → panneau d'édition** (le bouton IDU garde la fiche,
  `✕` archive).
- Champs : **Priorité** (était FIGÉE à « moyenne »), **Date de relance**, **Statut du
  propriétaire**, **Prochaine action**, **Contact** (nom/tél/email), **Notes** + disclaimer
  privacy. Tout via le **PATCH existant** ; `optimistic + rollback + toast`.
- `pipeline_meta` expose `proprietaire_statuts` (source unique, `prospection.statut_label`).
- **Contrôle** : PATCH persiste priorité/note/relance/prospection ; **SEC-IDOR** bloque un
  autre compte (404) sur PATCH **et** archive/restore.
- **Champ modèle sans chemin PATCH utilisateur** : seul `projet_id` (auto-géré par la
  synchro projet, jamais destiné à l'édition manuelle) — signalé, pas d'endpoint inventé.

## Lot 4 — C4 (N+1 agrégé)

`_entry_dict` accepte des maps pré-chargés (adresse BAN / proprio public / projet) ;
`_prefetch_maps` les charge en 3 requêtes batch ; `pipeline_list`/`pipeline_archived`
**eager-load** `parcel` (`joinedload`). Mono-entrée → repli par-carte.

**Mesure (pilote, 40 cartes)** :

| État | Requêtes/carte | Total (40) | Temps |
|---|---|---|---|
| Audit M136 (C4) | ~5-6 | — | — |
| Après Lot 2 (retrait verdict/premium) | 3,9 | 155 | 121 ms |
| **Après Lot 4 (batch + eager)** | **0,12** | **5** | **49 ms** |

Non-régression **prouvée** : payload batch == par-carte, **0** entrée divergente / 40.
Pas de `LIMIT`/pagination (5 requêtes = O(1) en nb de cartes ; volume CRM faible) —
**pagination consignée en dette** si le pipeline grossit.

---

## Contrôles d'acceptation finaux

1. **Aucun chemin de perte définitive** : grep `DELETE`/`db.delete` de carte → seul
   `demo.py` (hors utilisateur). Front : 0 suppression dure. ✓
2. **Rollback + message** sur chaque mutation (move/archive/restore/patch + colonnes). ✓
3. **Payload** `/pipeline` = 0 `rang_v2`/`opportunity_score`/`verdict.rang`/`q_score`/
   `a_score`. ✓
4. **Édition persistée** + **cloison compte prouvée** (PATCH + archive/restore SEC-IDOR
   → 404 sur un autre compte). ✓
5. **Compteurs justes** : base 40 → +ajout 41 → +archive 40 → +restore 41. ✓
6. **Non-régression** : drag-drop (`move.mutate` au drop) intact, lien fiche (`select`)
   intact, badges de coin toujours absents, **`tsc` vert**, **ruff sans nouveau warning**
   (app.py 16=16, models 0=0, projets 3=3, pré-existants). ✓
7. Ce rapport. ✓

## À PROPOSER (pas appliqué — arbitrage Vic)

**Indicateur de relance échue sur la carte.** Utile, mais on vient de retirer les
badges de coin (M136 P1) — je ne le rajoute pas d'office. Maquette sobre proposée :
un point ambre discret + l'échéance, à gauche du titre, UNIQUEMENT si `reminder_date`
est passée :

```
┌────────────────────────────────┐
│ 🔸 03/09  97416000AB1234    ✕ │   ← 🔸 ambre + date : relance échue (sinon rien)
│ 1 240 m² · Saint-Pierre        │
│ ▸ Projet Pierrefonds           │
└────────────────────────────────┘
```

Zéro score/rang (respecte D1). Vic tranche au rendu.

## Dette (à consigner)

- **Historique des mouvements** de carte (hors périmètre M137) — non journalisé.
- **Pagination `/pipeline`** si le volume grossit (aujourd'hui O(1) requêtes, tout-en-mémoire).
- **Purge des archivées** : décision future de Vic (aucune purge auto — une archivée vit
  jusqu'à décision contraire).
- `demo.py:122` : seul `DELETE` dur restant (données de démo, hors chemin utilisateur).
- `_premium_head` (app.py) devient inutilisé après le Lot 2 — helper laissé, à retirer.

---

*Fin. Commits sur `feat/m137-crm` (un par lot). CC ne merge jamais.*
