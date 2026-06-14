# RAPPORT — Lot D (UX du DONE)

> Suite de la directive « on fait tout d'un coup ». Lot D livré intégralement.
> **254 tests verts** (+4), ruff clean, JS OK, démo 8/8, baseline 3 000.

## D1 — Export PDF 1 page (document de comité) ✅

Pas de moteur PDF serveur disponible (weasyprint/reportlab/headless-chrome absents) → **one-pager
HTML print-to-PDF** (le standard : navigateur → « Enregistrer en PDF »), comme l'export HTML
existant. `fiche_onepager()` : 1 page A4 (`@page size:A4`), 2 colonnes — verdict + scores,
capacité, **potentiel résiduel**, **bilan** (CA/charge foncière), **contraintes**, **à vérifier**,
**prochaine action**, et une **mini-carte aérienne** (IGN WMS ortho + contour parcelle en overlay
SVG, dégrade proprement hors-ligne). Route `GET /parcels/{idu}/export?format=onepager` (récupère
la géométrie pour l'overlay). Bouton fiche « 📄 Fiche 1 page (PDF) ». Tuile WMS testée (HTTP 200).

## D2 — Comparateur 2-3 parcelles ✅

`GET /compare?idus=a,b,c` → résumé aligné par parcelle (verdict, opp/compl, zone, capacité, SDP
max, taux d'emprise, SDP résiduelle, CA, charge foncière/m², nb contraintes, synthèse). UI : bouton
fiche « ⊕ Comparer » → **barre de sélection** flottante (max 3) → **panneau côte à côte** (tableau,
**meilleure valeur surlignée par ligne**, clic sur un IDU rouvre sa fiche). Ignore proprement un
IDU introuvable.

## D3 — Filtres sauvegardés ✅

Table `saved_filters` (params JSONB, pilote mono-compte). `GET/POST /filters`, `DELETE
/filters/{id}`. UI dans le panneau de filtres : champ nom + « 💾 Sauvegarder » (capture l'état
complet : statuts, seuils opp/compl/surface, sous-densité + seuil, propriétaire) ; **menu déroulant**
pour réappliquer un filtre sauvegardé en un clic ; bouton supprimer.

---

## État global après Lot D

| Critère DONE §7 | État |
|---|---|
| Audit pull (réf/adresse/polygone) | ✅ Lot A |
| Potentiel résiduel | ✅ Lot B (+ C0 hauteurs réelles) |
| Couches Phase 3 | ✅ C1/C3/C4/C5 · ⛔ C2 (PEIGEO bloqué) |
| **Export PDF 1 page** | ✅ **D1** |
| **Comparateur** | ✅ **D2** |
| **Filtres sauvegardés** | ✅ **D3** |
| Pipeline de prospection (statuts + notes) | ✅ (préexistant — Kanban) |

**Le critère DONE §7 est intégralement couvert** (seul C2 reste en attente de la donnée PEIGEO).

## Reste en attente (toi)
1. **C2 — 50 pas géométriques** : whitelist PEIGEO (action environnement).
2. **Calibrage des PLACEHOLDERS** : `buffer_m` ravine, `assemblage_min/individuel`, `prix_m2_lls`,
   `majoration_vrd_pluvial`, seuils A/N (90/5) et ER (50) — non inventés (pas de source).
3. **Revue annexe carte A/N+ER** (async, non bloquante).
