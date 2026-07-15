# PROJET · PARCOURS DE SÉLECTION (Tinder) — Phase 1 livrée

**Branche** : `feat/projet-parcours` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Construit SUR l'objet Projet existant** (table `projets`, entretien de cadrage). **Zéro touche
scoring/cascade/étage 0/run** : `git diff main...HEAD` = modèle + API projet + front + docs. Aucun
fichier scoring/engine. Les parcelles viennent du run servi `q_v6_m8` — **on ne gère que des statuts**.

| Lot | Commit | Contenu |
|-----|--------|---------|
| 0 | constat | modèle existant décortiqué → verdict **additif propre** (`PROJET-PARCOURS-LOT0.md`) |
| 1 | modèle | table `projet_parcelles` (statut de tri), rétro-compatible |
| 2-3 (back) | API | proposer / deck / carte décision / statut |
| 3-5 (front) | UI | tri Tinder + sections réversibles + reprise |

## Lot 0 — Constat (verdict : pas de divergence)
`projets` = **critères seuls** (fiche dite / filtres dérivés / programme), **aucune** relation
parcelle, doctrine « ouvrir = REJOUER ». `pipeline_entries.projet_id` existe déjà (ancre CRM, Phase 2).
→ le modèle supposé (statuts proposée/retenue/écartée) **s'ajoute proprement** en table de liaison.
**Point remonté** : décision #4 « retenues → CRM auto » vs phasage « CRM = Phase 2 » — j'applique le
**phasage** (en Phase 1, `retenue` est un statut ; aucune écriture CRM). À confirmer si tu veux l'auto-CRM
dès maintenant.

## Lot 1 — Modèle `projet_parcelles`
`(id, projet_id FK CASCADE, parcel_id FK CASCADE, statut, rang, proposee_at, timestamps,
UNIQUE(projet_id, parcel_id))`. Statuts : `proposee | retenue | ecartee | a_analyser`. Créée par
`create_all` (idempotent). **Rétro-compatible** : projets existants (« LES LILAS », « Résidence
étudiante… ») intacts, table naît vide. **Écarter ne détruit rien** (réversible).

## Lot 2 — Proposition (recherche → proposées)
`POST /projets/{pid}/proposer` **réutilise la recherche existante** (M22 `faisabilite_sens2` si
programme, sinon `q_v6_m8 _q_v2_list`) — **même source que `/apercu`, aucun re-scoring** — et rattache
les résultats en `proposee` (best-first, `rang`). **UPSERT non destructif** (`ON CONFLICT DO NOTHING`) :
une parcelle déjà décidée n'est **jamais** re-proposée (une écartée ne ressuscite pas au rejeu).

## Lot 3 — Tri Tinder (carte en fond + carte de décision)
`ParcoursTinder` : la **carte remplit l'écran** (store : `moduleMap` surligne les proposées pour le
contexte, `flyTo` **centre la courante**), une **carte de décision flotte** par-dessus —
IDU · **adresse BAN** · tier · **scores Q/A/complétude** · **points clés** (forces ✓ / attentions ⚠,
**dérivés des facteurs, logique du pack apporteur**, sourcés) · **« voir la fiche complète »** (ouvre la
fiche). **✕ Écarter / ✓ Retenir** (optimiste, passage auto à la suivante). **Progression** « N/total ·
X retenues » + barre. Preuve : `parcours-1-tri.png`, `parcours-2-apres-retenir.png`.

## Lot 4 — Sections retenues & écartées (RÉVERSIBLE)
Tiroir : **Retenues** (idu, commune, tier ; « fiche », « retirer » → repasse à trier) + **Écartées —
récupérables** (« fiche », **« ↩ récupérer »** → repasse à trier). **Rien n'est détruit — la boussole.**
Preuve : `parcours-3-sections.png` ; récupération `parcours-4-recuperation.png` (écartées **2 → 1**).

## Lot 5 — Reprise à tout moment
L'état vit en base (`projet_parcelles`). **Quitter** (→ Mes projets) puis **rouvrir** relit
`GET /parcelles` → on reprend **où on s'était arrêté**. Preuve : `parcours-5-reprise.png` — après
récupération l'état exact est **3 / 24 triées · 2 retenues** (identique avant/après quitter-rouvrir).

## Entrée & non-régression
- Entrée : bouton **« Trier les parcelles »** sur la carte projet. **« Ouvrir »** (restitution/rejeu)
  reste **inchangé**. Store `openParcours` (bascule carte + arme le parcours en un geste).
- Nav exclusive respectée : `parcours` nettoyé par `setView`/`setModule`/`toggleOutils`/`openSources`.

## Endpoints (récap)
`POST /projets/{pid}/proposer` · `GET /projets/{pid}/parcelles` · `GET /projets/{pid}/carte/{idu}` ·
`PATCH /projets/{pid}/parcelle/{idu}` (statut, 422 si invalide). Testés live (projet 13).

## Garanties
- **Zéro touche scoring** : `git diff main...HEAD` = `models.py` (+table), `projets.py` (+routes),
  front, docs. Aucun fichier scoring/cascade/étage 0/run/engine. Aucune re-golden.
- **Réversible** prouvé (récupération). **Rétro-compatible** (projets existants intacts).
- `tsc --noEmit` vert ; build Vite OK.

## PHASE 2 — NON faite (cadrée pour mémoire)
« Chercher plus de parcelles » (recherche élargie / ajout manuel) + **lien CRM raffiné** (retenues →
`pipeline_entries` avec `projet_id`, notes, contact). Mandat séparé après validation Phase 1.

*Commits séparés sur `feat/projet-parcours`. Pas de merge.*
