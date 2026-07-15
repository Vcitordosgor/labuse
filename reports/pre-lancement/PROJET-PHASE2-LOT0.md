# PROJET Phase 2 — Constat Lot 0 (lecture seule)

**Branche** : `feat/projet-phase2`. **Date** : 2026-07-15. **Verdict : auto-CRM + chercher-plus
s'ajoutent PROPREMENT — aucun obstacle, on construit.**

## Le CRM / pipeline (décortiqué)
`pipeline_entries` (`models.py:607`) : `parcel_id UNIQUE, status, priority, notes, reminder_date,
prospection jsonb, projet_id (FK→projets, SET NULL)`. Colonnes de statut EN CONFIG (`config/pipeline.yaml`) :
`reperee → proprietaire_a_identifier → contact_a_preparer → contacte → relance_prevue → en_discussion →
chaud → abandonnee`. Défaut `reperee`. Priorités haute/moyenne/basse.
- **Création** : `POST /pipeline {idu, status?, priority?, projet_id?}` (déjà **already:true** si la parcelle
  y est déjà — `parcel_id` unique). **`PATCH /pipeline/{id}`** (statut/priorité/notes/rappel).
  **`DELETE /pipeline/{id}`** (existe, `app.py:2891`).
- **Affichage** : `GET /pipeline` → Kanban (`crm/Kanban.tsx`), cartes glissables par colonne.
  `_entry_dict` renvoie déjà **`projet` = {id, nom}** (`_projet_ref`, d'où vient la piste) — le lien
  projet↔CRM est **déjà cablé côté donnée**, il ne s'affiche juste pas encore sur la carte.
- **Statut d'entrée pour une retenue** : `contact_a_preparer` (« Contact à préparer ») = le « à contacter ».

## Contact propriétaire (privacy)
`parcelle_personne_morale` (idu, denomination, siren, groupe_label, forme_juridique…) : **82 701 lignes,
TOUTES avec dénomination — PM UNIQUEMENT** (données DGFiP publiques). Un **particulier n'y est jamais**.
Le pattern privacy existe déjà : la **fiche** expose `proprietaire_moral` (join sur cette table) et rien
pour un particulier. **Règle** : idu présent dans `parcelle_personne_morale` → afficher dénomination +
SIREN ; **sinon → aucune identité** (« propriétaire particulier — non communiqué »). C'est la même ligne
rouge que M11 B2.

## « Chercher plus »
La proposition Phase 1 (`_search_items` dans `projets.py`) réutilise la recherche servie (M22
`faisabilite_sens2` si programme, sinon `q_v6_m8 _q_v2_list`). `POST /{pid}/proposer` **upsert
`ON CONFLICT DO NOTHING`** → **déjà dédupliqué**. Pour « chercher plus » :
- **Élargir** : rejouer la recherche avec des filtres **assouplis** (override sur les filtres dérivés :
  surface min ↓, périmètre → toute l'île) → nouvelles `proposee`, dédup automatique.
- **Ajout manuel** : `INSERT` d'une parcelle par IDU en `proposee` (dédup via la même contrainte unique).
  Le clic-carte alimente le champ IDU (la carte reste cliquable en fond du parcours).

## Verdict — s'ajoute proprement
- **Auto-CRM** : le `PATCH /{pid}/parcelle/{idu}` (Phase 1) est le point unique où le statut change → on y
  branche : `retenue` ⇒ `INSERT pipeline_entries (projet_id=pid, status=contact_a_preparer) ON CONFLICT
  DO NOTHING` ; quitter `retenue` ⇒ `DELETE ... WHERE parcel_id AND projet_id=pid` (ne touche QUE les
  entrées auto-liées à CE projet — une entrée manuelle d'un autre projet/hors projet est préservée).
- **Chercher plus** : 2 routes additives (`/{pid}/chercher-plus` élargi, `/{pid}/ajouter` manuel), dédup
  par la contrainte unique de `projet_parcelles`.
- **Privacy** : `proprietaire_public` ajouté à `_entry_dict` (PM → dénomination+SIREN ; sinon type
  `particulier` sans identité). **Aucune touche scoring** : on lit le run servi, on gère statuts+pipeline.

*Constat rendu. Aucun obstacle → construction Phase 2.*
