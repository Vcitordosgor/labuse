# PROJET Phase 2 — chercher plus + lien CRM — livré

**Branche** : `feat/projet-phase2` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Construit SUR Phase 1** (`projet_parcelles`) **et le CRM existant** (`pipeline_entries.projet_id`).
**Zéro touche scoring/cascade/étage 0/run** : `git diff main...HEAD` = API projet/CRM + front + docs,
aucun fichier scoring/engine. Les parcelles viennent du run servi — on gère parcelles/statuts/pipeline.

| Lot | Commit | Contenu |
|-----|--------|---------|
| 0 | constat | CRM + privacy + chercher-plus décortiqués → verdict **additif** (`PROJET-PHASE2-LOT0.md`) |
| 1-2 (back) | backend | chercher-plus/ajouter + auto-CRM + contact `_proprietaire_public` |
| 1-2 (front) | front | panneau « Chercher plus » + Kanban (projet + contact privacy) + cohérence |

## Lot 0 — Constat (verdict : additif, aucun obstacle)
`pipeline_entries` complet (POST/PATCH/DELETE, `projet_id` déjà cablé, `_entry_dict` renvoie déjà
`projet`). `parcelle_personne_morale` = **PM UNIQUEMENT** (82 701 lignes, DGFiP public) → un particulier
n'y est **jamais** → base sûre pour la règle privacy. Colonne d'entrée d'une retenue = `contact_a_preparer`.

## Lot 1 — Chercher plus (dédupliqué, zéro re-scoring)
Panneau **« ＋ Chercher plus »** dans le parcours :
- **Élargir la recherche à toute l'île** (`POST /{pid}/chercher-plus {ile:true}`) : rejoue le **même
  moteur** avec le périmètre relâché (communes = île) et une profondeur plus grande → ajoute les
  **nouvelles** parcelles en `proposee`. **Dédup** par la contrainte unique (`ON CONFLICT DO NOTHING`).
- **Ajout manuel** par **IDU** (`POST /{pid}/ajouter {idu}`) — le **clic-carte** pré-remplit le champ
  (la carte reste cliquable en fond du parcours). `already=true` si déjà dans le projet.
- Les ajouts rejoignent le flux de tri normalement.
**Preuve** : `phase2-1-chercher-plus-elargir.png` (**+24** parcelles) ; `phase2-2-ajout-manuel.png`
(IDU Saint-Leu hors périmètre ajouté). Re-run élargir → **0 ajout** (dédup vérifié).

## Lot 2 — Lien CRM (retenues → pipeline), réversible, privacy
- **Auto-création** : `retenue` ⇒ entrée `pipeline_entries` liée au projet (`projet_id`), statut
  **`contact_a_preparer`** (« à contacter »). `ON CONFLICT (parcel_id) DO NOTHING` (n'écrase pas une
  entrée manuelle pré-existante).
- **Réversibilité / cohérence** : quitter `retenue` (retirer / ré-écarter) ⇒ **DELETE ciblé**
  (`parcel_id + projet_id`) → **aucune orpheline** ; une entrée manuelle d'un **autre** projet est
  préservée. Le front **invalide `['pipeline']`** à chaque décision → le Kanban reflète **en direct**.
- **Contact propriétaire — PRIVACY (ligne rouge)** : `_proprietaire_public` — **personne morale**
  (dénomination + SIREN, DGFiP public) affichée ; **particulier → aucune identité** (« Propriétaire
  particulier — non communiqué »). Même règle que M11 B2.
- **Projet ↔ CRM connectés** : chaque carte Kanban porte le **chip projet « ▸ {nom} »** (le vrai
  aboutissement du point 3).
**Preuve** : `phase2-3-crm-auto-contact.png` — colonne « Contact à préparer » peuplée, chip projet,
**ZOGREV · SIREN 388712853 / SOFICOOP · SIREN 383755949** (PM nommées) ET **« Propriétaire particulier —
non communiqué »** (particulier masqué). `phase2-4-reversibilite-crm.png` : retrait d'une retenue →
**7 → 6** cartes du projet (réversible, cohérent).

## Privacy — preuve explicite (les deux cas)
Log QA live : CRM contient un **SIREN** (PM nommée) = **true** ET contient **« non communiqué »**
(particulier masqué) = **true**. Aucune identité de personne physique n'est exposée. Backend :
`parcelle_personne_morale` PM-only ; absent de la table ⇒ type `particulier` sans champ nominatif.

## Non-régression & garanties
- **Phase 1 intacte** : le parcours (tri, sections, reprise) fonctionne (le script Phase 2 l'emprunte).
- **CRM existant intact** : les entrées hors projet gardent leur affichage (et bénéficient du contact
  proprio public). `POST/PATCH/DELETE /pipeline` inchangés.
- **Projets existants intacts** (additif).
- **Zéro touche scoring** : `git diff main...HEAD` = `projets.py`/`app.py` (routes + contact), front, docs.
  Aucun fichier scoring/cascade/étage 0/run/engine. `tsc` vert, build OK. Testé live (projet 13).

*Commits séparés sur `feat/projet-phase2`. Pas de merge.*
