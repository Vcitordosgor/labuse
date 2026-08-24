# AUDIT — CRM (pipeline de prospection)

**Branche** : `audit/crm` · **Date** : 2026-08-24 · **Type** : audit seul (aucun code modifié, un seul rapport)
**Méthode** : 2 inventaires parallèles (chaîne backend / UI Kanban) + vérification personnelle du cloisonnement (chaque requête) et de la fuite fiche. Postgres en lecture stricte, serveur intact.

**Périmètre** : ce qui vit ENTRE l'utilisateur et ses prospects — `pipeline_entries` (table CRM), `crm_columns` (colonnes par tenant), les endpoints `/pipeline*`, le front `crm/Kanban.tsx`. Six axes : cloisonnement, chaîne de données, pipeline/Kanban, ponts, blocs morts, RGPD.

**Verdict global** : le cloisonnement du CRM **proprement dit** (`/pipeline*` + `/pipeline/columns`) est **solide et testé** — chaque requête filtre `compte_id`, l'isolation est verrouillée par un test IDOR réel. **MAIS** une porte dérobée fuit : la fiche **legacy** (`_build_fiche`, servie par `/explain` et `/export`) renvoie la **prospection d'un AUTRE compte** (contact PII compris) sans filtre de compte. C'est le défaut cardinal du mandat (« un client ne doit jamais voir les prospects d'un autre ») — **C1, gravité haute**. Le reste est mineur (blocs morts d'affichage, RGPD per-prospect).

---

## 1. Cloisonnement (périmètre 1 — le point critique)

`SCOPED_TABLES` (tenant.py:33) inclut `pipeline_entries`, `crm_columns` (via son propre DDL), `courrier_demandes`, `projets`… Mécanique : `compte_id IS NOT DISTINCT FROM :cid` en lecture, `:cid` en écriture, FK `ON DELETE CASCADE`, unique `(compte_id, parcel_id)`.

| Surface | Cloisonnée ? | Vérif |
|---------|-------------|-------|
| `GET/POST/PATCH/DELETE /pipeline*` (8 routes) | ✓ toutes | chaque requête filtre `compte_id` (SEC-IDOR) ; single-get → `(e.compte_id or None) != (cid or None)` → 404 ; insert pose `compte_id=cid` ; rattachement projet vérifie l'appartenance |
| `/pipeline/columns` (7 routes) | ✓ toutes | `_own_column` (404 IDOR), `_cards_in`, list/create/rename/reorder/delete/reset : toutes `WHERE compte_id IS NOT DISTINCT FROM :cid` |
| Enrichissement `_entry_dict`/`_prefetch_maps` | ✓ | entrées déjà scopées ; `proprietaire_public` = **personne morale publique seulement, jamais un particulier** ; adresse BAN = publique ; projet = celui de l'entrée (scopé) |
| `/pipeline-rarete` | N/A | données publiques agrégées (ENAF/ZAN par commune) — pas de scope requis |
| Test d'isolation | ✓ | `test_audit_secu.py:101 test_idor_pipeline_cloison_et_meme_parcelle` (DB réelle, 2 comptes) + `test_crm_columns.py` |
| **Fiche legacy `_build_fiche`** | ✗ **C1** | `/explain` + `/export` renvoient la prospection d'un autre compte (voir C1) |

### C1 — Fuite inter-comptes de la prospection via `_build_fiche` · gravité : HAUTE
- **Où** : `_build_fiche` (app.py:3698-3710) interroge `select(PipelineEntry).where(parcel_id == p.id)` **SANS `compte_id`**, puis compose `prosp_block` avec **`"data": pe.prospection`** — c'est-à-dire **toute la prospection saisie** (contact_nom, contact_telephone, contact_email, contact_adresse, notes_contact, prochaine_action…). Servie dans le payload (app.py:3938).
- **Exposition** : `/parcels/{idu}/explain` (4017) et `/parcels/{idu}/export` (4028) appellent `_build_fiche(db, idu)` — **sans paramètre `request`**, donc incapables de connaître le compte appelant, encore moins de filtrer dessus. Authentifiées (hors `_PUBLIC`, auth.py:35) mais **inter-tenant** : n'importe quel compte connecté peut lire, pour **n'importe quel IDU**, la prospection du compte qui suit cette parcelle. Les IDU sont énumérables (431 663) → **vecteur de moisson de masse** des contacts saisis de tous les comptes.
- **La fiche PRINCIPALE est SAINE** : `/parcels/{idu}` sert `_q_v2_fiche` (premium, FIX-FICHE F3) qui **ne porte PAS** de bloc prospection ; le front récupère l'état « suivie » via `/pipeline/parcel/{idu}` (scopé). La fuite est **cantonnée aux deux chemins legacy** `/explain` + `/export`.
- **Latence** : en déploiement pilote mono-compte (tous `compte_id` NULL) rien ne fuit encore ; la faille s'ouvre **dès le 2ᵉ compte** — soit exactement le scénario pour lequel toute la cloison a été bâtie.
- **Bug conjoint** : `scalar_one_or_none()` (3700) **lève** (`MultipleResultsFound`) si **2 comptes ou plus** suivent la même parcelle — ce que l'unique `(compte_id, parcel_id)` autorise **explicitement** → `/explain` et `/export` **500** sur ces parcelles.
- **Correctif candidat (sans le faire)** : le plus simple et le plus sûr — **retirer `prosp_block` de `_build_fiche`** (la fiche premium ne l'a pas ; `/explain` et `/export` n'ont aucun besoin de la prospection d'autrui). Sinon : passer `request`/compte à `_build_fiche` et filtrer `WHERE compte_id IS NOT DISTINCT FROM :cid` + `.limit(1)` comme `/pipeline/parcel`.

### C2 — Défenses en profondeur mineures · gravité : très faible
- `rename_column` (crm_columns.py:222) fait `UPDATE … WHERE id = :id` **sans** `compte_id` — sûr **uniquement** parce que `_own_column` (404) l'a gaté juste avant ; fragile à un futur refactor. Même remarque : la boucle shortlist (app.py:3491) appelle `_build_fiche` et **exécute la requête pipeline non scopée** pour chaque candidat (le bloc est ensuite jeté — pas de fuite, mais gaspillage).

---

## 2. Chaîne de données (périmètre 2)

| Donnée | Origine | Personnel ? |
|--------|---------|-------------|
| `parcel_id` | importé (référentiel parcels, FK cascade) | non |
| `status`, `priority` | saisi (clé colonne / priorité validée) | non |
| `notes` (Text) | **saisi** (texte libre) | potentiellement (l'utilisateur peut y taper un nom) |
| `reminder_date` | saisi (PATCH) | non |
| `prospection` (JSONB) | **saisi** : `statut_proprietaire`, `contact_nom/organisation/telephone/email/adresse`, `prochaine_action`, `responsable_interne`, `notes_contact` (≤2000 car), + dates | **OUI — PII tierce** (le propriétaire prospecté) |
| `projet_id` | dérivé (piste venue d'un projet copilote, FK SET NULL) | non |
| `proprietaire_public` (servi) | dérivé — **PM publique seulement** (SIREN DGFiP), jamais un particulier | non |
| `adresse` (servi) | dérivé (BAN, publique) | non |

**Doctrine (prospection.py:3-4)** : « LA BUSE ne récupère AUCUNE donnée propriétaire nominative : tous les champs sont saisis par l'utilisateur ». Vérifié : aucune donnée nominative **importée/dérivée** ; le seul PII est **saisi par l'utilisateur** (avec `prospection.disclaimer()`). Sain sur le principe.

---

## 3. Pipeline / Kanban (périmètre 3)

- **Colonnes** : par tenant (`crm_columns`, M12 LOT H), `key` ascii stable, renommables/réordonnables/supprimables/reset. `status` d'une carte = `key` de colonne.
- **Transitions** : libres (aucune FSM) — toute colonne → toute colonne (PATCH `status`).
- **Archivage** : soft-delete réversible (`archived_at`), pas de suppression dure ; ré-ajout d'une parcelle archivée → **restaure** (garde notes/prospection). « Aucune carte perdue » : supprimer une colonne peuplée exige `move_to`, la dernière colonne est protégée, `reset` remappe avant de re-semer.
- **Compteurs** : `SELECT status, count(*) … GROUP BY status` scopé (O(1)) ; côté front = dénombrement du payload reçu. **Cohérents** (même snapshot).
- Rien ne se perd ni ne se duplique au changement de colonne (juste `status` muté, réversible).

---

## 4. Ponts (périmètre 4)

| Pont | Mécanisme | Verdict |
|------|-----------|---------|
| CRM → fiche parcelle | clic IDU sur la carte → `setView('cartes')` + `select(idu)` | ✓ sain |
| fiche → CRM | bouton « + CRM » → `POST /pipeline {idu}` (dédup + restore) | ✓ sain |
| projet « retenue » → CRM | `_sync_crm_retenue` (projets.py:835) crée/restaure une piste + `invalidate(['pipeline'])` | ✓ (scopé via `projet_id` du compte ; l'UPDATE ne re-filtre pas `compte_id` mais le projet est déjà à lui — cf. C2) |
| CRM → Courrier | **absent** — pas de bouton courrier depuis une carte ; il faut passer par la fiche | ⚠ P1 (manque, cf §5) |
| CRM → veille/surveillance | **inexistant** (découplés) | note (choix produit) |
| **deux Kanban** (`crm/Kanban` vs `projets/ProjetKanban`) | CRM = global + colonnes perso ; Projets = par projet, 3 statuts figés, tri Tinder | ✓ **distincts, pas un doublon** |

---

## 5. Blocs morts, champs jamais remplis, promesses (périmètre 5)

| Réf | Constat | Gravité |
|-----|---------|---------|
| D1 | `proprietaire_label` et `has_manual_contact` sont dans le payload (`_entry_dict`) mais **jamais rendus** par le front | faible |
| D2 | `priority` est **éditable et stockée** mais **non affichée sur la carte** (retirée du coin bas avec rang/score, purge M133 B.6 décidée par Vic) — l'utilisateur règle un champ invisible sur le tableau (visible seulement dans l'écran d'édition) | faible |
| P1 | **Pas de pont CRM → Courrier** direct depuis une carte (le Courrier ne s'atteint que par la fiche) — friction, pas un bug | faible |
| D3 | **Pas d'export CSV** du CRM (présent sur les projets `projetCsvUrl`, absent ici) | faible |
| — | Aucune colonne de `pipeline_entries`/`crm_columns` orpheline ; aucun endpoint mort ; aucune action backend sans effet (inventaire agent : tout est câblé) | ✓ |
| — | **Bonne surprise honnêteté** : le bouton d'archivage est **correctement libellé** « Archiver (réversible — restaurable) » + confirmation + toast « Carte archivée — restaurable dans Archivées » — **pas** un « Supprimer » trompeur | ✓ |

---

## 6. RGPD (périmètre 6)

**Données personnelles stockées** : uniquement **saisies par l'utilisateur** — `prospection.contact_*` (nom/tél/email/adresse du propriétaire prospecté), `notes_contact`, `notes`. Aucune donnée nominative importée/dérivée (le `proprietaire_public` servi est PM-only). Justifié (fonction cœur du CRM), avec `disclaimer()`.

| Réf | Constat | Gravité | Correctif candidat |
|-----|---------|---------|--------------------|
| **C1** (bis) | La fuite §1 expose de la **PII tierce** (contacts saisis) à d'autres comptes → **violation RGPD**, pas seulement de confidentialité | **haute** | fermer C1 (retirer `prosp_block` de `_build_fiche`) |
| R1 | **Aucune suppression définitive par carte/prospect** : `DELETE` = archive (conservée **indéfiniment**, « pas de purge auto »). Le seul effacement réel est **au compte entier** (`effacer_compte_rgpd`, comptes.py:415, tout ou rien). Un promoteur ne peut pas effacer les données d'UN prospect (droit à l'effacement au grain individuel) sans supprimer tout son compte | moyenne | ajouter une purge définitive par carte (ou sur les archivées) + une politique de rétention |
| R2 | `effacer_compte_rgpd` est **CLI/admin uniquement** (cli.py:2766) — pas de self-service effacement/export. La cascade FK est solide (supprime pipeline/prospection/notes) mais le déclencheur est manuel | faible-moyenne | exposer une demande d'effacement / portabilité (ou documenter le circuit support) |
| R3 | Contacts tiers saisis **sans gestion de consentement / base légale** à l'écran (disclaimer présent, pas de traçage de base légale) — responsabilité partagée (le promoteur est responsable de traitement) | note | surface facultative ; l'essentiel (pas de PII auto, cascade d'effacement) est là |

**Ce que l'app tient** : cascade d'effacement au compte ✓, disclaimer ✓, pas de PII auto-dérivée ✓, archivage honnêtement libellé ✓. **Ce qu'elle ne tient pas** : l'isolation inter-comptes **sur `/explain`+`/export`** (C1), et l'effacement **au grain d'un prospect** (R1).

---

## 7. Gravités & priorités

| Réf | Constat | Gravité | Action |
|-----|---------|---------|--------|
| **C1** | Fuite inter-comptes de la prospection (PII) via `_build_fiche` → `/explain`, `/export` ; + 500 si 2 comptes suivent la même parcelle | **HAUTE** | retirer `prosp_block` de `_build_fiche` (ou scoper la requête + `.limit(1)`) |
| R1 | Pas d'effacement définitif par prospect (archive conservée sans limite) | moyenne | purge par carte + rétention |
| R2 | Effacement de compte CLI/admin seulement | faible-moy. | self-service ou circuit documenté |
| C2 | `rename_column` / shortlist : requêtes non re-scopées (sûres par gate amont, fragiles) | très faible | défense en profondeur |
| D1/D2/D3/P1 | champs non rendus (proprietaire_label, has_manual_contact, priority), pas d'export CSV, pas de pont Courrier | faible | UX/complétude |

**Points sains à conserver** : cloison `/pipeline*` + `/pipeline/columns` **complète et testée** (IDOR réel), invariant « aucune carte perdue », compteurs cohérents, deux Kanban distincts non redondants, prospection sans PII auto-dérivée + disclaimer, archivage honnêtement libellé.

**Conclusion** : le CRM est bien cloisonné **là où il se pilote** ; le seul vrai trou est une **porte legacy** (`_build_fiche` via `/explain`/`/export`) qui ressert la prospection d'autrui — à fermer avant tout passage réel en multi-comptes (**C1, haute**). Le reste est de la finition (RGPD per-prospect, champs d'affichage, export CSV).
