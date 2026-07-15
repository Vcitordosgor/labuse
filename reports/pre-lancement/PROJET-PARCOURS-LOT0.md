# PROJET · PARCOURS DE SÉLECTION — Constat Lot 0 (lecture seule)

**Branche** : `feat/projet-parcours` (NON mergée). **Date** : 2026-07-15. **Verdict : le modèle
supposé s'ajoute PROPREMENT à l'existant — pas de divergence, on construit la Phase 1.**

## Le modèle Projet existant (décortiqué)

**Table `projets`** (`models.py:635`, DDL `projets.py`) : `id, nom, fiche jsonb, filtres jsonb,
programme jsonb, statut('actif'|'archive'), derniere_execution_at, created_at, updated_at`.
- `fiche` = ce que le promoteur A DIT (structuré par l'entretien : type_programme, ampleur,
  perimetre, contraintes, budget, criteres_libres — `FICHE_SCHEMA`).
- `filtres` = dérivé DÉTERMINISTE de la fiche (sdpMin, communes, flagsExclus…).
- `programme` = paramètres M22 si programme chiffré.
- **Aucune relation projet × parcelle aujourd'hui.** Un projet ne stocke QUE des critères.
- Doctrine (docstring du modèle) : **« Ouvrir un projet = REJOUER filtres — jamais un snapshot
  figé. »** Les parcelles ne sont pas persistées : elles sont recalculées à chaque ouverture.

**L'entretien de cadrage** (`ia.py:475`, `POST /ia/entretien`) : conversation multi-tours → construit
`fiche` + `nom` + `pret`. Quand `pret=true`, le front dérive `filtres`/`programme` (déterministe,
aucun chiffre inventé par l'IA) et prévisualise via `POST /projets/apercu`.

**La « proposition »** (`projets.py:244 /apercu`) : compteur SQL + **top N** (≤20) parcelles avec un
**« pourquoi » SORTI DU MOTEUR** (`_pourquoi_lignes` : verdict/tier, SDP résiduelle vs besoin, hauteur
PLU, carence SRU — aucune valeur inventée). Source : **M22 `faisabilite_sens2`** (si programme) ou le
**run servi `q_v6_m8` `_q_v2_list`** (sinon). **Live à chaque appel, jamais un snapshot.** Sur la carte,
la restitution flotte (`iaRestitution`, top cliquable — la « pastille en lévitation »).

**Le CRM** (`pipeline_entries`, `models.py:607`) : `parcel_id UNIQUE, status, priority, notes,
reminder_date, prospection jsonb, projet_id (FK→projets, ON DELETE SET NULL)`. **La colonne `projet_id`
existe déjà** — le branchement « retenues → CRM » a donc déjà son point d'ancrage (Phase 2). Une parcelle
entre au CRM via `POST /pipeline` (`{idu, status?, priority?, projet_id?}`).

## Verdict de faisabilité — **s'ajoute proprement**

Les hypothèses (statuts `proposée`/`retenue`/`écartée`, reprise = rejouer + réafficher les statuts,
retenues → CRM) **collent** :
- Le modèle Projet reste **piloté par les faits** (fiche dite / filtres dérivés) — on n'y touche pas.
- On ajoute une **table de liaison** `projet_parcelles(projet_id, parcel_id, statut, rang, timestamps,
  UNIQUE(projet_id,parcel_id))` — purement additive, rétro-compatible (les projets existants restent
  intacts, la table naît vide).
- **Proposition** = on RÉUTILISE la recherche existante (`/apercu` → M22/q_v2) et on **rattache** les
  résultats au projet en statut `proposée` (upsert **sans écraser** une décision `retenue`/`écartée`).
  **Zéro re-scoring** : on lit `q_v6_m8`, on ne calcule rien.
- **Décision** (Tinder) : `proposée → retenue|écartée`, persistée. **Réversible** : `écartée` reste en
  base, récupérable (jamais de destruction — la boussole).
- **Reprise** : rejouer les filtres (proposer les nouvelles) + réafficher les statuts persistés.
- **Retenues → CRM** : `pipeline_entries.projet_id` prêt — **mais c'est la Phase 2** (lien raffiné),
  hors de ce mandat. En Phase 1, `retenue` est un statut ; aucune écriture CRM.

**Données réutilisées telles quelles** (aucune invention) : `_q_v2_fiche` (adresse BAN, q/a/complétude,
`score_v2.tier`, centroïde, `lines`) + `_points_cles` (forces/attentions, logique du pack apporteur) +
`_pourquoi_lignes` (SDP vs besoin, hauteur, SRU). La carte de décision n'affiche que du sourcé.

## Point de vigilance remonté (non bloquant)
La décision produit **#4 « retenues → CRM automatique »** et le **phasage** (« lien CRM raffiné = Phase 2 »)
se recouvrent. J'applique le **phasage** : en Phase 1 `retenue` est un **statut** (pas d'insertion CRM
automatique). Le FK `projet_id` est prêt pour brancher ça en Phase 2. À confirmer par Vic si tu veux
l'insertion CRM dès maintenant.

*Constat rendu. Aucune divergence bloquante → construction Phase 1.*
