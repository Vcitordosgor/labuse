# AUDIT — SECTION PROJETS

**Branche** : `audit/projets` · **Date** : 2026-08-24 · **Type** : audit seul (aucun code modifié, un seul rapport)
**Méthode** : 2 inventaires parallèles (chaîne backend/cloisonnement · UI kanban/ponts/compteurs) + vérifications personnelles (cloisonnement au bit près comme l'audit CRM, cause du compteur « 60 », unicité de la PK projet). Postgres en lecture stricte, serveur intact.

**Verdict global** : le **cloisonnement est solide** (tous les endpoints `/{pid}*` gatent par `_projet_or_404`, 404 SEC-IDOR ; `projet_parcelles` scopé par un `projet_id` de PK GLOBALE toujours vérifié-appartenant). **Aucune fuite inter-comptes** — le « leak critique » soupçonné sur `_sync_crm` est un **faux positif levé** (voir C-note). Les grandeurs viennent du **même moteur** que les fiches. Le vrai défaut est le **compteur « 60 »** signalé par Vic : une **migration M140 à moitié faite** — la liste affiche le compte FIGÉ (stocké, ~60), l'ouverture sert le compte VIF (cadrage complet, plus). C'est le point à corriger (P1).

---

## 1. Cloisonnement (périmètre 1) — SOLIDE

| Surface | Cloisonnée ? | Vérif |
|---------|-------------|-------|
| `GET /projets` (liste) | ✓ | `_scope(query, cid)` (compte_id IS NULL / == cid) |
| `GET/PATCH/DELETE /{pid}`, `/rejouer`, `/proposer`, `/parcelles`, `/carte/{idu}`, `/parcelle/{idu}`, `/chercher-plus`, `/ajouter`, `/export.pdf`, `/export.csv` | ✓ **12/12** | chacun appelle `_projet_or_404(db, pid, current_compte(request))` → 404 si pas au compte (SEC-IDOR, jamais un 403 révélateur) |
| `GET /pour-parcelle/{idu}` | ✓ | jointure `projets.compte_id` scopée (l.735) |
| `projet_parcelles` (par `projet_id`) | ✓ | `projet_id` = PK GLOBALE de `projets` (models.py:689, serial) → un id = un projet = un compte ; toujours lu APRÈS le gate d'appartenance |
| `POST /apercu`, `/derive`, `/compteur` | ✓ | preview sans état (pas de donnée d'un compte servie) |
| `GET /reperes`, `/types` | ✓ | référentiel PUBLIC (pas de donnée client) |
| migration l.84/96 (`SELECT/UPDATE projets` sans compte) | ✓ | **migration M120** (backfill `identite` depuis `fiche`), tous projets, boot/admin — pas un endpoint servi |

### C-note — `_sync_crm_*` sans `compte_id` explicite : SÛR (défense en profondeur) · gravité : très faible
Un inventaire a signalé une « fuite critique » : `_sync_crm_projet_statut` (l.849) fait `UPDATE pipeline_entries SET archived_at … WHERE projet_id = :pid` **sans `compte_id`**. **Faux positif, levé** : `projets.id` est une **PK globale** (models.py:689) — un `projet_id` désigne UN projet d'UN compte. La fonction est appelée UNIQUEMENT après `_projet_or_404` (PATCH l.772, DELETE l.794) qui a vérifié l'appartenance ; et les `pipeline_entries` portant ce `projet_id` ont été créées par `_sync_crm_retenue` avec `compte_id = cid` (le compte du projet). L'UPDATE ne peut donc TOUCHER qu'un seul compte. **Aucune fuite.** Réserve identique à `_sync_crm_retenue` (l.844, `WHERE parcel_id AND projet_id`). C'est de la **défense en profondeur** (comme le `rename_column` du CRM, C2) : sûr aujourd'hui par l'unicité de la PK + le gate amont, fragile si un futur refactor retirait le gate. Correctif candidat : passer `cid` et ajouter `AND compte_id IS NOT DISTINCT FROM :cid`.

---

## 2. Chaîne de données & grandeurs (périmètre 2) — SOLIDE

- **`projets`** : `filtres` (JSONB) = **LE CADRAGE**, un jeu de `Filters` (camelCase : communes/surfaceMin/sdpMin/flags…) — **point unique des critères** (la dérivation parallèle a disparu en M120) ; `identite` (JSONB) = budget_eur/type_logement **informatifs, 0 effet moteur** (mesuré M119/M120) ; `derniere_execution_at`, `shortlist_perimee`. Legacy `fiche`/`programme` **jamais relus** (conservés pour migration — cf. blocs morts).
- **`projet_parcelles`** : `statut` (proposee/retenue/ecartee/a_analyser), `rang`, `proposee_at`, `hors_criteres`. `UNIQUE(projet_id, parcel_id)`, FK cascade.
- **Grandeurs** (surface, SDP, charge, tier) : viennent du **MÊME moteur que les fiches** — `parcel_residuel` (cache de la cascade) + le run servi via `FiltreCriteres.where()`. **Aucun recalcul divergent** dans projets.py : le cadrage filtre sur les mêmes colonnes que la carte et la fiche. Le kanban affiche `tier` (via `TierBadge`, source unique), `surface_m2`, `etat_bien`, `marche_eur_m2`, `proprietaire_public` (PM publique seulement) — cohérents avec la fiche.

---

## 3. Compteurs (périmètre 3) — LE BUG « 60 vs plus » · gravité : MOYENNE-HAUTE (P1)

**Cause racine : une migration M140 à moitié faite.** Deux modèles de « proposées » coexistent :

| Mécanisme | Ce qu'il compte | Où affiché |
|-----------|-----------------|-----------|
| **STOCKÉ (M120)** `_figer_shortlist` écrit ~60 lignes `statut='proposee'` (cap `shortlist_defaut = 60`, l.594) ; `_counts_by_projet` (l.550) = `SELECT statut, count(*) FROM projet_parcelles GROUP BY` | le **figé** (≈ **60**) | **badge de la LISTE** (`GET /projets` → `p.counts.proposee`, ProjetsPanel.tsx:97) + l'export PDF/CSV (toutes les figées, sans LIMIT) |
| **VIF (M140 Lot A)** `GET /{pid}/parcelles` : `counts.proposee = _cadrage_total(cadrage) − décidées` (recompte LIVE du cadrage, ~4 s) | le **total réel du cadrage** (souvent **> 60**) | **en-tête de colonne à l'OUVERTURE** (`etat.counts.proposee`, ProjetKanban.tsx:259) |

**Le « 60 » que Vic voit** = le compte FIGÉ stocké (la shortlist M120 plafonnée à 60). **À l'ouverture**, l'en-tête sert le total VIF du cadrage (davantage). M140 a rendu l'OUVERTURE vive mais a laissé la LISTE (et l'export) lire le compte figé → **les deux divergent**.

**Confusion secondaire à l'ouverture** : l'en-tête montre le total VIF (ex. 200) mais la fenêtre chargée montre `etat.proposees.length` (page paginée, 60) → « X sur N » (ProjetKanban.tsx:302). Intentionnel (pagination M140) mais lisible comme une 3ᵉ valeur.

**Les autres compteurs ont-ils le défaut ?** NON. `retenue`/`ecartee`/`a_analyser` sont des **décidées, stockées dans les deux modèles** → le badge de la liste et l'en-tête d'ouverture **concordent**. **Seul `proposee` diverge** (figé-stocké côté liste vs vif-cadrage côté ouverture).

**Correctifs candidats (sans les faire)** :
- rendre la liste cohérente avec l'ouverture — servir/mettre en cache le total VIF du cadrage pour la liste (coût : ~4 s × N projets → cache/matérialisation nécessaire) ; OU
- **assumer** que le badge liste est le « top N figé » et l'ÉTIQUETER comme tel (« top 60 figé le JJ/MM », pas un « 60 » brut) ; OU
- (le plus propre) achever M140 : **cesser de stocker les `proposee`** (elles sont vives), servir UN seul compte vif partout, et retirer les lignes `proposee` stockées devenues vestigiales.

---

## 4. Formulaire de création (périmètre 4) — SAIN

`ParcoursProjet.tsx` : nom (défaut calculé « Projet {commune} » si vide), périmètre (île par défaut / communes), budget + type (facultatifs, informatifs), cadrage (facettes `FiltreFacettes` en contexte isolé, jamais écrit dans le store carte). Erreurs : `setErreur('La création a échoué — réessayez.')`, bouton désarmé (`envoi`), réarmé en `finally`. Succès → `setCree(...)` + **invalidation `['projets']`** (la liste se rafraîchit) + écran « projet créé » avec la shortlist. **Dédup douce** (`_find_doublon`) : un projet actif de même cadrage/nom propose la reprise (rien n'est écrasé). Pas de piège d'échec partiel identifié.

---

## 5. Kanban projet (périmètre 5) — SAIN, distinct du CRM

3 colonnes (`proposee` À trier / `retenue` Retenues / `ecartee` Écartées) + pile `a_analyser`. Déplacement par **drag** ou boutons (✓ Retenir / ◑ Peut-être / ✕ Écarter / ↩ À trier). `PATCH /{pid}/parcelle/{idu}` → `{ok, statut, counts}`. **Optimistic update + rollback + toast** ; `onSettled` invalide `['parcours', pid]`, **`['pipeline']`** (auto-CRM), `['projets']`. **Non-perte au rejeu** : une décision hors cadrage RESTE (`hors_criteres`), jamais évincée en silence. Tri Tinder (`ParcoursTinder`) : une-par-une, mêmes statuts. Rien ne se perd/duplique au changement (arrays repositionnés, `counts` par delta). Distinct du Kanban CRM (colonnes personnalisables, table `pipeline_entries`).

**`_sync_crm` (projet → CRM)** : « retenir » une parcelle → `_sync_crm_retenue(…, cid)` crée une piste `pipeline_entries` avec `compte_id=cid`, `projet_id=pid` (ON CONFLICT restaure) ; « écarter/à-trier » → archive la piste de CE projet (`WHERE projet_id`). Archiver le projet (PATCH/DELETE) → `_sync_crm_projet_statut` suit les cartes. Scopé (cf. C-note).

---

## 6. Ponts & blocs morts (périmètre 6)

| Pont | Mécanisme | Verdict |
|------|-----------|---------|
| Projet → fiche | clic carte → `select(idu)` (store) | ✓ |
| Projet → CRM | « retenue » → `_sync_crm_retenue` (+ invalidate `['pipeline']`) | ✓ |
| Copilote → Projet | `projet_form.prefill` → `ParcoursProjet` (nettoyé après création) | ✓ |
| Projet → outils (Assemblage/Courrier/Faisa) | **pas de pont direct** — passe par la fiche (`select` puis outil) | note (choix produit) |
| Export | PDF (`/export.pdf`) + CSV (`/export.csv`) câblés (mais lisent la shortlist FIGÉE — cf. §3) | ✓ (réserve compteur) |

**Blocs morts / champs morts** (gravité faible) :
- `capacite_estimee` : sélectionnée dans la requête PDF (`_shortlist_pdf`) mais **jamais rendue** — colonne morte.
- Colonnes legacy **`fiche`** et **`programme`** (models.py) : `fiche` lue UNE fois à la migration M120, jamais après ; `programme` jamais lu/écrit — conservées **non-destructif** (extinction). À documenter comme telles.
- Aucun bouton `onClick` vide, aucun « bientôt », aucun disabled non câblé (vérifié front).

---

## 7. Gravités & correctifs candidats

| Réf | Constat | Gravité | Correctif candidat |
|-----|---------|---------|--------------------|
| **P1** | compteur « proposee » : LISTE = figé stocké (~60) vs OUVERTURE = vif cadrage (plus) — M140 à moitié fait | **moyenne-haute** | un seul compte servi partout (cacher le total vif OU étiqueter « top N figé » OU cesser de stocker les proposées) |
| **P2** | à l'ouverture, en-tête (total vif) vs cartes chargées (`.length` page 60) lisible comme 2 chiffres | faible | libeller « X affichées sur N » sans ambiguïté |
| C-note | `_sync_crm_*` UPDATE par `projet_id` sans `compte_id` explicite | très faible | ajouter `AND compte_id IS NOT DISTINCT FROM :cid` (défense en profondeur) |
| D1 | `capacite_estimee` sélectionnée jamais rendue ; colonnes `fiche`/`programme` en extinction | faible | retirer la colonne du SELECT PDF ; documenter fiche/programme « en extinction » |

**Points sains à conserver** : cloisonnement complet (12/12 endpoints gatés, PK globale + gate = pas de fuite) ; grandeurs = source unique moteur (parcel_residuel, comme la fiche) ; cadrage = jeu de filtres unique (`FiltreCriteres`) ; non-perte au rejeu (`hors_criteres`) ; auto-CRM scopé ; formulaire honnête (erreur + invalidation + dédup douce) ; deux Kanban distincts.

**Conclusion** : la section Projets est **bien cloisonnée et cohérente sur les grandeurs** ; le « leak » soupçonné n'en est pas un (PK globale + gate). Le seul vrai défaut est le **compteur « 60 »** — une migration M140 laissée à mi-chemin entre le figé stocké (liste/export) et le vif cadrage (ouverture). Le fermer aligne ce que le projet promet sur ce qu'il liste.
